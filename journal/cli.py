from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from journal import metrics, parse, render, scaffold
from journal.config import Config, find_root, load_config
from journal.metrics import Snapshot
from journal.models import AREAS, ValidationError


def build_snapshot(cfg: Config, today: date | None = None) -> tuple[Snapshot, list[str]]:
    errors: list[str] = []
    snap = Snapshot(
        cfg=cfg,
        today=today or cfg.today(),
        dailies=tuple(parse.load_dailies(cfg, errors)),
        mistakes=tuple(parse.load_mistakes(cfg, errors)),
        assessments=tuple(parse.load_assessments(cfg, errors)),
        phases=tuple(parse.load_roadmap(cfg, errors)),
    )
    return snap, errors


def _report(errors: list[str]) -> int:
    for message in errors:
        print(f"error: {message}", file=sys.stderr)
    return 1


def _iso(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("use YYYY-MM-DD") from exc


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="journal", description="Frontend engineering journal CLI")
    sub = p.add_subparsers(dest="command", required=True)

    new = sub.add_parser("new", help="create today's daily log")
    new.add_argument("--date", type=_iso, help="defaults to today (program timezone)")

    mistake = sub.add_parser("mistake", help="document a mistake (root-cause note)")
    mistake.add_argument("title")
    mistake.add_argument("--area", choices=AREAS, default="other")
    mistake.add_argument("--date", type=_iso)

    review = sub.add_parser("review", help="generate a review skeleton with the numbers filled in")
    review.add_argument("kind", choices=("week", "phase"))
    review.add_argument("--week-start", type=_iso, help="week reviews: defaults to last full week")
    review.add_argument("--phase", type=int, help="phase reviews: 1-based phase number")

    sub.add_parser("validate", help="check every file against the schema")
    sub.add_parser("stats", help="print the dashboard to the terminal")
    sub.add_parser("update", help="rewrite the dashboard block in README.md")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        cfg = load_config(find_root())
    except (FileNotFoundError, ValidationError) as exc:
        return _report([str(exc)])
    snap, errors = build_snapshot(cfg)

    if args.command == "validate":
        if errors:
            return _report(errors)
        print(
            f"ok: {len(snap.dailies)} daily, {len(snap.mistakes)} mistakes, "
            f"{len(snap.assessments)} assessments"
        )
        return 0

    if errors:  # never compute on top of broken data
        return _report(errors)

    if args.command == "new":
        path, created = scaffold.new_daily(snap, args.date or snap.today)
    elif args.command == "mistake":
        path, created = scaffold.new_mistake(snap, args.title, args.area, args.date or snap.today)
    elif args.command == "review":
        if args.kind == "week":
            start = args.week_start or scaffold.previous_week_start(snap)
            path, created = scaffold.new_week_review(snap, metrics.week_start(start, cfg))
        else:
            current = metrics.current_phase(snap)
            default = snap.phases.index(current) + 1 if current else 1
            number = args.phase or default
            if not 1 <= number <= len(snap.phases):
                return _report([f"phase must be between 1 and {len(snap.phases)}"])
            path, created = scaffold.new_phase_review(snap, number)
    elif args.command == "stats":
        print(render.render_dashboard(snap))
        return 0
    else:  # update
        readme = Path(cfg.root / "README.md")
        try:
            updated = render.splice_readme(
                readme.read_text(encoding="utf-8"), render.render_dashboard(snap)
            )
        except ValueError as exc:
            return _report([str(exc)])
        if updated != readme.read_text(encoding="utf-8"):
            readme.write_text(updated, encoding="utf-8")
            print("README.md updated")
        else:
            print("README.md already up to date")
        return 0

    rel = path.relative_to(cfg.root)
    print(f"{'created' if created else 'already exists'}: {rel}")
    return 0
