// ────────────────────────────────────────────────────────────
// 腾讯云 CloudBase SDK — 社区场景包后端的可选实现方案
// ────────────────────────────────────────────────────────────
// 当前社区页面使用本地静态数据（见 Community.vue 的 packs 数组）。
// 若需要动态后端，可选择以下方案之一：
//
//   方案 A: CloudBase (BaaS) — 使用本文件的 SDK 接入
//   方案 B: 自建 FastAPI 后端 — 见 Docs.vue 的「社区 API」章节
//
// 本文件为方案 A 的参考实现骨架，需安装 @cloudbase/js-sdk 并配置环境 ID。
//
// 使用方法:
//   1. npm install @cloudbase/js-sdk
//   2. 替换下方 init({ env: 'your-env-id' }) 中的环境 ID
//   3. 在组件中 import { getScenePacks } from '@/cloudbase'
//   4. 调用 getScenePacks() 替换 Community.vue 中的本地 packs 数组
// ────────────────────────────────────────────────────────────

// import cloudbase from '@cloudbase/js-sdk'
//
// const app = cloudbase.init({
//   env: 'echotalk-docs-xxxxx', // 替换为你的 CloudBase 环境 ID
// })
//
// const auth = app.auth()
// const db = app.database()
//
// export async function login() {
//   const loginState = await auth.signInAnonymously()
//   return loginState
// }
//
// export async function getScenePacks() {
//   const collection = db.collection('scene_packs')
//   const res = await collection.get()
//   return res.data
// }
//
// export async function getScenePack(id) {
//   const collection = db.collection('scene_packs')
//   const res = await collection.doc(id).get()
//   return res.data
// }
//
// export async function createScenePack(data) {
//   const collection = db.collection('scene_packs')
//   const res = await collection.add(data)
//   return res.id
// }
//
// export { app, auth, db }

// 当前使用本地 Mock 数据，未启用 CloudBase
export async function getScenePacks() { return [] }
