"""请求级工具注册表：模型不接收用户 ID、场景 ID 或数据库连接。"""
import ast
from dataclasses import dataclass
import json
import operator
import re
from typing import Any, Callable

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, ConfigDict, Field

from app.scenes.schema import ScenePackage


class SearchArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=4, ge=1, le=8)


class UpdateArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(min_length=1, max_length=100)
    value: Any
    evidence: str = Field(min_length=1, max_length=1000, description="Exact quote from the current user input supporting this change")


class ListAppendArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(min_length=1, max_length=100)
    item: str | dict[str, Any]
    evidence: str = Field(min_length=1, max_length=1000, description="Exact quote from the current user input supporting this addition")


class ListRemoveArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(min_length=1, max_length=100)
    match: str = Field(min_length=1, max_length=200, description="Keyword matching the item to remove")
    evidence: str = Field(min_length=1, max_length=1000, description="Exact quote from the current user input supporting this removal")


class AdjustNumberArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(min_length=1, max_length=100)
    delta: int | float
    evidence: str = Field(min_length=1, max_length=1000, description="Exact quote from the current user input supporting this change")


class CalcArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expression: str = Field(min_length=1, max_length=200, description="Arithmetic expression using numbers, + - * /, parentheses, round, min, max")


class LookupWordArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    word: str = Field(min_length=1, max_length=80, description="English word or phrase to look up in scene context")


class HintArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    focus: str = Field(default="", max_length=200, description="Optional topic or goal the learner is stuck on")


class NextStageArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(default="", max_length=200, description="Brief reason for moving to the next interview or conversation stage")


class ReviewTaskArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic: str = Field(min_length=1, max_length=160, description="Key expression, grammar point, or weak area to review later")
    note: str = Field(default="", max_length=300, description="Optional brief feedback or example")


_BIN_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_SAFE_FUNCS = {"round": round, "min": min, "max": max, "abs": abs}


def _safe_eval_expr(expr: str) -> float:
    """使用 AST 白名单安全求值四则运算，禁止任何变量、属性或任意代码执行。"""
    tree = ast.parse(expr.strip(), mode="eval")

    def _eval(node: ast.AST, depth: int = 0) -> float:
        if depth > 12:
            raise ValueError("Expression is too deeply nested")
        if isinstance(node, ast.Expression):
            return _eval(node.body, depth + 1)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return float(node.value)
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
            return _UNARY_OPS[type(node.op)](_eval(node.operand, depth + 1))
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
            right = _eval(node.right, depth + 1)
            if isinstance(node.op, ast.Div) and right == 0:
                raise ValueError("Division by zero")
            return _BIN_OPS[type(node.op)](_eval(node.left, depth + 1), right)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _SAFE_FUNCS and not node.keywords:
            args = [_eval(a, depth + 1) for a in node.args]
            return float(_SAFE_FUNCS[node.func.id](*args))
        raise ValueError("Unsupported operation in expression")

    return round(_eval(tree), 4)


@dataclass
class ToolRegistry:
    package: ScenePackage
    input_text: str
    search: Callable[[str, int], dict]

    def schemas(self) -> list[StructuredTool]:
        """返回本场景同时声明且当前已实现的工具参数定义。

        这里的函数仅向模型发布工具名称、描述和参数结构；真实执行由 execute
        通过服务端注入的 handler 完成，未实现的工具不会暴露给模型。
        """
        specs = {
            "search_knowledge": (SearchArgs, "Search reference materials for the current scene."),
            "update_scene_state": (UpdateArgs, "Record a supported scalar scene fact using an exact quote from the current user input."),
            "append_state_item": (ListAppendArgs, "Append an item to a declared list in scenario_state (e.g., orders, bookings, symptoms, checklist) with exact user quote evidence."),
            "remove_state_item": (ListRemoveArgs, "Remove a matching item from a declared list in scenario_state with exact user quote evidence."),
            "adjust_state_number": (AdjustNumberArgs, "Increment or decrement a declared numeric field in scenario_state with exact user quote evidence."),
            "calculate_expression": (CalcArgs, "Safely evaluate an arithmetic expression for prices, totals, quantities, or conversions."),
            "lookup_word": (LookupWordArgs, "Look up a word or phrase in the scene materials to explain meaning and usage."),
            "get_hint": (HintArgs, "Fetch current scene objectives and speaking tips to give the learner a gentle one-line hint."),
            "next_interview_stage": (NextStageArgs, "Advance the interview or multi-stage conversation to the next stage when the current topic is covered."),
            "add_review_task": (ReviewTaskArgs, "Record a vocabulary item, expression, or feedback point for the learner to review later."),
        }
        return [StructuredTool.from_function(
            func=lambda **kwargs: kwargs, name=name, description=specs[name][1], args_schema=specs[name][0],
        ) for name in self.package.tools.allowed if name in specs]

    def execute(self, name: str, args: dict, scenario_state: dict) -> dict:
        """校验并执行一个工具，返回可供模型理解的结构化结果。

        检索范围由当前场景闭包确定；状态更新仅允许声明字段及本轮原文证据。
        状态字典属于本轮临时副本，只有整轮成功后才会由会话服务提交。
        """
        names = {t.name for t in self.schemas()}
        if name not in names:
            raise ValueError("Tool is unavailable in this scene")
        if name == "search_knowledge":
            parsed = SearchArgs.model_validate(args)
            return self.search(parsed.query, parsed.top_k)
        if name == "calculate_expression":
            parsed = CalcArgs.model_validate(args)
            return {"expression": parsed.expression, "result": _safe_eval_expr(parsed.expression)}
        if name == "lookup_word":
            parsed = LookupWordArgs.model_validate(args)
            matches = self.search(parsed.word, 2)
            return {"word": parsed.word, "scene_matches": matches}
        if name == "get_hint":
            parsed = HintArgs.model_validate(args)
            tips = [t.tip for t in self.package.guardrails.keyword_tips][:3]
            goals = [o.label for o in self.package.objectives][:4]
            return {"focus": parsed.focus, "objectives": goals, "tips": tips}
        if name == "next_interview_stage":
            parsed = NextStageArgs.model_validate(args)
            scenario_state["_advance_stage_request"] = True
            return {"advance_requested": True, "reason": parsed.reason}
        if name == "add_review_task":
            parsed = ReviewTaskArgs.model_validate(args)
            tasks = list(scenario_state.get("review_tasks") or [])
            if len(tasks) < 20:
                tasks.append({"topic": parsed.topic, "note": parsed.note})
            scenario_state["review_tasks"] = tasks
            return {"added": True, "topic": parsed.topic, "note": parsed.note, "count": len(tasks)}
        if name == "append_state_item":
            parsed = ListAppendArgs.model_validate(args)
            self._require_declared_and_evidence(parsed.key, parsed.evidence)
            if not isinstance(self.package.state[parsed.key], list):
                raise ValueError("Target state key is not a list")
            lst = list(scenario_state.get(parsed.key) or [])
            if len(lst) >= 50:
                raise ValueError("State list capacity limit reached")
            lst.append(parsed.item)
            scenario_state[parsed.key] = lst
            return {"appended": parsed.key, "item": parsed.item, "items": lst, "evidence": parsed.evidence}
        if name == "remove_state_item":
            parsed = ListRemoveArgs.model_validate(args)
            self._require_declared_and_evidence(parsed.key, parsed.evidence)
            if not isinstance(self.package.state[parsed.key], list):
                raise ValueError("Target state key is not a list")
            lst = list(scenario_state.get(parsed.key) or [])
            needle = parsed.match.lower()
            removed = None
            kept = []
            for entry in lst:
                hay = entry if isinstance(entry, str) else json.dumps(entry, ensure_ascii=False)
                if removed is None and needle in hay.lower():
                    removed = entry
                    continue
                kept.append(entry)
            scenario_state[parsed.key] = kept
            return {"removed": parsed.key, "removed_item": removed, "items": kept, "evidence": parsed.evidence}
        if name == "adjust_state_number":
            parsed = AdjustNumberArgs.model_validate(args)
            self._require_declared_and_evidence(parsed.key, parsed.evidence)
            expected = self.package.state[parsed.key]
            if isinstance(expected, bool) or not isinstance(expected, (int, float)):
                raise ValueError("Target state key is not numeric")
            cur = scenario_state.get(parsed.key, expected)
            new_val = round(cur + parsed.delta, 2)
            if isinstance(expected, int):
                new_val = int(round(new_val))
            scenario_state[parsed.key] = new_val
            return {"adjusted": parsed.key, "value": new_val, "delta": parsed.delta, "evidence": parsed.evidence}
        parsed = UpdateArgs.model_validate(args)
        self._require_declared_and_evidence(parsed.key, parsed.evidence)
        expected = self.package.state[parsed.key]
        if isinstance(parsed.value, (dict, list)) or (expected is not None and type(parsed.value) is not type(expected)):
            raise ValueError("Only scalar values matching the declared type are supported")
        scenario_state[parsed.key] = parsed.value
        return {"updated": parsed.key, "value": parsed.value, "evidence": parsed.evidence}

    @staticmethod
    def _norm_quote(text: str) -> str:
        """归一化空白和大小写，并消除常见标点差异以便宽松匹配证据引用。"""
        cleaned = re.sub(r"[\s\.,!?;:\"'`~()\[\]{}\-_/]+", " ", (text or "").lower())
        return cleaned.strip()

    def _require_declared_and_evidence(self, key: str, evidence: str) -> None:
        if key not in self.package.state:
            raise ValueError("State key was not declared by the scene")
        ev = (evidence or "").strip()
        if not ev:
            raise ValueError("Evidence must be non-empty")
        if ev in self.input_text:
            return
        norm_ev = self._norm_quote(ev)
        norm_in = self._norm_quote(self.input_text)
        if not norm_ev or norm_ev not in norm_in:
            raise ValueError("Evidence must reference content from this user turn")
