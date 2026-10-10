from pathlib import Path

import pytest

from journal.models import ValidationError
from journal.parse import count_tasks, parse_daily, parse_roadmap

BASE = """---
date: 2026-10-07
focus: Closures
minutes: {coding: 40, study: 20, english: 10, typing: 15}
ai: hint
energy: 4
learned: "Closures capture bindings, not values."
---

# Day

## Tasks

- [x] write counter
- [ ] explain scope
- [ ]

## Notes

- [x] not a task
"""


def test_parse_daily_reads_fields_and_tasks():
    day = parse_daily(BASE, Path("2026-10-07.md"))
    assert day.total_minutes == 85
    assert day.ai == "hint"
    assert (day.tasks_done, day.tasks_total) == (1, 2)


def test_count_tasks_ignores_other_sections_and_empty_boxes():
    assert count_tasks(BASE.split("---", 2)[2]) == (1, 2)


@pytest.mark.parametrize(
    "mutation, message",
    [
        (("minutes: {coding: 40", "minutes: {codng: 40"), "unknown field"),
        (("ai: hint", "ai: maybe"), "'ai' must be one of"),
        (("energy: 4", "energy: 9"), "between 1 and 5"),
        (("date: 2026-10-07", "date: 2026-10-08"), "does not match"),
    ],
)
def test_parse_daily_rejects_bad_input(mutation, message):
    with pytest.raises(ValidationError, match=message):
        parse_daily(BASE.replace(*mutation), Path("2026-10-07.md"))


def test_missing_front_matter():
    with pytest.raises(ValidationError, match="front matter"):
        parse_daily("# no front matter", Path("2026-10-07.md"))


def test_roadmap_requires_closed_on():
    text = """
phases:
  - id: a
    title: A
    weeks: [1, 4]
    topics:
      - {id: t1, title: T1, status: closed}
"""
    with pytest.raises(ValidationError, match="closed_on"):
        parse_roadmap(text)


def test_split_sections_strips_comments_and_keeps_headings():
    from journal.parse import split_sections

    body = "# Title\n\n## A\n\ntext <!-- gone -->\n\n### sub\n\n## B\n\n<!-- only comment -->\n"
    assert split_sections(body) == {"A": "text\n\n### sub", "B": ""}
