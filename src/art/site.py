"""Static gallery generator: resized images + a single Jinja2-rendered page."""
from __future__ import annotations

import base64
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .catalog import Catalog, Painting, format_price
from .config import SiteConfig
from .images import save_resized

HERE = Path(__file__).parent
FULL_SIDE = 1800
THUMB_SIDE = 700
ABOUT_PHOTO_SIDE = 1200

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


def _copy_logo(root: Path, config: SiteConfig, out: Path) -> dict | None:
    if not config.logo:
        return None
    from PIL import Image

    src = root / config.logo
    dest = out / "assets" / f"logo{src.suffix.lower()}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dest)
    size = (None, None) if src.suffix.lower() == ".svg" else Image.open(src).size  # SVG: let CSS size it
    return {"src": f"assets/{dest.name}", "w": size[0], "h": size[1]}


def _build_about(root: Path, config: SiteConfig, env: Environment, common: dict, out: Path) -> None:
    """Write about.html (and its photo) when `about` is set; remove them when it's switched off."""
    page, photo_file = out / "about.html", out / "assets" / "about.jpg"
    if not config.about:
        page.unlink(missing_ok=True)
        photo_file.unlink(missing_ok=True)
        return
    import markdown

    photo = None
    if config.about_photo:
        w, h = save_resized(root / config.about_photo, photo_file, ABOUT_PHOTO_SIDE)
        photo = {"src": "assets/about.jpg", "w": w, "h": h}
    else:
        photo_file.unlink(missing_ok=True)
    body = markdown.markdown((root / config.about).read_text(encoding="utf-8"))
    html = env.get_template("about.html").render(**common, page="about", about_html=body, photo=photo)
    page.write_text(html, encoding="utf-8")


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
            "category": config.category(p.location),
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

    categories = [c for c in config.categories if any(w["p"].location == c.key for w in works)]
    env = Environment(loader=FileSystemLoader(HERE / "templates"), autoescape=True)
    common = dict(
        config=config,
        contact_encoded=base64.b64encode(config.contact_email.encode()).decode() if config.contact_email else "",
        contact_fallback=config.contact_email.replace("@", " [at] ").replace(".", " [dot] "),
        logo=_copy_logo(catalog.root, config, out),
        has_about=bool(config.about),
    )
    html = env.get_template("index.html").render(
        **common,
        page="home",
        works=works,
        categories=categories,
        size_buckets=[(f"b{i}", b.label, b.min, b.max) for i, b in enumerate(config.size_buckets)],
    )
    (out / "index.html").write_text(html, encoding="utf-8")

    assets = out / "assets"
    assets.mkdir(exist_ok=True)
    _build_about(catalog.root, config, env, common, out)
    for name in ("style.css", "app.js"):
        shutil.copy(HERE / "static" / name, assets / name)

    (out / ".nojekyll").touch()
    if config.domain:
        (out / "CNAME").write_text(config.domain + "\n", encoding="utf-8")
    return BuildResult(works=len(works), rendered=rendered, removed=removed)
