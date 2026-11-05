"""练习知识点的可见性、来源分组与场景隔离回归。"""
import os
import unittest

os.environ.setdefault("ECHOTALK_DB_PASSWORD", "offline-test-only")

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db, get_optional_user
from app.api.endpoints.scenes import router
from app.core.database import Base
from app.core.errors import AppError, register_exception_handlers
from app.models import Chunk, Document, Scene, User
from app.services.scene_service import practice_knowledge


class PracticeKnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.user = User(username="author", password_hash="unused")
        self.db.add(self.user)
        self.db.flush()
        self.db.add_all([
            Scene(id="public", name="Public", source="builtin", package_json={}),
            Scene(id="private", name="Private", source="custom", author_id=self.user.id, status="private", package_json={}),
        ])
        self.db.flush()
        self.a = Document(scene_id="public", filename="menu.md", visibility="user")
        self.b = Document(scene_id="public", filename="staff.md", visibility="ai_only")
        self.c = Document(scene_id="private", filename="private.md", visibility="user")
        self.db.add_all([self.a, self.b, self.c])
        self.db.flush()
        self.full_text = "Full content beyond preview. " * 15 + "END_OF_SECTION"
        self.db.add_all([
            Chunk(document_id=self.a.id, scene_id="public", section="prices", ordinal=1, visibility="user", text=self.full_text),
            Chunk(document_id=self.a.id, scene_id="public", section="prices", ordinal=0, visibility="user", text="First chunk"),
            Chunk(document_id=self.a.id, scene_id="public", section="prices", ordinal=2, visibility="ai_only", text="HIDDEN_STAFF_NOTE"),
            Chunk(document_id=self.b.id, scene_id="public", section="prices", ordinal=0, visibility="user", text="User override in hidden file"),
            Chunk(document_id=self.c.id, scene_id="private", section="prices", ordinal=0, visibility="user", text="PRIVATE_ONLY"),
            Chunk(document_id=self.c.id, scene_id="public", section="bad-link", ordinal=1, visibility="user", text="INVALID_CROSS_SCENE"),
        ])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_full_text_order_and_same_title_sources(self):
        result = practice_knowledge(self.db, "public", None)
        self.assertEqual([d["filename"] for d in result["documents"]], ["menu.md", "staff.md"])
        chunks = result["documents"][0]["sections"][0]["chunks"]
        self.assertEqual([c["text"] for c in chunks], ["First chunk", self.full_text])
        self.assertEqual(result["documents"][1]["sections"][0]["chunks"][0]["text"], "User override in hidden file")

    def test_hidden_and_other_scene_content_excluded(self):
        result = str(practice_knowledge(self.db, "public", self.user))
        for forbidden in ["HIDDEN_STAFF_NOTE", "PRIVATE_ONLY", "INVALID_CROSS_SCENE"]:
            self.assertNotIn(forbidden, result)

    def test_private_scene_requires_author(self):
        with self.assertRaises(AppError) as caught:
            practice_knowledge(self.db, "private", None)
        self.assertEqual(caught.exception.status_code, 404)
        self.assertIn("PRIVATE_ONLY", str(practice_knowledge(self.db, "private", self.user)))

    def test_content_endpoint(self):
        app = FastAPI()
        register_exception_handlers(app)
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_optional_user] = lambda: None
        with TestClient(app) as client:
            response = client.get("/api/scenes/public/knowledge/content")
            self.assertEqual(response.status_code, 200)
            self.assertIn("END_OF_SECTION", response.text)
            self.assertNotIn("HIDDEN_STAFF_NOTE", response.text)
            self.assertEqual(client.get("/api/scenes/private/knowledge/content").status_code, 404)


if __name__ == "__main__":
    unittest.main()
