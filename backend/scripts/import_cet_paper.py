"""四六级 / 听力工作室资源导入与语音合成工具。

用法示例：
1. 从本地四六级 LRC 字幕生成 EchoTalk 关卡 JSON（配合你的本地 MP3）：
   backend/.venv/bin/python backend/scripts/import_cet_paper.py lrc \
     --lrc path/to/cet4_2024_06.lrc \
     --audio-url /audio/cet4_2024_06.mp3 \
     --level cet4 \
     --title "2024年6月四级真题听力" \
     --out cet4_2024_06.json

2. 用 Edge-TTS 为 JSON 关卡批量合成真实 MP3 音频：
   backend/.venv/bin/python backend/scripts/import_cet_paper.py tts \
     --input cet4_2024_06.json \
     --out-dir frontend/public/audio/listening
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
from pathlib import Path

LRC_LINE_RE = re.compile(r"^\[(\d{1,2}):(\d{2})(?:\.(\d{1,3}))?\]\s*(.+)$")


def parse_lrc(lrc_path: Path) -> list[dict]:
    """解析 LRC 时间轴字幕，输出带 start_ms / end_ms 的分句列表。"""
    entries: list[dict] = []
    for raw in lrc_path.read_text(encoding="utf-8").splitlines():
        m = LRC_LINE_RE.match(raw.strip())
        if not m:
            continue
        mins, secs, ms_str, text = m.groups()
        ms = int(ms_str.ljust(3, "0")[:3]) if ms_str else 0
        start_ms = (int(mins) * 60 + int(secs)) * 1000 + ms
        if text:
            entries.append({"start_ms": start_ms, "text": text})

    for idx, item in enumerate(entries):
        item["idx"] = idx + 1
        item["end_ms"] = entries[idx + 1]["start_ms"] if idx + 1 < len(entries) else item["start_ms"] + 5000
    return entries


def build_unit_from_lrc(args: argparse.Namespace) -> dict:
    """将 LRC 分句转换为 EchoTalk ListeningStudio 可直接导入的单元 JSON。"""
    sentences = parse_lrc(Path(args.lrc))
    exercises = []
    for s in sentences[: args.max_items]:
        words = [w.strip(".,!?;:\"'") for w in s["text"].split() if len(w.strip(".,!?;:\"'")) >= 4]
        blank = words[-1] if words else "answer"
        template = s["text"].replace(blank, "____", 1) if blank in s["text"] else f"{s['text']} ____"
        exercises.append(
            {
                "id": f"imp-{s['idx']}",
                "type": "cloze",
                "prompt": f"精听第 {s['idx']} 句并补全关键词（{s['start_ms'] // 1000}s）",
                "audioText": s["text"],
                "audioUrl": args.audio_url,
                "startMs": s["start_ms"],
                "endMs": s["end_ms"],
                "zhText": "（本地导入真题，可按需补充译文）",
                "keywords": words[:3],
                "template": template,
                "blanks": [blank],
                "tip": "点击播放原句核对连读与弱读细节。",
                "errorTag": "真题精听",
            }
        )

    return {
        "id": f"local-{args.level}-{Path(args.lrc).stem}",
        "channel": "cet",
        "cetLevel": args.level,
        "cetSection": "news" if args.level == "cet4" else "lecture",
        "channelLabel": f"{args.level.upper()} · 本地真题",
        "level": "本地导入",
        "title": args.title,
        "subtitle": f"共 {len(exercises)} 个精听分句 · 来自 {Path(args.lrc).name}",
        "duration": f"{max(1, len(exercises) // 2)} 分钟",
        "xp": 35,
        "accent": "真题原音",
        "progress": 0,
        "exercises": exercises,
    }


async def synthesize_json_tts(input_path: Path, out_dir: Path, voice: str) -> None:
    """调用 edge_tts 为关卡 JSON 中的每道题合成真实 MP3 音频。"""
    import edge_tts

    out_dir.mkdir(parents=True, exist_ok=True)
    data = json.loads(input_path.read_text(encoding="utf-8"))
    units = data if isinstance(data, list) else [data]

    for unit in units:
        for ex in unit.get("exercises", []):
            text = ex.get("audioText")
            if not text:
                continue
            filename = f"{unit['id']}_{ex['id']}.mp3"
            target = out_dir / filename
            communicate = edge_tts.Communicate(text, voice=voice)
            await communicate.save(str(target))
            ex["audioUrl"] = f"/audio/listening/{filename}"
            print(f"已合成: {target}")

    output_json = input_path.with_stem(f"{input_path.stem}_with_audio")
    output_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已输出带音频路径的关卡包: {output_json}")


def main() -> None:
    parser = argparse.ArgumentParser(description="EchoTalk 四六级与听力资源导入工具")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_lrc = sub.add_parser("lrc", help="从 LRC 字幕生成关卡 JSON")
    p_lrc.add_argument("--lrc", required=True, help="LRC 字幕文件路径")
    p_lrc.add_argument("--audio-url", default="", help="对应的 MP3 访问路径或本地 URL")
    p_lrc.add_argument("--level", choices=["cet4", "cet6"], default="cet4")
    p_lrc.add_argument("--title", default="本地四六级真题精听")
    p_lrc.add_argument("--max-items", type=int, default=15)
    p_lrc.add_argument("--out", required=True, help="输出 JSON 路径")

    p_tts = sub.add_parser("tts", help="用 Edge-TTS 为关卡 JSON 批量合成 MP3")
    p_tts.add_argument("--input", required=True, help="输入关卡 JSON 路径")
    p_tts.add_argument("--out-dir", default="frontend/public/audio/listening")
    p_tts.add_argument("--voice", default="en-US-JennyNeural")

    args = parser.parse_args()
    if args.cmd == "lrc":
        unit = build_unit_from_lrc(args)
        Path(args.out).write_text(json.dumps(unit, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已生成真题关卡包: {args.out}（{len(unit['exercises'])} 题）")
    elif args.cmd == "tts":
        asyncio.run(synthesize_json_tts(Path(args.input), Path(args.out_dir), args.voice))


if __name__ == "__main__":
    main()
