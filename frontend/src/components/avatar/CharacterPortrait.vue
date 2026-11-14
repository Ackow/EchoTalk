<script setup>
import { computed } from 'vue'
import ScenePortrait from './ScenePortrait.vue'

const props = defineProps({
  character: { type: String, default: 'leo_2d' },
  appearance: { type: Object, default: null },
  gaze: { type: Object, default: () => ({ x: 0, y: 0 }) },
  happy: Boolean,
  state: { type: String, default: 'idle' },
  lipSync: { type: Boolean, default: true },
  animated: { type: Boolean, default: true },
  theme: { type: String, default: 'amber' },
  name: { type: String, default: 'Leo' },
})

const VALID_CHARACTERS = new Set(['leo_2d', 'emily_2d', 'david_2d', 'sarah_2d', 'claire_2d'])
const resolvedCharacter = computed(() => (VALID_CHARACTERS.has(props.character) ? props.character : 'leo_2d'))
</script>

<template>
  <ScenePortrait
    :character="resolvedCharacter"
    :appearance="appearance"
    :gaze="gaze"
    :happy="happy"
    :state="state"
    :lip-sync="lipSync"
    :animated="animated"
    :name="name"
  />
</template>
