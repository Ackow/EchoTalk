import React from "react";
import {
  AbsoluteFill,
  Audio,
  Composition,
  Easing,
  interpolate,
  staticFile,
} from "remotion";
import {
  TransitionSeries,
  springTiming,
} from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { slide } from "@remotion/transitions/slide";
import { Scene1Intro } from "./scenes/Scene1Intro";
import { Scene2Demo } from "./scenes/Scene2Demo";
import { Scene3Features } from "./scenes/Scene3Features";
import { Scene4Outro } from "./scenes/Scene4Outro";

const FPS = 60;
const TRANSITION_FRAMES = 20;

const SCENE_1_FRAMES = 170; // 0.00s - 2.83s (Pain-point Hook & EchoTalk 2.0 Reveal)
const SCENE_2_FRAMES = 440; // 2.50s - 9.83s (1v1 Voice -> Multi-Role Debate + Neural English Audio)
const SCENE_3_FRAMES = 310; // 9.50s - 14.67s (Scenes Explorer + Dual-Engine RAG + Speech/SM-2)
const SCENE_4_FRAMES = 220; // 14.33s - 18.00s (Open Source CTA & GitHub Star Burst Freeze)

// Exact total: 170 + 440 + 310 + 220 - (20 * 3) = 1080 frames (18.0s @ 60fps)
const TOTAL_DURATION_FRAMES =
  SCENE_1_FRAMES +
  SCENE_2_FRAMES +
  SCENE_3_FRAMES +
  SCENE_4_FRAMES -
  TRANSITION_FRAMES * 3;

/**
 * Dynamic BGM volume curve:
 * - Silky 0.75s fade-in from silence
 * - Automatic gentle vocal ducking (0.34 -> 0.13) while Leo, Marcus & Elena speak English
 * - Smooth lift back to 0.34 for Scenes/RAG & Outro
 * - Silky 1.5s fade-out at the end
 */
const bgmVolumeCurve = (globalFrame: number): number => {
  const baseGain = 0.34;

  const fadeIn = interpolate(globalFrame, [0, 45], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.quad),
  });

  const fadeOut = interpolate(
    globalFrame,
    [TOTAL_DURATION_FRAMES - 90, TOTAL_DURATION_FRAMES],
    [1, 0],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.inOut(Easing.cubic),
    }
  );

  // Scene 2 starts at global frame 150 (170 - 20):
  // Leo speaks: 260..358, Marcus speaks: 370..476, Elena speaks: 480..588
  const duckIn = interpolate(globalFrame, [248, 266], [1, 0.38], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });
  const duckOut = interpolate(globalFrame, [576, 602], [0.38, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });
  const vocalDuckMultiplier = globalFrame < 420 ? duckIn : duckOut;

  return baseGain * fadeIn * fadeOut * vocalDuckMultiplier;
};

export const EchoTalkLaunchVideo: React.FC = () => {
  return (
    <AbsoluteFill>
      {/* Full-Length Modern Bright Tech Launch BGM with Auto Vocal Ducking */}
      <Audio src={staticFile("audio/bgm.wav")} volume={bgmVolumeCurve} />

      <TransitionSeries>
        <TransitionSeries.Sequence durationInFrames={SCENE_1_FRAMES}>
          <Scene1Intro />
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          presentation={fade()}
          timing={springTiming({
            config: { damping: 200 },
            durationInFrames: TRANSITION_FRAMES,
          })}
        />

        <TransitionSeries.Sequence durationInFrames={SCENE_2_FRAMES}>
          <Scene2Demo />
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          presentation={slide({ direction: "from-bottom" })}
          timing={springTiming({
            config: { damping: 200 },
            durationInFrames: TRANSITION_FRAMES,
          })}
        />

        <TransitionSeries.Sequence durationInFrames={SCENE_3_FRAMES}>
          <Scene3Features />
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          presentation={fade()}
          timing={springTiming({
            config: { damping: 200 },
            durationInFrames: TRANSITION_FRAMES,
          })}
        />

        <TransitionSeries.Sequence durationInFrames={SCENE_4_FRAMES}>
          <Scene4Outro />
        </TransitionSeries.Sequence>
      </TransitionSeries>
    </AbsoluteFill>
  );
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="EchoTalkLaunch"
      component={EchoTalkLaunchVideo}
      durationInFrames={TOTAL_DURATION_FRAMES}
      fps={FPS}
      width={1920}
      height={1080}
    />
  );
};
