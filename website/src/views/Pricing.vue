<template>
  <div class="pricing-page">
    <section class="page-head">
      <span class="pill">SaaS Plans &amp; Echo Credits</span>
      <h1>清晰透明的订阅与算力体系</h1>
      <p>每日共享免费额度池覆盖常规训练，搭配签到与任务中心赚取 Echo Credit，按需升级解锁场景包导入导出与私有知识库。</p>

      <div class="billing-toggle">
        <button type="button" :class="{ active: cycle === 'monthly' }" @click="cycle = 'monthly'">按月订阅</button>
        <button type="button" :class="{ active: cycle === 'yearly' }" @click="cycle = 'yearly'">
          按年订阅 <span class="save-tag">省 20%+</span>
        </button>
      </div>
    </section>

    <!-- 三档核心套餐卡片 -->
    <section class="plans-grid">
      <div
        v-for="p in plans"
        :key="p.tier"
        class="tactile-card plan-card"
        :class="{ featured: p.tier === 'PRO' }"
      >
        <span class="tier-pill" :class="p.cls">{{ p.tier }}</span>
        <h3>{{ p.name }}</h3>
        <p class="plan-desc">{{ p.desc }}</p>
        <div class="plan-price">
          <template v-if="p.monthly === 0">
            <strong>¥0</strong><span>/ 永久免费</span>
          </template>
          <template v-else>
            <strong>¥{{ cycle === 'yearly' ? p.yearly : p.monthly }}</strong>
            <span>/ {{ cycle === 'yearly' ? '年' : '月' }}</span>
            <del v-if="cycle === 'yearly'" class="price-strike">¥{{ p.monthly * 12 }}</del>
          </template>
        </div>

        <ul class="plan-features">
          <li>每月赠送 <b>{{ p.grant }}</b> 积分（签到 {{ p.checkinMult }}x）</li>
          <li>每日共享免费额度池：<b>{{ p.pool }}</b></li>
          <li>超额积分抵扣：<b>{{ p.discount }}</b></li>
          <li class="feature-bool">
            <span>场景包 ZIP 导入：</span>
            <span class="bool-mark" :class="p.zipImport ? 'yes' : 'no'">{{ p.zipImport ? '✓' : '✕' }}</span>
          </li>
          <li class="feature-bool">
            <span>场景包 ZIP 导出分发：</span>
            <span class="bool-mark" :class="p.zipExport ? 'yes' : 'no'">{{ p.zipExport ? '✓' : '✕' }}</span>
          </li>
          <li>私有知识库文档：<b>{{ p.docs }}</b></li>
        </ul>
      </div>
    </section>

    <!-- 加油包 -->
    <section class="tactile-card packs-box">
      <div class="packs-head">
        <div>
          <h3>回声积分（Echo Credit）加油包</h3>
          <p>积分永久有效，可在每日共享免费额度池用满（100%）后自动抵扣所有 AI 对话与生成</p>
        </div>
      </div>
      <div class="packs-grid">
        <div v-for="pk in packs" :key="pk.credits" class="pack-item">
          <div>
            <strong><EchoCreditIcon :size="16" /> {{ pk.credits }} 点</strong>
            <small>{{ pk.name }}</small>
          </div>
          <span class="pack-price">¥{{ pk.price }}</span>
        </div>
      </div>
    </section>

    <!-- 全量权益对比表 -->
    <section class="matrix-section">
      <h2>全量功能权益对比</h2>
      <div class="tactile-card table-wrap">
        <table class="compare-table">
          <thead>
            <tr>
              <th>功能权益维度</th>
              <th>FREE 免费版</th>
              <th class="pro-col">PRO 专业版</th>
              <th>ENTERPRISE 企业版</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in matrix" :key="row.label">
              <td>{{ row.label }}</td>
              <td>{{ row.free }}</td>
              <td class="pro-col"><b>{{ row.pro }}</b></td>
              <td>{{ row.ent }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- FAQ -->
    <section class="faq-section">
      <h2>常见计费与权限说明</h2>
      <div class="faq-list">
        <div v-for="(item, idx) in faqs" :key="item.q" class="tactile-card faq-item">
          <button type="button" class="faq-q" @click="openFaq = openFaq === idx ? -1 : idx">
            <span>{{ item.q }}</span>
            <b>{{ openFaq === idx ? '−' : '+' }}</b>
          </button>
          <p v-if="openFaq === idx" class="faq-a">{{ item.a }}</p>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import EchoCreditIcon from '../components/EchoCreditIcon.vue'

const cycle = ref('yearly')
const openFaq = ref(0)

const plans = [
  {
    tier: 'FREE',
    cls: 'tier-free',
    name: 'Free 免费体验版',
    monthly: 0,
    yearly: 0,
    grant: 0,
    checkinMult: 1,
    pool: '40 点 / 日',
    discount: '10 折消耗',
    zipImport: false,
    zipExport: false,
    docs: '不支持',
    desc: '每日赠送共享免费额度池，搭配签到与任务中心赚取积分继续练习。',
  },
  {
    tier: 'PRO',
    cls: 'tier-pro',
    name: 'Pro 个人专业版',
    monthly: 29,
    yearly: 268,
    grant: 1200,
    checkinMult: 2,
    pool: '400 点 / 日（10x）',
    discount: '8 折消耗',
    zipImport: true,
    zipExport: false,
    docs: '上限 15 份',
    desc: '开放场景包 ZIP 导入、AI 草稿生成、私有简历知识库与 8 折积分消耗。',
  },
  {
    tier: 'ENT',
    cls: 'tier-ent',
    name: 'Enterprise 机构/企业版',
    monthly: 199,
    yearly: 1880,
    grant: 10000,
    checkinMult: 3,
    pool: '无限制畅享',
    discount: '全免畅享',
    zipImport: true,
    zipExport: true,
    docs: '上限 200 份',
    desc: '开放场景包 ZIP 打包导出分发、无限场景创建与大容量企业知识库。',
  },
]

const packs = [
  { credits: 300, name: '轻量体验包', price: 6 },
  { credits: 1000, name: '高频冲刺包', price: 18 },
  { credits: 3000, name: '年度备考大容量包', price: 48 },
]

const matrix = [
  { label: '每日共享免费额度池', free: '40 点 / 日', pro: '400 点 / 日', ent: '无限制' },
  { label: '1v1 语音对话（单轮消耗）', free: '2 点 / 轮', pro: '2 点 / 轮（8折超额）', ent: '全免' },
  { label: '1vN 多角色辩论 / 群面', free: '4 点 / 轮', pro: '4 点 / 轮（8折超额）', ent: '全免' },
  { label: '自定义 1v1 / 多角色场景上限', free: '2 个 / 1 个', pro: '30 个 / 20 个', ent: '无限制' },
  { label: '场景包 ZIP 导入（上传使用）', free: '不支持', pro: '支持导入', ent: '支持批量导入' },
  { label: '场景包 ZIP 导出分发（防盗版打包）', free: '不支持', pro: '不支持', ent: '企业专享导出' },
  { label: '私有知识库 (Hybrid + LightRAG)', free: '不支持', pro: '最多 15 份文档', ent: '最多 200 份文档' },
  { label: '每日签到与任务中心双奖励', free: '1x 基础倍率', pro: '2x 积分倍率', ent: '3x 积分倍率' },
]

const faqs = [
  {
    q: '什么是「统一共享免费额度池」？',
    a: '系统不再为 1v1 对话、多角色、听力 AI 助教分别设限，而是统一提供一个每日 00:00 重置的共享额度池（如 Free 每日 40 点，Pro 每日 400 点），所有消耗性动作共用同一进度池。',
  },
  {
    q: '免费额度池用满 100% 后会直接扣我的回声积分吗？',
    a: '取决于你在「任务与积分」中心开启的「超额自动消耗回声积分」开关。开启后自动按折扣扣减永久积分；关闭则暂停扣费，避免误花积分。',
  },
  {
    q: '为什么场景包 ZIP 导出仅向 Enterprise 企业版开放？',
    a: 'Pro 用户可自由导入社区或老师分享的 ZIP 场景包用于个人练习；Enterprise 版额外开放标准 ZIP 导出分发，方便教研机构与企业 HR 制作并分发内训题库包。',
  },
]
</script>

<style scoped>
.pricing-page { max-width: 1180px; margin: 0 auto; padding: 104px 24px 64px; }
.page-head { text-align: center; max-width: 700px; margin: 0 auto 32px; }
.pill { display: inline-block; padding: 4px 12px; border-radius: 999px; background: #eee9ff; color: var(--primary-ink); font-size: 12px; font-weight: 700; margin-bottom: 10px; }
.page-head h1 { font-size: 34px; font-weight: 900; margin-bottom: 10px; }
.page-head p { font-size: 14.5px; color: var(--text-muted); margin-bottom: 20px; }

.billing-toggle { display: inline-flex; background: #f1edf9; padding: 4px; border-radius: 12px; }
.billing-toggle button { border: none; background: transparent; padding: 8px 18px; border-radius: 9px; font-size: 13.5px; font-weight: 700; color: var(--text-muted); cursor: pointer; }
.billing-toggle button.active { background: #ffffff; color: var(--primary-ink); box-shadow: 0 2px 6px rgba(96, 70, 180, 0.12); }
.save-tag { background: var(--green-soft); color: var(--green); padding: 1px 6px; border-radius: 6px; font-size: 11px; margin-left: 4px; }

.plans-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; margin-bottom: 20px; }
.plan-card { padding: 24px; display: flex; flex-direction: column; }
.plan-card.featured { border-color: #b7a6ea; background: linear-gradient(180deg, #faf8ff 0%, #ffffff 48%); }
.tier-pill { align-self: flex-start; padding: 3px 10px; border-radius: 999px; font-size: 11px; font-weight: 800; margin-bottom: 10px; }
.tier-free { background: #eaf7f0; color: #2a8c5f; }
.tier-pro { background: linear-gradient(135deg, #8b73dd, #6046b4); color: #ffffff; }
.tier-ent { background: #2f2a45; color: #ffd670; }
.plan-card h3 { font-size: 19px; margin-bottom: 6px; }
.plan-desc { font-size: 13px; color: var(--text-muted); min-height: 40px; margin-bottom: 12px; }
.plan-price { display: flex; align-items: baseline; gap: 4px; margin-bottom: 16px; }
.plan-price strong { font-size: 32px; color: var(--text); }
.plan-price span { font-size: 13px; color: var(--text-muted); }
.price-strike { margin-left: 6px; font-size: 14px; color: #dc4c41; text-decoration: line-through; text-decoration-thickness: 1.5px; }
.plan-features { list-style: none; display: flex; flex-direction: column; gap: 9px; font-size: 13.5px; color: var(--text-soft); }
.feature-bool { display: flex; align-items: center; gap: 6px; }
.bool-mark { display: inline-grid; place-items: center; width: 20px; height: 20px; border-radius: 999px; font-size: 11px; font-weight: 800; }
.bool-mark.yes { background: #eaf7f0; color: #2a8c5f; }
.bool-mark.no { background: #fdece8; color: #b84a39; }

.packs-box { padding: 20px 24px; margin-bottom: 48px; }
.packs-head h3 { font-size: 16px; margin-bottom: 3px; }
.packs-head p { font-size: 13px; color: var(--text-muted); margin-bottom: 14px; }
.packs-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.pack-item { border: 1px solid var(--border); border-radius: 12px; background: #faf9fd; padding: 14px 16px; display: flex; justify-content: space-between; align-items: center; }
.pack-item strong { display: flex; align-items: center; gap: 5px; font-size: 15px; }
.pack-item small { display: block; font-size: 12px; color: var(--text-muted); margin-top: 2px; }
.pack-price { font-size: 16px; font-weight: 800; color: var(--primary-ink); }

.matrix-section { margin-bottom: 48px; }
.matrix-section h2, .faq-section h2 { font-size: 24px; font-weight: 800; text-align: center; margin-bottom: 20px; }
.table-wrap { overflow-x: auto; }
.compare-table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
.compare-table th, .compare-table td { padding: 13px 16px; text-align: left; border-bottom: 1px solid #efecf7; }
.compare-table th { background: #faf9fd; font-weight: 750; color: var(--text); }
.compare-table .pro-col { background: #f8f5ff; color: var(--primary-ink); }

.faq-list { max-width: 820px; margin: 0 auto; display: flex; flex-direction: column; gap: 12px; }
.faq-item { padding: 16px 20px; }
.faq-q { width: 100%; border: none; background: transparent; display: flex; justify-content: space-between; align-items: center; font-size: 15px; font-weight: 700; color: var(--text); cursor: pointer; text-align: left; }
.faq-q b { color: var(--primary-ink); font-size: 18px; }
.faq-a { margin-top: 10px; font-size: 13.5px; color: var(--text-muted); line-height: 1.7; }

@media (max-width: 900px) {
  .plans-grid, .packs-grid { grid-template-columns: 1fr; }
}
</style>
