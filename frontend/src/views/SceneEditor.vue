<template>
  <!-- 场景创建/编辑向导：分步表单产出场景包字段，保存前经后端全量校验 -->
  <section class="editor-page">
    <!-- 页头：返回 + 居中步骤条（标题由壳层顶栏提供，主操作按钮固定在底部） -->
    <header class="editor-topbar">
      <button class="back-button" type="button" @click="goBack">
        <AppIcon name="chevron-left" :size="15" />返回
      </button>
      <ol class="steps" aria-label="创建步骤">
        <li v-for="(step, index) in STEPS" :key="step.key">
          <button
            type="button"
            class="step-item"
            :class="{ active: stepIndex === index, done: stepIndex > index }"
            :aria-current="stepIndex === index ? 'step' : undefined"
            @click="goStep(index)"
          >
            <span class="step-dot">{{ stepIndex > index ? '✓' : index + 1 }}</span>
            {{ step.label }}
          </button>
        </li>
      </ol>
      <span class="topbar-balance" aria-hidden="true"></span>
    </header>

    <!-- 错误区：校验失败的字段级错误列表 -->
    <transition name="expand">
      <div v-if="errors.length" class="error-panel" role="alert">
        <p class="error-title"><AppIcon name="x" :size="13" />{{ saveError || '请修正以下问题后再保存' }}</p>
        <ul>
          <li v-for="(item, index) in errors.slice(0, 6)" :key="index">
            <code>{{ item.field }}</code>{{ item.message }}
          </li>
        </ul>
      </div>
    </transition>

    <!-- 步骤面板：滑动过渡 -->
    <div class="step-viewport">
      <transition :name="stepDirection > 0 ? 'slide-left' : 'slide-right'" mode="out-in">
        <!-- 第 1 步：基本信息 -->
        <div v-if="stepIndex === 0" key="s0" class="step-panel">
          <div v-if="!isEdit" class="template-row">
            <label class="template-label">从内置模板开始<span>可选</span></label>
            <select v-model="templateId" class="field-select" @change="applyTemplate">
              <option value="">空白创建</option>
              <option v-for="tpl in templates" :key="tpl.id" :value="tpl.id">{{ tpl.name }}</option>
            </select>
            <p class="field-hint">选择模板会预填角色、提示词与目标，保存时以你修改后的内容为准。</p>
          </div>

          <div class="form-card">
            <div class="field-grid">
              <label class="field">场景名称<input v-model="form.meta.name" placeholder="如：酒店入住沟通" maxlength="100" /></label>
              <label class="field">场景 ID<small v-if="!isEdit">（URL 与导出标识，创建后不可改）</small><input v-model="form.meta.id" placeholder="如：hotel_checkin" pattern="[a-z][a-z0-9_]*" /></label>
            </div>
            <label class="field">一句话描述<textarea v-model="form.meta.description" rows="2" placeholder="学习者将在卡片上看到这句介绍" maxlength="200"></textarea></label>
            <div class="field-grid three">
              <label class="field">分类
                <select v-model="form.meta.category">
                  <option value="daily">日常沟通</option>
                  <option value="business">职场沟通</option>
                  <option value="career">求职训练</option>
                  <option value="academic">学术场景</option>
                  <option value="custom">自定义</option>
                </select>
              </label>
              <label class="field">难度
                <select v-model="form.meta.difficulty">
                  <option value="entry">入门 · 零基础友好</option>
                  <option value="easy">简单 · 日常基础</option>
                  <option value="normal">普通 · 进阶练习</option>
                  <option value="hard">困难 · 高压实战</option>
                  <option value="expert">专家 · 极限挑战</option>
                </select>
              </label>
              <label class="field">训练模式
                <select v-model="form.meta.mode">
                  <option value="conversation">任务对话</option>
                  <option value="interview">模拟面试</option>
                  <option value="debate">辩论</option>
                </select>
              </label>
            </div>
            <label class="field">标签（逗号分隔，最多 8 个）<input v-model="tagsText" placeholder="礼貌表达, 应变, 差旅" /></label>
          </div>

          <!-- 封面设置：编辑模式直传，创建模式保存后补传 -->
          <div class="form-card">
            <span class="field-label">封面图<span class="optional">可选</span></span>
            <div class="cover-row">
              <div class="cover-preview">
                <img v-if="coverPreviewUrl" :src="coverPreviewUrl" alt="封面预览" />
                <div v-else class="cover-placeholder">
                  <AppIcon name="image" :size="20" />
                  <span>暂无封面</span>
                </div>
              </div>
              <div class="cover-actions">
                <label class="ghost-button" :class="{ disabled: uploadingCover }">
                  <AppIcon name="upload" :size="13" />{{ coverPreviewUrl ? '更换封面' : '上传封面' }}
                  <input type="file" accept=".jpg,.jpeg,.png,.webp" class="hidden-input" :disabled="uploadingCover" @change="handleCover" />
                </label>
                <button
                  v-if="coverPreviewUrl"
                  class="ghost-button"
                  type="button"
                  :disabled="uploadingCover"
                  @click="isEdit ? doRemoveCover() : clearPendingCover()"
                >移除</button>
                <p class="field-hint">展示在场景卡与详情页顶部；支持 jpg / png / webp，5 MB 以内。未设置时使用默认样式。</p>
              </div>
            </div>
          </div>
        </div>

        <!-- 第 2 步：角色与对话 -->
        <div v-else-if="stepIndex === 1" key="s1" class="step-panel">
          <div class="form-card">
            <span class="field-label">角色<span class="optional">1–4 个，对话中 AI 扮演的人设</span></span>
            <div v-for="(role, index) in form.roles" :key="index" class="role-card">
              <div class="field-grid four">
                <label class="field">角色 ID<input v-model="role.id" placeholder="barista" /></label>
                <label class="field">名字<input v-model="role.display_name" placeholder="Leo" /></label>
                <label class="field">职务<input v-model="role.title" placeholder="Barista" /></label>
                <label class="field">性格<input v-model="role.personality" placeholder="friendly but busy" /></label>
              </div>
              <button
                v-if="form.roles.length > 1"
                class="role-remove"
                type="button"
                :aria-label="`删除角色 ${role.display_name || index + 1}`"
                @click="form.roles.splice(index, 1)"
              ><AppIcon name="x" :size="13" /></button>
            </div>
            <button v-if="form.roles.length < 4" class="ghost-button add-row" type="button" @click="addRole">
              <AppIcon name="plus" :size="13" />添加角色
            </button>
          </div>

          <div class="form-card">
            <div class="state-head">
              <span class="field-label">对话指引<span class="optional">告诉 AI 它是谁、该怎么做</span></span>
              <button class="adv-toggle" type="button" @click="togglePromptAdvanced">
                {{ form.promptAdvanced ? '返回引导模式' : '直接编辑 Prompt' }}
              </button>
            </div>
            <!-- 引导模式：结构化输入，保存时自动拼装 System Prompt -->
            <template v-if="!form.promptAdvanced">
              <div class="field">
                <span class="field-label">AI 扮演的角色</span>
                <p class="derive-note">{{ roleSummary }}</p>
                <p class="field-hint">在上方「角色」卡片修改名字、职务与性格，这里会自动同步。</p>
              </div>
              <label class="field">
                场景说明
                <textarea
                  ref="promptDescInput"
                  v-model="form.promptDesc"
                  rows="4"
                  placeholder="用你自己的话描述背景与要求，比如：你在一家咖啡店工作，学习者是来点单的顾客，请用英语自然交流，帮TA完成下单。"
                ></textarea>
              </label>
              <div class="var-chips" v-if="variableChips.length">
                <span class="var-chips-label">点击插入变量</span>
                <button
                  v-for="v in variableChips"
                  :key="'d' + v.token"
                  type="button"
                  class="var-chip"
                  :title="v.desc"
                  @click="insertTo(promptDescInput, v.token)"
                >{{ v.token }}</button>
              </div>
              <div class="field">
                <span class="field-label">对话规则<span class="optional">逐条添加，AI 会严格遵守</span></span>
                <div v-for="(rule, index) in form.promptRules" :key="index" class="rule-row">
                  <input v-model="rule.text" placeholder="如：始终使用英语回复；一次只推荐一款饮品" />
                  <button class="role-remove" type="button" :aria-label="`删除规则 ${index + 1}`" @click="form.promptRules.splice(index, 1)">
                    <AppIcon name="x" :size="13" />
                  </button>
                </div>
                <button class="ghost-button add-row" type="button" @click="addPromptRule">
                  <AppIcon name="plus" :size="13" />添加规则
                </button>
              </div>
            </template>
            <!-- 高级模式：直接编辑 System Prompt 原文 -->
            <label v-else class="field">System Prompt（{{ '{' }}roles.{{ '·' }}{{ '}' }} 与参数占位符可复用）
              <textarea ref="promptInput" v-model="form.prompt.system" rows="7" spellcheck="false" placeholder="You are {roles.barista.display_name}, a friendly barista at {store_name}…"></textarea>
            </label>
          </div>

          <div class="form-card">
            <label class="field">开场问候语
              <textarea ref="greetingInput" v-model="form.prompt.greeting" rows="2" placeholder="Hi there! Welcome to {store_name}…"></textarea>
            </label>
            <div class="var-chips" v-if="variableChips.length">
              <span class="var-chips-label">点击插入变量</span>
              <button
                v-for="v in variableChips"
                :key="'g' + v.token"
                type="button"
                class="var-chip"
                :title="v.desc"
                @click="insertTo(greetingInput, v.token)"
              >{{ v.token }}</button>
            </div>
            <p class="field-hint">学习者进入场景看到的第一句话；点上方变量可插入角色名、店名等个性化内容。</p>
            <div class="field">
              <span class="field-label">可覆盖参数</span>
              <div v-for="(param, index) in form.prompt.params" :key="index" class="param-row">
                <input v-model="param.key" placeholder="store_name" />
                <input v-model="param.default" placeholder="默认值" />
                <button class="role-remove" type="button" :aria-label="`删除参数 ${param.key || index + 1}`" @click="form.prompt.params.splice(index, 1)">
                  <AppIcon name="x" :size="13" />
                </button>
              </div>
              <button class="ghost-button add-row" type="button" @click="form.prompt.params.push({ key: '', default: '' })">
                <AppIcon name="plus" :size="13" />添加参数
              </button>
            </div>
          </div>
        </div>

        <!-- 第 3 步：目标与完成 -->
        <div v-else-if="stepIndex === 2" key="s2" class="step-panel">
          <div class="form-card">
            <span class="field-label">训练目标<span class="optional">希望学习者在对话中做到的事</span></span>
            <div v-for="(objective, index) in form.objectives" :key="index" class="role-card">
              <div class="field-grid two">
                <label class="field">目标描述<input v-model="objective.label" placeholder="礼貌提出请求" /></label>
                <div class="field">
                  <span class="field-label">达成判定<span class="optional">可选</span></span>
                  <select v-model="objective.checkMode">
                    <option value="none">不判定（仅展示）</option>
                    <option value="state">某个状态达成</option>
                    <option value="tool">调用了某工具</option>
                    <option value="custom">自定义表达式</option>
                  </select>
                </div>
              </div>
              <!-- 状态达成：变量 + 比较符 + 值 -->
              <div v-if="objective.checkMode === 'state'" class="cond-row no-remove">
                <select v-model="objective.checkKey" aria-label="状态变量">
                  <option value="" disabled>选择变量</option>
                  <option v-for="key in stateKeys" :key="key" :value="key">{{ key }}</option>
                </select>
                <select v-model="objective.checkOp" aria-label="比较符">
                  <option value="==">等于</option>
                  <option value="!=">不等于</option>
                  <option value=">">大于</option>
                  <option value=">=">不小于</option>
                  <option value="<">小于</option>
                  <option value="<=">不大于</option>
                </select>
                <input v-model="objective.checkValue" placeholder="值，如是/否填 true" />
              </div>
              <p v-if="objective.checkMode === 'state' && !stateKeys.length" class="field-hint">
                还没有状态变量，先在下方「初始任务状态」添加，或改用其他判定方式。
              </p>
              <!-- 工具判定：从白名单选择 -->
              <select v-if="objective.checkMode === 'tool'" v-model="objective.checkTool" aria-label="选择工具">
                <option value="" disabled>选择工具</option>
                <option v-for="tool in TOOLS" :key="tool.id" :value="tool.id">{{ tool.name }}（{{ tool.id }}）</option>
              </select>
              <input v-if="objective.checkMode === 'custom'" v-model="objective.check" spellcheck="false" placeholder="state.confirmed == true 或 tool_called('modify_order')" />
              <button class="role-remove" type="button" :aria-label="`删除目标 ${objective.label || index + 1}`" @click="form.objectives.splice(index, 1)">
                <AppIcon name="x" :size="13" />
              </button>
            </div>
            <button class="ghost-button add-row" type="button" @click="addObjective">
              <AppIcon name="plus" :size="13" />添加目标
            </button>
          </div>

          <div class="form-card">
            <div class="field">
              <span class="field-label">结束时机<span class="optional">训练何时收尾</span></span>
              <div class="finish-modes" role="radiogroup" aria-label="结束时机">
                <label v-for="mode in FINISH_MODES" :key="mode.value" class="finish-mode" :class="{ active: form.finishMode === mode.value }">
                  <input v-model="form.finishMode" type="radio" :value="mode.value" />
                  <span class="fm-title">{{ mode.title }}</span>
                  <span class="fm-desc">{{ mode.desc }}</span>
                </label>
              </div>
            </div>

            <!-- 状态条件构建器：变量 + 比较符 + 值，AND/OR 组合 -->
            <div v-if="form.finishMode === 'state'" class="cond-builder">
              <div v-for="(row, index) in form.finishRows" :key="index" class="cond-row">
                <select v-model="row.key" aria-label="状态变量">
                  <option value="" disabled>选择变量</option>
                  <option v-for="key in stateKeys" :key="key" :value="key">{{ key }}</option>
                </select>
                <select v-model="row.op" aria-label="比较符">
                  <option value="==">等于</option>
                  <option value="!=">不等于</option>
                  <option value=">">大于</option>
                  <option value=">=">不小于</option>
                  <option value="<">小于</option>
                  <option value="<=">不大于</option>
                </select>
                <input v-model="row.value" placeholder="值，如 true / 3 / 文本" />
                <button class="role-remove" type="button" :aria-label="`删除条件 ${index + 1}`" @click="form.finishRows.splice(index, 1)">
                  <AppIcon name="x" :size="13" />
                </button>
              </div>
              <div class="cond-toolbar">
                <select v-model="form.finishJoin" aria-label="条件组合方式">
                  <option value="and">满足全部条件</option>
                  <option value="or">满足任一条件</option>
                </select>
                <button class="ghost-button" type="button" @click="form.finishRows.push({ key: '', op: '==', value: '' })">
                  <AppIcon name="plus" :size="13" />添加条件
                </button>
              </div>
              <p v-if="!stateKeys.length" class="field-hint">还没有状态变量——先在下方「初始任务状态」添加，或改用其他结束时机。</p>
            </div>
            <label v-else-if="form.finishMode === 'custom'" class="field">完成条件表达式
              <input v-model="form.finish.when" spellcheck="false" placeholder="state.confirmed == true and state.paid == true" />
            </label>
            <p v-else-if="form.finishMode === 'goals'" class="field-hint">所有训练目标的达成判定都满足时，对话自动结束。</p>
            <p v-else class="field-hint">不设额外条件，对话进行到最大轮数后自动结束，适合自由练习。</p>

            <div class="field-grid two">
              <label class="field">最大轮数兜底<input v-model.number="form.finish.max_turns" type="number" min="2" max="200" /></label>
            </div>
            <p class="field-hint">无论哪种结束时机，达到最大轮数都会强制收尾，避免无限对话。</p>
            <div class="field">
              <div class="state-head">
                <span class="field-label">初始任务状态<span class="optional">记录训练进度，如「订单是否已确认」</span></span>
                <button class="adv-toggle" type="button" @click="toggleStateAdvanced">
                  {{ form.stateAdvanced ? '返回简单模式' : 'JSON 高级模式' }}
                </button>
              </div>
              <!-- 简单模式：键值行编辑器，无需手写 JSON -->
              <div v-if="!form.stateAdvanced" class="state-rows">
                <p v-if="!form.stateRows.length" class="state-empty">
                  暂无状态变量，不影响正常训练。添加后可用于训练目标的达成判定。
                </p>
                <div v-for="(row, index) in form.stateRows" :key="index" class="state-row">
                  <input v-model="row.key" placeholder="变量名，如 confirmed" />
                  <select v-model="row.type" aria-label="变量类型">
                    <option value="bool">是 / 否</option>
                    <option value="number">数字</option>
                    <option value="string">文本</option>
                  </select>
                  <label v-if="row.type === 'bool'" class="state-bool">
                    <input v-model="row.value" type="checkbox" />初始为「是」
                  </label>
                  <input
                    v-else-if="row.type === 'number'"
                    v-model.number="row.value"
                    type="number"
                    placeholder="0"
                  />
                  <input v-else v-model="row.value" placeholder="初始内容" />
                  <button
                    class="role-remove"
                    type="button"
                    :aria-label="`删除状态 ${row.key || index + 1}`"
                    @click="form.stateRows.splice(index, 1)"
                  ><AppIcon name="x" :size="13" /></button>
                </div>
                <button class="ghost-button add-row" type="button" @click="form.stateRows.push({ key: '', type: 'bool', value: false })">
                  <AppIcon name="plus" :size="13" />添加状态变量
                </button>
              </div>
              <!-- 高级模式：直接编辑 JSON（数组 / 对象等复杂结构仅在此模式支持） -->
              <textarea
                v-else
                v-model="form.stateText"
                rows="5"
                spellcheck="false"
                class="mono"
                placeholder='{ "order": [], "confirmed": false }'
              ></textarea>
              <p v-if="stateVarsHint" class="field-hint">已定义变量：{{ stateVarsHint }}。可在下方判定表达式中以 <code>state.变量名</code> 引用。</p>
            </div>
            <div class="field">
              <span class="field-label">允许工具<span class="optional">白名单引用，不定义实现；悬浮查看作用</span></span>
              <div class="tool-checks">
                <label v-for="tool in TOOLS" :key="tool.id" class="tool-check" :data-tip="`${tool.name}：${tool.desc}`" :title="`${tool.name}：${tool.desc}`">
                  <input v-model="form.tools.allowed" type="checkbox" :value="tool.id" />{{ tool.name }}
                </label>
              </div>
            </div>
          </div>
        </div>

        <!-- 第 4 步：资料与预览 -->
        <div v-else key="s3" class="step-panel">
          <div class="form-card">
            <span class="field-label">场景资料<span class="optional">md / txt / pdf，保存后可继续管理</span></span>
            <ul v-if="form.documents.length" class="doc-list">
              <li v-for="doc in form.documents" :key="doc.id">
                <AppIcon name="file-text" :size="13" />
                <span class="doc-name">{{ doc.filename }}</span>
                <span class="doc-meta">{{ doc.chunk_count }} 块 · {{ doc.visibility === 'user' ? '学习者可见' : '仅 AI 检索' }}</span>
                <button v-if="isEdit" class="doc-remove" type="button" @click="removeDocument(doc)"><AppIcon name="trash" :size="13" /></button>
              </li>
            </ul>
            <p v-else class="field-hint">还没有资料。菜单、内部规范、JD 等文件可以先保存场景，再在编辑页上传。</p>
            <label class="ghost-button add-row" :class="{ disabled: uploading }">
              <AppIcon name="upload" :size="13" />{{ isEdit ? '上传资料' : '选择资料（保存场景时一并上传）' }}
              <input type="file" accept=".md,.markdown,.txt,.pdf" class="hidden-input" :disabled="uploading" @change="handleFiles" />
            </label>
          </div>
          <div class="form-card">
            <span class="field-label">包结构预览</span>
            <pre class="pkg-preview mono">{{ packagePreview }}</pre>
          </div>
        </div>
      </transition>
    </div>

    <!-- 底部导航 -->
    <div class="editor-footer">
      <button class="ghost-button" type="button" :disabled="stepIndex === 0 || saving" @click="stepIndex -= 1; stepDirection = -1">
        <AppIcon name="chevron-left" :size="13" />上一步
      </button>
      <span class="step-indicator">{{ stepIndex + 1 }} / {{ STEPS.length }} · {{ STEPS[stepIndex].label }}</span>
      <button
        v-if="stepIndex < STEPS.length - 1"
        class="primary-button slim"
        type="button"
        :disabled="saving"
        @click="stepIndex += 1; stepDirection = 1"
      >下一步<AppIcon name="arrow-right" :size="13" /></button>
      <button v-else class="primary-button slim" type="button" :disabled="saving" @click="save">
        <AppIcon name="check" :size="13" />{{ isEdit ? '保存修改' : '创建场景' }}
      </button>
    </div>

    <transition name="toast">
      <div v-if="toast" class="toast" role="status">{{ toast }}</div>
    </transition>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import { session } from '../auth/session'
import { coverUrl, uploadCover, removeCover } from '../api/scenes'
import {
  createScene, getScene, listTemplates, updateScene, uploadKnowledge, deleteKnowledge,
} from '../api/scenes'

const STEPS = [
  { key: 'basic', label: '基本信息' },
  { key: 'role', label: '角色与对话' },
  { key: 'goal', label: '目标与完成' },
  { key: 'material', label: '资料与预览' },
]
// 工具白名单：界面显示中文名，悬浮 tooltip 解释作用（提交给后端的仍是英文 id）
const TOOLS = [
  { id: 'search_knowledge', name: '知识检索', desc: '在场景资料中检索相关内容，用于回答事实性问题' },
  { id: 'lookup_word', name: '词汇查询', desc: '查询单词释义与例句，适合语言学习类场景' },
  { id: 'get_learning_profile', name: '学习者画像', desc: '读取学习者的等级与偏好，动态调整对话难度' },
  { id: 'calculate_order', name: '订单计算', desc: '计算点餐 / 购物场景中的价格与合计' },
  { id: 'modify_order', name: '订单修改', desc: '修改当前订单内容，配合订单类训练目标使用' },
  { id: 'update_scene_state', name: '状态更新', desc: '更新任务状态 state，驱动目标判定与完成条件' },
  { id: 'get_hint', name: '获取提示', desc: '学习者卡住时给出一句话提示，不直接给出答案' },
  { id: 'add_review_task', name: '加入复习', desc: '把本次的错误或生词加入复习计划' },
  { id: 'next_interview_stage', name: '进入下一阶段', desc: '推进面试流程到下一环节（如技术面 → HR 面）' },
]

// 结束时机的四种模式（radio 卡片）
const FINISH_MODES = [
  { value: 'turns', title: '轮数收尾', desc: '进行到最大轮数自动结束，适合自由练习' },
  { value: 'goals', title: '目标达成', desc: '所有训练目标的判定都满足时结束' },
  { value: 'state', title: '状态条件', desc: '按任务状态收尾，如订单确认、预约成功' },
  { value: 'custom', title: '自定义表达式', desc: '手写白名单表达式，最灵活' },
]

const route = useRoute()
const router = useRouter()
const isEdit = computed(() => route.name === 'scene-edit')

// ---- 表单状态 ----
const blankObjective = () => ({ label: '', checkMode: 'none', checkKey: '', checkOp: '==', checkValue: '', checkTool: '', check: '' })
const blankForm = () => ({
  meta: { id: '', name: '', description: '', category: 'custom', difficulty: 'normal', mode: 'conversation' },
  roles: [{ id: '', display_name: '', title: '', personality: '', voice: '' }],
  prompt: { system: '', greeting: '', params: [] },
  // 对话指引：默认引导模式（场景说明 + 规则）；promptAdvanced 时直接编辑原文
  promptAdvanced: false,
  promptPlain: false, // 从高级模式带回原文后原样输出，不再拼脚手架
  promptDesc: '',
  promptRules: [],
  objectives: [blankObjective()],
  tools: { allowed: ['search_knowledge', 'get_hint'] },
  finish: { when: '', max_turns: 30 },
  // 结束时机：turns=轮数收尾 / goals=目标达成 / state=状态条件 / custom=表达式
  finishMode: 'turns',
  finishJoin: 'and',
  finishRows: [{ key: '', op: '==', value: '' }],
  // 初始状态：默认简单模式（键值行）；stateText 仅在 JSON 高级模式下使用
  stateRows: [],
  stateAdvanced: false,
  stateText: '',
  documents: [],
})
const form = ref(blankForm())
const tagsText = ref('')
const stepIndex = ref(0)
const stepDirection = ref(1)
const saving = ref(false)
const errors = ref([])
const saveError = ref('')
const toast = ref('')
const templates = ref([])
const templateId = ref('')
let toastTimer = null

const notify = (message) => {
  toast.value = message
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => (toast.value = ''), 2600)
}

function goBack() {
  router.push({ name: 'scenes' })
}

function addRole() {
  form.value.roles.push({ id: '', display_name: '', title: '', personality: '', voice: '' })
}

// ---- 对话指引：引导模式（结构化输入 → 拼装 System Prompt）与高级模式互转 ----
const promptDescInput = ref(null)
const promptInput = ref(null)
const greetingInput = ref(null)

const roleSummary = computed(() => {
  const roles = form.value.roles.filter((role) => role.display_name.trim() || role.id.trim())
  if (!roles.length) return '还没有角色，请先在上方添加。'
  return roles
    .map((role) => `${role.display_name.trim() || role.id.trim()}${role.title.trim() ? `（${role.title.trim()}）` : ''}`)
    .join('、')
})

// 可插入变量：角色名 + 可覆盖参数
const variableChips = computed(() => {
  const chips = []
  for (const role of form.value.roles) {
    if (role.id.trim()) {
      chips.push({ token: `{roles.${role.id.trim()}.display_name}`, desc: `角色「${role.display_name.trim() || role.id.trim()}」的名字` })
    }
  }
  for (const param of form.value.prompt.params) {
    if (param.key.trim()) {
      chips.push({ token: `{${param.key.trim()}}`, desc: `参数 ${param.key.trim()}（默认值：${param.default || '空'}）` })
    }
  }
  return chips
})

// 在光标处插入文本并同步 v-model（textarea 原生 input 事件）
function insertTo(elRef, token) {
  const el = elRef
  if (!el) return
  const start = el.selectionStart ?? el.value.length
  const end = el.selectionEnd ?? start
  el.value = el.value.slice(0, start) + token + el.value.slice(end)
  el.dispatchEvent(new Event('input'))
  el.focus()
  el.setSelectionRange(start + token.length, start + token.length)
}

function addPromptRule() {
  form.value.promptRules.push({ text: '' })
  form.value.promptPlain = false // 用户想加规则说明需要脚手架，退出原文直通
}

function addObjective() {
  form.value.objectives.push(blankObjective())
}

// 引导模式 → 拼装 System Prompt（英文脚手架 + 用户内容）
function assembleSimplePrompt() {
  const desc = form.value.promptDesc.trim()
  if (form.value.promptPlain) return desc // 高级模式带回的原文，原样使用
  const role = form.value.roles.find((item) => item.id.trim())
  const parts = []
  let head = 'You are ' + (role ? `{roles.${role.id.trim()}.display_name}` : 'a role-playing assistant')
  if (role?.title.trim()) head += `, ${role.title.trim()}`
  if (role?.personality.trim()) head += `. Personality: ${role.personality.trim()}`
  parts.push(head + '.')
  if (desc) parts.push(`Scenario: ${desc}`)
  const rules = form.value.promptRules.map((rule) => rule.text.trim()).filter(Boolean)
  if (rules.length) parts.push('Rules:\n' + rules.map((rule) => `- ${rule}`).join('\n'))
  parts.push('Always stay in character and keep the conversation natural.')
  return parts.join('\n\n')
}

function togglePromptAdvanced() {
  if (!form.value.promptAdvanced) {
    form.value.prompt.system = assembleSimplePrompt()
    form.value.promptAdvanced = true
    return
  }
  // 高级 → 引导：原文放进「场景说明」并进入直通模式，内容不丢失
  form.value.promptDesc = form.value.prompt.system
  form.value.promptRules = []
  form.value.promptPlain = true
  form.value.promptAdvanced = false
}

// ---- 封面 ----
const pendingCover = ref(null) // 创建模式暂存 { file, url }，保存后补传
const coverExists = ref(false) // 编辑模式：后端已有封面
const coverBust = ref(0) // 更换封面后强制刷新缓存
const uploadingCover = ref(false)

// 预览地址：优先本地暂存，其次后端已有封面
const coverPreviewUrl = computed(() => {
  if (pendingCover.value) return pendingCover.value.url
  if (isEdit.value && coverExists.value) return coverUrl(route.params.id, coverBust.value || undefined)
  return null
})

async function handleCover(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  if (!isEdit.value) {
    if (pendingCover.value) URL.revokeObjectURL(pendingCover.value.url)
    pendingCover.value = { file, url: URL.createObjectURL(file) } // 场景未创建：本地预览，保存后补传
    return
  }
  uploadingCover.value = true
  try {
    await uploadCover(route.params.id, file)
    coverExists.value = true
    coverBust.value = Date.now()
    notify('封面已更新')
  } catch (error) {
    notify(`封面上传失败：${error.message}`)
  } finally {
    uploadingCover.value = false
  }
}

async function doRemoveCover() {
  uploadingCover.value = true
  try {
    await removeCover(route.params.id)
    coverExists.value = false
    coverBust.value = 0
    notify('封面已移除')
  } catch (error) {
    notify(error.message)
  } finally {
    uploadingCover.value = false
  }
}

function clearPendingCover() {
  if (pendingCover.value) URL.revokeObjectURL(pendingCover.value.url)
  pendingCover.value = null
}

// 模板预填：克隆内置包 → 覆盖 ID/名称留空待用户填写
async function loadTemplates() {
  try {
    const { data } = await listTemplates()
    templates.value = data.items
  } catch {
    templates.value = [] // 模板加载失败不阻塞空白创建
  }
}

function applyTemplate() {
  const template = templates.value.find((item) => item.id === templateId.value)
  if (!template) return
  getScene(template.id)
    .then(({ data }) => {
      fillForm(data.package)
      form.value.meta.id = ''
      form.value.meta.name = ''
      form.value.meta.author = undefined
      form.value.meta.tags = []
      tagsText.value = ''
      notify(`已按「${template.name}」预填，记得修改 ID 与名称`)
    })
    .catch((error) => notify(error.message))
}

// ---- 初始状态 state：简单模式（键值行）与 JSON 高级模式互转 ----

// state 对象 → 键值行；返回 null 表示含数组/对象，无法用行表达
function stateToRows(state) {
  const entries = Object.entries(state || {})
  const rows = []
  for (const [key, value] of entries) {
    if (typeof value === 'boolean') rows.push({ key, type: 'bool', value })
    else if (typeof value === 'number') rows.push({ key, type: 'number', value })
    else if (typeof value === 'string') rows.push({ key, type: 'string', value })
    else return null
  }
  return rows
}

// 键值行 → state 对象（构建包与切换到 JSON 模式共用）
function stateFromRows(rows) {
  const state = {}
  for (const row of rows) {
    const key = row.key.trim()
    if (!key) continue
    if (row.type === 'bool') state[key] = !!row.value
    else if (row.type === 'number') {
      const num = Number(row.value)
      state[key] = row.value === '' || row.value === null || !Number.isFinite(num) ? 0 : num
    } else state[key] = String(row.value ?? '')
  }
  return state
}

function toggleStateAdvanced() {
  if (!form.value.stateAdvanced) {
    // 简单 → 高级：把当前行序列化为 JSON，避免内容丢失
    form.value.stateText = JSON.stringify(stateFromRows(form.value.stateRows), null, 2)
    form.value.stateAdvanced = true
    return
  }
  // 高级 → 简单：JSON 必须合法且仅含基础类型
  let parsed = {}
  try {
    parsed = form.value.stateText.trim() ? JSON.parse(form.value.stateText) : {}
  } catch {
    notify('JSON 尚未合法，修正后再切换回简单模式')
    return
  }
  const rows = stateToRows(parsed)
  if (!rows) {
    notify('包含数组或对象类型的状态，仅能在 JSON 模式下编辑')
    return
  }
  form.value.stateRows = rows
  form.value.stateAdvanced = false
}

// 已定义的状态变量键（简单模式取行，JSON 模式取解析后的键），供判定/完成条件构建器引用
const stateKeys = computed(() => {
  if (form.value.stateAdvanced) {
    try {
      return Object.keys(JSON.parse(form.value.stateText || '{}'))
    } catch {
      return []
    }
  }
  return form.value.stateRows.map((row) => row.key.trim()).filter(Boolean)
})

// 变量提示：帮助理解判定表达式里能引用什么
const stateVarsHint = computed(() => stateKeys.value.join('、'))

// ---- 表达式反向解析：把既有 check / finish.when 还原成可视化控件 ----

// 还原字面量："abc" / 'abc' → abc；true/数字保持
function unquoteLiteral(lit) {
  const text = lit.trim()
  if (/^".*"$/.test(text) || /^'.*'$/.test(text)) return text.slice(1, -1)
  return text
}

// 解析单条 state 比较：state.a == true → { key, op, value }；失败返回 null
const STATE_COND_RE = /^state\.([A-Za-z_][\w.]*)\s*(==|!=|>=|<=|>|<)\s*(.+)$/
function parseStateCond(part) {
  const match = part.trim().match(STATE_COND_RE)
  return match ? { key: match[1], op: match[2], value: unquoteLiteral(match[3]) } : null
}

// finish.when → 结束时机模式（turns/goals/state/custom）
function parseFinish(when) {
  const text = (when || '').trim()
  if (!text) return { mode: 'turns', join: 'and', rows: [{ key: '', op: '==', value: '' }] }
  if (text === 'goals_done()') return { mode: 'goals', join: 'and', rows: [{ key: '', op: '==', value: '' }] }
  // 历史兜底表达式 turn_count >= N 视为「轮数收尾」
  if (/^turn_count\s*>=\s*\d+$/.test(text)) {
    return { mode: 'turns', join: 'and', rows: [{ key: '', op: '==', value: '' }] }
  }
  const orParts = text.split(/\s+or\s+/)
  const andParts = text.split(/\s+and\s+/)
  const parts = orParts.length > 1 ? orParts : andParts
  const rows = []
  for (const part of parts) {
    const cond = parseStateCond(part)
    if (!cond) return { mode: 'custom', join: 'and', rows: [{ key: '', op: '==', value: '' }] }
    rows.push(cond)
  }
  return { mode: 'state', join: orParts.length > 1 ? 'or' : 'and', rows }
}

// objective.check → 判定模式（none/state/tool/custom）
function parseCheck(check) {
  const text = (check || '').trim()
  const blank = { checkMode: 'none', checkKey: '', checkOp: '==', checkValue: '', checkTool: '', check: '' }
  if (!text) return blank
  const tool = text.match(/^tool_called\(\s*'([\w]+)'\s*\)$/)
  if (tool) return { ...blank, checkMode: 'tool', checkTool: tool[1] }
  const cond = parseStateCond(text)
  if (cond) return { ...blank, checkMode: 'state', checkKey: cond.key, checkOp: cond.op, checkValue: cond.value }
  return { ...blank, checkMode: 'custom', check: text }
}

// 把完整包数据填充进分步表单（编辑模式同样走这里）
function fillForm(pkg) {
  const state = pkg.state || {}
  const rows = stateToRows(state)
  const useAdvanced = rows === null
  const finish = parseFinish(pkg.finish?.when)
  form.value = {
    meta: {
      ...pkg.meta,
      // 难度统一为中文三档展示（旧 CEFR 值按首字母归档）
      difficulty: normalizeDifficulty(pkg.meta.difficulty),
    },
    roles: pkg.roles.map((role) => ({ ...role })),
    prompt: {
      system: pkg.prompt.system,
      greeting: pkg.prompt.greeting || '',
      params: (pkg.prompt.params || []).map((param) => ({ key: param.key, default: param.default })),
    },
    // 既有包的 prompt 已成型，默认进高级模式原文编辑；空白创建才走引导模式
    promptAdvanced: true,
    promptPlain: false,
    promptDesc: '',
    promptRules: [],
    objectives: (pkg.objectives || []).map((objective) => ({ ...blankObjective(), label: objective.label, ...parseCheck(objective.check) })),
    tools: { allowed: [...(pkg.tools?.allowed || [])] },
    finish: { when: pkg.finish?.when || '', max_turns: pkg.finish?.max_turns || 30 },
    finishMode: finish.mode,
    finishJoin: finish.join,
    finishRows: finish.rows,
    stateRows: rows || [],
    stateAdvanced: useAdvanced,
    stateText: useAdvanced ? JSON.stringify(state, null, 2) : '',
    documents: [],
  }
  tagsText.value = (pkg.meta.tags || []).join(', ')
}

// 难度归一为五级英文枚举：合法值保留；历史 CEFR/中文三档映射；未知归 normal
function normalizeDifficulty(value) {
  const text = (value || '').trim()
  if (DIFFICULTY_SET.has(text)) return text
  if (text === '简单') return 'easy'
  if (text === '困难') return 'hard'
  if (text === '普通') return 'normal'
  const first = text.charAt(0).toUpperCase()
  if (first === 'A') return 'easy'
  if (first === 'C') return 'hard'
  return 'normal'
}
const DIFFICULTY_SET = new Set(['entry', 'easy', 'normal', 'hard', 'expert'])

// 编辑模式：加载现有包
onMounted(async () => {
  if (session.token === undefined) await new Promise((resolve) => setTimeout(resolve, 0))
  if (isEdit.value) {
    try {
      const { data } = await getScene(route.params.id)
      if (data.source === 'builtin') {
        notify('内置场景只读，已切换为复制创建模式')
        router.replace({ name: 'scene-create' })
        return
      }
      fillForm(data.package)
      form.value.documents = data.documents || []
      coverExists.value = !!data.cover_path
    } catch (error) {
      notify(error.message)
      router.replace({ name: 'scenes' })
      return
    }
  }
  loadTemplates()
})

// ---- 包组装与保存 ----

function slugify(name) {
  // 中文名 → 缺省 ID：拼音不可用时退化为 scene + 随机后缀
  const cleaned = name.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '')
  return cleaned || `scene_${Math.random().toString(36).slice(2, 6)}`
}

function buildPackage() {
  const tags = tagsText.value.split(/[,，]/).map((tag) => tag.trim()).filter(Boolean)
  const meta = {
    id: form.value.meta.id?.trim() || slugify(form.value.meta.name),
    name: form.value.meta.name.trim(),
    description: form.value.meta.description.trim(),
    category: form.value.meta.category,
    mode: form.value.meta.mode,
    version: 2,
  }
  if (form.value.meta.difficulty?.trim()) meta.difficulty = form.value.meta.difficulty.trim()
  if (tags.length) meta.tags = tags.slice(0, 8)

  const roles = form.value.roles
    .filter((role) => role.display_name.trim() || role.id.trim())
    .map((role, index) => {
      const item = {
        id: role.id.trim() || `role_${index + 1}`,
        display_name: role.display_name.trim() || role.id.trim() || `Role ${index + 1}`,
      }
      if (role.title.trim()) item.title = role.title.trim()
      if (role.personality.trim()) item.personality = role.personality.trim()
      return item
    })

  const params = form.value.prompt.params
    .filter((param) => param.key.trim())
    .map((param) => ({ key: param.key.trim(), type: 'string', default: param.default, editable: true }))

  const objectives = form.value.objectives
    .filter((objective) => objective.label.trim())
    .map((objective, index) => {
      const item = { id: `obj_${index + 1}`, label: objective.label.trim() }
      const check = buildObjectiveCheck(objective)
      if (check) item.check = check
      return item
    })

  // 初始状态：简单模式由行构建；高级模式解析 JSON（非法时交给后端给可解释错误）
  const state = form.value.stateAdvanced
    ? (() => {
        try {
          return form.value.stateText.trim() ? JSON.parse(form.value.stateText) : {}
        } catch {
          return { __invalid_json__: form.value.stateText }
        }
      })()
    : stateFromRows(form.value.stateRows)

  return {
    meta,
    roles: roles.length ? roles : [{ id: 'assistant', display_name: 'Assistant' }],
    prompt: {
      system: form.value.promptAdvanced ? form.value.prompt.system.trim() : assembleSimplePrompt(),
      greeting: form.value.prompt.greeting.trim(),
      params,
    },
    objectives,
    state,
    tools: { allowed: [...form.value.tools.allowed], config: {} },
    finish: buildFinish(),
  }
}

// 用户输入的值 → 表达式字面量：true/false/数字原样，其余加双引号
function buildLiteral(raw) {
  const text = String(raw ?? '').trim()
  if (!text) return 'true'
  if (/^(true|false|null)$/.test(text) || /^-?\d+(\.\d+)?$/.test(text)) return text
  return `"${text.replace(/"/g, '\\"')}"`
}

// 目标判定：可视化模式 → 表达式；未配置返回空（不写 check 字段）
function buildObjectiveCheck(objective) {
  if (objective.checkMode === 'state' && objective.checkKey) {
    return `state.${objective.checkKey} ${objective.checkOp} ${buildLiteral(objective.checkValue)}`
  }
  if (objective.checkMode === 'tool' && objective.checkTool) {
    return `tool_called('${objective.checkTool}')`
  }
  if (objective.checkMode === 'custom') return objective.check.trim()
  return ''
}

// 结束时机：按模式产出 finish.when；无内容时保留 turn_count 兜底
function buildFinish() {
  const maxTurns = form.value.finish.max_turns || 30
  let when = ''
  if (form.value.finishMode === 'goals') {
    when = 'goals_done()'
  } else if (form.value.finishMode === 'state') {
    const conds = form.value.finishRows
      .filter((row) => row.key)
      .map((row) => `state.${row.key} ${row.op} ${buildLiteral(row.value)}`)
    when = conds.join(form.value.finishJoin === 'or' ? ' or ' : ' and ')
  } else if (form.value.finishMode === 'custom') {
    when = form.value.finish.when.trim()
  }
  return { when: when || `turn_count >= ${maxTurns}`, max_turns: maxTurns }
}

const packagePreview = computed(() => {
  try {
    return JSON.stringify(buildPackage(), null, 2)
  } catch {
    return '// state JSON 尚未合法，修正后可预览完整包结构'
  }
})

function goStep(index) {
  stepDirection.value = index > stepIndex.value ? 1 : -1
  stepIndex.value = index
}

async function save() {
  if (saving.value) return
  errors.value = []
  saveError.value = ''
  saving.value = true
  const pkg = buildPackage()
  try {
    const { data } = isEdit.value
      ? await updateScene(route.params.id, pkg)
      : await createScene(pkg)
    // 向导中暂存的封面/资料在创建后补传（上传端点需要场景已存在）
    if (!isEdit.value && pendingCover.value) {
      try {
        await uploadCover(data.id, pendingCover.value.file)
      } catch (uploadError) {
        notify(`封面上传失败：${uploadError.message}`)
      }
      clearPendingCover()
    }
    if (!isEdit.value && pendingFiles.value.length) {
      for (const file of pendingFiles.value) {
        try {
          await uploadKnowledge(data.id, file)
        } catch (uploadError) {
          notify(`资料 ${file.name} 上传失败：${uploadError.message}`)
        }
      }
    }
    notify(isEdit.value ? '修改已保存' : `场景「${data.name}」已创建，默认本地私有`)
    router.push({ name: 'scenes' })
  } catch (error) {
    saveError.value = error.code === 'SCENE_INVALID_PACKAGE' ? '' : error.message
    errors.value = error.details?.length ? error.details : [{ field: '', message: error.message }]
  } finally {
    saving.value = false
  }
}

const pendingFiles = ref([]) // 创建模式暂存的资料文件（保存后补传）
const uploading = ref(false)

async function handleFiles(event) {
  const files = Array.from(event.target.files || [])
  event.target.value = ''
  if (!files.length) return
  if (!isEdit.value) {
    pendingFiles.value.push(...files) // 场景未创建：先暂存，save() 成功后补传
    notify(`已选择 ${files.length} 个文件，将在创建场景后上传`)
    return
  }
  uploading.value = true
  for (const file of files) {
    try {
      const { data } = await uploadKnowledge(route.params.id, file)
      form.value.documents.push(data)
      notify(`已上传 ${data.filename}（${data.chunk_count} 块）`)
    } catch (error) {
      notify(`上传 ${file.name} 失败：${error.message}`)
    }
  }
  uploading.value = false
}

async function removeDocument(doc) {
  try {
    await deleteKnowledge(route.params.id, doc.id)
    form.value.documents = form.value.documents.filter((item) => item.id !== doc.id)
    notify(`已删除 ${doc.filename}`)
  } catch (error) {
    notify(error.message)
  }
}
</script>

<style scoped>
/* 整页布局：页头与底部操作栏固定，步骤区独立滚动（内容再多也不顶出窗口） */
.editor-page { flex: 1; min-height: 0; display: flex; flex-direction: column; padding: 16px 28px 0; overflow: hidden; }

/* 页头：返回 + 居中步骤条；标题由壳层顶栏提供，避免重复 */
.editor-topbar { display: flex; flex: 0 0 auto; align-items: center; justify-content: space-between; gap: 14px; margin-bottom: 14px; }
.back-button { display: inline-flex; align-items: center; gap: 4px; height: 34px; padding: 0 13px 0 9px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); color: var(--ink-soft); font-size: 13.5px; transition: border-color .15s, color .15s, background .15s; }
.back-button:hover { border-color: #d5d7e6; color: var(--ink); background: #fafafd; }
.topbar-balance { width: 74px; flex: 0 0 auto; } /* 平衡返回按钮宽度，让步骤条视觉居中 */

.primary-button.slim { width: auto; height: 36px; margin-top: 0; gap: 6px; padding: 0 18px; justify-content: center; }
.ghost-button { display: inline-flex; align-items: center; gap: 6px; height: 34px; padding: 0 14px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); color: var(--ink-soft); font-size: 13.5px; transition: border-color .15s, color .15s, background .15s; }
.ghost-button:hover:not(:disabled) { border-color: #d5d7e6; color: var(--ink); background: #fafafd; }
.ghost-button:disabled { opacity: .5; cursor: default; }
.ghost-button.disabled { opacity: .6; pointer-events: none; }

/* 步骤条 */
.steps { display: flex; align-items: center; gap: 4px; margin: 0; padding: 0; list-style: none; }
.step-item { display: inline-flex; align-items: center; gap: 7px; height: 33px; padding: 0 13px; border: 0; border-radius: 8px; background: transparent; color: var(--muted); font-size: 13.5px; transition: background .15s, color .15s; }
.step-item:hover { color: var(--ink); }
.step-item.active { background: var(--brand-soft); color: var(--brand-deep, var(--brand)); font-weight: 500; }
.step-dot { display: grid; width: 20px; height: 20px; place-items: center; border-radius: 50%; background: #eef0f5; color: var(--muted); font-size: 11px; font-weight: 600; }
.step-item.active .step-dot { background: var(--brand); color: #fff; }
.step-item.done .step-dot { background: #e3ecf9; color: #3d6bc4; }

.error-panel { flex: 0 0 auto; width: 100%; max-width: 780px; margin: 0 auto 14px; padding: 13px 15px; border: 1px solid #f0d9dd; border-radius: 10px; background: #fdf7f8; }
.error-title { display: flex; align-items: center; gap: 6px; margin: 0 0 6px; color: var(--danger); font-size: 13.5px; font-weight: 500; }
.error-panel ul { margin: 0; padding: 0 0 0 4px; list-style: none; }
.error-panel li { margin: 3px 0; color: var(--ink-soft); font-size: 13px; }
.error-panel code { margin-right: 7px; padding: 1px 6px; border-radius: 5px; background: #f7e9eb; color: var(--danger); font-size: 11.5px; }

/* 步骤区：唯一滚动容器；错误面板与步骤面板居中于其中 */
.step-viewport { flex: 1; min-height: 0; overflow-y: auto; margin: 0 -28px; padding: 2px 28px 22px; }
.step-panel { display: flex; flex-direction: column; gap: 16px; width: 100%; max-width: 780px; margin: 0 auto; } /* 内容整体居中 */
.slide-left-enter-active, .slide-left-leave-active,
.slide-right-enter-active, .slide-right-leave-active { transition: opacity .18s ease, transform .18s ease; }
.slide-left-enter-from { opacity: 0; transform: translateX(18px); }
.slide-left-leave-to { opacity: 0; transform: translateX(-14px); }
.slide-right-enter-from { opacity: 0; transform: translateX(-18px); }
.slide-right-leave-to { opacity: 0; transform: translateX(14px); }
.expand-enter-active, .expand-leave-active { transition: opacity .18s, transform .18s; }
.expand-enter-from, .expand-leave-to { opacity: 0; transform: translateY(-4px); }

/* 表单分组卡片：相关字段归组，节奏感优于长表单 */
.form-card { display: flex; flex-direction: column; gap: 15px; padding: 20px; border: 1px solid var(--line); border-radius: 12px; background: var(--surface); }

.field { display: block; }
.field-label { display: block; margin-bottom: 7px; color: var(--ink-soft); font-size: 13px; font-weight: 500; }
.optional { margin-left: 7px; color: var(--muted); font-size: 12px; font-weight: 400; }
.field input, .field textarea, .field-select, .field select {
  display: block; width: 100%; padding: 9px 12px; border: 1px solid #e0e1e9; border-radius: 8px; outline: none;
  background: var(--surface); color: var(--ink); font-size: 14px; font-family: inherit;
  transition: border-color .15s, box-shadow .15s;
}
.field textarea { resize: vertical; line-height: 1.6; }
/* 统一 select 外观：去掉原生控件样式，自绘下拉箭头 */
.field select, .field-select {
  appearance: none; -webkit-appearance: none; cursor: pointer;
  background-image: url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%237b8095' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
  background-repeat: no-repeat; background-position: right 11px center; padding-right: 32px;
}
.field input:focus, .field textarea:focus, .field-select:focus, .field select:focus { border-color: var(--brand); box-shadow: 0 0 0 3px rgba(98, 101, 232, .12); }
.field input::placeholder, .field textarea::placeholder { color: var(--faint); }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12.5px !important; }
.field small { margin-left: 4px; color: var(--faint); font-weight: 400; }
.field-hint { margin: 7px 0 0; color: var(--muted); font-size: 12.5px; line-height: 1.6; text-wrap: pretty; }
.field-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.field-grid.three { grid-template-columns: 1fr 1fr 1fr; }
.field-grid.four { grid-template-columns: repeat(4, 1fr); }
.field-grid.two { grid-template-columns: 1fr 1fr; }

/* 模板行：浅色提示带，不再用品牌色块 */
.template-row { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; width: 100%; max-width: 780px; margin: 0 auto; padding: 13px 15px; border: 1px solid var(--line); border-radius: 12px; background: var(--surface); }
.template-label { display: inline-flex; align-items: center; gap: 7px; color: var(--ink-soft); font-size: 13.5px; font-weight: 500; }
.template-row .field-select { width: auto; min-width: 200px; flex: 0 1 260px; }
.template-row .field-hint { flex: 1 1 100%; margin: 0; }

/* 封面设置 */
.cover-row { display: flex; gap: 18px; align-items: flex-start; }
.cover-preview { display: grid; flex: 0 0 auto; width: 200px; height: 113px; place-items: center; overflow: hidden; border: 1px dashed #d9dbe8; border-radius: 10px; background: #f7f8fc; }
.cover-preview img { display: block; width: 100%; height: 100%; object-fit: cover; }
.cover-placeholder { display: grid; justify-items: center; gap: 6px; color: var(--faint); font-size: 12px; }
.cover-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; flex: 1; padding-top: 4px; }
.cover-actions .field-hint { flex: 1 1 100%; margin: 0; }

.role-card, .objective-card { position: relative; padding: 12px; margin-bottom: 9px; border: 1px solid var(--line); border-radius: 10px; background: #fbfbfd; }
.role-card:last-of-type, .objective-card:last-of-type { margin-bottom: 0; }
.role-remove { position: absolute; top: 9px; right: 9px; display: grid; width: 22px; height: 22px; place-items: center; border: 0; border-radius: 6px; background: transparent; color: var(--muted); transition: background .15s, color .15s; }
.role-remove:hover { background: #fbf1f2; color: var(--danger); }
.param-row { display: grid; grid-template-columns: 1fr 1fr 26px; gap: 9px; margin-bottom: 8px; align-items: center; }
.param-row input { padding: 8px 11px; border: 1px solid #e0e1e9; border-radius: 8px; outline: none; font-size: 13.5px; background: var(--surface); color: var(--ink); }
.param-row input:focus { border-color: var(--brand); }
.param-row .role-remove { position: static; }
.add-row { margin-top: 4px; }

.tool-checks { display: flex; flex-wrap: wrap; gap: 7px; }
/* chip 不收缩且禁止断行：中文标签在空间不足时会逐字换行，把固定高度的胶囊撑爆（截图 bug 根因） */
.tool-check { position: relative; display: inline-flex; flex: 0 0 auto; align-items: center; gap: 6px; height: 29px; padding: 0 12px; border: 1px solid var(--line); border-radius: 7px; background: var(--surface); color: var(--ink-soft); font-size: 12.5px; white-space: nowrap; cursor: help; transition: border-color .15s, background .15s, color .15s; }
/* 悬浮 tooltip：解释工具的详细作用（title 属性兜底触屏/读屏） */
.tool-check::after {
  content: attr(data-tip);
  position: absolute; bottom: calc(100% + 8px); left: 50%; z-index: 15;
  width: max-content; max-width: 250px; transform: translateX(-50%) translateY(3px);
  padding: 7px 10px; border-radius: 8px; background: #2b2d4e; color: #fff;
  font-size: 12px; font-weight: 400; line-height: 1.55; text-align: left; white-space: normal;
  opacity: 0; pointer-events: none; transition: opacity .15s, transform .15s;
}
.tool-check::before {
  content: ''; position: absolute; bottom: calc(100% + 3px); left: 50%; z-index: 15;
  border: 5px solid transparent; border-top-color: #2b2d4e;
  opacity: 0; pointer-events: none; transition: opacity .15s;
}
.tool-check:hover::after { opacity: 1; transform: translateX(-50%) translateY(0); }
.tool-check:hover::before { opacity: 1; }
.tool-check:has(input:checked) { border-color: var(--brand); background: var(--brand-soft); color: var(--brand-deep, var(--brand)); }
.tool-check input { accent-color: var(--brand); }

/* 初始状态编辑器：简单模式键值行 + JSON 模式切换 */
.state-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 7px; }
.state-head .field-label { margin-bottom: 0; }
.adv-toggle { flex: 0 0 auto; border: 0; padding: 2px 4px; background: transparent; color: var(--brand); font-size: 12.5px; cursor: pointer; }
.adv-toggle:hover { text-decoration: underline; }
.state-rows { display: flex; flex-direction: column; gap: 8px; }
.state-empty { margin: 0; padding: 11px 13px; border: 1px dashed var(--line); border-radius: 8px; color: var(--muted); font-size: 12.5px; line-height: 1.6; }
.state-row { display: grid; grid-template-columns: 1.2fr 104px 1fr 26px; gap: 8px; align-items: center; }
.state-row input, .state-row select {
  min-width: 0; padding: 8px 11px; border: 1px solid #e0e1e9; border-radius: 8px; outline: none;
  background: var(--surface); color: var(--ink); font-size: 13.5px; font-family: inherit;
  transition: border-color .15s;
}
.state-row select { cursor: pointer; }
.state-row input:focus, .state-row select:focus { border-color: var(--brand); }
.state-bool { display: inline-flex; align-items: center; gap: 7px; min-width: 0; color: var(--ink-soft); font-size: 13px; cursor: pointer; white-space: nowrap; }
.state-bool input { width: auto; accent-color: var(--brand); }
.state-row .role-remove { position: static; }
.field-hint code { padding: 1px 5px; border-radius: 4px; background: #f1f2f7; font-size: 11.5px; }

/* 对话指引引导模式：角色摘要 + 规则行 + 变量 chips */
.derive-note { margin: 0; padding: 9px 12px; border: 1px solid #e8e9f2; border-radius: 8px; background: #fbfbfd; color: var(--ink-soft); font-size: 13.5px; }
.rule-row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.rule-row input { flex: 1; min-width: 0; padding: 8px 11px; border: 1px solid #e0e1e9; border-radius: 8px; outline: none; background: var(--surface); color: var(--ink); font-size: 13.5px; transition: border-color .15s; }
.rule-row input:focus { border-color: var(--brand); }
.rule-row .role-remove { position: static; }
.var-chips { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.var-chips-label { color: var(--muted); font-size: 12px; }
.var-chip { height: 24px; padding: 0 9px; border: 1px dashed #d9dbe8; border-radius: 6px; background: #fbfbfd; color: var(--brand); font-size: 11.5px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; cursor: pointer; transition: border-color .15s, background .15s; }
.var-chip:hover { border-color: var(--brand); background: var(--brand-soft); }

/* 结束时机：四选一模式卡片 */
.finish-modes { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
.finish-mode { position: relative; display: flex; flex-direction: column; gap: 3px; padding: 11px 12px; border: 1px solid var(--line); border-radius: 10px; background: var(--surface); cursor: pointer; transition: border-color .15s, background .15s; }
.finish-mode:hover { border-color: #d5d7e6; }
.finish-mode.active { border-color: var(--brand); background: var(--brand-soft); }
.finish-mode input { position: absolute; opacity: 0; pointer-events: none; }
.fm-title { color: var(--ink); font-size: 13px; font-weight: 600; }
.finish-mode.active .fm-title { color: var(--brand-deep, var(--brand)); }
.fm-desc { color: var(--muted); font-size: 11.5px; line-height: 1.5; }

/* 条件构建器：变量 + 比较符 + 值（目标判定与结束条件共用） */
.cond-builder { display: flex; flex-direction: column; gap: 8px; }
.cond-row { display: grid; grid-template-columns: 1.1fr 92px 1fr 26px; gap: 8px; align-items: center; }
.cond-row.no-remove { grid-template-columns: 1.1fr 92px 1fr; }
.cond-row select, .cond-row input, .cond-toolbar select {
  min-width: 0; padding: 8px 11px; border: 1px solid #e0e1e9; border-radius: 8px; outline: none;
  background: var(--surface); color: var(--ink); font-size: 13px; font-family: inherit;
  transition: border-color .15s;
}
.cond-row select, .cond-toolbar select { cursor: pointer; }
.cond-row input:focus, .cond-row select:focus, .cond-toolbar select:focus { border-color: var(--brand); }
.cond-row .role-remove { position: static; }
.cond-toolbar { display: flex; align-items: center; gap: 8px; }
/* 目标卡片内的工具选择 / 自定义表达式输入 */
.role-card > input, .role-card > select { width: 100%; margin-top: 9px; padding: 8px 11px; border: 1px solid #e0e1e9; border-radius: 8px; outline: none; background: var(--surface); color: var(--ink); font-size: 13.5px; font-family: inherit; transition: border-color .15s; }
.role-card > select { cursor: pointer; }
.role-card > input:focus, .role-card > select:focus { border-color: var(--brand); }

.doc-list { margin: 0; padding: 0; list-style: none; }
.doc-list li { display: flex; align-items: center; gap: 8px; height: 36px; padding: 0 12px; margin-bottom: 6px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); color: var(--ink-soft); font-size: 13.5px; }
.doc-name { color: var(--ink); }
.doc-meta { margin-left: auto; color: var(--muted); font-size: 12px; }
.doc-remove { display: grid; width: 24px; height: 24px; place-items: center; border: 0; border-radius: 6px; background: transparent; color: var(--muted); transition: background .15s, color .15s; }
.doc-remove:hover { background: #fbf1f2; color: var(--danger); }
.pkg-preview { max-height: 300px; overflow: auto; margin: 0; padding: 13px; border: 1px solid var(--line); border-radius: 10px; background: #fbfbfd; color: var(--ink-soft); font-size: 12.5px; line-height: 1.6; white-space: pre; }

/* 底部操作栏：固定贴底（不随内容滚动），主操作按钮永远可见 */
.editor-footer { display: flex; flex: 0 0 auto; align-items: center; justify-content: space-between; margin: 0 -28px; padding: 12px 28px; border-top: 1px solid var(--line); background: var(--surface); }
.step-indicator { color: var(--muted); font-size: 12.5px; }

.hidden-input { display: none; }

.toast { position: fixed; top: 58px; left: 50%; z-index: 50; max-width: min(460px, calc(100vw - 40px)); padding: 9px 16px; border-radius: 9px; background: #2b2d4e; color: #fff; font-size: 13.5px; box-shadow: 0 10px 28px rgba(34, 37, 59, .22); transform: translateX(-50%); }
.toast-enter-active, .toast-leave-active { transition: opacity .2s, transform .2s; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translate(-50%, -6px) !important; }

@media (max-width: 900px) {
  .field-grid.four { grid-template-columns: 1fr 1fr; }
  .field-grid.three { grid-template-columns: 1fr; }
  .cover-row { flex-direction: column; }
  .finish-modes { grid-template-columns: 1fr 1fr; }
}
</style>
