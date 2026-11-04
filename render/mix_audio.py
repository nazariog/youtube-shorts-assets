"""Mixa a narração original com efeitos sonoros discretos.

- Narração: Audio.wav, sem processamento além de reamostrar para 48 kHz.
- "Whoosh" em cada transição de cena e batida grave (~55 Hz, abaixo da voz)
  nas palavras de impacto. Ambos ficam bem abaixo do nível da voz.
Duração de saída = duração exata da narração (48,36 s).
"""
import json
import subprocess
import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent.resolve()
REPO = HERE.parent
WORK = REPO.parent / "work"
SR = 48000
PRE = 0.30  # igual a engine.js


def ffmpeg_exe():
    import shutil
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def read_wav(path):
    with wave.open(str(path)) as w:
        assert w.getnchannels() == 1 and w.getsampwidth() == 2
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768, w.getframerate()


def whoosh(dur=0.55, seed=1):
    n = int(dur * SR)
    rng = np.random.default_rng(seed)
    noise = rng.standard_normal(n)
    x = np.linspace(0, 1, n)
    # filtro passa-baixa com corte subindo e depois descendo (varredura)
    cutoff = 400 + 5200 * np.sin(np.pi * x) ** 1.5
    alpha = 1 - np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty(n)
    s1 = s2 = 0.0
    for i in range(n):
        s1 += alpha[i] * (noise[i] - s1)
        s2 += alpha[i] * (s1 - s2)
        y[i] = s2
    env = np.sin(np.pi * x) ** 2
    y *= env
    return y / (np.max(np.abs(y)) + 1e-9)


def thump(dur=0.45):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 42 + 40 * np.exp(-t * 18)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) * np.exp(-t * 9) * np.minimum(1, t * 400)
    return y


def add(buf, clip, at, gain):
    i = int(at * SR)
    j = min(len(buf), i + len(clip))
    if i < len(buf):
        buf[i:j] += clip[: j - i] * gain


def main():
    tl = json.loads((HERE / "timeline.json").read_text())
    WORK.mkdir(exist_ok=True)
    tmp = WORK / "narration48.wav"
    subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(REPO / "Audio.wav"),
                    "-ar", str(SR), "-ac", "1", "-c:a", "pcm_s16le", str(tmp)], check=True)
    nar, sr = read_wav(tmp)
    assert sr == SR
    n_total = int(round(tl["duration"] * SR))
    nar = nar[:n_total] if len(nar) >= n_total else np.pad(nar, (0, n_total - len(nar)))
    peak = np.max(np.abs(nar))

    fx = np.zeros_like(nar)
    for k, b in enumerate(tl["bounds"][1:]):
        add(fx, whoosh(seed=10 + k), b - PRE - 0.08, 0.10 * peak)
    for t in tl["thumps"]:
        add(fx, thump(), t - 0.02, 0.18 * peak)

    mix = nar + fx
    m = np.max(np.abs(mix))
    if m > 0.97:  # evita clipping
        mix *= 0.97 / m
    out = WORK / "mixed_audio.wav"
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())
    print(f"narração pico={peak:.3f}  mix pico={np.max(np.abs(mix)):.3f}  dur={len(mix)/SR:.3f}s -> {out}")


if __name__ == "__main__":
    main()
