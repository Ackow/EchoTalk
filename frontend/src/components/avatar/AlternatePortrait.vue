<script setup>
import { computed, getCurrentInstance } from 'vue'

const props = defineProps({
  character: { type: String, required: true },
  gaze: { type: Object, default: () => ({ x: 0, y: 0 }) },
  happy: Boolean,
  state: { type: String, default: 'idle' },
  lipSync: { type: Boolean, default: true },
  animated: { type: Boolean, default: true },
  name: { type: String, default: '' },
})
// 每种形象有独立轮廓和服装；只共享互动参数和绘制坐标，避免换色冒充角色。
const variant = computed(() => props.character === 'nora_2d' ? 'nora' : props.character === 'iris_2d' ? 'iris' : 'vera')
const designs = {
  vera: {
    hair: ['#504135', '#302b27', '#221f21'], skin: ['#f8e5d0', '#e7bb9c', '#dca78c'], iris: ['#47514b', '#8d9c77'],
    outfit: ['#82b8a6', '#568774', '#3f6659'],
    face: 'M132 154Q150 119 201 119Q245 119 268 158L261 222Q255 253 223 278L200 291L178 279Q143 255 138 224Z',
    brow: 'M146 179L173 176M224 176L251 180',
    back: 'M128 219Q101 164 119 116Q129 77 172 72Q223 53 262 88Q290 108 283 171L268 228L252 226L145 230Z',
    fringe: 'M120 167Q102 112 148 89Q202 61 250 88Q281 110 279 174L264 194L261 154Q250 128 236 116Q203 151 144 154L135 199Z',
    description: '高马尾、白衬衫和绿色马甲',
  },
  nora: {
    hair: ['#414454', '#2c3042', '#1e2232'], skin: ['#fff0e2', '#f0cfc2', '#dfb2ad'], iris: ['#3d465d', '#8592b1'],
    outfit: ['#687b9e', '#435773', '#2d3e58'],
    face: 'M133 152Q151 120 200 117Q252 118 269 157L263 220Q262 261 220 284Q201 292 181 282Q140 261 137 223Z',
    brow: 'M149 180Q163 173 176 180M222 180Q237 174 250 181',
    back: 'M110 167Q103 104 149 81Q201 48 254 81Q293 99 291 161L300 325Q281 341 254 324L141 325Q120 339 99 324Z',
    fringe: 'M111 182Q99 115 148 86Q198 55 251 83Q291 109 281 179L265 203L258 147Q222 132 201 111Q178 140 140 150L134 211Z',
    description: '长直发、圆框眼镜和藏蓝外套',
  },
  iris: {
    hair: ['#b66a43', '#874b35', '#5f342b'], skin: ['#ffedd6', '#f4ccab', '#e6aa8f'], iris: ['#634532', '#c39857'],
    outfit: ['#f1d393', '#dcb36f', '#bd8d53'],
    face: 'M129 158Q144 123 201 123Q255 124 270 160L264 224Q264 262 223 282Q202 293 180 283Q139 266 135 226Z',
    brow: 'M145 178Q159 167 176 176M222 176Q239 168 253 179',
    back: 'M117 218Q102 205 109 183Q95 166 106 148Q97 123 119 110Q115 85 141 83Q156 62 180 72Q202 57 223 72Q253 66 266 89Q289 89 289 116Q306 133 294 157Q305 179 286 192Q293 217 270 230L257 253L140 251Z',
    fringe: 'M119 180Q97 162 113 142Q99 122 126 108Q125 82 151 91Q167 69 187 87Q208 71 226 89Q248 76 258 103Q287 101 279 128Q298 148 277 173L263 196L259 150Q244 137 225 143Q224 120 205 126Q190 152 169 143Q151 163 134 155L133 204Z',
    description: '双丸子卷发、雀斑和黄色连帽衫',
  },
}
const d = computed(() => designs[variant.value])
const id = `portrait-${getCurrentInstance().uid}`
const eyes = computed(() => `translate(${props.gaze.x * 2.6} ${props.gaze.y * 1.8})`)
const head = computed(() => `translate(${props.gaze.x * 1.8} ${props.gaze.y}) rotate(${props.gaze.x * 1.4} 200 185)`)
const eyeWidth = computed(() => variant.value === 'vera' ? 14 : variant.value === 'iris' ? 17 : 15)
const eyeHeight = computed(() => variant.value === 'vera' ? 9 : variant.value === 'iris' ? 15 : 11)
</script>

<template>
  <svg viewBox="0 0 400 480" xmlns="http://www.w3.org/2000/svg" class="portrait" :class="[variant, { animated, happy }, `is-${state}`]" role="img" :aria-label="`${name}，${d.description}`" :data-character="variant">
    <defs>
      <linearGradient :id="`${id}-hair`" x2="1" y2="1"><stop :stop-color="d.hair[0]"/><stop offset=".55" :stop-color="d.hair[1]"/><stop offset="1" :stop-color="d.hair[2]"/></linearGradient>
      <linearGradient :id="`${id}-skin`" x2=".8" y2="1"><stop :stop-color="d.skin[0]"/><stop offset=".65" :stop-color="d.skin[1]"/><stop offset="1" :stop-color="d.skin[2]"/></linearGradient>
      <linearGradient :id="`${id}-outfit`" x2="1" y2="1"><stop :stop-color="d.outfit[0]"/><stop offset=".5" :stop-color="d.outfit[1]"/><stop offset="1" :stop-color="d.outfit[2]"/></linearGradient>
      <linearGradient :id="`${id}-iris`" x2="0" y2="1"><stop :stop-color="d.iris[0]"/><stop offset="1" :stop-color="d.iris[1]"/></linearGradient>
      <radialGradient :id="`${id}-blush`"><stop stop-color="#df8b87" stop-opacity=".48"/><stop offset="1" stop-color="#df8b87" stop-opacity="0"/></radialGradient>
    </defs>
    <!-- 后发作为独立层放在肩部后方，长发与马尾都保持完整的外轮廓。 -->
    <g :transform="head" class="head-pose">
      <path v-if="variant === 'vera'" d="M252 100Q288 62 308 105Q338 167 294 281Q316 222 296 179Q280 154 267 145Z" :fill="`url(#${id}-hair)`"/>
      <path :d="d.back" :fill="`url(#${id}-hair)`"/>
      <g v-if="variant === 'iris'" :fill="`url(#${id}-hair)`">
        <path d="M128 122Q87 129 85 99Q73 83 91 69Q83 48 105 46Q125 30 140 50Q163 51 157 75Q174 100 148 117Z"/>
        <path d="M257 117Q286 131 305 107Q327 97 312 76Q320 54 298 49Q279 31 264 49Q241 46 240 69Q227 92 248 104Z"/>
        <path d="M97 75Q104 55 126 62M268 64Q289 52 300 77" fill="none" stroke="#df9d69" stroke-width="3" opacity=".55"/>
      </g>
    </g>
    <g class="body">
      <!-- Vera：衬衫袖口、V 领马甲、细金项链。 -->
      <g v-if="variant === 'vera'">
        <path d="M150 297Q99 307 81 344L63 480H339L323 347Q300 310 248 297Z" fill="#f5f0e6"/>
        <path d="M117 315L158 300L200 344L242 300L283 317L274 480H123Z" :fill="`url(#${id}-outfit)`"/>
        <path d="M115 319Q133 366 126 478M282 318Q265 369 274 478" fill="none" stroke="#314f44" stroke-width="2" opacity=".35"/>
        <path d="M200 346V480" stroke="#e0dfc8" stroke-width="2" opacity=".65"/>
        <g fill="#ded5b1"><circle cx="200" cy="380" r="3"/><circle cx="200" cy="415" r="3"/><circle cx="200" cy="449" r="3"/></g>
        <path d="M227 386h29v4h-29Z" fill="#375c4f"/><path d="M238 364l8-12 8 12-8 4Z" fill="#d5c397"/>
        <path d="M92 363Q94 406 87 477M311 361Q306 405 316 477" fill="none" stroke="#dedbd4" stroke-width="2"/>
      </g>
      <!-- Nora：宽翻领外套、奶白高领内搭、胸前笔袋。 -->
      <g v-else-if="variant === 'nora'">
        <path d="M147 298Q102 308 82 347L67 480H334L320 348Q297 312 251 297Z" :fill="`url(#${id}-outfit)`"/>
        <path d="M162 299H236L247 480H152Z" fill="#eee9df"/>
        <path d="M148 302L163 294L183 480H155L125 352L151 338L133 330Z" fill="#7285a2"/>
        <path d="M249 300L236 294L215 480H244L274 352L248 338L266 330Z" fill="#607593"/>
        <path d="M125 352L156 460M274 352L246 460" stroke="#91a1b8" stroke-width="1.6" fill="none" opacity=".55"/>
        <path d="M98 366L93 480M301 366L308 480" fill="none" stroke="#293b54" stroke-width="2" opacity=".5"/>
        <path d="M254 386h25v5h-25Z" fill="#2e405a"/><path d="M261 374v15M269 377v12" stroke="#bbced5" stroke-width="3"/>
        <circle cx="153" cy="393" r="3.5" fill="#ced1d1"/>
      </g>
      <!-- Iris：大帽领与抽绳、斜挎带、花朵徽章。 -->
      <g v-else>
        <path d="M139 304Q95 315 78 354L58 480H342L326 355Q306 317 256 304Z" :fill="`url(#${id}-outfit)`"/>
        <path d="M144 297Q122 314 141 346Q173 373 202 341Q230 373 260 343Q277 315 252 296L230 308H167Z" fill="#edca8c" stroke="#c69b5f" stroke-width="2"/>
        <path d="M156 307Q146 330 173 343M240 307Q252 330 230 343" fill="none" stroke="#ffe5af" stroke-width="3"/>
        <path d="M172 342L168 392M230 342L233 393" stroke="#fff1cb" stroke-width="3" stroke-linecap="round"/>
        <rect x="164" y="389" width="7" height="10" rx="2" fill="#a7764c"/><rect x="230" y="390" width="7" height="10" rx="2" fill="#a7764c"/>
        <path d="M116 320L253 480" stroke="#9b6750" stroke-width="16"/><path d="M116 320L253 480" stroke="#c48b68" stroke-width="10"/>
        <path d="M93 371Q95 416 84 480M305 371Q301 420 313 480" fill="none" stroke="#b98852" stroke-width="2" opacity=".5"/>
        <g transform="translate(257 378)"><g fill="#fff1cc"><ellipse cy="-7" rx="4" ry="7"/><ellipse cy="7" rx="4" ry="7"/><ellipse cx="-7" rx="7" ry="4"/><ellipse cx="7" rx="7" ry="4"/></g><circle r="4" fill="#be8155"/></g>
      </g>
      <path d="M177 263L171 309Q199 330 230 309L223 263" :fill="`url(#${id}-skin)`"/>
      <path d="M178 269Q199 292 224 277L226 290Q200 301 175 287Z" fill="#b87d71" opacity=".23"/>
      <g v-if="variant === 'vera'"><path d="M171 297L197 326L174 338L153 312ZM230 297L202 326L226 339L250 312Z" fill="#fff9ee" stroke="#e3ddd1" stroke-width="1.5"/><path d="M181 304Q199 321 218 304" stroke="#ceac6f" stroke-width="2" fill="none"/><circle cx="200" cy="315" r="3" fill="#ceac6f"/></g>
      <g v-else-if="variant === 'nora'"><path d="M169 294Q199 307 231 294L233 319Q202 331 166 319Z" fill="#f3eee5"/><path d="M175 298v22M183 301v22M192 303v22M201 304v23M211 303v22M222 299v22" stroke="#d7d1c9" stroke-width="1.3"/></g>
      <path v-else d="M166 308Q199 335 234 308L232 325Q199 349 169 326Z" fill="#a87b51" opacity=".55"/>
    </g>
    <g :transform="head" class="head-pose">
      <!-- 薇拉的耳廓贴近下颌，耳根藏在鬓发与面部后方，避免两侧突出。 -->
      <path :d="variant === 'vera' ? 'M139 203Q126 197 125 210Q125 225 138 231L142 224ZM262 203Q275 198 276 210Q276 225 263 231L259 223Z' : 'M128 204Q109 190 110 217Q111 238 133 241M269 204Q287 194 287 217Q284 240 264 243'" :fill="d.skin[1]"/>
      <path v-if="variant === 'vera'" d="M132 207Q128 208 130 217M269 207Q273 209 271 217" fill="none" stroke="#c7977f" stroke-width="1.3" stroke-linecap="round"/>
      <path :d="d.face" :fill="`url(#${id}-skin)`"/>
      <path d="M140 184Q145 228 153 242" stroke="#fff3e5" stroke-width="3" fill="none" opacity=".5"/>
      <ellipse cx="154" cy="231" rx="23" ry="14" :fill="`url(#${id}-blush)`"/><ellipse cx="245" cy="231" rx="23" ry="14" :fill="`url(#${id}-blush)`"/>
      <g class="brows" fill="none" :stroke="d.hair[1]" :stroke-width="variant === 'vera' ? 3.6 : 2.7" stroke-linecap="round"><path :d="d.brow"/></g>
      <g class="eye-blink">
        <g v-for="x in [162, 237]" :key="x">
          <path :d="`M${x-eyeWidth} 199Q${x} ${199-eyeHeight} ${x+eyeWidth} 199Q${x} ${199+eyeHeight} ${x-eyeWidth} 199Z`" fill="#fffaf1"/>
          <g :transform="eyes"><ellipse :cx="x" cy="199" :rx="variant === 'iris' ? 9 : 7.5" :ry="variant === 'iris' ? 11 : 8.5" :fill="`url(#${id}-iris)`"/><ellipse :cx="x" cy="198" rx="3.8" ry="5.5" fill="#292c34"/><circle :cx="x+2.8" cy="194" r="2.7" fill="#fff"/><circle :cx="x-3" cy="202" r="1.1" fill="#f7d7b4"/></g>
          <path :d="`M${x-eyeWidth-1} 199Q${x} ${197-eyeHeight} ${x+eyeWidth} 198`" fill="none" :stroke="d.hair[2]" stroke-width="2.6" stroke-linecap="round"/>
        </g>
      </g>
      <g v-if="happy" class="smile-eyes" :stroke="d.hair[1]" stroke-width="2.8" stroke-linecap="round" fill="none"><path d="M148 198Q162 185 177 198M222 198Q236 185 251 198"/></g>
      <path :d="variant === 'vera' ? 'M201 203L196 226Q201 231 207 227' : 'M199 207L195 224Q200 228 205 224'" fill="none" stroke="#b88576" stroke-width="1.8" stroke-linecap="round"/>
      <g v-if="variant === 'iris'" fill="#bc7c60" opacity=".65"><circle cx="147" cy="224" r="1.4"/><circle cx="154" cy="220" r="1.5"/><circle cx="160" cy="226" r="1.4"/><circle cx="242" cy="224" r="1.4"/><circle cx="249" cy="219" r="1.5"/><circle cx="255" cy="225" r="1.4"/><circle cx="191" cy="220" r="1"/><circle cx="206" cy="220" r="1"/></g>
      <g v-if="state === 'speaking' && lipSync" class="talk-mouth"><ellipse cx="201" cy="247" rx="10" ry="6" fill="#8d4b5b"/><path d="M194 243Q201 245 208 243" stroke="#fff5ec" stroke-width="2.5" stroke-linecap="round"/></g>
      <g v-else><path :d="happy ? 'M188 244Q201 264 216 244Q201 250 188 244Z' : variant === 'vera' ? 'M190 246Q202 251 212 244' : variant === 'iris' ? 'M187 243Q201 257 216 242' : 'M192 246Q201 253 212 246'" :fill="happy ? '#a35c69' : 'none'" stroke="#a35c69" stroke-width="2" stroke-linecap="round"/><path d="M198 255h7" stroke="#fff0df" stroke-width="2" stroke-linecap="round"/></g>
      <path :d="d.fringe" :fill="`url(#${id}-hair)`"/>
      <g v-if="variant === 'vera'" fill="none" stroke-linecap="round"><path d="M127 126Q154 91 206 91M143 136Q176 123 207 103M275 116Q299 91 303 132Q306 160 295 186" stroke="#ad9279" stroke-width="2.5" opacity=".35"/><path d="M269 113l15 4" stroke="#b4caba" stroke-width="6"/><circle cx="132" cy="231" r="3.6" stroke="#d7b56d" stroke-width="2"/><circle cx="269" cy="231" r="3.6" stroke="#d7b56d" stroke-width="2"/></g>
      <g v-else-if="variant === 'nora'">
        <path d="M119 160Q117 107 158 88M262 111Q282 164 279 213M111 219L116 292M284 217L286 290" stroke="#8393b3" stroke-width="2.5" fill="none" opacity=".25"/>
        <!-- 眼镜覆盖眼部而不挡住视线跟随；开心时依然显示笑眼。 -->
        <g fill="#d1e4ec" fill-opacity=".12" stroke="#ac987c" stroke-width="2.6"><circle cx="161" cy="201" r="23"/><circle cx="238" cy="201" r="23"/><path d="M184 199Q199 191 215 199M137 198L127 193M262 197L273 192" fill="none"/></g>
        <path d="M145 190l8-6M222 190l8-6" stroke="#fff9e5" stroke-width="2.2" stroke-linecap="round" opacity=".7"/>
        <circle cx="126" cy="240" r="3" fill="#dce4ec"/><circle cx="274" cy="239" r="3" fill="#dce4ec"/>
      </g>
      <g v-else>
        <path d="M121 123Q130 101 146 110M154 102Q171 83 182 101M225 105Q245 97 249 118" stroke="#d89868" stroke-width="2.7" fill="none" opacity=".5" stroke-linecap="round"/>
        <path d="M111 120l-5 9M276 118l6 9" stroke="#eaca7e" stroke-width="6" stroke-linecap="round"/>
        <path d="M270 171l9 3-8 4 1-9 5 7" fill="#f7d783" stroke="#f7d783" stroke-width="1.4" stroke-linejoin="round"/>
        <circle cx="126" cy="236" r="4" fill="#d77e60"/><circle cx="275" cy="237" r="4" fill="#d77e60"/>
      </g>
    </g>
  </svg>
</template>

<style scoped>
.portrait { width: 100%; height: 100%; overflow: visible; }
.head-pose { transition: transform .2s ease-out; }
.eye-blink, .talk-mouth { transform-box: fill-box; transform-origin: center; }
.happy .eye-blink { opacity: 0; }
@media (prefers-reduced-motion: no-preference) {
  .animated .body { animation: breathe 4s ease-in-out infinite; transform-origin: 200px 450px; }
  .animated.vera .body { animation-duration: 4.6s; }
  .animated.iris .body { animation-duration: 3.6s; }
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
