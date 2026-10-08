<script setup>
// 3D 数字人：three.js 程序化搭建的 Q 版角色（无外部模型文件、无贴图加载管线）。
// 配色随角色主题实时切换；呼吸 / 眨眼 / 状态姿态 / 口型全部程序驱动。
// 组件不持业务状态：口型数值与会话状态由 AvatarStage 下发；
// 初始化失败（如 WebGL 不可用）emit('failed') 由父级降级占位。
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as THREE from 'three'

const props = defineProps({
  palette: { type: Object, required: true },   // 主题配色 { skin, skinShade, hair, cloth, clothShade, accent }
  state: { type: String, default: 'idle' },    // 会话状态：idle/listening/thinking/speaking
  lipSync: { type: String, default: 'state' }, // 口型级别：timeline/envelope/state/off
  mouthOpen: { type: Number, default: 0 },     // L1/L2 实时开合 0~1
})

const emit = defineEmits(['failed'])

const container = ref(null)

// three 对象全部用普通变量：进 Vue 响应式代理会拖垮每帧渲染
let containerEl = null
let renderer = null
let scene = null
let camera = null
let clock = null
let gradMap = null
let char = null
let headGrp = null
let torso = null
let mouth = null
let eyeGroups = []
let armGroups = []
let rafId = 0
let observer = null
let nextBlink = 2 + Math.random() * 2.5 // 距下次眨眼的秒数
let blinkPhase = 0                      // >0 表示眨眼进行中（0.26s 一轮）

// 三档灰度渐变图：给 MeshToonMaterial 做赛璐璐分档着色
function makeGradientMap() {
  const steps = [110, 190, 255]
  const data = new Uint8Array(steps.length * 4)
  steps.forEach((v, i) => data.set([v, v, v, 255], i * 4))
  const tex = new THREE.DataTexture(data, steps.length, 1, THREE.RGBAFormat)
  tex.minFilter = THREE.NearestFilter
  tex.magFilter = THREE.NearestFilter
  tex.needsUpdate = true
  return tex
}

const toon = (color) => new THREE.MeshToonMaterial({ color, gradientMap: gradMap })

// 反向壳描边：同几何体背面放大一圈，得到二次元轮廓线
function addOutline(mesh, s = 1.05) {
  const outline = new THREE.Mesh(
    mesh.geometry,
    new THREE.MeshBasicMaterial({ color: 0x26273a, side: THREE.BackSide }),
  )
  outline.scale.setScalar(s)
  mesh.add(outline)
}

function sphere(r, mat, x, y, z, sx = 1, sy = 1, sz = 1) {
  const m = new THREE.Mesh(new THREE.SphereGeometry(r, 28, 20), mat)
  m.position.set(x, y, z)
  m.scale.set(sx, sy, sz)
  return m
}

// 按主题配色搭建角色：Q 版比例（头大身小），面部朝 +Z，头顶约 1.35 单位
function buildCharacter() {
  if (char) { scene.remove(char); disposeGroup(char) }
  char = new THREE.Group()
  eyeGroups = []
  armGroups = []
  const P = props.palette
  const skin = toon(P.skin)
  const skinShade = toon(P.skinShade)
  const hair = toon(P.hair)
  const cloth = toon(P.cloth)
  const clothShade = toon(P.clothShade)
  const accent = toon(P.accent)
  const white = toon('#ffffff')
  const iris = toon('#' + new THREE.Color(P.hair).offsetHSL(0, 0.05, -0.06).getHexString())

  // 腿脚：常规取景被裁掉，保底身形完整
  for (const side of [-1, 1]) {
    const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.062, 0.07, 0.3, 16), clothShade)
    leg.position.set(side * 0.09, 0.15, 0)
    char.add(leg)
    char.add(sphere(0.07, toon('#3a3d4d'), side * 0.09, 0.045, 0.02, 1, 0.6, 1.35))
  }

  // 躯干 + 下摆 + 衣领
  torso = new THREE.Mesh(new THREE.CylinderGeometry(0.17, 0.145, 0.36, 24), cloth)
  torso.position.y = 0.46
  addOutline(torso, 1.06)
  char.add(torso)
  const hem = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.255, 0.16, 24), clothShade)
  hem.position.y = 0.345
  char.add(hem)
  const collar = new THREE.Mesh(new THREE.TorusGeometry(0.095, 0.026, 12, 24), toon('#f6f3ec'))
  collar.rotation.x = Math.PI / 2
  collar.position.y = 0.655
  char.add(collar)

  // 手臂挂在肩部（随说话轻摆）+ 手
  for (const side of [-1, 1]) {
    const armGrp = new THREE.Group()
    armGrp.position.set(side * 0.185, 0.575, 0)
    armGrp.rotation.z = side * 0.16
    const arm = new THREE.Mesh(new THREE.CapsuleGeometry(0.05, 0.22, 6, 14), cloth)
    arm.position.y = -0.13
    armGrp.add(arm)
    armGrp.add(sphere(0.054, skin, 0, -0.29, 0))
    char.add(armGrp)
    armGroups.push(armGrp)
  }

  // 颈
  const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.052, 0.09, 16), skinShade)
  neck.position.y = 0.68
  char.add(neck)

  // 头组：绕颈底 (0,0.70) 做点头 / 侧头，子元素坐标均为局部值
  headGrp = new THREE.Group()
  headGrp.position.y = 0.7
  char.add(headGrp)

  const head = sphere(0.3, skin, 0, 0.3, 0.01, 1, 0.94, 0.96)
  addOutline(head, 1.035)
  headGrp.add(head)

  // 后发 + 覆顶刘海 + 两侧发 + 呆毛 + 发饰
  // 后发：整体后移压扁，只包住头侧与脑后，不遮脸
  const hairBack = sphere(0.34, hair, 0, 0.33, -0.07, 1.04, 1.02, 0.88)
  addOutline(hairBack, 1.03)
  headGrp.add(hairBack)
  const fringe = new THREE.Mesh(
    new THREE.SphereGeometry(0.315, 28, 20, 0, Math.PI * 2, 0, Math.PI * 0.4),
    hair,
  )
  fringe.scale.set(1.04, 1.06, 1.0)
  fringe.position.set(0, 0.315, 0.005)
  fringe.rotation.x = 0.28 // 前缘下压：刘海盖住额头、露双眼
  headGrp.add(fringe)
  for (const side of [-1, 1]) {
    const lock = new THREE.Mesh(new THREE.CapsuleGeometry(0.055, 0.17, 6, 14), hair)
    lock.position.set(side * 0.3, 0.26, 0.14)
    lock.rotation.z = side * 0.08
    headGrp.add(lock)
  }
  const ahoge = new THREE.Mesh(new THREE.ConeGeometry(0.022, 0.1, 10), hair)
  ahoge.position.set(0.03, 0.685, 0)
  ahoge.rotation.z = 0.35
  headGrp.add(ahoge)
  headGrp.add(sphere(0.042, accent, 0.24, 0.545, 0.2))
  headGrp.add(sphere(0.026, accent, 0.3, 0.505, 0.15))

  // 眼：白眼球 + 虹膜 + 高光；整组 scale.y 压扁实现眨眼
  for (const side of [-1, 1]) {
    const eye = new THREE.Group()
    eye.position.set(side * 0.115, 0.3, 0.262)
    eye.add(sphere(0.052, white, 0, 0, 0, 1, 1.35, 0.45))
    eye.add(sphere(0.034, iris, 0, -0.004, 0.014, 1, 1.3, 0.55))
    eye.add(sphere(0.011, white, 0.013, 0.022, 0.03))
    headGrp.add(eye)
    eyeGroups.push(eye)
  }

  // 眉
  for (const side of [-1, 1]) {
    const brow = new THREE.Mesh(new THREE.BoxGeometry(0.085, 0.014, 0.012), hair)
    brow.position.set(side * 0.115, 0.418, 0.25)
    brow.rotation.z = side * -0.1
    headGrp.add(brow)
  }

  // 腮红
  const blushMat = new THREE.MeshBasicMaterial({ color: '#f2a39a', transparent: true, opacity: 0.5, side: THREE.DoubleSide })
  for (const side of [-1, 1]) {
    const blush = new THREE.Mesh(new THREE.CircleGeometry(0.034, 16), blushMat)
    blush.position.set(side * 0.178, 0.225, 0.238)
    blush.rotation.y = side * 0.28
    headGrp.add(blush)
  }

  // 嘴：开合靠 scale.y 拉伸
  mouth = sphere(0.045, new THREE.MeshBasicMaterial({ color: '#7d4a52' }), 0, 0.185, 0.262, 1, 0.3, 0.4)
  headGrp.add(mouth)

  scene.add(char)
}

function init() {
  try {
    const el = containerEl
    if (!el) return
    const width = el.clientWidth || 300
    const height = el.clientHeight || 375

    renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setSize(width, height, false)
    Object.assign(renderer.domElement.style, { width: '100%', height: '100%', display: 'block' })
    el.appendChild(renderer.domElement)

    scene = new THREE.Scene()
    camera = new THREE.PerspectiveCamera(30, width / height, 0.1, 20)
    camera.position.set(0, 1.02, 2.35)
    camera.lookAt(0, 0.99, 0)

    // 半球底光 + 暖色主光 + 冷紫轮廓光（在深色舞台上有立体感）
    scene.add(new THREE.HemisphereLight(0xffffff, 0x7a7aa8, 0.85))
    const key = new THREE.DirectionalLight(0xfff2e2, 1.0)
    key.position.set(0.7, 1.5, 1.3)
    scene.add(key)
    const rim = new THREE.DirectionalLight(0x9aa4f0, 0.5)
    rim.position.set(-1.2, 1.1, -0.9)
    scene.add(rim)

    gradMap = makeGradientMap()
    buildCharacter()

    clock = new THREE.Clock()
    loop()

    observer = new ResizeObserver(() => {
      const w = el.clientWidth
      const h = el.clientHeight
      if (!w || !h || !renderer) return
      renderer.setSize(w, h, false)
      camera.aspect = w / h
      camera.updateProjectionMatrix()
    })
    observer.observe(el)
  } catch (err) {
    console.warn('3D 角色初始化失败：', err)
    emit('failed')
  }
}

function loop() {
  rafId = requestAnimationFrame(loop)
  if (!char || !clock) return
  const dt = Math.min(clock.getDelta(), 0.05)
  const t = clock.elapsedTime
  const state = props.state

  // 呼吸：躯干缓慢起伏
  torso.scale.y = 1 + Math.sin(t * 1.6) * 0.02
  torso.scale.x = torso.scale.z = 1 - Math.sin(t * 1.6) * 0.008

  // 头部姿态：speaking 点头节奏 / thinking 低头 / listening 侧头 / idle 轻晃
  if (headGrp) {
    headGrp.rotation.x =
      state === 'speaking' ? Math.sin(t * 3.1) * 0.055
      : state === 'thinking' ? 0.13
      : state === 'listening' ? 0.05
      : Math.sin(t * 0.9) * 0.02
    headGrp.rotation.z = state === 'listening' ? -0.09 : 0
    headGrp.rotation.y = state === 'speaking' ? Math.sin(t * 2.3) * 0.06 : Math.sin(t * 0.6) * 0.09
  }

  // 手臂：静止微摆；speaking 时小幅挥动
  armGroups.forEach((g, i) => {
    const side = i === 0 ? -1 : 1
    const wave = state === 'speaking' ? Math.sin(t * 3.1 + i * 1.7) * 0.03 : 0
    g.rotation.z = side * (0.16 + Math.sin(t * 1.3 + i) * 0.02 + wave)
  })

  // 口型：L1/L2 用实时数值；L3 仅 speaking 时内置节奏；off 恒闭
  let mouthVal = 0
  if (props.lipSync === 'timeline' || props.lipSync === 'envelope') mouthVal = props.mouthOpen
  else if (props.lipSync === 'state' && state === 'speaking') mouthVal = 0.3 + Math.sin(t * 7.4) * 0.22
  mouthVal = Math.max(0, Math.min(1, mouthVal))
  if (mouth) {
    mouth.scale.y = 0.3 + mouthVal * 1.15
    mouth.scale.x = 1 + mouthVal * 0.2
  }

  // 眨眼：随机间隔触发 0.26s 一轮；listening 刻意减少（专注感）
  nextBlink -= dt
  if (nextBlink <= 0 && blinkPhase <= 0) {
    blinkPhase = 0.26
    nextBlink = state === 'listening' ? 4.5 + Math.random() * 2 : 2 + Math.random() * 2.6
  }
  const blink = blinkPhase > 0 ? Math.sin((1 - Math.max(0, blinkPhase) / 0.26) * Math.PI) : 0
  if (blinkPhase > 0) blinkPhase -= dt
  eyeGroups.forEach((e) => { e.scale.y = 1 - blink * 0.94 })

  renderer.render(scene, camera)
}

// 主题配色变化时整体重建（程序化建模开销可忽略）
watch(() => props.palette, () => { if (scene) buildCharacter() })

function disposeGroup(root) {
  root.traverse((o) => {
    if (o.geometry) o.geometry.dispose()
    if (o.material) {
      const mats = Array.isArray(o.material) ? o.material : [o.material]
      mats.forEach((m) => m.dispose())
    }
  })
}

function disposeAll() {
  if (rafId) cancelAnimationFrame(rafId)
  rafId = 0
  if (char && scene) { scene.remove(char); disposeGroup(char) }
  char = null
  headGrp = null
  torso = null
  mouth = null
  eyeGroups = []
  armGroups = []
  if (gradMap) { gradMap.dispose(); gradMap = null }
  if (renderer) {
    renderer.dispose()
    renderer.domElement?.remove()
    renderer = null
  }
  scene = null
  camera = null
  clock = null
}

onMounted(() => {
  containerEl = container.value
  init()
})

onBeforeUnmount(() => {
  observer?.disconnect()
  observer = null
  disposeAll()
})
</script>

<template>
  <div ref="container" class="stage-3d" />
</template>

<style scoped>
/* 填满舞台：透明背景直接露出 AvatarStage 的深色聚光底 */
.stage-3d { position: absolute; inset: 0; }
</style>
