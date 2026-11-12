"""Static gallery generator: resized images + a single Jinja2-rendered page."""
from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .catalog import LOCATION_LABELS, Catalog, Painting, format_price
from .config import SiteConfig
from .images import save_resized

HERE = Path(__file__).parent
FULL_SIDE = 1800
THUMB_SIDE = 700

# (label, exclusive min, inclusive max) on the longest side, in inches.
SIZE_BUCKETS = [
    ("Small (up to 24 in)", None, 24),
    ("Medium (over 24 to 40 in)", 24, 40),
    ("Large (over 40 in)", 40, None),
]


@dataclass
class BuildResult:
    works: int
    rendered: int  # images (re)generated, vs. reused from a previous build
    removed: int


def _slug(painting: Painting) -> str:
    stem = Path(painting.file).with_suffix("").as_posix()
    return re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")


def _render(src: Path, dst: Path, side: int) -> tuple[tuple[int, int], bool]:
    """Resize src to dst unless an up-to-date copy exists. Returns (size, was_rendered)."""
    from PIL import Image

    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        with Image.open(dst) as img:
            return img.size, False
    return save_resized(src, dst, side), True


def build_site(catalog: Catalog, config: SiteConfig, out: Path, *, show_prices: bool) -> BuildResult:
    out.mkdir(parents=True, exist_ok=True)
    rendered = 0
    keep: set[Path] = set()
    works = []
    for p in catalog.paintings:
        slug = _slug(p)
        src = catalog.image_path(p)
        full_rel, thumb_rel = f"img/{slug}.jpg", f"thumb/{slug}.jpg"
        _, r1 = _render(src, out / full_rel, FULL_SIDE)
        (tw, th), r2 = _render(src, out / thumb_rel, THUMB_SIDE)
        rendered += r1 + r2
        keep |= {out / full_rel, out / thumb_rel}
        works.append({
            "p": p,
            "location_label": LOCATION_LABELS.get(p.location, p.location.upper()),
            "full": full_rel,
            "thumb": thumb_rel,
            "tw": tw,
            "th": th,
            "price": format_price(p.price, config.currency) if show_prices else "",
        })

    removed = 0
    for folder in ("img", "thumb"):
        for stale in (out / folder).glob("*"):
            if stale not in keep:
                stale.unlink()
                removed += 1

    locations = [loc for loc in LOCATION_LABELS if any(w["p"].location == loc for w in works)]
    env = Environment(loader=FileSystemLoader(HERE / "templates"), autoescape=True)
    html = env.get_template("index.html").render(
        config=config,
        works=works,
        locations=[(loc, LOCATION_LABELS[loc]) for loc in locations],
        size_buckets=[
            (f"b{i}", label, lo, hi) for i, (label, lo, hi) in enumerate(SIZE_BUCKETS)
        ],
    )
    (out / "index.html").write_text(html, encoding="utf-8")

    assets = out / "assets"
    assets.mkdir(exist_ok=True)
    for name in ("style.css", "app.js"):
        shutil.copy(HERE / "static" / name, assets / name)

    (out / ".nojekyll").touch()
    if config.domain:
        (out / "CNAME").write_text(config.domain + "\n", encoding="utf-8")
    return BuildResult(works=len(works), rendered=rendered, removed=removed)
