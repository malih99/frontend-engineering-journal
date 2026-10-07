from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

ACTIVITIES = ("coding", "study", "english", "typing")
AI_LEVELS = ("independent", "hint", "explained")
AREAS = (
    "javascript",
    "typescript",
    "react",
    "debugging",
    "architecture",
    "patterns",
    "tooling",
    "other",
)
MISTAKE_STATUS = ("open", "resolved")
TOPIC_STATUS = ("todo", "active", "closed")
ASSESSMENT_KINDS = ("baseline", "checkpoint")


class ValidationError(ValueError):
    """Raised when a journal file does not follow the documented schema."""


@dataclass(frozen=True)
class Daily:
    date: date
    focus: str
    minutes: dict[str, int]
    ai: str | None
    energy: int | None
    learned: str
    excused: bool
    typing_wpm: float | None
    typing_accuracy: float | None
    tasks_done: int
    tasks_total: int
    path: Path

    @property
    def total_minutes(self) -> int:
        return sum(self.minutes.values())


@dataclass(frozen=True)
class Mistake:
    date: date
    title: str
    area: str
    status: str
    resolved_on: date | None
    ai_help: str
    recurred: bool
    path: Path


@dataclass(frozen=True)
class Benchmark:
    name: str
    minutes: int | None
    independent: bool | None  # None = not attempted


@dataclass(frozen=True)
class Assessment:
    date: date
    kind: str
    typing_wpm: float | None
    typing_accuracy: float | None
    benchmarks: tuple[Benchmark, ...]
    path: Path

    @property
    def attempted(self) -> int:
        return sum(1 for b in self.benchmarks if b.independent is not None)

    @property
    def independent(self) -> int:
        return sum(1 for b in self.benchmarks if b.independent)


@dataclass(frozen=True)
class Topic:
    id: str
    title: str
    status: str
    closed_on: date | None = None


@dataclass(frozen=True)
class Phase:
    id: str
    title: str
    first_week: int
    last_week: int
    topics: tuple[Topic, ...] = field(default_factory=tuple)

    @property
    def closed(self) -> int:
        return sum(1 for t in self.topics if t.status == "closed")
