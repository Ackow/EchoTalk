<template>
  <PracticeReportModal :open="open" :report="report" @close="emit('close')" />
</template>

<script setup>
import PracticeReportModal from './PracticeReportModal.vue'

defineProps({
  open: { type: Boolean, default: false },
  report: { type: Object, default: null },
})

const emit = defineEmits(['close'])
</script>
