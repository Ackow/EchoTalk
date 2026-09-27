#!/usr/bin/env python3
"""Smoke test for the local MLX LFM2.5-Audio model.

Examples:
    python VoiceModelTest/test_lfm_audio.py --mode stt --audio dummy.mp3
    python VoiceModelTest/test_lfm_audio.py --mode tts --text "Hello from EchoTalk."
    python VoiceModelTest/test_lfm_audio.py --mode sts --audio dummy.mp3

The script intentionally uses the model files stored next to it, so it does
not contact Hugging Face during inference.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


MODEL_DIR = Path(__file__).resolve().parent / "LFM2.5-Audio-1.5B-4bit"
PROJECT_DIR = Path(__file__).resolve().parents[1]


def load_dependencies():
    try:
        import mlx.core as mx
        import numpy as np
        from mlx_audio.audio_io import read as audio_read, write as audio_write
        from mlx_audio.sts.models.lfm_audio import (
            ChatState,
            LFM2AudioModel,
            LFM2AudioProcessor,
            LFMModality,
        )
    except ImportError as exc:
        if "Metal device" in str(exc):
            raise SystemExit(
                "当前环境无法访问 Apple Metal GPU。请在可用 Metal 的 Apple Silicon macOS 环境运行此测试。"
            ) from exc
        raise SystemExit(
            "缺少模型运行依赖，请先执行：\n"
            "  python -m pip install -r VoiceModelTest/requirements.txt"
        ) from exc
    return mx, np, audio_read, audio_write, ChatState, LFM2AudioModel, LFM2AudioProcessor, LFMModality


def load_model_components(deps):
    _, _, _, _, _, model_cls, processor_cls, _ = deps
    if not MODEL_DIR.is_dir():
        raise SystemExit(
            f"模型目录不存在：{MODEL_DIR}\n"
            "请先运行：python VoiceModelTest/download_model.py"
        )
    print(f"Loading model from {MODEL_DIR} ...", flush=True)
    model = model_cls.from_pretrained(str(MODEL_DIR))
    processor = processor_cls.from_pretrained(str(MODEL_DIR))
    return model, processor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("stt", "tts", "sts"), default="stt")
    parser.add_argument("--audio", type=Path, help="输入音频；STT/STS 必填")
    parser.add_argument("--text", default="Hello from EchoTalk.", help="TTS 文本")
    parser.add_argument("--output", type=Path, default=Path("VoiceModelTest/output.wav"))
    parser.add_argument("--max-new-tokens", type=int, default=None)
    return parser


def read_audio(audio_path, audio_read, np, mx):
    if not audio_path.is_file():
        raise SystemExit(f"音频文件不存在：{audio_path}")
    audio, sample_rate = audio_read(str(audio_path))
    return mx.array(audio.astype(np.float32)), sample_rate


def run_stt(args, model, processor, deps):
    mx, np, audio_read, _, ChatState, _, _, LFMModality = deps
    if not args.audio:
        raise SystemExit("STT 模式需要 --audio 参数")
    audio, sample_rate = read_audio(args.audio, audio_read, np, mx)
    chat = ChatState(processor)
    chat.new_turn("user")
    chat.add_audio(audio, sample_rate=sample_rate)
    chat.add_text("Transcribe the audio.")
    chat.end_turn()
    chat.new_turn("assistant")

    parts = []
    kwargs = {"max_new_tokens": args.max_new_tokens or 512}
    for token, modality in model.generate_interleaved(**dict(chat), **kwargs):
        mx.eval(token)
        if modality == LFMModality.TEXT:
            text = processor.decode_text(token[None])
            parts.append(text)
            print(text, end="", flush=True)
    print()
    return "".join(parts)


def build_text_chat(processor, text, ChatState):
    chat = ChatState(processor)
    chat.new_turn("system")
    chat.add_text("Perform TTS. Use a clear English voice.")
    chat.end_turn()
    chat.new_turn("user")
    chat.add_text(text)
    chat.end_turn()
    chat.new_turn("assistant")
    return chat


def run_tts(args, model, processor, deps):
    mx, _, _, audio_write, _, _, _, LFMModality = deps
    from mlx_audio.sts.models.lfm_audio.model import AUDIO_EOS_TOKEN

    chat = build_text_chat(processor, args.text, deps[4])
    audio_codes = []
    kwargs = {"max_new_tokens": args.max_new_tokens or 2048, "temperature": 0.8}
    for token, modality in model.generate_sequential(**dict(chat), **kwargs):
        mx.eval(token)
        if modality == LFMModality.AUDIO_OUT:
            if token[0].item() == AUDIO_EOS_TOKEN:
                break
            audio_codes.append(token)
    if not audio_codes:
        raise SystemExit("模型没有生成音频 token")
    codes = mx.stack(audio_codes, axis=0)[None, :].transpose(0, 2, 1)
    waveform = processor.decode_audio(codes)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    audio_write(str(args.output), waveform[0].tolist(), model.sample_rate)
    print(f"Wrote {args.output}")


def run_sts(args, model, processor, deps):
    mx, np, audio_read, audio_write, ChatState, _, _, LFMModality = deps
    if not args.audio:
        raise SystemExit("STS 模式需要 --audio 参数")
    audio, sample_rate = read_audio(args.audio, audio_read, np, mx)
    chat = ChatState(processor)
    chat.new_turn("system")
    chat.add_text("Respond with interleaved text and audio.")
    chat.end_turn()
    chat.new_turn("user")
    chat.add_audio(audio, sample_rate=sample_rate)
    chat.end_turn()
    chat.new_turn("assistant")

    text_parts, audio_codes = [], []
    kwargs = {"max_new_tokens": args.max_new_tokens or 2048}
    for token, modality in model.generate_interleaved(**dict(chat), **kwargs):
        mx.eval(token)
        if modality == LFMModality.TEXT:
            text = processor.decode_text(token[None])
            text_parts.append(text)
            print(text, end="", flush=True)
        else:
            audio_codes.append(token)
    print()
    if audio_codes:
        codes = mx.stack(audio_codes[:-1], axis=1)[None, :]
        waveform = processor.decode_with_detokenizer(codes)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        audio_write(str(args.output), waveform[0].tolist(), 24000)
        print(f"Wrote {args.output}")
    return "".join(text_parts)


def main() -> int:
    args = build_parser().parse_args()
    deps = load_dependencies()
    model, processor = load_model_components(deps)
    if args.mode == "stt":
        run_stt(args, model, processor, deps)
    elif args.mode == "tts":
        run_tts(args, model, processor, deps)
    else:
        run_sts(args, model, processor, deps)
    print("Model test completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
