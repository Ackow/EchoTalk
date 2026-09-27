"""ScenePackage：场景包 v2 的声明模型与全量校验（设计稿场景包方案 §4.2）。

创建、编辑、导入三个入口共用同一模型；校验失败抛 SceneValidationError，
由 API 层转换为 422 SCENE_INVALID_PACKAGE（detail 为字段级错误列表）。
"""
import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core import expr

# 工具注册表白名单：包只能引用这些已注册工具，不定义实现
REGISTERED_TOOLS = {
    "search_knowledge",
    "lookup_word",
    "get_learning_profile",
    "calculate_order",
    "modify_order",
    "update_scene_state",
    "get_hint",
    "add_review_task",
    "next_interview_stage",
}

CATEGORIES = {"daily", "business", "career", "academic", "custom"}
MODES = {"conversation", "interview", "debate"}
# 难度五级：英文枚举存储（前后端契约），前端负责映射中文标签与配色
DIFFICULTY_LEVELS = ("entry", "easy", "normal", "hard", "expert")
# 历史值 → 新枚举迁移映射（v1.4 及之前：CEFR 区间 / 中文三档）
_LEGACY_DIFFICULTY = {"简单": "easy", "普通": "normal", "困难": "hard"}
_ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,49}$")


def normalize_difficulty(value: str | None) -> str | None:
    """历史难度值归一为五级枚举：CEFR 按首字母归档（A→easy / B→normal / C+→hard），中文三档直接映射，未知归 normal。"""
    if not value:
        return None
    text = value.strip()
    if text in DIFFICULTY_LEVELS:
        return text
    if text in _LEGACY_DIFFICULTY:
        return _LEGACY_DIFFICULTY[text]
    first = text[:1].upper()
    if first == "A":
        return "easy"
    if first == "B":
        return "normal"
    if first == "C":
        return "hard"
    return "normal"


class SceneValidationError(ValueError):
    """场景包校验失败：errors 为 (字段路径, 原因) 列表。"""

    def __init__(self, errors: list[tuple[str, str]]):
        self.errors = errors
        summary = "；".join(f"{path}: {reason}" for path, reason in errors[:5])
        super().__init__(f"场景包校验失败（{len(errors)} 处）：{summary}")


class SceneMeta(BaseModel):
    """包身份信息：ID、名称、分类、难度、模式与版本。"""

    id: str
    name: str = Field(min_length=1, max_length=100)
    description: str = ""
    category: Literal["daily", "business", "career", "academic", "custom"] = "custom"
    difficulty: str | None = None  # 五级英文枚举：entry/easy/normal/hard/expert
    mode: Literal["conversation", "interview", "debate"] = "conversation"
    version: int = 2
    compat: dict[str, str] = Field(default_factory=lambda: {"min_app": "2.0.0"})
    author: str | None = None
    tags: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("id")
    @classmethod
    def _check_id(cls, value: str) -> str:
        if not _ID_RE.match(value):
            raise ValueError("id 需匹配 ^[a-z][a-z0-9_]{1,49}$（小写字母开头，仅小写字母/数字/下划线）")
        return value

    @field_validator("difficulty")
    @classmethod
    def _check_difficulty(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip().lower()
        if text not in DIFFICULTY_LEVELS:
            raise ValueError(f"difficulty 需为 {'/'.join(DIFFICULTY_LEVELS)} 之一")
        return text


class SceneRole(BaseModel):
    """角色：1–4 个，含性格与形象/声音推荐（§4.7：仅为推荐值）。"""

    id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,29}$")
    display_name: str = Field(min_length=1, max_length=50)
    title: str | None = None
    personality: str | None = None
    voice: str | None = None      # TTS 声音风格推荐
    avatar: str | None = None     # 数字人形象推荐
    backstage: bool = False       # true = 不参与对话（评估角色）


class PromptParam(BaseModel):
    """可覆盖参数：带类型与默认值，占位符 {key} 在渲染时替换。"""

    key: str = Field(pattern=r"^[a-z][a-z0-9_]{0,29}$")
    type: Literal["string", "number", "boolean"] = "string"
    default: Any = None
    editable: bool = True
    tip: str | None = None


class ScenePrompt(BaseModel):
    """提示词区块：System Prompt 模板 + 问候语 + 参数。"""

    system: str = Field(min_length=1)
    greeting: str = ""
    params: list[PromptParam] = Field(default_factory=list, max_length=16)

    @property
    def param_map(self) -> dict[str, PromptParam]:
        return {p.key: p for p in self.params}


class SceneObjective(BaseModel):
    """训练目标：label 展示、skill 关联技能图、check 程序化达成判定。"""

    id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,29}$")
    label: str = Field(min_length=1, max_length=60)
    skill: str | None = None
    check: str | None = None  # 白名单表达式


class SceneTools(BaseModel):
    """允许工具白名单 + 工具静态配置（config 键必须 ⊆ allowed）。"""

    allowed: list[str] = Field(default_factory=list)
    config: dict[str, dict[str, Any]] = Field(default_factory=dict)


class SceneStage(BaseModel):
    """阶段：id/name 必填；guidance 软引导；exit_when 声明式推进。"""

    id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,29}$")
    name: str = Field(min_length=1, max_length=60)
    guidance: str | None = None
    exit_when: str | None = None


class SceneFinish(BaseModel):
    """完成条件：when 表达式 + 轮数兜底 + 结束动作。"""

    when: str = Field(min_length=1)
    max_turns: int = Field(default=30, ge=2, le=200)
    on_finish: Literal["request_feedback"] = "request_feedback"


class KnowledgeFile(BaseModel):
    """资料清单条目：path 相对 knowledge/ 目录，visibility 分节可见性。"""

    path: str
    visibility: Literal["user", "ai_only"] = "user"
    sections: list[str] = Field(default_factory=list)


class SceneKnowledge(BaseModel):
    """资料区块：文件清单 + 检索参数。"""

    files: list[KnowledgeFile] = Field(default_factory=list, max_length=20)
    retrieval: dict[str, Any] = Field(default_factory=lambda: {"default_top_k": 4})


class EvalDimension(BaseModel):
    """评估维度：weight 加权；source=state 由程序判定 / llm 由模型评。"""

    id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,29}$")
    label: str
    weight: float = Field(gt=0, le=1)
    source: Literal["state", "llm"] = "llm"
    hints: list[str] = Field(default_factory=list)


class SceneEvaluation(BaseModel):
    """结构化 rubric + 场景评估备注。"""

    dimensions: list[EvalDimension] = Field(default_factory=list, max_length=6)
    notes: str | None = None


class KeywordTip(BaseModel):
    """关键词教学提示：用户话语命中 match 时气泡展示 tip。"""

    match: str
    tip: str


class SceneGuardrails(BaseModel):
    """护栏规则（§5.3）：语言/词数/关键词提示/跑题检测，动作统一为 warn。"""

    language: str | None = None
    min_words: int | None = Field(default=None, ge=1, le=100)
    keyword_tips: list[KeywordTip] = Field(default_factory=list)
    off_topic: dict[str, Any] | None = None  # {domain_keywords: [...], action: warn}
    max_warnings_per_turn: int = Field(default=1, ge=1, le=5)


class SceneAvatar(BaseModel):
    """数字人推荐值（§4.7：可选且无副作用，实际由用户偏好决定）。"""

    preferred: str | None = None
    rate: float | None = Field(default=None, ge=0.5, le=2.0)


class ScenePackage(BaseModel):
    """场景包 v2 完整声明：scene.yaml 的规范化结果。"""

    meta: SceneMeta
    roles: list[SceneRole] = Field(min_length=1, max_length=4)
    prompt: ScenePrompt
    objectives: list[SceneObjective] = Field(default_factory=list, max_length=8)
    state: dict[str, Any] = Field(default_factory=dict)
    tools: SceneTools = Field(default_factory=SceneTools)
    coordination: dict[str, Any] = Field(default_factory=dict)  # {order: [role_id]}
    stages: list[SceneStage] = Field(default_factory=list, max_length=8)
    finish: SceneFinish
    knowledge: SceneKnowledge = Field(default_factory=SceneKnowledge)
    evaluation: SceneEvaluation = Field(default_factory=SceneEvaluation)
    guardrails: SceneGuardrails = Field(default_factory=SceneGuardrails)
    avatar: SceneAvatar = Field(default_factory=SceneAvatar)

    # ---- 跨字段校验 ----
    @model_validator(mode="after")
    def _cross_check(self) -> "ScenePackage":
        errors: list[tuple[str, str]] = []

        # 角色与协调顺序
        role_ids = [r.id for r in self.roles]
        if len(set(role_ids)) != len(role_ids):
            errors.append(("roles", f"角色 id 重复：{role_ids}"))
        order = self.coordination.get("order") or []
        for role_id in order:
            if role_id not in role_ids:
                errors.append(("coordination.order", f"引用了不存在的角色：{role_id}"))

        # 工具白名单：allowed ⊆ 注册表；config 键 ⊆ allowed
        unknown_tools = [t for t in self.tools.allowed if t not in REGISTERED_TOOLS]
        if unknown_tools:
            errors.append(("tools.allowed", f"未注册的工具：{', '.join(unknown_tools)}"))
        for key in self.tools.config:
            if key not in self.tools.allowed:
                errors.append(("tools.config", f"配置键 {key} 不在 allowed 中"))
        allowed_set = set(self.tools.allowed)

        # 声明的 state 根键（表达式 dry-run 与 update_scene_state 边界共用）
        declared = set(self.state.keys())

        # prompt 占位符：{param} 或 {roles.<id>.<field>}
        param_keys = set(self.prompt.param_map.keys())
        role_fields = {"id", "display_name", "title", "personality", "voice", "avatar"}
        for text, label in ((self.prompt.system, "prompt.system"), (self.prompt.greeting, "prompt.greeting")):
            for name in expr.extract_placeholders(text):
                if name in param_keys:
                    continue
                parts = name.split(".")
                if len(parts) == 3 and parts[0] == "roles" and parts[1] in role_ids and parts[2] in role_fields:
                    continue
                errors.append((label, f"占位符 {{{name}}} 无法解析（可用参数或 roles.<id>.<字段>）"))

        # 表达式 dry-run：objectives.check / stages.exit_when / finish.when
        for objective in self.objectives:
            if objective.check is not None:
                try:
                    expr.dry_run(objective.check, declared)
                except expr.ExpressionError as exc:
                    errors.append((f"objectives[{objective.id}].check", str(exc)))
        for index, stage in enumerate(self.stages):
            if stage.exit_when is not None:
                try:
                    expr.dry_run(stage.exit_when, declared)
                except expr.ExpressionError as exc:
                    errors.append((f"stages[{index}].exit_when", str(exc)))
        try:
            expr.dry_run(self.finish.when, declared)
        except expr.ExpressionError as exc:
            errors.append(("finish.when", str(exc)))

        if errors:
            raise SceneValidationError(errors)
        return self

    # ---- 便捷访问 ----
    @property
    def state_keys(self) -> set[str]:
        """包内声明的 state 根键集合。"""
        return set(self.state.keys())
