<script setup>
import { computed, ref } from 'vue'
import AppTabs from '../AppTabs.vue'
import { APPEARANCE_OPTIONS, resolveAppearance } from './avatarAppearance'

const props = defineProps({
  characterId: { type: String, default: 'leo_2d' },
  modelValue: { type: Object, default: null },
  compact: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'reset'])

const activeCategory = ref('face')
const categories = [
  { value: 'face', label: '五官轮廓' },
  { value: 'hair', label: '发型发色' },
  { value: 'outfit', label: '穿搭配饰' },
  { value: 'backdrop', label: '场景背景' },
]

const current = computed(() => resolveAppearance(props.characterId, props.modelValue))

function patch(key, value) {
  emit('update:modelValue', { ...current.value, [key]: value })
}
</script>

<template>
  <div class="customizer" :class="{ compact }">
    <div class="cust-tabs-row">
      <AppTabs v-model="activeCategory" :options="categories" aria-label="外观分类" />
    </div>

    <div class="cust-panel">
      <Transition name="cust-fade" mode="out-in">
        <div v-if="activeCategory === 'face'" key="face" class="cust-section">
          <div class="cust-row">
            <span class="cust-label">轮廓与肤色</span>
            <div class="inline-controls">
              <div class="pill-group">
                <button
                  v-for="opt in APPEARANCE_OPTIONS.base"
                  :key="opt.value"
                  type="button"
                  class="pill-btn"
                  :class="{ active: current.base === opt.value }"
                  @click="patch('base', opt.value)"
                >{{ opt.label }}</button>
              </div>
              <div class="swatch-group" aria-label="肤色">
                <button
                  v-for="opt in APPEARANCE_OPTIONS.skinTone"
                  :key="opt.value"
                  type="button"
                  class="swatch-btn"
                  :class="{ active: current.skinTone === opt.value }"
                  :style="{ background: opt.color }"
                  :title="opt.label"
                  @click="patch('skinTone', opt.value)"
                />
              </div>
            </div>
          </div>

          <div class="cust-row">
            <span class="cust-label">眼型与瞳色</span>
            <div class="inline-controls">
              <div class="pill-group">
                <button
                  v-for="opt in APPEARANCE_OPTIONS.eyeStyle"
                  :key="opt.value"
                  type="button"
                  class="pill-btn"
                  :class="{ active: current.eyeStyle === opt.value }"
                  @click="patch('eyeStyle', opt.value)"
                >{{ opt.label }}</button>
              </div>
              <div class="swatch-group" aria-label="瞳色">
                <button
                  v-for="opt in APPEARANCE_OPTIONS.eyeColor"
                  :key="opt.value"
                  type="button"
                  class="swatch-btn"
                  :class="{ active: current.eyeColor === opt.value }"
                  :style="{ background: opt.value }"
                  :title="opt.label"
                  @click="patch('eyeColor', opt.value)"
                />
              </div>
            </div>
          </div>
        </div>

        <div v-else-if="activeCategory === 'hair'" key="hair" class="cust-section">
          <div class="cust-row">
            <span class="cust-label">发型（{{ APPEARANCE_OPTIONS.hairStyle.length }}款）</span>
            <div class="pill-group">
              <button
                v-for="opt in APPEARANCE_OPTIONS.hairStyle"
                :key="opt.value"
                type="button"
                class="pill-btn"
                :class="{ active: current.hairStyle === opt.value }"
                @click="patch('hairStyle', opt.value)"
              >{{ opt.label }}</button>
            </div>
          </div>

          <div class="cust-row">
            <span class="cust-label">发色</span>
            <div class="swatch-group" aria-label="发色">
              <button
                v-for="opt in APPEARANCE_OPTIONS.hairColor"
                :key="opt.value"
                type="button"
                class="swatch-btn"
                :class="{ active: current.hairColor === opt.value }"
                :style="{ background: opt.value }"
                :title="opt.label"
                @click="patch('hairColor', opt.value)"
              />
            </div>
          </div>
        </div>

        <div v-else-if="activeCategory === 'outfit'" key="outfit" class="cust-section">
          <div class="cust-row">
            <span class="cust-label">服装</span>
            <div class="pill-group">
              <button
                v-for="opt in APPEARANCE_OPTIONS.outfit"
                :key="opt.value"
                type="button"
                class="pill-btn"
                :class="{ active: current.outfit === opt.value }"
                @click="patch('outfit', opt.value)"
              >{{ opt.label }}</button>
            </div>
          </div>

          <div class="cust-row">
            <span class="cust-label">眼镜</span>
            <div class="pill-group">
              <button
                v-for="opt in APPEARANCE_OPTIONS.glasses"
                :key="opt.value"
                type="button"
                class="pill-btn"
                :class="{ active: current.glasses === opt.value }"
                @click="patch('glasses', opt.value)"
              >{{ opt.label }}</button>
            </div>
          </div>

          <div class="cust-row">
            <span class="cust-label">配饰（{{ APPEARANCE_OPTIONS.accessory.length }}款）</span>
            <div class="pill-group">
              <button
                v-for="opt in APPEARANCE_OPTIONS.accessory"
                :key="opt.value"
                type="button"
                class="pill-btn"
                :class="{ active: current.accessory === opt.value }"
                @click="patch('accessory', opt.value)"
              >{{ opt.label }}</button>
            </div>
          </div>
        </div>

        <div v-else key="backdrop" class="cust-section">
          <div class="cust-row">
            <span class="cust-label">场景背景（{{ APPEARANCE_OPTIONS.backdrop.length }}款）</span>
            <div class="pill-group">
              <button
                v-for="opt in APPEARANCE_OPTIONS.backdrop"
                :key="opt.value"
                type="button"
                class="pill-btn"
                :class="{ active: current.backdrop === opt.value }"
                @click="patch('backdrop', opt.value)"
              >{{ opt.label }}</button>
            </div>
          </div>
        </div>
      </Transition>
    </div>

    <div class="cust-footer">
      <button type="button" class="reset-link" @click="emit('reset')">还原该角色默认外观</button>
    </div>
  </div>
</template>

<style scoped>
.customizer { display: grid; gap: 12px; margin-top: 12px; padding-top: 12px; border-top: 1px dashed #e6dff5; }
.cust-tabs-row { display: flex; align-items: center; }
.cust-panel { min-height: 176px; display: flex; flex-direction: column; justify-content: flex-start; }
.cust-section { display: grid; gap: 12px; }
.cust-row { display: grid; gap: 6px; }
.cust-label { font-size: 11.5px; font-weight: 600; color: #6b6584; }
.inline-controls { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.pill-group { display: flex; flex-wrap: wrap; gap: 6px; }
.pill-btn {
  padding: 5px 11px; border-radius: 9px; border: 1.5px solid #ebe7f4; border-bottom-width: 2.5px;
  background: #fff; color: #4b436b; font-size: 11.5px; font-weight: 550; cursor: pointer;
  transition: border-color .15s, background .15s, color .15s;
}
.pill-btn:hover { border-color: #cfc1f1; background: #fcfaff; }
.pill-btn.active { border-color: #9b83e5; border-bottom-color: #8067d1; background: #f0eaff; color: #654ab8; font-weight: 650; }
.swatch-group { display: flex; flex-wrap: wrap; align-items: center; gap: 7px; padding-left: 2px; }
.swatch-btn {
  width: 22px; height: 22px; border-radius: 50%; border: 2px solid #fff;
  box-shadow: 0 0 0 1.5px #dcd3f2; cursor: pointer; transition: transform .15s, box-shadow .15s;
}
.swatch-btn:hover { transform: scale(1.1); }
.swatch-btn.active { box-shadow: 0 0 0 2.5px #8067d1; transform: scale(1.12); }
.cust-footer { display: flex; justify-content: flex-end; }
.reset-link { border: 0; background: transparent; padding: 2px 4px; font-size: 11.5px; color: #8069c7; cursor: pointer; }
.reset-link:hover { text-decoration: underline; }
.cust-fade-enter-active, .cust-fade-leave-active { transition: opacity .15s ease, transform .15s ease; }
.cust-fade-enter-from { opacity: 0; transform: translateY(4px); }
.cust-fade-leave-to { opacity: 0; transform: translateY(-4px); }
</style>
