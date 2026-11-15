---
name: echotalk-frontend-ui
description: EchoTalk 2.0 前端 UI 设计规范与组件复用指南。在新增或重构 frontend/src/views/ 页面、卡片、按钮、弹窗、对话/辩论工作台或接入语音输入时使用，确保页面留白、触感紫白风格、遮罩与组件复用全站一致。
---

# EchoTalk 2.0 前端 UI 开发规范

在修改或新建 `frontend/` 页面时，严格遵循以下步骤与令牌规范，避免出现贴边、风格割裂、双层边框或重复造轮子。

## 1. 页面骨架与留白（必检）

`AppShell` 主工作区不自带内边距，**每个一级视图根节点必须自带标准四周留白**：

```css
.xxx-page {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 22px 28px 28px;
  overflow-y: auto;
}
```

- **列表大厅型（如 `Scenes.vue`、`ListeningStudio.vue`、`Debate.vue` Hub）**：内层容器用 `width: 100%; max-width: 1320px; margin: 0 auto; display: flex; flex-direction: column; gap: 18px;`。
- **对话/辩论工作台型（如 `Practice.vue`、`Debate.vue` Arena）**：外层 `flex: 1; min-height: 520px; display: flex; flex-direction: column; gap: 14px;`，消息记录流用 `flex: 1; min-height: 0; overflow-y: auto;` 自动撑满视口剩余高度，底部紧贴输入栏，不在底部留大片空白。

## 2. 视觉令牌（触感紫白风）

| 用途 | 规范值 |
| :--- | :--- |
| 主品牌紫 / 按压底边 | `#8b73dd` / `#6951b8`（浅紫底 `#f4f0ff` / `#eee9ff`，深紫字 `#6046b4`） |
| 标题正文 / 次级 / 弱字 | `#35304e` / `#625e76` / `#837f96` |
| 标准触感卡片 | `border: 1.5px solid #ebe7f5; border-bottom: 4px solid #e3dcf2; border-radius: 18px; background: #ffffff;` |
| 卡片内分组块 | `border: 1px solid #efecf7; border-radius: 11px; background: #faf9fd;` |
| 主按钮 | `border: 1.5px solid #8067d1; border-bottom: 3px solid #6951b8; border-radius: 10px; background: #8b73dd; color: #ffffff; font-weight: 700;` |
| 次级描边按钮 | `border: 1.5px solid #e6e1f2; border-bottom: 3px solid #ddd6ec; border-radius: 10px; background: #ffffff; color: #5a5572; font-weight: 600;` |
| 辅助点缀色 | 薄荷绿（完成/正方/XP）：`#eaf7f0` 底 + `#2a8c5f` 字；暖橙/珊瑚（挑战/反方）：`#fff3ea` / `#fdece8` 底 + `#c46a24` / `#b84a39` 字 |

## 3. 统一弹窗遮罩

所有全屏遮罩（`modal-backdrop` / `*-scrim`）必须复用 `frontend/src/assets/styles.css` 变量：

```css
background: var(--scrim-bg, rgba(34, 37, 59, .28));
-webkit-backdrop-filter: var(--scrim-blur, blur(2px));
backdrop-filter: var(--scrim-blur, blur(2px));
```

弹窗主体使用 `border: 1.5px solid #ebe7f5; border-bottom: 5px solid #e3dcf2; border-radius: 20px; background: #ffffff;`。

## 4. 必复用组件与接口约定

1. **Tab 筛选栏**：使用 `AppTabs`（`frontend/src/components/AppTabs.vue`）。
2. **图标**：统一使用 `AppIcon`（`frontend/src/components/AppIcon.vue`），先确认 `icons` 表中存在该图标名再使用。
3. **语音 + 文字输入栏**：
   - 直接复用 `PracticeComposer` + `useVoiceInput`，**禁止在 `PracticeComposer` 外层再套一层 `border` 容器**（其内部 `.composer` 自带边框，外包会产生双层边框）。
   - 查询语音识别可用性时，读取 `getSpeechStatus()` 的 **`data?.configured`**（不要写错成 `asr_available`）。
4. **对话/辩论消息流**：采用「头像 + 角色元信息行 + 圆角气泡」结构，AI 居左、用户居右，保持清晰对话感而非整行日志框堆叠。

## 5. 交付前自检清单

- [ ] 一级页面根节点包含 `padding: 22px 28px 28px`，四周留白与 `Scenes.vue` 一致。
- [ ] 卡片、主按钮、次级按钮均采用 `#ebe7f5` / `#8b73dd` 触感底边规范，无割裂的平底灰框或高饱和蓝块。
- [ ] 所有弹窗遮罩使用 `--scrim-bg` 与 `--scrim-blur`。
- [ ] 运行 `npm --prefix /Users/mac/Files/EchoTalk/frontend run build -- --mode development` 通过。
