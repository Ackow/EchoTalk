import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";

interface AmbientBackdropProps {
  /** Visual intensity of the pastel lavender-mint aurora washes */
  intensity?: number;
  /** Optional subtle zoom scale for the breathing tech grid */
  gridScale?: number;
  /** Shift aurora focus horizontally (-1 to 1) */
  focusX?: number;
  /** Shift aurora focus vertically (-1 to 1) */
  focusY?: number;
}

/**
 * EchoTalk 2.0 Official Light Tactile Purple-White Stage:
 * Crisp snow-lavender canvas (#F8F7FD -> #FFFFFF) with airy #8B73DD lavender
 * & #45C98E mint pastel aurora washes and a whisper-subtle breathing grid.
 */
export const AmbientBackdrop: React.FC<AmbientBackdropProps> = ({
  intensity = 1,
  gridScale = 1,
  focusX = 0,
  focusY = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;

  // Gentle breathing lavender grid
  const gridOpacity =
    interpolate(Math.sin(t * 1.35), [-1, 1], [0.22, 0.38]) * intensity;
  const gridBreathScale = gridScale + Math.sin(t * 0.8) * 0.006;

  // Smooth pastel aurora orb drift
  const orb1X = 24 + Math.sin(t * 0.52) * 8 + focusX * 10;
  const orb1Y = 22 + Math.cos(t * 0.44) * 7 + focusY * 8;

  const orb2X = 78 + Math.cos(t * 0.48) * 9 + focusX * 8;
  const orb2Y = 72 + Math.sin(t * 0.56) * 8 + focusY * 8;

  const orb3X = 68 + Math.sin(t * 0.68 + 1.1) * 10;
  const orb3Y = 18 + Math.cos(t * 0.5 + 0.4) * 6;

  return (
    <AbsoluteFill
      style={{
        background:
          "linear-gradient(180deg, #FBFAFF 0%, #F5F2FC 55%, #F9F8FE 100%)",
        overflow: "hidden",
      }}
    >
      {/* Airy Lavender (#8B73DD) & Mint (#45C98E) Pastel Aurora Washes */}
      <div
        style={{
          position: "absolute",
          inset: "-12%",
          background: `
            radial-gradient(720px circle at ${orb1X}% ${orb1Y}%, rgba(139, 115, 221, ${0.18 * intensity}), transparent 68%),
            radial-gradient(660px circle at ${orb2X}% ${orb2Y}%, rgba(184, 169, 248, ${0.22 * intensity}), transparent 70%),
            radial-gradient(540px circle at ${orb3X}% ${orb3Y}%, rgba(69, 201, 142, ${0.13 * intensity}), transparent 66%)
          `,
          filter: "blur(36px)",
          willChange: "transform",
        }}
      />

      {/* Subtle Top Lavender Wash matching website-home.jpg */}
      <div
        style={{
          position: "absolute",
          top: -140,
          left: "12%",
          right: "12%",
          height: 280,
          background:
            "radial-gradient(ellipse at center, rgba(139, 115, 221, 0.14) 0%, rgba(184, 169, 248, 0.05) 48%, transparent 74%)",
          filter: "blur(24px)",
          opacity: 0.9 * intensity,
        }}
      />

      {/* Subtle Breathing Lavender Grid */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: `
            linear-gradient(to right, rgba(139, 115, 221, 0.11) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(139, 115, 221, 0.11) 1px, transparent 1px)
          `,
          backgroundSize: "64px 64px",
          opacity: gridOpacity,
          transform: `scale(${gridBreathScale})`,
          maskImage:
            "radial-gradient(ellipse 80% 76% at 50% 48%, rgba(0, 0, 0, 1) 18%, rgba(0, 0, 0, 0) 94%)",
          WebkitMaskImage:
            "radial-gradient(ellipse 80% 76% at 50% 48%, rgba(0, 0, 0, 1) 18%, rgba(0, 0, 0, 0) 94%)",
        }}
      />

      {/* Fine Dot Intersections */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage:
            "radial-gradient(circle, rgba(139, 115, 221, 0.28) 1.2px, transparent 1.2px)",
          backgroundSize: "64px 64px",
          opacity: gridOpacity * 0.95,
          transform: `scale(${gridBreathScale})`,
          maskImage:
            "radial-gradient(ellipse 70% 66% at 50% 50%, rgba(0, 0, 0, 1) 12%, rgba(0, 0, 0, 0) 88%)",
          WebkitMaskImage:
            "radial-gradient(ellipse 70% 66% at 50% 50%, rgba(0, 0, 0, 1) 12%, rgba(0, 0, 0, 0) 88%)",
        }}
      />

      {/* Soft Edge Framing Vignette (bright, never muddy) */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(ellipse 92% 88% at 50% 50%, transparent 58%, rgba(226, 219, 245, 0.36) 100%)",
          pointerEvents: "none",
        }}
      />
    </AbsoluteFill>
  );
};
