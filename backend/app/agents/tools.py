"""请求级工具注册表：模型不接收用户 ID、场景 ID 或数据库连接。"""
from dataclasses import dataclass
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
        parsed = UpdateArgs.model_validate(args)
        if parsed.key not in self.package.state:
            raise ValueError("State key was not declared by the scene")
        if parsed.evidence not in self.input_text:
            raise ValueError("Evidence must be an exact quote from this user turn")
        expected = self.package.state[parsed.key]
        if isinstance(parsed.value, (dict, list)) or (expected is not None and type(parsed.value) is not type(expected)):
            raise ValueError("Only scalar values matching the declared type are supported")
        scenario_state[parsed.key] = parsed.value
        return {"updated": parsed.key, "value": parsed.value, "evidence": parsed.evidence}
