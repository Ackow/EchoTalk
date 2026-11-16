<template>
  <Teleport to="body">
    <!-- 设置弹窗：遮罩 + 左侧分类 + 右侧内容；账户只是其中一项 -->
    <div class="settings-scrim" @click.self="emit('close')">
      <section ref="panel" class="settings-dialog" role="dialog" aria-modal="true" aria-labelledby="settings-title" tabindex="-1">
        <button class="dialog-close" type="button" aria-label="关闭设置" @click="emit('close')">
          <AppIcon name="x" :size="16" />
        </button>

        <aside class="set-nav">
          <h2 id="settings-title" class="set-nav-title"><AppIcon name="settings" :size="15" />设置</h2>
          <nav class="set-nav-list" aria-label="设置分类">
            <button
              v-for="item in SECTIONS"
              :key="item.key"
              class="set-nav-item"
              :class="{ active: active === item.key }"
              type="button"
              @click="active = item.key"
            >
              <AppIcon :name="item.icon" :size="15" />{{ item.label }}
            </button>
          </nav>
        </aside>

        <div class="dialog-body">
          <!-- 账户：头像 + 基本信息 + 退出登录 -->
          <section v-if="active === 'account'" class="pane">
            <header class="pane-head">
              <h3>账户</h3>
              <p>头像会显示在左下角的账户卡上，用户名暂不支持修改。</p>
            </header>

            <div class="profile">
              <UserAvatar :user="user" :size="72" />
              <div class="profile-copy">
                <b>{{ user?.username }}</b>
                <small>{{ joinedDays }}</small>
              </div>
              <div class="profile-actions">
                <label class="primary-button slim" :class="{ busy: uploading }">
                  <AppIcon name="upload" :size="14" />{{ uploading ? '正在上传…' : user?.avatar_path ? '更换' : '上传' }}
                  <input class="hidden-input" type="file" accept=".jpg,.jpeg,.png,.webp" :disabled="uploading" @change="handleAvatar" />
                </label>
                <button class="ghost-button" type="button" :disabled="uploading || !user?.avatar_path" @click="clearAvatar">
                  <AppIcon name="trash" :size="14" />移除
                </button>
              </div>
            </div>
            <p class="hint">JPG / PNG / WebP，上传后自动裁切为 512px 正方形。</p>
            <p v-if="avatarError" class="error" role="alert">{{ avatarError }}</p>

            <div class="fields">
              <label class="field ro">
                <span>用户名</span>
                <input :value="user?.username" readonly tabindex="-1" />
              </label>
              <label class="field ro">
                <span>注册时间</span>
                <input :value="joinedFull" readonly tabindex="-1" />
              </label>
            </div>

            <div class="danger-zone">
              <div class="danger-copy">
                <b>退出登录</b>
                <small>只退出当前设备，练习记录仍保留在账户里。</small>
              </div>
              <button class="ghost-button danger" type="button" :disabled="loggingOut" @click="doLogout">
                <AppIcon name="log-out" :size="14" />{{ loggingOut ? '正在退出…' : '退出登录' }}
              </button>
            </div>
            <p v-if="logoutError" class="error" role="alert">{{ logoutError }}</p>
          </section>

          <!-- 安全：修改密码 -->
          <section v-else-if="active === 'security'" class="pane">
            <header class="pane-head">
              <h3>安全</h3>
              <p>修改密码后，其他设备上的登录会被退出，本机保持登录。</p>
            </header>

            <form class="pwd-form" @submit.prevent="submitPassword">
              <label class="field">
                <span>当前密码</span>
                <span class="field-input">
                  <input v-model="form.current" :type="visible.current ? 'text' : 'password'" autocomplete="current-password" placeholder="输入当前使用的密码" maxlength="128" />
                  <button class="peek" type="button" :aria-label="visible.current ? '隐藏当前密码' : '显示当前密码'" @click="visible.current = !visible.current">
                    <AppIcon name="eye" :size="15" />
                  </button>
                </span>
              </label>
              <label class="field">
                <span>新密码</span>
                <span class="field-input">
                  <input v-model="form.next" :type="visible.next ? 'text' : 'password'" autocomplete="new-password" placeholder="至少 8 位" maxlength="128" />
                  <button class="peek" type="button" :aria-label="visible.next ? '隐藏新密码' : '显示新密码'" @click="visible.next = !visible.next">
                    <AppIcon name="eye" :size="15" />
                  </button>
                </span>
              </label>
              <label class="field">
                <span>确认新密码</span>
                <span class="field-input">
                  <input v-model="form.confirm" :type="visible.confirm ? 'text' : 'password'" autocomplete="new-password" placeholder="再次输入新密码" maxlength="128" />
                  <button class="peek" type="button" :aria-label="visible.confirm ? '隐藏确认密码' : '显示确认密码'" @click="visible.confirm = !visible.confirm">
                    <AppIcon name="eye" :size="15" />
                  </button>
                </span>
              </label>
              <p v-if="formError" class="error" role="alert">{{ formError }}</p>
              <p v-else-if="formDone" class="ok" role="status"><AppIcon name="check" :size="14" />{{ formDone }}</p>
              <button class="primary-button slim submit" type="submit" :disabled="busy">
                <AppIcon name="check" :size="15" />{{ busy ? '正在保存…' : '保存新密码' }}
              </button>
            </form>
            <p class="hint">密码至少 8 位，建议字母、数字与符号混用。</p>
          </section>

          <!-- 外观：本机界面偏好 -->
          <section v-else-if="active === 'appearance'" class="pane">
            <header class="pane-head">
              <h3>外观</h3>
              <p>这里的偏好只保存在本机，换设备需要重新设置。</p>
            </header>

            <div class="pref-row">
              <div class="pref-copy"><b>收起侧边栏</b><small>隐藏左侧导航，把宽度让给内容区（⌘/Ctrl + B 也可切换）。</small></div>
              <button class="switch" type="button" role="switch" :aria-checked="sidebarHidden" aria-label="收起侧边栏" @click="sidebarHidden = !sidebarHidden">
                <span class="knob"></span>
              </button>
            </div>
          </section>

          <!-- 关于：版本与产品信息（面向用户，不展示技术实现） -->
          <section v-else class="pane">
            <div class="about-hero">
              <span class="about-mark"><img :src="brandImage" alt="" /></span>
              <div class="about-name">
                <h3>EchoTalk <em>2.0</em></h3>
                <p>英语情景对话与 AI 陪练</p>
              </div>
              <span class="about-state" :class="{ warn: updateState.status === 'available' }">
                <i></i>{{ updateBadgeText }}
              </span>
            </div>

            <dl class="about-grid">
              <div><dt>版本号</dt><dd>{{ appVersion }}</dd></div>
              <div><dt>构建日期</dt><dd>2026年11月16日</dd></div>
              <div><dt>版本类型</dt><dd>正式版</dd></div>
              <div><dt>适用平台</dt><dd>macOS · Windows</dd></div>
            </dl>

            <div v-if="isDesktop" class="update-bar">
              <div class="update-bar-copy">
                <b v-if="updateState.status === 'available'">发现新版本 v{{ updateState.latestVersion }}</b>
                <b v-else-if="updateState.status === 'error'">检查更新失败</b>
                <b v-else>版本更新检测</b>
                <small v-if="updateState.status === 'available'">{{ updateState.releaseName || '包含功能优化与问题修复' }}</small>
                <small v-else-if="updateState.status === 'error'">{{ updateState.message || '请检查网络连接后重试' }}</small>
                <small v-else>自动检测 GitHub Releases 最新桌面端版本</small>
              </div>
              <div class="update-bar-actions">
                <button
                  v-if="updateState.status === 'available'"
                  class="primary-button slim"
                  type="button"
                  @click="downloadLatest"
                >
                  下载 v{{ updateState.latestVersion }}
                </button>
                <button
                  class="ghost-button"
                  type="button"
                  :disabled="checkingUpdate"
                  @click="runUpdateCheck"
                >
                  {{ checkingUpdate ? '检查中…' : '检查更新' }}
                </button>
              </div>
            </div>

            <div class="about-updates">
              <b>本版更新</b>
              <ul>
                <li>新增设置面板，头像、密码与侧边栏偏好集中在一处</li>
                <li>场景包与语音对话流程重做，练习衔接更连贯</li>
                <li>历史记录支持逐句复盘，积累常用表达</li>
              </ul>
            </div>

            <p class="about-note">面向大学生与成年人的英语口语练习工具：在真实情境中对话、复盘与积累表达，练习记录与场景资料都保存在自己的账户里。</p>
            <p class="about-copy">© 2026 EchoTalk · 仅供个人学习与练习使用</p>
          </section>
        </div>
      </section>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '../AppIcon.vue'
import UserAvatar from '../UserAvatar.vue'
import brandImage from '../../assets/echotalk-brand.png'
import { changePassword, logout, removeAvatar, uploadAvatar } from '../../api/auth'
import { clearSession, session } from '../../auth/session'
import { sidebarHidden } from '../../app/prefs'

const emit = defineEmits(['close'])
const router = useRouter()

const SECTIONS = [
  { key: 'account', label: '账户', icon: 'user' },
  { key: 'security', label: '安全', icon: 'lock' },
  { key: 'appearance', label: '外观', icon: 'image' },
  { key: 'about', label: '关于', icon: 'info' },
]

const active = ref('account') // 当前分类：账户只是其中一项
const user = computed(() => session.user)
const panel = ref(null)

const visible = reactive({ current: false, next: false, confirm: false }) // 三个密码框的明文开关
const form = reactive({ current: '', next: '', confirm: '' })
const busy = ref(false)
const formError = ref('')
const formDone = ref('')
const uploading = ref(false)
const avatarError = ref('')
const loggingOut = ref(false)
const logoutError = ref('')
const isDesktop = Boolean(window.electronAPI?.checkForUpdates)
const appVersion = ref('2.0.0')
const checkingUpdate = ref(false)
const updateState = reactive({ status: 'idle', latestVersion: '', releaseName: '', downloadUrl: '', releaseUrl: '', message: '' })

const updateBadgeText = computed(() => {
  if (checkingUpdate.value) return '正在检查…'
  if (updateState.status === 'available') return `有新版本 v${updateState.latestVersion}`
  if (updateState.status === 'error') return '检查失败'
  return '已是最新版本'
})

async function runUpdateCheck() {
  if (!window.electronAPI?.checkForUpdates || checkingUpdate.value) return
  checkingUpdate.value = true
  try {
    const res = await window.electronAPI.checkForUpdates()
    Object.assign(updateState, {
      status: res?.status || 'latest',
      latestVersion: res?.latestVersion || '',
      releaseName: res?.releaseName || '',
      downloadUrl: res?.downloadUrl || '',
      releaseUrl: res?.releaseUrl || '',
      message: res?.message || '',
    })
  } finally {
    checkingUpdate.value = false
  }
}

function downloadLatest() {
  const url = updateState.downloadUrl || updateState.releaseUrl
  if (!url) return
  if (window.electronAPI?.openExternal) window.electronAPI.openExternal(url)
  else window.open(url, '_blank')
}

const pad = (value) => String(value).padStart(2, '0')
// 后端为北京时间 naive：直接按本地时区解析
const joinedFull = computed(() => {
  const iso = user.value?.created_at
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日 ${pad(date.getHours())}:${pad(date.getMinutes())}`
})
// 加入时长：只展示天数，避免和下方「注册时间」重复，也不暴露账户 ID
const joinedDays = computed(() => {
  const iso = user.value?.created_at
  if (!iso) return '刚加入'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '刚加入'
  const days = Math.floor((Date.now() - date.getTime()) / 86400000)
  if (days <= 0) return '今天加入'
  if (days < 90) return `已加入 ${days} 天`
  if (days < 365) return `已加入 ${Math.floor(days / 30)} 个月`
  return `已加入 ${Math.floor(days / 365)} 年`
})

function onKeydown(event) {
  if (event.key === 'Escape') emit('close') // 弹窗惯例：Esc 关闭
}
onMounted(async () => {
  window.addEventListener('keydown', onKeydown)
  panel.value?.focus({ preventScroll: true }) // 焦点移到弹窗本身：键盘可达，又不给关闭按钮留焦点框
  if (window.electronAPI?.getAppVersion) {
    try {
      appVersion.value = await window.electronAPI.getAppVersion()
    } catch { /* ignore */ }
  }
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))

// 头像压缩：中心裁正方形 → 512px → WebP，避免把几 MB 原图直接传上去
async function squareImage(file, size) {
  try {
    const bitmap = await createImageBitmap(file)
    const side = Math.min(bitmap.width, bitmap.height)
    const canvas = document.createElement('canvas')
    canvas.width = size
    canvas.height = size
    canvas.getContext('2d').drawImage(
      bitmap,
      (bitmap.width - side) / 2, (bitmap.height - side) / 2, side, side, // 中心裁切区域
      0, 0, size, size,
    )
    bitmap.close()
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/webp', 0.9))
    if (!blob) return file // 不支持 WebP 编码：退回原图，交给后端校验
    return new File([blob], 'avatar.webp', { type: 'image/webp' })
  } catch {
    return file // 解码失败（非常见格式）：退回原图
  }
}

async function handleAvatar(event) {
  const input = event.target
  const file = input.files?.[0]
  if (!file) return
  avatarError.value = ''
  if (!/\.(jpe?g|png|webp)$/i.test(file.name)) {
    avatarError.value = '仅支持 JPG / PNG / WebP 图片'
    input.value = ''
    return
  }
  if (file.size > 8 * 1024 * 1024) {
    avatarError.value = '图片不能超过 8 MB'
    input.value = ''
    return
  }
  uploading.value = true
  try {
    const { data } = await uploadAvatar(await squareImage(file, 512))
    session.user = { ...session.user, avatar_path: data.avatar_path } // 侧栏头像同步更新
  } catch (error) {
    avatarError.value = error.message || '头像上传失败，请稍后重试'
  } finally {
    uploading.value = false
    input.value = '' // 上传结束后再清空：同一张图重选也能触发 change
  }
}

async function clearAvatar() {
  if (!user.value?.avatar_path || uploading.value) return
  avatarError.value = ''
  uploading.value = true
  try {
    await removeAvatar()
    session.user = { ...session.user, avatar_path: null } // 回落到用户名首字母
  } catch (error) {
    avatarError.value = error.message || '移除失败，请稍后重试'
  } finally {
    uploading.value = false
  }
}

async function submitPassword() {
  formError.value = ''
  formDone.value = ''
  if (!form.current) {
    formError.value = '请输入当前密码'
    return
  }
  if (form.next.length < 8) {
    formError.value = '新密码至少 8 位'
    return
  }
  if (form.next !== form.confirm) {
    formError.value = '两次输入的新密码不一致'
    return
  }
  if (form.next === form.current) {
    formError.value = '新密码不能与当前密码相同'
    return
  }
  busy.value = true
  try {
    await changePassword({ current_password: form.current, new_password: form.next })
    formDone.value = '密码已修改，其他设备上的登录已退出。'
    form.current = ''
    form.next = ''
    form.confirm = ''
    visible.current = visible.next = visible.confirm = false
  } catch (error) {
    formError.value = error.message || '修改失败，请稍后重试' // 后端已把「当前密码不正确」转成可读文案
  } finally {
    busy.value = false
  }
}

async function doLogout() {
  loggingOut.value = true
  logoutError.value = ''
  try {
    await logout() // 先撤销令牌，失败则保留登录态让用户重试
  } catch (error) {
    logoutError.value = error.message || '退出服务暂不可用，请稍后重试'
    loggingOut.value = false
    return
  }
  clearSession()
  emit('close')
  await router.replace({ name: 'login' })
}
</script>

<style scoped>
.settings-scrim {
  position: fixed;
  inset: 0;
  z-index: 2500; /* 高于侧栏与账户浮层，低于全局加载遮罩 */
  display: grid;
  place-items: center;
  padding: 40px;
  background: var(--scrim-bg, rgba(34, 37, 59, .28));
  -webkit-backdrop-filter: var(--scrim-blur, blur(2px));
  backdrop-filter: var(--scrim-blur, blur(2px));
  animation: scrim-in .16s ease-out;
}

.settings-dialog {
  position: relative;
  display: grid;
  grid-template-columns: 188px minmax(0, 1fr);
  width: min(840px, 100%);
  height: min(540px, 100%);
  overflow: hidden;
  border: 2px solid #ebe7f5;
  border-bottom: 6px solid #e3dcf0;
  border-radius: 22px;
  background: #fff;
  box-shadow: 0 24px 60px rgba(34, 37, 59, .22);
  animation: dialog-in .18s cubic-bezier(.2, .9, .3, 1);
  outline: none; /* 焦点落在弹窗本身，不画聚焦框 */
}

.dialog-close { position: absolute; top: 12px; right: 12px; z-index: 1; display: grid; width: 30px; height: 30px; place-items: center; border: 0; border-radius: 10px; background: transparent; color: #9791ab; transition: background .15s, color .15s; }
.dialog-close:hover { background: #f3f0fa; color: #5d4b9c; }

/* 左侧分类栏 */
.set-nav { display: flex; flex-direction: column; gap: 6px; padding: 16px 12px 12px; border-right: 1px solid #f1eef8; background: #faf8ff; }
.set-nav-title { display: flex; align-items: center; gap: 8px; margin: 0 8px 10px; color: #393451; font-size: 16px; font-weight: 750; }
.set-nav-list { display: flex; flex-direction: column; gap: 3px; }
.set-nav-item { display: flex; height: 38px; align-items: center; gap: 9px; padding: 0 11px; border: 0; border-radius: 10px; background: transparent; color: #625e76; font-size: 14.5px; text-align: left; transition: background .15s, color .15s; }
.set-nav-item:hover { background: #f3effc; color: #5946a7; }
.set-nav-item.active { background: #eee9ff; color: #6c52c4; font-weight: 700; }

/* 右侧内容区 */
.dialog-body { min-height: 0; overflow-y: auto; padding: 22px 26px 24px; }
.pane { display: flex; flex-direction: column; }
.pane-head { margin-bottom: 18px; padding-right: 30px; }
.pane-head h3 { margin: 0; color: #393451; font-size: 16px; font-weight: 750; }
.pane-head p { margin: 5px 0 0; color: #8b87a0; font-size: 12.5px; line-height: 1.7; }

/* 账户概览：头像 + 名字 + 操作 */
.profile { display: flex; align-items: center; gap: 14px; }
.profile :deep(.user-avatar) { box-shadow: inset 0 0 0 2px #efeaf9, 0 2px 0 #eee8f7; }
.profile-copy { min-width: 0; flex: 1; }
.profile-copy b { display: block; overflow: hidden; color: #332f4b; font-size: 15px; font-weight: 750; text-overflow: ellipsis; white-space: nowrap; }
.profile-copy small { display: block; margin-top: 5px; color: #918da6; font-size: 12px; }
.profile-actions { display: flex; flex: 0 0 auto; align-items: center; gap: 8px; }

.hidden-input { display: none; }
.ghost-button { display: inline-flex; align-items: center; gap: 6px; height: 34px; padding: 0 13px; border: 1px solid var(--line); border-radius: 9px; background: var(--surface); color: var(--ink-soft); font-size: 13px; transition: border-color .15s, color .15s, background .15s; }
.ghost-button:hover:not(:disabled) { border-color: #d5d7e6; color: var(--ink); background: #fafafd; }
.ghost-button:disabled { opacity: .55; cursor: not-allowed; }
.ghost-button.danger { border-color: #f0dde1; color: #b8485a; }
.ghost-button.danger:hover:not(:disabled) { border-color: #e6c6cd; background: #fdf4f5; color: #a13d4d; }
.primary-button.slim { display: inline-flex; width: auto; height: 34px; align-items: center; justify-content: center; gap: 6px; margin-top: 0; padding: 0 14px; border-radius: 9px; background: var(--brand); color: #fff; font-size: 13px; font-weight: 500; transition: background .15s, opacity .15s; }
.primary-button.slim:hover:not(:disabled) { background: var(--brand-deep); }
.primary-button.slim.busy, .primary-button.slim:disabled { opacity: .7; cursor: progress; }

/* 只读字段：与密码框同一套形状，弱化底色表示不可编辑 */
.fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-top: 18px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field > span:first-child { color: #6b6683; font-size: 12.5px; font-weight: 600; }
.field input { width: 100%; height: 38px; padding: 0 12px; border: 1.5px solid #ece8f5; border-radius: 11px; background: #faf9fd; color: #4a4560; font-size: 13px; }
.field.ro input { cursor: default; }
.field.ro input:focus { outline: none; }

/* 危险区 */
.danger-zone { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-top: 20px; padding-top: 16px; border-top: 1px solid #f2eff8; }
.danger-copy b { display: block; color: #3a3552; font-size: 13.5px; font-weight: 700; }
.danger-copy small { display: block; margin-top: 4px; color: #918da6; font-size: 12px; }

/* 密码表单 */
.pwd-form { display: flex; flex-direction: column; gap: 12px; }
.pwd-form .field > span:first-child { color: #5f5a76; }
.field-input { position: relative; display: flex; align-items: center; }
.field-input input { width: 100%; height: 38px; padding: 0 38px 0 12px; border: 1.5px solid #e6e2f1; border-radius: 11px; background: #fcfbff; color: #3a3552; font-size: 13.5px; transition: border-color .15s, background .15s, box-shadow .15s; }
.field-input input::placeholder { color: #b0aac2; }
.field-input input:focus { border-color: #b6a4e8; background: #fff; box-shadow: 0 0 0 3px #f1ecff; outline: none; }
.peek { position: absolute; right: 6px; display: grid; width: 28px; height: 28px; place-items: center; border: 0; border-radius: 8px; background: transparent; color: #9a94ad; transition: background .15s, color .15s; }
.peek:hover { background: #f4f1fb; color: #6d57bb; }
.submit { align-self: flex-start; margin-top: 2px; }

/* 偏好开关 */
.pref-row { display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 14px 16px; border: 1.5px solid #eeeaf7; border-bottom: 4px solid #e9e3f4; border-radius: 15px; background: #fdfcff; }
.pref-copy b { display: block; color: #3a3552; font-size: 13.5px; font-weight: 700; }
.pref-copy small { display: block; margin-top: 5px; color: #8b87a0; font-size: 12px; line-height: 1.6; }
.switch { position: relative; flex: 0 0 44px; width: 44px; height: 24px; padding: 0; border: 1px solid #ded8ee; border-radius: 999px; background: #f0edf8; transition: background .16s, border-color .16s; }
.switch .knob { position: absolute; top: 2px; left: 2px; width: 18px; height: 18px; border-radius: 50%; background: #fff; box-shadow: 0 1px 2px rgba(34, 37, 59, .18); transition: transform .16s; }
.switch[aria-checked="true"] { border-color: #8b73dd; background: #8b73dd; }
.switch[aria-checked="true"] .knob { transform: translateX(20px); }

/* 关于：品牌 + 两列信息 */
.about-hero { display: flex; align-items: center; gap: 14px; padding-bottom: 18px; border-bottom: 1px solid #f2eff8; }
.about-state { display: inline-flex; align-items: center; gap: 6px; margin-left: auto; padding: 4px 10px; border: 1px solid #d8ece1; border-radius: 999px; background: #f2f8f4; color: #2f7d5f; font-size: 11.5px; font-weight: 600; white-space: nowrap; }
.about-state i { width: 6px; height: 6px; border-radius: 50%; background: #3f9e78; }
.about-state.warn { border-color: #f4d8be; background: #fff6ee; color: #c46a24; }
.about-state.warn i { background: #e08234; }
.update-bar { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 18px; padding: 12px 14px; border: 1px solid #ece7f7; border-radius: 13px; background: #faf9fd; }
.update-bar-copy { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.update-bar-copy b { font-size: 13px; color: #35304e; }
.update-bar-copy small { font-size: 12px; color: #76718c; }
.update-bar-actions { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.about-mark { display: grid; width: 56px; height: 56px; flex: 0 0 56px; place-items: center; overflow: hidden; border-radius: 16px; background: #f5f1ff; box-shadow: inset 0 0 0 1.5px #ebe4fb; }
.about-mark img { width: 100%; height: 100%; object-fit: contain; transform: scale(1.2); }
.about-name h3 { display: flex; align-items: center; gap: 7px; margin: 0; color: #332f4b; font-size: 17px; font-weight: 800; letter-spacing: -.01em; }
.about-name em { padding: 1.5px 7px; border: 1px solid #ddd3f3; border-radius: 999px; background: #fff; color: #7b68b8; font-size: 10px; font-style: normal; font-weight: 700; }
.about-name p { margin: 6px 0 0; color: #8b87a0; font-size: 12.5px; }
.about-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px 28px; margin: 18px 0 0; }
.about-grid dt { color: #918da6; font-size: 11.5px; }
.about-grid dd { margin: 4px 0 0; color: #3a3552; font-size: 13px; font-weight: 600; }
.about-updates { margin-top: 22px; }
.about-updates b { display: block; color: #4b4664; font-size: 12.5px; font-weight: 700; }
.about-updates ul { margin: 8px 0 0; padding-left: 17px; color: #6f6a86; font-size: 12.5px; line-height: 1.9; }
.about-updates li::marker { color: #b9aee0; }
.about-note { margin: 20px 0 0; padding: 13px 15px; border: 1px solid #f0edf8; border-radius: 13px; background: #fbf9ff; color: #6f6a86; font-size: 12.5px; line-height: 1.85; }
.about-copy { margin: 16px 0 0; color: #a9a4b8; font-size: 11.5px; }

.hint { margin: 12px 0 0; color: #8b87a0; font-size: 12px; line-height: 1.7; }
.error { margin: 10px 0 0; color: var(--danger); font-size: 12.5px; }
.ok { display: flex; align-items: center; gap: 6px; margin: 2px 0 0; color: #2f7d5f; font-size: 12.5px; }

@keyframes scrim-in { from { opacity: 0; } to { opacity: 1; } }
@keyframes dialog-in { from { opacity: 0; transform: translateY(8px) scale(.99); } to { opacity: 1; transform: none; } }

@media (max-width: 760px) {
  .settings-scrim { padding: 16px; }
  .settings-dialog { grid-template-columns: 148px minmax(0, 1fr); }
  .dialog-body { padding: 16px 16px 20px; }
  .fields { grid-template-columns: minmax(0, 1fr); }
  .profile { flex-wrap: wrap; }
}

@media (prefers-reduced-motion: reduce) {
  .settings-scrim, .settings-dialog { animation: none; }
}
</style>
