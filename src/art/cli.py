"""Command-line entry point: art list | check | build."""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from .catalog import STATUSES, STATUS_LABELS, CatalogError, Catalog, fmt_num, filter_paintings, format_price, load_catalog
from .check import run_checks
from .config import ConfigError, SiteConfig, load_config


def _table(rows: list[list[str]], header: list[str]) -> str:
    widths = [max(len(r[i]) for r in [header, *rows]) for i in range(len(header))]
    line = lambda r: "  ".join(c.ljust(w) for c, w in zip(r, widths)).rstrip()
    return "\n".join([line(header), line(["-" * w for w in widths]), *map(line, rows)])


def _describe_filters(args: argparse.Namespace, config: SiteConfig) -> str:
    parts = []
    if args.location:
        parts.append(f"{config.category_label}: {config.category(args.location).label}")
    if args.status:
        parts.append(f"Status: {STATUS_LABELS[args.status]}")
    if args.min_size is not None:
        parts.append(f"Longest side ≥ {fmt_num(args.min_size)} in")
    if args.max_size is not None:
        parts.append(f"Longest side ≤ {fmt_num(args.max_size)} in")
    return " · ".join(parts)


def cmd_list(args: argparse.Namespace, catalog: Catalog, config: SiteConfig) -> int:
    keys = [c.key for c in config.categories]
    if args.location and args.location not in keys:
        print(f"error: unknown {config.category_label.lower()} {args.location!r} (choose from: {', '.join(keys)})",
              file=sys.stderr)
        return 2
    for problem in catalog.problems:
        print(f"warning: skipped row: {problem}", file=sys.stderr)
    shown = filter_paintings(
        catalog.paintings, location=args.location, status=args.status,
        min_size=args.min_size, max_size=args.max_size,
    )
    if not shown:
        print("No works match.")
    else:
        header = [config.category_label, "Title", "Medium", "Size", "Year", "Status"]
        if args.prices:
            header.append("Price")
        rows = []
        for p in shown:
            row = [config.category(p.location).label, p.title, p.medium, p.size_label,
                   str(p.year or ""), p.status_label]
            if args.prices:
                row.append(format_price(p.price, config.currency))
            rows.append(row)
        print(_table(rows, header))
        print(f"\n{len(shown)} work{'s' if len(shown) != 1 else ''}")

    if args.pdf:
        from .pdf import write_pdf

        out = Path(args.pdf)
        write_pdf(catalog, shown, out, config=config, subtitle=_describe_filters(args, config),
                  show_prices=args.prices)
        print(f"Wrote {out}")
    return 0


def cmd_check(args: argparse.Namespace, catalog: Catalog, config: SiteConfig) -> int:
    findings = run_checks(catalog, config)
    for f in findings:
        print(f"{f.level.upper():7}  {f.message}")
    errors = sum(f.level == "error" for f in findings)
    warnings = len(findings) - errors
    if findings:
        print()
    print(f"{len(catalog.paintings)} works checked: {errors} error(s), {warnings} warning(s)")
    return 1 if errors else 0


def cmd_build(args: argparse.Namespace, catalog: Catalog, config: SiteConfig) -> int:
    from .site import build_site

    out = args.root / args.out
    if args.clean and out.exists():
        shutil.rmtree(out)
    show_prices = config.show_prices if args.prices is None else args.prices
    result = build_site(catalog, config, out, show_prices=show_prices)
    print(f"Built {result.works} works into {out}/ "
          f"({result.rendered} images resized, {result.removed} stale removed; "
          f"prices {'shown' if show_prices else 'hidden'})")
    return 0


def cmd_deploy(args: argparse.Namespace, catalog: Catalog, config: SiteConfig) -> int:
    from .deploy import DeployError, deploy

    cmd_build(argparse.Namespace(out="dist", clean=True, prices=None, root=args.root), catalog, config)
    try:
        remote = deploy(args.root, args.root / "dist")
    except DeployError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Pushed dist/ to the gh-pages branch of {remote}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="art", description="Manage the painting inventory.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="project folder containing paintings/ (default: current directory)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="list paintings, optionally filtered")
    p_list.add_argument("--location", "--category", dest="location", type=str.lower, metavar="NAME",
                        help="only works in this category folder, e.g. studio (see site.toml)")
    p_list.add_argument("--status", type=str.lower, choices=STATUSES)
    p_list.add_argument("--min-size", type=float, metavar="IN", help="longest side at least IN inches")
    p_list.add_argument("--max-size", type=float, metavar="IN", help="longest side at most IN inches")
    p_list.add_argument("--prices", action="store_true", help="include prices")
    p_list.add_argument("--pdf", nargs="?", const="art-catalog.pdf", metavar="FILE",
                        help="also write the filtered list as a PDF with thumbnails (default: art-catalog.pdf)")
    p_list.set_defaults(func=cmd_list)

    p_check = sub.add_parser("check", help="flag mismatches between images and catalog.csv")
    p_check.set_defaults(func=cmd_check)

    p_build = sub.add_parser("build", help="generate the static gallery site")
    p_build.add_argument("--out", default="dist", help="output folder (default: dist)")
    p_build.add_argument("--prices", action=argparse.BooleanOptionalAction, default=None,
                         help="show or hide prices (default: show_prices in site.toml)")
    p_build.add_argument("--clean", action="store_true", help="delete the output folder first")
    p_build.set_defaults(func=cmd_build)

    p_deploy = sub.add_parser("deploy", help="build, then publish dist/ to the gh-pages branch of origin")
    p_deploy.set_defaults(func=cmd_deploy)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.root)
        catalog = load_catalog(args.root)
        return args.func(args, catalog, config)
    except (CatalogError, ConfigError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
