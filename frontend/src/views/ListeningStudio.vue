<template>
  <section class="listening-page">
    <ListeningHub
      v-if="!activeUnit"
      v-model:selected-channel="selectedChannel"
      v-model:cet-level="cetLevel"
      v-model:cet-mode="cetMode"
      v-model:selected-cet-year="selectedCetYear"
      :units="units"
      :loading="loadingUnits"
      :error="loadError"
      :stats="stats"
      :today-xp="todayXp"
      :daily-goal-xp="dailyGoalXp"
      @start-unit="startUnit"
      @retry="loadListeningData"
    />

    <ListeningRunner
      v-else
      :unit="activeUnit"
      :is-mock-restricted="isMockRestricted"
      @exit="activeUnit = null"
      @completed="handleUnitCompleted"
    />
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import ListeningHub from '../components/listening/ListeningHub.vue'
import ListeningRunner from '../components/listening/ListeningRunner.vue'
import { getListeningUnits } from '../api/listening'
import { usePageLoading } from '../app/loading'
import { dailyGoalXp, syncGlobalXpProfile, todayXp } from '../app/xp'
import { session } from '../auth/session'

const route = useRoute()
const finishLoading = usePageLoading()

const stats = ref({
  independentRate: null,
  assistedRate: null,
  weakTags: []
})
const units = ref([])
const loadingUnits = ref(false)
const loadError = ref('')
const selectedChannel = ref(route.query.channel === 'cet' ? 'cet' : 'all')
const cetLevel = ref('cet4')
const cetMode = ref('practice') // practice | mock
const selectedCetYear = ref('all')
const activeUnit = ref(null)

watch(cetLevel, () => {
  selectedCetYear.value = 'all'
})

watch(
  () => route.query.channel,
  (val) => {
    if (val === 'cet') selectedChannel.value = 'cet'
  }
)

function selectUnitFromRoute() {
  const unitId = String(route.query.unit || '').trim()
  if (!unitId || !units.value.length) return
  const matched = units.value.find((u) => u.id === unitId)
  if (matched) activeUnit.value = matched
}

watch(
  () => route.query.unit,
  () => selectUnitFromRoute()
)

const isMockRestricted = computed(
  () => activeUnit.value?.channel === 'cet' && cetMode.value === 'mock'
)

async function loadListeningData() {
  loadingUnits.value = true
  loadError.value = ''
  try {
    const { data } = await getListeningUnits()
    if (Array.isArray(data?.units)) units.value = data.units
    if (data?.stats) {
      stats.value = {
        independentRate: data.stats.independentRate ?? null,
        assistedRate: data.stats.assistedRate ?? null,
        weakTags: Array.isArray(data.stats.weakTags) ? data.stats.weakTags : []
      }
    }
    selectUnitFromRoute()
  } catch (err) {
    loadError.value = err?.message || '听力单元加载失败，请检查网络后重试'
  } finally {
    loadingUnits.value = false
    finishLoading()
  }
}

onMounted(() => {
  loadListeningData()
  if (session.token) syncGlobalXpProfile()
})

function startUnit(unit) {
  activeUnit.value = unit
}

async function handleUnitCompleted() {
  if (activeUnit.value) {
    activeUnit.value.progress = 100
  }
  await loadListeningData()
}
</script>

<style scoped>
/* 对齐 Workspace.vue / Scenes.vue 的 2.0 视觉体系：暖紫底 #fbfaff、2px 描边 + 立体底边、#8b73dd 主题按钮 */
.listening-page {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  background: #fbfaff;
  color: #29283e;
  padding: 26px clamp(22px, 3vw, 40px) 44px;
}
</style>
