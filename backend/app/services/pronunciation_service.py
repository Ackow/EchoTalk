"""科大讯飞 ISE 流式口语发音、语调与语速（WPM）评测服务。"""
import asyncio
import base64
import hashlib
import hmac
import io
import json
import logging
import re
import time
import wave
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlencode
from uuid import uuid4

import websockets

from app.core import config

logger = logging.getLogger("echotalk")

TMP_ASR_DIR = config.BACKEND_DIR / "storage" / "tmp_asr"
TMP_TTL_SECONDS = 900  # 15 分钟内有效，发送后即消费清理


def is_configured() -> bool:
    """检查科大讯飞 ISE 凭据是否已配置。"""
    return bool(
        config.XFYUN_APP_ID
        and config.XFYUN_API_KEY
        and config.XFYUN_API_SECRET
        and config.XFYUN_APP_ID != "mock-appid"
        and config.XFYUN_API_KEY != "mock-key"
    )


def _cleanup_expired_staged() -> None:
    if not TMP_ASR_DIR.exists():
        return
    cutoff = time.time() - TMP_TTL_SECONDS
    for meta_path in TMP_ASR_DIR.glob("*.json"):
        try:
            if meta_path.stat().st_mtime < cutoff:
                wav_path = meta_path.with_suffix(".wav")
                meta_path.unlink(missing_ok=True)
                wav_path.unlink(missing_ok=True)
        except OSError:
            pass


def stage_audio(user_id: int, wav_bytes: bytes, duration_sec: float) -> str:
    """暂存已校验的 WAV 录音，返回一次性 audio_token 供流式对话直接复用。"""
    TMP_ASR_DIR.mkdir(parents=True, exist_ok=True)
    _cleanup_expired_staged()
    token = uuid4().hex
    (TMP_ASR_DIR / f"{token}.wav").write_bytes(wav_bytes)
    (TMP_ASR_DIR / f"{token}.json").write_text(
        json.dumps({"user_id": user_id, "duration": round(float(duration_sec), 3)}),
        encoding="utf-8",
    )
    return token


def pop_staged_audio(user_id: int, token: str) -> tuple[bytes, float] | None:
    """按用户校验并取出暂存录音，同时清理临时文件。"""
    clean_token = re.sub(r"[^a-f0-9]", "", (token or "").lower())
    if not clean_token or len(clean_token) != 32:
        return None
    meta_path = TMP_ASR_DIR / f"{clean_token}.json"
    wav_path = TMP_ASR_DIR / f"{clean_token}.wav"
    if not meta_path.exists() or not wav_path.exists():
        return None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if int(meta.get("user_id", -1)) != int(user_id):
            return None
        wav_bytes = wav_path.read_bytes()
        duration = float(meta.get("duration") or 0.0)
        return wav_bytes, duration
    except Exception:
        return None
    finally:
        meta_path.unlink(missing_ok=True)
        wav_path.unlink(missing_ok=True)


def compute_speech_rate(reference_text: str, duration_sec: float | None) -> dict:
    """根据词数与录音时长计算每分钟词数（WPM）与语速档位。"""
    words = re.findall(r"[A-Za-z0-9']+", reference_text or "")
    dur = float(duration_sec or 0.0)
    if dur <= 0.2 or not words:
        return {"speech_rate_wpm": 0, "rate_level": "unknown", "duration_sec": round(dur, 2)}
    wpm = round(len(words) / (dur / 60.0))
    if wpm < 100:
        level = "slow"
    elif wpm <= 150:
        level = "natural"
    else:
        level = "fast"
    return {"speech_rate_wpm": wpm, "rate_level": level, "duration_sec": round(dur, 2)}


def _extract_pcm_and_duration(wav_bytes: bytes) -> tuple[bytes, float]:
    try:
        with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
            nframes = wav_file.getnframes()
            framerate = wav_file.getframerate() or 16000
            pcm = wav_file.readframes(nframes)
            return pcm, nframes / float(framerate)
    except Exception:
        return wav_bytes, len(wav_bytes) / 32000.0


def _parse_xfyun_xml(xml_str: str) -> dict:
    """解析科大讯飞 ISE XML 结果，提取总分、准确度、流利度、完整度、语调、连读与逐词得分。"""
    scores = {
        "total_score": 0.0,
        "accuracy_score": 0.0,
        "fluency_score": 0.0,
        "integrity_score": 0.0,
        "intonation_score": 0.0,
        "liaison_score": 0.0,
        "words": [],
    }
    try:
        root = ET.fromstring(xml_str)
        for elem in root.iter():
            if elem.tag in ("rhythm", "rhythm_score"):
                for attr_key in ("total_score", "score", "rhythm"):
                    if attr_key in elem.attrib:
                        try:
                            scores["intonation_score"] = float(elem.attrib[attr_key])
                        except ValueError:
                            pass
            for key in ("total_score", "accuracy_score", "fluency_score", "integrity_score", "rhythm", "standard_score"):
                if key in elem.attrib:
                    try:
                        val = float(elem.attrib[key])
                        if key == "rhythm":
                            scores["intonation_score"] = val
                        elif key == "standard_score":
                            if scores["intonation_score"] == 0.0:
                                scores["intonation_score"] = val
                        elif scores[key] == 0.0:
                            scores[key] = val
                    except ValueError:
                        pass

        word_map: dict[int, dict] = {}
        for idx, word_elem in enumerate(root.findall(".//word")):
            content = word_elem.attrib.get("content", "").strip()
            if not content or content.lower() in ("sil", "fil", "silv"):
                continue
            w_score = 0.0
            for attr in ("total_score", "score", "accuracy_score"):
                if attr in word_elem.attrib:
                    try:
                        val = float(word_elem.attrib[attr])
                        if val > 0:
                            w_score = val
                            break
                    except ValueError:
                        pass
            if w_score == 0.0:
                syll_scores = []
                for syll in word_elem.findall(".//syll"):
                    if "total_score" in syll.attrib:
                        try:
                            syll_scores.append(float(syll.attrib["total_score"]))
                        except ValueError:
                            pass
                if syll_scores:
                    w_score = round(sum(syll_scores) / len(syll_scores), 1)
            word_map[idx] = {"word": content, "score": w_score}

        scores["words"] = list(word_map.values())
        if scores["words"] and scores["accuracy_score"] == 0.0:
            valid = [w["score"] for w in scores["words"] if w["score"] > 0]
            if valid:
                scores["accuracy_score"] = round(sum(valid) / len(valid), 1)
        if scores["total_score"] == 0.0 and scores["accuracy_score"] > 0:
            scores["total_score"] = round(
                scores["accuracy_score"] * 0.5
                + (scores["fluency_score"] or scores["accuracy_score"]) * 0.3
                + (scores["integrity_score"] or 95.0) * 0.2,
                1,
            )

        scale_factor = 20.0 if 0.0 < scores["total_score"] <= 5.0 else 1.0
        if scale_factor != 1.0:
            for k in ("total_score", "accuracy_score", "fluency_score", "integrity_score", "intonation_score"):
                if scores[k] > 0:
                    scores[k] = round(scores[k] * scale_factor, 1)
            for w in scores["words"]:
                if 0 < w["score"] <= 5.0:
                    w["score"] = round(w["score"] * scale_factor, 1)

        if scores["intonation_score"] == 0.0 and scores["accuracy_score"] > 0:
            scores["intonation_score"] = round(scores["accuracy_score"] * 0.55 + scores["fluency_score"] * 0.45, 1)
        if scores["liaison_score"] == 0.0 and scores["accuracy_score"] > 0:
            scores["liaison_score"] = round(scores["accuracy_score"] * 0.9 + scores["fluency_score"] * 0.1, 1)
        for k in ("total_score", "accuracy_score", "fluency_score", "integrity_score", "intonation_score", "liaison_score"):
            scores[k] = round(min(100.0, max(0.0, float(scores[k]))), 1)
    except Exception as exc:
        logger.warning("解析讯飞 ISE XML 失败: %s", exc)
    return scores


def _mock_assessment(reference_text: str, duration_sec: float | None, reason: str) -> dict:
    """未配置讯飞凭据或网络异常时的降级评分（仍保留真实 WPM 语速）。"""
    words = re.findall(r"[A-Za-z0-9']+", reference_text or "")
    seed = sum(ord(ch) for ch in (reference_text or "echo"))
    acc = round(80.0 + (seed % 11), 1)
    flu = round(79.0 + ((seed >> 2) % 12), 1)
    integ = 95.0
    inton = round(78.0 + ((seed >> 3) % 13), 1)
    total = round(acc * 0.4 + flu * 0.4 + integ * 0.2, 1)
    rate_info = compute_speech_rate(reference_text, duration_sec)
    return {
        "total_score": total,
        "accuracy_score": acc,
        "fluency_score": flu,
        "integrity_score": integ,
        "intonation_score": inton,
        "liaison_score": round(acc * 0.9 + flu * 0.1, 1),
        "words": [{"word": w, "score": round(acc - 3 + ((i * 7 + seed) % 8), 1)} for i, w in enumerate(words)],
        "is_mock": True,
        "mock_reason": reason,
        **rate_info,
    }


def _build_xfyun_ws_url() -> str:
    host = "ise-api.xfyun.cn"
    path = "/v2/open-ise"
    date = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
    signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"
    signature_sha = hmac.new(
        config.XFYUN_API_SECRET.encode("utf-8"),
        signature_origin.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    signature = base64.b64encode(signature_sha).decode("utf-8")
    auth_origin = (
        f'api_key="{config.XFYUN_API_KEY}", '
        f'algorithm="hmac-sha256", '
        f'headers="host date request-line", '
        f'signature="{signature}"'
    )
    authorization = base64.b64encode(auth_origin.encode("utf-8")).decode("utf-8")
    return f"wss://{host}{path}?" + urlencode({"authorization": authorization, "date": date, "host": host})


async def assess_pronunciation(wav_bytes: bytes, reference_text: str, duration_sec: float | None = None) -> dict:
    """异步流式调用科大讯飞 ISE，返回发音/语调/逐词评分与 WPM 语速。"""
    pcm_data, detected_duration = _extract_pcm_and_duration(wav_bytes)
    dur = duration_sec if duration_sec and duration_sec > 0 else detected_duration
    rate_info = compute_speech_rate(reference_text, dur)

    if not is_configured():
        return _mock_assessment(reference_text, dur, "未配置科大讯飞 ISE 凭据")

    clean_text = (reference_text or "").strip()
    if not clean_text:
        return _mock_assessment(reference_text, dur, "待评测文本为空")

    ws_url = _build_xfyun_ws_url()
    first_frame = {
        "common": {"app_id": config.XFYUN_APP_ID},
        "business": {
            "category": "read_sentence",
            "language": "en_us",
            "rst": "entirety",
            "sub": "ise",
            "ent": "en_vip",
            "tte": "utf-8",
            "cmd": "ssb",
            "text": f"\uFEFF[content]\n{clean_text}",
            "aue": "raw",
            "auf": "audio/L16;rate=16000",
        },
        "data": {"status": 0},
    }

    try:
        result_xml = None
        async with websockets.connect(ws_url, open_timeout=10, close_timeout=3, proxy=None) as ws:
            await ws.send(json.dumps(first_frame))
            chunk_size = 1280
            total_bytes = len(pcm_data)
            offset = 0
            aus = 1

            while offset < total_bytes:
                chunk = pcm_data[offset:offset + chunk_size]
                offset += chunk_size
                is_last = offset >= total_bytes
                frame = {
                    "business": {"cmd": "auw", "aus": 4 if is_last else aus},
                    "data": {
                        "status": 2 if is_last else 1,
                        "data": base64.b64encode(chunk).decode("utf-8"),
                        "data_type": 1,
                        "encoding": "raw",
                    },
                }
                await ws.send(json.dumps(frame))
                aus = 2
                await asyncio.sleep(0.02)

            deadline = time.monotonic() + 12.0
            while time.monotonic() < deadline:
                raw_resp = await asyncio.wait_for(ws.recv(), timeout=max(0.5, deadline - time.monotonic()))
                resp = json.loads(raw_resp)
                code = resp.get("code", 0)
                if code != 0:
                    raise RuntimeError(f"ISE code={code}: {resp.get('message', '')}")
                data_node = resp.get("data") or {}
                if data_node.get("status") == 2 and data_node.get("data"):
                    result_xml = base64.b64decode(data_node["data"]).decode("utf-8", errors="ignore")
                    break

        if not result_xml:
            raise RuntimeError("ISE 未返回最终评测结果")

        parsed = _parse_xfyun_xml(result_xml)
        return {**parsed, **rate_info, "is_mock": False}
    except Exception as exc:
        logger.warning("科大讯飞 ISE 流式评测失败，已降级: %s", exc)
        return _mock_assessment(reference_text, dur, f"ISE 调用异常: {type(exc).__name__}")
