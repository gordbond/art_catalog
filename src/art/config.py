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


def load_config(root: Path) -> SiteConfig:
    path = root / "site.toml"
    if not path.exists():
        return SiteConfig()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path}: {exc}") from exc
    known = {f.name for f in fields(SiteConfig)}
    unknown = sorted(set(data) - known)
    if unknown:
        raise ConfigError(f"{path}: unknown setting(s): {', '.join(unknown)}")
    return SiteConfig(**data)
