"""场景包条件表达式子语言（设计稿场景包方案 §4.6）。

文法（白名单，禁止属性访问、任意调用与算术）：

    表达式   := 或表达式
    或表达式 := 与表达式 ('or' 与表达式)*
    与表达式 := 非表达式 ('and' 非表达式)*
    非表达式 := 'not' 非表达式 | 比较
    比较     := 操作数 (运算符 操作数)?
    操作数   := 字面量 | 引用 | 函数
    引用     := state.<路径> | stage | stage_turns | turn_count
    函数     := tool_called('名') | state_changed('路径') | goals_done()

提供两个入口：
- ``parse(expr)``     → 解析并返回 AST（校验期用，含状态路径检查）
- ``evaluate(expr, ctx)`` → 运行时求值（每轮工具执行后调用）
"""
import ast
import re
from dataclasses import dataclass, field
from typing import Any

# 运行时保留键：由图写入，包内 state 不可声明，但表达式可引用
RESERVED_REFS = {"stage", "stage_turns", "turn_count"}

# YAML 风格小写字面量（DSL 采用 true/false/null，而非 Python 的 True/False/None）
_LITERAL_NAMES = {"true": True, "false": False, "null": None}

# 表达式内可调用的函数名 → 参数个数
EXPR_FUNCS = {
    "tool_called": 1,      # 本轮是否调用过某工具
    "state_changed": 1,    # 本轮某 state 路径是否发生变化
    "goals_done": 0,       # 全部目标是否达成
}

_CMP_OPS = {
    ast.Eq: "==", ast.NotEq: "!=", ast.GtE: ">=", ast.LtE: "<=",
    ast.Gt: ">", ast.Lt: "<", ast.In: "in",
}


class ExpressionError(ValueError):
    """表达式非法：携带可解释原因（用于 422 SCENE_INVALID_EXPRESSION）。"""


@dataclass
class ParsedExpression:
    """解析结果：AST 根节点 + 表达式中引用的全部 state 根键。"""

    tree: ast.expr
    state_roots: set[str] = field(default_factory=set)  # state.<root> 的根键集合


# ---- 解析：ast 解析 + 节点白名单校验 ---------------------------------------

def parse(expr: str) -> ParsedExpression:
    """解析表达式；任何越界语法都抛 ExpressionError（附原因）。"""
    if not isinstance(expr, str) or not expr.strip():
        raise ExpressionError("表达式不能为空")
    try:
        tree = ast.parse(expr.strip(), mode="eval")
    except SyntaxError as exc:
        raise ExpressionError(f"表达式语法错误：{exc.msg}（位置 {exc.offset}）") from exc

    state_roots: set[str] = set()
    _validate_node(tree.body, state_roots)
    return ParsedExpression(tree=tree.body, state_roots=state_roots)


def _validate_node(node: ast.expr, state_roots: set[str]) -> None:
    """递归校验 AST 节点类型，只放行白名单内的语法结构。"""
    if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
        for value in node.values:
            _validate_node(value, state_roots)
        return
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        _validate_node(node.operand, state_roots)
        return
    if isinstance(node, ast.Compare):
        if len(node.ops) != len(node.comparators):
            raise ExpressionError("不支持链式比较")
        for op in node.ops:
            if type(op) not in _CMP_OPS:
                raise ExpressionError(f"不支持的比较运算符：{type(op).__name__}")
        _validate_node(node.left, state_roots)
        for comp in node.comparators:
            _validate_node(comp, state_roots)
        return
    if isinstance(node, ast.Name):
        if node.id in _LITERAL_NAMES:
            return
        if node.id not in RESERVED_REFS:
            raise ExpressionError(f"未知的引用：{node.id}（可用：{', '.join(sorted(RESERVED_REFS))}）")
        return
    if isinstance(node, ast.Attribute):
        # 仅允许 state.<路径> 形式（属性链的根必须是 state）
        _validate_state_ref(node, state_roots)
        return
    if isinstance(node, ast.Subscript):
        # state.list[0] 形式：下标只允许整数或字符串字面量
        _validate_state_ref(node, state_roots)
        return
    if isinstance(node, ast.Constant) and isinstance(node.value, (bool, int, float, str, type(None))):
        return
    if isinstance(node, ast.Call):
        _validate_call(node, state_roots)
        return
    if isinstance(node, ast.List):  # 'x' in state.tags 之类的右值列表不必要，但 in 比较左侧可为列表
        for item in node.elts:
            _validate_node(item, state_roots)
        return
    raise ExpressionError(f"表达式含有不被允许的语法：{type(node).__name__}")


def _validate_state_ref(node: ast.expr, state_roots: set[str]) -> None:
    """校验 state.<路径>（含 . 与 [n] 混合），记录根键供 dry-run 检查。"""
    # 自底向上拆属性/下标链
    parts: list[str] = []
    current = node
    while True:
        if isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        elif isinstance(current, ast.Subscript):
            index = current.slice
            if isinstance(index, ast.Constant) and isinstance(index.value, (int, str)):
                parts.append(str(index.value))
            else:
                raise ExpressionError("下标只允许整数字面量或字符串字面量")
            current = current.value
        else:
            break
    if not (isinstance(current, ast.Name) and current.id == "state") or not parts:
        raise ExpressionError("只允许引用 state.<路径>（根必须是 state）")
    parts.reverse()
    state_roots.add(parts[0])


def _validate_call(node: ast.Call, state_roots: set[str]) -> None:
    """校验白名单函数调用：参数必须是字符串字面量。"""
    if not isinstance(node.func, ast.Name) or node.func.id not in EXPR_FUNCS:
        raise ExpressionError("只允许调用 tool_called / state_changed / goals_done")
    if node.keywords:
        raise ExpressionError("函数调用不允许关键字参数")
    expected = EXPR_FUNCS[node.func.id]
    if len(node.args) != expected:
        raise ExpressionError(f"{node.func.id} 需要 {expected} 个参数")
    for arg in node.args:
        if not (isinstance(arg, ast.Constant) and isinstance(arg.value, str)):
            raise ExpressionError(f"{node.func.id} 的参数必须是字符串字面量")
        if node.func.id == "state_changed":
            root = arg.value.split(".")[0].split("[")[0]
            state_roots.add(root)


# ---- dry-run：声明检查（state 路径必须包内声明） ----------------------------

def dry_run(expr: str, declared_state_keys: set[str]) -> ParsedExpression:
    """解析并检查表达式中引用的 state 根键都在包内声明（校验期调用）。"""
    parsed = parse(expr)
    unknown = parsed.state_roots - declared_state_keys - RESERVED_REFS
    if unknown:
        raise ExpressionError(
            f"表达式引用了未在 state 中声明的键：{', '.join(sorted(unknown))}"
        )
    return parsed


# ---- 运行时求值 ------------------------------------------------------------

_MISSING = object()  # 路径缺失标记：参与比较时按 None 处理但可区分


def _resolve_state(root: dict, path_parts: list[str | int]) -> Any:
    """沿 . 与 [n] 路径取值；缺失返回 _MISSING。"""
    current: Any = root
    for part in path_parts:
        if isinstance(current, dict) and isinstance(part, str):
            if part not in current:
                return _MISSING
            current = current[part]
        elif isinstance(current, list) and isinstance(part, int):
            if part < 0 or part >= len(current):
                return _MISSING
            current = current[part]
        else:
            return _MISSING
    return current


def _path_to_parts(node: ast.expr) -> list[str | int] | None:
    """把 state 属性/下标链还原为路径片段；非 state 引用返回 None。"""
    parts: list[str | int] = []
    current = node
    while True:
        if isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        elif isinstance(current, ast.Subscript):
            value = current.slice.value  # 校验期已确保是字面量
            parts.append(value)
            current = current.value
        else:
            break
    parts.reverse()
    if isinstance(current, ast.Name) and current.id == "state" and parts:
        return parts
    return None


def _eval_node(node: ast.expr, ctx: dict) -> Any:
    """按白名单语义求值。ctx 提供运行时上下文。"""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BoolOp):
        values = [_eval_node(v, ctx) for v in node.values]
        result = all(values) if isinstance(node.op, ast.And) else any(values)
        return bool(result)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not _truthy(_eval_node(node.operand, ctx))
    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, ctx)
        right = _eval_node(node.comparators[0], ctx)
        op = node.ops[0]
        left, right = _normalize(left), _normalize(right)
        try:
            if isinstance(op, ast.Eq):
                return left == right
            if isinstance(op, ast.NotEq):
                return left != right
            if isinstance(op, ast.In):
                return left in right if right is not None else False
            if left is None or right is None:
                return False  # 与 None 的有序比较视为不成立
            if isinstance(op, ast.GtE):
                return left >= right
            if isinstance(op, ast.LtE):
                return left <= right
            if isinstance(op, ast.Gt):
                return left > right
            if isinstance(op, ast.Lt):
                return left < right
        except TypeError:
            return False  # 类型不可比（如字符串与数字）：按条件未满足处理
        return False
    if isinstance(node, ast.Name):
        if node.id in _LITERAL_NAMES:
            return _LITERAL_NAMES[node.id]
        return ctx.get(node.id)  # stage / stage_turns / turn_count
    if isinstance(node, ast.Attribute) or isinstance(node, ast.Subscript):
        parts = _path_to_parts(node)
        if parts is None:
            raise ExpressionError("表达式含有不被允许的引用")
        value = _resolve_state(ctx.get("state") or {}, parts)
        return None if value is _MISSING else value
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        name = node.func.id
        if name == "tool_called":
            return node.args[0].value in (ctx.get("tools_called_this_turn") or ())
        if name == "state_changed":
            return node.args[0].value in (ctx.get("state_changed_keys") or ())
        if name == "goals_done":
            goals = ctx.get("goals") or []
            return bool(goals) and all(bool(g.get("done")) for g in goals)
    if isinstance(node, ast.List):
        return [_eval_node(item, ctx) for item in node.elts]
    raise ExpressionError(f"表达式含有不被允许的语法：{type(node).__name__}")


def _truthy(value: Any) -> bool:
    return bool(_normalize(value))


def _normalize(value: Any) -> Any:
    """_MISSING 视为 None，便于 'state.x != null' 这类判断。"""
    return None if value is _MISSING else value


def evaluate(expr: str | ast.expr, ctx: dict) -> bool:
    """运行时求值：expr 可为字符串或已解析的 AST；返回布尔结果。"""
    tree = parse(expr).tree if isinstance(expr, str) else expr
    return _truthy(_eval_node(tree, ctx))


# ---- 提示词/状态初值中 {param} 占位符校验 ----------------------------------

_PARAM_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_.]*)\}")


def extract_placeholders(text: str) -> set[str]:
    """提取 {xxx} 占位符名（供 prompt 模板渲染校验）。"""
    return set(_PARAM_RE.findall(text or ""))
