"""统一数据库幂等建表与列迁移逻辑。

收敛原本分散在 main.py、debate_service.py、avatars.py 中的手写 ALTER TABLE，
确保 FastAPI lifespan 启动阶段与单元测试内存库均可安全幂等执行。
"""
from __future__ import annotations

from weakref import WeakSet

from sqlalchemy import inspect as sa_inspect, text
from sqlalchemy.engine import Connection, Engine

_CHECKED_DEBATE_ENGINES: WeakSet[Engine] = WeakSet()

_PRACTICE_TURN_COLUMNS: dict[str, str] = {
    "pronunciation_score": "JSON NULL",
    "grammar_correction": "JSON NULL",
}

_AVATAR_COLUMNS: dict[str, str] = {
    "is_public": "INTEGER NOT NULL DEFAULT 0",
    "author_name": "VARCHAR(100) NOT NULL DEFAULT ''",
    "source_avatar_id": "VARCHAR(50)",
}

_DEBATE_TABLE_COLUMNS: dict[str, dict[str, str]] = {
    "debate_topics": {
        "background_context": "TEXT NULL",
        "key_expressions": "JSON NULL",
        "default_style": "VARCHAR(24) NOT NULL DEFAULT 'balanced'",
        "scene_type": "VARCHAR(24) NOT NULL DEFAULT 'debate'",
        "user_role_label": "VARCHAR(64) NOT NULL DEFAULT '候选人 / 主讲人'",
        "roles_config": "JSON NULL",
        "stages_config": "JSON NULL",
        "opponent_name": "VARCHAR(64) NOT NULL DEFAULT 'Sonia'",
        "opponent_title": "VARCHAR(64) NOT NULL DEFAULT '对手辩手'",
        "opponent_persona": "TEXT NULL",
        "opponent_voice": "VARCHAR(32) NOT NULL DEFAULT 'sonia'",
        "opponent_avatar_id": "VARCHAR(32) NOT NULL DEFAULT 'sarah_2d'",
        "knowledge_doc_ids": "JSON NULL",
        "cover_path": "VARCHAR(512) NULL",
        "tools_config": "JSON NULL",
        "status": "VARCHAR(24) NOT NULL DEFAULT 'private'",
        "likes_count": "INT NOT NULL DEFAULT 0",
        "favorites_count": "INT NOT NULL DEFAULT 0",
    },
    "debate_sessions": {
        "scene_type": "VARCHAR(24) NOT NULL DEFAULT 'debate'",
    },
    "debate_turns": {
        "role_title": "VARCHAR(64) NOT NULL DEFAULT ''",
        "avatar_id": "VARCHAR(32) NOT NULL DEFAULT ''",
    },
}


def _resolve_engine(bind: Engine | Connection) -> Engine:
    return bind.engine if isinstance(bind, Connection) else bind


def _add_missing_columns(bind: Engine | Connection, table_columns: dict[str, dict[str, str]]) -> None:
    engine = _resolve_engine(bind)
    inspector = sa_inspect(engine)
    existing_tables = set(inspector.get_table_names())
    statements: list[str] = []
    for table_name, columns_map in table_columns.items():
        if table_name not in existing_tables:
            continue
        existing_cols = {c["name"] for c in inspector.get_columns(table_name)}
        for col_name, col_ddl in columns_map.items():
            if col_name not in existing_cols:
                statements.append(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_ddl}")
    if not statements:
        return
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


def ensure_avatar_columns(bind: Engine | Connection) -> None:
    """补齐 avatars 表发布与来源字段。"""
    _add_missing_columns(bind, {"avatars": _AVATAR_COLUMNS})


def ensure_debate_schema(bind: Engine | Connection) -> None:
    """确保多角色辩论/圆桌及关联表已建表并补齐增量列。"""
    from app.models import DebateSession, DebateTopic, DebateTurn, PersonalChunk, ReviewItem, UserXpState
    from app.models.debate import DebateTopicReaction

    engine = _resolve_engine(bind)
    for tbl in (
        DebateTopic,
        DebateTopicReaction,
        DebateSession,
        DebateTurn,
        ReviewItem,
        UserXpState,
        PersonalChunk,
    ):
        tbl.__table__.create(bind=engine, checkfirst=True)
    if engine not in _CHECKED_DEBATE_ENGINES:
        _add_missing_columns(engine, _DEBATE_TABLE_COLUMNS)
        _CHECKED_DEBATE_ENGINES.add(engine)


def run_startup_migrations(bind: Engine | Connection) -> None:
    """应用启动阶段统一执行的建表与幂等列迁移。"""
    from app.models.avatar import AvatarPreset
    from app.models.listening import ListeningAttempt, ListeningProgress, ListeningUnit, UserXpState

    engine = _resolve_engine(bind)
    AvatarPreset.__table__.create(bind=engine, checkfirst=True)
    for tbl in (ListeningUnit, ListeningProgress, ListeningAttempt, UserXpState):
        tbl.__table__.create(bind=engine, checkfirst=True)
    _add_missing_columns(engine, {"practice_turns": _PRACTICE_TURN_COLUMNS, "avatars": _AVATAR_COLUMNS})
    ensure_debate_schema(engine)
