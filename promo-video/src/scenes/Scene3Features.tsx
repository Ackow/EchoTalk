import React from "react";
import {
  AbsoluteFill,
  Easing,
  Img,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import {
  AudioWaveform,
  BookOpen,
  Bot,
  Briefcase,
  Check,
  Compass,
  Download,
  Eye,
  FileText,
  Heart,
  MessageCircle,
  Plus,
  RotateCcw,
  Search,
  ShieldCheck,
  Star,
  Target,
  Upload,
  Zap,
} from "lucide-react";
import { AmbientBackdrop } from "../components/AmbientBackdrop";
import { SfxCue } from "../components/SfxCue";

const RAG_KEY_FRAMES = [64, 72, 80, 88, 96, 104, 112, 120];

const SCENE_CARDS = [
  {
    title: "火车站购票 (Train Ticket)",
    category: "日常沟通",
    mode: "对话",
    isInterview: false,
    desc: "在车站人工售票窗口查询车次、比较席别与票价，选定座位并完成购票付款。",
    cover: "covers/train_ticket.png",
    level: "简单",
    levelBg: "#EAF7F0",
    levelText: "#2A8C5F",
    meta: "3 个目标 · 1 份资料",
    tags: ["出行交通", "购票", "日常口语"],
  },
  {
    title: "软件工程师面试 (Job Interview)",
    category: "求职训练",
    mode: "面试",
    isInterview: true,
    desc: "模拟外企软件工程师英文技术面试，考察专业术语、沟通能力与逻辑表达。",
    cover: "covers/tech_interview.png",
    level: "专家",
    levelBg: "#FDECE8",
    levelText: "#B84A39",
    meta: "1 份资料 · AI 底牌",
    tags: ["技术面试", "资料驱动", "多阶段"],
  },
  {
    title: "繁忙咖啡厅点餐 (Cafe Ordering)",
    category: "日常沟通",
    mode: "对话",
    isInterview: false,
    desc: "在纽约街头咖啡馆点一份早餐与咖啡，练习日常口语、定制化订单与结账表达。",
    cover: "covers/cafe_ordering.png",
    level: "简单",
    levelBg: "#EAF7F0",
    levelText: "#2A8C5F",
    meta: "3 个目标 · 2 份资料",
    tags: ["礼貌表达", "订单工具", "日常沟通"],
  },
  {
    title: "航班改签 (Airport Rebooking)",
    category: "日常沟通",
    mode: "对话",
    isInterview: false,
    desc: "航班临时取消，在机场柜台向地勤说明情况、比较改签方案并确认新行程。",
    cover: "covers/airport_rebooking.png",
    level: "普通",
    levelBg: "#EEF4FF",
    levelText: "#3B67C9",
    meta: "3 个目标 · 1 份资料",
    tags: ["应变沟通", "差旅", "说明问题"],
  },
];

// Authentic LightRAG Force-Directed Entity Nodes matching Knowledge.vue (lines 279-289):
// Translucent colored aura circle + solid center dot + crisp label positioned cleanly BELOW circle.
const LR_NODES = [
  { id: "n0", label: "System Design", type: "概念", color: "#8B73DD", x: 142, y: 84, r: 16, degree: 5 },
  { id: "n1", label: "Sharding", type: "架构", color: "#2A8C5F", x: 54, y: 44, r: 12, degree: 3 },
  { id: "n2", label: "Latency SLA", type: "指标", color: "#D97706", x: 232, y: 46, r: 12, degree: 3 },
  { id: "n3", label: "Cache Tier", type: "架构", color: "#2A8C5F", x: 46, y: 124, r: 11, degree: 2 },
  { id: "n4", label: "Trade-offs", type: "规则", color: "#C87462", x: 230, y: 128, r: 13, degree: 4 },
  { id: "n5", label: "Failover", type: "架构", color: "#3B67C9", x: 142, y: 156, r: 11, degree: 2 },
];

const LR_EDGES: Array<[number, number]> = [
  [0, 1],
  [0, 2],
  [0, 3],
  [0, 4],
  [0, 5],
  [1, 3],
  [2, 4],
  [3, 5],
  [4, 5],
];

const LR_LEGEND = [
  { label: "概念", color: "#8B73DD" },
  { label: "架构", color: "#2A8C5F" },
  { label: "指标", color: "#D97706" },
  { label: "规则", color: "#C87462" },
];

const RAG_QUERY = "scalability trade-offs";

export const Scene3Features: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;

  // Staggered Springs
  const headerSpring = spring({
    frame,
    fps,
    config: { damping: 18, stiffness: 135, mass: 0.9 },
  });
  const card1Spring = spring({
    frame: frame - 8,
    fps,
    config: { damping: 16, stiffness: 128, mass: 0.9 },
  });
  const card2Spring = spring({
    frame: frame - 18,
    fps,
    config: { damping: 16, stiffness: 128, mass: 0.9 },
  });
  const card3Spring = spring({
    frame: frame - 28,
    fps,
    config: { damping: 16, stiffness: 128, mass: 0.9 },
  });

  // Sequential Spotlight Focus Waves
  const focus1 =
    interpolate(frame, [24, 48], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.out(Easing.cubic),
    }) *
    interpolate(frame, [116, 142], [1, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.inOut(Easing.cubic),
    });

  const focus2 =
    interpolate(frame, [110, 136], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.out(Easing.cubic),
    }) *
    interpolate(frame, [212, 238], [1, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.inOut(Easing.cubic),
    });

  const focus3 =
    interpolate(frame, [196, 222], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.out(Easing.cubic),
    }) *
    interpolate(frame, [278, 304], [1, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.inOut(Easing.cubic),
    });

  // Highlighted scene card cycles cleanly
  const highlightedSceneIdx = Math.floor(frame / 44) % 4;

  // Live RAG Search Typing (starts early enough so it looks active & crisp immediately)
  const ragTypePct = interpolate(frame, [62, 132], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.quad),
  });
  const typedRagQuery = RAG_QUERY.slice(
    0,
    Math.round(ragTypePct * RAG_QUERY.length)
  );
  const ragHighlightSpring = spring({
    frame: frame - 118,
    fps,
    config: { damping: 16, stiffness: 155, mass: 0.85 },
  });

  // Selected entity node inside LightRAG graph cycles between System Design (0) and Trade-offs (4)
  const selectedLrIdx = frame >= 168 ? 4 : 0;
  const selectedLrNode = LR_NODES[selectedLrIdx];

  // SM-2 retention curve draws smoothly
  const curveDraw = interpolate(frame, [140, 265], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  // Smooth convergence exit into Scene 4
  const exitConverge = interpolate(frame, [276, 310], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.in(Easing.cubic),
  });

  return (
    <AbsoluteFill className="font-sans text-[#35304E] select-none">
      {/* Frame-Synced Tactile Sound Design: Scenes + Dual-Engine RAG + SM-2 */}
      <SfxCue sfx="whoosh" from={0} volume={0.30} />
      <SfxCue sfx="pop" from={8} volume={0.18} playbackRate={0.94} />
      <SfxCue sfx="pop" from={18} volume={0.18} playbackRate={1.04} />
      <SfxCue sfx="pop" from={28} volume={0.18} playbackRate={1.14} />
      {RAG_KEY_FRAMES.map((kf, idx) => (
        <SfxCue
          key={kf}
          sfx="key-click"
          from={kf}
          volume={0.18}
          playbackRate={0.96 + (idx % 3) * 0.05}
        />
      ))}
      <SfxCue sfx="pop" from={122} volume={0.22} playbackRate={1.2} />
      <SfxCue sfx="pop" from={168} volume={0.18} playbackRate={1.15} />
      <SfxCue sfx="whoosh" from={208} volume={0.18} playbackRate={1.3} />

      <AmbientBackdrop
        intensity={1.08}
        focusX={focus1 * -0.35 + focus2 * 0.35 + focus3 * 0.3}
        focusY={focus2 * -0.25 + focus3 * 0.32}
      />

      <AbsoluteFill
        className="flex flex-col px-[68px] py-[46px]"
        style={{
          transform: `scale(${1 - exitConverge * 0.05})`,
          opacity: 1 - exitConverge * 0.65,
        }}
      >
        {/* Top Section Header (100% EchoTalk 2.0 Light Tactile Style) */}
        <header
          className="mb-5 flex items-end justify-between"
          style={{
            opacity: headerSpring,
            transform: `translateY(${interpolate(headerSpring, [0, 1], [20, 0])}px)`,
          }}
        >
          <div>
            <div className="mb-2 inline-flex items-center gap-2 rounded-full border-[1.5px] border-[#E6E0F5] border-b-[3px] border-b-[#DDD5F1] bg-white px-3.5 py-1 shadow-sm">
              <Zap className="h-3.5 w-3.5 text-[#2A8C5F]" />
              <span className="font-mono text-[12px] font-bold tracking-[0.15em] text-[#6046B4] uppercase">
                Full-Stack Ecosystem · Scenes · RAG · Speech
              </span>
            </div>
            <h2
              className="text-[44px] font-extrabold tracking-[-0.03em] leading-tight"
              style={{
                background:
                  "linear-gradient(135deg, #2C2642 15%, #6951B8 85%)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
              }}
            >
              场景探索、双引擎 RAG 与全链路学习闭环
            </h2>
          </div>

          <div className="flex items-center gap-2.5 pb-1">
            {[
              { label: "01 场景探索", active: focus1 > 0.2 },
              { label: "02 双引擎 RAG 知识工作区", active: focus2 > 0.2 },
              { label: "03 语音流水线 × SM-2", active: focus3 > 0.2 },
            ].map((pill) => (
              <div
                key={pill.label}
                className={`rounded-full border-[1.5px] border-b-[3px] px-4 py-1.5 font-mono text-[12.5px] font-bold ${
                  pill.active
                    ? "border-[#8067D1] border-b-[#6951B8] bg-[#8B73DD] text-white shadow-md"
                    : "border-[#EBE7F5] border-b-[#E3DCF2] bg-white text-[#6E6886]"
                }`}
              >
                {pill.label}
              </div>
            ))}
          </div>
        </header>

        {/* BENTO GRID — 100% Unified Tactile Purple-White Cards */}
        <div className="grid flex-1 grid-cols-12 grid-rows-12 gap-5">
          {/* ==============================================================
              CARD 1 (Left Hero, 5 cols x 12 rows):
              Faithful Scenes.vue Replica matching docs/screenshots/web-scenes.jpg
             ============================================================== */}
          <div
            className="relative col-span-5 row-span-12 flex flex-col overflow-hidden rounded-[22px] border-[1.5px] border-b-[5px] bg-[#FAF9FD] p-4"
            style={{
              opacity: card1Spring,
              transform: `translateY(${interpolate(card1Spring, [0, 1], [40, 0])}px) scale(${1 + focus1 * 0.014})`,
              borderColor: focus1 > 0.2 ? "#8B73DD" : "#E5DEF4",
              borderBottomColor: focus1 > 0.2 ? "#6951B8" : "#D8CEF0",
              boxShadow:
                focus1 > 0.2
                  ? "0 24px 56px rgba(139, 115, 221, 0.22)"
                  : "0 14px 36px rgba(105, 81, 184, 0.09)",
            }}
          >
            {/* Scenes.vue Top Row: Mode Tabs + Scope Pills + Import/Create CTA */}
            <div className="mb-2.5 flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <div className="inline-flex items-center gap-0.5 rounded-xl border border-[#E6E0F5] bg-white p-0.5 text-[11px] font-bold">
                  <span className="inline-flex items-center gap-1 rounded-lg bg-[#EEE9FF] px-2 py-1 text-[#6046B4]">
                    <Compass className="h-3 w-3" />
                    对话场景 4
                  </span>
                  <span className="px-2 py-1 text-[#837F96]">多角色 4</span>
                </div>
                <div className="inline-flex items-center gap-1 rounded-xl border border-[#EBE7F5] bg-[#F4F0FF]/70 px-2 py-1 text-[10.5px] font-bold">
                  <span className="rounded-md bg-white px-1.5 py-0.5 text-[#6046B4] shadow-sm">
                    全部 4
                  </span>
                  <span className="px-1 text-[#837F96]">内置 4</span>
                  <span className="px-1 text-[#837F96]">社区</span>
                </div>
              </div>

              <div className="flex items-center gap-1.5">
                <span className="inline-flex items-center gap-1 rounded-xl border-[1.5px] border-[#E6E1F2] border-b-[2.5px] border-b-[#DDD6EC] bg-white px-2.5 py-1 text-[10.5px] font-bold text-[#5A5572]">
                  <Download className="h-3 w-3" />
                  导入包
                </span>
                <span className="inline-flex items-center gap-1 rounded-xl border-[1.5px] border-[#8067D1] border-b-[2.5px] border-b-[#6951B8] bg-[#8B73DD] px-2.5 py-1 text-[10.5px] font-bold text-white">
                  <Plus className="h-3 w-3" />
                  新建场景
                </span>
              </div>
            </div>

            {/* Category Filter Bar */}
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-[10.5px] font-bold">
                {["全部", "日常沟通", "职场沟通", "求职训练", "学术场景"].map(
                  (cat, ci) => (
                    <span
                      key={cat}
                      className={`rounded-full px-2.5 py-0.5 ${
                        ci === 0
                          ? "border border-[#8B73DD] bg-[#EEE9FF] text-[#6046B4]"
                          : "border border-[#EBE7F5] bg-white text-[#625E76]"
                      }`}
                    >
                      {cat}
                    </span>
                  )
                )}
              </div>
              <span className="font-mono text-[10px] font-semibold text-[#837F96]">
                ScenePackage v2
              </span>
            </div>

            {/* 2x2 Grid of REAL Full-Detail Scene Cards (No Empty White Space!) */}
            <div className="grid flex-1 grid-cols-2 grid-rows-2 gap-3">
              {SCENE_CARDS.map((scene, idx) => {
                const isSelected = idx === highlightedSceneIdx && focus1 > 0.15;
                return (
                  <div
                    key={scene.title}
                    className="flex flex-col overflow-hidden rounded-[16px] border-[1.5px] border-b-[4px] bg-white"
                    style={{
                      borderColor: isSelected ? "#8B73DD" : "#EBE7F5",
                      borderBottomColor: isSelected ? "#6951B8" : "#E3DCF2",
                      transform: isSelected ? "translateY(-3px)" : "translateY(0px)",
                      boxShadow: isSelected
                        ? "0 12px 24px rgba(139, 115, 221, 0.22)"
                        : "none",
                    }}
                  >
                    {/* Cover Illustration */}
                    <div className="relative h-[126px] w-full flex-shrink-0 overflow-hidden bg-[#EDE8FA]">
                      <Img
                        src={staticFile(scene.cover)}
                        style={{
                          width: "100%",
                          height: "100%",
                          objectFit: "cover",
                          transform: isSelected ? "scale(1.05)" : "scale(1)",
                        }}
                      />
                      <div
                        className="absolute inset-0"
                        style={{
                          background:
                            "linear-gradient(180deg, rgba(25,20,45,0.06) 28%, rgba(25,20,45,0.78) 100%)",
                        }}
                      />
                      <span className="absolute top-2 left-2 rounded-md bg-black/45 px-2 py-0.5 text-[10px] font-bold text-white backdrop-blur-sm">
                        {scene.category}
                      </span>
                      <div className="absolute bottom-2 left-2.5 right-2.5 truncate text-[13px] font-extrabold text-white drop-shadow">
                        {scene.title}
                      </div>
                    </div>

                    {/* Full Authentic Card Body (exact match to web-scenes.jpg) */}
                    <div className="flex flex-1 flex-col justify-between p-3">
                      <div>
                        {/* Mode + Built-in badges */}
                        <div className="flex items-center gap-1.5">
                          <span className="inline-flex items-center gap-1 rounded-full bg-[#F4F0FF] px-2 py-0.5 text-[10.5px] font-bold text-[#6046B4]">
                            {scene.isInterview ? (
                              <Briefcase className="h-2.5 w-2.5" />
                            ) : (
                              <MessageCircle className="h-2.5 w-2.5" />
                            )}
                            {scene.mode}
                          </span>
                          <span className="inline-flex items-center gap-0.5 rounded-full bg-[#EAF7F0] px-2 py-0.5 text-[10.5px] font-bold text-[#2A8C5F]">
                            <Check className="h-2.5 w-2.5" />
                            内置
                          </span>
                        </div>

                        {/* Authentic 2-Line Description */}
                        <p className="mt-2 line-clamp-2 text-[11.5px] leading-[1.45] text-[#5A5572]">
                          {scene.desc}
                        </p>

                        {/* Tag Pills */}
                        <div className="mt-2 flex flex-wrap gap-1">
                          {scene.tags.map((tg) => (
                            <span
                              key={tg}
                              className="rounded-md border border-[#EFECF7] bg-[#FAF9FD] px-1.5 py-0.5 text-[10px] font-semibold text-[#6E6886]"
                            >
                              {tg}
                            </span>
                          ))}
                        </div>
                      </div>

                      {/* Author + Difficulty + Footer Counts */}
                      <div className="mt-2 flex flex-col gap-1.5">
                        <div className="flex items-center justify-between">
                          <span className="inline-flex items-center gap-1.5 text-[10.5px] font-bold text-[#4B4663]">
                            <Img
                              src={staticFile("app-icon.png")}
                              style={{ width: 15, height: 15, objectFit: "contain" }}
                            />
                            EchoTalk 官方
                          </span>
                          <span
                            className="rounded-md px-2 py-0.5 text-[10px] font-bold"
                            style={{
                              backgroundColor: scene.levelBg,
                              color: scene.levelText,
                            }}
                          >
                            {scene.level}
                          </span>
                        </div>

                        <div className="flex items-center justify-between border-t border-[#F2EFFA] pt-1.5 text-[10px] font-medium text-[#837F96]">
                          <span className="inline-flex items-center gap-1">
                            <Target className="h-3 w-3 text-[#8B73DD]" />
                            {scene.meta}
                          </span>
                          <span className="inline-flex items-center gap-2">
                            <span className="inline-flex items-center gap-0.5">
                              <Heart className="h-2.5 w-2.5" /> 18
                            </span>
                            <span className="inline-flex items-center gap-0.5">
                              <Star className="h-2.5 w-2.5" /> 12
                            </span>
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* ==============================================================
              CARD 2 (Top Right, 7 cols x 7 rows):
              Faithful Knowledge.vue Replica (Hybrid RAG + Authentic LightRAG Graph)
             ============================================================== */}
          <div
            className="relative col-span-7 row-span-7 flex flex-col overflow-hidden rounded-[22px] border-[1.5px] border-b-[5px] bg-[#FAF9FD] p-4"
            style={{
              opacity: card2Spring,
              transform: `translateY(${interpolate(card2Spring, [0, 1], [38, 0])}px) scale(${1 + focus2 * 0.014})`,
              borderColor: focus2 > 0.2 ? "#45C98E" : "#E5DEF4",
              borderBottomColor: focus2 > 0.2 ? "#2A8C5F" : "#D8CEF0",
              boxShadow:
                focus2 > 0.2
                  ? "0 24px 56px rgba(69, 201, 142, 0.2)"
                  : "0 14px 36px rgba(105, 81, 184, 0.09)",
            }}
          >
            {/* Knowledge.vue Row 1: Scope AppTabs + Upload CTA */}
            <div className="mb-2.5 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="inline-flex items-center gap-1 rounded-xl border border-[#E6E0F5] bg-white p-0.5 text-[11.5px] font-bold">
                  <span className="inline-flex items-center gap-1.5 rounded-lg bg-[#EEE9FF] px-3 py-1 text-[#6046B4]">
                    <BookOpen className="h-3.5 w-3.5" />
                    场景资料 <em className="not-italic font-mono text-[10.5px]">4</em>
                  </span>
                  <span className="px-3 py-1 text-[#837F96]">
                    个人资料 <em className="not-italic font-mono text-[10.5px]">2</em>
                  </span>
                </div>
                <span className="rounded-full bg-[#EAF7F0] px-2.5 py-0.5 font-mono text-[11px] font-bold text-[#2A8C5F]">
                  Hybrid RRF (ngram + bge-m3 1024d)
                </span>
              </div>

              <span className="inline-flex items-center gap-1.5 rounded-xl border-[1.5px] border-[#8067D1] border-b-[3px] border-b-[#6951B8] bg-[#8B73DD] px-3 py-1 text-[11.5px] font-bold text-white">
                <Upload className="h-3.5 w-3.5" />
                上传资料
              </span>
            </div>

            {/* Knowledge.vue Row 2: Scene Selector + Search Engine + Search Input */}
            <div className="mb-3 flex items-center justify-between gap-2.5">
              <div className="inline-flex items-center gap-1.5 rounded-xl border border-[#EBE7F5] bg-white px-3 py-1.5 text-[11.5px]">
                <span className="text-[#837F96] font-semibold">场景</span>
                <span className="font-bold text-[#35304E]">软件工程师面试</span>
              </div>

              <div className="flex flex-1 items-center gap-2">
                <div className="inline-flex items-center gap-1.5 rounded-xl border border-[#EBE7F5] bg-white px-2.5 py-1.5 text-[11.5px]">
                  <span className="text-[#837F96] font-semibold">检索</span>
                  <span className="font-bold text-[#6046B4]">混合检索</span>
                </div>
                <div className="flex flex-1 items-center gap-2 rounded-xl border-[1.5px] border-[#8B73DD] bg-white px-3 py-1.5 shadow-sm">
                  <Search className="h-3.5 w-3.5 text-[#8B73DD]" />
                  <span className="flex-1 font-mono text-[12px] font-semibold text-[#35304E]">
                    {typedRagQuery || "搜索资料内容，回车检索"}
                    {ragTypePct > 0 && ragTypePct < 1 && (
                      <span className="ml-0.5 inline-block h-3.5 w-1 bg-[#8B73DD] align-middle" />
                    )}
                  </span>
                  <span className="rounded-md bg-[#F4F0FF] px-2 py-0.5 text-[10px] font-bold text-[#6046B4]">
                    关键词 + 向量融合
                  </span>
                </div>
              </div>
            </div>

            {/* Knowledge.vue 2-Column Workspace: Left Docs & RRF Result | Right Authentic LightRAG Graph */}
            <div className="grid flex-1 grid-cols-12 gap-3.5 overflow-hidden">
              {/* Left 7 cols: Real Document Rows + Crisp RRF Match */}
              <div className="col-span-7 flex flex-col gap-2.5">
                {/* Document Card with [ai] / [user] Section Visibility */}
                <div className="flex flex-col gap-2 rounded-[16px] border-[1.5px] border-[#EBE7F5] border-b-[3px] border-b-[#E3DCF2] bg-white p-3">
                  {[
                    {
                      name: "interview_rubric.md",
                      type: "MD",
                      chunks: "18 块",
                      sections: "3 个分节 · 标题行 [ai] 标注",
                      vis: "ai",
                    },
                    {
                      name: "candidate_brief.pdf",
                      type: "PDF",
                      chunks: "12 块",
                      sections: "2 个分节 · 参考板对用户可见",
                      vis: "user",
                    },
                  ].map((doc) => (
                    <div
                      key={doc.name}
                      className="flex items-center justify-between rounded-xl border border-[#EFECF7] bg-[#FAF9FD] px-3 py-2"
                    >
                      <div className="flex items-center gap-2.5">
                        <span className="flex h-8 w-9 items-center justify-center rounded-lg bg-[#EEE9FF] font-mono text-[10.5px] font-extrabold text-[#6046B4]">
                          {doc.type}
                        </span>
                        <div>
                          <div className="flex items-center gap-1.5">
                            <span className="text-[12.5px] font-bold text-[#35304E]">
                              {doc.name}
                            </span>
                            <span className="inline-flex items-center gap-0.5 rounded-full bg-[#EAF7F0] px-2 py-0.5 text-[10px] font-bold text-[#2A8C5F]">
                              <Check className="h-2.5 w-2.5" />
                              {doc.chunks}
                            </span>
                          </div>
                          <div className="text-[10.5px] text-[#837F96]">
                            {doc.sections}
                          </div>
                        </div>
                      </div>
                      <span
                        className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[10.5px] font-bold ${
                          doc.vis === "ai"
                            ? "bg-[#FFF3EA] text-[#C46A24]"
                            : "bg-[#EEE9FF] text-[#6046B4]"
                        }`}
                      >
                        {doc.vis === "ai" ? (
                          <>
                            <Bot className="h-3 w-3" /> 仅 AI
                          </>
                        ) : (
                          <>
                            <Eye className="h-3 w-3" /> 用户可见
                          </>
                        )}
                      </span>
                    </div>
                  ))}
                </div>

                {/* High-Contrast Hybrid RRF Retrieval Snippet (matches Knowledge.vue .search-results) */}
                <div
                  className="flex flex-1 flex-col justify-between rounded-[16px] border-[1.5px] border-[#BEE8D3] border-b-[3px] border-b-[#98D9B8] bg-white p-3"
                  style={{
                    transform: `scale(${interpolate(ragHighlightSpring, [0, 0.5, 1], [0.97, 1.01, 1])})`,
                  }}
                >
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="inline-flex items-center gap-1.5 font-bold text-[#35304E]">
                      <FileText className="h-3.5 w-3.5 text-[#8B73DD]" />
                      interview_rubric.md · System Design
                    </span>
                    <div className="flex items-center gap-1.5">
                      <span className="rounded-full bg-[#FFF3EA] px-2 py-0.5 text-[10px] font-bold text-[#C46A24]">
                        仅 AI
                      </span>
                      <span className="rounded-md bg-[#EAF7F0] px-1.5 py-0.5 font-mono text-[10px] font-bold text-[#2A8C5F]">
                        RRF #1 · 0.94
                      </span>
                    </div>
                  </div>
                  <p className="mt-1.5 text-[12px] leading-[1.5] text-[#4B4663]">
                    Probe{" "}
                    <mark className="rounded bg-[#EEE9FF] px-1 font-bold text-[#6046B4]">
                      scalability trade-offs
                    </mark>{" "}
                    across sharding, cache invalidation & failover SLAs — injected into AI prompt only, hidden from learner UI.
                  </p>
                </div>
              </div>

              {/* Right 5 cols: REAL Knowledge.vue LightRAG Entity Graph Panel */}
              <div className="col-span-5 flex flex-col justify-between overflow-hidden rounded-[16px] border-[1.5px] border-[#EBE7F5] border-b-[3px] border-b-[#E3DCF2] bg-white p-3">
                {/* Side Head matching Knowledge.vue lines 231-246 */}
                <div className="flex items-center justify-between">
                  <h4 className="text-[13px] font-extrabold text-[#35304E]">
                    实体关系
                  </h4>
                  <div className="flex items-center gap-1.5">
                    <span className="rounded-lg border border-[#EBE7F5] bg-[#FAF9FD] px-2 py-0.5 text-[10px] font-bold text-[#5A5572]">
                      后台构建
                    </span>
                    <span className="rounded-full bg-[#EEE9FF] px-2 py-0.5 font-mono text-[10px] font-bold text-[#6046B4]">
                      LightRAG
                    </span>
                  </div>
                </div>

                {/* Authentic Force-Directed Graph Canvas (Labels cleanly BELOW nodes!) */}
                <div className="relative my-1.5 flex-1 rounded-xl border border-[#F1EEF8] bg-[#FCFBFD]">
                  <svg viewBox="0 0 284 186" className="h-[168px] w-full">
                    {/* Curved Edges */}
                    {LR_EDGES.map(([a, b], idx) => {
                      const na = LR_NODES[a];
                      const nb = LR_NODES[b];
                      const isHot = a === selectedLrIdx || b === selectedLrIdx;
                      const mx = (na.x + nb.x) / 2;
                      const my = (na.y + nb.y) / 2 - 8;
                      return (
                        <path
                          key={idx}
                          d={`M ${na.x} ${na.y} Q ${mx} ${my} ${nb.x} ${nb.y}`}
                          fill="none"
                          stroke={isHot ? "#8B73DD" : "#D6CEE8"}
                          strokeWidth={isHot ? 1.8 : 1.1}
                          strokeOpacity={isHot ? 0.8 : 0.65}
                        />
                      );
                    })}

                    {/* Authentic LightRAG Nodes: translucent aura + solid dot + label below */}
                    {LR_NODES.map((n, idx) => {
                      const isSel = idx === selectedLrIdx;
                      const pulse = isSel ? 1 + 0.08 * Math.sin(t * 6) : 1;
                      const dy = Math.sin(t * 2 + idx * 0.9) * 2;
                      return (
                        <g key={n.id} transform={`translate(${n.x}, ${n.y + dy})`}>
                          <circle
                            r={n.r * pulse}
                            fill={n.color}
                            fillOpacity={isSel ? 0.24 : 0.14}
                            stroke={n.color}
                            strokeWidth={isSel ? 2.1 : 1.4}
                          />
                          <circle r={3.6} fill={n.color} />
                          <text
                            x={0}
                            y={n.r + 12}
                            textAnchor="middle"
                            fill={isSel ? "#2C2642" : "#5A5572"}
                            fontSize="9.8"
                            fontWeight={isSel ? "800" : "600"}
                            fontFamily="sans-serif"
                          >
                            {n.label}
                          </text>
                        </g>
                      );
                    })}
                  </svg>

                  {/* Authentic Zoom Controls (+ / − / 重置) from Knowledge.vue lines 291-295 */}
                  <div className="absolute right-2 bottom-2 flex items-center gap-1 rounded-lg border border-[#EBE7F5] bg-white/95 px-1.5 py-0.5 text-[10px] font-bold text-[#625E76] shadow-sm">
                    <span>+</span>
                    <span className="text-[#DDD6EC]">|</span>
                    <span>−</span>
                    <span className="text-[#DDD6EC]">|</span>
                    <span>重置</span>
                  </div>
                </div>

                {/* Selected Entity Detail & Type Legend (Knowledge.vue lines 299-312) */}
                <div className="rounded-lg border border-[#EFECF7] bg-[#FAF9FD] px-2.5 py-1.5">
                  <div className="flex items-center justify-between text-[10.5px]">
                    <span className="inline-flex items-center gap-1.5 font-bold text-[#35304E]">
                      <span
                        className="h-2 w-2 rounded-full"
                        style={{ backgroundColor: selectedLrNode.color }}
                      />
                      {selectedLrNode.label}
                    </span>
                    <span className="font-mono text-[10px] text-[#837F96]">
                      {selectedLrNode.type} · {selectedLrNode.degree} 条关联
                    </span>
                  </div>
                </div>

                <div className="mt-1.5 flex items-center justify-between px-0.5 text-[10px] font-semibold text-[#6E6886]">
                  <div className="flex items-center gap-2.5">
                    {LR_LEGEND.map((item) => (
                      <span key={item.label} className="inline-flex items-center gap-1">
                        <span
                          className="h-2 w-2 rounded-full"
                          style={{ backgroundColor: item.color }}
                        />
                        {item.label}
                      </span>
                    ))}
                  </div>
                  <span className="font-mono text-[9.5px] text-[#837F96]">
                    DeepSeek-V3
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* ==============================================================
              CARD 3 (Bottom Right, 7 cols x 5 rows):
              100% Unified Tactile White Card — Speech Engine + AST + SM-2 Loop
             ============================================================== */}
          <div
            className="relative col-span-7 row-span-5 grid grid-cols-12 gap-4 overflow-hidden rounded-[22px] border-[1.5px] border-b-[5px] bg-white p-5"
            style={{
              opacity: card3Spring,
              transform: `translateY(${interpolate(card3Spring, [0, 1], [36, 0])}px) scale(${1 + focus3 * 0.014})`,
              borderColor: focus3 > 0.2 ? "#8B73DD" : "#E5DEF4",
              borderBottomColor: focus3 > 0.2 ? "#6951B8" : "#D8CEF0",
              boxShadow:
                focus3 > 0.2
                  ? "0 24px 56px rgba(139, 115, 221, 0.2)"
                  : "0 14px 36px rgba(105, 81, 184, 0.09)",
            }}
          >
            {/* Left 7 cols: Low-Latency Speech Pipeline & AST Zero-Hallucination */}
            <div className="col-span-7 flex flex-col justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#EEE9FF] text-[#6046B4]">
                  <AudioWaveform className="h-5 w-5" />
                </div>
                <div>
                  <h4 className="text-[18px] font-extrabold text-[#35304E]">
                    全双工低延迟语音 & AST 受控状态机
                  </h4>
                  <p className="text-[11.5px] font-medium text-[#837F96]">
                    浏览器零 FFmpeg 直采 · 1× audio_token 复用 · 原话证据强校验
                  </p>
                </div>
              </div>

              <div className="my-2 flex flex-col gap-2">
                {[
                  {
                    label: "主链路",
                    text: "16kHz PCM16 → Flash ASR → SSE 切句并发 TTS",
                    barColor: "rgba(139, 115, 221, 0.16)",
                    dot: "#8B73DD",
                    w: 44 + ((t * 42) % 52),
                  },
                  {
                    label: "双旁路",
                    text: "讯飞 ISE 逐词发音评分 + LLM 实时语法纠错",
                    barColor: "rgba(69, 201, 142, 0.18)",
                    dot: "#2A8C5F",
                    w: 38 + ((t * 48 + 25) % 56),
                  },
                ].map((row) => (
                  <div key={row.label} className="flex items-center gap-2.5">
                    <span className="w-[50px] font-mono text-[11px] font-bold text-[#625E76]">
                      {row.label}
                    </span>
                    <div className="relative flex h-8 flex-1 items-center overflow-hidden rounded-xl border border-[#EBE7F5] bg-[#FAF9FD] px-3">
                      <div
                        className="absolute inset-y-0 left-0"
                        style={{
                          width: `${row.w}%`,
                          backgroundColor: row.barColor,
                        }}
                      />
                      <span
                        className="relative z-10 mr-2 h-2 w-2 rounded-full"
                        style={{ backgroundColor: row.dot }}
                      />
                      <span className="relative z-10 text-[12px] font-bold text-[#35304E]">
                        {row.text}
                      </span>
                    </div>
                  </div>
                ))}
              </div>

              <div className="flex items-center gap-2 font-mono text-[11px]">
                <span className="inline-flex items-center gap-1 rounded-lg bg-[#EAF7F0] px-2.5 py-1 font-bold text-[#2A8C5F]">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  0% 状态幻觉
                </span>
                <span className="rounded-lg bg-[#EEE9FF] px-2.5 py-1 font-bold text-[#6046B4]">
                  10 项受控工具
                </span>
                <span className="rounded-lg border border-[#EBE7F5] bg-[#FAF9FD] px-2.5 py-1 font-bold text-[#625E76]">
                  乐观锁幂等提交
                </span>
              </div>
            </div>

            {/* Right 5 cols: SM-2 Spaced Repetition Light Tactile Panel */}
            <div className="col-span-5 flex flex-col justify-between rounded-2xl border border-[#EBE7F5] bg-[#FAF9FD] p-3.5">
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-1.5 font-mono text-[11.5px] font-extrabold text-[#2A8C5F]">
                  <RotateCcw className="h-3.5 w-3.5" />
                  SM-2 间隔重复
                </span>
                <span className="rounded-md bg-[#FFF3EA] px-2 py-0.5 font-mono text-[10px] font-bold text-[#C46A24]">
                  &lt; 78 分自动入卡
                </span>
              </div>

              <svg viewBox="0 0 260 88" className="my-1 h-[84px] w-full">
                <line x1="6" y1="78" x2="254" y2="78" stroke="#E6E0F5" />
                <line x1="6" y1="44" x2="254" y2="44" stroke="#EFEBF7" strokeDasharray="4 4" />
                <path
                  d="M10 20 Q42 56 68 62 L74 16 Q120 38 152 44 L158 14 Q212 24 250 22"
                  fill="none"
                  stroke="#2A8C5F"
                  strokeWidth="3"
                  strokeLinecap="round"
                  strokeDasharray="340"
                  strokeDashoffset={340 * (1 - curveDraw)}
                />
                {[
                  { x: 74, y: 16, label: "Day 1" },
                  { x: 158, y: 14, label: "Day 6" },
                  { x: 248, y: 22, label: "Day 15" },
                ].map((pt, i) => (
                  <g key={pt.label} opacity={curveDraw > 0.25 + i * 0.28 ? 1 : 0}>
                    <circle cx={pt.x} cy={pt.y} r="4.5" fill="#2A8C5F" />
                    <text x={pt.x - 12} y={74} fill="#837F96" fontSize="9.5" fontFamily="monospace" fontWeight="600">
                      {pt.label}
                    </text>
                  </g>
                ))}
              </svg>

              <div className="flex items-center justify-between font-mono text-[10.5px] font-bold">
                <span className="rounded-md border border-[#EBE7F5] bg-white px-1.5 py-0.5 text-[#837F96]">
                  Again
                </span>
                <span className="rounded-md border border-[#EBE7F5] bg-white px-1.5 py-0.5 text-[#625E76]">
                  Hard
                </span>
                <span className="rounded-md bg-[#EAF7F0] px-2 py-0.5 text-[#2A8C5F]">
                  Good · EF 2.5
                </span>
                <span className="rounded-md bg-[#EEE9FF] px-1.5 py-0.5 text-[#6046B4]">
                  Easy
                </span>
              </div>
            </div>
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
