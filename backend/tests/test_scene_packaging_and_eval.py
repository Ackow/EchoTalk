import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import Base  # noqa: E402
from app.models import PracticeSession, PracticeTurn, Scene, User  # noqa: E402
from app.scenes import knowledge as knowledge_svc  # noqa: E402
from app.scenes import packaging, registry  # noqa: E402
from app.services import scene_service  # noqa: E402
from app.services.session.report import get_session_report  # noqa: E402
from app.services.session.turn import _evaluate_guardrails  # noqa: E402


def _sample_package(scene_id: str = "cafe_test") -> dict:
    return {
        "meta": {
            "id": scene_id,
            "name": "Cafe Test",
            "category": "daily",
            "mode": "conversation",
            "difficulty": "easy",
            "description": "Test cafe scenario",
            "tags": ["coffee"],
            "compat": {"min_app": "2.0.0"},
        },
        "roles": [
            {
                "id": "barista",
                "display_name": "Emma",
                "title": "Barista",
                "persona": "Friendly barista",
                "style": "Short natural replies",
            }
        ],
        "prompt": {
            "opening": "Hi! What can I get for you?",
            "system": "You are a friendly barista.",
            "rules": ["Keep replies under 3 sentences."],
        },
        "objectives": [
            {"id": "obj_1", "label": "Order a drink", "description": "Order one drink"},
        ],
        "state": {"polite_request": False},
        "tools": {"allowed": ["search_knowledge"], "config": {}},
        "stages": [{"id": "s1", "name": "Order", "advance_when": "false"}],
        "finish": {"max_turns": 6, "when": "false"},
        "knowledge": {"files": []},
        "evaluation": {
            "dimensions": [
                {"id": "task_completion", "label": "任务完成度", "weight": 0.4, "source": "state"},
                {"id": "politeness", "label": "礼貌与得体", "weight": 0.2, "source": "llm", "hints": ["please", "could i"]},
                {"id": "accuracy", "label": "语法与用词", "weight": 0.4, "source": "llm"},
            ],
            "notes": "Focus on polite ordering",
        },
        "guardrails": {
            "language": "en",
            "min_words": 3,
            "keyword_tips": [
                {"match": "croissant", "tip": "可颂已售罄，请尝试更换点单。"}
            ],
            "max_warnings_per_turn": 2,
        },
    }


class ScenePackagingAndEvalTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.tmpdir = tempfile.TemporaryDirectory()
        self.patcher = patch.object(knowledge_svc, "STORAGE_ROOT", Path(self.tmpdir.name))
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.tmpdir.cleanup()
        self.engine.dispose()

    def test_upload_and_delete_knowledge_syncs_knowledge_count(self):
        with Session(self.engine) as db:
            user = User(id=1, username="alice", password_hash="x")
            db.add(user)
            pkg_dict = _sample_package("custom_cafe")
            pkg = registry.validate(pkg_dict)
            row = Scene(id="custom_cafe", source="custom", author_id=1)
            registry.apply_package(row, pkg, pkg_dict)
            db.add(row)
            db.commit()

            self.assertEqual(registry.summary(row)["knowledge_count"], 0)
            doc = scene_service.upload_knowledge(
                db, user, "custom_cafe", "menu.txt", b"Latte $4.50\nCroissant sold out", "text/plain", "user"
            )
            db.refresh(row)
            self.assertEqual(registry.summary(row)["knowledge_count"], 1)

            scene_service.delete_knowledge(db, user, "custom_cafe", doc.id)
            db.refresh(row)
            self.assertEqual(registry.summary(row)["knowledge_count"], 0)

    def test_export_and_import_zip_carries_cover(self):
        with Session(self.engine) as db:
            user = User(id=1, username="alice", password_hash="x")
            db.add(user)
            pkg_dict = _sample_package("zip_cafe")
            pkg = registry.validate(pkg_dict)
            row = Scene(id="zip_cafe", source="custom", author_id=1)
            registry.apply_package(row, pkg, pkg_dict)
            db.add(row)
            db.commit()

            fake_png = b"\x89PNG\r\n\x1a\nfake_cover_bytes"
            scene_service.set_cover(db, user, "zip_cafe", "mycover.png", fake_png)
            zip_bytes = packaging.export_zip(db, row)

            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                self.assertIn("cover.png", zf.namelist())
                self.assertEqual(zf.read("cover.png"), fake_png)

            imported, action = packaging.import_package(db, zip_bytes, author_id=1, resolve="rename")
            self.assertEqual(action, "renamed")
            self.assertIsNotNone(imported.cover_path)
            self.assertEqual(knowledge_svc.cover_file(imported.cover_path).read_bytes(), fake_png)

    def test_guardrails_detects_keyword_tips_and_min_words(self):
        pkg = registry.validate(_sample_package())
        tips = _evaluate_guardrails(pkg, "croissant")
        kinds = [t["kind"] for t in tips]
        self.assertIn("keyword_tip", kinds)
        self.assertIn("min_words", kinds)

        tips_long = _evaluate_guardrails(pkg, "Could I have an iced latte please?")
        self.assertEqual(tips_long, [])

    def test_report_computes_evaluation_dimensions(self):
        with Session(self.engine) as db:
            user = User(id=1, username="alice", password_hash="x")
            db.add(user)
            pkg_dict = _sample_package()
            sess = PracticeSession(
                id="sess_1",
                user_id=1,
                scene_id="cafe_test",
                scene_snapshot=pkg_dict,
                state_json={
                    "status": "active",
                    "goals": [{"id": "obj_1", "label": "Order a drink", "done": True}],
                    "scenario_state": {"polite_request": True},
                },
                greeting="Hi!",
                version=1,
            )
            db.add(sess)
            db.add(
                PracticeTurn(
                    id="t1",
                    session_id="sess_1",
                    request_id="req1",
                    number=1,
                    input_text="Could I please have a latte?",
                    response_json={"text": "Sure!"},
                    trace_json=[],
                    grammar_correction={"has_error": False},
                )
            )
            db.commit()

            report = get_session_report(db, 1, "sess_1")
            self.assertIsNotNone(report["evaluation"])
            dims = {d["id"]: d for d in report["evaluation"]["dimensions"]}
            self.assertEqual(dims["task_completion"]["score"], 100)
            self.assertGreaterEqual(dims["politeness"]["score"], 85)
            self.assertEqual(dims["accuracy"]["score"], 100)
            self.assertIsNotNone(report["evaluation"]["scenario_score"])


if __name__ == "__main__":
    unittest.main()
