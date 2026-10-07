from datetime import date
from pathlib import Path

from journal import metrics
from journal.models import Daily
from tests.conftest import make_snapshot


def day(d: date, coding=60, study=30, english=30, typing=15, learned="x", ai=None, excused=False):
    return Daily(
        date=d,
        focus="",
        minutes={"coding": coding, "study": study, "english": english, "typing": typing},
        ai=ai,
        energy=None,
        learned=learned,
        excused=excused,
        typing_wpm=None,
        typing_accuracy=None,
        tasks_done=2,
        tasks_total=3,
        path=Path(f"{d}.md"),
    )


def test_week_starts_on_saturday_and_plan_week_is_one_based(cfg):
    assert metrics.week_start(date(2026, 10, 7), cfg) == date(2026, 10, 3)  # Wednesday -> Saturday
    assert metrics.plan_week(date(2026, 10, 7), cfg) == 1
    assert metrics.plan_week(date(2026, 10, 10), cfg) == 2
    assert metrics.plan_week(date(2026, 10, 1), cfg) == 0


def test_levels(cfg):
    assert metrics.level(day(date(2026, 10, 7)), cfg) == "excellent"
    assert (
        metrics.level(day(date(2026, 10, 7), coding=30, study=0, english=0, typing=15), cfg)
        == "minimum"
    )
    assert (
        metrics.level(day(date(2026, 10, 7), coding=20, study=0, english=0, typing=0), cfg)
        == "partial"
    )
    assert metrics.level(day(date(2026, 10, 7), coding=5, study=5), cfg) is None
    assert metrics.level(day(date(2026, 10, 7), learned=""), cfg) is None


def test_hours_beyond_target_do_not_raise_level(cfg):
    big = day(date(2026, 10, 7), coding=300, study=0, english=0, typing=0)
    assert metrics.level(big, cfg) == "minimum"  # 60/135 capped -> 44%


def test_streak_ignores_rest_days_and_today(cfg):
    # Sat 10 Oct to Wed 14 Oct valid; Fri 9 Oct is a rest day; Thu 15 Oct has no entry yet.
    days = [day(date(2026, 10, n)) for n in (7, 8, 10, 11, 12, 13, 14)]
    snap = make_snapshot(cfg, date(2026, 10, 15), days)
    assert metrics.streaks(snap) == (7, 7)


def test_streak_breaks_on_a_missed_day_but_not_an_excused_one(cfg):
    base = [day(date(2026, 10, n)) for n in (7, 8, 10)]  # Oct 11 missing
    snap = make_snapshot(cfg, date(2026, 10, 13), [*base, day(date(2026, 10, 12))])
    assert metrics.streaks(snap) == (1, 3)
    excused = [*base, day(date(2026, 10, 11), excused=True, learned=""), day(date(2026, 10, 12))]
    assert metrics.streaks(make_snapshot(cfg, date(2026, 10, 13), excused)) == (4, 4)


def test_independence_uses_weights(cfg):
    days = [day(date(2026, 10, 7), ai="independent"), day(date(2026, 10, 8), ai="explained")]
    assert metrics.independence(days, cfg) == (1.0 + 0.4) / 2
    assert metrics.independence([day(date(2026, 10, 7))], cfg) is None


def test_insight_flags_drop_without_blame(cfg):
    heavy = [day(date(2026, 10, n)) for n in (10, 11, 12, 13)]  # full week 2
    light = [day(date(2026, 10, 17), coding=20, study=0, english=0, typing=0)]  # week 3
    snap = make_snapshot(cfg, date(2026, 10, 25), [*heavy, *light])
    notes = metrics.insights(snap)
    assert any("lower" in n and "overworking" in n for n in notes)
    assert not any("fail" in n.lower() for n in notes)
