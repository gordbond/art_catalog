"""Loading, filtering and validating paintings/catalog.csv."""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

LOCATIONS = ("studio", "agh")
LOCATION_LABELS = {"studio": "Studio", "agh": "AGH"}
STATUSES = ("available", "sold", "on_hold")
STATUS_LABELS = {"available": "Available", "sold": "Sold", "on_hold": "On hold"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
COLUMNS = ("file", "title", "medium", "width_in", "height_in", "year", "status", "price")


class CatalogError(Exception):
    pass


def fmt_num(value: float) -> str:
    return f"{value:g}"


@dataclass(frozen=True)
class Painting:
    file: str  # path relative to paintings/, e.g. "studio/baseball.JPG"
    title: str
    medium: str
    width_in: float
    height_in: float
    year: int | None
    status: str
    price: float | None

    @property
    def location(self) -> str:
        return self.file.split("/", 1)[0].lower()

    @property
    def longest(self) -> float:
        return max(self.width_in, self.height_in)

    @property
    def status_label(self) -> str:
        return STATUS_LABELS.get(self.status, self.status)

    @property
    def size_label(self) -> str:
        return f"{fmt_num(self.width_in)} × {fmt_num(self.height_in)} in"


@dataclass
class Catalog:
    root: Path
    paintings: list[Painting] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)  # rows that couldn't be loaded

    @property
    def paintings_dir(self) -> Path:
        return self.root / "paintings"

    def image_path(self, painting: Painting) -> Path:
        return self.paintings_dir / painting.file


def _number(raw: str, name: str, *, required: bool) -> float | None:
    raw = raw.strip().replace("$", "").replace(",", "")
    if not raw:
        if required:
            raise ValueError(f"{name} is empty")
        return None
    try:
        value = float(raw)
    except ValueError:
        raise ValueError(f"{name} is not a number: {raw!r}") from None
    if value < 0 or (required and value == 0):
        raise ValueError(f"{name} must be positive: {raw!r}")
    return value


def load_catalog(root: Path) -> Catalog:
    csv_path = root / "paintings" / "catalog.csv"
    if not csv_path.exists():
        raise CatalogError(f"{csv_path} not found (run from the project root or pass --root)")

    catalog = Catalog(root=root)
    seen: set[str] = set()
    with csv_path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise CatalogError(f"{csv_path}: missing column(s): {', '.join(missing)}")
        for lineno, row in enumerate(reader, start=2):
            row = {k: (v or "").strip() for k, v in row.items() if k}
            if not any(row.values()):
                continue
            where = f"catalog.csv line {lineno}"
            file = row["file"].replace("\\", "/")
            if not file:
                catalog.problems.append(f"{where}: 'file' is empty")
                continue
            if file in seen:
                catalog.problems.append(f"{where}: duplicate entry for {file}")
                continue
            try:
                width = _number(row["width_in"], "width_in", required=True)
                height = _number(row["height_in"], "height_in", required=True)
                year = _number(row["year"], "year", required=False)
                price = _number(row["price"], "price", required=False)
            except ValueError as exc:
                catalog.problems.append(f"{where} ({file}): {exc}")
                continue
            seen.add(file)
            catalog.paintings.append(
                Painting(
                    file=file,
                    title=row["title"] or Path(file).stem,
                    medium=row["medium"],
                    width_in=width,
                    height_in=height,
                    year=int(year) if year else None,
                    status=row["status"],
                    price=price,
                )
            )
    catalog.paintings.sort(key=lambda p: (p.location, p.title.casefold()))
    return catalog


def filter_paintings(
    paintings: list[Painting],
    *,
    location: str | None = None,
    status: str | None = None,
    min_size: float | None = None,
    max_size: float | None = None,
) -> list[Painting]:
    """Size bounds are inclusive and apply to the longest side."""
    out = []
    for p in paintings:
        if location and p.location != location.casefold():
            continue
        if status and p.status != status:
            continue
        if min_size is not None and p.longest < min_size:
            continue
        if max_size is not None and p.longest > max_size:
            continue
        out.append(p)
    return out


def format_price(price: float | None, currency: str = "$") -> str:
    if price is None:
        return ""
    return f"{currency}{price:,.0f}" if price == int(price) else f"{currency}{price:,.2f}"
