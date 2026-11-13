<script setup>
import { computed, getCurrentInstance } from 'vue'
import { resolveAppearance, SKIN_TONES } from './avatarAppearance'

const props = defineProps({
  character: { type: String, default: 'leo_2d' },
  appearance: { type: Object, default: null },
  gaze: { type: Object, default: () => ({ x: 0, y: 0 }) },
  happy: Boolean,
  state: { type: String, default: 'idle' },
  lipSync: { type: Boolean, default: true },
  animated: { type: Boolean, default: true },
  name: { type: String, default: 'Leo' },
})

const uid = `scene-${getCurrentInstance().uid}`
const ap = computed(() => resolveAppearance(props.character, props.appearance))
const skin = computed(() => SKIN_TONES[ap.value.skinTone] || SKIN_TONES.warm)

const pupilTransform = computed(() => {
  if (props.state === 'thinking' && !props.happy) {
    return `translate(${(2.6 + props.gaze.x * 1.4).toFixed(2)} ${(-2.6 + props.gaze.y * 1.2).toFixed(2)})`
  }
  return `translate(${(props.gaze.x * 3.4).toFixed(2)} ${(props.gaze.y * 2.4).toFixed(2)})`
})
const headTransform = computed(() => `translate(${(props.gaze.x * 1.8).toFixed(2)} ${(props.gaze.y * 1.1).toFixed(2)}) rotate(${(props.gaze.x * 1.3).toFixed(2)} 200 185)`)
const showTalking = computed(() => props.state === 'speaking' && props.lipSync && !props.happy)
const showThinking = computed(() => props.state === 'thinking' && !props.happy)
const showListening = computed(() => props.state === 'listening' && !props.happy)
const showHappy = computed(() => props.happy || props.state === 'happy')

const eyeRy = computed(() => (ap.value.eyeStyle === 'gentle' ? 12 : ap.value.eyeStyle === 'calm' ? 10.2 : 11))
const irisR = computed(() => (ap.value.eyeStyle === 'calm' ? 6.2 : 6.8))
</script>

<template>
  <svg
    :data-character="character"
    viewBox="32 48 336 392"
    preserveAspectRatio="xMidYMax meet"
    xmlns="http://www.w3.org/2000/svg"
    class="portrait"
    :class="[{ animated, happy: showHappy, talking: showTalking }, `is-${state}`]"
    role="img"
    :aria-label="`${name}，数字人交流伙伴`"
  >
    <defs>
      <linearGradient :id="`${uid}-skin`" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" :stop-color="skin.top" />
        <stop offset="100%" :stop-color="skin.bottom" />
      </linearGradient>
      <linearGradient :id="`${uid}-apron`" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#7c63c9" />
        <stop offset="100%" stop-color="#5a449e" />
      </linearGradient>
      <linearGradient :id="`${uid}-blazer`" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#6d56a8" />
        <stop offset="100%" stop-color="#4e3b82" />
      </linearGradient>
      <linearGradient :id="`${uid}-suit`" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#48426d" />
        <stop offset="100%" stop-color="#302b4d" />
      </linearGradient>
      <linearGradient :id="`${uid}-cardigan`" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#53407d" />
        <stop offset="100%" stop-color="#39295c" />
      </linearGradient>
    </defs>

    <!-- Listening State: Side Ear Sound Waves -->
    <g v-if="showListening" class="listen-waves" stroke="#8b73dd" stroke-width="4" stroke-linecap="round" fill="none" aria-hidden="true">
      <path d="M108,174 Q100,188 108,202" />
      <path d="M96,164 Q84,188 96,212" opacity="0.65" />
      <path d="M292,174 Q300,188 292,202" />
      <path d="M304,164 Q316,188 304,212" opacity="0.65" />
    </g>

    <!-- Back Hair Layer (for long / bun / ponytail styles) -->
    <path
      v-if="ap.hairStyle === 'shoulder_sleek'"
      d="M126,162 C116,228 118,296 138,324 L262,324 C282,296 284,228 274,162 C264,96 236,78 200,78 C164,78 136,96 126,162 Z"
      :fill="ap.hairColor"
      stroke="#3d2c56"
      stroke-width="4.5"
      stroke-linejoin="round"
    />
    <template v-else-if="ap.hairStyle === 'wavy_long'">
      <path
        d="M122,162 C108,200 124,232 114,268 C108,294 120,318 138,332 L262,332 C280,318 292,294 286,268 C276,232 292,200 278,162 C268,94 238,76 200,76 C162,76 132,94 122,162 Z"
        :fill="ap.hairColor"
        stroke="#3d2c56"
        stroke-width="4.5"
        stroke-linejoin="round"
      />
      <path d="M128,236 Q138,258 128,284 M272,236 Q262,258 272,284" fill="none" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round" opacity="0.16" />
    </template>
    <template v-else-if="ap.hairStyle === 'high_ponytail'">
      <path
        d="M236,98 C276,90 296,126 288,168 C282,196 290,228 274,256 C262,236 258,206 262,174 C264,142 252,120 234,114 Z"
        :fill="ap.hairColor"
        stroke="#3d2c56"
        stroke-width="4.5"
        stroke-linejoin="round"
      />
      <path d="M270,136 Q280,168 272,204" fill="none" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round" opacity="0.2" />
      <rect x="238" y="96" width="14" height="22" rx="7" transform="rotate(-18 245 107)" fill="#7b61ff" stroke="#3d2c56" stroke-width="3.5" />
    </template>

    <!-- Torso & Outfit Layer -->
    <g class="torso-group">
      <!-- Barista Apron -->
      <template v-if="ap.outfit === 'apron_violet'">
        <path d="M68,440 C74,342 118,308 158,302 L242,302 C282,308 326,342 332,440 Z"
              fill="#fffaf3" stroke="#3d2c56" stroke-width="4.5" stroke-linejoin="round" />
        <path d="M164,302 L182,334 L200,326 L218,334 L236,302" fill="#f3e8d8" stroke="#3d2c56" stroke-width="3.5" stroke-linejoin="round" />
        <line x1="200" y1="326" x2="200" y2="370" stroke="#3d2c56" stroke-width="3" />
        <path d="M126,326 L274,326 L288,440 L112,440 Z"
              :fill="`url(#${uid}-apron)`" stroke="#3d2c56" stroke-width="4.5" stroke-linejoin="round" />
        <path d="M138,305 L138,332" stroke="#5a449e" stroke-width="14" stroke-linecap="round" />
        <path d="M138,305 L138,332" stroke="#3d2c56" stroke-width="4" stroke-linecap="round" fill="none" />
        <path d="M262,305 L262,332" stroke="#5a449e" stroke-width="14" stroke-linecap="round" />
        <path d="M262,305 L262,332" stroke="#3d2c56" stroke-width="4" stroke-linecap="round" fill="none" />
        <circle cx="138" cy="332" r="6" fill="#fbbf24" stroke="#3d2c56" stroke-width="3" />
        <circle cx="262" cy="332" r="6" fill="#fbbf24" stroke="#3d2c56" stroke-width="3" />
        <rect x="164" y="368" width="72" height="50" rx="10" fill="#6b52b8" stroke="#3d2c56" stroke-width="3.5" />
        <circle cx="242" cy="352" r="13" fill="#fef3c7" stroke="#3d2c56" stroke-width="3" />
        <path d="M236,350 L248,350 L246,359 L238,359 Z" fill="#b45309" />
      </template>

      <!-- Airline Blazer + Scarf -->
      <template v-else-if="ap.outfit === 'airline_blazer'">
        <path d="M84,440 C90,348 130,312 166,306 L234,306 C270,312 310,348 316,440 Z"
              :fill="`url(#${uid}-blazer)`" stroke="#3d2c56" stroke-width="4.5" stroke-linejoin="round" />
        <path d="M168,306 L200,378 L232,306 Z" fill="#ffffff" stroke="#3d2c56" stroke-width="3.5" stroke-linejoin="round" />
        <path d="M168,306 L150,350 L176,368 L200,378" fill="#7d66ba" stroke="#3d2c56" stroke-width="3.5" stroke-linejoin="round" />
        <path d="M232,306 L250,350 L224,368 L200,378" fill="#7d66ba" stroke="#3d2c56" stroke-width="3.5" stroke-linejoin="round" />
        <path d="M174,302 Q200,322 226,302 L214,334 Q200,342 186,334 Z" fill="#34d399" stroke="#3d2c56" stroke-width="3.5" stroke-linejoin="round" />
        <path d="M196,332 L184,366 L204,358 L216,366 L206,332" fill="#a78bfa" stroke="#3d2c56" stroke-width="3" stroke-linejoin="round" />
        <path d="M236,362 L262,356 L256,366 L238,368 Z" fill="#fde68a" stroke="#3d2c56" stroke-width="2.5" stroke-linejoin="round" />
      </template>

      <!-- PM Slate-Indigo Suit -->
      <template v-else-if="ap.outfit === 'pm_suit'">
        <path d="M60,440 C66,338 112,304 156,298 L244,298 C288,304 334,338 340,440 Z"
              :fill="`url(#${uid}-suit)`" stroke="#3d2c56" stroke-width="4.5" stroke-linejoin="round" />
        <path d="M162,298 L200,398 L238,298 Z" fill="#f5f3ff" stroke="#3d2c56" stroke-width="3.5" stroke-linejoin="round" />
        <path d="M164,298 L178,336 L200,322 L222,336 L236,298" fill="#ffffff" stroke="#3d2c56" stroke-width="3.5" stroke-linejoin="round" />
        <line x1="200" y1="322" x2="200" y2="394" stroke="#cbd5e1" stroke-width="2.5" />
        <path d="M162,298 L138,348 L164,370 L200,398" fill="#595285" stroke="#3d2c56" stroke-width="3.5" stroke-linejoin="round" />
        <path d="M238,298 L262,348 L236,370 L200,398" fill="#595285" stroke="#3d2c56" stroke-width="3.5" stroke-linejoin="round" />
        <path d="M250,394 L268,382 L278,394 Z" fill="#a78bfa" stroke="#3d2c56" stroke-width="2.8" stroke-linejoin="round" />
      </template>

      <!-- Tech Cardigan -->
      <template v-else>
        <path d="M84,440 C90,348 130,312 168,306 L232,306 C270,312 310,348 316,440 Z"
              :fill="`url(#${uid}-cardigan)`" stroke="#3d2c56" stroke-width="4.5" stroke-linejoin="round" />
        <path d="M170,306 L200,378 L230,306 Z" fill="#ffffff" stroke="#3d2c56" stroke-width="3.5" stroke-linejoin="round" />
        <path d="M172,306 L186,336 L200,326 L214,336 L228,306" fill="#f8fafc" stroke="#3d2c56" stroke-width="3.2" stroke-linejoin="round" />
        <rect x="234" y="362" width="24" height="10" rx="4" fill="#c4b5fd" stroke="#3d2c56" stroke-width="2.5" />
      </template>

      <!-- Neck -->
      <path
        v-if="ap.base === 'male'"
        d="M171,260 L171,306 C171,319 229,319 229,306 L229,260 Z"
        :fill="skin.neck"
        stroke="#3d2c56"
        stroke-width="4.5"
      />
      <path
        v-else
        d="M180,258 L180,308 C180,316 220,316 220,308 L220,258 Z"
        :fill="skin.neck"
        stroke="#3d2c56"
        stroke-width="4.5"
      />
      <path d="M174,268 Q200,290 226,268 L226,280 Q200,298 174,280 Z" :fill="skin.shadow" opacity="0.45" />

      <!-- Torso Accessories: Bow Tie & Name Badge -->
      <g v-if="ap.accessory === 'bow_tie'">
        <path d="M200,322 L176,310 L176,334 Z" fill="#8b73dd" stroke="#3d2c56" stroke-width="3" stroke-linejoin="round" />
        <path d="M200,322 L224,310 L224,334 Z" fill="#8b73dd" stroke="#3d2c56" stroke-width="3" stroke-linejoin="round" />
        <circle cx="200" cy="322" r="5.5" fill="#6d55c7" stroke="#3d2c56" stroke-width="2.8" />
      </g>
      <g v-else-if="ap.accessory === 'name_badge'">
        <path d="M174,306 L154,366 M226,306 L168,366" fill="none" stroke="#8b73dd" stroke-width="3.2" stroke-linecap="round" />
        <rect x="142" y="366" width="38" height="26" rx="5" fill="#ffffff" stroke="#3d2c56" stroke-width="3" />
        <rect x="148" y="372" width="10" height="10" rx="3" fill="#a78bfa" />
        <line x1="162" y1="375" x2="174" y2="375" stroke="#3d2c56" stroke-width="2.5" stroke-linecap="round" />
        <line x1="162" y1="382" x2="172" y2="382" stroke="#9c95b0" stroke-width="2.2" stroke-linecap="round" />
      </g>
    </g>

    <!-- Head Group -->
    <g class="head-pose" :transform="headTransform">
      <!-- Low Bun behind ear -->
      <template v-if="ap.hairStyle === 'low_bun'">
        <circle cx="256" cy="206" r="24" :fill="ap.hairColor" stroke="#3d2c56" stroke-width="4.5" />
        <path d="M242,190 Q258,196 266,214" fill="none" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round" opacity="0.22" />
      </template>

      <!-- Back cap for short / pulled-back styles -->
      <path
        v-if="ap.hairStyle === 'undercut' || ap.hairStyle === 'low_bun' || ap.hairStyle === 'spiky_crop' || ap.hairStyle === 'high_ponytail'"
        d="M136,162 C130,110 160,74 200,74 C240,74 270,110 264,162 Z"
        :fill="ap.hairColor"
        stroke="#3d2c56"
        stroke-width="4.5"
      />
      <path
        v-else-if="ap.hairStyle === 'curly_short'"
        d="M128,166 C116,144 122,116 140,104 C146,82 172,68 200,70 C228,68 254,82 260,104 C278,116 284,144 272,166 Z"
        :fill="ap.hairColor"
        stroke="#3d2c56"
        stroke-width="4.5"
        stroke-linejoin="round"
      />

      <!-- Ears -->
      <path
        :d="ap.base === 'male' ? 'M139,179 C123,178 122,208 138,214' : 'M144,186 C132,186 132,208 146,212'"
        :fill="skin.bottom"
        stroke="#3d2c56"
        stroke-width="4"
        stroke-linecap="round"
      />
      <path
        :d="ap.base === 'male' ? 'M261,179 C277,178 278,208 262,214' : 'M256,186 C268,186 268,208 254,212'"
        :fill="skin.bottom"
        stroke="#3d2c56"
        stroke-width="4"
        stroke-linecap="round"
      />

      <!-- Pearl Earring Accessory -->
      <circle
        v-if="ap.accessory === 'earring_pearl'"
        :cx="ap.base === 'male' ? 136 : 141"
        cy="213"
        r="4.2"
        fill="#fefefe"
        stroke="#3d2c56"
        stroke-width="2.5"
      />

      <!-- Face Contour -->
      <path
        v-if="ap.base === 'male'"
        d="M139,150 C139,110 261,110 261,150 L259,205 C259,237 236,269 216,275 L184,275 C164,269 141,237 141,205 Z"
        :fill="`url(#${uid}-skin)`"
        stroke="#3d2c56"
        stroke-width="4.5"
        stroke-linejoin="round"
      />
      <path
        v-else
        d="M146,154 C146,114 254,114 254,154 L252,203 C251,242 225,268 200,270 C175,268 149,242 148,203 Z"
        :fill="`url(#${uid}-skin)`"
        stroke="#3d2c56"
        stroke-width="4.5"
      />

      <!-- Cheek blush / shading -->
      <ellipse cx="163" cy="213" rx="12" ry="6" :fill="ap.base === 'male' ? '#f49d84' : '#fda4af'" :opacity="ap.base === 'male' ? 0.26 : 0.38" />
      <ellipse cx="237" cy="213" rx="12" ry="6" :fill="ap.base === 'male' ? '#f49d84' : '#fda4af'" :opacity="ap.base === 'male' ? 0.26 : 0.38" />

      <!-- Nose -->
      <path
        :d="ap.base === 'male' ? 'M200,182 L196,210 L205,213' : 'M200,191 Q197,206 203,209'"
        fill="none"
        :stroke="skin.nose"
        :stroke-width="ap.base === 'male' ? 3.3 : 3"
        stroke-linecap="round"
        stroke-linejoin="round"
      />

      <!-- Eyes -->
      <g class="eye-blink">
        <ellipse cx="173" cy="187" rx="12.5" :ry="eyeRy" fill="#ffffff" stroke="#3d2c56" stroke-width="3.2" />
        <g :transform="pupilTransform">
          <circle cx="174" cy="188" :r="irisR" :fill="ap.eyeColor" />
          <circle cx="176" cy="185" r="2.2" fill="#ffffff" />
        </g>
        <path v-if="ap.base === 'female'" d="M159,182 Q173,173 186,182" fill="none" stroke="#3d2c56" stroke-width="3.4" stroke-linecap="round" />

        <ellipse cx="227" cy="187" rx="12.5" :ry="eyeRy" fill="#ffffff" stroke="#3d2c56" stroke-width="3.2" />
        <g :transform="pupilTransform">
          <circle cx="228" cy="188" :r="irisR" :fill="ap.eyeColor" />
          <circle cx="230" cy="185" r="2.2" fill="#ffffff" />
        </g>
        <path v-if="ap.base === 'female'" d="M214,182 Q227,173 241,182" fill="none" stroke="#3d2c56" stroke-width="3.4" stroke-linecap="round" />
      </g>

      <!-- Happy Eyes -->
      <g v-if="showHappy" class="smile-eyes" stroke="#3d2c56" stroke-width="3.5" stroke-linecap="round" fill="none">
        <path d="M159,187 Q173,175 187,187" />
        <path d="M213,187 Q227,175 241,187" />
      </g>

      <!-- Glasses Layer -->
      <g v-if="ap.glasses === 'rect_dark'" stroke="#2d294b" stroke-width="3.8" fill="#ffffff" fill-opacity="0.14">
        <rect x="148" y="172" width="46" height="28" rx="7" />
        <rect x="206" y="172" width="46" height="28" rx="7" />
        <line x1="194" y1="184" x2="206" y2="184" />
        <line x1="140" y1="182" x2="148" y2="184" />
        <line x1="252" y1="184" x2="260" y2="182" />
      </g>
      <g v-else-if="ap.glasses === 'round_violet'" stroke="#6d55c7" stroke-width="3" fill="#ffffff" fill-opacity="0.12">
        <circle cx="173" cy="187" r="21" />
        <circle cx="227" cy="187" r="21" />
        <path d="M194,185 Q200,181 206,185" fill="none" />
        <line x1="145" y1="183" x2="152" y2="185" />
        <line x1="248" y1="185" x2="255" y2="183" />
      </g>

      <!-- Eyebrows -->
      <g class="brows">
        <template v-if="ap.base === 'male'">
          <path d="M154,166 Q172,161 188,165" fill="none" :stroke="ap.hairColor" stroke-width="5.4" stroke-linecap="round" />
          <path d="M212,165 Q228,161 246,166" fill="none" :stroke="ap.hairColor" stroke-width="5.4" stroke-linecap="round" />
        </template>
        <template v-else>
          <path d="M160,166 Q174,160 187,166" fill="none" :stroke="ap.hairColor" stroke-width="3.7" stroke-linecap="round" />
          <path d="M213,166 Q226,160 240,166" fill="none" :stroke="ap.hairColor" stroke-width="3.7" stroke-linecap="round" />
        </template>
      </g>

      <!-- Mouth -->
      <ellipse v-if="showTalking" class="talk-mouth" cx="200" cy="236" rx="10" ry="7.2" fill="#9c3f58" stroke="#3d2c56" stroke-width="3.3" />
      <path v-else-if="showHappy" d="M182,232 Q200,250 218,232 Z" fill="#ffffff" stroke="#3d2c56" stroke-width="3.3" stroke-linejoin="round" />
      <path
        v-else
        :d="ap.base === 'male' ? 'M185,236 Q200,244 216,235' : 'M188,234 Q200,241 212,233'"
        fill="none"
        :stroke="ap.base === 'male' ? '#3d2c56' : '#b25068'"
        stroke-width="3.8"
        stroke-linecap="round"
      />

      <!-- Front Hair Layer -->
      <template v-if="ap.hairStyle === 'undercut'">
        <path d="M134,166 C130,124 152,82 202,78 C246,74 274,108 268,162 C264,142 252,130 236,126 C222,138 198,142 178,132 C164,142 146,146 134,166 Z"
              :fill="ap.hairColor" stroke="#3d2c56" stroke-width="4.5" stroke-linejoin="round" />
        <path d="M174,84 C190,62 224,62 242,84 C224,80 198,84 174,84 Z"
              :fill="ap.hairColor" stroke="#3d2c56" stroke-width="4" stroke-linejoin="round" />
        <path d="M172,102 Q204,92 234,106" fill="none" stroke="#ffffff" stroke-width="3" stroke-linecap="round" opacity="0.2" />
      </template>
      <template v-else-if="ap.hairStyle === 'side_part'">
        <path d="M135,164 C132,118 156,78 202,76 C248,74 270,110 265,164 C260,140 248,124 222,118 C196,126 168,126 150,140 C144,146 138,154 135,164 Z"
              :fill="ap.hairColor" stroke="#3d2c56" stroke-width="4.5" stroke-linejoin="round" />
        <path d="M156,104 Q198,86 244,104" fill="none" stroke="#ffffff" stroke-width="3" stroke-linecap="round" opacity="0.2" />
      </template>
      <template v-else-if="ap.hairStyle === 'low_bun'">
        <path d="M142,172 C142,118 168,84 202,84 C236,84 260,116 258,170 C248,140 226,122 204,118 C184,132 162,144 142,172 Z"
              :fill="ap.hairColor" stroke="#3d2c56" stroke-width="4.5" stroke-linejoin="round" />
        <path d="M174,104 Q202,94 232,112" fill="none" stroke="#ffffff" stroke-width="3" stroke-linecap="round" opacity="0.22" />
      </template>
      <template v-else-if="ap.hairStyle === 'spiky_crop'">
        <path d="M134,166 C132,130 144,102 162,88 L158,72 L182,82 L198,62 L212,80 L236,66 L236,88 C258,100 270,128 266,164 C260,142 248,132 232,128 C216,138 194,140 174,128 C156,136 142,146 134,166 Z"
              :fill="ap.hairColor" stroke="#3d2c56" stroke-width="4.5" stroke-linejoin="round" />
        <path d="M174,100 Q202,90 228,104" fill="none" stroke="#ffffff" stroke-width="3" stroke-linecap="round" opacity="0.2" />
      </template>
      <template v-else-if="ap.hairStyle === 'curly_short'">
        <path d="M132,168 C126,140 134,110 156,94 C168,78 192,72 214,76 C236,74 256,88 264,108 C272,128 272,150 266,168 C256,144 242,132 226,134 C216,144 198,144 188,134 C172,144 152,144 142,136 C138,148 134,158 132,168 Z"
              :fill="ap.hairColor" stroke="#3d2c56" stroke-width="4.5" stroke-linejoin="round" />
        <path d="M164,104 Q180,92 196,102 M208,98 Q226,90 240,104" fill="none" stroke="#ffffff" stroke-width="2.8" stroke-linecap="round" opacity="0.2" />
      </template>
      <template v-else-if="ap.hairStyle === 'high_ponytail'">
        <path d="M140,170 C140,116 168,82 202,82 C236,82 260,116 260,170 C248,138 228,118 202,116 C176,118 154,138 140,170 Z"
              :fill="ap.hairColor" stroke="#3d2c56" stroke-width="4.5" stroke-linejoin="round" />
        <path d="M170,104 Q202,92 232,108" fill="none" stroke="#ffffff" stroke-width="3" stroke-linecap="round" opacity="0.22" />
      </template>
      <template v-else-if="ap.hairStyle === 'wavy_long'">
        <path d="M132,190 C132,120 162,80 202,80 C242,80 270,120 268,190 C258,154 240,130 210,116 C192,134 176,144 158,150 C146,162 138,176 132,190 Z"
              :fill="ap.hairColor" stroke="#3d2c56" stroke-width="4.5" stroke-linejoin="round" />
        <path d="M166,104 Q204,90 238,112" fill="none" stroke="#ffffff" stroke-width="3" stroke-linecap="round" opacity="0.22" />
      </template>
      <template v-else>
        <path d="M136,184 C136,118 164,82 204,82 C244,82 266,118 264,174 C252,138 228,118 198,114 C178,136 158,154 136,184 Z"
              :fill="ap.hairColor" stroke="#3d2c56" stroke-width="4.5" stroke-linejoin="round" />
        <path d="M168,104 Q206,92 238,114" fill="none" stroke="#ffffff" stroke-width="3" stroke-linecap="round" opacity="0.22" />
      </template>

      <!-- Single-ear Headset Accessory -->
      <g v-if="ap.accessory === 'headset_single'">
        <path d="M142,190 C138,136 160,92 200,88" fill="none" stroke="#3d2c56" stroke-width="5" stroke-linecap="round" />
        <rect x="132" y="182" width="14" height="26" rx="7" fill="#34d399" stroke="#3d2c56" stroke-width="3.5" />
        <path d="M138,206 Q142,234 176,238" fill="none" stroke="#3d2c56" stroke-width="3.5" stroke-linecap="round" />
        <circle cx="178" cy="238" r="4.5" fill="#2d294b" />
      </g>

      <!-- Over-ear Wireless Headphones Accessory -->
      <g v-else-if="ap.accessory === 'headphones'">
        <path d="M126,184 C124,104 156,66 200,66 C244,66 276,104 274,184" fill="none" stroke="#6d55c7" stroke-width="9" stroke-linecap="round" />
        <path d="M126,184 C124,104 156,66 200,66 C244,66 276,104 274,184" fill="none" stroke="#3d2c56" stroke-width="4" stroke-linecap="round" />
        <rect x="114" y="172" width="22" height="42" rx="11" fill="#8b73dd" stroke="#3d2c56" stroke-width="3.8" />
        <rect x="264" y="172" width="22" height="42" rx="11" fill="#8b73dd" stroke="#3d2c56" stroke-width="3.8" />
        <circle cx="125" cy="193" r="4.5" fill="#34d399" />
      </g>

      <!-- Warm Amber Hairclip Accessory -->
      <g v-else-if="ap.accessory === 'hairclip'">
        <rect x="234" y="128" width="24" height="8" rx="4" transform="rotate(16 246 132)" fill="#fbbf24" stroke="#3d2c56" stroke-width="2.8" />
        <rect x="230" y="138" width="22" height="7" rx="3.5" transform="rotate(16 241 141)" fill="#fde68a" stroke="#3d2c56" stroke-width="2.5" />
      </g>

      <!-- Violet Beret Hat Accessory -->
      <g v-else-if="ap.accessory === 'beret'">
        <path d="M126,112 C122,74 166,54 218,58 C264,62 284,88 270,114 C236,102 164,102 126,112 Z" fill="#7c63c9" stroke="#3d2c56" stroke-width="4" stroke-linejoin="round" />
        <path d="M130,112 Q200,100 268,113" fill="none" stroke="#5a449e" stroke-width="5" stroke-linecap="round" />
        <path d="M198,58 L203,48" stroke="#3d2c56" stroke-width="4" stroke-linecap="round" />
      </g>
    </g>

    <!-- Thinking State: Floating Thought Bubble & Bouncing Dots -->
    <g v-if="showThinking" class="think-bubble" transform="translate(274, 68)" aria-hidden="true">
      <circle cx="-12" cy="40" r="4.5" fill="#ffffff" stroke="#8b73dd" stroke-width="2.5" />
      <circle cx="-2" cy="30" r="6" fill="#ffffff" stroke="#8b73dd" stroke-width="2.5" />
      <rect x="6" y="0" width="58" height="30" rx="15" fill="#ffffff" stroke="#8b73dd" stroke-width="3" />
      <circle class="think-dot think-dot-1" cx="22" cy="15" r="3.8" fill="#8b73dd" />
      <circle class="think-dot think-dot-2" cx="35" cy="15" r="3.8" fill="#8b73dd" />
      <circle class="think-dot think-dot-3" cx="48" cy="15" r="3.8" fill="#8b73dd" />
    </g>
  </svg>
</template>

<style scoped>
.portrait { width: 100%; height: 100%; overflow: visible; }
.head-pose { transition: transform .2s ease-out; transform-origin: 200px 260px; }
.torso-group { transform-origin: 200px 420px; }
.eye-blink { transform-box: fill-box; transform-origin: center; }
.happy .eye-blink { opacity: 0; }
.talk-mouth { transform-box: fill-box; transform-origin: center; }

@media (prefers-reduced-motion: no-preference) {
  .animated .torso-group { animation: breathe 4.2s ease-in-out infinite; }
  .animated .eye-blink { animation: blink 5.4s infinite; }
  .animated.is-listening .eye-blink { animation-duration: 7.5s; }
  .animated.is-listening .head-pose { animation: listenTilt 2.2s ease-in-out infinite; }
  .animated.is-listening .listen-waves { animation: wavePulse 0.9s ease-in-out infinite alternate; }
  .animated.is-thinking .head-pose { animation: thinkTilt 2.8s ease-in-out infinite; }
  .animated.is-thinking .brows { transform: translateY(-4px); transition: transform .25s ease; }
  .animated.is-thinking .think-dot-1 { animation: dotBounce 1.1s ease-in-out infinite 0s; }
  .animated.is-thinking .think-dot-2 { animation: dotBounce 1.1s ease-in-out infinite 0.18s; }
  .animated.is-thinking .think-dot-3 { animation: dotBounce 1.1s ease-in-out infinite 0.36s; }
  .animated.talking .talk-mouth { animation: talk .32s ease-in-out infinite alternate; }
}

@keyframes breathe { 50% { transform: translateY(-1.5px) scaleY(1.006); } }
@keyframes blink { 0%, 94%, 98%, 100% { transform: scaleY(1); } 96% { transform: scaleY(.08); } }
@keyframes talk { from { transform: scaleY(.45); } to { transform: scaleY(1.12); } }
@keyframes listenTilt { 0%, 100% { transform: translateY(0px) rotate(-2deg); } 50% { transform: translateY(-2px) rotate(1.2deg); } }
@keyframes wavePulse { from { opacity: 0.45; } to { opacity: 1; } }
@keyframes thinkTilt { 0%, 100% { transform: translateY(-1px) rotate(2.5deg); } 50% { transform: translateY(-3px) rotate(4deg); } }
@keyframes dotBounce { 0%, 80%, 100% { transform: translateY(0); opacity: 0.4; } 40% { transform: translateY(-5px); opacity: 1; } }

@media (prefers-reduced-motion: reduce) {
  .head-pose { transition: none; }
}
</style>
