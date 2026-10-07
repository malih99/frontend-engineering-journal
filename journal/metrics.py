"""Pure functions that turn parsed journal data into numbers. No I/O here."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from journal.config import Config
from journal.models import ACTIVITIES, Assessment, Daily, Mistake, Phase


@dataclass(frozen=True)
class Snapshot:
    cfg: Config
    today: date
    dailies: tuple[Daily, ...]
    mistakes: tuple[Mistake, ...]
    assessments: tuple[Assessment, ...]
    phases: tuple[Phase, ...]

    @property
    def by_date(self) -> dict[date, Daily]:
        return {d.date: d for d in self.dailies}


@dataclass(frozen=True)
class WeekStats:
    start: date
    end: date
    plan_week: int
    complete: bool
    valid_days: int
    expected_days: int
    minutes: dict[str, int]
    tasks_done: int
    tasks_total: int
    independence: float | None
    mistakes_found: int
    mistakes_resolved: int

    @property
    def total_minutes(self) -> int:
        return sum(self.minutes.values())

    @property
    def completion(self) -> float | None:
        return self.tasks_done / self.tasks_total if self.tasks_total else None


# ---- calendar helpers -------------------------------------------------------------------------


def week_start(d: date, cfg: Config) -> date:
    return d - timedelta(days=(d.weekday() - cfg.week_start) % 7)


def plan_week(d: date, cfg: Config) -> int:
    """1-based plan week (week 1 is the possibly partial week containing the start date)."""
    if d < cfg.start:
        return 0
    return (week_start(d, cfg) - week_start(cfg.start, cfg)).days // 7 + 1


def week_window(week: int, cfg: Config) -> tuple[date, date]:
    first = week_start(cfg.start, cfg) + timedelta(weeks=week - 1)
    return first, first + timedelta(days=6)


# ---- day level --------------------------------------------------------------------------------


def is_valid(day: Daily, cfg: Config) -> bool:
    if day.excused:
        return False
    learning = day.minutes["coding"] + day.minutes["study"]
    if learning < cfg.min_learning_minutes:
        return False
    return bool(day.learned) or not cfg.require_learned


def level(day: Daily, cfg: Config) -> str | None:
    if not is_valid(day, cfg):
        return None
    capped = sum(min(day.minutes[a], cfg.daily_targets[a]) for a in ACTIVITIES)
    ratio = capped / cfg.daily_target_total
    if ratio >= cfg.level_excellent:
        return "excellent"
    if ratio >= cfg.level_good:
        return "good"
    if ratio >= cfg.level_minimum:
        return "minimum"
    return "partial"


def streaks(snap: Snapshot) -> tuple[int, int]:
    """(current, longest). Rest days and excused days are neutral; today is never a miss yet."""
    cfg, by_date = snap.cfg, snap.by_date
    run = longest = 0
    d = cfg.start
    while d <= snap.today:
        entry = by_date.get(d)
        if entry and is_valid(entry, cfg):
            run += 1
            longest = max(longest, run)
        elif (entry and entry.excused) or d.weekday() in cfg.rest_days or d == snap.today:
            pass
        else:
            run = 0
        d += timedelta(days=1)
    return run, longest


# ---- aggregates -------------------------------------------------------------------------------


def independence(days: list[Daily], cfg: Config) -> float | None:
    scores = [cfg.ai_weights[d.ai] for d in days if d.ai]
    return sum(scores) / len(scores) if scores else None


def week_stats(start: date, snap: Snapshot) -> WeekStats:
    cfg = snap.cfg
    end = start + timedelta(days=6)
    days = [d for d in snap.dailies if start <= d.date <= end]
    window_from, window_to = max(start, cfg.start), min(end, snap.today)
    expected, cursor = 0, window_from
    while cursor <= window_to:
        expected += cursor.weekday() not in cfg.rest_days
        cursor += timedelta(days=1)
    return WeekStats(
        start=start,
        end=end,
        plan_week=plan_week(start if start >= cfg.start else cfg.start, cfg),
        complete=end < snap.today,
        valid_days=sum(is_valid(d, cfg) for d in days),
        expected_days=expected,
        minutes={a: sum(d.minutes[a] for d in days) for a in ACTIVITIES},
        tasks_done=sum(d.tasks_done for d in days),
        tasks_total=sum(d.tasks_total for d in days),
        independence=independence(days, cfg),
        mistakes_found=sum(start <= m.date <= end for m in snap.mistakes),
        mistakes_resolved=sum(
            m.resolved_on is not None and start <= m.resolved_on <= end for m in snap.mistakes
        ),
    )


def all_weeks(snap: Snapshot) -> list[WeekStats]:
    cfg = snap.cfg
    weeks, cursor = [], week_start(cfg.start, cfg)
    while cursor <= snap.today:
        weeks.append(week_stats(cursor, snap))
        cursor += timedelta(weeks=1)
    return weeks


def current_phase(snap: Snapshot) -> Phase | None:
    wk = max(plan_week(snap.today, snap.cfg), 1)
    return next((p for p in snap.phases if p.first_week <= wk <= p.last_week), None)


def topics_closed(snap: Snapshot) -> tuple[int, int]:
    topics = [t for p in snap.phases for t in p.topics]
    return sum(t.status == "closed" for t in topics), len(topics)


def mistake_summary(snap: Snapshot) -> dict[str, object]:
    found = len(snap.mistakes)
    resolved = sum(m.status == "resolved" for m in snap.mistakes)
    by_area: dict[str, int] = {}
    for m in snap.mistakes:
        by_area[m.area] = by_area.get(m.area, 0) + 1
    return {
        "found": found,
        "resolved": resolved,
        "rate": resolved / found if found else None,
        "recurred": sum(m.recurred for m in snap.mistakes),
        "by_area": dict(sorted(by_area.items(), key=lambda kv: (-kv[1], kv[0]))),
    }


def typing_progress(snap: Snapshot) -> dict[str, float | None]:
    samples = [(d.date, d.typing_wpm, d.typing_accuracy) for d in snap.dailies if d.typing_wpm]
    samples += [(a.date, a.typing_wpm, a.typing_accuracy) for a in snap.assessments if a.typing_wpm]
    samples.sort(key=lambda s: s[0])
    baseline = next((a for a in snap.assessments if a.kind == "baseline" and a.typing_wpm), None)
    first = (baseline.typing_wpm, baseline.typing_accuracy) if baseline else None
    if first is None and samples:
        first = (samples[0][1], samples[0][2])
    latest = samples[-1] if samples else None
    return {
        "baseline_wpm": first[0] if first else None,
        "latest_wpm": latest[1] if latest else None,
        "latest_accuracy": latest[2] if latest else None,
    }


# ---- feedback ---------------------------------------------------------------------------------


def insights(snap: Snapshot) -> list[str]:
    """Short, non-judgmental observations based on the last two *complete* weeks."""
    if not snap.dailies:
        return ["No entries yet. Run `journal new` to create today's log."]
    complete = [w for w in all_weeks(snap) if w.complete]
    notes: list[str] = []
    if len(complete) < 2:
        notes.append(
            "The first full week is still in progress. Consistency matters more than volume."
        )
        return notes
    prev, last = complete[-2], complete[-1]
    if prev.total_minutes and last.total_minutes < 0.6 * prev.total_minutes:
        drop = round(100 * (1 - last.total_minutes / prev.total_minutes))
        notes.append(
            f"Focused time was {drop}% lower last week. That happens. Do not compensate by "
            "overworking; return to the minimum routine (typing plus one 30-minute block)."
        )
    elif prev.total_minutes and last.total_minutes > prev.total_minutes:
        gain = round(100 * (last.total_minutes / prev.total_minutes - 1))
        notes.append(f"Focused time is up {gain}% on the previous week. Keep the pace steady.")
    if (
        last.completion is not None
        and prev.completion is not None
        and last.completion < prev.completion - 0.15
        and last.tasks_total > prev.tasks_total
    ):
        notes.append(
            f"Task completion fell while planned tasks grew ({prev.tasks_total} -> "
            f"{last.tasks_total}). Plan fewer tasks per day."
        )
    if (
        last.independence is not None
        and prev.independence is not None
        and last.independence - prev.independence >= 0.05
    ):
        notes.append(
            f"AI independence rose from {prev.independence:.0%} to {last.independence:.0%}."
        )
    return notes[:3] or ["On pace. No change needed."]


def milestones(snap: Snapshot) -> list[str]:
    cfg = snap.cfg
    _, longest = streaks(snap)
    total = sum(d.total_minutes for d in snap.dailies)
    closed, _ = topics_closed(snap)
    resolved = mistake_summary(snap)["resolved"]
    wpm = typing_progress(snap)["latest_wpm"]
    checks = [
        (longest >= 7, "7-day streak"),
        (longest >= 14, "14-day streak"),
        (longest >= 30, "30-day streak"),
        (total >= 50 * 60, "50 focused hours"),
        (total >= 100 * 60, "100 focused hours"),
        (resolved >= 10, "10 mistakes resolved with a written root cause"),
        (closed >= 5, "5 topics closed"),
        (closed >= 15, "15 topics closed"),
        (
            bool(wpm) and wpm >= cfg.typing_wpm_target,
            f"Typing target ({cfg.typing_wpm_target} WPM)",
        ),
    ]
    return [text for ok, text in checks if ok]
