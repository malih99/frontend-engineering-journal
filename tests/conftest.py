from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from journal.config import Config, load_config
from journal.metrics import Snapshot

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def cfg() -> Config:
    return load_config(REPO)


def make_snapshot(cfg: Config, today: date, dailies=(), mistakes=(), assessments=(), phases=()):
    return Snapshot(cfg, today, tuple(dailies), tuple(mistakes), tuple(assessments), tuple(phases))
