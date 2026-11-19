import React from "react";

export type AvatarPersona = "leo" | "marcus" | "elena";

interface Avatar2DProps {
  persona: AvatarPersona;
  frame: number;
  fps: number;
  speaking: boolean;
  listening?: boolean;
  height?: number;
}

/**
 * Procedural 2D Character Portraits matching EchoTalk 2.0's clean illustrated style
 * (CharacterPortrait.vue / AvatarStage.vue) with real-time RMS lip-sync & blinking.
 */
export const Avatar2D: React.FC<Avatar2DProps> = ({
  persona,
  frame,
  fps,
  speaking,
  listening = false,
  height = 166,
}) => {
  const t = frame / fps;
  const lipOpen = speaking
    ? 3.8 + Math.abs(Math.sin(t * 18.2)) * 6.8 + Math.abs(Math.cos(t * 11.4)) * 4.2
    : 1.5;

  const blinkPhase = ((frame + (persona === "marcus" ? 45 : persona === "elena" ? 90 : 0)) % 186) / 186;
  const eyeScaleY = blinkPhase > 0.94 && blinkPhase < 0.985 ? 0.12 : 1;
  const breathY = Math.sin(t * 2.5 + (persona === "elena" ? 1.2 : 0)) * 2.0;
  const ringPulse = speaking ? 0.5 + 0.5 * Math.sin(t * 10.5) : 0;

  const palette =
    persona === "marcus"
      ? {
          bg: "linear-gradient(180deg, #FDF6F4 0%, #F9ECE8 100%)",
          ring: "rgba(200, 116, 98, 0.45)",
          dot: "#C87462",
          shirt: "#3B3752",
          accent: "#C87462",
          hair: "#2F2638",
          skinTop: "#FBE0C8",
          skinBot: "#EFC19C",
        }
      : persona === "elena"
        ? {
            bg: "linear-gradient(180deg, #F3FBF7 0%, #E7F6EE 100%)",
            ring: "rgba(42, 140, 95, 0.45)",
            dot: "#2A8C5F",
            shirt: "#4B3F72",
            accent: "#45C98E",
            hair: "#3C2A3E",
            skinTop: "#FDE7D4",
            skinBot: "#F5CBB0",
          }
        : {
            bg: "linear-gradient(180deg, #F7F4FF 0%, #EFEAFE 100%)",
            ring: "rgba(139, 115, 221, 0.5)",
            dot: "#8B73DD",
            shirt: "#FFFFFF",
            accent: "#7C64D1",
            hair: "#352A44",
            skinTop: "#FDE3CC",
            skinBot: "#F4C9A4",
          };

  return (
    <div
      className="relative flex w-full items-center justify-center overflow-hidden rounded-xl border border-[#EBE7F5]"
      style={{ height, background: palette.bg }}
    >
      {/* Speaking / Listening RMS Halo */}
      {(speaking || listening) && (
        <>
          <div
            style={{
              position: "absolute",
              width: 128,
              height: 128,
              borderRadius: "50%",
              border: `2px solid ${palette.ring}`,
              transform: `scale(${0.92 + ringPulse * 0.22})`,
              opacity: 0.35 + ringPulse * 0.45,
            }}
          />
          <div
            style={{
              position: "absolute",
              width: 162,
              height: 162,
              borderRadius: "50%",
              border: `1.5px solid ${palette.ring}`,
              transform: `scale(${0.95 + ringPulse * 0.16})`,
              opacity: 0.18 + ringPulse * 0.28,
            }}
          />
        </>
      )}

      <svg viewBox="0 0 220 180" width="210" height="170" style={{ position: "relative" }}>
        {/* Background subtle architectural lines */}
        {persona === "leo" && (
          <>
            <path d="M24 172 V54 A36 36 0 0 1 96 54 V172 Z" fill="#FFFFFF" opacity="0.65" stroke="#E5DEF2" strokeWidth="1.5" />
            <rect x="148" y="68" width="52" height="5" rx="2.5" fill="#DFD7F0" />
            <rect x="158" y="54" width="12" height="14" rx="3" fill="#B8A9F8" />
            <rect x="176" y="57" width="10" height="11" rx="2" fill="#7ADBB0" />
          </>
        )}
        {persona === "marcus" && (
          <>
            <rect x="20" y="34" width="60" height="84" rx="10" fill="#FFFFFF" opacity="0.55" stroke="#EED8D2" strokeWidth="1.5" />
            <line x1="32" y1="54" x2="68" y2="54" stroke="#E8C6BD" strokeWidth="3" strokeLinecap="round" />
            <line x1="32" y1="68" x2="60" y2="68" stroke="#E8C6BD" strokeWidth="3" strokeLinecap="round" />
            <circle cx="176" cy="56" r="22" fill="#F2CFC6" opacity="0.35" />
          </>
        )}
        {persona === "elena" && (
          <>
            <rect x="142" y="32" width="56" height="82" rx="10" fill="#FFFFFF" opacity="0.6" stroke="#C9E9D8" strokeWidth="1.5" />
            <circle cx="48" cy="58" r="24" fill="#B7EAD0" opacity="0.4" />
          </>
        )}

        <g transform={`translate(0, ${breathY})`}>
          {/* Back Hair for Elena */}
          {persona === "elena" && (
            <path
              d="M66 84 C64 42 84 26 110 26 C136 26 156 42 154 84 L158 134 C144 140 76 140 62 134 Z"
              fill={palette.hair}
              stroke="#261D2C"
              strokeWidth="2.2"
            />
          )}

          {/* Shoulders & Outfit */}
          <path
            d="M58 180 C60 142 78 130 110 130 C142 130 160 142 162 180 Z"
            fill={palette.shirt}
            stroke="#35304E"
            strokeWidth="2.4"
          />

          {/* Persona-specific Clothing Detail */}
          {persona === "leo" && (
            <>
              <path d="M80 133 H140 L146 180 H74 Z" fill="#8B73DD" stroke="#35304E" strokeWidth="2.2" />
              <line x1="88" y1="133" x2="88" y2="152" stroke="#EDE8FF" strokeWidth="2.2" />
              <line x1="132" y1="133" x2="132" y2="152" stroke="#EDE8FF" strokeWidth="2.2" />
              <rect x="96" y="154" width="28" height="16" rx="4" fill="#FFFFFF" opacity="0.22" />
            </>
          )}
          {persona === "marcus" && (
            <>
              <path d="M96 130 L110 162 L124 130 Z" fill="#FFFFFF" />
              <path d="M107 136 L110 166 L113 136 Z" fill={palette.accent} />
            </>
          )}
          {persona === "elena" && (
            <>
              <path d="M92 131 L110 160 L128 131 Z" fill="#FFFFFF" />
              <circle cx="132" cy="148" r="5" fill={palette.accent} />
            </>
          )}

          {/* Neck */}
          <rect x="99" y="114" width="22" height="20" rx="8" fill={palette.skinBot} />

          {/* Ears */}
          <ellipse cx="75" cy="84" rx="6" ry="9" fill={palette.skinBot} stroke="#35304E" strokeWidth="2" />
          <ellipse cx="145" cy="84" rx="6" ry="9" fill={palette.skinBot} stroke="#35304E" strokeWidth="2" />

          {/* Face */}
          <rect
            x="78"
            y="45"
            width="64"
            height="76"
            rx="30"
            fill={palette.skinTop}
            stroke="#35304E"
            strokeWidth="2.4"
          />

          {/* Hair Front */}
          {persona === "elena" ? (
            <path
              d="M75 74 C76 42 92 31 110 31 C128 31 144 42 145 74 C135 55 123 50 110 52 C96 50 84 56 75 74 Z"
              fill={palette.hair}
              stroke="#261D2C"
              strokeWidth="2"
            />
          ) : persona === "marcus" ? (
            <path
              d="M76 72 C75 40 94 28 114 29 C136 30 147 45 144 72 C136 53 122 48 106 50 C92 52 82 58 76 72 Z"
              fill={palette.hair}
              stroke="#261D2C"
              strokeWidth="2"
            />
          ) : (
            <path
              d="M76 74 C74 44 92 31 112 31 C134 31 146 46 144 74 C139 58 128 52 114 53 C98 54 84 60 76 74 Z"
              fill={palette.hair}
              stroke="#261D2C"
              strokeWidth="2"
            />
          )}

          {/* Eyebrows */}
          <path
            d={persona === "marcus" ? "M89 70 L103 73" : "M90 71 Q97 67 103 70"}
            stroke="#35304E"
            strokeWidth="2.4"
            fill="none"
            strokeLinecap="round"
          />
          <path
            d={persona === "marcus" ? "M117 73 L131 70" : "M117 70 Q123 67 130 71"}
            stroke="#35304E"
            strokeWidth="2.4"
            fill="none"
            strokeLinecap="round"
          />

          {/* Eyes */}
          <g transform={`translate(97, 82) scale(1, ${eyeScaleY})`}>
            <circle cx="0" cy="0" r="4.1" fill="#2A243F" />
            <circle cx="1.3" cy="-1.3" r="1.4" fill="#FFFFFF" />
          </g>
          <g transform={`translate(123, 82) scale(1, ${eyeScaleY})`}>
            <circle cx="0" cy="0" r="4.1" fill="#2A243F" />
            <circle cx="1.3" cy="-1.3" r="1.4" fill="#FFFFFF" />
          </g>

          {/* Glasses for Marcus */}
          {persona === "marcus" && (
            <g stroke="#35304E" strokeWidth="2.1" fill="rgba(255,255,255,0.22)">
              <rect x="86" y="75" width="21" height="14" rx="4" />
              <rect x="113" y="75" width="21" height="14" rx="4" />
              <line x1="107" y1="82" x2="113" y2="82" />
            </g>
          )}

          {/* Soft Blush */}
          <ellipse cx="88" cy="92" rx="5.2" ry="2.6" fill="rgba(244, 114, 182, 0.25)" />
          <ellipse cx="132" cy="92" rx="5.2" ry="2.6" fill="rgba(244, 114, 182, 0.25)" />

          {/* Nose */}
          <path d="M110 83 L108 92 Q110 94 113 92" stroke="#C68E68" strokeWidth="1.8" fill="none" strokeLinecap="round" />

          {/* Animated Lip-Sync Mouth */}
          {speaking ? (
            <ellipse
              cx="110"
              cy="104"
              rx={8.2}
              ry={Math.min(9.5, lipOpen * 0.62)}
              fill="#B84A63"
              stroke="#35304E"
              strokeWidth="2"
            />
          ) : (
            <path
              d="M101 102 Q110 109 119 102"
              stroke="#35304E"
              strokeWidth="2.3"
              fill="none"
              strokeLinecap="round"
            />
          )}
        </g>
      </svg>

      {/* Live RMS Lip-sync Pill */}
      <div className="absolute bottom-2 right-2 flex items-center gap-1.5 rounded-full border border-[#EBE7F5] bg-white/90 px-2.5 py-0.5 shadow-sm">
        <span
          className="h-1.5 w-1.5 rounded-full"
          style={{
            backgroundColor: speaking ? palette.dot : listening ? "#8B73DD" : "#45C98E",
          }}
        />
        <span className="font-mono text-[10px] font-semibold text-[#5A5572]">
          {speaking ? "LIP-SYNC" : listening ? "LISTENING" : "READY"}
        </span>
      </div>
    </div>
  );
};
