"""Pillow helpers shared by the PDF export, the checker and the site build."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps


def open_upright(path: Path) -> Image.Image:
    """Open an image as RGB with EXIF rotation applied and transparency flattened onto white."""
    img = ImageOps.exif_transpose(Image.open(path))
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        flat = Image.new("RGB", img.size, "white")
        flat.paste(img, mask=img.getchannel("A"))
        return flat
    return img.convert("RGB")


def upright_size(path: Path) -> tuple[int, int]:
    """Pixel size as displayed, without decoding the whole image."""
    with Image.open(path) as img:
        w, h = img.size
        if img.getexif().get(0x0112) in (5, 6, 7, 8):
            w, h = h, w
    return w, h


def save_resized(src: Path, dst: Path, max_side: int, quality: int = 85) -> tuple[int, int]:
    img = open_upright(src)
    img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst, "JPEG", quality=quality, optimize=True, progressive=True)
    return img.size


def jpeg_bytes(src: Path, max_side: int, quality: int = 80) -> tuple[bytes, tuple[int, int]]:
    img = open_upright(src)
    img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    buf = BytesIO()
    img.save(buf, "JPEG", quality=quality)
    return buf.getvalue(), img.size
