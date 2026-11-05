# EchoTalk 2.0 对话 Agent 框架

当前交付包含后端对话框架与前端练习页：使用 LangChain 消息/工具/模型适配与 LangGraph StateGraph，复用现有 FastAPI、SQLAlchemy 和 ScenePackage。前端支持文字输入、录音后 ASR 转写、确认发送与 TTS 回放，语音配置见 [录音与转写接入](speech-input.md)。

## 执行结构

```text
POST /api/sessions/{id}/turns
  → 身份与会话归属校验、request_id 去重
  → 读取场景快照、任务状态、最近 8 轮对话
  → 释放读取事务
  → LangGraph：agent → tools → agent … → finalize
  → 乐观版本检查，原子提交轮次、状态和内部轨迹
  → 返回公开回复与任务状态
```

每个 HTTP 请求运行一轮图。模型选择工具和交流内容；程序校验工具、修改业务状态、计算目标/阶段和完成条件。图结束不等于会话结束。ASR 和 TTS 后续在图前后接入。

## 文件职责

| 文件 | 职责 |
|---|---|
| `app/agents/conversation.py` | 图结构、工具循环、调用预算和模型错误处理 |
| `app/agents/state.py` | 单轮图状态契约 |
| `app/agents/context.py` | 场景模板、运行状态与近期消息上下文 |
| `app/agents/model_gateway.py` | 对话模型配置与 LangChain ChatOpenAI 适配 |
| `app/agents/tools.py` | 场景白名单与当前已实现工具的交集、参数和证据校验 |
| `app/services/scene_runtime.py` | 场景初值、累计目标、声明式阶段推进、结束判定 |
| `app/services/session_service.py` | 会话快照、历史、幂等、版本控制与持久化 |
| `app/api/endpoints/sessions.py` | 登录后的文字练习接口 |

当前注册了 `search_knowledge` 与 `update_scene_state`：

- 检索仅作用于会话场景，服务端注入范围，并重新校验资料访问权限；个人资料尚未接入。
- 状态更新仅支持包内声明的标量根键，类型须与非空初值一致，且必须引用本轮用户原话。证据引用只验证来源，不保证模型的语义判断正确。
- 未实现的工具不会绑定给模型，并在运行提示词中列为不可用。咖啡厅计价/改单、面试阶段切换、Coach、复习工具仍需实现，不应把当前框架当成这些业务已完成。
- `exit_when` 由程序推进一个阶段；缺省没有推进规则时保持当前阶段。无 `check` 的目标保留未判定，待课后评价接入。
- 每轮最多 4 次模型调用、6 次工具执行。最后一次模型调用不绑定工具，若仍返回工具调用则整轮失败。

## 配置与启动

在 `backend/.env` 增加以下字段；它们与 LightRAG 的模型配置相互独立：

```dotenv
ECHOTALK_CHAT_API_KEY=你的服务端密钥
ECHOTALK_CHAT_MODEL=你的模型名称
ECHOTALK_CHAT_API_BASE=https://api.openai.com/v1
```

模型端点须支持标准 Chat Completions 与 Tool Calling。此适配器不处理供应商特有的推理字段；如需此类功能，在 `model_gateway.py` 换用对应的 LangChain 集成。没有配置时可以创建/读取会话，提交轮次返回 `503 CHAT_NOT_CONFIGURED`，不回退假回复。

```powershell
cd backend
uv sync --locked
uv run --locked python init_db.py
uv run --locked python main.py
```

`init_db.py` 创建新增的 `practice_sessions`、`practice_turns` 表。API 不自动执行建表。此次框架搭建未对开发 MySQL 执行 DDL。

## 接口试用

启动后可通过 `http://127.0.0.1:8000/docs` 登录授权并调用接口，Bearer token 沿用现有账户 API。

1. `POST /api/sessions`，建议先用会议场景验证状态工具：

```json
{"scene_id": "launch_alignment"}
```

返回 `id`、渲染后的 `greeting`、初始 `state` 与 `version`。不暴露场景系统提示词或完整快照。

2. `POST /api/sessions/{id}/turns`：

```json
{
  "request_id": "turn_001",
  "text": "The frontend is delayed because the payment API is not ready."
}
```

返回 `turn_id`、输入、AI 文本、任务状态与新版本号。同一输入使用同一 `request_id` 重试会返回已提交结果；同 ID 换输入返回 409。客户端重试失败轮次时也应沿用原 ID。

3. `GET /api/sessions/{id}`：恢复最后成功提交的状态和按序轮次。结束会话只能读取/重试已完成轮次，新轮次返回 409。

会话接口要求登录。独立的 `/api/speech/transcriptions` 提供录音上传与转写，文字经用户确认后仍通过轮次接口提交。当前没有 SSE、手动结束、会话列表或报告接口。

## 状态与失败边界

- 业务状态与场景快照保存在 MySQL；未配置 LangGraph checkpoint。重启后可恢复到最后提交的轮次，不能恢复到失败轮次的中间节点。
- 场景包被冻结，知识资料仍读取当前场景的资料，尚未冻结资料版本。场景删除或权限撤销后检索失败，历史会话仍可查看。
- 近期聊天仅载入最近 8 轮和开场白；结构化任务状态完整保留。尚未实现旧对话摘要或长期学习记忆。
- 网络调用不持有读取事务。工具先修改本轮私有状态，最后用版本比较更新会话。并发请求可能重复花费模型调用，但至多一个版本提交成功，其他返回 409。
- 模型失败不提交本轮状态。检索失败/参数错误作为工具结果返回模型，可澄清或给出受限回复。
- 工具结果与参数保存在 `trace_json`，不通过公开接口下发，避免直接泄露 `ai_only` 片段。模型收到不引用隐藏资料的指令；这不构成对自然语言泄漏的严格保证。
- 当前工具仅检索或修改内存状态。增加支付、发消息等外部副作用之前，必须增加持久化操作幂等/事务消息；不能直接沿用内存回滚假设。

## 后续扩展

1. 在 `agents/tools.py` 中为业务工具增加参数模型与 handler，并加入可绑定 schema；场景包白名单继续限制可用工具。
2. 实现结构化菜单、计价、改单、确认和模拟支付；业务约束应放工具服务中。
3. 实现 `next_interview_stage` 的合法迁移校验，再接面试场景。
4. 在现有录音转写、TTS 回放与练习前端之上增加 SSE 事件和更自然的语音交互。
5. 会话结束触发独立 Learning 工作流，生成带原话证据的评价，不占实时对话关键路径。

## 离线验证

```powershell
cd backend
uv run --locked python -m unittest discover -s tests -p 'test_*.py' -v
```

测试注入脚本模型和检索函数，使用临时内存 SQLite，不连接开发 MySQL，也不消耗真实模型额度。覆盖幂等、权限、快照、工具失败、状态恢复、并发版本冲突与预算。真实供应商的 Tool Calling 兼容性需配置后另行联调。
