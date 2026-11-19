import React from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import {
  BookOpen,
  Check,
  ChevronDown,
  ChevronLeft,
  Compass,
  FileText,
  Headphones,
  History,
  Keyboard,
  Layers,
  MessageSquare,
  Mic,
  RotateCcw,
  Sparkles,
  Star,
  Sun,
  TrendingUp,
  UserCheck,
  Volume2,
  Zap,
} from "lucide-react";
import { AmbientBackdrop } from "../components/AmbientBackdrop";
import { Avatar2D, AvatarPersona } from "../components/Avatars2D";
import { EchoTalkLogo } from "../components/EchoTalkLogo";
import { SfxCue, VoiceClip } from "../components/SfxCue";

const USER_TRANSCRIPT =
  "Hi there! Could I get a large drip coffee and a butter croissant, please?";
const LEO_REPLY =
  "Sorry, we're out of croissants today! A large drip coffee is $3.50 — would you like a blueberry muffin instead?";

const MARCUS_REBUTTAL =
  "AI copilots already generate 60% of boilerplate code — junior roles must prove deeper architectural value.";
const ELENA_RULING =
  "Sharp counter-argument! Grounding your point in system ownership pushed Pro momentum to 72%.";

const WORD_SCORES = [
  { word: "Could", score: 96 },
  { word: "large", score: 95 },
  { word: "drip", score: 93 },
  { word: "coffee", score: 94 },
  { word: "croissant", score: 84 },
];

const NAV_GROUPS = [
  {
    title: "训练",
    items: [
      { id: "today", label: "今日训练", icon: Sun },
      { id: "practice", label: "语音对话", icon: Mic },
      { id: "debate", label: "多角色对话", icon: MessageSquare },
      { id: "listening", label: "听力工作室", icon: Headphones },
    ],
  },
  {
    title: "内容与工具",
    items: [
      { id: "scenes", label: "场景探索", icon: Compass },
      { id: "knowledge", label: "知识工作区", icon: BookOpen },
      { id: "avatar", label: "数字人角色", icon: UserCheck },
    ],
  },
  {
    title: "成长",
    items: [
      { id: "review", label: "复习计划", icon: RotateCcw },
      { id: "history", label: "历史记录", icon: History },
      { id: "analytics", label: "成长分析", icon: TrendingUp },
    ],
  },
];

const DEBATE_ROLES: Array<{
  id: AvatarPersona;
  name: string;
  roleLabel: string;
  roleType: "opponent" | "judge" | "teammate";
  borderActive: string;
  bevelActive: string;
  bgActive: string;
  pillBg: string;
  pillText: string;
}> = [
  {
    id: "marcus",
    name: "Marcus",
    roleLabel: "反方辩手",
    roleType: "opponent",
    borderActive: "#DF9D8F",
    bevelActive: "#C87462",
    bgActive: "#FDF6F4",
    pillBg: "#FDECE8",
    pillText: "#B84A39",
  },
  {
    id: "elena",
    name: "Elena",
    roleLabel: "资深评委",
    roleType: "judge",
    borderActive: "#82CCA4",
    bevelActive: "#4AA777",
    bgActive: "#F3FBF7",
    pillBg: "#EAF7F0",
    pillText: "#2A8C5F",
  },
  {
    id: "leo",
    name: "Leo",
    roleLabel: "正方队友",
    roleType: "teammate",
    borderActive: "#8B73DD",
    bevelActive: "#6951B8",
    bgActive: "#F5F1FF",
    pillBg: "#EEE9FF",
    pillText: "#6046B4",
  },
];

/**
 * Reusable EchoTalk 2.0 Voice-First Playback Capsule + Smooth Expanding Transcript Box
 * Matches frontend/src/components/practice/VoiceBubbleRow.vue:
 * Step 1: Voice playback capsule appears first and starts playing audio.
 * Step 2: "原文" toggles to "收起" and the transcript card smoothly unfolds downward.
 */
const ExpandableVoiceBubble: React.FC<{
  secondsLabel: string;
  playing: boolean;
  progressPct: number;
  expandedSpring: number;
  isExpanded: boolean;
  text: string;
  t: number;
  tone?: "purple" | "coral" | "mint";
}> = ({
  secondsLabel,
  playing,
  progressPct,
  expandedSpring,
  isExpanded,
  text,
  t,
  tone = "purple",
}) => {
  const styles =
    tone === "coral"
      ? {
          capsuleBorder: "#DF9D8F",
          capsuleBg: "#FDF6F4",
          fillBg: "rgba(200, 116, 98, 0.14)",
          accent: "#B84A39",
          bar: "#C87462",
          textBorder: "#F0D5CE",
          textBg: "#FFF9F8",
        }
      : tone === "mint"
        ? {
            capsuleBorder: "#82CCA4",
            capsuleBg: "#F3FBF7",
            fillBg: "rgba(42, 140, 95, 0.14)",
            accent: "#2A8C5F",
            bar: "#2A8C5F",
            textBorder: "#BEE6D0",
            textBg: "#F7FDF9",
          }
        : {
            capsuleBorder: "#8B73DD",
            capsuleBg: "#F4F0FF",
            fillBg: "rgba(139, 115, 221, 0.16)",
            accent: "#6046B4",
            bar: "#8B73DD",
            textBorder: "#E5DEF4",
            textBg: "#FAF9FD",
          };

  return (
    <div className="flex flex-col gap-1.5">
      {/* Row 1: Voice Playback Capsule + 原文/收起 Toggle Pill */}
      <div className="flex items-center gap-2">
        <div
          className="relative flex w-[224px] items-center gap-2.5 overflow-hidden rounded-2xl border-[1.5px] px-3.5 py-2 shadow-sm"
          style={{
            borderColor: styles.capsuleBorder,
            backgroundColor: styles.capsuleBg,
          }}
        >
          {/* Live Playback Progress Fill */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              width: `${Math.min(100, Math.max(0, progressPct))}%`,
              backgroundColor: styles.fillBg,
            }}
          />
          <Volume2
            className="relative z-10 h-4 w-4 flex-shrink-0"
            style={{ color: styles.accent }}
          />
          <span
            className="relative z-10 font-mono text-[12px] font-bold"
            style={{ color: styles.accent }}
          >
            {secondsLabel}
          </span>
          <div className="relative z-10 flex flex-1 items-center gap-[3px]">
            {Array.from({ length: 13 }).map((_, i) => {
              const barH = playing
                ? 5 + Math.abs(Math.sin(t * 15.5 + i * 0.68)) * 12
                : 5 + ((i * 5) % 8);
              return (
                <span
                  key={i}
                  className="w-[3px] rounded-full"
                  style={{
                    height: barH,
                    backgroundColor: styles.bar,
                    opacity: playing ? 0.92 : 0.45,
                  }}
                />
              );
            })}
          </div>
        </div>

        {/* Authentic 原文 / 收起 Button */}
        <span
          className="inline-flex items-center gap-1 rounded-xl border px-2.5 py-1.5 text-[11.5px] font-bold"
          style={{
            borderColor: isExpanded ? styles.capsuleBorder : "#EBE7F5",
            backgroundColor: isExpanded ? styles.capsuleBg : "#FFFFFF",
            color: isExpanded ? styles.accent : "#625E76",
            transform: isExpanded
              ? `scale(${interpolate(expandedSpring, [0, 0.45, 1], [0.92, 1.06, 1])})`
              : "scale(1)",
          }}
        >
          <FileText className="h-3 w-3" />
          <span>{isExpanded ? "收起" : "原文"}</span>
        </span>
      </div>

      {/* Row 2: Smooth Unfolding Transcript Card (expands after voice capsule starts!) */}
      {expandedSpring > 0.01 && (
        <div
          style={{
            overflow: "hidden",
            maxHeight: interpolate(expandedSpring, [0, 1], [0, 120]),
            opacity: interpolate(expandedSpring, [0, 0.35, 1], [0, 0.85, 1]),
            transform: `translateY(${interpolate(expandedSpring, [0, 1], [-8, 0])}px)`,
          }}
        >
          <div
            className="max-w-[555px] rounded-2xl rounded-tl-sm border-[1.5px] px-4 py-2.5 text-[13.5px] font-medium leading-relaxed text-[#35304E]"
            style={{
              borderColor: styles.textBorder,
              backgroundColor: styles.textBg,
            }}
          >
            {text}
          </div>
        </div>
      )}
    </div>
  );
};

export const Scene2Demo: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;

  // --- Phase Switch: Practice (0-210f) -> Multi-Role Debate Arena (210-440f) ---
  const SWITCH_FRAME = 210;
  const isDebatePhase = frame >= SWITCH_FRAME;

  const enterSpring = spring({
    frame,
    fps,
    config: { damping: 17, stiffness: 96, mass: 1.0 },
  });

  const zoomIn = interpolate(frame, [38, 92], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });

  const switchBreath = interpolate(frame, [196, 214, 240], [0, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.quad),
  });

  const endPullback = interpolate(frame, [398, 436], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });

  const activeZoom =
    zoomIn * (1 - switchBreath * 0.45) * (1 - endPullback * 0.72);
  const scale =
    interpolate(enterSpring, [0, 1], [0.8, 0.94]) + activeZoom * 0.25;
  const rotateX = interpolate(enterSpring, [0, 1], [20, 0]) - activeZoom * 0.8;
  const rotateY =
    interpolate(enterSpring, [0, 1], [-14, 0]) +
    (isDebatePhase ? -1.4 : 1.2) * activeZoom;
  const translateX = -activeZoom * 96;
  const translateY =
    interpolate(enterSpring, [0, 1], [120, 0]) - activeZoom * 10;

  // --- PART A: Practice.vue Timelines (0 - 210f) ---
  const isRecording = frame >= 44 && frame < 84;
  const userSent = frame >= 84;
  const evalVisible = frame >= 94;
  const goalDone = frame >= 106;

  // Leo outputs voice bubble FIRST at 110f, THEN smoothly expands transcript at 136f!
  const LEO_BUBBLE_FRAME = 110;
  const LEO_EXPAND_FRAME = 136;
  const leoVisible = frame >= LEO_BUBBLE_FRAME;
  const leoSpeaking = frame >= LEO_BUBBLE_FRAME && frame < SWITCH_FRAME;

  const asrProgress = interpolate(frame, [48, 82], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.quad),
  });
  const liveAsrText = USER_TRANSCRIPT.slice(
    0,
    Math.round(asrProgress * USER_TRANSCRIPT.length)
  );

  const userBubbleSpring = spring({
    frame: frame - 84,
    fps,
    config: { damping: 16, stiffness: 170, mass: 0.82 },
  });
  const evalSpring = spring({
    frame: frame - 94,
    fps,
    config: { damping: 15, stiffness: 155, mass: 0.88 },
  });
  const goalSpring = spring({
    frame: frame - 106,
    fps,
    config: { damping: 13, stiffness: 195, mass: 0.72 },
  });
  const leoBubbleSpring = spring({
    frame: frame - LEO_BUBBLE_FRAME,
    fps,
    config: { damping: 15, stiffness: 165, mass: 0.82 },
  });
  const leoExpandSpring = spring({
    frame: frame - LEO_EXPAND_FRAME,
    fps,
    config: { damping: 17, stiffness: 135, mass: 0.9 },
  });
  const leoPlayPct = interpolate(frame, [LEO_BUBBLE_FRAME, SWITCH_FRAME], [0, 88], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.quad),
  });

  // --- PART B: Multi-Role Debate Arena Timelines (210 - 440f) ---
  const debateEnterSpring = spring({
    frame: frame - SWITCH_FRAME,
    fps,
    config: { damping: 16, stiffness: 135, mass: 0.88 },
  });

  // Marcus speaks first (voice bubble at 220f -> transcript unfolds at 246f)
  const MARCUS_BUBBLE_FRAME = 220;
  const MARCUS_EXPAND_FRAME = 246;

  // Elena rotates onto stage (328f -> voice bubble at 330f -> transcript unfolds at 356f)
  const ROLE_ROTATE_FRAME = 328;
  const ELENA_BUBBLE_FRAME = 330;
  const ELENA_EXPAND_FRAME = 356;

  const activeSpeakerId: AvatarPersona =
    frame >= ROLE_ROTATE_FRAME ? "elena" : "marcus";
  const activeRoleMeta =
    DEBATE_ROLES.find((r) => r.id === activeSpeakerId) || DEBATE_ROLES[0];

  const marcusBubbleSpring = spring({
    frame: frame - MARCUS_BUBBLE_FRAME,
    fps,
    config: { damping: 15, stiffness: 165, mass: 0.82 },
  });
  const marcusExpandSpring = spring({
    frame: frame - MARCUS_EXPAND_FRAME,
    fps,
    config: { damping: 17, stiffness: 135, mass: 0.9 },
  });
  const marcusPlayPct = interpolate(
    frame,
    [MARCUS_BUBBLE_FRAME, ROLE_ROTATE_FRAME],
    [0, 100],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const elenaRotateSpring = spring({
    frame: frame - ROLE_ROTATE_FRAME,
    fps,
    config: { damping: 13, stiffness: 175, mass: 0.8 },
  });
  const elenaBubbleSpring = spring({
    frame: frame - ELENA_BUBBLE_FRAME,
    fps,
    config: { damping: 15, stiffness: 165, mass: 0.82 },
  });
  const elenaExpandSpring = spring({
    frame: frame - ELENA_EXPAND_FRAME,
    fps,
    config: { damping: 17, stiffness: 135, mass: 0.9 },
  });
  const elenaPlayPct = interpolate(frame, [ELENA_BUBBLE_FRAME, 438], [0, 92], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Win-rate tug bar & 4D radar dynamically animate when Elena rules
  const winRate = Math.round(
    interpolate(elenaRotateSpring, [0, 1], [58, 72])
  );
  const radarScores = {
    logic: Math.round(interpolate(elenaRotateSpring, [0, 1], [80, 92])),
    rebuttal: Math.round(interpolate(elenaRotateSpring, [0, 1], [76, 88])),
    presence: Math.round(interpolate(elenaRotateSpring, [0, 1], [82, 90])),
    fluency: Math.round(interpolate(elenaRotateSpring, [0, 1], [78, 86])),
  };
  const cx = 124;
  const cy = 92;
  const maxR = 54;
  const radarPts = [
    { x: cx, y: cy - (maxR * radarScores.logic) / 100 },
    { x: cx + (maxR * radarScores.rebuttal) / 100, y: cy },
    { x: cx, y: cy + (maxR * radarScores.presence) / 100 },
    { x: cx - (maxR * radarScores.fluency) / 100, y: cy },
  ];
  const radarPolygon = radarPts
    .map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`)
    .join(" ");

  const activeNavId = isDebatePhase ? "debate" : "practice";

  return (
    <AbsoluteFill className="font-sans select-none">
      {/* Frame-Synced Tactile SFX */}
      <SfxCue sfx="whoosh" from={0} volume={0.28} />
      <SfxCue sfx="mic-ping" from={44} volume={0.26} />
      <SfxCue sfx="pop" from={84} volume={0.22} playbackRate={1.0} />
      <SfxCue sfx="pop" from={94} volume={0.18} playbackRate={1.18} />
      <SfxCue sfx="success-chime" from={106} volume={0.25} />
      <SfxCue sfx="pop" from={LEO_BUBBLE_FRAME} volume={0.20} playbackRate={0.94} />
      <SfxCue sfx="pop" from={LEO_EXPAND_FRAME} volume={0.16} playbackRate={1.22} />

      <SfxCue sfx="whoosh" from={SWITCH_FRAME} volume={0.28} playbackRate={1.15} />
      <SfxCue sfx="pop" from={MARCUS_BUBBLE_FRAME} volume={0.20} playbackRate={0.92} />
      <SfxCue sfx="pop" from={MARCUS_EXPAND_FRAME} volume={0.16} playbackRate={1.2} />
      <SfxCue sfx="whoosh" from={ROLE_ROTATE_FRAME} volume={0.22} playbackRate={1.32} />
      <SfxCue sfx="pop" from={ELENA_BUBBLE_FRAME} volume={0.20} playbackRate={1.08} />
      <SfxCue sfx="pop" from={ELENA_EXPAND_FRAME} volume={0.16} playbackRate={1.24} />
      <SfxCue sfx="success-chime" from={362} volume={0.24} />

      {/* Real Neural English Voice Clips with Smooth Fade-In & Fade-Out */}
      <VoiceClip
        src="audio/leo-cafe.mp3"
        from={LEO_BUBBLE_FRAME}
        durationInFrames={98}
        peakVolume={0.86}
        fadeInFrames={14}
        fadeOutFrames={26}
      />
      <VoiceClip
        src="audio/marcus-debate.mp3"
        from={MARCUS_BUBBLE_FRAME}
        durationInFrames={106}
        peakVolume={0.86}
        fadeInFrames={14}
        fadeOutFrames={26}
      />
      <VoiceClip
        src="audio/elena-ruling.mp3"
        from={ELENA_BUBBLE_FRAME}
        durationInFrames={108}
        peakVolume={0.88}
        fadeInFrames={14}
        fadeOutFrames={28}
      />

      <AmbientBackdrop
        intensity={1.08}
        focusX={isDebatePhase ? -0.2 : 0.22}
        focusY={-0.08}
      />

      {/* Floating Mode Pill at Top */}
      <div className="absolute top-6 left-0 right-0 z-30 flex justify-center pointer-events-none">
        <div
          className="inline-flex items-center gap-2 rounded-full border-[1.5px] border-[#E6E0F5] border-b-[3px] border-b-[#DCD4F0] bg-white/95 px-2.5 py-1.5 shadow-[0_12px_32px_rgba(105,81,184,0.12)]"
          style={{
            opacity: interpolate(enterSpring, [0, 0.4], [0, 1], {
              extrapolateRight: "clamp",
            }),
          }}
        >
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-3.5 py-1 text-[13px] font-bold ${
              !isDebatePhase
                ? "bg-[#8B73DD] text-white shadow-sm"
                : "text-[#6E6886]"
            }`}
          >
            <Mic className="h-3.5 w-3.5" />
            1v1 场景语音对话
          </span>
          <span className="text-[#C7BFE0] font-bold">→</span>
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-3.5 py-1 text-[13px] font-bold ${
              isDebatePhase
                ? "bg-[#45C98E] text-white shadow-sm"
                : "text-[#6E6886]"
            }`}
          >
            <MessageSquare className="h-3.5 w-3.5" />
            多角色辩论 · 轮换数字人
          </span>
        </div>
      </div>

      {/* 3D Perspective Stage */}
      <AbsoluteFill
        className="flex items-center justify-center"
        style={{ perspective: "1800px" }}
      >
        <div
          style={{
            width: 1520,
            height: 890,
            transformStyle: "preserve-3d",
            transform: `translate3d(${translateX}px, ${translateY}px, 0px) scale(${scale}) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`,
            opacity: interpolate(enterSpring, [0, 0.25], [0, 1], {
              extrapolateRight: "clamp",
            }),
          }}
        >
          {/* REAL EchoTalk 2.0 Tactile Purple-White Desktop App Window */}
          <div
            className="relative flex h-full w-full overflow-hidden rounded-[24px] border-2 border-[#E4DDF4] border-b-[6px] border-b-[#D5CBEF] bg-[#F7F6FC]"
            style={{
              boxShadow:
                "0 36px 90px rgba(105, 81, 184, 0.18), 0 12px 32px rgba(53, 48, 78, 0.08)",
            }}
          >
            {/* LEFT SIDEBAR */}
            <aside className="flex w-[240px] flex-shrink-0 flex-col border-r border-[#EBE7F5] bg-white px-4 py-4">
              <div className="mb-4 flex items-center gap-2 px-1">
                <span className="h-3 w-3 rounded-full bg-[#FF5F56]" />
                <span className="h-3 w-3 rounded-full bg-[#FFBD2E]" />
                <span className="h-3 w-3 rounded-full bg-[#27C93F]" />
              </div>

              <div className="mb-5 flex items-center gap-3 px-1">
                <EchoTalkLogo size={42} glow={false} framed />
                <div className="flex flex-col leading-tight">
                  <span className="text-[17px] font-extrabold tracking-tight text-[#35304E]">
                    EchoTalk
                  </span>
                  <span className="font-mono text-[11.5px] font-semibold text-[#837F96]">
                    2.0
                  </span>
                </div>
              </div>

              <nav className="flex flex-1 flex-col gap-4">
                {NAV_GROUPS.map((group) => (
                  <div key={group.title}>
                    <div className="mb-1.5 px-2.5 text-[11px] font-semibold text-[#837F96]">
                      {group.title}
                    </div>
                    <div className="flex flex-col gap-0.5">
                      {group.items.map((item) => {
                        const Icon = item.icon;
                        const active = item.id === activeNavId;
                        return (
                          <div
                            key={item.id}
                            className={`flex items-center gap-2.5 rounded-xl px-3 py-2 text-[13.5px] font-semibold ${
                              active
                                ? "bg-[#EEE9FF] text-[#6046B4]"
                                : "text-[#5A5572]"
                            }`}
                          >
                            <Icon
                              className={`h-4 w-4 ${
                                active ? "text-[#6951B8]" : "text-[#837F96]"
                              }`}
                            />
                            <span>{item.label}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </nav>

              <div className="mt-2 flex items-center gap-2.5 rounded-2xl border-[1.5px] border-[#EBE7F5] border-b-[3px] border-b-[#E3DCF2] bg-white px-3 py-2.5">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-[#8B73DD] to-[#6951B8] text-[13px] font-bold text-white">
                  A
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[13px] font-bold text-[#35304E]">
                      ackow
                    </span>
                    <span className="rounded-md bg-[#8B73DD] px-1.5 py-0.5 font-mono text-[10px] font-bold text-white">
                      Lv.4
                    </span>
                  </div>
                  <div className="text-[11px] text-[#837F96]">微光旅人 · II</div>
                </div>
              </div>
            </aside>

            {/* MAIN CONTENT WORKSPACE */}
            <div className="relative flex flex-1 flex-col overflow-hidden bg-[#F7F6FC]">
              <div className="flex items-center justify-between border-b border-[#EBE7F5] bg-white px-6 py-3">
                <span className="text-[15px] font-bold text-[#35304E]">
                  {isDebatePhase ? "多角色对话 · 辩论工作台" : "语音对话"}
                </span>
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-[#EAF7F0] px-3 py-1 font-mono text-[11.5px] font-bold text-[#2A8C5F]">
                    <span className="h-1.5 w-1.5 rounded-full bg-[#2A8C5F]" />
                    {isDebatePhase
                      ? "Multi-Agent Arena · 3 AI 席位"
                      : "LangGraph StateGraph · Live"}
                  </span>
                </div>
              </div>

              {/* ==========================================================
                  VIEW 1: 1v1 语音对话 (Practice.vue)
                 ========================================================== */}
              {!isDebatePhase && (
                <div className="flex flex-1 flex-col overflow-hidden px-6 pt-4 pb-5">
                  <div className="mb-3.5 flex items-center justify-between">
                    <div className="flex items-center gap-3.5">
                      <div className="flex h-9 w-9 items-center justify-center rounded-xl border-[1.5px] border-[#E6E1F2] border-b-[3px] border-b-[#DDD6EC] bg-white text-[#5A5572]">
                        <ChevronLeft className="h-4 w-4" />
                      </div>
                      <div>
                        <div className="text-[19px] font-extrabold tracking-tight text-[#35304E]">
                          繁忙咖啡厅点餐 (Cafe Ordering)
                        </div>
                        <div className="mt-0.5 flex items-center gap-2 text-[12.5px] text-[#837F96]">
                          <span>日常</span>
                          <span>·</span>
                          <span>场景口语练习</span>
                          <span>·</span>
                          <span className="font-semibold text-[#6951B8]">
                            {userSent ? "2 轮对话" : "1 轮对话"}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="inline-flex items-center gap-1.5 rounded-xl border-[1.5px] border-[#E6E1F2] border-b-[3px] border-b-[#DDD6EC] bg-white px-3.5 py-1.5 text-[13px] font-semibold text-[#5A5572]">
                      <BookOpen className="h-3.5 w-3.5 text-[#8B73DD]" />
                      <span>参考板</span>
                    </div>
                  </div>

                  <div className="flex flex-1 gap-4 overflow-hidden">
                    <section className="flex flex-1 flex-col overflow-hidden rounded-[18px] border-[1.5px] border-[#EBE7F5] border-b-[4px] border-b-[#E3DCF2] bg-white">
                      <div className="flex items-center justify-between border-b border-[#F1EEF8] px-5 py-3">
                        <div className="flex items-center gap-3">
                          <div className="flex h-10 w-10 items-center justify-center rounded-full border-[1.5px] border-[#E3DCF2] bg-[#F4F0FF] text-[15px] font-bold text-[#6046B4]">
                            L
                          </div>
                          <div>
                            <div className="text-[15px] font-bold text-[#35304E]">
                              Leo · Barista
                            </div>
                            <div className="flex items-center gap-1.5 text-[12px] text-[#837F96]">
                              <span
                                className="h-2 w-2 rounded-full"
                                style={{
                                  backgroundColor: leoSpeaking
                                    ? "#8B73DD"
                                    : isRecording
                                      ? "#45C98E"
                                      : "#2A8C5F",
                                }}
                              />
                              <span>
                                {leoSpeaking
                                  ? "正在播放 AI 语音回复…"
                                  : isRecording
                                    ? "正在采集 16kHz PCM16 语音…"
                                    : "等待你的回应"}
                              </span>
                            </div>
                          </div>
                        </div>

                        <div className="inline-flex items-center gap-1.5 rounded-xl border-[1.5px] border-[#E6E1F2] border-b-[3px] border-b-[#DDD6EC] bg-white px-3 py-1.5 text-[12px] font-semibold text-[#5A5572]">
                          <FileText className="h-3.5 w-3.5 text-[#8B73DD]" />
                          <span>
                            {frame >= LEO_EXPAND_FRAME ? "原文已展开" : "原文已隐藏"}
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center justify-between border-b border-[#F4F2FA] bg-[#FAF9FD] px-5 py-2">
                        <div className="inline-flex items-center gap-2 rounded-full border border-[#E6E1F2] bg-white px-3 py-1 text-[12px]">
                          <Layers className="h-3.5 w-3.5 text-[#8B73DD]" />
                          <span className="text-[#837F96]">阶段</span>
                          <span className="font-bold text-[#35304E]">
                            {goalDone ? "确认与结算" : "点单与定制"}
                          </span>
                          <span className="font-mono text-[11px] font-bold text-[#6951B8]">
                            {goalDone ? "3 / 3" : "2 / 3"}
                          </span>
                          <ChevronDown className="h-3 w-3 text-[#837F96]" />
                        </div>

                        <div className="inline-flex items-center gap-1.5 rounded-full border border-[#E6E1F2] bg-white px-3 py-1 font-mono text-[11px] text-[#625E76]">
                          <span>state:</span>
                          <span className="font-bold text-[#6046B4]">
                            {goalDone ? "order_confirmed=true" : "item=drip_coffee"}
                          </span>
                        </div>
                      </div>

                      <div className="flex flex-1 flex-col gap-3.5 overflow-hidden px-5 py-4">
                        {/* Opening Leo Voice Bubble (collapsed by default) */}
                        <div className="flex items-start gap-2.5">
                          <div className="mt-1 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-[#F4F0FF] text-[12px] font-bold text-[#6046B4]">
                            L
                          </div>
                          <div className="flex flex-col gap-1">
                            <span className="text-[11.5px] font-semibold text-[#837F96]">
                              Leo
                            </span>
                            <div className="flex items-center gap-2">
                              <div className="flex w-[166px] items-center gap-2 rounded-2xl border-[1.5px] border-[#EBE7F5] bg-white px-3.5 py-2 shadow-sm">
                                <Volume2 className="h-4 w-4 text-[#8B73DD]" />
                                <span className="font-mono text-[12px] font-bold text-[#6046B4]">
                                  8&quot;
                                </span>
                                <div className="flex flex-1 items-center gap-1">
                                  {[5, 11, 8, 13, 9, 6, 10, 7].map((h, i) => (
                                    <span
                                      key={i}
                                      className="w-[3px] rounded-full bg-[#C7BBEE]"
                                      style={{ height: h }}
                                    />
                                  ))}
                                </div>
                              </div>
                              <span className="rounded-xl border border-[#EBE7F5] bg-[#FAF9FD] px-2.5 py-1.5 text-[11.5px] font-semibold text-[#625E76]">
                                原文
                              </span>
                            </div>
                          </div>
                        </div>

                        {/* User Bubble + Parallel ISE & Grammar Feedback */}
                        {userSent && (
                          <div
                            className="flex flex-col items-end gap-2"
                            style={{
                              opacity: userBubbleSpring,
                              transform: `translateY(${interpolate(userBubbleSpring, [0, 1], [18, 0])}px)`,
                            }}
                          >
                            <div className="flex items-start gap-2.5">
                              <div className="flex flex-col items-end gap-1">
                                <span className="text-[11.5px] font-semibold text-[#837F96]">
                                  你
                                </span>
                                <div className="max-w-[540px] rounded-2xl rounded-tr-sm border border-[#DFD6F7] bg-[#EAE3FF] px-4 py-2.5 text-[14px] font-medium leading-relaxed text-[#35304E]">
                                  {USER_TRANSCRIPT}
                                </div>
                              </div>
                              <div className="mt-5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-[#8B73DD] text-[12px] font-bold text-white">
                                A
                              </div>
                            </div>

                            {evalVisible && (
                              <div
                                className="mr-10 flex flex-col gap-2 rounded-2xl border-[1.5px] border-[#EBE7F5] border-b-[3px] border-b-[#E3DCF2] bg-[#FAF9FD] px-3.5 py-2.5"
                                style={{
                                  opacity: evalSpring,
                                  transform: `translateY(${interpolate(evalSpring, [0, 1], [10, 0])}px)`,
                                }}
                              >
                                <div className="flex items-center gap-2.5 text-[12px] text-[#5A5572]">
                                  <span className="inline-flex items-center gap-1 font-semibold">
                                    <Mic className="h-3.5 w-3.5 text-[#8B73DD]" />
                                    发音 <b className="font-mono text-[#2A8C5F]">92</b>
                                  </span>
                                  <span>·</span>
                                  <span>
                                    语调 <b className="font-mono text-[#6951B8]">89</b>
                                  </span>
                                  <span>·</span>
                                  <span className="font-mono font-semibold text-[#6046B4]">
                                    138 WPM
                                  </span>
                                  <span className="ml-1 inline-flex items-center gap-1 rounded-full bg-[#EAF7F0] px-2.5 py-0.5 text-[11px] font-bold text-[#2A8C5F]">
                                    <Check className="h-3 w-3" />
                                    表达自然准确
                                  </span>
                                </div>

                                <div className="flex flex-wrap gap-1.5">
                                  {WORD_SCORES.map((w) => {
                                    const warn = w.score < 86;
                                    return (
                                      <span
                                        key={w.word}
                                        className={`inline-flex items-baseline gap-1 rounded-lg px-2 py-0.5 text-[11.5px] font-semibold ${
                                          warn
                                            ? "bg-[#FFF3EA] text-[#C46A24]"
                                            : "bg-[#EAF7F0] text-[#2A8C5F]"
                                        }`}
                                      >
                                        <span>{w.word}</span>
                                        <small className="font-mono text-[10px]">
                                          {w.score}
                                        </small>
                                      </span>
                                    );
                                  })}
                                </div>
                              </div>
                            )}
                          </div>
                        )}

                        {/* Leo Reply: Voice Playback Bubble FIRST -> Smoothly Expands Transcript! */}
                        {leoVisible && (
                          <div
                            className="flex items-start gap-2.5"
                            style={{
                              opacity: leoBubbleSpring,
                              transform: `translateY(${interpolate(leoBubbleSpring, [0, 1], [16, 0])}px)`,
                            }}
                          >
                            <div className="mt-1 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-[#F4F0FF] text-[12px] font-bold text-[#6046B4]">
                              L
                            </div>
                            <div className="flex flex-col gap-1.5">
                              <div className="flex items-center gap-2">
                                <span className="text-[11.5px] font-semibold text-[#837F96]">
                                  Leo
                                </span>
                                <span className="rounded-md bg-[#F4F0FF] px-1.5 py-0.5 font-mono text-[10px] font-bold text-[#6951B8]">
                                  Andrew · 美式英语
                                </span>
                              </div>
                              <ExpandableVoiceBubble
                                secondsLabel='6"'
                                playing={leoSpeaking}
                                progressPct={leoPlayPct}
                                expandedSpring={leoExpandSpring}
                                isExpanded={frame >= LEO_EXPAND_FRAME}
                                text={LEO_REPLY}
                                t={t}
                                tone="purple"
                              />
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Tactile PracticeComposer */}
                      <div className="border-t border-[#F1EEF8] bg-white px-4 py-3">
                        <div
                          className={`flex items-center justify-between rounded-2xl border-[1.5px] px-4 py-2.5 ${
                            isRecording
                              ? "border-[#8B73DD] bg-[#F4F0FF]"
                              : "border-[#EBE7F5] bg-[#FAF9FD]"
                          }`}
                        >
                          <div className="flex flex-1 items-center gap-3.5">
                            <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-full border-b-[3px] border-b-[#6951B8] bg-[#8B73DD] text-white shadow-md">
                              <Mic className="h-5 w-5" />
                            </div>
                            {isRecording ? (
                              <div className="flex flex-1 flex-col gap-1">
                                <div className="flex items-center gap-2">
                                  <div className="flex items-center gap-[3px]">
                                    {Array.from({ length: 16 }).map((_, i) => (
                                      <span
                                        key={i}
                                        className="w-[3px] rounded-full bg-[#8B73DD]"
                                        style={{
                                          height:
                                            4 + Math.abs(Math.sin(t * 16 + i * 0.6)) * 14,
                                        }}
                                      />
                                    ))}
                                  </div>
                                  <span className="font-mono text-[11px] font-bold text-[#6951B8]">
                                    16kHz PCM16 · Flash ASR
                                  </span>
                                </div>
                                <div className="truncate text-[13.5px] font-semibold text-[#35304E]">
                                  {liveAsrText || "正在聆听…"}
                                </div>
                              </div>
                            ) : (
                              <div>
                                <div className="text-[14px] font-bold text-[#35304E]">
                                  点击说英语
                                </div>
                                <div className="text-[11.5px] text-[#837F96]">
                                  最长 60 秒，录完可试听或重录
                                </div>
                              </div>
                            )}
                          </div>

                          {!isRecording && (
                            <div className="flex items-center gap-2">
                              <span className="inline-flex items-center gap-1 rounded-xl border-[1.5px] border-[#E6E1F2] border-b-[3px] border-b-[#DDD6EC] bg-white px-3 py-1.5 text-[12px] font-semibold text-[#6046B4]">
                                <Sparkles className="h-3.5 w-3.5 text-[#8B73DD]" />
                                AI 帮回复
                              </span>
                              <span className="inline-flex items-center gap-1 rounded-xl border-[1.5px] border-[#E6E1F2] border-b-[3px] border-b-[#DDD6EC] bg-white px-3 py-1.5 text-[12px] font-semibold text-[#5A5572]">
                                <Keyboard className="h-3.5 w-3.5" />
                                文字输入
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    </section>

                    {/* Right Coach Drawer */}
                    <aside className="flex w-[292px] flex-shrink-0 flex-col gap-3.5">
                      <div className="flex flex-col rounded-[18px] border-[1.5px] border-[#EBE7F5] border-b-[4px] border-b-[#E3DCF2] bg-white p-3.5">
                        <div className="mb-2 text-[14px] font-bold text-[#35304E]">
                          交流伙伴
                        </div>
                        <Avatar2D
                          persona="leo"
                          frame={frame}
                          fps={fps}
                          speaking={leoSpeaking}
                          listening={isRecording}
                          height={172}
                        />
                        <div className="mt-2.5 flex items-baseline gap-2">
                          <b className="text-[14.5px] font-bold text-[#35304E]">
                            Leo
                          </b>
                          <span className="text-[12px] text-[#837F96]">
                            Barista
                          </span>
                        </div>
                        <div className="mt-2 flex items-center justify-between border-t border-[#F1EEF8] pt-2 text-[11.5px] text-[#6E6886]">
                          <span className="inline-flex items-center gap-1.5 font-semibold">
                            <span className="flex h-3.5 w-3.5 items-center justify-center rounded bg-[#8B73DD] text-white">
                              <Check className="h-2.5 w-2.5" />
                            </span>
                            自动播放
                          </span>
                          <span>Andrew · 美式英语</span>
                        </div>
                        <div className="mt-2 flex items-center gap-2 border-t border-dashed border-[#F1EEF8] pt-2 text-[11.5px]">
                          <span className="font-semibold text-[#6E6886]">语速</span>
                          <div className="relative h-1.5 flex-1 rounded-full bg-[#EEE9FA]">
                            <div className="h-full w-1/2 rounded-full bg-[#8B73DD]" />
                            <div className="absolute top-1/2 left-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#8B73DD]" />
                          </div>
                          <span className="font-mono font-bold text-[#694EC0]">
                            1.00×
                          </span>
                        </div>
                      </div>

                      <div className="flex flex-1 flex-col rounded-[18px] border-[1.5px] border-[#EBE7F5] border-b-[4px] border-b-[#E3DCF2] bg-white p-4">
                        <div className="flex items-center justify-between">
                          <span className="text-[14px] font-bold text-[#35304E]">
                            训练目标
                          </span>
                          <span className="font-mono text-[12.5px] font-bold text-[#694EC0]">
                            {goalDone ? "3 / 3" : "2 / 3"}
                          </span>
                        </div>
                        <div className="mt-2.5 h-1.5 w-full overflow-hidden rounded-full bg-[#EEE9FA]">
                          <div
                            className="h-full rounded-full bg-[#8B73DD]"
                            style={{
                              width: `${interpolate(goalSpring, [0, 1], [66.6, 100])}%`,
                            }}
                          />
                        </div>
                        <ul className="mt-3.5 flex flex-col gap-2">
                          {[
                            { label: "礼貌提出请求", done: true },
                            { label: "表达数量与规格", done: true },
                            { label: "复述并确认订单", done: goalDone },
                          ].map((g, idx) => (
                            <li
                              key={g.label}
                              className={`flex items-center gap-2.5 rounded-xl px-2.5 py-1.5 text-[12.5px] font-semibold ${
                                g.done
                                  ? "bg-[#EAF7F0] text-[#2A8C5F]"
                                  : "bg-[#FAF9FD] text-[#837F96]"
                              }`}
                            >
                              <span
                                className={`flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-bold ${
                                  g.done
                                    ? "bg-[#2A8C5F] text-white"
                                    : "bg-[#EBE7F5] text-[#625E76]"
                                }`}
                              >
                                {g.done ? <Check className="h-3 w-3" /> : idx + 1}
                              </span>
                              <span>{g.label}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </aside>
                  </div>
                </div>
              )}

              {/* ==========================================================
                  VIEW 2: 多角色辩论工作台 (Debate.vue + MultiRoleArena.vue)
                  Voice Playback Capsule FIRST -> Smooth Transcript Unfold + Real English Audio!
                 ========================================================== */}
              {isDebatePhase && (
                <div
                  className="flex flex-1 flex-col overflow-hidden px-6 pt-4 pb-5"
                  style={{
                    opacity: debateEnterSpring,
                    transform: `translateX(${interpolate(debateEnterSpring, [0, 1], [36, 0])}px)`,
                  }}
                >
                  <div className="mb-3.5 flex items-center justify-between">
                    <div className="flex items-center gap-3.5">
                      <div className="flex h-9 w-9 items-center justify-center rounded-xl border-[1.5px] border-[#E6E1F2] border-b-[3px] border-b-[#DDD6EC] bg-white text-[#5A5572]">
                        <ChevronLeft className="h-4 w-4" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2.5">
                          <h2 className="text-[19px] font-extrabold tracking-tight text-[#35304E]">
                            AI 是否会取代初级软件工程师？
                          </h2>
                          <span className="rounded-full bg-[#EAF7F0] px-2.5 py-0.5 text-[11.5px] font-bold text-[#2A8C5F]">
                            我方：正方
                          </span>
                        </div>
                        <p className="mt-0.5 text-[12px] text-[#837F96]">
                          Motion: Will AI coding agents replace junior software engineers within five years?
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="rounded-xl border-[1.5px] border-[#E6E1F2] border-b-[3px] border-b-[#DDD6EC] bg-white px-3 py-1.5 text-[12.5px] font-semibold text-[#5A5572]">
                        双语对照
                      </span>
                      <span className="inline-flex items-center gap-1.5 rounded-xl border-[1.5px] border-[#8067D1] border-b-[3px] border-b-[#6951B8] bg-[#8B73DD] px-3.5 py-1.5 text-[12.5px] font-bold text-white">
                        <Star className="h-3.5 w-3.5" />
                        结束并裁决
                      </span>
                    </div>
                  </div>

                  <div className="flex flex-1 gap-4 overflow-hidden">
                    <section className="flex flex-1 flex-col overflow-hidden rounded-[18px] border-[1.5px] border-[#EBE7F5] border-b-[4px] border-b-[#E3DCF2] bg-white">
                      {/* Battle HUD Tug-of-War & Stage Bar */}
                      <div className="border-b border-[#F1EEF8] bg-[#FAF9FD] px-5 py-3">
                        <div className="flex items-center gap-3">
                          <div className="flex items-baseline gap-1.5 text-[12.5px]">
                            <span className="font-semibold text-[#625E76]">我方 (正)</span>
                            <strong className="font-mono text-[15px] font-extrabold text-[#2A8C5F]">
                              {winRate}%
                            </strong>
                          </div>
                          <div className="relative h-3 flex-1 overflow-hidden rounded-full bg-[#FDECE8]">
                            <div
                              className="h-full rounded-full bg-gradient-to-r from-[#8B73DD] to-[#45C98E]"
                              style={{ width: `${winRate}%` }}
                            />
                          </div>
                          <div className="flex items-baseline gap-1.5 text-[12.5px]">
                            <strong className="font-mono text-[15px] font-extrabold text-[#C87462]">
                              {100 - winRate}%
                            </strong>
                            <span className="font-semibold text-[#625E76]">对手</span>
                          </div>
                          <span className="inline-flex items-center gap-1 rounded-full bg-[#FFF3EA] px-2.5 py-0.5 text-[11.5px] font-bold text-[#C46A24]">
                            <Zap className="h-3 w-3" />
                            连击 ×3
                          </span>
                          <span className="rounded-full bg-[#EEE9FF] px-2.5 py-0.5 font-mono text-[11.5px] font-bold text-[#6046B4]">
                            第 4/6 轮
                          </span>
                        </div>

                        <div className="mt-2.5 grid grid-cols-4 gap-2 text-center text-[11.5px] font-semibold">
                          {[
                            { name: "1. 开篇立论", state: "done" },
                            { name: "2. 交叉质询", state: "done" },
                            { name: "3. 自由攻防", state: "active" },
                            { name: "4. 结辩裁决", state: "todo" },
                          ].map((st) => (
                            <div
                              key={st.name}
                              className={`rounded-lg py-1 ${
                                st.state === "active"
                                  ? "bg-[#8B73DD] text-white"
                                  : st.state === "done"
                                    ? "bg-[#EAF7F0] text-[#2A8C5F]"
                                    : "bg-white text-[#837F96] border border-[#EBE7F5]"
                              }`}
                            >
                              {st.name}
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Multi-Role Dialogue Messages */}
                      <div className="flex flex-1 flex-col gap-3.5 overflow-hidden px-5 py-4">
                        {/* User Pro Turn */}
                        <div className="flex items-start justify-end gap-2.5">
                          <div className="flex flex-col items-end gap-1">
                            <span className="text-[11.5px] font-semibold text-[#2A8C5F]">
                              你 · 正方一辩
                            </span>
                            <div className="max-w-[520px] rounded-2xl rounded-tr-sm border border-[#DFD6F7] bg-[#EAE3FF] px-4 py-2 text-[13.5px] font-medium leading-relaxed text-[#35304E]">
                              AI accelerates syntax, not accountability — teams still need engineers who own system boundaries.
                            </div>
                          </div>
                          <div className="mt-5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-[#8B73DD] text-[12px] font-bold text-white">
                            A
                          </div>
                        </div>

                        {/* Speaker 1: Marcus (Voice Capsule FIRST -> Smooth Transcript Unfold!) */}
                        {frame >= MARCUS_BUBBLE_FRAME && (
                          <div
                            className="flex items-start gap-2.5"
                            style={{
                              opacity: marcusBubbleSpring,
                              transform: `translateY(${interpolate(marcusBubbleSpring, [0, 1], [16, 0])}px)`,
                            }}
                          >
                            <div className="mt-1 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-[#FDECE8] text-[12px] font-bold text-[#B84A39]">
                              M
                            </div>
                            <div className="flex flex-col gap-1.5">
                              <div className="flex items-center gap-2">
                                <span className="text-[12px] font-bold text-[#35304E]">
                                  Marcus
                                </span>
                                <span className="rounded-full bg-[#FDECE8] px-2 py-0.5 text-[10.5px] font-bold text-[#B84A39]">
                                  反方辩手 · Ryan 英式
                                </span>
                                {activeSpeakerId === "marcus" && (
                                  <span className="font-mono text-[10.5px] font-semibold text-[#C87462]">
                                    ● 正在语音反驳
                                  </span>
                                )}
                              </div>
                              <ExpandableVoiceBubble
                                secondsLabel='7"'
                                playing={activeSpeakerId === "marcus"}
                                progressPct={marcusPlayPct}
                                expandedSpring={marcusExpandSpring}
                                isExpanded={frame >= MARCUS_EXPAND_FRAME}
                                text={MARCUS_REBUTTAL}
                                t={t}
                                tone="coral"
                              />
                            </div>
                          </div>
                        )}

                        {/* Speaker 2: Elena (Voice Capsule FIRST -> Smooth Transcript Unfold!) */}
                        {frame >= ELENA_BUBBLE_FRAME && (
                          <div
                            className="flex items-start gap-2.5"
                            style={{
                              opacity: elenaBubbleSpring,
                              transform: `translateY(${interpolate(elenaBubbleSpring, [0, 1], [16, 0])}px)`,
                            }}
                          >
                            <div className="mt-1 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-[#EAF7F0] text-[12px] font-bold text-[#2A8C5F]">
                              E
                            </div>
                            <div className="flex flex-col gap-1.5">
                              <div className="flex items-center gap-2">
                                <span className="text-[12px] font-bold text-[#35304E]">
                                  Elena
                                </span>
                                <span className="rounded-full bg-[#EAF7F0] px-2 py-0.5 text-[10.5px] font-bold text-[#2A8C5F]">
                                  资深评委 · Ava 美式
                                </span>
                                <span className="rounded-md bg-[#F4F0FF] px-1.5 py-0.5 font-mono text-[10.5px] font-bold text-[#6951B8]">
                                  +14% 胜率
                                </span>
                              </div>
                              <ExpandableVoiceBubble
                                secondsLabel='6"'
                                playing={activeSpeakerId === "elena"}
                                progressPct={elenaPlayPct}
                                expandedSpring={elenaExpandSpring}
                                isExpanded={frame >= ELENA_EXPAND_FRAME}
                                text={ELENA_RULING}
                                t={t}
                                tone="mint"
                              />
                            </div>
                          </div>
                        )}
                      </div>

                      <div className="border-t border-[#F1EEF8] bg-white px-4 py-2.5">
                        <div className="flex items-center justify-between rounded-2xl border-[1.5px] border-[#EBE7F5] bg-[#FAF9FD] px-4 py-2">
                          <div className="flex items-center gap-3">
                            <div className="flex h-10 w-10 items-center justify-center rounded-full border-b-[3px] border-b-[#6951B8] bg-[#8B73DD] text-white">
                              <Mic className="h-4 w-4" />
                            </div>
                            <span className="text-[13px] font-semibold text-[#5A5572]">
                              轮到你发言 · 按住麦克风回应质询或发起反驳
                            </span>
                          </div>
                          <span className="rounded-xl border-[1.5px] border-[#E6E1F2] bg-white px-3 py-1 text-[12px] font-semibold text-[#6046B4]">
                            AI 论点锦囊
                          </span>
                        </div>
                      </div>
                    </section>

                    {/* Right Side: MultiRoleArena Rotating Digital Human Stage + 4D Radar */}
                    <aside className="flex w-[306px] flex-shrink-0 flex-col gap-3.5">
                      <div className="flex flex-col gap-2.5 rounded-[18px] border-[1.5px] border-[#EBE7F5] border-b-[4px] border-b-[#E3DCF2] bg-white p-3.5">
                        <div className="flex items-center justify-between">
                          <h4 className="text-[13.5px] font-bold text-[#35304E]">
                            圆桌辩论席
                          </h4>
                          <span className="inline-flex items-center gap-1 text-[11.5px] font-semibold text-[#6E6886]">
                            <span className="flex h-3.5 w-3.5 items-center justify-center rounded bg-[#8B73DD] text-white">
                              <Check className="h-2.5 w-2.5" />
                            </span>
                            自动播报
                          </span>
                        </div>

                        <div
                          className="flex flex-col items-center gap-2 rounded-2xl border-[1.5px] border-b-[3px] p-2.5"
                          style={{
                            borderColor: activeRoleMeta.borderActive,
                            borderBottomColor: activeRoleMeta.bevelActive,
                            backgroundColor: activeRoleMeta.bgActive,
                            transform:
                              activeSpeakerId === "elena"
                                ? `scale(${interpolate(elenaRotateSpring, [0, 0.5, 1], [0.92, 1.03, 1])})`
                                : "scale(1)",
                          }}
                        >
                          <Avatar2D
                            persona={activeSpeakerId}
                            frame={frame}
                            fps={fps}
                            speaking={true}
                            height={158}
                          />

                          <div className="flex items-center gap-2">
                            <strong className="text-[14.5px] font-bold text-[#35304E]">
                              {activeRoleMeta.name}
                            </strong>
                            <span
                              className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-bold"
                              style={{
                                backgroundColor: activeRoleMeta.pillBg,
                                color: activeRoleMeta.pillText,
                              }}
                            >
                              <span
                                className="h-1.5 w-1.5 rounded-full"
                                style={{ backgroundColor: activeRoleMeta.pillText }}
                              />
                              正在发言
                            </span>
                          </div>
                          <span className="text-[11.5px] font-medium text-[#76718C]">
                            {activeRoleMeta.roleLabel}
                          </span>
                        </div>

                        <div className="grid grid-cols-3 gap-1.5">
                          {DEBATE_ROLES.map((r) => {
                            const active = r.id === activeSpeakerId;
                            return (
                              <div
                                key={r.id}
                                className="flex flex-col items-center justify-center rounded-xl border-[1.5px] border-b-[2.5px] py-1.5 px-1 text-center"
                                style={{
                                  borderColor: active ? r.borderActive : "#EBE7F5",
                                  borderBottomColor: active ? r.bevelActive : "#DFD8F0",
                                  backgroundColor: active ? r.bgActive : "#FFFFFF",
                                }}
                              >
                                <div className="flex items-center gap-1 text-[11.5px] font-bold text-[#35304E]">
                                  {active && (
                                    <span
                                      className="h-1.5 w-1.5 rounded-full"
                                      style={{ backgroundColor: r.pillText }}
                                    />
                                  )}
                                  <span>{r.name}</span>
                                </div>
                                <span className="text-[10px] text-[#837F96]">
                                  {r.roleLabel}
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      </div>

                      <div className="flex flex-1 flex-col justify-between rounded-[18px] border-[1.5px] border-[#EBE7F5] border-b-[4px] border-b-[#E3DCF2] bg-white px-4 py-3">
                        <div className="flex items-center justify-between">
                          <h4 className="text-[13.5px] font-bold text-[#35304E]">
                            战况雷达
                          </h4>
                          <span className="rounded-full bg-[#EAF7F0] px-2.5 py-0.5 font-mono text-[11.5px] font-bold text-[#2A8C5F]">
                            占优 {winRate}%
                          </span>
                        </div>

                        <svg viewBox="0 0 248 176" className="h-[154px] w-full">
                          {[0.38, 0.7, 1].map((ring) => (
                            <polygon
                              key={ring}
                              points={`${cx},${cy - maxR * ring} ${cx + maxR * ring},${cy} ${cx},${cy + maxR * ring} ${cx - maxR * ring},${cy}`}
                              fill="none"
                              stroke="#E9E4F5"
                              strokeWidth="1.2"
                            />
                          ))}
                          <line x1={cx} y1={cy - maxR} x2={cx} y2={cy + maxR} stroke="#EFEBF7" />
                          <line x1={cx - maxR} y1={cy} x2={cx + maxR} y2={cy} stroke="#EFEBF7" />
                          <polygon
                            points={radarPolygon}
                            fill="rgba(139, 115, 221, 0.24)"
                            stroke="#8B73DD"
                            strokeWidth="2.2"
                          />
                          {radarPts.map((pt, i) => (
                            <circle key={i} cx={pt.x} cy={pt.y} r="3.6" fill="#6951B8" />
                          ))}
                          <text x={cx} y="22" textAnchor="middle" fill="#4B4663" fontSize="11.5" fontWeight="700">
                            逻辑 {radarScores.logic}
                          </text>
                          <text x="186" y="96" textAnchor="start" fill="#4B4663" fontSize="11.5" fontWeight="700">
                            反驳 {radarScores.rebuttal}
                          </text>
                          <text x={cx} y="168" textAnchor="middle" fill="#4B4663" fontSize="11.5" fontWeight="700">
                            气场 {radarScores.presence}
                          </text>
                          <text x="62" y="96" textAnchor="end" fill="#4B4663" fontSize="11.5" fontWeight="700">
                            地道 {radarScores.fluency}
                          </text>
                        </svg>
                      </div>
                    </aside>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
