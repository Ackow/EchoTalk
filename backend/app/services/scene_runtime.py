"""由程序计算目标、阶段与结束条件，不接受模型直接覆盖运行时字段。"""
from copy import deepcopy

from app.core.expr import evaluate
from app.scenes.schema import ScenePackage


def initial_state(package: ScenePackage) -> dict:
    """从场景包生成一份相互独立的会话运行状态初值。"""
    return {
        "scenario_state": deepcopy(package.state),
        "stage": package.stages[0].id if package.stages else None,
        "stage_turns": 0,
        "turn_count": 0,
        "goals": [{"id": g.id, "label": g.label, "done": False} for g in package.objectives],
        "status": "active",
        "finish_reason": None,
    }


def advance(package: ScenePackage, state: dict, before: dict) -> dict:
    """根据场景表达式计算累计目标、阶段推进和结束条件。

    返回需要合并到会话状态的字段，不直接修改传入状态。目标一旦达成便保持
    达成；before 用于判断本轮哪些场景状态键实际发生了变化。
    """
    goals = deepcopy(state["goals"])
    context = {
        "state": state["scenario_state"],
        "stage": state["stage"],
        "stage_turns": state["stage_turns"],
        "turn_count": state["turn_count"],
        "tools_called_this_turn": [t["name"] for t in state["tool_results"] if t["ok"]],
        "state_changed_keys": [k for k, v in state["scenario_state"].items() if before.get(k) != v],
        "goals": goals,
    }
    for goal in goals:
        spec = next(g for g in package.objectives if g.id == goal["id"])
        if spec.check and evaluate(spec.check, context):
            goal["done"] = True
    stage_id, stage_turns = state["stage"], state["stage_turns"]
    for index, stage in enumerate(package.stages[:-1]):
        if stage.id == stage_id and stage.exit_when and evaluate(stage.exit_when, context):
            stage_id, stage_turns = package.stages[index + 1].id, 0
            break
    context.update(stage=stage_id, stage_turns=stage_turns)
    reason = state["finish_reason"]
    if evaluate(package.finish.when, context):
        reason = "condition_met"
    elif state["turn_count"] >= package.finish.max_turns:
        reason = "max_turns"
    return {
        "goals": goals, "stage": stage_id, "stage_turns": stage_turns,
        "status": "finished" if reason else "active", "finish_reason": reason,
    }
