import React from "react";
import { Audio, Easing, interpolate, Sequence, staticFile } from "remotion";

export type SfxName =
  | "key-click"
  | "whoosh"
  | "pop"
  | "mic-ping"
  | "success-chime"
  | "bloom-reveal"
  | "star-sparkle";

const SFX_DURATIONS_60FPS: Record<SfxName, number> = {
  "key-click": 8,
  whoosh: 32,
  pop: 14,
  "mic-ping": 20,
  "success-chime": 28,
  "bloom-reveal": 48,
  "star-sparkle": 40,
};

interface SfxCueProps {
  /** Which synthesized sound file in public/sfx/ to play */
  sfx: SfxName;
  /** Exact local scene frame to trigger the sound */
  from: number;
  /** Subtle tactile volume (0.0 - 1.0) */
  volume?: number;
  /** Slight pitch/speed shift for organic musical variation */
  playbackRate?: number;
}

/**
 * Frame-accurate Remotion <Audio> cue helper for tactile UI SFX.
 */
export const SfxCue: React.FC<SfxCueProps> = ({
  sfx,
  from,
  volume = 0.28,
  playbackRate = 1,
}) => {
  const durationInFrames = Math.ceil(
    SFX_DURATIONS_60FPS[sfx] / Math.max(0.5, playbackRate)
  );

  return (
    <Sequence from={from} durationInFrames={durationInFrames} layout="none">
      <Audio
        src={staticFile(`sfx/${sfx}.wav`)}
        volume={volume}
        playbackRate={playbackRate}
      />
    </Sequence>
  );
};

interface VoiceClipProps {
  /** Relative path under public/, e.g. "audio/leo-cafe.mp3" */
  src: string;
  /** Local scene frame to start voice playback */
  from: number;
  /** Total playback window in frames */
  durationInFrames: number;
  /** Peak speaking volume */
  peakVolume?: number;
  /** Smooth fade-in frames (e.g. 14f = 0.23s) */
  fadeInFrames?: number;
  /** Smooth fade-out frames (e.g. 28f = 0.47s) */
  fadeOutFrames?: number;
  /** Slight playback rate adjustment */
  playbackRate?: number;
}

/**
 * English neural voiceover clip with buttery smooth fade-in and fade-out envelope.
 */
export const VoiceClip: React.FC<VoiceClipProps> = ({
  src,
  from,
  durationInFrames,
  peakVolume = 0.85,
  fadeInFrames = 14,
  fadeOutFrames = 28,
  playbackRate = 1,
}) => {
  return (
    <Sequence from={from} durationInFrames={durationInFrames} layout="none">
      <Audio
        src={staticFile(src)}
        playbackRate={playbackRate}
        volume={(localFrame) => {
          const fadeIn = interpolate(
            localFrame,
            [0, fadeInFrames],
            [0, 1],
            {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.out(Easing.quad),
            }
          );
          const fadeOut = interpolate(
            localFrame,
            [Math.max(fadeInFrames, durationInFrames - fadeOutFrames), durationInFrames],
            [1, 0],
            {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.inOut(Easing.cubic),
            }
          );
          return peakVolume * fadeIn * fadeOut;
        }}
      />
    </Sequence>
  );
};
