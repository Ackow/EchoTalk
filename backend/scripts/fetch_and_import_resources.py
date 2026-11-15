#!/usr/bin/env python3
"""从开源四六级仓库与国内外公开电台/访谈 RSS 抓取并导入 EchoTalk 听力库。

用法（请在有网络与数据库连接的本机终端运行）：
    cd backend
    .venv/bin/python scripts/fetch_and_import_resources.py --all
"""
from __future__ import annotations

import argparse
import html
import io
import json
import os
import re
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select  # noqa: E402

from app.core.database import SessionLocal, engine  # noqa: E402
from app.models.listening import ListeningUnit  # noqa: E402
from app.services.listening_service import import_unit  # noqa: E402

RAW_DIR = BACKEND_DIR / "data" / "raw_sources"
BUNDLE_PATH = BACKEND_DIR / "data" / "listening_bundle.json"

CET_REPOS = {
    "english-exem-md": "https://github.com/wamich/english-exem-md.git",
    "cet6-full": "https://github.com/HCLEMINI/CET6-Full-Process-Learning.git",
    "cet4-pwa": "https://github.com/gongyining0601/cet4.git",
}

PUBLIC_RSS_FEEDS = [
    {
        "name": "BBC Global News Podcast",
        "url": "https://podcasts.files.bbci.co.uk/p02nq0gn.rss",
        "channel": "radio",
        "channelLabel": "BBC 国际新闻电台",
        "level": "常速新闻",
        "accent": "标准英音",
    },
    {
        "name": "NPR News Now",
        "url": "https://feeds.npr.org/500005/podcast.xml",
        "channel": "radio",
        "channelLabel": "NPR 整点新闻",
        "level": "常速新闻",
        "accent": "标准美音",
    },
    {
        "name": "TED Talks Daily",
        "url": "https://feeds.feedburner.com/TEDTalks_audio",
        "channel": "talks",
        "channelLabel": "TED 公开演讲与访谈",
        "level": "真实访谈",
        "accent": "多口音演讲",
    },
    {
        "name": "VOA Learning English",
        "url": "https://learningenglish.voanews.com/podcast/?zoneId=1579",
        "channel": "radio",
        "channelLabel": "VOA 慢速英语电台",
        "level": "慢速精听",
        "accent": "慢速美音",
    },
]


def _clean_text(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _download_github_zip(url: str, target: Path) -> bool:
    repo_base = url[:-4] if url.endswith(".git") else url
    for prefix in ("", "https://ghfast.top/", "https://gh-proxy.com/"):
        for branch in ("main", "master"):
            zip_url = f"{prefix}{repo_base}/archive/refs/heads/{branch}.zip"
            try:
                req = urllib.request.Request(zip_url, headers={"User-Agent": "EchoTalk/2.0"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = resp.read()
                with zipfile.ZipFile(io.BytesIO(data)) as zf:
                    target.mkdir(parents=True, exist_ok=True)
                    zf.extractall(target)
                print(f"[CET] 通过压缩包下载成功: {zip_url}")
                return True
            except Exception:
                continue
    return False


def _clone_or_pull(name: str, url: str, proxy: str = "") -> Path:
    target = RAW_DIR / name
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if target.exists() and (target / ".git").exists():
        subprocess.run(["git", "-C", str(target), "pull", "--ff-only"], check=False)
        return target
    if target.exists() and any(target.iterdir()):
        return target

    try:
        subprocess.run(["git", "clone", "--depth", "1", url, str(target)], check=True)
        return target
    except subprocess.CalledProcessError:
        pass

    candidate_proxy = proxy or os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY") or "http://127.0.0.1:7890"
    if candidate_proxy:
        try:
            subprocess.run(
                [
                    "git",
                    "-c",
                    f"http.proxy={candidate_proxy}",
                    "-c",
                    f"https.proxy={candidate_proxy}",
                    "clone",
                    "--depth",
                    "1",
                    url,
                    str(target),
                ],
                check=True,
            )
            return target
        except subprocess.CalledProcessError:
            pass

    if _download_github_zip(url, target):
        return target

    raise RuntimeError(f"无法拉取仓库 {url}（请检查代理或网络）")


def parse_cet_markdown_file(md_path: Path) -> dict | None:
    """从开源 Markdown 真题文件中尽量提取听力题目与原文，构造 ListeningUnit。"""
    if "技巧" in md_path.name or not re.search(r"20[0-2]\d", str(md_path)):
        return None
    text = md_path.read_text(encoding="utf-8", errors="ignore")
    if len(text) < 200:
        return None

    name_lower = str(md_path).lower()
    cet_level = "cet6" if ("cet6" in name_lower or "六级" in text[:400]) else "cet4"
    year_match = re.search(r"(20[0-2]\d)", md_path.name) or re.search(r"(20[0-2]\d)", text[:300])
    year_label = year_match.group(1) if year_match else "历年"

    # 提取英文句子作为听音练习素材（优先听力部分）
    listening_section = text
    m_sec = re.search(r"(Part\s*II\s*Listening.*?)(?=Part\s*III|\Z)", text, re.S | re.I)
    if m_sec:
        listening_section = m_sec.group(1)

    # 匹配常见 A/B/C/D 选择题块
    q_pattern = re.compile(
        r"(?:^|\n)\s*(\d{1,2})[\.、\)]\s*([^\n]+?)\n+"
        r"\s*A[\.、\)]\s*([^\n]+)\n+"
        r"\s*B[\.、\)]\s*([^\n]+)\n+"
        r"\s*C[\.、\)]\s*([^\n]+)\n+"
        r"\s*D[\.、\)]\s*([^\n]+)",
        re.M,
    )
    exercises = []
    for idx, m in enumerate(q_pattern.finditer(listening_section)):
        if idx >= 10:
            break
        q_num, prompt, opt_a, opt_b, opt_c, opt_d = [s.strip() for s in m.groups()]
        prompt_en = prompt if re.search(r"[A-Za-z]{3,}", prompt) else f"Question {q_num}: Listen and choose the best answer."
        exercises.append(
            {
                "id": f"{md_path.stem}-q{q_num}",
                "type": "choice",
                "prompt": prompt_en,
                "audioText": f"{prompt_en} Option A: {opt_a}. Option B: {opt_b}.",
                "zhText": f"第 {q_num} 题（{year_label} {cet_level.upper()} 真题）",
                "keywords": [w for w in re.findall(r"[A-Za-z]{5,}", prompt_en)[:3]],
                "options": [
                    {"key": "A", "text": opt_a},
                    {"key": "B", "text": opt_b},
                    {"key": "C", "text": opt_c},
                    {"key": "D", "text": opt_d},
                ],
                "answer": "A",
                "tip": "结合选项关键词预判听力重点，注意转折与因果信号词。",
                "errorTag": "真题听力",
            }
        )

    if not exercises:
        # 兜底：从英文长句生成听写与跟读练习
        sentences = [
            s.strip()
            for s in re.findall(r"([A-Z][A-Za-z0-9 ,;:'\"-]{25,140}[\.\?\!])", listening_section)
        ]
        for idx, sent in enumerate(sentences[:6]):
            words = [w for w in re.findall(r"[A-Za-z]{4,}", sent)]
            target_word = words[min(2, len(words) - 1)] if words else "English"
            exercises.append(
                {
                    "id": f"{md_path.stem}-s{idx + 1}",
                    "type": "cloze",
                    "prompt": "听录音补全真题原句关键信息",
                    "audioText": sent,
                    "zhText": f"{year_label} {cet_level.upper()} 真题句型",
                    "keywords": words[:3],
                    "template": sent.replace(target_word, "____", 1),
                    "blanks": [target_word],
                    "tip": f"核心词拼写：{target_word}",
                    "errorTag": "真题听写",
                }
            )

    if not exercises:
        return None

    m_meta = re.search(r"(20[0-2]\d)[._-](\d{2})[._-](\d+)", md_path.stem)
    pretty_title = (
        f"{m_meta.group(1)}年{m_meta.group(2)}月 {cet_level.upper()} 真题 · 第{m_meta.group(3)}套"
        if m_meta
        else f"{cet_level.upper()} 真题：{md_path.stem}"
    )

    return {
        "id": f"cet-{cet_level}-{re.sub(r'[^a-zA-Z0-9_-]+', '-', md_path.stem).lower()}",
        "channel": "cet",
        "cetLevel": cet_level,
        "cetSection": "news" if cet_level == "cet4" else "conversation",
        "channelLabel": f"{cet_level.upper()} · {year_label} 真题",
        "level": "四级真题" if cet_level == "cet4" else "六级真题",
        "title": pretty_title,
        "subtitle": f"来源开源真题库 · 共 {len(exercises)} 题",
        "duration": f"{max(3, len(exercises) * 2)} 分钟",
        "xp": 35,
        "accent": "标准美音",
        "exercises": exercises,
    }


def parse_cet4_pwa_js(js_path: Path) -> dict | None:
    """解析 cet4-pwa/bank/cet4-*.js 中的结构化真题与听力定位原句。"""
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
    try:
        paper = json.loads(json_str)
    except Exception:
        return None

    questions = [q for q in (paper.get("questions") or []) if q.get("type") == "listening"]
    if not questions:
        return None

    exercises = []
    for q in questions:
        analysis = q.get("analysis") or ""
        loc_match = re.search(r"【定位】([^\n【]+)", analysis)
        audio_text = loc_match.group(1).strip() if loc_match else (q.get("stem") or "")
        # 去掉末尾中文翻译，保留英文原句
        audio_en = re.split(r"[\u4e00-\u9fff]", audio_text, maxsplit=1)[0].strip()
        if len(audio_en) < 12:
            audio_en = q.get("stem") or audio_text

        tip_match = re.search(r"【替换】([^\n【]+)", analysis)
        tip = tip_match.group(1).strip() if tip_match else "注意因果、转折与同义替换信号词。"

        opts = []
        for o in q.get("options") or []:
            m_opt = re.match(r"^([A-D])[\)\.\s]+(.*)$", str(o).strip())
            if m_opt:
                opts.append({"key": m_opt.group(1), "text": m_opt.group(2).strip()})

        if not opts:
            continue

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
                "answer": str(q.get("answer") or "A").strip()[:1],
                "tip": tip,
                "errorTag": points[-1] if points else "四级真题",
            }
        )

    if not exercises:
        return None

    paper_id = str(paper.get("id") or js_path.stem)
    source_title = paper.get("source") or paper_id
    return {
        "id": f"cet4-{paper_id}",
        "channel": "cet",
        "cetLevel": "cet4",
        "cetSection": "news",
        "channelLabel": f"CET-4 · {paper_id[:7]}",
        "level": "四级真题",
        "title": f"CET-4 真题：{source_title}",
        "subtitle": f"2015–2026 四级听力真题库 · 共 {len(exercises)} 题",
        "duration": f"{max(5, len(exercises))} 分钟",
        "xp": 40,
        "accent": "标准美音",
        "exercises": exercises,
    }


def collect_cet_units(proxy: str = "") -> list[dict]:
    units: list[dict] = []
    for name, url in CET_REPOS.items():
        print(f"[CET] 同步仓库 {name} -> {url}")
        try:
            repo_dir = _clone_or_pull(name, url, proxy=proxy)
        except Exception as exc:
            print(f"[CET] 仓库 {name} 拉取失败: {exc}")
            continue

        for md_path in sorted(repo_dir.rglob("*.md")):
            if md_path.name.lower() == "readme.md":
                continue
            unit = parse_cet_markdown_file(md_path)
            if unit:
                units.append(unit)

        for js_path in sorted(repo_dir.rglob("cet4-*.js")):
            unit = parse_cet4_pwa_js(js_path)
            if unit:
                units.append(unit)

        for json_path in sorted(repo_dir.rglob("*.json")):
            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if isinstance(item, dict) and item.get("title") and isinstance(item.get("exercises"), list) and item["exercises"]:
                        item.setdefault("channel", "cet")
                        item.setdefault("cetLevel", "cet6")
                        units.append(item)
            except Exception:
                continue
    return units


def parse_rss_feed(feed: dict, limit: int = 8) -> list[dict]:
    """解析公开电台/演讲 RSS，提取真实音频 URL 与精听练习。"""
    req = urllib.request.Request(feed["url"], headers={"User-Agent": "EchoTalk/2.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        xml_bytes = resp.read()

    root = ET.fromstring(xml_bytes)
    units: list[dict] = []
    for idx, item in enumerate(root.findall(".//item")):
        if len(units) >= limit:
            break
        title = _clean_text(item.findtext("title") or "")
        desc = _clean_text(item.findtext("description") or "")
        enclosure = item.find("enclosure")
        audio_url = enclosure.attrib.get("url", "").strip() if enclosure is not None else ""
        if not title or not audio_url:
            continue

        sentences = [
            s.strip()
            for s in re.split(r"(?<=[\.\?\!])\s+", desc)
            if len(s.strip()) >= 25
        ]
        summary_sent = sentences[0] if sentences else title
        words = re.findall(r"[A-Za-z]{4,}", summary_sent)
        blank_word = words[min(2, len(words) - 1)] if words else "news"

        exercises = [
            {
                "id": f"rss-{idx + 1}-shadow",
                "type": "shadowing",
                "prompt": f"收听原声节目《{title[:48]}》，跟读核心导语",
                "audioUrl": audio_url,
                "audioText": summary_sent,
                "zhText": "公开电台/演讲原声训练（支持 0.75× 慢速精听）",
                "keywords": words[:4],
                "tip": "先盲听大意，再抓主语与动词时态。",
                "errorTag": "电台精听",
            },
            {
                "id": f"rss-{idx + 1}-cloze",
                "type": "cloze",
                "prompt": "根据节目导语完成关键词听写",
                "audioText": summary_sent,
                "zhText": "核心句关键词拼写",
                "keywords": words[:3],
                "template": summary_sent.replace(blank_word, "____", 1),
                "blanks": [blank_word],
                "tip": f"目标词：{blank_word}",
                "errorTag": "连读弱读",
            },
        ]

        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:32] or str(idx + 1)
        units.append(
            {
                "id": f"{feed['channel']}-{slug}-{idx + 1}",
                "channel": feed["channel"],
                "cetLevel": None,
                "cetSection": None,
                "channelLabel": feed["channelLabel"],
                "level": feed["level"],
                "title": title[:80],
                "subtitle": (desc[:90] + "…") if len(desc) > 90 else desc,
                "duration": "5 分钟",
                "xp": 30,
                "accent": feed["accent"],
                "exercises": exercises,
            }
        )
    return units


def collect_public_feeds(limit_per_feed: int = 8) -> list[dict]:
    units: list[dict] = []
    for feed in PUBLIC_RSS_FEEDS:
        print(f"[RSS] 拉取 {feed['name']} -> {feed['url']}")
        try:
            units.extend(parse_rss_feed(feed, limit=limit_per_feed))
        except Exception as exc:
            print(f"[RSS] {feed['name']} 拉取失败: {exc}")
    return units


def save_units_to_db(units: list[dict]) -> int:
    ListeningUnit.__table__.create(bind=engine, checkfirst=True)
    inserted = 0
    with SessionLocal() as db:
        # 清理旧的模拟四六级占位单元与非真题文档（如“技巧学习”）
        for stale in db.scalars(select(ListeningUnit)).all():
            if stale.id in (
                "cet4-news-urban",
                "cet4-conv-library",
                "cet4-passage-museum",
                "cet6-conv-internship",
                "cet6-lecture-sleep",
            ) or "技巧学习" in (stale.title or ""):
                db.delete(stale)
        db.commit()

        existing_titles = set(db.scalars(select(ListeningUnit.title)).all())
        for unit in units:
            if unit["title"] in existing_titles:
                continue
            import_unit(db, None, unit)
            existing_titles.add(unit["title"])
            inserted += 1
    return inserted


def main() -> None:
    parser = argparse.ArgumentParser(description="抓取并导入四六级开源真题与公开电台/演讲听力资源")
    parser.add_argument("--cet", action="store_true", help="仅抓取开源四六级仓库")
    parser.add_argument("--feeds", action="store_true", help="仅抓取公开电台/TED RSS")
    parser.add_argument("--all", action="store_true", help="抓取全部资源并写入数据库")
    parser.add_argument("--export-only", action="store_true", help="仅导出 JSON 包，不直接写数据库")
    parser.add_argument("--limit-per-feed", type=int, default=8, help="每个公开电台抓取条数")
    parser.add_argument("--proxy", default="", help="可选 HTTP 代理，例如 http://127.0.0.1:7890")
    args = parser.parse_args()

    run_cet = args.all or args.cet or (not args.feeds)
    run_feeds = args.all or args.feeds or (not args.cet)

    collected: list[dict] = []
    if run_cet:
        collected.extend(collect_cet_units(proxy=args.proxy))
    if run_feeds:
        collected.extend(collect_public_feeds(limit_per_feed=args.limit_per_feed))

    BUNDLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BUNDLE_PATH.write_text(json.dumps(collected, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已生成资源包：{BUNDLE_PATH}（共 {len(collected)} 个单元）")

    if not args.export_only and collected:
        count = save_units_to_db(collected)
        print(f"已写入数据库：新增 {count} 个听力单元")


if __name__ == "__main__":
    main()
