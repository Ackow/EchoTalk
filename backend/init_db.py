"""显式初始化 EchoTalk 数据表、执行结构迁移并同步内置场景包种子；部署 API 时不会自动执行 DDL。"""
from app import models  # noqa: F401 注册所有模型表
from app.core.database import Base, engine, SessionLocal


def migrate_avatar_preferences() -> None:
    """偏好表迁移：主键从 (user_id) 扩为 (user_id, scene_id)，实现按场景档存储。

    旧表 scene_id 可空且带 scenes 外键；新表 scene_id 为 NOT NULL 主键列、无外键
    （空串表示「跟随场景推荐」档，不属于任何真实场景）。幂等：已迁移则直接返回。
    """
    from sqlalchemy import text

    with engine.connect() as conn:
        nullable = conn.execute(text(
            "SELECT IS_NULLABLE FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'avatar_preferences' "
            "AND COLUMN_NAME = 'scene_id'"
        )).scalar()
        if nullable != "YES":
            return  # 已迁移：scene_id 已是主键一部分（NOT NULL）

        # 先解除 scene_id 上的外键（空串不属于 scenes 表，FK 必须先撤）
        fk = conn.execute(text(
            "SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'avatar_preferences' "
            "AND COLUMN_NAME = 'scene_id' AND REFERENCED_TABLE_NAME = 'scenes' LIMIT 1"
        )).scalar()
        if fk:
            conn.execute(text(f"ALTER TABLE avatar_preferences DROP FOREIGN KEY `{fk}`"))

        # 空场景键归一：历史 NULL（跟随推荐）转为空串，须在 MODIFY NOT NULL 之前完成
        conn.execute(text("UPDATE avatar_preferences SET scene_id = '' WHERE scene_id IS NULL"))

        conn.execute(text(
            "ALTER TABLE avatar_preferences "
            "MODIFY scene_id VARCHAR(50) NOT NULL DEFAULT '', "
            "DROP PRIMARY KEY, ADD PRIMARY KEY (user_id, scene_id)"
        ))
        conn.commit()
        print("avatar_preferences 已迁移：主键扩为 (user_id, scene_id)，支持按场景档存偏好。")


def migrate_user_avatar() -> None:
    """用户表迁移：新增 avatar_path（头像相对路径），NULL 表示未设置。幂等。"""
    from sqlalchemy import text

    with engine.connect() as conn:
        exists = conn.execute(text(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'avatar_path'"
        )).scalar()
        if exists:
            return  # 已迁移
        conn.execute(text("ALTER TABLE users ADD COLUMN avatar_path VARCHAR(128) NULL AFTER password_hash"))
        conn.commit()
        print("users 已迁移：新增 avatar_path，支持用户头像。")


def migrate_user_admin() -> None:
    """用户表迁移：新增 is_admin（管理员标识），默认 0。幂等。"""
    from sqlalchemy import text

    with engine.connect() as conn:
        exists = conn.execute(text(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'is_admin'"
        )).scalar()
        if exists:
            return
        conn.execute(text("ALTER TABLE users ADD COLUMN is_admin TINYINT(1) NOT NULL DEFAULT 0 AFTER avatar_path"))
        conn.commit()
        print("users 已迁移：新增 is_admin，支持管理员权限。")


def ensure_default_admin() -> None:
    """若库中尚无管理员账号，则创建默认管理员（可通过环境变量覆盖用户名/密码）。"""
    import os
    from app.models import User
    from app.services.auth_service import hash_password

    username = os.getenv("ECHOTALK_ADMIN_USERNAME", "admin").strip() or "admin"
    password = os.getenv("ECHOTALK_ADMIN_PASSWORD", "admin123456").strip() or "admin123456"
    with SessionLocal() as db:
        has_admin = db.query(User).filter(User.is_admin == 1).first()
        if has_admin:
            return
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            existing.is_admin = 1
            db.commit()
            print(f"已将现有用户 {username} 提升为管理员。")
            return
        admin = User(username=username, password_hash=hash_password(password), is_admin=1)
        db.add(admin)
        db.commit()
        print(f"已创建默认管理员账号：{username}（请登录后及时修改密码）")


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    migrate_avatar_preferences()
    migrate_user_avatar()
    migrate_user_admin()
    ensure_default_admin()

    from app.scenes.registry import sync_seeds

    with SessionLocal() as db:
        count = sync_seeds(db)
    print(f"EchoTalk 数据表已初始化，内置场景包同步 {count} 个。")
