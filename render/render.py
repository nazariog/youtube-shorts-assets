"""Renderiza o Short: ai-bubble-storyboard-completo.html + Audio.wav -> MP4.

Uso:
    python render.py [--frames 0-1450] [--workers 6] [--out ../ai-bubble-short.mp4]

Requer: playwright (chromium), imageio-ffmpeg (ou ffmpeg no PATH), numpy.
Etapas: prep_timeline.py -> render.py (quadros) -> mix_audio.py -> ffmpeg.
"""
import argparse
import base64
import html as htmllib
import json
import re
import shutil
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).parent.resolve()
REPO = HERE.parent
WORK = HERE.parent.parent / "work"
FRAMES = WORK / "frames"
PAGE = WORK / "page.html"


def ffmpeg_exe():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def extract_scene_code():
    """Extrai, sem alterações, o código de desenho das cenas do storyboard."""
    src = (REPO / "ai-bubble-storyboard-completo.html").read_text(encoding="utf-8")
    inner = htmllib.unescape(re.search(r'data-srcdoc="(.*?)"\s*>\s*</iframe>', src, re.S).group(1))
    a = inner.index("const C={cream:")
    b = inner.index("const scenes=[")
    return inner[a:b]


def build_page():
    WORK.mkdir(exist_ok=True)
    fonts = (HERE / "fonts").as_uri()
    engine = (HERE / "engine.js").read_text(encoding="utf-8").replace("/*SCENES*/", extract_scene_code())
    timeline = (HERE / "timeline.json").read_text(encoding="utf-8")
    PAGE.write_text(f"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:Impact;src:url({fonts}/Anton.ttf)}}
@font-face{{font-family:Anton;src:url({fonts}/Anton.ttf)}}
@font-face{{font-family:Arial;src:url({fonts}/Arimo.ttf);font-weight:100 900}}
html,body{{margin:0;background:#000}}</style></head><body>
<canvas id="c" width="1080" height="1920"></canvas>
<script>window.TIMELINE={timeline};</script>
<script>{engine}</script></body></html>""", encoding="utf-8")


def worker(args):
    start, end = args
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1920})
        page.on("pageerror", lambda e: print("PAGE ERROR:", e, file=sys.stderr))
        page.goto(PAGE.as_uri())
        page.evaluate("Promise.all([document.fonts.load('900 20px Arial'), document.fonts.load('20px Impact'), document.fonts.load('20px Anton')])")
        page.wait_for_function("window.ENGINE_READY === true", timeout=60000)
        for f in range(start, end):
            data = page.evaluate(f"renderFrame({f})")
            (FRAMES / f"{f:05d}.jpg").write_bytes(base64.b64decode(data.split(",", 1)[1]))
        browser.close()
    return end - start


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", default=None, help="intervalo a-b (b exclusivo)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", default=str(REPO / "ai-bubble-short.mp4"))
    ap.add_argument("--audio", default=str(WORK / "mixed_audio.wav"))
    ap.add_argument("--no-encode", action="store_true")
    ap.add_argument("--encode-only", action="store_true", help="só codifica os quadros já renderizados")
    a = ap.parse_args()

    tl = json.loads((HERE / "timeline.json").read_text())
    total = round(tl["duration"] * tl["fps"])  # 48.36 * 30 = 1450.8 -> 1451
    first, last = (0, total) if not a.frames else map(int, a.frames.split("-"))
    if not a.encode_only:
        build_page()
        FRAMES.mkdir(parents=True, exist_ok=True)
        step = -(-(last - first) // a.workers)
        jobs = [(s, min(s + step, last)) for s in range(first, last, step)]
        with Pool(len(jobs)) as pool:
            done = sum(pool.map(worker, jobs))
        print(f"{done} quadros renderizados")

    if a.no_encode:
        return
    cmd = [ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error",
           "-framerate", str(tl["fps"]), "-i", str(FRAMES / "%05d.jpg"), "-i", a.audio,
           "-vf", "scale=in_range=full:in_color_matrix=bt601:out_range=limited:out_color_matrix=bt709,format=yuv420p",
           "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-profile:v", "high", "-pix_fmt", "yuv420p",
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
           "-t", str(tl["duration"]), "-movflags", "+faststart", a.out]
    subprocess.run(cmd, check=True)
    print("MP4:", a.out)


if __name__ == "__main__":
    main()
