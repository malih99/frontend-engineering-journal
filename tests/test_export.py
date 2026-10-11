import json
import shutil
from datetime import date
from pathlib import Path

import pytest

from journal import export, parse, scaffold
from journal.cli import build_snapshot
from journal.config import load_config
from journal.models import ValidationError
from tests.conftest import REPO

DAY = """---
date: 2026-10-08
focus: "Scope and closure"
minutes: {coding: 45, study: 30, english: 30, typing: 15}
ai: independent
learned: "Closures capture bindings."
---

## Tasks

- [x] Understand closures
- [ ] Write explanation

## Built or solved

Counter with a closure.

## Stuck on

<!-- guidance that must not leak into the data -->

## Notes
"""

MISTAKE = """---
date: 2026-10-08
title: "Stale closure"
area: react
status: resolved
resolved_on: 2026-10-09
---

# Stale closure

## Problem

<!-- hidden -->
The effect read an old value.

## Root cause

Wrong mental model of closures.
"""


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    for name in ("config.yml", "roadmap.yml"):
        shutil.copy(REPO / name, tmp_path / name)
    shutil.copytree(REPO / "templates", tmp_path / "templates")
    for folder in ("daily", "mistakes", "knowledge", "reviews/weekly", "reviews/phase"):
        (tmp_path / folder).mkdir(parents=True)
    (tmp_path / "daily" / "2026-10-08.md").write_text(DAY, encoding="utf-8")
    (tmp_path / "mistakes" / "2026-10-08-stale-closure.md").write_text(MISTAKE, encoding="utf-8")
    (tmp_path / "knowledge" / "javascript.md").write_text("# JavaScript\n", encoding="utf-8")
    return tmp_path


def snapshot(root: Path):
    snap, errors = build_snapshot(load_config(root), today=date(2026, 10, 8))
    assert errors == []
    return snap


def test_export_has_the_shape_the_dashboard_reads(repo):
    data = export.build_export(snapshot(repo))
    assert data["today"]["focus"] == "Scope and closure"
    assert data["today"]["tasks"] == [
        {"done": True, "text": "Understand closures"},
        {"done": False, "text": "Write explanation"},
    ]
    assert data["today"]["sections"]["built"] == "Counter with a closure."
    assert data["today"]["sections"]["stuck"] == ""  # HTML comments are stripped
    assert data["signals"]["mistakes"] == {"found": 1, "resolved": 1, "open": 0}
    assert data["mistakes"][0]["sections"] == {
        "Problem": "The effect read an old value.",
        "Root cause": "Wrong mental model of closures.",
    }
    assert data["knowledge"][0]["phase"] == "javascript"
    assert data["knowledge"][0]["url"].endswith("/blob/main/knowledge/javascript.md")
    assert len(data["series"]["focused"]) == 28
    json.dumps(data)  # must be serialisable


def test_export_is_deterministic(repo):
    snap = snapshot(repo)
    assert export.to_json(snap) == export.to_json(snap)


def test_empty_daily_file_gets_a_helpful_error(tmp_path):
    with pytest.raises(ValidationError, match="file is empty"):
        parse.parse_daily("", tmp_path / "2026-10-08.md")


def test_new_regenerates_an_empty_daily_file_but_never_overwrites_content(repo):
    snap = snapshot(repo)
    path = repo / "daily" / "2026-10-09.md"
    path.write_text("", encoding="utf-8")
    created_path, created = scaffold.new_daily(snap, date(2026, 10, 9))
    assert created and created_path.read_text(encoding="utf-8").startswith("---")
    _, created_again = scaffold.new_daily(snap, date(2026, 10, 9))
    assert not created_again


def test_cli_new_repairs_an_empty_daily_file(repo, monkeypatch, capsys):
    from journal import cli

    (repo / "daily" / "2026-10-09.md").write_text("", encoding="utf-8")
    monkeypatch.chdir(repo)
    assert cli.main(["new", "--date", "2026-10-09"]) == 0
    assert (repo / "daily" / "2026-10-09.md").read_text(encoding="utf-8").startswith("---")
    assert cli.main(["validate"]) == 0
    assert "warning" in capsys.readouterr().err
