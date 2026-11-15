"""混合检索与 RRF 重排单元测试（离线 SQLite + 桩向量/关键词召回）。"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import Base
from app.models import Chunk, ChunkEmbedding, Document, Scene
from app.scenes import embedding as embedding_svc
from app.scenes import retrieval


class RetrievalUnitTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        scene = Scene(
            id="scene_rag",
            name="RAG Test",
            description="desc",
            category="daily",
            mode="conversation",
            difficulty="beginner",
            source="custom",
            package_json={"meta": {"id": "scene_rag", "name": "RAG Test"}},
        )
        doc = Document(id=1, scene_id="scene_rag", filename="guide.md")
        self.db.add_all([scene, doc])
        self.db.flush()

        self.chunks = [
            Chunk(id=10, scene_id="scene_rag", document_id=1, section="menu", ordinal=1, visibility="public", text="Iced oat latte costs 5 dollars."),
            Chunk(id=20, scene_id="scene_rag", document_id=1, section="menu", ordinal=2, visibility="public", text="Croissant is freshly baked every morning."),
            Chunk(id=30, scene_id="scene_rag", document_id=1, section="policy", ordinal=3, visibility="ai_only", text="Refund policy allows free remake."),
        ]
        self.db.add_all(self.chunks)
        self.db.add_all([
            ChunkEmbedding(chunk_id=10, model="stub", embedding=embedding_svc.pack([1.0, 0.0])),
            ChunkEmbedding(chunk_id=20, model="stub", embedding=embedding_svc.pack([0.8, 0.2])),
            ChunkEmbedding(chunk_id=30, model="stub", embedding=embedding_svc.pack([0.0, 1.0])),
        ])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_rrf_fuse_boosts_shared_candidates_and_respects_top_k(self):
        fused = retrieval._rrf_fuse([[10, 20, 30], [20, 40, 10]], top_k=2)
        # 10 (1/61 + 1/63) vs 20 (1/62 + 1/61) -> 20 has higher combined RRF score
        self.assertEqual(fused, [20, 10])
        self.assertEqual(retrieval._rrf_fuse([], top_k=3), [])

    def test_search_scene_empty_query_and_empty_scene(self):
        self.assertEqual(retrieval.search_scene(self.db, "scene_rag", "   ")["mode"], "none")
        res = retrieval.search_scene(self.db, "non_existent_scene", "latte")
        self.assertEqual(res["mode"], "none")
        self.assertEqual(res["items"], [])

    def test_search_scene_hybrid_mode_combines_vector_and_keyword(self):
        with (
            patch.object(retrieval, "_ensure_fulltext", return_value=True),
            patch.object(retrieval, "_keyword_rank", return_value=[20, 10]),
            patch.object(embedding_svc, "available", return_value=True),
            patch.object(embedding_svc, "embed_texts", return_value=[[1.0, 0.0]]),
        ):
            res = retrieval.search_scene(self.db, "scene_rag", "oat latte", top_k=2)
        self.assertEqual(res["mode"], "hybrid")
        self.assertEqual(len(res["items"]), 2)
        self.assertEqual({item["chunk_id"] for item in res["items"]}, {10, 20})

    def test_search_scene_falls_back_to_keyword_when_embedding_unavailable(self):
        with (
            patch.object(retrieval, "_ensure_fulltext", return_value=True),
            patch.object(retrieval, "_keyword_rank", return_value=[30]),
            patch.object(embedding_svc, "available", return_value=False),
        ):
            res = retrieval.search_scene(self.db, "scene_rag", "refund", top_k=2)
        self.assertEqual(res["mode"], "keyword")
        self.assertEqual([item["chunk_id"] for item in res["items"]], [30])
        self.assertEqual(res["items"][0]["visibility"], "ai_only")


if __name__ == "__main__":
    unittest.main()
