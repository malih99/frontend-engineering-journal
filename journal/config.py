from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from journal.models import ACTIVITIES, AI_LEVELS, ValidationError

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
WEEKDAY_ABBR = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


@dataclass(frozen=True)
class Config:
    root: Path
    start: date
    end: date
    timezone: str
    week_start: int  # Python weekday index (Mon=0)
    rest_days: frozenset[int]
    daily_targets: dict[str, int]
    typing_wpm_target: int
    typing_accuracy_target: int
    level_minimum: float
    level_good: float
    level_excellent: float
    min_learning_minutes: int
    require_learned: bool
    ai_weights: dict[str, float]
    repository: str | None = None
    branch: str = "main"

    @property
    def daily_target_total(self) -> int:
        return sum(self.daily_targets.values())

    def today(self) -> date:
        return datetime.now(ZoneInfo(self.timezone)).date()


def find_root(start: Path | None = None) -> Path:
    """Walk up from `start` (default: cwd) until a config.yml is found."""
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "config.yml").is_file():
            return candidate
    raise FileNotFoundError("config.yml not found; run the command inside the journal repository")


def _weekday(name: str) -> int:
    try:
        return WEEKDAYS.index(str(name).lower())
    except ValueError as exc:
        raise ValidationError(f"config: unknown weekday {name!r}") from exc


def _date(value: object, key: str) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValidationError(f"config: {key} must be YYYY-MM-DD") from exc


def load_config(root: Path) -> Config:
    raw = yaml.safe_load((root / "config.yml").read_text(encoding="utf-8")) or {}
    try:
        program, targets = raw["program"], raw["targets"]
        levels, valid = raw["levels"], raw["valid_day"]
        daily = {a: int(targets["daily_minutes"][a]) for a in ACTIVITIES}
        weights = {k: float(raw["ai_weights"][k]) for k in AI_LEVELS}
        cfg = Config(
            root=root,
            start=_date(program["start"], "program.start"),
            end=_date(program["end"], "program.end"),
            timezone=str(program.get("timezone", "UTC")),
            week_start=_weekday(program.get("week_starts_on", "monday")),
            rest_days=frozenset(_weekday(d) for d in program.get("rest_days", [])),
            daily_targets=daily,
            typing_wpm_target=int(targets["typing_wpm"]),
            typing_accuracy_target=int(targets["typing_accuracy"]),
            level_minimum=float(levels["minimum"]),
            level_good=float(levels["good"]),
            level_excellent=float(levels["excellent"]),
            min_learning_minutes=int(valid["min_learning_minutes"]),
            require_learned=bool(valid["require_learned_note"]),
            ai_weights=weights,
            repository=(raw.get("links") or {}).get("repository"),
            branch=str((raw.get("links") or {}).get("branch", "main")),
        )
    except (KeyError, TypeError) as exc:
        raise ValidationError(f"config.yml is missing or has an invalid key: {exc}") from exc
    if cfg.end < cfg.start:
        raise ValidationError("config: program.end is before program.start")
    return cfg
