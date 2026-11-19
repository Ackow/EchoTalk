import React from "react";
import { Img, staticFile } from "remotion";

interface EchoTalkLogoProps {
  size?: number;
  glow?: boolean;
  /** Framed inside tactile purple-white tile (true) or raw mascot (false) */
  framed?: boolean;
}

/**
 * Official EchoTalk 2.0 Mascot Logo (frontend/public/app-icon.png)
 * Winking white speech-bubble mascot with #8B73DD purple headphones & #45C98E mint rays.
 */
export const EchoTalkLogo: React.FC<EchoTalkLogoProps> = ({
  size = 88,
  glow = true,
  framed = true,
}) => {
  const radius = Math.round(size * 0.25);

  return (
    <div
      style={{
        width: size,
        height: size,
        position: "relative",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
      }}
    >
      {glow && (
        <div
          style={{
            position: "absolute",
            inset: -size * 0.28,
            borderRadius: "50%",
            background:
              "radial-gradient(circle at 42% 52%, rgba(139, 115, 221, 0.52) 0%, rgba(69, 201, 142, 0.24) 48%, transparent 74%)",
            filter: "blur(20px)",
            pointerEvents: "none",
          }}
        />
      )}

      {framed ? (
        <div
          style={{
            position: "relative",
            width: size,
            height: size,
            borderRadius: radius,
            background: "linear-gradient(180deg, #FFFFFF 0%, #F6F3FF 100%)",
            border: `${Math.max(1.5, size * 0.02)}px solid #EBE7F5`,
            borderBottom: `${Math.max(3, size * 0.045)}px solid #DDD5F3`,
            boxShadow: glow
              ? "0 18px 46px rgba(139, 115, 221, 0.36), 0 4px 12px rgba(0, 0, 0, 0.22)"
              : "0 4px 12px rgba(105, 81, 184, 0.14)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: Math.round(size * 0.08),
            overflow: "hidden",
          }}
        >
          <Img
            src={staticFile("app-icon.png")}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "contain",
            }}
          />
        </div>
      ) : (
        <Img
          src={staticFile("app-icon.png")}
          style={{
            position: "relative",
            width: size,
            height: size,
            objectFit: "contain",
            filter: glow
              ? "drop-shadow(0 16px 32px rgba(139, 115, 221, 0.42))"
              : undefined,
          }}
        />
      )}
    </div>
  );
};
