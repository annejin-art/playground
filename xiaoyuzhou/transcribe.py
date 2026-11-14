#!/usr/bin/env python3
"""用 faster-whisper 转写音频为带时间戳的逐字稿。
用法: python3 transcribe.py <音频> <输出txt> [模型=small]
"""
import subprocess, sys
import numpy as np
from faster_whisper import WhisperModel

audio, out = sys.argv[1], sys.argv[2]
model = sys.argv[3] if len(sys.argv) > 3 else "small"
# 用 ffmpeg 解码为 16k 单声道 float32（绕开 PyAV 版本兼容问题）
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", audio, "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                     check=True, capture_output=True).stdout
audio = np.frombuffer(raw, dtype=np.float32)
m = WhisperModel(model, device="cpu", compute_type="int8")
segs, info = m.transcribe(audio, language="zh", vad_filter=True,
                          initial_prompt="以下是普通话播客的逐字稿，使用简体中文。")
with open(out, "w") as f:
    for s in segs:
        t = int(s.start)
        f.write(f"[{t//3600:02d}:{t%3600//60:02d}:{t%60:02d}] {s.text.strip()}\n")
        f.flush()
print("done", info.duration)
