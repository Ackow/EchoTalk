import React from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { AmbientBackdrop } from "../components/AmbientBackdrop";
import { EchoTalkLogo } from "../components/EchoTalkLogo";
import { SfxCue } from "../components/SfxCue";

const PAIN_POINT_TEXT = "背了十年英语，开口依然卡壳？";
const LOOP_STEPS = ["学", "练", "测", "评", "复习"];
const WAVE_BAR_COUNT = 41;
const KEY_CLICK_FRAMES = [6, 11, 16, 21, 27, 33, 39, 45, 51];

export const Scene1Intro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // --- Phase 1: Pain-Point Hook & Typewriter (0 - 80f) ---
  const hookIntroSpring = spring({
    frame,
    fps,
    config: { damping: 18, stiffness: 145, mass: 0.9 },
  });

  const typeProgress = interpolate(frame, [5, 52], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.quad),
  });
  const visibleChars = Math.round(typeProgress * PAIN_POINT_TEXT.length);
  const typedHeadline = PAIN_POINT_TEXT.slice(0, visibleChars);

  const subHookSpring = spring({
    frame: frame - 24,
    fps,
    config: { damping: 20, stiffness: 125, mass: 0.95 },
  });

  const hookExit = interpolate(frame, [72, 92], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.in(Easing.cubic),
  });

  // --- Phase 2: Waveform Collapse & Bloom (78 - 108f) ---
  const waveEnter = spring({
    frame: frame - 4,
    fps,
    config: { damping: 16, stiffness: 135, mass: 0.8 },
  });

  const collapseSpring = spring({
    frame: frame - 78,
    fps,
    config: { damping: 15, stiffness: 195, mass: 0.72 },
  });

  const waveFadeOut = interpolate(frame, [92, 105], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.in(Easing.quad),
  });

  const flashIn = interpolate(frame, [86, 98], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const flashOut = interpolate(frame, [98, 128], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const bloomOpacity = flashIn * flashOut;

  const shockwaveProgress = interpolate(frame, [92, 142], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.exp),
  });

  // --- Phase 3: EchoTalk 2.0 Brand Reveal (96 - 180f) ---
  const brandSpring = spring({
    frame: frame - 96,
    fps,
    config: { damping: 13, stiffness: 155, mass: 0.9 },
  });

  const logoSpring = spring({
    frame: frame - 94,
    fps,
    config: { damping: 12, stiffness: 170, mass: 0.85 },
  });

  const sloganSpring = spring({
    frame: frame - 114,
    fps,
    config: { damping: 18, stiffness: 125, mass: 0.95 },
  });

  const badgeSpring = spring({
    frame: frame - 110,
    fps,
    config: { damping: 14, stiffness: 175, mass: 0.8 },
  });

  const cursorOpacity =
    frame < 80 ? (Math.sin(frame * 0.35) > -0.15 ? 1 : 0.15) : 0;

  return (
    <AbsoluteFill className="font-sans text-[#35304E] select-none">
      {/* Frame-Synced Tactile Sound Design */}
      {KEY_CLICK_FRAMES.map((kf, idx) => (
        <SfxCue
          key={kf}
          sfx="key-click"
          from={kf}
          volume={0.22}
          playbackRate={0.94 + (idx % 3) * 0.06}
        />
      ))}
      <SfxCue sfx="whoosh" from={78} volume={0.28} playbackRate={1.25} />
      <SfxCue sfx="bloom-reveal" from={94} volume={0.40} />
      <SfxCue sfx="pop" from={124} volume={0.14} playbackRate={0.96} />
      <SfxCue sfx="pop" from={134} volume={0.14} playbackRate={1.06} />
      <SfxCue sfx="pop" from={144} volume={0.15} playbackRate={1.16} />

      <AmbientBackdrop
        intensity={interpolate(frame, [88, 114], [0.95, 1.2], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.out(Easing.cubic),
        })}
        gridScale={interpolate(brandSpring, [0, 1], [1.04, 1])}
      />

      {/* PHASE 1: Pain Point Hook (Bright Tactile Purple-White) */}
      {frame < 98 && (
        <AbsoluteFill className="flex flex-col items-center justify-center">
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              transform: `translateY(${interpolate(hookIntroSpring, [0, 1], [28, -56]) - hookExit * 22}px) scale(${1 - hookExit * 0.08})`,
              opacity: hookIntroSpring * (1 - hookExit),
              filter: `blur(${hookExit * 8}px)`,
            }}
          >
            {/* Tactile White-Lavender Eyebrow Pill */}
            <div className="mb-7 inline-flex items-center gap-2.5 rounded-full border-[1.5px] border-[#E6E0F5] border-b-[3px] border-b-[#DDD5F1] bg-white/95 px-5 py-1.5 shadow-sm">
              <span className="h-2.5 w-2.5 rounded-full bg-[#45C98E] shadow-[0_0_8px_rgba(69,201,142,0.75)]" />
              <span className="font-mono text-[14px] font-bold tracking-[0.16em] text-[#6046B4] uppercase">
                Speaking Practice · Reimagined
              </span>
            </div>

            {/* Typewriter Hook Headline */}
            <div className="flex items-center justify-center min-h-[96px]">
              <h1
                className="text-[76px] font-extrabold tracking-[-0.03em] leading-none"
                style={{
                  background:
                    "linear-gradient(135deg, #2C2642 15%, #6951B8 85%)",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                }}
              >
                {typedHeadline}
              </h1>
              <span
                style={{
                  display: "inline-block",
                  width: 5,
                  height: 70,
                  marginLeft: 10,
                  borderRadius: 4,
                  background: "linear-gradient(180deg, #45C98E, #8B73DD)",
                  boxShadow: "0 0 14px rgba(139, 115, 221, 0.55)",
                  opacity: cursorOpacity,
                }}
              />
            </div>

            <p
              className="mt-6 text-[24px] font-medium tracking-[0.02em] text-[#6E6886]"
              style={{
                opacity: subHookSpring,
                transform: `translateY(${interpolate(subHookSpring, [0, 1], [16, 0])}px)`,
              }}
            >
              死板脚本 · 泛泛闲聊 · AI 状态幻觉 · 缺乏实时发音与多角色实战
            </p>
          </div>
        </AbsoluteFill>
      )}

      {/* PHASE 1 -> 2: Vibrant EchoTalk Purple & Mint Waveform Collapsing to Center */}
      {frame < 108 && (
        <AbsoluteFill className="flex items-center justify-center pointer-events-none">
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: 180,
              transform: `translateY(${interpolate(collapseSpring, [0, 1], [148, 0])}px)`,
              opacity: waveEnter * waveFadeOut,
            }}
          >
            {Array.from({ length: WAVE_BAR_COUNT }).map((_, i) => {
              const center = (WAVE_BAR_COUNT - 1) / 2;
              const dist = Math.abs(i - center);
              const normalizedDist = dist / center;
              const envelope = Math.exp(-normalizedDist * normalizedDist * 3.4);

              const t = frame / fps;
              const wave =
                0.52 +
                0.28 * Math.sin(t * 9.5 + i * 0.48) +
                0.2 * Math.cos(t * 14.2 - i * 0.72);

              const activeHeight = Math.max(10, 138 * envelope * wave);
              const collapsedHeight = 14 + (1 - normalizedDist) * 28;
              const barHeight = interpolate(
                collapseSpring,
                [0, 1],
                [activeHeight, collapsedHeight]
              );

              const baseOffsetX = (i - center) * 22;
              const offsetX = baseOffsetX * (1 - collapseSpring);

              const barOpacity = interpolate(
                collapseSpring,
                [0, 0.85, 1],
                [0.35 + envelope * 0.65, 0.9, 1 - normalizedDist * 0.85]
              );

              return (
                <div
                  key={i}
                  style={{
                    position: "absolute",
                    width: interpolate(collapseSpring, [0, 1], [7.5, 5]),
                    height: barHeight,
                    borderRadius: 999,
                    transform: `translateX(${offsetX}px)`,
                    opacity: barOpacity,
                    background:
                      dist < 6
                        ? "linear-gradient(180deg, #8B73DD 0%, #6951B8 100%)"
                        : i % 5 === 0
                          ? "linear-gradient(180deg, #45C98E 0%, #2A8C5F 100%)"
                          : "linear-gradient(180deg, #B8A9F8 0%, #8B73DD 100%)",
                    boxShadow:
                      dist < 9
                        ? "0 4px 16px rgba(139, 115, 221, 0.35)"
                        : undefined,
                  }}
                />
              );
            })}
          </div>
        </AbsoluteFill>
      )}

      {/* Soft Lavender-Mint Convergence Bloom & Ripple */}
      {frame >= 84 && frame <= 146 && (
        <AbsoluteFill className="flex items-center justify-center pointer-events-none">
          <div
            style={{
              position: "absolute",
              width: 340,
              height: 340,
              borderRadius: "50%",
              background:
                "radial-gradient(circle, rgba(139,115,221,0.45) 0%, rgba(184,169,248,0.32) 38%, rgba(69,201,142,0.18) 65%, transparent 78%)",
              filter: "blur(22px)",
              opacity: bloomOpacity,
              transform: `scale(${interpolate(flashIn, [0, 1], [0.25, 1.4])})`,
            }}
          />
          <div
            style={{
              position: "absolute",
              width: 240,
              height: 240,
              borderRadius: "50%",
              border: "2px solid rgba(139, 115, 221, 0.42)",
              opacity: (1 - shockwaveProgress) * 0.85,
              transform: `scale(${0.4 + shockwaveProgress * 5.2})`,
            }}
          />
        </AbsoluteFill>
      )}

      {/* PHASE 3: EchoTalk 2.0 Official Light Purple-White Brand Reveal */}
      {frame >= 92 && (
        <AbsoluteFill className="flex flex-col items-center justify-center">
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
            }}
          >
            <div className="flex items-center gap-7">
              <div
                style={{
                  transform: `scale(${interpolate(logoSpring, [0, 1], [0.35, 1])}) rotate(${interpolate(logoSpring, [0, 1], [-10, 0])}deg)`,
                  opacity: interpolate(logoSpring, [0, 0.3], [0, 1], {
                    extrapolateRight: "clamp",
                  }),
                }}
              >
                <EchoTalkLogo size={130} glow framed />
              </div>

              <div
                className="flex items-baseline gap-4"
                style={{
                  transform: `translateY(${interpolate(brandSpring, [0, 1], [34, 0])}px) scale(${interpolate(brandSpring, [0, 1], [0.84, 1])})`,
                  opacity: interpolate(brandSpring, [0, 0.35], [0, 1], {
                    extrapolateRight: "clamp",
                  }),
                }}
              >
                <span
                  className="text-[128px] font-extrabold tracking-[-0.045em] leading-none"
                  style={{
                    background:
                      "linear-gradient(135deg, #2C2642 12%, #6951B8 68%, #8B73DD 100%)",
                    WebkitBackgroundClip: "text",
                    WebkitTextFillColor: "transparent",
                  }}
                >
                  EchoTalk
                </span>

                <span
                  className="rounded-2xl border-[1.5px] border-[#BEE8D3] border-b-[3.5px] border-b-[#98D9B8] bg-[#EAF7F0] px-4 py-1.5 font-mono text-[28px] font-extrabold tracking-tight text-[#2A8C5F]"
                  style={{
                    transform: `translateY(${interpolate(badgeSpring, [0, 1], [18, -14])}px) scale(${interpolate(badgeSpring, [0, 1], [0.7, 1])})`,
                    opacity: badgeSpring,
                  }}
                >
                  2.0
                </span>
              </div>
            </div>

            <p
              className="mt-8 text-[34px] font-bold tracking-[0.05em] text-[#4B4566]"
              style={{
                opacity: sloganSpring,
                transform: `translateY(${interpolate(sloganSpring, [0, 1], [24, 0])}px)`,
              }}
            >
              和 AI 练英语口语 · 从日常对话到模拟群面
            </p>

            {/* Tactile Closed-Loop Pills */}
            <div className="mt-9 flex items-center gap-3">
              {LOOP_STEPS.map((step, idx) => {
                const pillSpring = spring({
                  frame: frame - (124 + idx * 5),
                  fps,
                  config: { damping: 16, stiffness: 175, mass: 0.75 },
                });
                const isMint = idx === 1 || idx === 4;
                return (
                  <React.Fragment key={step}>
                    <div
                      className={`rounded-full border-[1.5px] border-b-[3px] px-5 py-1.5 text-[18px] font-bold ${
                        isMint
                          ? "border-[#BEE8D3] border-b-[#98D9B8] bg-[#EAF7F0] text-[#2A8C5F]"
                          : "border-[#E6E0F5] border-b-[#DDD5F1] bg-white text-[#6046B4]"
                      }`}
                      style={{
                        opacity: pillSpring,
                        transform: `translateY(${interpolate(pillSpring, [0, 1], [14, 0])}px) scale(${interpolate(pillSpring, [0, 1], [0.88, 1])})`,
                      }}
                    >
                      {step}
                    </div>
                    {idx < LOOP_STEPS.length - 1 && (
                      <span
                        className="font-bold text-[#B8A9F8] text-base"
                        style={{ opacity: pillSpring }}
                      >
                        →
                      </span>
                    )}
                  </React.Fragment>
                );
              })}
            </div>
          </div>
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};
