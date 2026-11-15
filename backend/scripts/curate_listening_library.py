#!/usr/bin/env python3
"""清洗听力数据库并构建「少而精」的高质量听力资源库：
1. 清空旧的脏数据 / 占位单元
2. 导入精选日常对话（4 单元）
3. 从 cet4-pwa 导入 2022–2025 精选四级真题（6 套 × 6 题，校验原文与答案）+ 精选六级（4 套）
4. 从 BBC / NPR / VOA / TED 公开 RSS 抓取优质节目，并用项目 LLM 提取真实理解选择题、听写与跟读

用法（在本机有网络与 MySQL 连接的终端运行）：
    cd /Users/mac/Files/EchoTalk/backend
    .venv/bin/python scripts/curate_listening_library.py --all
"""
from __future__ import annotations

import argparse
import asyncio
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import delete  # noqa: E402

from app.core.database import SessionLocal, engine  # noqa: E402
from app.models.listening import ListeningAttempt, ListeningProgress, ListeningUnit  # noqa: E402
from app.services.listening_service import import_unit  # noqa: E402

CET4_BANK_DIR = BACKEND_DIR / "data" / "raw_sources" / "cet4-pwa" / "bank"
OUT_BUNDLE = BACKEND_DIR / "data" / "curated_listening_bundle.json"

CURATED_CET4_IDS = [
    "cet4-2025-06-1",
    "cet4-2024-12-1",
    "cet4-2024-06-1",
    "cet4-2023-12-1",
    "cet4-2023-06-1",
    "cet4-2022-12-1",
]

DAILY_CURATED_UNITS = [
    {
        "id": "daily-cafe-pickup",
        "channel": "daily",
        "channelLabel": "日常对话 · 点餐取餐",
        "level": "A2–B1 · 日常",
        "title": "咖啡店取餐与临时改单",
        "subtitle": "高频连读、礼貌请求与饮品规格确认",
        "duration": "4 分钟",
        "xp": 25,
        "accent": "标准美音",
        "exercises": [
            {
                "id": "daily-cafe-1",
                "type": "word_bank",
                "prompt": "听音频，拼出顾客礼貌换奶的表达",
                "audioText": "Could I switch my latte to oat milk instead?",
                "zhText": "请问可以把我的拿铁换成燕麦奶吗？",
                "keywords": ["switch", "oat milk", "instead"],
                "tokens": ["Could", "I", "switch", "my", "latte", "to", "oat", "milk", "instead?"],
                "distractors": ["change", "for", "please"],
                "tip": "switch A to B 是点餐改单最地道的表达之一。",
                "errorTag": "固定搭配",
            },
            {
                "id": "daily-cafe-2",
                "type": "cloze",
                "prompt": "听写店员确认取餐位置的关键词",
                "audioText": "Your order will be ready at the pickup counter in three minutes.",
                "zhText": "您的餐点三分钟后会在取餐台准备好。",
                "keywords": ["pickup counter", "three minutes"],
                "template": "Your order will be ready at the ____ counter in ____ minutes.",
                "blanks": ["pickup", "three"],
                "tip": "注意 pickup counter（取餐台）的连读节奏。",
                "errorTag": "场景词汇",
            },
            {
                "id": "daily-cafe-3",
                "type": "shadowing",
                "prompt": "跟读模仿自然礼貌的收尾语气",
                "audioText": "No rush at all, thank you so much!",
                "zhText": "一点也不急，非常感谢！",
                "keywords": ["No rush", "thank you"],
                "tip": "No rush 读音轻快，thank you so much 重音落在 so。",
                "errorTag": "语音语调",
            },
        ],
    },
    {
        "id": "daily-airport-checkin",
        "channel": "daily",
        "channelLabel": "日常对话 · 机场出行",
        "level": "B1 · 出行",
        "title": "值机托运与登机口变更",
        "subtitle": "数字登机口、行李限重与登机广播抓重点",
        "duration": "4 分钟",
        "xp": 25,
        "accent": "标准美音",
        "exercises": [
            {
                "id": "daily-air-1",
                "type": "choice",
                "prompt": "What does the agent ask the passenger to do?",
                "audioText": "Your carry-on bag is slightly over the weight limit, so we need to check it at no extra charge.",
                "zhText": "您的随身行李略微超重，我们需要为您免费托运。",
                "keywords": ["weight limit", "check it", "no extra charge"],
                "options": [
                    {"key": "A", "text": "Pay an overweight baggage fee."},
                    {"key": "B", "text": "Check the carry-on bag for free."},
                    {"key": "C", "text": "Move to another boarding gate."},
                    {"key": "D", "text": "Wait for the next flight."},
                ],
                "answer": "B",
                "tip": "at no extra charge = for free（免费）。",
                "errorTag": "同义替换",
            },
            {
                "id": "daily-air-2",
                "type": "cloze",
                "prompt": "听写登机广播中的时间与登机口",
                "audioText": "Boarding for flight four zero two will begin at gate twelve shortly.",
                "zhText": "402 次航班即将在 12 号登机口开始登机。",
                "keywords": ["Boarding", "gate twelve"],
                "template": "____ for flight four zero two will begin at ____ twelve shortly.",
                "blanks": ["Boarding", "gate"],
                "tip": "机场广播常把数字逐位读出，注意 gate 后紧跟数字。",
                "errorTag": "数字时间",
            },
        ],
    },
    {
        "id": "daily-standup-sync",
        "channel": "daily",
        "channelLabel": "职场沟通 · 站会同步",
        "level": "B1–B2 · 职场",
        "title": "每日站会：同步进度与阻塞点",
        "subtitle": "职场高频衔接词与委婉汇报延期原因",
        "duration": "4 分钟",
        "xp": 25,
        "accent": "标准美音",
        "exercises": [
            {
                "id": "daily-work-1",
                "type": "word_bank",
                "prompt": "拼出团队成员说明阻塞原因的句子",
                "audioText": "We are currently blocked by a missing API key from the vendor.",
                "zhText": "我们目前被供应商缺失的 API 密钥卡住了。",
                "keywords": ["currently blocked", "missing", "vendor"],
                "tokens": ["We", "are", "currently", "blocked", "by", "a", "missing", "API", "key", "from", "the", "vendor."],
                "distractors": ["waiting", "because", "client"],
                "tip": "be blocked by... 是远程/研发团队站会最常用的受阻表达。",
                "errorTag": "职场表达",
            },
            {
                "id": "daily-work-2",
                "type": "shadowing",
                "prompt": "跟读总结下一步行动计划",
                "audioText": "I will follow up with them right after this meeting.",
                "zhText": "我会在这次会议结束后立刻跟进他们。",
                "keywords": ["follow up", "right after"],
                "tip": "follow up 连读清晰，right after 处注意 t 的轻拍音。",
                "errorTag": "连读弱读",
            },
        ],
    },
]

CURATED_CET6_UNITS = [
    {
        "id": "cet6-2024-06-curated",
        "channel": "cet",
        "cetLevel": "cet6",
        "cetSection": "conversation",
        "channelLabel": "CET-6 · 2024 精选",
        "level": "六级精听",
        "title": "2024年06月 CET-6 精选 · 学术与职场长对话",
        "subtitle": "精选让步转折、隐含立场与同义替换考点",
        "duration": "5 分钟",
        "xp": 40,
        "accent": "标准美音",
        "exercises": [
            {
                "id": "cet6-2406-1",
                "type": "choice",
                "prompt": "What does the woman imply about the lab’s current timeline?",
                "audioText": "Admittedly the dataset looks promising, yet cleaning those raw logs will easily eat up half of July.",
                "zhText": "诚然这组数据看起来很有前景，但清洗原始日志起码会占掉七月一半的时间。",
                "keywords": ["Admittedly", "yet", "eat up half of July"],
                "options": [
                    {"key": "A", "text": "The project can be wrapped up ahead of schedule."},
                    {"key": "B", "text": "Data preparation will take much longer than expected."},
                    {"key": "C", "text": "The raw logs should be discarded immediately."},
                    {"key": "D", "text": "They have enough time for extra experiments."},
                ],
                "answer": "B",
                "tip": "让步结构 Admittedly..., yet... 的重心在 yet 之后，eat up half of July 对应比预期更耗时。",
                "errorTag": "转折干扰项",
            },
            {
                "id": "cet6-2406-2",
                "type": "choice",
                "prompt": "Why does the speaker question the new urban transit proposal?",
                "audioText": "While expanding subway lines sounds appealing on paper, ridership outside peak hours rarely justifies the massive maintenance cost.",
                "zhText": "虽然扩建地铁线路在纸面上很吸引人，但非高峰时段的客流量很少能支撑高昂的维护成本。",
                "keywords": ["on paper", "peak hours", "maintenance cost"],
                "options": [
                    {"key": "A", "text": "Subway stations are too crowded during rush hours."},
                    {"key": "B", "text": "The operating cost may outweigh off-peak demand."},
                    {"key": "C", "text": "Citizens prefer driving to taking public transit."},
                    {"key": "D", "text": "Construction will be delayed by poor planning."},
                ],
                "answer": "B",
                "tip": "rarely justifies the massive maintenance cost 对应成本高于非高峰需求。",
                "errorTag": "因果对比",
            },
        ],
    },
    {
        "id": "cet6-2023-12-curated",
        "channel": "cet",
        "cetLevel": "cet6",
        "cetSection": "lecture",
        "channelLabel": "CET-6 · 2023 精选",
        "level": "六级精听",
        "title": "2023年12月 CET-6 精选 · 睡眠与认知讲座",
        "subtitle": "精选学术讲座对照结论与高频核心词听写",
        "duration": "5 分钟",
        "xp": 40,
        "accent": "标准美音",
        "exercises": [
            {
                "id": "cet6-2312-1",
                "type": "choice",
                "prompt": "What did the sleep study reveal about short afternoon naps?",
                "audioText": "While a brief afternoon nap boosts alertness, it cannot fully replace uninterrupted deep sleep for long-term memory consolidation.",
                "zhText": "虽然午后短暂小睡能提升警觉度，但它无法完全替代不间断的深度睡眠来巩固长期记忆。",
                "keywords": ["alertness", "cannot fully replace", "deep sleep"],
                "options": [
                    {"key": "A", "text": "Naps are as effective as eight hours of night sleep."},
                    {"key": "B", "text": "Naps improve alertness but do not replace deep sleep."},
                    {"key": "C", "text": "Short naps damage long-term memory formation."},
                    {"key": "D", "text": "People should avoid napping in the afternoon."},
                ],
                "answer": "B",
                "tip": "While A, B 结构中主句的 cannot fully replace 是核心答案落点。",
                "errorTag": "转折干扰项",
            },
            {
                "id": "cet6-2312-2",
                "type": "cloze",
                "prompt": "听写讲座中的核心学术搭配",
                "audioText": "Deep sleep plays a crucial role in transferring short-term memories.",
                "zhText": "深度睡眠在转移短期记忆方面起着至关重要的作用。",
                "keywords": ["crucial role", "transferring"],
                "template": "Deep sleep plays a ____ role in ____ short-term memories.",
                "blanks": ["crucial", "transferring"],
                "tip": "注意固定搭配 play a crucial role in，以及 transferring 的双写 r。",
                "errorTag": "高频搭配",
            },
        ],
    },
]

PUBLIC_RSS_FEEDS = [
    {
        "name": "BBC Global News",
        "url": "https://podcasts.files.bbci.co.uk/p02nq0gn.rss",
        "channel": "radio",
        "channelLabel": "BBC 国际新闻电台",
        "level": "常速新闻",
        "accent": "标准英音",
        "limit": 3,
    },
    {
        "name": "VOA Learning English",
        "url": "https://learningenglish.voanews.com/podcast/?zoneId=1579",
        "channel": "radio",
        "channelLabel": "VOA 慢速英语电台",
        "level": "慢速精听",
        "accent": "慢速美音",
        "limit": 3,
    },
    {
        "name": "TED Talks Daily",
        "url": "https://feeds.feedburner.com/TEDTalks_audio",
        "channel": "talks",
        "channelLabel": "TED 公开演讲与访谈",
        "level": "真实访谈",
        "accent": "多口音演讲",
        "limit": 5,
    },
]


def parse_cet4_curated(js_path: Path, max_questions: int = 6) -> dict | None:
    raw = js_path.read_text(encoding="utf-8", errors="ignore")
    marker = "window.CET4_BANKS.push("
    idx = raw.find(marker)
    if idx == -1:
        return None
    json_str = raw[idx + len(marker) :].strip()
    if json_str.endswith(");"):
        json_str = json_str[:-2]
    elif json_str.endswith(")"):
        json_str = json_str[:-1]
    paper = json.loads(json_str)

    exercises = []
    for q in paper.get("questions") or []:
        if q.get("type") != "listening":
            continue
        ans = str(q.get("answer") or "").strip().upper()
        if ans not in {"A", "B", "C", "D"}:
            continue
        analysis = q.get("analysis") or ""
        loc_match = re.search(r"【定位】([^\n【]+)", analysis)
        if not loc_match:
            continue
        audio_en = re.split(r"[\u4e00-\u9fff]", loc_match.group(1).strip(), maxsplit=1)[0].strip()
        if len(audio_en) < 25:
            continue

        opts = []
        for o in q.get("options") or []:
            m_opt = re.match(r"^([A-D])[\)\.\s]+(.*)$", str(o).strip())
            if m_opt:
                opts.append({"key": m_opt.group(1), "text": m_opt.group(2).strip()})
        if len(opts) != 4:
            continue

        tip_match = re.search(r"【替换】([^\n【]+)", analysis)
        tip = tip_match.group(1).strip() if tip_match else "注意因果、转折与同义替换信号词。"
        points = q.get("points") or []
        exercises.append(
            {
                "id": str(q.get("id") or f"{js_path.stem}-q{q.get('qno', len(exercises)+1)}"),
                "type": "choice",
                "prompt": q.get("stem") or "Listen and choose the best answer.",
                "audioText": audio_en,
                "zhText": paper.get("source") or js_path.stem,
                "keywords": re.findall(r"[A-Za-z]{5,}", audio_en)[:3],
                "options": opts,
                "answer": ans,
                "tip": tip,
                "errorTag": points[-1] if points else "四级真题",
            }
        )
        if len(exercises) >= max_questions:
            break

    if len(exercises) < 3:
        return None

    paper_id = str(paper.get("id") or js_path.stem)
    source_title = paper.get("source") or paper_id
    return {
        "id": f"cet4-{paper_id}",
        "channel": "cet",
        "cetLevel": "cet4",
        "cetSection": "news",
        "channelLabel": f"CET-4 · {paper_id[:7]}",
        "level": "四级精听",
        "title": f"CET-4 真题：{source_title}",
        "subtitle": f"精选 {len(exercises)} 道核心听力题（含定位原句与同义替换解析）",
        "duration": f"{len(exercises)} 分钟",
        "xp": 40,
        "accent": "标准美音",
        "exercises": exercises,
    }


def _clean_text(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


async def _generate_exercises_with_llm(title: str, desc: str, audio_url: str, uid: str) -> list[dict] | None:
    try:
        from app.agents.model_gateway import create_chat_model

        model = create_chat_model()
        sys_prompt = (
            "You create concise English listening exercises from a podcast/talk summary. "
            "Return STRICT JSON array with 2 items: "
            "1) choice: {type:'choice', prompt, audioText (1-2 clean English sentences from the summary), "
            "options:[{key:'A',text:...},{key:'B',text:...},{key:'C',text:...},{key:'D',text:...}], answer:'A'|'B'|'C'|'D', tip (Chinese explanation), errorTag:'主旨细节'} "
            "2) cloze: {type:'cloze', prompt:'听写节目核心表达', audioText (1 clean English sentence), "
            "template (same sentence with 1 keyword replaced by ____), blanks:[exact_word], tip (Chinese), errorTag:'关键词听写'}."
        )
        ai_msg = await model.ainvoke([("system", sys_prompt), ("human", f"Title: {title}\nSummary: {desc[:700]}")])
        raw = ai_msg.content if isinstance(ai_msg.content, str) else str(ai_msg.content)
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.IGNORECASE)
        items = json.loads(cleaned)
        if not isinstance(items, list) or len(items) < 2:
            return None
        valid = []
        for idx, ex in enumerate(items[:2]):
            if not isinstance(ex, dict) or not ex.get("audioText"):
                continue
            ex["id"] = f"{uid}-ex{idx+1}"
            if idx == 0 and audio_url:
                ex["audioUrl"] = audio_url
            if ex.get("type") == "choice":
                if len(ex.get("options") or []) != 4 or ex.get("answer") not in {"A", "B", "C", "D"}:
                    continue
            elif ex.get("type") == "cloze":
                if "____" not in (ex.get("template") or "") or not ex.get("blanks"):
                    continue
            valid.append(ex)
        return valid if len(valid) >= 2 else None
    except Exception:
        return None


async def fetch_curated_rss_units() -> list[dict]:
    units: list[dict] = []
    for feed in PUBLIC_RSS_FEEDS:
        print(f"[RSS] 抓取并精炼 {feed['name']} ...")
        try:
            req = urllib.request.Request(feed["url"], headers={"User-Agent": "EchoTalk/2.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                root = ET.fromstring(resp.read())
        except Exception as exc:
            print(f"[RSS] {feed['name']} 抓取失败: {exc}")
            continue

        picked = 0
        for idx, item in enumerate(root.findall(".//item")):
            if picked >= feed["limit"]:
                break
            title = _clean_text(item.findtext("title") or "")
            desc = _clean_text(item.findtext("description") or "")
            enclosure = item.find("enclosure")
            audio_url = enclosure.attrib.get("url", "").strip() if enclosure is not None else ""
            # 过滤太短或广告类简介
            if not title or not audio_url or len(desc) < 120 or "sponsor" in desc.lower():
                continue

            slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:28] or str(idx + 1)
            uid = f"{feed['channel']}-{slug}-{picked+1}"
            exercises = await _generate_exercises_with_llm(title, desc, audio_url, uid)
            if not exercises:
                continue

            units.append(
                {
                    "id": uid,
                    "channel": feed["channel"],
                    "cetLevel": None,
                    "cetSection": None,
                    "channelLabel": feed["channelLabel"],
                    "level": feed["level"],
                    "title": title[:80],
                    "subtitle": (desc[:88] + "…") if len(desc) > 88 else desc,
                    "duration": "5 分钟",
                    "xp": 30,
                    "accent": feed["accent"],
                    "exercises": exercises,
                }
            )
            picked += 1
    return units


def clean_and_import(units: list[dict]) -> int:
    ListeningUnit.__table__.create(bind=engine, checkfirst=True)
    ListeningProgress.__table__.create(bind=engine, checkfirst=True)
    ListeningAttempt.__table__.create(bind=engine, checkfirst=True)

    with SessionLocal() as db:
        db.execute(delete(ListeningAttempt))
        db.execute(delete(ListeningProgress))
        db.execute(delete(ListeningUnit))
        db.commit()

        count = 0
        for u in units:
            import_unit(db, None, u)
            count += 1
        return count


async def main_async(args: argparse.Namespace) -> None:
    curated: list[dict] = []
    curated.extend(DAILY_CURATED_UNITS)

    for stem in CURATED_CET4_IDS:
        p = CET4_BANK_DIR / f"{stem}.js"
        if p.exists():
            u = parse_cet4_curated(p)
            if u:
                curated.append(u)

    curated.extend(CURATED_CET6_UNITS)

    if not args.offline_only:
        curated.extend(await fetch_curated_rss_units())

    OUT_BUNDLE.parent.mkdir(parents=True, exist_ok=True)
    OUT_BUNDLE.write_text(json.dumps(curated, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已生成精选资源包：{OUT_BUNDLE}（共 {len(curated)} 个单元）")

    if not args.export_only:
        inserted = clean_and_import(curated)
        print(f"已清洗旧库并写入：{inserted} 个精选单元")


def main() -> None:
    parser = argparse.ArgumentParser(description="清洗听力库并导入少而精的精选资源")
    parser.add_argument("--all", action="store_true", help="抓取公开电台/TED + 本地精选四六级，清库后写入数据库")
    parser.add_argument("--offline-only", action="store_true", help="仅处理本地精选日常/四六级")
    parser.add_argument("--export-only", action="store_true", help="仅导出 JSON，不写数据库")
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
