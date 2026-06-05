import { defineStore } from 'pinia'

export const useAppStore = defineStore('app', {
  state: () => ({
    // 当前选择的练习场景配置
    currentScene: null,
    
    // 当前会话的可修改场景参数（天气、对方性格等）
    activeParams: {},
    
    // 当前正在进行的会话历史 ID
    activeHistoryId: null,
    
    // 当前会话的多轮对话明细列表
    dialogueTurns: [],
    
    // 全局录音与AI回应加载状态
    isRecording: false,
    isProcessingAudio: false,
    isSpeakingAI: false,
    
    // 后端 API 服务地址
    backendBaseUrl: 'http://127.0.0.1:8000'
  }),
  
  actions: {
    // 设定当前选择的练习场景并载入其默认参数
    setCurrentScene(scene) {
      this.currentScene = scene
      this.activeParams = JSON.parse(JSON.stringify(scene.default_params || {}))
    },
    
    // 开始新会话并重置对话列表
    setActiveHistoryId(id) {
      this.activeHistoryId = id
      this.dialogueTurns = []
    },
    
    // 增加新对话明细（用户/AI）
    addDialogueTurn(turn) {
      this.dialogueTurns.push(turn)
    },
    
    // 清除重置当前会话的所有状态
    clearActiveSession() {
      this.activeHistoryId = null
      this.dialogueTurns = []
      this.isRecording = false
      this.isProcessingAudio = false
      this.isSpeakingAI = false
    }
  }
})
