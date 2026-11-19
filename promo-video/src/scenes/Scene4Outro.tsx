import React from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Star } from "lucide-react";
import { AmbientBackdrop } from "../components/AmbientBackdrop";
import { EchoTalkLogo } from "../components/EchoTalkLogo";
import { SfxCue } from "../components/SfxCue";

const TECH_STACK = [
  { name: "Python 3.12", dot: "#3776AB" },
  { name: "FastAPI", dot: "#2A8C5F" },
  { name: "LangGraph", dot: "#8B73DD" },
  { name: "LightRAG", dot: "#6951B8" },
  { name: "Vue 3", dot: "#45C98E" },
  { name: "Electron 30", dot: "#5B8DEF" },
  { name: "MySQL 8.0", dot: "#4479A1" },
];

const SPARK_COUNT = 12;

const GitHubMark: React.FC<{ size?: number }> = ({ size = 26 }) => (
  <svg
    viewBox="0 0 24 24"
    width={size}
    height={size}
    fill="currentColor"
    aria-hidden="true"
  >
    <path d="M12 0.3C5.37 0.3 0 5.67 0 12.3c0 5.3 3.44 9.8 8.2 11.39 0.6 0.11 0.82-0.26 0.82-0.58 0-0.29-0.01-1.05-0.02-2.06-3.34 0.72-4.04-1.61-4.04-1.61-0.55-1.39-1.33-1.76-1.33-1.76-1.09-0.74 0.08-0.73 0.08-0.73 1.2 0.09 1.84 1.24 1.84 1.24 1.07 1.83 2.81 1.3 3.5 1 0.11-0.78 0.42-1.3 0.76-1.6-2.66-0.3-5.47-1.33-5.47-5.93 0-1.31 0.47-2.38 1.24-3.22-0.12-0.3-0.54-1.52 0.12-3.18 0 0 1.01-0.32 3.3 1.23 0.96-0.27 1.98-0.4 3-0.4 1.02 0 2.04 0.14 3 0.4 2.29-1.55 3.3-1.23 3.3-1.23 0.66 1.66 0.24 2.88 0.12 3.18 0.77 0.84 1.24 1.91 1.24 3.22 0 4.61-2.81 5.62-5.48 5.92 0.43 0.37 0.81 1.1 0.81 2.22 0 1.6-0.01 2.9-0.01 3.29 0 0.32 0.22 0.7 0.82 0.58C20.56 22.1 24 17.6 24 12.3 24 5.67 18.63 0.3 12 0.3z" />
  </svg>
);

export const Scene4Outro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const convergeSpring = spring({
    frame,
    fps,
    config: { damping: 18, stiffness: 108, mass: 1.0 },
  });

  const logoSpring = spring({
    frame: frame - 8,
    fps,
    config: { damping: 14, stiffness: 148, mass: 0.9 },
  });

  const titleSpring = spring({
    frame: frame - 16,
    fps,
    config: { damping: 15, stiffness: 138, mass: 0.92 },
  });

  const taglineSpring = spring({
    frame: frame - 28,
    fps,
    config: { damping: 18, stiffness: 122, mass: 0.95 },
  });

  const ctaSpring = spring({
    frame: frame - 60,
    fps,
    config: { damping: 15, stiffness: 138, mass: 0.9 },
  });

  const cursorEnter = spring({
    frame: frame - 78,
    fps,
    config: { damping: 17, stiffness: 118, mass: 0.95 },
  });

  const clickFrame = 116;
  const isStarred = frame >= clickFrame;

  const starBurstSpring = spring({
    frame: frame - clickFrame,
    fps,
    config: { damping: 11, stiffness: 215, mass: 0.75 },
  });

  const pressScale =
    frame >= clickFrame - 5 && frame <= clickFrame + 16
      ? interpolate(
          frame,
          [clickFrame - 5, clickFrame, clickFrame + 7, clickFrame + 16],
          [1, 0.92, 1.05, 1],
          {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.out(Easing.cubic),
          }
        )
      : 1;

  const sparkProgress = interpolate(frame, [clickFrame, clickFrame + 38], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.exp),
  });

  const cursorFadeOut = interpolate(frame, [134, 158], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.in(Easing.cubic),
  });

  const footerSpring = spring({
    frame: frame - 82,
    fps,
    config: { damping: 18, stiffness: 112 },
  });

  return (
    <AbsoluteFill className="font-sans text-[#35304E] select-none">
      {/* Frame-Synced Tactile Sound Design: Outro Convergence + Star Click Burst */}
      <SfxCue sfx="whoosh" from={0} volume={0.26} playbackRate={0.92} />
      <SfxCue sfx="bloom-reveal" from={10} volume={0.34} />
      <SfxCue sfx="pop" from={60} volume={0.22} playbackRate={1.0} />
      <SfxCue sfx="key-click" from={116} volume={0.32} playbackRate={1.25} />
      <SfxCue sfx="star-sparkle" from={116} volume={0.40} />

      <AmbientBackdrop intensity={1.15} />

      {/* Converging Soft Lavender & Mint Orbital Rings */}
      <AbsoluteFill className="flex items-center justify-center pointer-events-none">
        {[
          { d: 580, color: "rgba(139, 115, 221, 0.18)" },
          { d: 820, color: "rgba(69, 201, 142, 0.16)" },
          { d: 1080, color: "rgba(184, 169, 248, 0.18)" },
        ].map((ring, idx) => (
          <div
            key={ring.d}
            style={{
              position: "absolute",
              width: ring.d,
              height: ring.d,
              borderRadius: "50%",
              border: `1.5px solid ${ring.color}`,
              transform: `scale(${interpolate(convergeSpring, [0, 1], [1.45 + idx * 0.18, 1])})`,
              opacity: interpolate(convergeSpring, [0, 0.4, 1], [0, 0.8, 0.65]),
            }}
          />
        ))}
      </AbsoluteFill>

      <AbsoluteFill className="flex flex-col items-center justify-center px-16">
        {/* Official EchoTalk 2.0 Mascot Logo + Wordmark */}
        <div className="flex flex-col items-center">
          <div
            style={{
              transform: `scale(${interpolate(logoSpring, [0, 1], [0.55, 1])}) translateY(${interpolate(logoSpring, [0, 1], [28, 0])}px)`,
              opacity: logoSpring,
            }}
          >
            <EchoTalkLogo size={124} glow framed />
          </div>

          <div
            className="mt-7 flex items-baseline gap-4"
            style={{
              transform: `translateY(${interpolate(titleSpring, [0, 1], [28, 0])}px)`,
              opacity: titleSpring,
            }}
          >
            <h1
              className="text-[104px] font-extrabold tracking-[-0.045em] leading-none"
              style={{
                background:
                  "linear-gradient(135deg, #2C2642 15%, #6951B8 70%, #8B73DD 100%)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
              }}
            >
              EchoTalk
            </h1>
            <span className="rounded-2xl border-[1.5px] border-[#BEE8D3] border-b-[3.5px] border-b-[#98D9B8] bg-[#EAF7F0] px-3.5 py-1 font-mono text-[24px] font-extrabold text-[#2A8C5F]">
              2.0
            </span>
          </div>

          <p
            className="mt-4 text-[26px] font-bold tracking-[0.04em] text-[#5A5475]"
            style={{
              opacity: taglineSpring,
              transform: `translateY(${interpolate(taglineSpring, [0, 1], [18, 0])}px)`,
            }}
          >
            开源全栈 AI 英语听说与多智能体实训平台
          </p>
        </div>

        {/* Core Tech Stack Tactile White Pills */}
        <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
          {TECH_STACK.map((tech, idx) => {
            const pillSpring = spring({
              frame: frame - (40 + idx * 4),
              fps,
              config: { damping: 16, stiffness: 165, mass: 0.78 },
            });
            return (
              <div
                key={tech.name}
                className="inline-flex items-center gap-2 rounded-full border-[1.5px] border-[#EBE7F5] border-b-[3px] border-b-[#E3DCF2] bg-white px-4 py-1.5 shadow-sm"
                style={{
                  opacity: pillSpring,
                  transform: `translateY(${interpolate(pillSpring, [0, 1], [16, 0])}px) scale(${interpolate(pillSpring, [0, 1], [0.88, 1])})`,
                }}
              >
                <span
                  className="h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: tech.dot }}
                />
                <span className="font-mono text-[14.5px] font-bold text-[#35304E]">
                  {tech.name}
                </span>
              </div>
            );
          })}
        </div>

        {/* Prominent Tactile GitHub Repository CTA Card with One-Click Star */}
        <div
          className="relative mt-11"
          style={{
            opacity: ctaSpring,
            transform: `translateY(${interpolate(ctaSpring, [0, 1], [32, 0])}px) scale(${interpolate(ctaSpring, [0, 1], [0.92, 1])})`,
          }}
        >
          {/* Soft Lavender-Gold Ambient Halo */}
          <div
            className="pointer-events-none absolute -inset-3 rounded-[28px] blur-2xl"
            style={{
              background: isStarred
                ? "linear-gradient(90deg, rgba(139,115,221,0.28), rgba(250,204,21,0.28), rgba(69,201,142,0.24))"
                : "linear-gradient(90deg, rgba(139,115,221,0.22), rgba(69,201,142,0.16))",
            }}
          />

          <div
            className="relative flex items-center gap-6 rounded-[24px] border-[2px] border-b-[5px] bg-white px-8 py-5"
            style={{
              borderColor: isStarred ? "#EAB308" : "#E5DEF4",
              borderBottomColor: isStarred ? "#CA8A04" : "#D6CCEE",
              boxShadow:
                "0 22px 54px rgba(105, 81, 184, 0.14)",
            }}
          >
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-[#EBE7F5] bg-[#F4F0FF] text-[#35304E]">
                <GitHubMark size={26} />
              </div>
              <div className="flex flex-col">
                <span className="font-mono text-[12px] font-bold tracking-[0.16em] text-[#837F96] uppercase">
                  Open Source on GitHub
                </span>
                <span className="font-mono text-[28px] font-extrabold tracking-tight text-[#35304E]">
                  github.com/
                  <span className="text-[#6951B8]">Ackow/EchoTalk</span>
                </span>
              </div>
            </div>

            <div className="h-11 w-[1.5px] bg-[#EBE7F5]" />

            {/* Tactile One-Click Star Button */}
            <div className="relative">
              {isStarred && sparkProgress < 1 && (
                <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
                  {Array.from({ length: SPARK_COUNT }).map((_, i) => {
                    const angle = (i / SPARK_COUNT) * Math.PI * 2;
                    const dist = 24 + sparkProgress * 64;
                    const sx = Math.cos(angle) * dist;
                    const sy = Math.sin(angle) * dist;
                    const sparkColor =
                      i % 3 === 0 ? "#EAB308" : i % 3 === 1 ? "#8B73DD" : "#45C98E";
                    return (
                      <span
                        key={i}
                        style={{
                          position: "absolute",
                          width: i % 2 === 0 ? 7 : 5,
                          height: i % 2 === 0 ? 7 : 5,
                          borderRadius: "50%",
                          backgroundColor: sparkColor,
                          transform: `translate(${sx}px, ${sy}px) scale(${1 - sparkProgress * 0.7})`,
                          opacity: 1 - sparkProgress,
                        }}
                      />
                    );
                  })}
                </div>
              )}

              <div
                className="flex items-center gap-3 rounded-2xl border-[1.5px] border-b-[3.5px] px-6 py-3"
                style={{
                  transform: `scale(${pressScale})`,
                  borderColor: isStarred ? "#EAB308" : "#8067D1",
                  borderBottomColor: isStarred ? "#CA8A04" : "#6951B8",
                  background: isStarred ? "#FEF9C3" : "#8B73DD",
                }}
              >
                <div
                  style={{
                    transform: isStarred
                      ? `scale(${interpolate(starBurstSpring, [0, 0.45, 1], [0.5, 1.35, 1])}) rotate(${interpolate(starBurstSpring, [0, 1], [-45, 0])}deg)`
                      : "none",
                  }}
                >
                  <Star
                    className="h-6 w-6"
                    color={isStarred ? "#CA8A04" : "#FFFFFF"}
                    fill={isStarred ? "#EAB308" : "transparent"}
                    strokeWidth={2.4}
                  />
                </div>
                <span
                  className={`text-[19px] font-extrabold tracking-tight ${
                    isStarred ? "text-[#A16207]" : "text-white"
                  }`}
                >
                  {isStarred ? "Starred" : "Star"}
                </span>
              </div>

              {frame >= 76 && frame <= 162 && (
                <svg
                  viewBox="0 0 28 28"
                  width="30"
                  height="30"
                  style={{
                    position: "absolute",
                    right: interpolate(cursorEnter, [0, 1], [-86, 12]),
                    bottom: interpolate(cursorEnter, [0, 1], [-68, -12]),
                    opacity:
                      interpolate(cursorEnter, [0, 0.25], [0, 1], {
                        extrapolateRight: "clamp",
                      }) * cursorFadeOut,
                    transform: `scale(${pressScale})`,
                    filter: "drop-shadow(0 6px 12px rgba(53, 48, 78, 0.28))",
                    pointerEvents: "none",
                  }}
                >
                  <path
                    d="M5 3L22 14.5L14.2 16.2L10.8 23.5L5 3Z"
                    fill="#35304E"
                    stroke="#FFFFFF"
                    strokeWidth="2"
                    strokeLinejoin="round"
                  />
                </svg>
              )}
            </div>
          </div>
        </div>

        {/* Clean Footer */}
        <div
          className="mt-9 flex items-center gap-4 font-mono text-[14px] font-semibold text-[#7E7896]"
          style={{
            opacity: footerSpring,
            transform: `translateY(${interpolate(footerSpring, [0, 1], [12, 0])}px)`,
          }}
        >
          <span>MIT License</span>
          <span>·</span>
          <span>1v1 语音对话 · 多角色辩论 · 场景探索 · 双引擎 RAG</span>
          <span>·</span>
          <span className="text-[#2A8C5F]">EchoTalk 2.0</span>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
