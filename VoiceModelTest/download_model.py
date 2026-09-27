#!/usr/bin/env python3
"""Download the MLX model into VoiceModelTest."""

from pathlib import Path

from huggingface_hub import snapshot_download


ROOT = Path(__file__).resolve().parent
snapshot_download(
    repo_id="mlx-community/LFM2.5-Audio-1.5B-4bit",
    local_dir=ROOT / "LFM2.5-Audio-1.5B-4bit",
    max_workers=1,
)
print("Model downloaded successfully.")
