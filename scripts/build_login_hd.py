"""Refine the approved LoadX login photograph without changing its composition.

A 2x Lanczos resize alone cannot recover lost photographic detail. The mild
local edge/contrast pass improves perceived clarity and allows higher-quality
delivery than the strongly compressed 900x1000 reference.
"""
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "frontend/public/images/login-cinematic-scene.webp"
target = ROOT / "frontend/public/images/login-cinematic-scene-hd.webp"

with Image.open(source) as image:
    if image.size != (900, 1000):
        raise SystemExit(f"Source dimensions changed: {image.size}")
    image = image.convert("RGB")
    image = ImageEnhance.Contrast(image).enhance(1.055)
    image = image.resize((1800, 2000), Image.Resampling.LANCZOS)
    image = image.filter(ImageFilter.UnsharpMask(radius=1.15, percent=135, threshold=4))
    image.save(target, format="WEBP", quality=93, method=6)

if not 50000 <= target.stat().st_size <= 1500000:
    raise SystemExit("Unexpected optimized file size")

with Image.open(target) as result:
    if result.size != (1800, 2000):
        raise SystemExit(f"Unexpected output dimensions: {result.size}")

print(f"Generated {target.relative_to(ROOT)} ({target.stat().st_size} bytes)")
