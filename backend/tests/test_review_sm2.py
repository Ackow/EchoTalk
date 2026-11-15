"""SM-2 间隔重复算法边界单元测试（基于内存 SQLite）。"""
import sys
import unittest
from datetime import timedelta
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import Base
from app.core.timeutil import utcnow
from app.models.listening import UserXpState
from app.models.review import ReviewItem
from app.models.user import User
from app.services import review_service


class ReviewSm2UnitTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        review_service._TABLE_READY = True

        self.user = User(id=1, username="sm2_tester", password_hash="x")
        self.db.add(self.user)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _add_item(self, **overrides) -> ReviewItem:
        defaults = dict(
            user_id=1,
            kind="expression",
            prompt="How to ask for a refund?",
            answer="Could I get a refund for this?",
            repetitions=0,
            interval_days=0,
            ease_factor=2.5,
            mastery=0,
            status="active",
            due_at=utcnow() - timedelta(hours=1),
        )
        defaults.update(overrides)
        item = ReviewItem(**defaults)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def test_again_resets_progress_and_clamps_ease_and_mastery(self):
        item = self._add_item(repetitions=3, interval_days=10, ease_factor=1.35, mastery=0)
        res = review_service.submit_review_result(self.db, 1, item.id, "again")
        out = res["item"]
        self.assertEqual(out["repetitions"], 0)
        self.assertEqual(out["interval_days"], 0)
        self.assertEqual(out["ease_factor"], 1.3)
        self.assertEqual(out["mastery"], 0)
        self.assertEqual(out["status"], "active")

    def test_hard_sets_one_day_interval_and_clamps_ease(self):
        item = self._add_item(repetitions=0, interval_days=0, ease_factor=1.32, mastery=0)
        res = review_service.submit_review_result(self.db, 1, item.id, "hard")
        out = res["item"]
        self.assertEqual(out["repetitions"], 1)
        self.assertEqual(out["interval_days"], 1)
        self.assertEqual(out["ease_factor"], 1.3)
        self.assertEqual(out["mastery"], 1)
        self.assertEqual(out["status"], "active")

    def test_good_progression_and_mastered_threshold(self):
        item = self._add_item(repetitions=0, interval_days=0, ease_factor=2.5, mastery=2)
        r1 = review_service.submit_review_result(self.db, 1, item.id, "good")["item"]
        self.assertEqual((r1["repetitions"], r1["interval_days"], r1["mastery"], r1["status"]), (1, 1, 3, "active"))

        r2 = review_service.submit_review_result(self.db, 1, item.id, "good")["item"]
        self.assertEqual((r2["repetitions"], r2["interval_days"], r2["mastery"], r2["status"]), (2, 3, 4, "active"))

        r3 = review_service.submit_review_result(self.db, 1, item.id, "good")["item"]
        self.assertEqual((r3["repetitions"], r3["interval_days"], r3["mastery"], r3["status"]), (3, 8, 5, "mastered"))

    def test_easy_caps_ease_at_3_and_awards_clear_due_bonus_xp(self):
        item = self._add_item(repetitions=1, interval_days=1, ease_factor=2.95, mastery=4)
        res = review_service.submit_review_result(self.db, 1, item.id, "easy")
        out = res["item"]
        self.assertEqual(out["repetitions"], 3)
        self.assertEqual(out["ease_factor"], 3.0)
        self.assertGreaterEqual(out["interval_days"], 7)
        self.assertEqual(out["mastery"], 5)
        self.assertEqual(out["status"], "mastered")
        self.assertEqual(res["stats"]["due"], 0)
        xp_state = self.db.get(UserXpState, 1)
        self.assertIsNotNone(xp_state)
        self.assertEqual(xp_state.total_xp, 18)  # 3 base + 15 clear-due bonus


if __name__ == "__main__":
    unittest.main()
