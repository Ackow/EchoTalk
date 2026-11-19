/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        obsidian: "#09090B",
        brand: "#8B73DD",
        brandDeep: "#6951B8",
        brandSoft: "#F4F0FF",
        brandMint: "#45C98E",
        brandMintDark: "#2A8C5F",
        brandCoral: "#DF9D8F",
        brandInk: "#35304E",
      },
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          '"SF Pro Display"',
          '"PingFang SC"',
          '"Hiragino Sans GB"',
          '"Microsoft YaHei"',
          "sans-serif",
        ],
        mono: [
          '"JetBrains Mono"',
          '"SF Mono"',
          "Menlo",
          "Monaco",
          "Consolas",
          "monospace",
        ],
      },
    },
  },
  plugins: [],
};
