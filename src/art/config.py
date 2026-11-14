"""Site settings, read from site.toml (and the git-ignored site.local.toml) in the project root."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path


class ConfigError(Exception):
    pass


@dataclass
class Category:
    """A subfolder of paintings/ (e.g. studio, agh, prints) shown as a filter on the site."""

    key: str  # folder name; matched case-insensitively
    label: str = ""
    link: str = ""  # optional page where works in this category can be bought
    link_label: str = "View collection"

    def __post_init__(self) -> None:
        self.key = self.key.strip().lower()
        self.label = self.label or self.key.replace("_", " ").replace("-", " ").title()


@dataclass
class SizeBucket:
    """A site size filter on the longest side, in inches: over `min` (exclusive) up to `max` (inclusive)."""

    label: str
    min: float | None = None
    max: float | None = None


def _default_buckets() -> list[SizeBucket]:
    return [
        SizeBucket("Small (up to 24 in)", max=24),
        SizeBucket("Medium (over 24 to 40 in)", min=24, max=40),
        SizeBucket("Large (over 40 in)", min=40),
    ]


@dataclass
class SiteConfig:
    title: str = "Gord Bond"
    tagline: str = "Paintings"
    domain: str = ""
    show_prices: bool = False
    currency: str = "$"
    contact_email: str = ""
    logo: str = ""  # image path relative to the project folder; blank shows the title as text
    logo_width: int = 260  # displayed width in px
    about: str = ""  # Markdown file for the About page (bio, statement); blank = no About page
    about_photo: str = ""  # optional photo for the About page
    category_label: str = "Location"  # what to call categories in the CLI and filter bar
    categories: list[Category] = field(default_factory=list)  # blank: use the folders in paintings/
    size_buckets: list[SizeBucket] = field(default_factory=_default_buckets)

    def category(self, key: str) -> Category:
        return next((c for c in self.categories if c.key == key), Category(key))


def load_config(root: Path) -> SiteConfig:
    """site.toml is committed; site.local.toml (git-ignored) overrides it, e.g. for a private email."""
    known = {f.name for f in fields(SiteConfig)}
    data: dict = {}
    for name in ("site.toml", "site.local.toml"):
        path = root / name
        if not path.exists():
            continue
        try:
            part = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            raise ConfigError(f"{path}: {exc}") from exc
        unknown = sorted(set(part) - known)
        if unknown:
            raise ConfigError(f"{path}: unknown setting(s): {', '.join(unknown)}")
        data |= part

    try:
        data["categories"] = [Category(**c) for c in data.get("categories", [])]
        if "size_buckets" in data:
            data["size_buckets"] = [SizeBucket(**b) for b in data["size_buckets"]]
        config = SiteConfig(**data)
    except TypeError as exc:
        raise ConfigError(f"site.toml: bad [[categories]] or [[size_buckets]] entry ({exc})") from exc

    if not config.categories:
        base = root / "paintings"
        if base.is_dir():
            config.categories = [Category(d.name) for d in sorted(base.iterdir())
                                 if d.is_dir() and not d.name.startswith(".")]
    keys = [c.key for c in config.categories]
    if len(keys) != len(set(keys)):
        raise ConfigError("site.toml: duplicate category key in [[categories]]")
    for setting in ("logo", "about", "about_photo"):
        value = getattr(config, setting)
        if value and not (root / value).is_file():
            raise ConfigError(f"site.toml: {setting} file not found: {root / value}")
    return config
