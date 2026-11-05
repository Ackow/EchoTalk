"""离线验证 Agent 的状态/工具/持久化边界，不调用模型或开发数据库。"""
import os
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from unittest.mock import AsyncMock
from tempfile import TemporaryDirectory

os.environ.setdefault("ECHOTALK_DB_PASSWORD", "offline-test-only")

import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user, get_db
from app.api.endpoints.sessions import router
from app.agents.context import render
from app.agents.model_gateway import create_chat_model
from app.agents.tools import ToolRegistry
from app.core.database import Base
from app.core.errors import AppError, register_exception_handlers
from app.models import PracticeSession, PracticeTurn, Scene, User
from app.scenes.schema import ScenePackage
from app.services import session_service
from app.services.scene_runtime import advance, initial_state


def meeting_package():
    path = Path(__file__).resolve().parents[1] / "app/content/scenes/launch_alignment.yaml"
    return ScenePackage.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


class ScriptedModel:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.prompts = []
        self.bound_names = []

    def bind_tools(self, tools):
        self.bound_names = [t.name for t in tools]
        return self

    def invoke(self, messages):
        self.prompts.append(messages)
        value = next(self.responses)
        if isinstance(value, Exception):
            raise value
        return value


def call(name, args, ident="call_1"):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": ident, "type": "tool_call"}])


class ConversationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.user = User(username="learner", password_hash="unused")
        self.other = User(username="other", password_hash="unused")
        self.package = meeting_package()
        self.db.add_all([self.user, self.other, Scene(
            id=self.package.meta.id, name=self.package.meta.name,
            package_json=self.package.model_dump(mode="json"), source="builtin",
        )])
        self.db.commit()
        self.uid, self.other_uid = self.user.id, self.other.id
        self.sid = session_service.create_session(self.db, self.user, self.package.meta.id)["id"]

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def run_turn(self, model, text="We are delayed.", request_id="request_1", **kwargs):
        return session_service.run_turn(self.db, self.uid, self.sid, request_id, text, model=model, **kwargs)

    def test_plain_reply_and_idempotency(self):
        model = ScriptedModel(AIMessage("What is blocking you?"))
        first = self.run_turn(model)
        self.assertEqual(first, self.run_turn(model))
        self.assertEqual(len(model.prompts), 1)
        self.assertEqual(first["state"]["turn_count"], 1)
        self.assertEqual(first["version"], 1)
        with self.assertRaises(AppError) as caught:
            self.run_turn(model, text="Different input")
        self.assertEqual(caught.exception.code, "TURN_ID_CONFLICT")

    def test_state_tool_and_goal_persist(self):
        model = ScriptedModel(
            call("update_scene_state", {"key": "reported", "value": True, "evidence": "We are delayed."}),
            AIMessage("What is your next step?"),
        )
        result = self.run_turn(model)
        self.assertTrue(result["state"]["scenario_state"]["reported"])
        self.assertTrue(result["state"]["goals"][0]["done"])
        self.assertEqual(result["state"]["turn_count"], 1)
        self.assertIn('"reported": true', model.prompts[1][0].content)
        with Session(self.engine) as reopened:
            saved = session_service.get_session(reopened, self.uid, self.sid)
            self.assertEqual(saved["turns"][0], result)
            trace = reopened.scalar(select(PracticeTurn)).trace_json
            self.assertTrue(trace[0]["ok"])

    def test_invalid_tools_do_not_mutate(self):
        for name, args in [
            ("delete_all", {}),
            ("update_scene_state", {"key": "reported", "value": "yes", "evidence": "We are delayed."}),
            ("update_scene_state", {"key": "reported", "value": True, "evidence": "fabricated"}),
            ("update_scene_state", {"key": "admin", "value": True, "evidence": "We are delayed."}),
        ]:
            with self.subTest(name=name, args=args):
                result = self.run_turn(ScriptedModel(call(name, args), AIMessage("Please clarify.")), request_id=f"case_{len(self.db.scalars(select(PracticeTurn)).all())}")
                self.assertFalse(result["state"]["scenario_state"]["reported"])

    def test_model_failure_rolls_back_tool_changes(self):
        model = ScriptedModel(
            call("update_scene_state", {"key": "reported", "value": True, "evidence": "We are delayed."}),
            RuntimeError("offline"),
        )
        with self.assertRaises(AppError):
            self.run_turn(model)
        saved = session_service.get_session(self.db, self.uid, self.sid)
        self.assertEqual(saved["version"], 0)
        self.assertEqual(saved["turns"], [])
        self.assertFalse(saved["state"]["scenario_state"]["reported"])

    def test_retrieval_is_internal_and_not_in_history(self):
        model = ScriptedModel(call("search_knowledge", {"query": "launch"}), AIMessage("Could you explain the delay?"))
        seen = []
        def search(query, top_k):
            seen.append((query, top_k))
            return {"items": [{"visibility": "ai_only", "text": "internal_fixture"}]}
        result = self.run_turn(model, search=search)
        self.assertEqual(seen, [("launch", 4)])
        self.assertNotIn("internal_fixture", str(result))
        self.assertIn("internal_fixture", str(model.prompts[1]))
        followup = ScriptedModel(AIMessage("Thanks."))
        self.run_turn(followup, request_id="next")
        self.assertNotIn("internal_fixture", str(followup.prompts))

    def test_isolation(self):
        with self.assertRaises(AppError) as caught:
            session_service.get_session(self.db, self.other_uid, self.sid)
        self.assertEqual(caught.exception.status_code, 404)
        with self.assertRaises(AppError):
            session_service.run_turn(self.db, self.other_uid, self.sid, "x", "Hello", model=ScriptedModel())

    def test_private_scene_cannot_start_session(self):
        scene = self.db.get(Scene, self.package.meta.id)
        scene.source, scene.author_id, scene.status = "custom", self.other_uid, "private"
        self.db.commit()
        with self.assertRaises(AppError) as caught:
            session_service.create_session(self.db, self.user, scene.id)
        self.assertEqual(caught.exception.status_code, 404)

    def test_missing_model_config_and_empty_reply(self):
        with patch.dict(os.environ, {"ECHOTALK_CHAT_API_KEY": "", "ECHOTALK_CHAT_MODEL": ""}):
            with self.assertRaises(AppError) as caught:
                create_chat_model()
            self.assertEqual(caught.exception.code, "CHAT_NOT_CONFIGURED")
        with self.assertRaises(AppError) as caught:
            self.run_turn(ScriptedModel(AIMessage("")))
        self.assertEqual(caught.exception.code, "CHAT_EMPTY_RESPONSE")
        self.assertEqual(self.db.get(PracticeSession, self.sid).version, 0)

    def test_concurrent_version_conflict(self):
        engine, sid = self.engine, self.sid
        class ConcurrentModel(ScriptedModel):
            def invoke(self, messages):
                with Session(engine) as concurrent:
                    concurrent.execute(update(PracticeSession).where(PracticeSession.id == sid).values(version=1))
                    concurrent.commit()
                return AIMessage("Hello")
        with self.assertRaises(AppError) as caught:
            self.run_turn(ConcurrentModel())
        self.assertEqual(caught.exception.code, "SESSION_VERSION_CONFLICT")
        self.assertEqual(self.db.scalars(select(PracticeTurn)).all(), [])

    def test_tool_budget_terminates(self):
        responses = [call("search_knowledge", {"query": "launch"}, str(n)) for n in range(4)]
        with self.assertRaises(AppError) as caught:
            self.run_turn(ScriptedModel(*responses), search=lambda q, k: {})
        self.assertEqual(caught.exception.code, "CHAT_TOOL_LIMIT")
        self.assertEqual(self.db.get(PracticeSession, self.sid).version, 0)

    def test_finish_and_reject_next_turn(self):
        row = self.db.get(PracticeSession, self.sid)
        state = deepcopy(row.state_json)
        state["scenario_state"].update(reported=True, clarified=True, next_step="Ship tomorrow")
        row.state_json = state
        self.db.commit()
        result = self.run_turn(ScriptedModel(AIMessage("Thanks, we have a plan.")))
        self.assertEqual(result["state"]["finish_reason"], "condition_met")
        with self.assertRaises(AppError) as caught:
            self.run_turn(ScriptedModel(), request_id="next")
        self.assertEqual(caught.exception.code, "SESSION_FINISHED")

    def test_api_validation_and_read(self):
        app = FastAPI()
        register_exception_handlers(app)
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_current_user] = lambda: self.user
        app.dependency_overrides[get_db] = lambda: self.db
        with TestClient(app) as client:
            self.assertEqual(client.get(f"/api/sessions/{self.sid}").status_code, 200)
            for text in ["", "   ", "x" * 4001]:
                response = client.post(f"/api/sessions/{self.sid}/turns", json={"request_id": "x", "text": text})
                self.assertEqual(response.status_code, 422)

    def test_greeting_audio_requires_ownership_and_valid_voice_options(self):
        app = FastAPI()
        register_exception_handlers(app)
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_current_user] = lambda: self.user
        app.dependency_overrides[get_db] = lambda: self.db
        with TemporaryDirectory() as folder:
            path = Path(folder) / "greeting.mp3"
            path.write_bytes(b"cached-audio")
            with patch("app.api.endpoints.sessions.greeting_audio_service.get_audio", AsyncMock(return_value=path)) as audio:
                with TestClient(app) as client:
                    response = client.get(f"/api/sessions/{self.sid}/greeting-audio")
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.content, b"cached-audio")
                    self.assertIn("private", response.headers["cache-control"])
                    for query in ["voice_style=unknown", "speech_rate=2", "speech_rate=nan"]:
                        self.assertEqual(client.get(f"/api/sessions/{self.sid}/greeting-audio?{query}").status_code, 422)
                    app.dependency_overrides[get_current_user] = lambda: self.other
                    self.assertEqual(client.get(f"/api/sessions/{self.sid}/greeting-audio").status_code, 404)
            self.assertEqual(audio.await_count, 1)

    def test_runtime_stage_and_accumulated_goals(self):
        data = self.package.model_dump()
        data["stages"] = [
            {"id": "intro", "name": "Intro", "exit_when": "state.reported == true"},
            {"id": "plan", "name": "Plan"},
        ]
        package = ScenePackage.model_validate(data)
        state = initial_state(package)
        before = deepcopy(state["scenario_state"])
        state.update(tool_results=[], turn_count=1, stage_turns=1)
        state["scenario_state"]["reported"] = True
        state.update(advance(package, state, before))
        self.assertEqual(state["stage"], "plan")
        self.assertEqual(state["stage_turns"], 0)
        self.assertTrue(state["goals"][0]["done"])
        state["scenario_state"]["reported"] = False
        self.assertTrue(advance(package, state, before)["goals"][0]["done"])

    def test_render_and_unimplemented_tools(self):
        self.assertNotIn("{roles.", render(self.package.prompt.system, self.package))
        registry = ToolRegistry(self.package, "input", lambda q, k: {})
        self.assertNotIn("get_hint", [t.name for t in registry.schemas()])

    def test_missing_greeting_still_opens_conversation(self):
        scene = self.db.get(Scene, self.package.meta.id)
        data = deepcopy(scene.package_json)
        data["prompt"]["greeting"] = "   "
        scene.package_json = data
        self.db.commit()
        created = session_service.create_session(self.db, self.user, scene.id)
        self.assertIn(self.package.roles[0].display_name, created["greeting"])
        self.assertTrue(created["greeting"].endswith("?"))

    def test_auth_is_required(self):
        app = FastAPI()
        register_exception_handlers(app)
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: self.db
        with TestClient(app) as client:
            self.assertEqual(client.post("/api/sessions", json={"scene_id": self.package.meta.id}).status_code, 401)

    def test_snapshot_survives_scene_edit(self):
        scene = self.db.get(Scene, self.package.meta.id)
        data = deepcopy(scene.package_json)
        data["prompt"]["system"] = "Different role after edit"
        scene.package_json = data
        self.db.commit()
        model = ScriptedModel(AIMessage("Hello"))
        self.run_turn(model)
        self.assertNotIn("Different role after edit", model.prompts[0][0].content)
        self.assertIn("Product Manager", model.prompts[0][0].content)


if __name__ == "__main__":
    unittest.main()
