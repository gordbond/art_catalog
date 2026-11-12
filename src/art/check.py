"""Cross-check paintings/ images against catalog.csv."""
from __future__ import annotations

from dataclasses import dataclass

from .catalog import IMAGE_EXTS, LOCATIONS, STATUSES, Catalog
from .images import upright_size

ASPECT_TOLERANCE = 0.10  # photos are rarely cropped exactly to the canvas


@dataclass(frozen=True)
class Finding:
    level: str  # "error" or "warning"
    message: str


def _disk_images(catalog: Catalog) -> dict[str, str]:
    """Map of file key (posix path under paintings/) -> same key."""
    base = catalog.paintings_dir
    found = {}
    if base.is_dir():
        for path in base.rglob("*"):
            rel = path.relative_to(base)
            if path.is_file() and path.suffix.lower() in IMAGE_EXTS and not any(
                part.startswith(".") for part in rel.parts
            ):
                found[rel.as_posix()] = rel.as_posix()
    return found


def run_checks(catalog: Catalog) -> list[Finding]:
    findings = [Finding("error", msg) for msg in catalog.problems]
    on_disk = _disk_images(catalog)
    by_lower = {k.lower(): k for k in on_disk}
    listed = {p.file for p in catalog.paintings}
    case_matched: set[str] = set()

    for p in catalog.paintings:
        if p.location not in LOCATIONS:
            findings.append(Finding("error", f"{p.file}: must be under {' or '.join(l + '/' for l in LOCATIONS)}"))
        if p.file not in on_disk:
            actual = by_lower.get(p.file.lower())
            if actual:
                case_matched.add(actual)
                findings.append(Finding(
                    "error", f"{p.file}: filename case differs from disk ({actual}); "
                    "this breaks on GitHub's case-sensitive servers"))
            else:
                findings.append(Finding("error", f"{p.file}: in CSV but no image on disk"))
            continue
        if p.status not in STATUSES:
            findings.append(Finding(
                "error", f"{p.file}: status {p.status!r} must be one of {', '.join(STATUSES)}"))
        try:
            iw, ih = upright_size(catalog.image_path(p))
        except Exception as exc:  # corrupt or unreadable image
            findings.append(Finding("error", f"{p.file}: cannot read image ({exc})"))
            continue
        csv_ratio, img_ratio = p.width_in / p.height_in, iw / ih
        if abs(img_ratio / csv_ratio - 1) > ASPECT_TOLERANCE:
            findings.append(Finding(
                "warning",
                f"{p.file}: image is {iw}×{ih}px (ratio {img_ratio:.2f}) but CSV size is "
                f"{p.size_label} (ratio {csv_ratio:.2f}); width/height swapped?"))

    for key in sorted(on_disk):
        if key in listed or key in case_matched:
            continue
        if key.split("/", 1)[0].lower() not in LOCATIONS or "/" not in key:
            findings.append(Finding("warning", f"{key}: image is outside studio/ and agh/, ignored"))
        else:
            findings.append(Finding("error", f"{key}: image on disk but not in CSV"))
    return findings
