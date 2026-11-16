"""SaaS 订阅、每日免费额度、积分抵扣开关、任务签到与兑换码单元测试。"""
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.core.errors import AppError
from app.core.migrations import run_startup_migrations
from app.models import User
from app.models.saas import RedeemCode, SaasPlanConfig
from app.services import saas_service


class SaasServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=self.engine)
        run_startup_migrations(self.engine)
        SessionLocal = sessionmaker(bind=self.engine)
        self.db = SessionLocal()
        saas_service.ensure_saas_defaults(self.db)
        self.user = User(username="test_saas_user", password_hash="salt$hash", credits_balance=50)
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

    def tearDown(self):
        self.db.close()

    def test_free_quota_then_credit_overage_and_switch(self):
        # 将 free 用户的每日共享免费额度池设为 6 点，practice_turn 每次消耗 3 点
        free_plan = self.db.get(SaasPlanConfig, "free")
        free_plan.daily_free_credits = 6
        quotas = dict(free_plan.quotas_json)
        quotas["practice_turn"] = {"credit_cost": 3, "allow_overage_credits": True}
        free_plan.quotas_json = quotas
        self.db.add(free_plan)
        self.db.commit()

        # 前 2 次走免费额度，不扣积分
        r1 = saas_service.check_and_consume_quota(self.db, self.user, "practice_turn")
        r2 = saas_service.check_and_consume_quota(self.db, self.user, "practice_turn")
        self.assertEqual(r1["mode"], "free_quota")
        self.assertEqual(r2["remaining_free"], 0)
        self.assertEqual(self.user.credits_balance, 50)

        # 第 3 次超出免费额度，走积分抵扣（-3）
        r3 = saas_service.check_and_consume_quota(self.db, self.user, "practice_turn")
        self.assertEqual(r3["mode"], "credits")
        self.assertEqual(r3["credits_spent"], 3)
        self.assertEqual(self.user.credits_balance, 47)

        # 关闭用户「超额自动使用积分」开关 -> 第 4 次应被拦截
        self.user.auto_use_credits = 0
        self.db.commit()
        with self.assertRaises(AppError) as ctx:
            saas_service.check_and_consume_quota(self.db, self.user, "practice_turn")
        self.assertEqual(ctx.exception.code, "QUOTA_EXCEEDED")

    def test_checkin_and_tasks_reward(self):
        res = saas_service.daily_checkin(self.db, self.user)
        self.assertEqual(res["checkin_streak"], 1)
        self.assertEqual(res["credits_earned"], 10)
        self.assertEqual(self.user.credits_balance, 60)

        # 重复签到应拦截
        with self.assertRaises(AppError) as ctx:
            saas_service.daily_checkin(self.db, self.user)
        self.assertEqual(ctx.exception.code, "ALREADY_CHECKED_IN")

        # 触发任务进度并领奖
        saas_service.record_task_progress(self.db, self.user.id, "daily_practice_1")
        tasks = saas_service.get_tasks_with_progress(self.db, self.user)
        t = next(x for x in tasks if x["task_code"] == "daily_practice_1")
        self.assertTrue(t["claimable"])
        claim = saas_service.claim_task_reward(self.db, self.user, "daily_practice_1")
        self.assertEqual(claim["credits_earned"], 15)
        self.assertEqual(self.user.credits_balance, 75)

    def test_mock_checkout_zip_permissions_and_redeem(self):
        # Free 用户不能导入/导出 ZIP
        with self.assertRaises(AppError):
            saas_service.check_zip_permission(self.db, self.user, "import")
        with self.assertRaises(AppError):
            saas_service.check_zip_permission(self.db, self.user, "export")

        # 模拟升级 Pro：可导入 ZIP，仍不可导出 ZIP
        saas_service.mock_checkout(self.db, self.user, order_type="plan_upgrade", target_tier="pro", billing_cycle="monthly")
        saas_service.check_zip_permission(self.db, self.user, "import")
        with self.assertRaises(AppError):
            saas_service.check_zip_permission(self.db, self.user, "export")
        self.assertGreater(self.user.credits_balance, 50)

        # 兑换码核销升级 Enterprise：可导出 ZIP
        rc = RedeemCode(code="ECHO-ENT-TEST", reward_type="plan_days", reward_credits=500, reward_tier="enterprise", reward_days=30)
        self.db.add(rc)
        self.db.commit()
        redeem_res = saas_service.redeem_code(self.db, self.user, "echo-ent-test")
        self.assertEqual(redeem_res["plan_tier"], "enterprise")
        saas_service.check_zip_permission(self.db, self.user, "export")


if __name__ == "__main__":
    unittest.main()
