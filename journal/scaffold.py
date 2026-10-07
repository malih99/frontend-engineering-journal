"""Create new files from templates and generate review skeletons."""

from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path

from journal import metrics
from journal.metrics import Snapshot
from journal.render import fmt_minutes, week_table


def _fill(template: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    return template


def _yaml_str(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:60].strip("-") or "mistake"


def new_daily(snap: Snapshot, day: date) -> tuple[Path, bool]:
    root = snap.cfg.root
    target = root / "daily" / f"{day.isoformat()}.md"
    if target.exists():
        return target, False
    active = next((t.title for p in snap.phases for t in p.topics if t.status == "active"), "")
    text = _fill(
        (root / "templates" / "daily.md").read_text(encoding="utf-8"),
        {"date": day.isoformat(), "weekday": day.strftime("%A"), "focus": _yaml_str(active)},
    )
    target.write_text(text, encoding="utf-8")
    return target, True


def new_mistake(snap: Snapshot, title: str, area: str, day: date) -> tuple[Path, bool]:
    root = snap.cfg.root
    target = root / "mistakes" / f"{day.isoformat()}-{slugify(title)}.md"
    if target.exists():
        return target, False
    text = _fill(
        (root / "templates" / "mistake.md").read_text(encoding="utf-8"),
        {"date": day.isoformat(), "title": _yaml_str(title), "area": area},
    )
    target.write_text(text, encoding="utf-8")
    return target, True


_WEEK_PROMPTS = """
## Reflection

### What did I understand better?

### What still feels weak?

### What will I change next week?

## Next week

1.
2.
3.
"""


def new_week_review(snap: Snapshot, start: date) -> tuple[Path, bool]:
    root = snap.cfg.root
    target = root / "reviews" / "weekly" / f"{start.isoformat()}.md"
    if target.exists():
        return target, False
    w = metrics.week_stats(start, snap)
    text = (
        f"# Week {w.plan_week} review: {w.start} to {w.end}\n\n"
        f"## Numbers\n\n{week_table(w)}\n{_WEEK_PROMPTS}"
    )
    target.write_text(text, encoding="utf-8")
    return target, True


def new_phase_review(snap: Snapshot, number: int) -> tuple[Path, bool]:
    cfg, root = snap.cfg, snap.cfg.root
    phase = snap.phases[number - 1]
    target = root / "reviews" / "phase" / f"phase-{number}.md"
    if target.exists():
        return target, False
    first, _ = metrics.week_window(phase.first_week, cfg)
    _, last = metrics.week_window(phase.last_week, cfg)
    weeks = [w for w in metrics.all_weeks(snap) if first <= w.start <= last]
    minutes = sum(w.total_minutes for w in weeks)
    valid = sum(w.valid_days for w in weeks)
    expected = sum(w.expected_days for w in weeks)
    done = sum(w.tasks_done for w in weeks)
    total = sum(w.tasks_total for w in weeks)
    topics = "\n".join(
        f"- [{'x' if t.status == 'closed' else ' '}] {t.title}" for t in phase.topics
    )
    text = (
        f"# Phase {number} review: {phase.title}\n\n"
        f"Weeks {phase.first_week} to {phase.last_week} ({first} to {last})\n\n"
        f"## Numbers\n\n"
        f"- Active days: {valid} / {expected}\n"
        f"- Focused time: {fmt_minutes(minutes)}\n"
        f"- Tasks done: {done} / {total}\n"
        f"- Topics closed: {phase.closed} / {len(phase.topics)}\n\n"
        f"## Topics\n\n{topics}\n\n"
        "## Closing check\n\n"
        "For every topic still open: explain it in two minutes, implement it from scratch, "
        "show three real examples, answer the review questions. Carry over only what fails.\n\n"
        "## Before and after\n\n"
        "- Before this phase I could not:\n- After this phase I can:\n"
        f"{_WEEK_PROMPTS}"
    )
    target.write_text(text, encoding="utf-8")
    return target, True


def previous_week_start(snap: Snapshot) -> date:
    return metrics.week_start(snap.today, snap.cfg) - timedelta(weeks=1)
