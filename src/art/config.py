"""Site settings, read from site.toml in the project root."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, fields
from pathlib import Path


class ConfigError(Exception):
    pass


@dataclass
class SiteConfig:
    title: str = "Gord Bond"
    tagline: str = "Paintings"
    domain: str = ""
    show_prices: bool = False
    currency: str = "$"
    contact_email: str = ""
    agh_url: str = ""


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
    return SiteConfig(**data)
