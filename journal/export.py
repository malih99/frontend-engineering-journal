"""Build the generated JSON the dashboard renders. Markdown stays the source of truth."""

from __future__ import annotations

import json
import re
from datetime import timedelta
from pathlib import Path

from journal import metrics
from journal.metrics import Snapshot
from journal.models import ACTIVITIES, AI_LEVELS

_H1 = re.compile(r"^#\s+(.*\S)\s*$", re.M)
_SECTION_KEYS = {"Built or solved": "built", "Stuck on": "stuck", "Notes": "notes"}


def _title(path: Path) -> str:
    match = _H1.search(path.read_text(encoding="utf-8"))
    return match.group(1) if match else path.stem.replace("-", " ").title()


def _url(snap: Snapshot, rel: str) -> str | None:
    cfg = snap.cfg
    return f"{cfg.repository}/blob/{cfg.branch}/{rel}" if cfg.repository else None


def _files(snap: Snapshot, folder: str) -> list[Path]:
    directory = snap.cfg.root / folder
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.glob("*.md") if not p.name.startswith(("_", "README")))


def _day(d, cfg) -> dict:
    return {
        "date": d.date.isoformat(),
        "weekday": d.date.strftime("%A"),
        "focus": d.focus,
        "minutes": d.minutes,
        "total": d.total_minutes,
        "level": metrics.level(d, cfg),
        "valid": metrics.is_valid(d, cfg),
        "excused": d.excused,
        "ai": d.ai,
        "energy": d.energy,
        "learned": d.learned,
        "typingWpm": d.typing_wpm,
        "typingAccuracy": d.typing_accuracy,
        "tasks": [{"done": done, "text": text} for done, text in d.tasks],
        "sections": {key: d.sections.get(heading, "") for heading, key in _SECTION_KEYS.items()},
    }


def _week(w) -> dict:
    return {
        "start": w.start.isoformat(),
        "end": w.end.isoformat(),
        "planWeek": w.plan_week,
        "complete": w.complete,
        "validDays": w.valid_days,
        "expectedDays": w.expected_days,
        "minutes": w.minutes,
        "total": w.total_minutes,
        "completion": w.completion,
        "independence": w.independence,
        "mistakesFound": w.mistakes_found,
        "mistakesResolved": w.mistakes_resolved,
    }


def build_export(snap: Snapshot) -> dict:
    cfg, today = snap.cfg, snap.today
    by_date = snap.by_date
    current, longest = metrics.streaks(snap)
    phase = metrics.current_phase(snap)
    closed, topics = metrics.topics_closed(snap)
    summary = metrics.mistake_summary(snap)
    typing = metrics.typing_progress(snap)
    recent = [d for d in snap.dailies if today - timedelta(days=6) <= d.date <= today]
    tasks_total = sum(d.tasks_total for d in recent)
    ai_counts = {k: sum(d.ai == k for d in snap.dailies) for k in AI_LEVELS}
    samples = [(d.date, d.typing_wpm, d.typing_accuracy) for d in snap.dailies if d.typing_wpm]
    samples += [(a.date, a.typing_wpm, a.typing_accuracy) for a in snap.assessments if a.typing_wpm]
    phase_of_note = {p.note: p.id for p in snap.phases if p.note}

    return {
        "meta": {
            "title": "Frontend Engineering Journal",
            "today": today.isoformat(),
            "lastEntry": (max(d.date for d in snap.dailies).isoformat() if snap.dailies else None),
            "week": max(metrics.plan_week(today, cfg), 1),
            "weeks": metrics.plan_week(cfg.end, cfg),
            "targets": {
                "dailyMinutes": cfg.daily_targets,
                "typingWpm": cfg.typing_wpm_target,
                "typingAccuracy": cfg.typing_accuracy_target,
            },
            "restDays": sorted(cfg.rest_days),
        },
        "today": _day(by_date[today], cfg) if today in by_date else None,
        "daily": [_day(d, cfg) for d in snap.dailies],
        "weeks": [_week(w) for w in metrics.all_weeks(snap)],
        "signals": {
            "streak": {"current": current, "longest": longest},
            "focusedMinutes": sum(d.total_minutes for d in snap.dailies),
            "taskCompletion": (
                sum(d.tasks_done for d in recent) / tasks_total if tasks_total else None
            ),
            "aiIndependence": metrics.independence(recent, cfg),
            "aiCounts": ai_counts,
            "typing": {**typing, "target": cfg.typing_wpm_target},
            "mistakes": {
                "found": summary["found"],
                "resolved": summary["resolved"],
                "open": summary["found"] - summary["resolved"],
            },
            "topics": {"closed": closed, "total": topics},
        },
        "series": {
            "focused": [
                {
                    "date": (today - timedelta(days=i)).isoformat(),
                    "minutes": by_date[today - timedelta(days=i)].total_minutes
                    if (today - timedelta(days=i)) in by_date
                    else 0,
                }
                for i in range(27, -1, -1)
            ],
            "typing": [
                {"date": d.isoformat(), "wpm": wpm, "accuracy": acc}
                for d, wpm, acc in sorted(samples, key=lambda s: s[0])
            ],
        },
        "roadmap": [
            {
                "id": p.id,
                "title": p.title,
                "firstWeek": p.first_week,
                "lastWeek": p.last_week,
                "current": p is phase,
                "closed": p.closed,
                "total": len(p.topics),
                "topics": [{"id": t.id, "title": t.title, "status": t.status} for t in p.topics],
            }
            for p in snap.phases
        ],
        "knowledge": [
            {
                "id": f.stem,
                "title": _title(f),
                "path": f"knowledge/{f.name}",
                "url": _url(snap, f"knowledge/{f.name}"),
                "phase": phase_of_note.get(f.stem),
            }
            for f in _files(snap, "knowledge")
        ],
        "mistakes": [
            {
                "date": m.date.isoformat(),
                "title": m.title,
                "area": m.area,
                "status": m.status,
                "resolvedOn": m.resolved_on.isoformat() if m.resolved_on else None,
                "aiHelp": m.ai_help,
                "recurred": m.recurred,
                "url": _url(snap, f"mistakes/{m.path.name}"),
                "sections": {k: v for k, v in m.sections.items() if v},
            }
            for m in sorted(snap.mistakes, key=lambda m: m.date, reverse=True)
        ],
        "reviews": {
            kind: [
                {
                    "name": f.stem,
                    "title": _title(f),
                    "url": _url(snap, f"reviews/{kind}/{f.name}"),
                }
                for f in reversed(_files(snap, f"reviews/{kind}"))
            ]
            for kind in ("weekly", "phase")
        },
        "insights": metrics.insights(snap),
        "activities": list(ACTIVITIES),
    }


def to_json(snap: Snapshot) -> str:
    return json.dumps(build_export(snap), indent=2, ensure_ascii=False) + "\n"
