"""Markdown rendering for the README dashboard and for terminal output."""

from __future__ import annotations

from datetime import timedelta

from journal import metrics
from journal.config import WEEKDAY_ABBR
from journal.metrics import Snapshot, WeekStats

START_MARK = "<!-- dashboard:start -->"
END_MARK = "<!-- dashboard:end -->"
_LEVEL_CHAR = {"partial": "░", "minimum": "▒", "good": "▓", "excellent": "█"}


def fmt_minutes(minutes: int) -> str:
    hours, rest = divmod(minutes, 60)
    if hours and rest:
        return f"{hours}h {rest:02d}m"
    return f"{hours}h" if hours else f"{rest}m"


def pct(value: float | None) -> str:
    return "-" if value is None else f"{value:.0%}"


def bar(fraction: float, width: int = 10) -> str:
    filled = round(max(0.0, min(1.0, fraction)) * width)
    return "█" * filled + "░" * (width - filled)


def _table(header: list[str], rows: list[list[str]], right: set[int] | None = None) -> str:
    right = right or set()
    sep = ["---:" if i in right else "---" for i in range(len(header))]
    lines = [header, sep, *rows]
    return "\n".join("| " + " | ".join(row) + " |" for row in lines)


def _status_section(snap: Snapshot) -> str:
    cfg = snap.cfg
    week = max(metrics.plan_week(snap.today, cfg), 1)
    last_week = metrics.plan_week(cfg.end, cfg)
    phase = metrics.current_phase(snap)
    current, longest = metrics.streaks(snap)
    total = sum(d.total_minutes for d in snap.dailies)
    closed, topics = metrics.topics_closed(snap)
    rows = [
        ["Program", f"Week {min(week, last_week)} of {last_week}"],
        ["Current phase", phase.title if phase else "-"],
        ["Streak", f"{current} days (longest {longest})"],
        ["Focused time", fmt_minutes(total)],
        ["Topics closed", f"{closed} / {topics}"],
    ]
    return _table(["", ""], rows)


def _weeks_section(snap: Snapshot) -> str:
    weeks = metrics.all_weeks(snap)[-6:]
    rows = []
    for w in weeks:
        label = f"W{w.plan_week}" + ("" if w.complete else " *")
        rows.append(
            [
                label,
                f"{w.valid_days} / {w.expected_days}",
                fmt_minutes(w.total_minutes),
                pct(w.completion),
                pct(w.independence),
                f"{w.mistakes_resolved} / {w.mistakes_found}",
            ]
        )
    header = ["Week", "Active days", "Focused", "Tasks done", "AI independence", "Mistakes fixed"]
    note = "\\* week in progress. AI independence is self-reported."
    return _table(header, rows, right={1, 2, 3, 4, 5}) + "\n\n" + note


def _roadmap_section(snap: Snapshot) -> str:
    rows = []
    for p in snap.phases:
        total = len(p.topics)
        frac = p.closed / total if total else 0.0
        rows.append([p.title, f"{p.closed} / {total}", f"`{bar(frac)}` {frac:.0%}"])
    return _table(["Phase", "Closed", "Progress"], rows, right={1})


def _mistakes_section(snap: Snapshot) -> str:
    s = metrics.mistake_summary(snap)
    areas = ", ".join(f"{k} {v}" for k, v in list(s["by_area"].items())[:3]) or "-"
    rows = [
        ["Documented", str(s["found"])],
        ["Resolved", f"{s['resolved']} ({pct(s['rate'])})"],
        ["Repeated", str(s["recurred"])],
        ["Most common areas", areas],
    ]
    return _table(["", ""], rows)


def _skills_section(snap: Snapshot) -> str:
    cfg = snap.cfg
    t = metrics.typing_progress(snap)
    base = next((a for a in snap.assessments if a.kind == "baseline"), None)
    latest = snap.assessments[-1] if snap.assessments else None

    def wpm(v: float | None) -> str:
        return "-" if v is None else f"{v:.0f} WPM"

    def bench(a) -> str:
        return "-" if a is None or not a.attempted else f"{a.independent} / {a.attempted}"

    rows = [
        ["Typing", wpm(t["baseline_wpm"]), wpm(t["latest_wpm"]), f"{cfg.typing_wpm_target} WPM"],
        ["Benchmarks solved without AI", bench(base), bench(latest), "-"],
    ]
    return _table(["", "Baseline", "Latest", "Target"], rows, right={1, 2, 3})


def _heatmap(snap: Snapshot, weeks: int = 12) -> str:
    cfg, by_date = snap.cfg, snap.by_date
    first = metrics.week_start(snap.today, cfg) - timedelta(weeks=weeks - 1)
    lines = []
    for row in range(7):
        label = WEEKDAY_ABBR[(cfg.week_start + row) % 7]
        cells = []
        for col in range(weeks):
            d = first + timedelta(weeks=col, days=row)
            entry = by_date.get(d)
            if d > snap.today or d < cfg.start:
                cells.append(" ")
            elif entry and (lvl := metrics.level(entry, cfg)):
                cells.append(_LEVEL_CHAR[lvl])
            elif entry and entry.excused:
                cells.append("○")
            else:
                cells.append("·")
        lines.append(f"{label}  {' '.join(cells)}")
    legend = "· none   ░ partial   ▒ minimum   ▓ good   █ excellent   ○ excused"
    return "```text\n" + "\n".join(lines) + f"\n\n{legend}\n```"


def render_dashboard(snap: Snapshot) -> str:
    last = max((d.date for d in snap.dailies), default=None)
    parts = [
        _status_section(snap),
        "#### Weekly trend\n\n" + _weeks_section(snap),
        "#### Roadmap\n\n" + _roadmap_section(snap),
        "#### Skills vs baseline\n\n" + _skills_section(snap),
        "#### Mistakes\n\n" + _mistakes_section(snap),
        "#### Last 12 weeks\n\n" + _heatmap(snap),
    ]
    achieved = metrics.milestones(snap)
    if achieved:
        parts.append("#### Milestones\n\n" + "\n".join(f"- {m}" for m in achieved))
    parts.append("#### Notes\n\n" + "\n".join(f"- {m}" for m in metrics.insights(snap)))
    parts.append(f"<sub>Last entry: {last.isoformat() if last else 'none'}</sub>")
    return "\n\n".join(parts)


def splice_readme(readme: str, block: str) -> str:
    start, end = readme.find(START_MARK), readme.find(END_MARK)
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"README.md must contain {START_MARK} and {END_MARK}")
    head = readme[: start + len(START_MARK)]
    return f"{head}\n\n{block}\n\n{readme[end:]}"


def week_table(w: WeekStats) -> str:
    rows = [
        ["Active days", f"{w.valid_days} / {w.expected_days}"],
        *[[a.capitalize(), fmt_minutes(m)] for a, m in w.minutes.items()],
        ["Focused total", fmt_minutes(w.total_minutes)],
        ["Tasks done", f"{w.tasks_done} / {w.tasks_total} ({pct(w.completion)})"],
        ["AI independence", pct(w.independence)],
        ["Mistakes fixed / documented", f"{w.mistakes_resolved} / {w.mistakes_found}"],
    ]
    return _table(["Metric", "Value"], rows, right={1})
