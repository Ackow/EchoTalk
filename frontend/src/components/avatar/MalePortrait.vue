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
const noah = computed(() => props.character === 'nora_2d')
const id = `male-${getCurrentInstance().uid}`
const head = computed(() => `translate(${props.gaze.x * 1.8} ${props.gaze.y}) rotate(${props.gaze.x * 1.4} 200 185)`)
const eyes = computed(() => `translate(${props.gaze.x * 2.6} ${props.gaze.y * 1.8})`)
</script>

<template>
  <svg viewBox="0 0 400 480" xmlns="http://www.w3.org/2000/svg" class="portrait" :class="[{ animated, happy }, `is-${state}`]" role="img" :aria-label="`${name}，${noah ? '短发、方框眼镜和西装' : '卷发、雀斑和连帽衫'}的交流伙伴`">
    <defs>
      <linearGradient :id="`${id}-skin`" x2=".8" y2="1"><stop :stop-color="noah ? '#f5dfce' : '#f1cfaa'"/><stop offset="1" :stop-color="noah ? '#d7aa95' : '#cf9873'"/></linearGradient>
      <linearGradient :id="`${id}-hair`" x2="1" y2="1"><stop :stop-color="noah ? '#454654' : '#9a6246'"/><stop offset="1" :stop-color="noah ? '#202635' : '#593b30'"/></linearGradient>
      <linearGradient :id="`${id}-clothes`" x2="1" y2="1"><stop :stop-color="noah ? '#788da8' : '#efcf8c'"/><stop offset="1" :stop-color="noah ? '#354a66' : '#b7864b'"/></linearGradient>
    </defs>
    <g class="body">
      <path d="M150 296Q95 304 72 350L51 480H349L329 350Q305 305 250 296Z" :fill="`url(#${id}-clothes)`"/>
      <path d="M177 259L171 305Q200 330 229 305L223 259" :fill="`url(#${id}-skin)`"/>
      <g v-if="noah">
        <path d="M169 298L200 329L231 298L244 480H155Z" fill="#f3f1e9"/>
        <path d="M155 299L122 318L143 355L127 363L174 449L200 329Z" fill="#637994"/>
        <path d="M245 299L278 318L257 355L273 363L226 449L200 329Z" fill="#526a87"/>
        <path d="M189 324L200 337L211 324L206 356L200 368L194 356Z" fill="#92796e"/>
        <path d="M251 388h26" stroke="#cbd5de" stroke-width="3"/>
      </g>
      <g v-else>
        <path d="M150 302Q137 325 160 348Q200 368 240 348Q263 325 250 302L231 307Q200 337 169 307Z" fill="#e4b975" stroke="#bd925d" stroke-width="2"/>
        <path d="M175 343L172 393M225 343L228 393" stroke="#fff0ca" stroke-width="3" stroke-linecap="round"/>
        <path d="M143 424Q200 403 257 424L264 480H136Z" fill="#c99b5e" opacity=".5"/>
      </g>
      <path d="M97 365Q100 416 89 480M303 365Q300 416 311 480" fill="none" stroke="#253348" stroke-opacity=".18" stroke-width="3"/>
    </g>
    <g :transform="head" class="head-pose">
      <path d="M126 204Q110 194 111 216Q112 237 134 241M268 204Q288 194 288 216Q286 237 266 241" :fill="`url(#${id}-skin)`"/>
      <path d="M128 153Q132 102 200 102Q266 102 273 154L263 229Q257 264 225 282Q200 297 176 282Q143 264 137 229Z" :fill="`url(#${id}-skin)`"/>
      <path :d="noah ? 'M126 181Q104 125 132 95Q157 64 208 71Q261 66 276 111Q286 138 272 184L262 168L259 136Q232 144 202 119Q180 142 141 145L138 177Z' : 'M126 182Q112 166 119 150Q107 132 122 120Q118 100 139 94Q146 74 168 80Q183 64 203 76Q224 62 240 80Q262 74 270 94Q290 103 280 124Q291 140 277 155L271 181L260 159Q244 162 232 144Q213 155 199 137Q181 153 165 141Q154 157 139 153L137 180Z'" :fill="`url(#${id}-hair)`"/>
      <path :d="noah ? 'M135 113Q158 86 195 89M211 91Q243 89 262 114' : 'M134 116Q143 98 158 106M181 96Q192 83 203 97M226 99Q239 89 252 106'" fill="none" stroke="#c7a08c" stroke-width="3" stroke-linecap="round" opacity=".4"/>
      <g class="brows" fill="none" :stroke="noah ? '#3d3a41' : '#714b3a'" stroke-width="4" stroke-linecap="round"><path d="M146 179Q160 172 177 179M223 179Q239 172 253 179"/></g>
      <g class="eye-blink">
        <g v-for="x in [162, 238]" :key="x">
          <path :d="`M${x-14} 199Q${x} 188 ${x+14} 199Q${x} 210 ${x-14} 199Z`" fill="#fffaf3"/>
          <g :transform="eyes"><ellipse :cx="x" cy="199" rx="7" ry="8.5" :fill="noah ? '#536274' : '#805b40'"/><ellipse :cx="x" cy="199" rx="3.5" ry="5" fill="#292c34"/><circle :cx="x+2" cy="196" r="2.4" fill="white"/></g>
          <path :d="`M${x-14} 199Q${x} 187 ${x+14} 199`" fill="none" stroke="#493b39" stroke-width="2.5" stroke-linecap="round"/>
        </g>
      </g>
      <path v-if="happy" d="M148 199Q162 187 176 199M224 199Q238 187 252 199" fill="none" stroke="#604b45" stroke-width="3" stroke-linecap="round"/>
      <path d="M200 204L195 225Q200 230 207 225" fill="none" stroke="#b98470" stroke-width="2" stroke-linecap="round"/>
      <g v-if="!noah" fill="#ae7458" opacity=".7"><circle cx="150" cy="224" r="1.5"/><circle cx="157" cy="221" r="1.5"/><circle cx="244" cy="221" r="1.5"/><circle cx="251" cy="224" r="1.5"/></g>
      <g v-if="state === 'speaking' && lipSync" class="talk-mouth"><ellipse cx="200" cy="247" rx="10" ry="6" fill="#88534e"/><path d="M194 244H206" stroke="#fff6ec" stroke-width="2"/></g>
      <path v-else :d="happy ? 'M187 243Q200 262 214 243' : 'M190 245Q200 251 211 245'" fill="none" stroke="#925d55" stroke-width="2.5" stroke-linecap="round"/>
      <g v-if="noah" fill="#dce9ee" fill-opacity=".12" stroke="#65717d" stroke-width="3"><rect x="136" y="183" width="49" height="35" rx="9"/><rect x="215" y="183" width="49" height="35" rx="9"/><path d="M185 194Q200 187 215 194M136 193L126 189M264 193L274 189" fill="none"/></g>
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
