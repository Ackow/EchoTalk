<template>
  <!-- 多角色对话/辩论场景创建与编辑向导 -->
  <section class="editor-page">
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

    <transition name="expand">
      <div v-if="formError" class="error-panel" role="alert">
        <p class="error-title"><AppIcon name="x" :size="13" />{{ formError }}</p>
      </div>
    </transition>

    <div class="step-viewport">
      <transition :name="stepDirection > 0 ? 'slide-left' : 'slide-right'" mode="out-in">
        <!-- 第 1 步：基本信息 -->
        <div v-if="stepIndex === 0" key="d0" class="step-panel">
          <div class="form-card">
            <span class="field-label">场景子类型<span class="optional">决定房间机制与 AI 轮替规则</span></span>
            <div class="scene-type-grid" role="radiogroup" aria-label="多角色场景类型">
              <button
                type="button"
                class="scene-type-card"
                :class="{ active: form.sceneType === 'debate' }"
                @click="switchSceneType('debate')"
              >
                <strong><AppIcon name="messages" :size="14" />辩论对抗 (Debate)</strong>
                <span>选择正反立场、反方质询、评委打分与实时胜率交锋条</span>
              </button>
              <button
                type="button"
                class="scene-type-card"
                :class="{ active: form.sceneType === 'panel' }"
                @click="switchSceneType('panel')"
              >
                <strong><AppIcon name="users" :size="14" />多人对话 / 群面 (Panel)</strong>
                <span>2–4 位不同角色轮流追问、切换对应数字人与音色，适合终面与方案评审</span>
              </button>
            </div>
          </div>

          <div v-if="!isEdit" class="ai-draft-card">
            <div class="ai-draft-head">
              <strong><AppIcon name="sparkles" :size="14" />AI 一键生成多角色场景参数</strong>
              <span>{{ form.sceneType === 'panel' ? '输入群面或圆桌主题，自动规划 3 位考官/评审数字人、阶段与高频表达' : '输入一句辩题想法，自动生成中英文 Motion、正反论点与核心表达' }}</span>
            </div>
            <div class="ai-draft-row">
              <input
                v-model="aiIdea"
                :placeholder="form.sceneType === 'panel' ? '例如：高级后端工程师终面（架构师 + HRBP + 技术VP）' : '例如：高校是否应全面允许学生在考试中使用 AI 工具'"
                @keydown.enter.prevent="handleGenerateDraft"
              />
              <button
                type="button"
                class="primary-button slim"
                :disabled="generating || !aiIdea.trim()"
                @click="handleGenerateDraft"
              >
                {{ generating ? '生成中...' : 'AI 一键生成' }}
              </button>
            </div>
          </div>

          <div class="form-card">
            <div class="field-grid">
              <label class="field">{{ form.sceneType === 'panel' ? '场景中文名称' : '中文辩题名称' }}
                <input v-model="form.titleZh" :placeholder="form.sceneType === 'panel' ? '如：跨部门新产品 Q3 上线评审会' : '如：AI 是否应该参与司法量刑辅助？'" maxlength="120" />
              </label>
              <label class="field">建议时长<small>（影响总轮数 4 / 6 / 8 轮）</small>
                <select v-model="form.duration">
                  <option value="6 分钟">6 分钟（4 轮）</option>
                  <option value="8 分钟">8 分钟（6 轮）</option>
                  <option value="10 分钟">10 分钟（8 轮）</option>
                </select>
              </label>
            </div>
            <label class="field">{{ form.sceneType === 'panel' ? '英文议题与任务指令' : '英文辩题 Motion' }}
              <textarea v-model="form.motionEn" rows="2" :placeholder="form.sceneType === 'panel' ? 'Senior Backend Panel: Defend your production reliability trade-offs...' : 'This house believes...'" maxlength="400"></textarea>
            </label>
            <div class="field-grid" :class="form.sceneType === 'panel' ? 'four' : 'three'">
              <label v-if="form.sceneType === 'panel'" class="field">我方身份
                <input v-model="form.userRoleLabel" placeholder="候选人 / 主讲人" maxlength="48" />
              </label>
              <label class="field">分类
                <select v-model="form.category">
                  <option value="tech">科技伦理</option>
                  <option value="workplace">职场文化</option>
                  <option value="education">教育成长</option>
                  <option value="society">社会生活</option>
                </select>
              </label>
              <label class="field">难度
                <select v-model="form.difficulty">
                  <option value="beginner">入门</option>
                  <option value="intermediate">进阶</option>
                  <option value="advanced">挑战</option>
                </select>
              </label>
              <label class="field">{{ form.sceneType === 'panel' ? '默认追问压力' : '默认对手风格' }}
                <select v-model="form.defaultStyle">
                  <option value="supportive">温和引导</option>
                  <option value="balanced">逻辑严密</option>
                  <option value="sharp">犀利压迫</option>
                </select>
              </label>
            </div>
          </div>

          <!-- 封面图设置：编辑模式直传，创建模式保存后补传 -->
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

        <!-- 第 2 步：角色阵容与观点 -->
        <div v-else-if="stepIndex === 1" key="d1" class="step-panel">
          <div class="form-card">
            <div class="field-grid">
              <label class="field">{{ form.sceneType === 'panel' ? '核心展示要点' : '正方核心论点' }}
                <textarea v-model="form.proSummary" rows="2" :placeholder="form.sceneType === 'panel' ? '本场希望用户展现哪些优势或关键逻辑' : '概括支持该辩题的核心理由'"></textarea>
              </label>
              <label class="field">{{ form.sceneType === 'panel' ? '重点质疑与压力方向' : '反方核心论点' }}
                <textarea v-model="form.conSummary" rows="2" :placeholder="form.sceneType === 'panel' ? 'AI 角色将重点挑战哪些风险或短板' : '概括反对该辩题的核心理由'"></textarea>
              </label>
            </div>
          </div>

          <div class="form-card">
            <div class="card-head-row">
              <span class="field-label" style="margin-bottom:0">AI 多角色阵容<span class="optional">2–4 位，支持独立绑定数字人形象与音色</span></span>
              <button v-if="form.roles.length < 4" class="ghost-button slim-btn" type="button" @click="addRole">
                <AppIcon name="plus" :size="13" />添加角色 ({{ form.roles.length }}/4)
              </button>
            </div>
            <div v-for="(role, idx) in form.roles" :key="role.id || idx" class="sub-role-card">
              <div class="sub-role-head">
                <span class="role-badge">席位 {{ idx + 1 }}</span>
                <button
                  v-if="form.roles.length > 2"
                  type="button"
                  class="role-del-btn"
                  aria-label="删除角色"
                  @click="form.roles.splice(idx, 1)"
                ><AppIcon name="x" :size="13" /></button>
              </div>
              <div class="field-grid three">
                <label class="field">角色定位
                  <select v-model="role.roleType">
                    <option value="moderator">主理 / 主持人</option>
                    <option value="interviewer">面试 / 评审官</option>
                    <option value="opponent">对手辩手</option>
                    <option value="judge">评委 / 决策官</option>
                  </select>
                </label>
                <label class="field">英文名字<input v-model="role.name" placeholder="如：Claire" maxlength="40" /></label>
                <label class="field">职务头衔<input v-model="role.title" placeholder="如：技术总监 / HRBP" maxlength="48" /></label>
              </div>
              <div class="field-grid" style="margin-top: 10px;">
                <label class="field">数字人形象
                  <select v-model="role.avatarId" @change="onRoleAvatarChange(role)">
                    <option v-for="av in avatarOptions" :key="av.id" :value="av.id">
                      {{ av.display_name || av.name || av.id }}{{ av.kind === 'custom' || av.is_custom ? '（自定义）' : '' }}
                    </option>
                  </select>
                </label>
                <label class="field">角色音色
                  <select v-model="role.voice">
                    <option v-for="v in voiceOptions" :key="v.style || v.id" :value="v.style || v.id">
                      {{ v.label || v.style }}
                    </option>
                  </select>
                </label>
              </div>
              <label class="field" style="margin-top: 10px;">人设与发言侧重点
                <textarea v-model="role.persona" rows="2" placeholder="如：聚焦高并发系统稳定性，擅长顺着回答里的薄弱环节连续追问"></textarea>
              </label>
            </div>
          </div>
        </div>

        <!-- 第 3 步：流程、背景与工具 -->
        <div v-else-if="stepIndex === 2" key="d2" class="step-panel">
          <div class="form-card">
            <div class="card-head-row">
              <span class="field-label" style="margin-bottom:0">对话阶段流程<span class="optional">自定义各阶段名称与短标签（2–6 步）</span></span>
              <div class="stage-head-actions">
                <button class="ghost-button slim-btn" type="button" @click="resetDefaultStages">恢复默认阶段</button>
                <button v-if="form.stages.length < 6" class="ghost-button slim-btn" type="button" @click="addStage">
                  <AppIcon name="plus" :size="13" />添加阶段
                </button>
              </div>
            </div>
            <div class="stage-list">
              <div v-for="(st, idx) in form.stages" :key="st.id || idx" class="stage-edit-row">
                <span class="stage-num">{{ idx + 1 }}</span>
                <input v-model="st.shortTag" class="stage-tag-input" placeholder="短标签" maxlength="6" />
                <input v-model="st.label" class="stage-label-input" placeholder="阶段完整名称（如：深度追问）" maxlength="32" />
                <button
                  v-if="form.stages.length > 2"
                  type="button"
                  class="role-del-btn"
                  aria-label="删除阶段"
                  @click="form.stages.splice(idx, 1)"
                ><AppIcon name="x" :size="13" /></button>
              </div>
            </div>
          </div>

          <div class="form-card">
            <label class="field">场景背景知识<small>（注入所有 AI 角色共享上下文）</small>
              <textarea v-model="form.backgroundContext" rows="3" placeholder="输入公司背景、技术约束、行业数据或争议焦点..."></textarea>
            </label>
            <label class="field" style="margin-top: 10px;">推荐地道表达<small>（每行一条或逗号分隔）</small>
              <textarea v-model="form.keyExpressionsText" rows="3" placeholder="high-stakes trade-off&#10;cross-functional alignment"></textarea>
            </label>
          </div>

          <div class="form-card">
            <span class="field-label">启用工具<span class="optional">按需开关，运行时真实生效</span></span>
            <div class="tool-checks">
              <label
                v-for="tool in DEBATE_TOOLS"
                :key="tool.id"
                class="tool-check"
                :data-tip="`${tool.name}：${tool.desc}`"
                :title="`${tool.name}：${tool.desc}`"
              >
                <input v-model="form.tools" type="checkbox" :value="tool.id" />{{ tool.name }}
              </label>
            </div>
          </div>
        </div>

        <!-- 第 4 步：资料与预览 -->
        <div v-else key="d3" class="step-panel">
          <div class="form-card">
            <div class="doc-head-row">
              <span class="field-label">关联个人知识库文档<span class="optional">可选 · 多角色追问时自动检索（最多 5 份）</span></span>
              <label class="ghost-button slim-upload" :class="{ disabled: uploadingDoc }">
                <AppIcon name="upload" :size="13" />{{ uploadingDoc ? '上传解析中…' : '上传资料' }}
                <input
                  type="file"
                  accept=".md,.markdown,.txt,.pdf"
                  class="hidden-input"
                  :disabled="uploadingDoc"
                  @change="handlePersonalDocUpload"
                />
              </label>
            </div>
            <div v-if="personalDocs.length" class="doc-check-list">
              <button
                v-for="doc in personalDocs"
                :key="doc.id"
                type="button"
                class="doc-check-pill"
                :class="{ checked: form.knowledgeDocIds.includes(doc.id) }"
                @click="toggleDoc(doc.id)"
              >
                <AppIcon :name="form.knowledgeDocIds.includes(doc.id) ? 'check' : 'book-open'" :size="12" />
                <span>{{ doc.filename || doc.title || `文档 #${doc.id}` }}</span>
              </button>
            </div>
            <p v-else class="field-hint">当前暂无已上传的个人知识库文档，可直接点击右上角「上传资料」（支持 Markdown、TXT、PDF）。</p>
          </div>

          <div class="form-card">
            <span class="field-label">场景包摘要预览</span>
            <div class="preview-summary">
              <div class="preview-row"><span>场景类型</span><b>{{ form.sceneType === 'panel' ? '多人对话 / 群面 (Panel)' : '正反辩论对抗 (Debate)' }}</b></div>
              <div class="preview-row"><span>场景名称</span><b>{{ form.titleZh || '未填写' }}</b></div>
              <div class="preview-row"><span>英文议题</span><b>{{ form.motionEn || '未填写' }}</b></div>
              <div class="preview-row"><span>AI 角色阵容</span><b>{{ rolesPreviewLabel }}</b></div>
              <div class="preview-row"><span>流程阶段</span><b>{{ form.stages.map(s => s.label).filter(Boolean).join(' → ') || '默认四阶段' }}</b></div>
              <div class="preview-row"><span>启用工具</span><b>{{ form.tools.length }} 项</b></div>
              <div class="preview-row"><span>关联知识库</span><b>{{ form.knowledgeDocIds.length }} 份文档</b></div>
            </div>
          </div>
        </div>
      </transition>
    </div>

    <div class="editor-footer">
      <button class="ghost-button" type="button" :disabled="stepIndex === 0" @click="goStep(stepIndex - 1)">
        <AppIcon name="chevron-left" :size="14" />上一步
      </button>
      <span class="step-indicator">{{ stepIndex + 1 }} / {{ STEPS.length }} · {{ STEPS[stepIndex].label }}</span>
      <button
        v-if="stepIndex < STEPS.length - 1"
        class="primary-button slim"
        type="button"
        @click="goStep(stepIndex + 1)"
      >
        下一步<AppIcon name="arrow-right" :size="14" />
      </button>
      <button
        v-else
        class="primary-button slim"
        type="button"
        :disabled="saving"
        @click="saveDebate"
      >
        {{ saving ? '保存中...' : (isEdit ? '保存修改' : '创建多角色场景') }}
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
import { usePageLoading } from '../app/loading'
import { http } from '../api/http'
import { listPersonalDocuments, uploadPersonalKnowledge } from '../api/scenes'
import { FALLBACK_AVATARS, FALLBACK_VOICES, listAvatars, listVoices } from '../api/avatar'
import {
  createDebateTopic,
  debateCoverUrl,
  generateDebateTopicDraft,
  listDebateTopics,
  removeDebateCover,
  updateDebateTopic,
  uploadDebateCover,
} from '../api/debate'

const STEPS = [
  { key: 'basic', label: '基本信息' },
  { key: 'persona', label: '角色与立场' },
  { key: 'tools', label: '阶段与工具' },
  { key: 'knowledge', label: '资料与预览' },
]

// 与 1v1 对话共享通用工具能力，并保留多角色专属评分/核查工具
const DEBATE_TOOLS = [
  { id: 'search_knowledge', name: '知识检索', desc: '在场景背景与个人知识库文档中检索论据与细节' },
  { id: 'rebuttal_hint', name: '回复与表达提示', desc: '为学习者提供英文回复切入点与地道高分句式' },
  { id: 'lookup_word', name: '词汇查询', desc: '辅助解释专业术语、核心词汇与地道表达用法' },
  { id: 'calculate_expression', name: '精确计算', desc: '支持预算评审、商业论证中的数值核算与对比' },
  { id: 'add_review_task', name: '加入复习', desc: '将本轮地道表达或薄弱点自动沉淀至 SM-2 复习队列' },
  { id: 'judge_score', name: '实时评估评分', desc: '每轮自动评估逻辑、回应力、流畅度并动态调整认可度/胜率' },
  { id: 'fact_check', name: '事实核查追问', desc: '强化核查发言中的数据、技术细节或论证逻辑漏洞' },
]

const AVATAR_VOICE_MAP = {
  sarah_2d: 'sonia',
  claire_2d: 'emma',
  emily_2d: 'aria',
  david_2d: 'andrew',
  leo_2d: 'brian',
}

const DEFAULT_DEBATE_ROLES = () => [
  { id: 'moderator', roleType: 'moderator', name: 'Brian', title: '主持人', avatarId: 'david_2d', voice: 'brian', persona: '把控交锋节奏与议程推进的中立主持人。' },
  { id: 'opponent', roleType: 'opponent', name: 'Sonia', title: '对手辩手', avatarId: 'sarah_2d', voice: 'sonia', persona: '条理清晰、善于针对核心预设提出反驳质询。' },
  { id: 'judge', roleType: 'judge', name: 'Andrew', title: '特邀评委', avatarId: 'leo_2d', voice: 'andrew', persona: '客观评估双方逻辑严密性与临场举证质量。' },
]

const DEFAULT_PANEL_ROLES = () => [
  { id: 'tech_lead', roleType: 'interviewer', name: 'Claire', title: '技术 / 业务负责人', avatarId: 'claire_2d', voice: 'emma', persona: '专注核心方案架构与量化落地效果，追问具体且直接。' },
  { id: 'hrbp', roleType: 'interviewer', name: 'Emily', title: '协同方 / HRBP', avatarId: 'emily_2d', voice: 'aria', persona: '聚焦团队协作冲突、跨部门推动阻力与失败复盘诚实度。' },
  { id: 'vp', roleType: 'judge', name: 'Leo', title: '委员会决策官', avatarId: 'leo_2d', voice: 'brian', persona: '站在业务全局 ROI 与长期可控视角做最终委员会评估。' },
]

const DEFAULT_DEBATE_STAGES = () => [
  { id: 'opening', shortTag: '立论', label: '开篇立论' },
  { id: 'cross', shortTag: '质询', label: '交叉质询' },
  { id: 'rebuttal', shortTag: '攻防', label: '焦点攻防' },
  { id: 'closing', shortTag: '裁决', label: '总结裁决' },
]

const DEFAULT_PANEL_STAGES = () => [
  { id: 'opening', shortTag: '陈述', label: '自我陈述' },
  { id: 'deep_dive', shortTag: '追问', label: '深度追问' },
  { id: 'pressure', shortTag: '挑战', label: '压力挑战' },
  { id: 'summary', shortTag: '评估', label: '委员会评估' },
]

const route = useRoute()
const router = useRouter()
const finishLoading = usePageLoading()
const isEdit = computed(() => route.name === 'debate-edit')

const stepIndex = ref(0)
const stepDirection = ref(1)
const aiIdea = ref('')
const generating = ref(false)
const saving = ref(false)
const formError = ref('')
const toast = ref('')
const personalDocs = ref([])
const uploadingDoc = ref(false)
const avatarOptions = ref([...FALLBACK_AVATARS])
const voiceOptions = ref([...FALLBACK_VOICES])
const uploadingCover = ref(false)
const hasServerCover = ref(false)
const coverVersion = ref(0)
const pendingCoverFile = ref(null)
const pendingCoverUrl = ref('')
let toastTimer = null

const coverPreviewUrl = computed(() => {
  if (pendingCoverUrl.value) return pendingCoverUrl.value
  if (isEdit.value && hasServerCover.value) return debateCoverUrl(route.params.id, coverVersion.value)
  return ''
})

const rolesPreviewLabel = computed(() => {
  const list = (form.value.roles || []).filter((r) => r.name?.trim())
  if (!list.length) return '未配置'
  return list.map((r) => `${r.name.trim()}${r.title?.trim() ? `(${r.title.trim()})` : ''}`).join(' · ')
})

const form = ref({
  sceneType: 'debate',
  userRoleLabel: '候选人 / 主讲人',
  titleZh: '',
  motionEn: '',
  category: 'tech',
  difficulty: 'intermediate',
  duration: '8 分钟',
  defaultStyle: 'balanced',
  proSummary: '',
  conSummary: '',
  roles: DEFAULT_DEBATE_ROLES(),
  stages: DEFAULT_DEBATE_STAGES(),
  backgroundContext: '',
  keyExpressionsText: '',
  knowledgeDocIds: [],
  tools: ['search_knowledge', 'rebuttal_hint', 'judge_score'],
})

function notify(msg) {
  toast.value = msg
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = '' }, 2600)
}

function goBack() {
  if (route.query.from === 'debate') {
    router.push({ name: 'debate' })
  } else {
    router.push({ name: 'scenes', query: { tab: 'debate' } })
  }
}

function switchSceneType(type) {
  if (form.value.sceneType === type) return
  form.value.sceneType = type
  if (!isEdit.value) {
    form.value.roles = type === 'panel' ? DEFAULT_PANEL_ROLES() : DEFAULT_DEBATE_ROLES()
    form.value.stages = type === 'panel' ? DEFAULT_PANEL_STAGES() : DEFAULT_DEBATE_STAGES()
  }
}

function addRole() {
  if (form.value.roles.length >= 4) return
  form.value.roles.push({
    id: `role_${Date.now().toString(36).slice(-4)}`,
    roleType: form.value.sceneType === 'panel' ? 'interviewer' : 'opponent',
    name: '',
    title: '',
    avatarId: 'sarah_2d',
    voice: 'sonia',
    persona: '',
  })
}

function onRoleAvatarChange(role) {
  if (AVATAR_VOICE_MAP[role.avatarId]) {
    role.voice = AVATAR_VOICE_MAP[role.avatarId]
  }
}

function addStage() {
  if (form.value.stages.length >= 6) return
  form.value.stages.push({ id: `stage_${form.value.stages.length + 1}`, shortTag: '', label: '' })
}

function resetDefaultStages() {
  form.value.stages = form.value.sceneType === 'panel' ? DEFAULT_PANEL_STAGES() : DEFAULT_DEBATE_STAGES()
}

function goStep(idx) {
  if (idx < 0 || idx >= STEPS.length) return
  stepDirection.value = idx >= stepIndex.value ? 1 : -1
  stepIndex.value = idx
}

function toggleDoc(docId) {
  const list = [...form.value.knowledgeDocIds]
  const pos = list.indexOf(docId)
  if (pos >= 0) list.splice(pos, 1)
  else if (list.length < 5) list.push(docId)
  form.value.knowledgeDocIds = list
}

async function handlePersonalDocUpload(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file || uploadingDoc.value) return
  uploadingDoc.value = true
  try {
    const { data } = await uploadPersonalKnowledge(file)
    const uploaded = data?.document || data
    const { data: listData } = await listPersonalDocuments()
    if (Array.isArray(listData?.documents)) {
      personalDocs.value = listData.documents
    } else if (uploaded?.id) {
      personalDocs.value = [uploaded, ...personalDocs.value]
    }
    const newId = uploaded?.id
    if (newId && !form.value.knowledgeDocIds.includes(newId) && form.value.knowledgeDocIds.length < 5) {
      form.value.knowledgeDocIds = [...form.value.knowledgeDocIds, newId]
    }
    notify(`已上传并关联「${file.name}」`)
  } catch (err) {
    notify(err?.message || '上传个人知识库文档失败')
  } finally {
    uploadingDoc.value = false
  }
}

function clearPendingCover() {
  if (pendingCoverUrl.value) URL.revokeObjectURL(pendingCoverUrl.value)
  pendingCoverUrl.value = ''
  pendingCoverFile.value = null
}

async function handleCover(event) {
  const file = event.target?.files?.[0]
  event.target.value = ''
  if (!file) return
  if (file.size > 5 * 1024 * 1024) {
    notify('封面图不能超过 5 MB')
    return
  }
  if (!isEdit.value) {
    clearPendingCover()
    pendingCoverFile.value = file
    pendingCoverUrl.value = URL.createObjectURL(file)
    return
  }
  uploadingCover.value = true
  try {
    await uploadDebateCover(route.params.id, file)
    hasServerCover.value = true
    coverVersion.value += 1
    notify('封面已更新')
  } catch (err) {
    notify(err?.message || '上传封面失败')
  } finally {
    uploadingCover.value = false
  }
}

async function doRemoveCover() {
  uploadingCover.value = true
  try {
    await removeDebateCover(route.params.id)
    hasServerCover.value = false
    coverVersion.value += 1
    notify('已移除封面')
  } catch (err) {
    notify(err?.message || '移除封面失败')
  } finally {
    uploadingCover.value = false
  }
}

async function handleGenerateDraft() {
  const idea = aiIdea.value.trim()
  if (!idea || generating.value) return
  generating.value = true
  formError.value = ''
  try {
    const { data } = await generateDebateTopicDraft(idea, form.value.sceneType)
    const d = data?.draft
    if (d) {
      form.value = {
        ...form.value,
        sceneType: d.sceneType || form.value.sceneType,
        userRoleLabel: d.userRoleLabel || form.value.userRoleLabel || '候选人 / 主讲人',
        titleZh: d.titleZh || '',
        motionEn: d.motionEn || '',
        category: d.category || 'society',
        difficulty: d.difficulty || 'intermediate',
        duration: d.duration || '8 分钟',
        defaultStyle: d.defaultStyle || 'balanced',
        proSummary: d.proSummary || '',
        conSummary: d.conSummary || '',
        roles: Array.isArray(d.roles) && d.roles.length
          ? d.roles.map((r, idx) => ({
              id: r.id || `role_${idx + 1}`,
              roleType: r.roleType || (form.value.sceneType === 'panel' ? 'interviewer' : 'opponent'),
              name: r.name || `Role ${idx + 1}`,
              title: r.title || '',
              avatarId: r.avatarId || 'sarah_2d',
              voice: r.voice || AVATAR_VOICE_MAP[r.avatarId] || 'sonia',
              persona: r.persona || '',
            }))
          : form.value.roles,
        stages: Array.isArray(d.stages) && d.stages.length
          ? d.stages.map((s, idx) => ({
              id: s.id || `stage_${idx + 1}`,
              shortTag: s.shortTag || '',
              label: s.label || '',
            }))
          : form.value.stages,
        backgroundContext: d.backgroundContext || '',
        keyExpressionsText: Array.isArray(d.keyExpressions) ? d.keyExpressions.join('\n') : '',
      }
      notify('已生成多角色场景参数，可继续在各步骤微调')
    }
  } catch (err) {
    formError.value = err?.message || 'AI 生成失败，请先登录后重试'
  } finally {
    generating.value = false
  }
}

async function saveDebate() {
  if (!form.value.titleZh.trim() || !form.value.motionEn.trim()) {
    formError.value = '请在第 1 步填写中文场景名称与英文议题'
    goStep(0)
    return
  }
  const cleanRoles = (form.value.roles || [])
    .filter((r) => r.name?.trim())
    .slice(0, 4)
    .map((r, idx) => {
      const avId = r.avatarId || 'sarah_2d'
      return {
        id: r.id?.trim() || `role_${idx + 1}`,
        roleType: r.roleType || (form.value.sceneType === 'panel' ? 'interviewer' : 'opponent'),
        name: r.name.trim(),
        title: (r.title || '').trim(),
        avatarId: avId,
        voice: r.voice || AVATAR_VOICE_MAP[avId] || 'sonia',
        persona: (r.persona || '').trim(),
      }
    })
  if (cleanRoles.length < 2) {
    formError.value = '请至少填写 2 个 AI 角色名字（第 2 步）'
    goStep(1)
    return
  }
  const primaryOpp = cleanRoles.find((r) => r.roleType === 'opponent')
    || cleanRoles.find((r) => r.roleType === 'interviewer')
    || cleanRoles[0]
  const cleanStages = (form.value.stages || [])
    .filter((s) => s.label?.trim())
    .slice(0, 6)
    .map((s, idx) => ({
      id: s.id?.trim() || `stage_${idx + 1}`,
      shortTag: (s.shortTag || '').trim() || s.label.trim().slice(0, 2),
      label: s.label.trim(),
    }))

  saving.value = true
  formError.value = ''
  const payload = {
    sceneType: form.value.sceneType,
    userRoleLabel: (form.value.userRoleLabel || '').trim() || '候选人 / 主讲人',
    titleZh: form.value.titleZh.trim(),
    motionEn: form.value.motionEn.trim(),
    category: form.value.category,
    difficulty: form.value.difficulty,
    duration: form.value.duration,
    defaultStyle: form.value.defaultStyle,
    proSummary: form.value.proSummary.trim(),
    conSummary: form.value.conSummary.trim(),
    backgroundContext: form.value.backgroundContext.trim(),
    keyExpressions: form.value.keyExpressionsText
      .split(/\n|[,，]/)
      .map((s) => s.trim())
      .filter(Boolean),
    opponentName: primaryOpp.name,
    opponentTitle: primaryOpp.title || '对手辩手',
    opponentAvatarId: primaryOpp.avatarId,
    opponentVoice: primaryOpp.voice,
    opponentPersona: primaryOpp.persona,
    roles: cleanRoles,
    stages: cleanStages,
    knowledgeDocIds: form.value.knowledgeDocIds,
    tools: [...form.value.tools],
  }
  try {
    if (isEdit.value) {
      await updateDebateTopic(route.params.id, payload)
      notify('多角色场景已更新')
    } else {
      const { data } = await createDebateTopic(payload)
      const createdId = data?.topic?.id
      if (createdId && pendingCoverFile.value) {
        await uploadDebateCover(createdId, pendingCoverFile.value).catch(() => {})
        clearPendingCover()
      }
      notify('多角色场景创建成功')
    }
    goBack()
  } catch (err) {
    formError.value = err?.message || '保存失败，请先登录后重试'
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    const [docsRes, topicsRes, avRes, vRes] = await Promise.allSettled([
      http.get('/knowledge/personal'),
      isEdit.value ? listDebateTopics() : Promise.resolve(null),
      listAvatars(),
      listVoices(),
    ])
    if (avRes.status === 'fulfilled' && Array.isArray(avRes.value) && avRes.value.length) {
      avatarOptions.value = avRes.value
    }
    if (vRes.status === 'fulfilled' && Array.isArray(vRes.value) && vRes.value.length) {
      voiceOptions.value = vRes.value
    }
    if (docsRes.status === 'fulfilled' && Array.isArray(docsRes.value.data?.documents)) {
      personalDocs.value = docsRes.value.data.documents
    }
    if (isEdit.value && topicsRes.status === 'fulfilled' && topicsRes.value) {
      const target = (topicsRes.value.data?.items || []).find((t) => t.id === route.params.id)
      if (!target) {
        formError.value = '未找到该多角色场景'
      } else if (target.isBuiltin || !target.canManage) {
        notify('内置或他人多角色场景不可直接编辑')
        goBack()
        return
      } else {
        hasServerCover.value = Boolean(target.coverUrl)
        const sceneType = target.sceneType === 'panel' ? 'panel' : 'debate'
        form.value = {
          sceneType,
          userRoleLabel: target.userRoleLabel || '候选人 / 主讲人',
          titleZh: target.titleZh || '',
          motionEn: target.motionEn || '',
          category: target.category || 'tech',
          difficulty: target.difficulty || 'intermediate',
          duration: target.duration || '8 分钟',
          defaultStyle: target.defaultStyle || 'balanced',
          proSummary: target.proSummary || '',
          conSummary: target.conSummary || '',
          roles: Array.isArray(target.roles) && target.roles.length
            ? target.roles.map((r) => ({ ...r }))
            : (sceneType === 'panel' ? DEFAULT_PANEL_ROLES() : DEFAULT_DEBATE_ROLES()),
          stages: Array.isArray(target.stages) && target.stages.length
            ? target.stages.map((s) => ({ ...s }))
            : (sceneType === 'panel' ? DEFAULT_PANEL_STAGES() : DEFAULT_DEBATE_STAGES()),
          backgroundContext: target.backgroundContext || '',
          keyExpressionsText: Array.isArray(target.keyExpressions) ? target.keyExpressions.join('\n') : '',
          knowledgeDocIds: Array.isArray(target.knowledgeDocIds) ? [...target.knowledgeDocIds] : [],
          tools: Array.isArray(target.tools) ? [...target.tools] : ['search_knowledge', 'rebuttal_hint', 'judge_score'],
        }
      }
    }
  } finally {
    finishLoading()
  }
})
</script>

<style scoped>
.editor-page { flex: 1; min-height: 0; display: flex; flex-direction: column; padding: 20px 28px 0; overflow: hidden; background: #faf9ff; }
.editor-topbar { display: flex; flex: 0 0 auto; align-items: center; justify-content: space-between; gap: 14px; margin-bottom: 14px; }
.back-button { display: inline-flex; align-items: center; gap: 4px; height: 34px; padding: 0 13px 0 9px; border: 1.5px solid #e9e5f1; border-bottom-width: 3px; border-radius: 10px; background: #fff; color: var(--ink-soft); font-size: 13.5px; font-weight: 600; }
.topbar-balance { width: 74px; flex: 0 0 auto; }

.steps { display: flex; align-items: center; gap: 4px; margin: 0; padding: 0; list-style: none; }
.step-item { display: inline-flex; align-items: center; gap: 7px; height: 33px; padding: 0 13px; border: 0; border-radius: 11px; background: transparent; color: var(--muted); font-size: 13.5px; font-weight: 600; }
.step-item.active { background: #eee8ff; color: #694fc1; }
.step-dot { display: grid; width: 23px; height: 23px; place-items: center; border-radius: 50%; background: #f0edfa; color: var(--muted); font-size: 11px; font-weight: 700; }
.step-item.active .step-dot { background: #8b73dd; color: #fff; box-shadow: inset 0 -2px 0 #6951b8; }
.step-item.done .step-dot { background: #e3ecf9; color: #3d6bc4; }

.error-panel { flex: 0 0 auto; width: 100%; max-width: 780px; margin: 0 auto 14px; padding: 12px 15px; border: 1px solid #f0d9dd; border-radius: 12px; background: #fdf7f8; }
.error-title { display: flex; align-items: center; gap: 6px; margin: 0; color: var(--danger); font-size: 13.5px; font-weight: 600; }

.step-viewport { flex: 1; min-height: 0; overflow-y: auto; margin: 0 -28px; padding: 2px 28px 22px; }
.step-panel { display: flex; flex-direction: column; gap: 18px; width: 100%; max-width: 780px; margin: 0 auto; }

.ai-draft-card {
  padding: 16px 18px;
  border-radius: 16px;
  border: 1.5px solid #dfd6f6;
  border-bottom: 4px solid #cfc1f0;
  background: linear-gradient(135deg, #f8f5ff 0%, #ffffff 100%);
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.ai-draft-head { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
.ai-draft-head strong { display: inline-flex; align-items: center; gap: 6px; font-size: 13.5px; color: #5b44b6; }
.ai-draft-head span { font-size: 12px; color: #6b6480; }
.ai-draft-row { display: flex; gap: 10px; }
.ai-draft-row input {
  flex: 1;
  height: 38px;
  padding: 0 12px;
  border: 1.5px solid #dfd6f6;
  border-radius: 11px;
  background: #ffffff;
  font-size: 13px;
  color: #393451;
}

.form-card {
  display: flex;
  flex-direction: column;
  gap: 15px;
  padding: 22px;
  border: 1.5px solid #ebe7f5;
  border-bottom: 4px solid #e5def1;
  border-radius: 17px;
  background: #fff;
}

.field { display: block; color: var(--ink-soft); font-size: 13px; font-weight: 500; }
.field small { margin-left: 4px; color: var(--faint); font-size: 12px; font-weight: 400; }
.field-label { display: block; margin-bottom: 7px; color: var(--ink-soft); font-size: 13px; font-weight: 500; }
.optional { margin-left: 7px; color: var(--muted); font-size: 12px; font-weight: 400; }
.field input, .field textarea, .field select {
  display: block;
  width: 100%;
  margin-top: 6px;
  padding: 9px 12px;
  border: 1px solid #e0e1e9;
  border-radius: 11px;
  outline: none;
  background: #fff;
  color: var(--ink);
  font-size: 14px;
  font-family: inherit;
}
.field textarea { resize: vertical; line-height: 1.6; }
.field select {
  appearance: none;
  -webkit-appearance: none;
  cursor: pointer;
  background-image: url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%237b8095' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 11px center;
  padding-right: 32px;
}
.field input:focus, .field textarea:focus, .field select:focus { border-color: var(--brand); box-shadow: 0 0 0 3px rgba(98, 101, 232, .12); }
.field-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.field-grid.three { grid-template-columns: 1fr 1fr 1fr; }
.field-grid.four { grid-template-columns: repeat(4, 1fr); }
.field-hint { margin: 4px 0 0; color: var(--muted); font-size: 12.5px; line-height: 1.6; }

.scene-type-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.scene-type-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 5px;
  padding: 14px 16px;
  border: 1.5px solid #e7e2f4;
  border-bottom: 3px solid #dcd5ee;
  border-radius: 14px;
  background: #faf9ff;
  text-align: left;
  cursor: pointer;
  transition: border-color .15s, background .15s, transform .12s;
}
.scene-type-card strong { display: inline-flex; align-items: center; gap: 6px; font-size: 13.5px; font-weight: 700; color: #3d3659; }
.scene-type-card span { font-size: 12px; line-height: 1.5; color: #756e8c; }
.scene-type-card.active {
  border-color: #8067d1;
  border-bottom-color: #6951b8;
  background: #f2edff;
}
.scene-type-card.active strong { color: #5b44b6; }

.card-head-row { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 10px; }
.stage-head-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.ghost-button.slim-btn { min-height: 30px; height: 30px; padding: 0 12px; font-size: 12.5px; border-radius: 9px; }

.sub-role-card {
  padding: 14px;
  border: 1.5px solid #ebe7f5;
  border-radius: 13px;
  background: #fcfbff;
}
.sub-role-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.role-badge {
  display: inline-flex; align-items: center; height: 22px; padding: 0 9px;
  border-radius: 999px; background: #ede7fd; color: #5b44b6; font-size: 11.5px; font-weight: 700;
}
.role-del-btn {
  display: grid; place-items: center; width: 26px; height: 26px;
  border: 1px solid #ece7f4; border-radius: 7px; background: #fff; color: #78728c; cursor: pointer;
}
.role-del-btn:hover { background: #fbf1f2; border-color: #f0d0d5; color: var(--danger); }

.stage-list { display: flex; flex-direction: column; gap: 8px; }
.stage-edit-row { display: grid; grid-template-columns: 28px 110px 1fr 28px; gap: 8px; align-items: center; }
.stage-num {
  display: grid; place-items: center; width: 24px; height: 24px; border-radius: 50%;
  background: #efeafc; color: #5b44b6; font-size: 12px; font-weight: 700;
}
.stage-tag-input, .stage-label-input {
  padding: 8px 11px; border: 1px solid #e0e1e9; border-radius: 9px; outline: none;
  background: #fff; color: var(--ink); font-size: 13.5px; font-family: inherit;
}
.stage-tag-input:focus, .stage-label-input:focus { border-color: var(--brand); }

.doc-head-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.doc-head-row .field-label { margin-bottom: 0; }
.slim-upload { flex: 0 0 auto; min-height: 32px; padding: 0 12px; font-size: 12.5px; cursor: pointer; }
.slim-upload.disabled { opacity: 0.6; pointer-events: none; }
.doc-check-list { display: flex; flex-wrap: wrap; gap: 8px; }
.doc-check-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 999px;
  border: 1.5px solid #e6e1f2;
  background: #ffffff;
  color: #5a5572;
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
}
.doc-check-pill.checked { border-color: #8067d1; background: #f3effd; color: #5a42b3; }

.cover-row { display: flex; align-items: flex-start; gap: 18px; }
.cover-preview { display: grid; flex: 0 0 auto; width: 200px; height: 113px; place-items: center; overflow: hidden; border: 1px dashed #d9dbe8; border-radius: 10px; background: #f7f8fc; }
.cover-preview img { width: 100%; height: 100%; object-fit: cover; display: block; }
.cover-placeholder { display: grid; justify-items: center; gap: 6px; color: var(--faint); font-size: 12px; }
.cover-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; flex: 1; padding-top: 4px; }
.cover-actions .field-hint { flex: 1 1 100%; margin: 0; }
.hidden-input { position: absolute; width: 0; height: 0; opacity: 0; pointer-events: none; }

.tool-checks { display: flex; flex-wrap: wrap; gap: 7px; }
.tool-check { position: relative; display: inline-flex; flex: 0 0 auto; align-items: center; gap: 6px; height: 29px; padding: 0 12px; border: 1px solid var(--line); border-radius: 7px; background: var(--surface); color: var(--ink-soft); font-size: 12.5px; white-space: nowrap; cursor: help; transition: border-color .15s, background .15s, color .15s; }
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

.preview-summary { display: flex; flex-direction: column; gap: 8px; }
.preview-row { display: flex; align-items: baseline; justify-content: space-between; gap: 16px; padding: 8px 12px; border-radius: 10px; background: #faf8ff; font-size: 13px; }
.preview-row span { color: var(--muted); flex: 0 0 auto; }
.preview-row b { color: var(--ink); font-weight: 600; text-align: right; word-break: break-word; }

.editor-footer {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: space-between;
  margin: 0 -28px;
  padding: 12px 28px;
  border-top: 1px solid #ebe7f5;
  background: #fbfaff;
}
.step-indicator { color: var(--muted); font-size: 12.5px; white-space: nowrap; }
.primary-button.slim, .ghost-button { width: auto; flex: 0 0 auto; margin-top: 0; min-height: 38px; height: 38px; border-radius: 12px; font-weight: 650; display: inline-flex; align-items: center; justify-content: center; gap: 6px; padding: 0 18px; white-space: nowrap; }
.primary-button.slim { border: 1.5px solid #8067d1; border-bottom: 4px solid #6951b8; background: #8b73dd; color: #fff; }
.ghost-button { border: 1.5px solid #e9e5f1; border-bottom-width: 3px; background: #fff; color: var(--ink-soft); }
.ghost-button:disabled { opacity: .5; cursor: default; }

.toast { position: fixed; top: 58px; left: 50%; z-index: 50; padding: 9px 16px; border-radius: 9px; background: #2b2d4e; color: #fff; font-size: 13.5px; transform: translateX(-50%); }
.slide-left-enter-active, .slide-left-leave-active,
.slide-right-enter-active, .slide-right-leave-active { transition: opacity .18s ease, transform .18s ease; }
.slide-left-enter-from { opacity: 0; transform: translateX(18px); }
.slide-left-leave-to { opacity: 0; transform: translateX(-14px); }
.slide-right-enter-from { opacity: 0; transform: translateX(-18px); }
.slide-right-leave-to { opacity: 0; transform: translateX(14px); }

@media (max-width: 900px) {
  .field-grid, .field-grid.three, .field-grid.four, .scene-type-grid { grid-template-columns: 1fr; }
}
</style>
