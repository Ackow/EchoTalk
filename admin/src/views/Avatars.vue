<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  batchDeleteAvatarPreferences,
  batchDeleteAvatarPresets,
  batchUpdateAvatarPresetsPublic,
  deleteAvatarPreference,
  deleteAvatarPreset,
  fetchAvatarCatalog,
  fetchAvatarPreferences,
  fetchAvatarPresets,
  fetchScenes,
  fetchUsers,
  updateAvatarPreset,
  upsertAvatarPreference,
} from '../api/admin'

const activeTab = ref('presets')
const loadingPresets = ref(false)
const loadingCatalog = ref(false)
const loadingPrefs = ref(false)

const presets = ref([])
const presetTotal = ref(0)
const selectedPresets = ref([])

const avatars = ref([])
const voices = ref([])
const prefs = ref([])
const total = ref(0)
const selectedPrefs = ref([])

const userOptions = ref([])
const sceneOptions = ref([])

const presetQuery = reactive({
  q: '',
  is_builtin: '',
  is_public: '',
  owner_id: undefined,
  page: 1,
  page_size: 20,
})

const query = reactive({
  user_id: undefined,
  scene_id: undefined,
  avatar_id: '',
  voice_style: '',
  page: 1,
  page_size: 20,
})

const presetDrawerVisible = ref(false)
const presetForm = reactive({
  id: '',
  is_builtin: false,
  display_name: '',
  description: '',
  tagline: '',
  greeting: '',
  theme: 'violet',
  default_voice: 'emma',
  is_public: false,
  appearanceText: '',
})

const dialogVisible = ref(false)
const form = reactive({
  user_id: undefined,
  scene_id: '',
  avatar_id: 'leo_2d',
  voice_style: 'emma',
  speech_rate: 1.0,
  lip_sync_enabled: true,
})

const themeColor = {
  amber: '#d97706',
  teal: '#0d9488',
  blue: '#2563eb',
  violet: '#7c3aed',
}

function formatTime(val) {
  return val ? new Date(val).toLocaleString('zh-CN', { hour12: false }) : '-'
}

async function loadPresets() {
  loadingPresets.value = true
  try {
    const params = {
      page: presetQuery.page,
      page_size: presetQuery.page_size,
      q: presetQuery.q || undefined,
      is_builtin: presetQuery.is_builtin === '' ? undefined : presetQuery.is_builtin,
      is_public: presetQuery.is_public === '' ? undefined : presetQuery.is_public,
      owner_id: presetQuery.owner_id || undefined,
    }
    const { data } = await fetchAvatarPresets(params)
    presets.value = data.items
    presetTotal.value = data.total
  } finally {
    loadingPresets.value = false
  }
}

function handlePresetSearch() {
  presetQuery.page = 1
  loadPresets()
}

function openPresetEdit(row) {
  presetForm.id = row.id
  presetForm.is_builtin = row.is_builtin
  presetForm.display_name = row.display_name
  presetForm.description = row.description || ''
  presetForm.tagline = row.tagline || ''
  presetForm.greeting = row.greeting || ''
  presetForm.theme = row.theme || 'violet'
  presetForm.default_voice = row.default_voice || 'emma'
  presetForm.is_public = row.is_public
  presetForm.appearanceText = row.appearance ? JSON.stringify(row.appearance, null, 2) : ''
  presetDrawerVisible.value = true
}

async function savePresetEdit() {
  let appearance = undefined
  if (presetForm.appearanceText.trim()) {
    try {
      appearance = JSON.parse(presetForm.appearanceText)
    } catch {
      ElMessage.error('外观配置 JSON 格式不正确')
      return
    }
  }
  await updateAvatarPreset(presetForm.id, {
    display_name: presetForm.display_name,
    description: presetForm.description,
    tagline: presetForm.tagline,
    greeting: presetForm.greeting,
    theme: presetForm.theme,
    default_voice: presetForm.default_voice,
    is_public: presetForm.is_public,
    appearance,
  })
  ElMessage.success('数字人角色已更新')
  presetDrawerVisible.value = false
  loadPresets()
}

async function togglePresetPublic(row) {
  const nextPublic = !row.is_public
  await updateAvatarPreset(row.id, { is_public: nextPublic })
  ElMessage.success(nextPublic ? '已公开到角色市场' : '已设为私有')
  loadPresets()
}

async function handlePresetDelete(row) {
  await ElMessageBox.confirm(`确认删除数字人「${row.display_name}」吗？该操作不可恢复。`, '删除确认', {
    type: 'warning',
  })
  await deleteAvatarPreset(row.id)
  ElMessage.success('数字人已删除')
  loadPresets()
}

async function handlePresetBatchPublic(isPublic) {
  const ids = selectedPresets.value.map((r) => r.id)
  if (!ids.length) return
  const label = isPublic ? '公开到市场' : '设为私有'
  await ElMessageBox.confirm(`确认将选中的 ${ids.length} 个数字人${label}吗？`, `批量${label}`, {
    type: 'warning',
  })
  const { data } = await batchUpdateAvatarPresetsPublic(ids, isPublic)
  ElMessage.success(`已更新 ${data.updated} 个数字人状态`)
  selectedPresets.value = []
  loadPresets()
}

async function handlePresetBatchDelete() {
  const ids = selectedPresets.value.map((r) => r.id)
  if (!ids.length) return
  await ElMessageBox.confirm(`确认批量删除选中的 ${ids.length} 个数字人吗？（系统内置角色将自动跳过）`, '批量删除确认', {
    type: 'warning',
  })
  const { data } = await batchDeleteAvatarPresets(ids)
  const msg = data.skipped_builtin
    ? `已删除 ${data.deleted} 个数字人，跳过 ${data.skipped_builtin} 个内置角色`
    : `已删除 ${data.deleted} 个数字人`
  ElMessage.success(msg)
  selectedPresets.value = []
  loadPresets()
}

async function loadCatalog() {
  loadingCatalog.value = true
  try {
    const { data } = await fetchAvatarCatalog()
    avatars.value = data.avatars
    voices.value = data.voices
  } finally {
    loadingCatalog.value = false
  }
}

async function loadPrefs() {
  loadingPrefs.value = true
  try {
    const params = {
      page: query.page,
      page_size: query.page_size,
      user_id: query.user_id || undefined,
      scene_id: query.scene_id === undefined ? undefined : query.scene_id,
      avatar_id: query.avatar_id || undefined,
      voice_style: query.voice_style || undefined,
    }
    const { data } = await fetchAvatarPreferences(params)
    prefs.value = data.items
    total.value = data.total
  } finally {
    loadingPrefs.value = false
  }
}

async function loadOptions() {
  const [uRes, sRes] = await Promise.all([
    fetchUsers({ page: 1, page_size: 100 }),
    fetchScenes({ page: 1, page_size: 100 }),
  ])
  userOptions.value = uRes.data.items
  sceneOptions.value = sRes.data.items
}

function handleSearch() {
  query.page = 1
  loadPrefs()
}

function openCreate() {
  form.user_id = userOptions.value[0]?.id
  form.scene_id = ''
  form.avatar_id = avatars.value[0]?.id || 'leo_2d'
  form.voice_style = voices.value[0]?.style || 'emma'
  form.speech_rate = 1.0
  form.lip_sync_enabled = true
  dialogVisible.value = true
}

function openEdit(row) {
  form.user_id = row.user_id
  form.scene_id = row.scene_id || ''
  form.avatar_id = row.avatar_id
  form.voice_style = row.voice_style
  form.speech_rate = row.speech_rate
  form.lip_sync_enabled = row.lip_sync_enabled
  dialogVisible.value = true
}

async function submitForm() {
  if (!form.user_id) {
    ElMessage.warning('请选择用户')
    return
  }
  await upsertAvatarPreference({
    user_id: form.user_id,
    scene_id: form.scene_id || null,
    avatar_id: form.avatar_id,
    voice_style: form.voice_style,
    speech_rate: form.speech_rate,
    lip_sync_enabled: form.lip_sync_enabled,
  })
  ElMessage.success('数字人偏好配置已保存')
  dialogVisible.value = false
  loadPrefs()
  loadCatalog()
}

async function handleDelete(row) {
  await ElMessageBox.confirm(
    `确认删除用户「${row.username}」在「${row.scene_name}」的数字人配置吗？`,
    '删除确认',
    { type: 'warning' }
  )
  await deleteAvatarPreference(row.user_id, row.scene_id || '')
  ElMessage.success('配置已删除')
  loadPrefs()
  loadCatalog()
}

async function handleBatchDelete() {
  if (!selectedPrefs.value.length) return
  await ElMessageBox.confirm(
    `确认批量删除选中的 ${selectedPrefs.value.length} 条数字人配置吗？`,
    '批量删除确认',
    { type: 'warning' }
  )
  const payload = selectedPrefs.value.map((r) => ({ user_id: r.user_id, scene_id: r.scene_id || '' }))
  const { data } = await batchDeleteAvatarPreferences(payload)
  ElMessage.success(`已删除 ${data.deleted} 条配置`)
  selectedPrefs.value = []
  loadPrefs()
  loadCatalog()
}

onMounted(() => {
  loadPresets()
  loadCatalog()
  loadPrefs()
  loadOptions()
})
</script>

<template>
  <div class="page-card">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="创建的数字人" name="presets">
        <div class="filter-bar">
          <el-input
            v-model="presetQuery.q"
            placeholder="搜索角色 ID / 名称 / 简介 / 作者"
            clearable
            style="width: 240px"
            @keyup.enter="handlePresetSearch"
            @clear="handlePresetSearch"
          />
          <el-select v-model="presetQuery.is_builtin" placeholder="来源" clearable style="width: 120px" @change="handlePresetSearch">
            <el-option label="用户创作" :value="false" />
            <el-option label="系统内置" :value="true" />
          </el-select>
          <el-select v-model="presetQuery.is_public" placeholder="公开状态" clearable style="width: 130px" @change="handlePresetSearch">
            <el-option label="公开市场" :value="true" />
            <el-option label="仅自己可见" :value="false" />
          </el-select>
          <el-select v-model="presetQuery.owner_id" placeholder="按创作者筛选" clearable filterable style="width: 160px" @change="handlePresetSearch">
            <el-option v-for="u in userOptions" :key="u.id" :label="u.username" :value="u.id" />
          </el-select>
          <el-button type="primary" icon="Search" @click="handlePresetSearch">查询</el-button>
          <template v-if="selectedPresets.length">
            <el-button type="success" @click="handlePresetBatchPublic(true)">批量公开 ({{ selectedPresets.length }})</el-button>
            <el-button type="warning" @click="handlePresetBatchPublic(false)">批量私有 ({{ selectedPresets.length }})</el-button>
            <el-button type="danger" icon="Delete" @click="handlePresetBatchDelete">批量删除 ({{ selectedPresets.length }})</el-button>
          </template>
        </div>

        <el-table
          v-loading="loadingPresets"
          :data="presets"
          stripe
          border
          @selection-change="(val) => (selectedPresets = val)"
        >
          <el-table-column type="selection" width="48" />
          <el-table-column label="数字人角色" min-width="200">
            <template #default="{ row }">
              <div style="display: flex; align-items: center; gap: 10px">
                <span class="mini-badge" :style="{ backgroundColor: themeColor[row.theme] || '#7c3aed' }">
                  {{ row.display_name?.[0] || 'A' }}
                </span>
                <div>
                  <div style="font-weight: 600; color: #0f172a">{{ row.display_name }}</div>
                  <div style="font-size: 12px; color: #64748b">{{ row.id }}</div>
                </div>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="角色简介" min-width="180" show-overflow-tooltip />
          <el-table-column prop="owner_username" label="创作者" width="120" />
          <el-table-column label="来源" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="row.is_builtin ? 'primary' : 'info'" size="small">
                {{ row.is_builtin ? '系统内置' : '用户创作' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="市场状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="row.is_public ? 'success' : 'warning'" size="small">
                {{ row.is_public ? '公开' : '私有' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="default_voice" label="默认音色" width="110" align="center" />
          <el-table-column prop="usage_count" label="使用次数" width="90" align="center" />
          <el-table-column label="创建时间" width="170">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="190" fixed="right" align="center">
            <template #default="{ row }">
              <el-button type="primary" link size="small" @click="openPresetEdit(row)">编辑</el-button>
              <el-button
                type="warning"
                link
                size="small"
                :disabled="row.is_builtin"
                @click="togglePresetPublic(row)"
              >
                {{ row.is_public ? '设为私有' : '公开' }}
              </el-button>
              <el-button
                type="danger"
                link
                size="small"
                :disabled="row.is_builtin"
                @click="handlePresetDelete(row)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pagination-wrap">
          <el-pagination
            v-model:current-page="presetQuery.page"
            v-model:page-size="presetQuery.page_size"
            :total="presetTotal"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            @current-change="loadPresets"
            @size-change="handlePresetSearch"
          />
        </div>
      </el-tab-pane>

      <el-tab-pane label="用户数字人配置" name="preferences">
        <div class="filter-bar">
          <el-select v-model="query.user_id" placeholder="按用户筛选" clearable filterable style="width: 180px" @change="handleSearch">
            <el-option v-for="u in userOptions" :key="u.id" :label="u.username" :value="u.id" />
          </el-select>
          <el-select v-model="query.avatar_id" placeholder="按形象筛选" clearable style="width: 160px" @change="handleSearch">
            <el-option v-for="a in avatars" :key="a.id" :label="a.display_name" :value="a.id" />
          </el-select>
          <el-select v-model="query.voice_style" placeholder="按音色筛选" clearable style="width: 170px" @change="handleSearch">
            <el-option v-for="v in voices" :key="v.style" :label="v.label" :value="v.style" />
          </el-select>
          <el-button type="primary" icon="Search" @click="handleSearch">查询</el-button>
          <el-button
            v-if="selectedPrefs.length"
            type="danger"
            icon="Delete"
            @click="handleBatchDelete"
          >
            批量删除 ({{ selectedPrefs.length }})
          </el-button>
          <el-button type="success" icon="Plus" style="margin-left: auto" @click="openCreate">
            新增 / 分配配置
          </el-button>
        </div>

        <el-table
          v-loading="loadingPrefs"
          :data="prefs"
          stripe
          border
          @selection-change="(val) => (selectedPrefs = val)"
        >
          <el-table-column type="selection" width="48" />
          <el-table-column prop="username" label="用户" width="140" />
          <el-table-column label="适用场景" min-width="180">
            <template #default="{ row }">
              <el-tag v-if="!row.scene_id" type="info" effect="plain" size="small">跟随场景推荐</el-tag>
              <span v-else>{{ row.scene_name }} ({{ row.scene_id }})</span>
            </template>
          </el-table-column>
          <el-table-column prop="avatar_id" label="数字人形象" width="140">
            <template #default="{ row }">
              <el-tag effect="light" size="small">{{ row.avatar_id }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="voice_style" label="音色风格" width="130">
            <template #default="{ row }">
              <el-tag type="success" effect="light" size="small">{{ row.voice_style }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="speech_rate" label="语速倍率" width="100" align="center">
            <template #default="{ row }">{{ row.speech_rate.toFixed(2) }}x</template>
          </el-table-column>
          <el-table-column label="口型同步" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="row.lip_sync_enabled ? 'success' : 'info'" size="small">
                {{ row.lip_sync_enabled ? '开启' : '关闭' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="更新时间" width="180">
            <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right" align="center">
            <template #default="{ row }">
              <el-button type="primary" link size="small" @click="openEdit(row)">编辑</el-button>
              <el-button type="danger" link size="small" @click="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pagination-wrap">
          <el-pagination
            v-model:current-page="query.page"
            v-model:page-size="query.page_size"
            :total="total"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            @current-change="loadPrefs"
            @size-change="handleSearch"
          />
        </div>
      </el-tab-pane>

      <el-tab-pane label="系统数字人与音色目录" name="catalog">
        <div v-loading="loadingCatalog">
          <h4 class="section-title">内置数字人形象（{{ avatars.length }}）</h4>
          <el-row :gutter="16">
            <el-col v-for="item in avatars" :key="item.id" :xs="24" :sm="12" :lg="6" style="margin-bottom: 16px">
              <el-card shadow="hover">
                <div class="avatar-card-head">
                  <div class="avatar-badge" :style="{ backgroundColor: themeColor[item.theme] || '#3b82f6' }">
                    {{ item.display_name[0] }}
                  </div>
                  <div>
                    <div class="avatar-name">{{ item.display_name }}</div>
                    <div class="avatar-id">{{ item.id }} · {{ item.kind.toUpperCase() }}</div>
                  </div>
                </div>
                <p class="avatar-desc">{{ item.description }}</p>
                <p class="avatar-tagline">{{ item.tagline }}</p>
                <div class="avatar-foot">
                  <el-tag size="small" effect="plain">默认音色: {{ item.default_voice }}</el-tag>
                  <el-tag type="primary" size="small">已配置 {{ item.usage_count }} 次</el-tag>
                </div>
              </el-card>
            </el-col>
          </el-row>

          <h4 class="section-title" style="margin-top: 12px">可用 TTS 音色清单（{{ voices.length }}）</h4>
          <el-table :data="voices" stripe border size="small">
            <el-table-column prop="style" label="Style 标识" width="130" />
            <el-table-column prop="label" label="展示名称" min-width="180" />
            <el-table-column prop="tts_voice" label="Edge-TTS Voice" min-width="200" />
            <el-table-column prop="accent" label="口音" width="90" align="center" />
            <el-table-column prop="gender" label="性别" width="90" align="center" />
            <el-table-column prop="usage_count" label="用户配置数" width="110" align="center" />
          </el-table>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 编辑创建的数字人抽屉 -->
    <el-drawer v-model="presetDrawerVisible" :title="`编辑数字人：${presetForm.display_name}`" size="520px">
      <el-form label-width="92px" size="small">
        <el-form-item label="角色 ID">
          <el-input :model-value="presetForm.id" disabled />
        </el-form-item>
        <el-form-item label="展示名称">
          <el-input v-model="presetForm.display_name" />
        </el-form-item>
        <el-form-item label="角色简介">
          <el-input v-model="presetForm.description" />
        </el-form-item>
        <el-form-item label="个性标语">
          <el-input v-model="presetForm.tagline" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="开场问候语">
          <el-input v-model="presetForm.greeting" type="textarea" :rows="2" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="主题色">
              <el-select v-model="presetForm.theme" style="width: 100%">
                <el-option label="紫罗兰 (violet)" value="violet" />
                <el-option label="琥珀橙 (amber)" value="amber" />
                <el-option label="青绿 (teal)" value="teal" />
                <el-option label="海蓝 (blue)" value="blue" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="默认音色">
              <el-select v-model="presetForm.default_voice" style="width: 100%">
                <el-option v-for="v in voices" :key="v.style" :label="v.label" :value="v.style" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="公开市场">
          <el-switch v-model="presetForm.is_public" :disabled="presetForm.is_builtin" />
        </el-form-item>
        <el-form-item label="外观 JSON">
          <el-input
            v-model="presetForm.appearanceText"
            type="textarea"
            :rows="10"
            placeholder="可选，JSON 格式的外观参数"
            style="font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="presetDrawerVisible = false">取消</el-button>
        <el-button type="primary" @click="savePresetEdit">保存修改</el-button>
      </template>
    </el-drawer>

    <!-- 编辑 / 新增偏好弹窗 -->
    <el-dialog v-model="dialogVisible" title="数字人偏好配置" width="460px">
      <el-form label-width="96px">
        <el-form-item label="目标用户">
          <el-select v-model="form.user_id" filterable style="width: 100%">
            <el-option v-for="u in userOptions" :key="u.id" :label="u.username" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="适用场景">
          <el-select v-model="form.scene_id" filterable style="width: 100%">
            <el-option label="跟随场景推荐（全局默认）" value="" />
            <el-option v-for="s in sceneOptions" :key="s.id" :label="`${s.name} (${s.id})`" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="数字人形象">
          <el-select v-model="form.avatar_id" style="width: 100%">
            <el-option v-for="a in avatars" :key="a.id" :label="a.display_name" :value="a.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="音色风格">
          <el-select v-model="form.voice_style" style="width: 100%">
            <el-option v-for="v in voices" :key="v.style" :label="v.label" :value="v.style" />
          </el-select>
        </el-form-item>
        <el-form-item label="语速倍率">
          <el-slider v-model="form.speech_rate" :min="0.75" :max="1.25" :step="0.05" show-input />
        </el-form-item>
        <el-form-item label="口型演示">
          <el-switch v-model="form.lip_sync_enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">保存配置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.section-title {
  margin: 0 0 12px;
  font-size: 15px;
  color: #1e293b;
}

.mini-badge {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  color: #ffffff;
  font-weight: 700;
  font-size: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.avatar-card-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.avatar-badge {
  width: 42px;
  height: 42px;
  border-radius: 10px;
  color: #ffffff;
  font-weight: 700;
  font-size: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.avatar-name {
  font-weight: 600;
  color: #0f172a;
}

.avatar-id {
  font-size: 12px;
  color: #64748b;
}

.avatar-desc {
  font-size: 13px;
  color: #334155;
  margin: 0 0 6px;
}

.avatar-tagline {
  font-size: 12px;
  color: #64748b;
  margin: 0 0 12px;
  min-height: 34px;
}

.avatar-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
