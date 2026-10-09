<script setup>
import { computed, getCurrentInstance } from 'vue'
import AlternatePortrait from './AlternatePortrait.vue'

const props = defineProps({
  character: { type: String, default: 'mira_2d' },
  gaze: { type: Object, default: () => ({ x: 0, y: 0 }) },
  happy: Boolean,
  state: { type: String, default: 'idle' },
  lipSync: { type: Boolean, default: true },
  animated: { type: Boolean, default: true },
  // 形象主题：决定发色与衣着（形象清单见 api/avatar.js，与 AvatarStage 传值一致）
  theme: { type: String, default: 'violet' },
  // 展示名：仅用于无障碍描述
  name: { type: String, default: 'Mira' },
})

// 主题色板：hair=渐变三段发色；sweater=渐变三段衣着；其余为点缀与配饰
const THEMES = {
  violet: {
    hair: ['#514049', '#302a3d', '#201d30'], hairHi: '#97757a',
    sweater: ['#b6abd9', '#9282bb', '#70608e'], stitch: '#786791', knit: '#ded3ed',
    collar: '#c8bbdf', collarStroke: '#9180b4', hem: '#74638d',
    pouch: '#e9dded', pouchLine: '#9380b7', pin: '#d9c6e7',
    earBand: '#d8c7dc', earPiece: '#c5b0d7', earStroke: '#eee2ee', mic: '#78618e',
  },
  teal: {
    hair: ['#4a4238', '#332e28', '#221f1c'], hairHi: '#a08b6f',
    sweater: ['#a7d3c4', '#74b3a0', '#528a79'], stitch: '#5f9a88', knit: '#dcefe8',
    collar: '#c2ded6', collarStroke: '#6fa794', hem: '#5b9080',
    pouch: '#e2f0ea', pouchLine: '#7fae9c', pin: '#cfe8de',
    earBand: '#d5e6df', earPiece: '#a8cfc0', earStroke: '#eef7f2', mic: '#5f8f7f',
  },
  blue: {
    hair: ['#3d3a45', '#2b2933', '#1c1b24'], hairHi: '#8a8aa0',
    sweater: ['#a9bde0', '#7d95c6', '#5a709f'], stitch: '#6c82b1', knit: '#dfe6f3',
    collar: '#c5d2e9', collarStroke: '#7d95c6', hem: '#6880ae',
    pouch: '#e5ebf6', pouchLine: '#8ba1c9', pin: '#d2ddef',
    earBand: '#d9e1ef', earPiece: '#b0c1de', earStroke: '#f0f4fb', mic: '#6d84ab',
  },
  amber: {
    hair: ['#6b4a33', '#4a3325', '#32231a'], hairHi: '#b08c6a',
    sweater: ['#e4c294', '#cba468', '#a37e45'], stitch: '#b3874e', knit: '#f6ead2',
    collar: '#eed9b4', collarStroke: '#c8a05e', hem: '#b08a4e',
    pouch: '#f7ecd6', pouchLine: '#c8a05e', pin: '#f0e0bd',
    earBand: '#f0e2c8', earPiece: '#dcbc84', earStroke: '#fbf3e2', mic: '#a37e45',
  },
}
const t = computed(() => THEMES[props.theme] || THEMES.violet)

// 每个实例独立的渐变 ID，缩略图与大舞台同时出现时不会互相覆盖。
const id = `mira-${getCurrentInstance().uid}`
const eyes = computed(() => `translate(${props.gaze.x * 2.6} ${props.gaze.y * 1.8})`)
const head = computed(() => `translate(${props.gaze.x * 1.8} ${props.gaze.y}) rotate(${props.gaze.x * 1.4} 200 185)`)
</script>

<template>
  <svg v-if="character === 'mira_2d'" data-character="mira" viewBox="0 0 400 480" xmlns="http://www.w3.org/2000/svg" class="portrait" :class="[{ animated, happy }, `is-${state}`]" role="img" :aria-label="`${name}，戴耳麦的短发交流伙伴`">
    <defs>
      <linearGradient :id="`${id}-hair`" x1="0" y1="0" x2="1" y2="1"><stop :stop-color="t.hair[0]"/><stop offset=".55" :stop-color="t.hair[1]"/><stop offset="1" :stop-color="t.hair[2]"/></linearGradient>
      <linearGradient :id="`${id}-skin`" x1="0" y1="0" x2=".8" y2="1"><stop stop-color="#fff0dd"/><stop offset=".65" stop-color="#f8d9c7"/><stop offset="1" stop-color="#edb9ad"/></linearGradient>
      <linearGradient :id="`${id}-sweater`" x1="0" y1="0" x2="1" y2="1"><stop :stop-color="t.sweater[0]"/><stop offset=".5" :stop-color="t.sweater[1]"/><stop offset="1" :stop-color="t.sweater[2]"/></linearGradient>
      <linearGradient :id="`${id}-iris`" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#443447"/><stop offset="1" stop-color="#ad7c68"/></linearGradient>
      <radialGradient :id="`${id}-blush`"><stop stop-color="#e89b96" stop-opacity=".65"/><stop offset="1" stop-color="#e89b96" stop-opacity="0"/></radialGradient>
    </defs>
    <!-- 半身轮廓与针织细节，宽肩和自然颈部让比例更接近人物插画。 -->
    <g class="body">
      <path d="M143 299Q107 305 86 334Q69 365 60 480H339Q332 376 314 341Q296 314 256 301Z" :fill="`url(#${id}-sweater)`"/>
      <path d="M105 338Q117 362 108 472M296 340Q282 375 292 476" fill="none" :stroke="t.stitch" stroke-width="3" opacity=".5"/>
      <path d="M177 263L171 309Q196 339 229 309L222 263" :fill="`url(#${id}-skin)`"/>
      <path d="M177 264Q195 295 223 273L225 288Q197 303 175 285Z" fill="#dda79d" opacity=".5"/>
      <path d="M157 301L173 294Q199 319 228 294L246 306Q235 343 200 341Q170 338 157 301Z" :fill="t.collar"/>
      <path d="M165 304Q179 332 201 333Q226 333 238 307" fill="none" :stroke="t.collarStroke" stroke-width="2"/>
      <g stroke-width="2" opacity=".42" :stroke="t.knit"><path d="M173 301L180 320M181 307L186 325M190 312L193 328M201 313V330M211 312L209 329M221 309L217 326M230 302L226 319"/></g>
      <path d="M137 358Q157 382 151 480M258 355Q241 391 247 480" fill="none" stroke="#fff" stroke-opacity=".12" stroke-width="2"/>
      <path d="M176 370Q197 383 222 370" fill="none" :stroke="t.hem" stroke-width="1.5" opacity=".5"/>
      <rect x="220" y="371" width="25" height="31" rx="7" :fill="t.pouch" transform="rotate(5 220 371)"/>
      <path d="M227 383V394M232 378V396M237 382V393" :stroke="t.pouchLine" stroke-width="2.5" stroke-linecap="round"/>
    </g>
    <g class="head-pose" :transform="head">
      <!-- 圆润短发，层次高光保持克制。 -->
      <path d="M117 242Q88 194 108 127Q117 77 173 69Q231 42 274 93Q309 125 294 190Q291 237 262 282Q248 300 224 293L145 288Q124 279 117 242Z" :fill="`url(#${id}-hair)`"/>
      <path d="M127 204Q110 189 110 215Q110 239 132 243M268 204Q287 192 287 217Q284 240 264 243" fill="#efc1ae"/>
      <path d="M131 156Q140 115 201 117Q253 115 271 158L263 232Q258 265 221 283Q201 293 181 281Q144 263 136 231Z" :fill="`url(#${id}-skin)`"/>
      <path d="M137 182Q143 229 151 243" stroke="#fff4e9" stroke-width="4" fill="none" opacity=".65"/>
      <ellipse cx="155" cy="230" rx="22" ry="14" :fill="`url(#${id}-blush)`"/><ellipse cx="244" cy="230" rx="22" ry="14" :fill="`url(#${id}-blush)`"/>
      <g class="brows" fill="none" stroke="#62464c" stroke-width="3.4" stroke-linecap="round"><path d="M149 177Q161 171 176 177"/><path d="M222 177Q237 169 249 177"/></g>
      <g class="eye-blink">
        <g v-for="x in [162, 237]" :key="x">
          <path :d="`M${x-15} 198Q${x} 186 ${x+15} 198Q${x} 214 ${x-15} 198Z`" fill="#fff8f1"/>
          <g :transform="eyes"><ellipse :cx="x" cy="199" rx="8.4" ry="10" :fill="`url(#${id}-iris)`"/><ellipse :cx="x" cy="198" rx="4.3" ry="6.4" fill="#302b39"/><circle :cx="x+3" cy="194" r="3.2" fill="#fff"/><circle :cx="x-3" cy="202" r="1.4" fill="#eed0b9"/></g>
          <path :d="`M${x-16} 198Q${x-1} 183 ${x+15} 197`" fill="none" stroke="#46333f" stroke-width="3.2" stroke-linecap="round"/>
          <path :d="`M${x-15} 197l-3 -3`" stroke="#46333f" stroke-width="2" stroke-linecap="round"/>
        </g>
      </g>
      <g v-if="happy" class="smile-eyes" stroke="#62454e" stroke-width="3" stroke-linecap="round" fill="none"><path d="M148 198Q162 183 177 198M222 198Q236 183 251 198"/></g>
      <path d="M199 204L195 224Q198 227 204 224" fill="none" stroke="#d29e92" stroke-width="2" stroke-linecap="round"/>
      <path d="M196 231h9" stroke="#fff0df" stroke-width="2" stroke-linecap="round"/>
      <g v-if="state === 'speaking' && lipSync" class="talk-mouth"><ellipse cx="201" cy="245" rx="10" ry="6" fill="#8d4b5b"/><path d="M194 241Q201 243 208 241" stroke="#fff5ec" stroke-width="2.5" stroke-linecap="round"/></g>
      <g v-else><path :d="happy ? 'M189 241Q201 261 215 241Q201 247 189 241Z' : 'M190 243Q201 251 213 242'" :fill="happy ? '#a35c69' : 'none'" stroke="#a35c69" stroke-width="2.2" stroke-linecap="round"/><path d="M198 251h7" stroke="#fff0df" stroke-width="2" stroke-linecap="round"/></g>
      <path d="M115 174Q105 116 147 92Q192 59 243 88Q284 108 278 172L262 189Q265 140 239 124Q219 160 173 164Q195 144 196 126Q174 155 132 172L129 210Q115 200 115 174Z" :fill="`url(#${id}-hair)`"/>
      <g fill="none" stroke-linecap="round"><path d="M130 129Q145 88 185 88M143 140Q167 95 210 93M237 95Q261 108 270 140" :stroke="t.hairHi" stroke-width="3" opacity=".32"/><path d="M123 222Q125 257 143 272M274 217Q274 253 253 271" :stroke="t.hairHi" stroke-width="2" opacity=".32"/></g>
      <path d="M247 142l15 8M245 149l14 8" :stroke="t.pin" stroke-width="4" stroke-linecap="round"/>
      <!-- 轻量耳麦与小耳饰，增强交流伙伴的身份。 -->
      <path d="M113 202Q92 100 159 82" fill="none" :stroke="t.earBand" stroke-width="7"/>
      <rect x="107" y="193" width="20" height="40" rx="10" :fill="t.earPiece" :stroke="t.earStroke" stroke-width="3"/>
      <path d="M116 226Q117 252 167 250" fill="none" :stroke="t.earPiece" stroke-width="4"/>
      <rect x="163" y="246" width="14" height="8" rx="4" :fill="t.mic"/>
      <circle cx="273" cy="235" r="4" fill="#e9c58d"/>
    </g>
  </svg>
  <AlternatePortrait v-else :character="character" :gaze="gaze" :happy="happy" :state="state" :lip-sync="lipSync" :animated="animated" :name="name" />
</template>

<style scoped>
.portrait { width: 100%; height: 100%; overflow: visible; }
.head-pose { transition: transform .2s ease-out; }
.eye-blink { transform-box: fill-box; transform-origin: center; }
.happy .eye-blink { opacity: 0; }
.talk-mouth { transform-box: fill-box; transform-origin: center; }
@media (prefers-reduced-motion: no-preference) {
  .animated .body { animation: breathe 4s ease-in-out infinite; transform-origin: 200px 450px; }
  .animated .eye-blink { animation: blink 5.7s infinite; }
  .animated.is-listening .eye-blink { animation-duration: 8s; }
  .animated.is-speaking .talk-mouth { animation: talk .32s ease-in-out infinite alternate; }
  .animated.is-thinking .brows { transform: translateY(-3px); }
}
@keyframes breathe { 50% { transform: translateY(-2px) scaleY(1.006); } }
@keyframes blink { 0%, 94%, 98%, 100% { transform: scaleY(1); } 96% { transform: scaleY(.08); } }
@keyframes talk { from { transform: scaleY(.4); } to { transform: scaleY(1.15); } }
@media (prefers-reduced-motion: reduce) { .head-pose { transition: none; } }
</style>
