"""Strict readers for the journal's Markdown + YAML front matter files."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import yaml

from journal.config import Config
from journal.models import (
    ACTIVITIES,
    AI_LEVELS,
    AREAS,
    ASSESSMENT_KINDS,
    MISTAKE_STATUS,
    TOPIC_STATUS,
    Assessment,
    Benchmark,
    Daily,
    Mistake,
    Phase,
    Topic,
    ValidationError,
)

_FRONT = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?(.*)\Z", re.S)
_HEADING = re.compile(r"^#{1,6}\s+")
_TASKS_HEADING = re.compile(r"^##\s+tasks\s*$", re.I)
_TASK = re.compile(r"^\s*[-*]\s+\[([ xX])\]\s+\S")
_DAILY_NAME = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")
_MISTAKE_NAME = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9][a-z0-9-]*\.md$")

_DAILY_KEYS = {
    "date", "focus", "minutes", "ai", "energy", "learned",
    "excused", "typing_wpm", "typing_accuracy",
}  # fmt: skip
_MISTAKE_KEYS = {"date", "title", "area", "status", "resolved_on", "ai_help", "recurred"}
_ASSESSMENT_KEYS = {"date", "kind", "typing_wpm", "typing_accuracy", "benchmarks"}


def split_front_matter(text: str) -> tuple[dict, str]:
    match = _FRONT.match(text)
    if not match:
        raise ValidationError("missing YAML front matter (--- block at the top)")
    try:
        data = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        raise ValidationError(f"invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ValidationError("front matter must be a mapping")
    return data, match.group(2)


def _date(value: object, key: str) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    raise ValidationError(f"'{key}' must be an ISO date (YYYY-MM-DD), got {value!r}")


def _number(value: object, key: str, lo: float, hi: float, *, integer: bool) -> float | int:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValidationError(f"'{key}' must be a number, got {value!r}")
    if integer and int(value) != value:
        raise ValidationError(f"'{key}' must be a whole number, got {value!r}")
    if not lo <= value <= hi:
        raise ValidationError(f"'{key}' must be between {lo} and {hi}, got {value}")
    return int(value) if integer else float(value)


def _optional(value: object, key: str, lo: float, hi: float, *, integer: bool = False):
    return None if value is None else _number(value, key, lo, hi, integer=integer)


def _choice(value: object, key: str, allowed: tuple[str, ...], *, optional: bool = False):
    if value is None and optional:
        return None
    if value not in allowed:
        raise ValidationError(f"'{key}' must be one of {', '.join(allowed)}; got {value!r}")
    return value


def _bool(value: object, key: str) -> bool:
    if not isinstance(value, bool):
        raise ValidationError(f"'{key}' must be true or false, got {value!r}")
    return value


def _reject_unknown(data: dict, allowed: set[str]) -> None:
    unknown = set(data) - allowed
    if unknown:
        raise ValidationError(f"unknown field(s): {', '.join(sorted(map(str, unknown)))}")


def count_tasks(body: str) -> tuple[int, int]:
    """Count checked / total task items under the '## Tasks' heading only."""
    done = total = 0
    in_tasks = False
    for line in body.splitlines():
        if _HEADING.match(line):
            in_tasks = bool(_TASKS_HEADING.match(line.strip()))
            continue
        if in_tasks and (m := _TASK.match(line)):
            total += 1
            done += m.group(1) in "xX"
    return done, total


def parse_daily(text: str, path: Path) -> Daily:
    data, body = split_front_matter(text)
    _reject_unknown(data, _DAILY_KEYS)
    day = _date(data.get("date"), "date")
    if path.stem != day.isoformat():
        raise ValidationError(f"date {day} does not match the file name")
    raw_minutes = data.get("minutes") or {}
    if not isinstance(raw_minutes, dict):
        raise ValidationError("'minutes' must be a mapping")
    _reject_unknown(raw_minutes, set(ACTIVITIES))
    minutes = {
        a: _number(raw_minutes.get(a, 0), f"minutes.{a}", 0, 720, integer=True) for a in ACTIVITIES
    }
    done, total = count_tasks(body)
    return Daily(
        date=day,
        focus=str(data.get("focus") or "").strip(),
        minutes=minutes,
        ai=_choice(data.get("ai"), "ai", AI_LEVELS, optional=True),
        energy=_optional(data.get("energy"), "energy", 1, 5, integer=True),
        learned=str(data.get("learned") or "").strip(),
        excused=_bool(data.get("excused", False), "excused"),
        typing_wpm=_optional(data.get("typing_wpm"), "typing_wpm", 1, 250),
        typing_accuracy=_optional(data.get("typing_accuracy"), "typing_accuracy", 0, 100),
        tasks_done=done,
        tasks_total=total,
        path=path,
    )


def parse_mistake(text: str, path: Path) -> Mistake:
    data, _ = split_front_matter(text)
    _reject_unknown(data, _MISTAKE_KEYS)
    status = _choice(data.get("status"), "status", MISTAKE_STATUS)
    resolved_on = data.get("resolved_on")
    if status == "resolved" and resolved_on is None:
        raise ValidationError("resolved mistakes need 'resolved_on'")
    title = str(data.get("title") or "").strip()
    if not title:
        raise ValidationError("'title' is required")
    return Mistake(
        date=_date(data.get("date"), "date"),
        title=title,
        area=_choice(data.get("area"), "area", AREAS),
        status=status,
        resolved_on=None if resolved_on is None else _date(resolved_on, "resolved_on"),
        ai_help=_choice(data.get("ai_help", "none"), "ai_help", ("none", *AI_LEVELS[1:])),
        recurred=_bool(data.get("recurred", False), "recurred"),
        path=path,
    )


def parse_assessment(text: str, path: Path) -> Assessment:
    data, _ = split_front_matter(text)
    _reject_unknown(data, _ASSESSMENT_KEYS)
    benchmarks = []
    for i, item in enumerate(data.get("benchmarks") or []):
        if not isinstance(item, dict) or "name" not in item:
            raise ValidationError(f"benchmarks[{i}] needs a 'name'")
        independent = item.get("independent")
        if independent is not None:
            independent = _bool(independent, f"benchmarks[{i}].independent")
        benchmarks.append(
            Benchmark(
                name=str(item["name"]),
                minutes=_optional(
                    item.get("minutes"), f"benchmarks[{i}].minutes", 0, 600, integer=True
                ),
                independent=independent,
            )
        )
    return Assessment(
        date=_date(data.get("date"), "date"),
        kind=_choice(data.get("kind"), "kind", ASSESSMENT_KINDS),
        typing_wpm=_optional(data.get("typing_wpm"), "typing_wpm", 1, 250),
        typing_accuracy=_optional(data.get("typing_accuracy"), "typing_accuracy", 0, 100),
        benchmarks=tuple(benchmarks),
        path=path,
    )


def parse_roadmap(text: str) -> list[Phase]:
    try:
        raw = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        raise ValidationError(f"roadmap.yml: invalid YAML: {exc}") from exc
    phases: list[Phase] = []
    seen: set[str] = set()
    for p in raw.get("phases", []):
        topics = []
        for t in p.get("topics", []):
            if t["id"] in seen:
                raise ValidationError(f"roadmap.yml: duplicate topic id {t['id']!r}")
            seen.add(t["id"])
            status = _choice(t.get("status", "todo"), f"topic {t['id']} status", TOPIC_STATUS)
            closed_on = t.get("closed_on")
            if status == "closed" and closed_on is None:
                raise ValidationError(f"roadmap.yml: closed topic {t['id']!r} needs 'closed_on'")
            topics.append(
                Topic(
                    id=t["id"],
                    title=t["title"],
                    status=status,
                    closed_on=None if closed_on is None else _date(closed_on, "closed_on"),
                )
            )
        first, last = p["weeks"]
        phases.append(Phase(p["id"], p["title"], int(first), int(last), tuple(topics)))
    return phases


def _load(directory: Path, pattern: re.Pattern, parser, errors: list[str], root: Path) -> list:
    items = []
    if not directory.is_dir():
        return items
    for path in sorted(directory.glob("*.md")):
        if path.name.startswith(("_", "README")):
            continue
        rel = path.relative_to(root)
        if not pattern.match(path.name):
            errors.append(f"{rel}: unexpected file name")
            continue
        try:
            items.append(parser(path.read_text(encoding="utf-8"), path))
        except ValidationError as exc:
            errors.append(f"{rel}: {exc}")
    return items


def load_dailies(cfg: Config, errors: list[str]) -> list[Daily]:
    return _load(cfg.root / "daily", _DAILY_NAME, parse_daily, errors, cfg.root)


def load_mistakes(cfg: Config, errors: list[str]) -> list[Mistake]:
    return _load(cfg.root / "mistakes", _MISTAKE_NAME, parse_mistake, errors, cfg.root)


def load_assessments(cfg: Config, errors: list[str]) -> list[Assessment]:
    pattern = re.compile(r"^\d{4}-\d{2}-[a-z0-9-]+\.md$")
    found = _load(cfg.root / "assessments", pattern, parse_assessment, errors, cfg.root)
    return sorted(found, key=lambda a: a.date)


def load_roadmap(cfg: Config, errors: list[str]) -> list[Phase]:
    path = cfg.root / "roadmap.yml"
    if not path.is_file():
        return []
    try:
        return parse_roadmap(path.read_text(encoding="utf-8"))
    except (ValidationError, KeyError, TypeError, ValueError) as exc:
        errors.append(f"roadmap.yml: {exc}")
        return []
