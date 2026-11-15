# EchoTalk 2.0 系统与对话 Agent 架构说明

EchoTalk 2.0 采用 **1v1 语音对话（`Practice`）+ 1vN 多角色对话（`Debate / Panel`）** 双轨架构，结合场景知识库检索（Vector + FTS5 + RRF）、流式句子级 TTS 播报、听力工作室、SM-2 间隔重复复习计划以及后台管理端，形成完整的英语口语与听力训练闭环。

---

## 一、1v1 与 1vN 双轨对话架构

### 1. 1v1 语音对话（`Practice`）
专注单角色沉浸式任务流（日常情景、任务达成、1v1 模拟面试），基于 LangChain + LangGraph `StateGraph` 构建：

```text
POST /api/sessions/{id}/turns[/stream]
  → 身份与会话归属校验、request_id 幂等去重
  → 读取场景快照、任务状态、最近 8 轮对话，释放读取事务
  → LangGraph：agent → tools → agent … → finalize（每轮最多 4 次模型调用、6 次工具执行）
  → 流式输出（/turns/stream）：边生成英文回复边通过 _SentenceBuffer 切句合成 edge-tts，推送 text / audio / done SSE 事件
  → 乐观版本检查，原子提交轮次、状态、目标达成进度与内部轨迹（trace_json）
```

**核心模块职责：**

| 模块 | 职责 |
|---|---|
| `app/agents/conversation.py` | LangGraph 图结构、工具循环、调用预算与模型异常处理 |
| `app/agents/state.py` | 单轮图状态契约 |
| `app/agents/context.py` | 场景模板、运行状态、目标提示与近期对话上下文拼接 |
| `app/agents/model_gateway.py` | 对话模型配置与 `ChatOpenAI` 适配（支持 `ECHOTALK_CHAT_*` 配置） |
| `app/agents/tools.py` | `ToolRegistry`：场景白名单与已实现工具交集、归一化原文证据校验 |
| `app/services/scene_runtime.py` | 场景初值、目标完成判定、声明式阶段推进与结束判定 |
| `app/services/session/` | 会话 CRUD、流式轮次编排（`turn.py`）、复盘报告（`report.py`）、TTS 缓存 |
| `app/api/endpoints/sessions.py` | 会话创建、恢复、同步/流式轮次提交与复盘报告接口 |

### 2. 1vN 多角色对话（`Debate / Panel`）
专注多角色协同与交锋，统一支持两种子模式：
- **`debate`（正反辩论对抗）**：用户选择 `pro / con` 立场与交锋风格，主持人控场、对手辩手反驳、评委打分并维护四维战况雷达与胜率变化。
- **`panel`（多人圆桌 / 群面委员会）**：无需选择正反方，由 2–4 个独立 AI 角色（如技术总监、HRBP、财务/产品负责人）按议程阶段轮流追问、补充与合议评估。

内置多角色场景存放于 `backend/app/content/debates/*.yaml`，封面位于 `backend/app/content/debates/covers/`，服务启动时自动同步至 `debate_topics` 表，并与用户自建场景共用 `/api/debate/*` 接口及历史/复习/成长分析闭环。

---

## 二、工具注册表（Tool Registry）

### 1. 1v1 场景包白名单（`app/scenes/schema.py` & `app/agents/tools.py`）
场景包在 `tools.allowed` 中声明允许使用的工具，运行时 `ToolRegistry.schemas()` 仅暴露同时已实现且在白名单内的工具：

| 工具名 | 用途说明 |
|---|---|
| `search_knowledge` | 检索当前场景及关联资料库片段（混合检索 + RRF 重排） |
| `update_scene_state` | 使用本轮用户原话证据更新标量状态字段 |
| `append_state_item` | 向声明的列表状态追加条目（如订单、症状、清单） |
| `remove_state_item` | 从声明的列表状态移除匹配条目 |
| `adjust_state_number` | 对声明的数值状态字段执行加减运算 |
| `calculate_expression` | 安全计算算术表达式（价格、总计、数量换算） |
| `lookup_word` | 检索场景资料中的词句释义与用法 |
| `get_hint` | 获取当前场景目标与关键词提示 |
| `next_interview_stage` | 请求推进面试或分阶段对话至下一阶段 |
| `add_review_task` | 将重点表达或纠错点加入后续复习任务 |

> `schema.py` 的 `REGISTERED_TOOLS` 同时兼容预留声明（如 `get_learning_profile`、`calculate_order`、`modify_order`、`record_feedback`），未在 `ToolRegistry` 中实现的工具不会绑定给模型。

### 2. 多角色工具开关（`tools_config`）
多角色场景在 `tools` / `tools_config` 中配置可用能力：`search_knowledge`、`rebuttal_hint`、`judge_score`、`fact_check`、`calculate_expression`、`add_review_task`，由 `debate_service.py` 与前端 `Debate.vue` 按配置启停。

---

## 三、扩展功能模块

| 模块 | 后端入口与服务 | 核心能力 |
|---|---|---|
| **听力工作室** | `app/api/endpoints/listening.py`<br>`app/services/listening_service.py` | 精听 / 盲听 / 听写单元、音频合成缓存、答题批改与学习 XP 累计 |
| **SM-2 复习计划** | `app/api/endpoints/review.py`<br>`app/services/review_service.py` | 基于 SM-2 间隔重复算法安排今日待复习卡片，支持 1v1 / 多角色 / 手动建卡 |
| **成长分析与历史** | `app/services/analytics_service.py`<br>`app/services/session/crud.py` | 聚合 1v1、多角色对话与听力训练数据，输出趋势与复盘回看入口 |
| **后台管理端** | `app/api/endpoints/admin.py`<br>`app/services/admin/` + `admin/` 前端 | 独立的管理端界面与 API（`/api/admin/*`），支持用户、场景包与内容治理 |

---

## 四、配置、迁移与测试

### 1. 环境变量与启动
在 `backend/.env` 中配置数据库连接及对话模型（`ECHOTALK_CHAT_API_KEY`、`ECHOTALK_CHAT_MODEL`、`ECHOTALK_CHAT_API_BASE`）。表结构补齐与幂等列迁移统一收敛在 `app/core/migrations.py`，由 FastAPI `lifespan` 启动流程调用：

```bash
cd backend
python init_db.py
python main.py
```

### 2. 自动化测试
```bash
cd backend
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
```

测试使用临时内存 SQLite 与注入的伪模型/检索函数，不连接外部 MySQL，也不消耗真实模型额度。
