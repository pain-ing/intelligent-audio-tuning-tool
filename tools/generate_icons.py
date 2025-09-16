#!/usr/bin/env python3
"""
Generate AudioTuner application icons (PNG multi-sizes + Windows .ico)
- Theme: audio processing + tuning + AI
- Colors: dark teal gradient with accent neon green
- Elements: waveform + tuning knob + AI spark

If a source image exists at icons/source_upload.png, it will be composited
at the lower-right corner as a small mascot accent (optional).
"""

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from pathlib import Path
import math

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "icons"
RES_DIR = ROOT / "packaging" / "desktop" / "resources"
SOURCE_UPLOAD = OUT_DIR / "source_upload.png"

SIZES = [16, 32, 48, 64, 128, 256, 512]

# Colors
BG1 = (10, 25, 30)     # dark teal
BG2 = (16, 40, 50)
ACCENT = (60, 230, 190) # neon green
ACCENT2 = (0, 210, 180)
WAVE = (180, 255, 240)
RING = (70, 190, 170)


def radial_gradient(size):
    w, h = size
    cx, cy = w/2, h/2
    max_r = math.hypot(cx, cy)
    img = Image.new('RGB', size, BG1)
    px = img.load()
    for y in range(h):
        for x in range(w):
            r = math.hypot(x-cx, y-cy) / max_r
            t = min(1.0, r*1.2)
            # ease-in gradient
            k = t*t*(3-2*t)
            r_ = int(BG1[0]*(1-k) + BG2[0]*k)
            g_ = int(BG1[1]*(1-k) + BG2[1]*k)
            b_ = int(BG1[2]*(1-k) + BG2[2]*k)
            px[x, y] = (r_, g_, b_)
    return img


def draw_waveform(draw: ImageDraw.ImageDraw, bbox):
    x0, y0, x1, y1 = bbox
    w = x1 - x0
    h = y1 - y0
    mid = (y0 + y1) / 2
    pts = []
    for i in range(64):
        t = i/(63)
        x = x0 + t*w
        # combined sin waves for a smooth waveform
        y = mid + math.sin(t*math.pi*2)*h*0.18 + math.sin(t*math.pi*6)*h*0.06
        pts.append((x, y))
    draw.line(pts, fill=WAVE, width=max(1, int(h*0.07)))
    # glow
    for r in (6, 12):
        draw.line(pts, fill=(WAVE[0], WAVE[1], WAVE[2], 40), width=max(1, int(h*0.07)+r))


def draw_knob(img: Image.Image, center, radius):
    x, y = center
    knob = Image.new('RGBA', (radius*2, radius*2), (0,0,0,0))
    d = ImageDraw.Draw(knob)
    # outer ring
    d.ellipse([2,2, radius*2-2, radius*2-2], outline=RING, width=max(2, radius//7))
    # inner disk
    d.ellipse([radius*0.35, radius*0.35, radius*1.65, radius*1.65], fill=(20,30,35,255))
    # indicator
    angle = -40
    tip_x = radius + radius*0.7*math.cos(math.radians(angle))
    tip_y = radius + radius*0.7*math.sin(math.radians(angle))
    d.line([(radius, radius), (tip_x, tip_y)], fill=ACCENT, width=max(2, radius//6))
    img.alpha_composite(knob, (int(x-radius), int(y-radius)))


def draw_ai_spark(draw: ImageDraw.ImageDraw, center, r):
    x, y = center
    draw.ellipse([x-r, y-r, x+r, y+r], outline=ACCENT, width=max(1, r//3))
    draw.ellipse([x-r*0.5, y-r*0.5, x+r*0.5, y+r*0.5], fill=ACCENT2)


def compose_base(size):
    base = radial_gradient((size, size)).convert('RGBA')
    d = ImageDraw.Draw(base, 'RGBA')
    # top-left AI spark
    draw_ai_spark(d, (int(size*0.2), int(size*0.22)), int(size*0.07))
    # central waveform
    draw_waveform(d, (int(size*0.15), int(size*0.55), int(size*0.85), int(size*0.75)))
    # tuning knob bottom-right
    draw_knob(base, (int(size*0.72), int(size*0.70)), int(size*0.18))
    return base


def overlay_mascot(img: Image.Image):
    if not SOURCE_UPLOAD.exists():
        return img
    try:
        m = Image.open(SOURCE_UPLOAD).convert('RGBA')
        # fit into corner
        w = img.width
        target_w = int(w*0.36)
        m = m.resize((target_w, int(m.height*target_w/m.width)), Image.LANCZOS)
        # slight round mask
        mask = Image.new('L', m.size, 0)
        md = ImageDraw.Draw(mask)
        md.rounded_rectangle([0,0,m.size[0], m.size[1]], radius=int(target_w*0.08), fill=200)
        m.putalpha(mask)
        img.alpha_composite(m, (w - m.width - int(w*0.06), img.height - m.height - int(w*0.06)))
    except Exception:
        pass
    return img


def ensure_dirs():
    OUT_DIR.mkdir(exist_ok=True)
    RES_DIR.mkdir(parents=True, exist_ok=True)


def main():
    ensure_dirs()
    master = compose_base(512)
    master = overlay_mascot(master)

    png_paths = []
    for s in SIZES:
        im = master.resize((s, s), Image.LANCZOS)
        path = OUT_DIR / f"AudioTuner_{s}.png"
        im.save(path, format='PNG')
        png_paths.append(path)
    # 512 copy for general use
    master.save(OUT_DIR / "AudioTuner_512.png", format='PNG')

    # ICO with multiple sizes
    ico_path = OUT_DIR / "AudioTuner.ico"
    master.save(ico_path, format='ICO', sizes=[(s, s) for s in SIZES if s <= 256])

    # copy a standard icon for Electron
    (OUT_DIR / "icon.png").write_bytes((OUT_DIR / "AudioTuner_256.png").read_bytes())
    # place into electron resources
    (RES_DIR / "icon.png").write_bytes((OUT_DIR / "AudioTuner_256.png").read_bytes())
    (RES_DIR / "icon.ico").write_bytes(ico_path.read_bytes())

    print("Generated:")
    print("-", ico_path)
    for p in png_paths:
        print("-", p)
    print("-", RES_DIR / "icon.png")
    print("-", RES_DIR / "icon.ico")

if __name__ == "__main__":
    main()

