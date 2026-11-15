"""流式切句缓冲器（_SentenceBuffer）与 SSE 轮次编排单元测试。"""
import asyncio
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import Base
from app.models import PracticeSession, PracticeTurn, Scene, User
from app.services.session import turn as turn_svc


class SentenceBufferTests(unittest.TestCase):
    def test_splits_complete_sentences_and_preserves_decimals(self):
        buf = turn_svc._SentenceBuffer()
        self.assertEqual(buf.push("That iced latte costs $4.50 "), [])
        self.assertEqual(buf.push("for a medium size. Would you "), ["That iced latte costs $4.50 for a medium size."])
        self.assertEqual(buf.push("like oat milk? Sure!"), ["Would you like oat milk?"])
        self.assertEqual(buf.flush(), "Sure!")
        self.assertIsNone(buf.flush())

    def test_short_fragment_waits_for_next_sentence(self):
        buf = turn_svc._SentenceBuffer()
        # "Hi there." is 9 chars (< 10) without !/?/。, so push() holds it until flush()
        self.assertEqual(buf.push("Hi there. Welcome to "), [])
        self.assertEqual(buf.flush(), "Hi there. Welcome to")
        # With '!', short fragment emits immediately
        self.assertEqual(buf.push("Hi! How can I help?"), ["Hi!"])
        self.assertEqual(buf.flush(), "How can I help?")

    def test_newline_boundary_and_sse_formatting(self):
        buf = turn_svc._SentenceBuffer()
        out = buf.push("First full line here\nSecond line")
        self.assertEqual(out, ["First full line here"])
        self.assertEqual(buf.flush(), "Second line")

        sse = turn_svc._sse("text", {"delta": "hello"})
        self.assertTrue(sse.startswith("event: text\ndata: "))
        self.assertTrue(sse.endswith("\n\n"))
        self.assertEqual(json.loads(sse.split("data: ", 1)[1]), {"delta": "hello"})


class StreamTurnOrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        self.user = User(id=1, username="stream_user", password_hash="x")
        pkg = {
            "meta": {"id": "cafe_test", "name": "Cafe Test", "description": "desc", "category": "daily", "mode": "conversation", "difficulty": "entry"},
            "roles": [{"id": "barista", "display_name": "Mia", "title": "Barista"}],
            "prompt": {"system": "Be helpful.", "greeting": "Hi there!"},
            "state": {},
            "objectives": [],
            "stages": [],
            "finish": {"max_turns": 10, "when": "turn_count >= 10"},
            "tools": {"allowed": []},
        }
        scene = Scene(
            id="cafe_test",
            name="Cafe Test",
            description="desc",
            category="daily",
            mode="conversation",
            difficulty="beginner",
            source="builtin",
            status="published",
            package_json=pkg,
        )
        sess = PracticeSession(
            id="sess_stream_1",
            user_id=1,
            scene_id="cafe_test",
            scene_snapshot=pkg,
            state_json=turn_svc.initial_state(turn_svc.validate(pkg)),
            greeting="Hi there!",
            version=1,
        )
        self.db.add_all([self.user, scene, sess])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_stream_turn_emits_meta_text_audio_done_and_persists_turn(self):
        class FakeGraph:
            def __init__(self, on_delta):
                self.on_delta = on_delta

            async def ainvoke(self, state, _config):
                await self.on_delta("Sure, one oat latte ")
                await self.on_delta("coming right up! Anything else?")
                return {
                    **state,
                    "model_calls": 1,
                    "tool_results": [],
                    "final_text": "Sure, one oat latte coming right up! Anything else?",
                }

        def fake_build_graph(_package, _model, _registry, _before, on_delta=None):
            return FakeGraph(on_delta)

        async def fake_grammar(*_args, **_kwargs):
            return {"has_error": False, "original": "One oat latte please", "corrected": "One oat latte please", "issue_type": "none", "explanation": "", "better_expressions": []}

        async def fake_synthesize(*_args, **_kwargs):
            return b"ID3-MP3"

        async def collect():
            events = []
            with (
                patch.object(turn_svc, "create_chat_model", return_value=object()),
                patch.object(turn_svc, "build_async_conversation_graph", side_effect=fake_build_graph),
                patch.object(turn_svc, "_evaluate_grammar", side_effect=fake_grammar),
                patch("app.services.tts_service.synthesize", side_effect=fake_synthesize),
            ):
                async for raw in turn_svc.stream_turn(
                    self.engine,
                    self.user.id,
                    "sess_stream_1",
                    "req_001",
                    "One oat latte please",
                    voice_style="jenny",
                    include_audio=True,
                ):
                    lines = raw.strip().splitlines()
                    ev = lines[0].replace("event: ", "")
                    data = json.loads(lines[1].replace("data: ", ""))
                    events.append((ev, data))
            return events

        events = asyncio.run(collect())
        names = [e[0] for e in events]
        self.assertIn("delta", names)
        self.assertIn("audio", names)
        self.assertIn("done", names)
        self.assertEqual(names[-1], "audio_end")

        audio_events = [d for ev, d in events if ev == "audio"]
        self.assertEqual(len(audio_events), 2)
        self.assertEqual(audio_events[0]["text"], "Sure, one oat latte coming right up!")
        self.assertEqual(audio_events[1]["text"], "Anything else?")

        saved_turns = self.db.query(PracticeTurn).filter(PracticeTurn.session_id == "sess_stream_1").all()
        self.assertEqual(len(saved_turns), 1)
        self.assertEqual(saved_turns[0].request_id, "req_001")


if __name__ == "__main__":
    unittest.main()
