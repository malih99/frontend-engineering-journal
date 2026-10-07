# Design and metric definitions

## Principles

1. **Markdown is the database.** Every record is a readable file under version control.
2. **One source of truth per fact.** Numbers live in front matter, prose lives in the body.
3. **Derived, never typed.** Dashboards, weekly numbers, streaks and trends are computed.
4. **Strict input, quiet output.** `journal validate` rejects typos; the dashboard never shames.
5. **Small on purpose.** Python standard library plus PyYAML. No framework, no database.

## Definitions

| Term | Definition |
|---|---|
| Valid day | `coding + study >= 20` minutes, a non-empty `learned` line, and not `excused`. |
| Level | Focused minutes divided by the daily target, each activity capped at its own target: partial, minimum (>= 30%), good (>= 60%), excellent (>= 85%). |
| Streak | Consecutive valid days. Rest days (see `config.yml`) and `excused` days neither count nor break it. Today never breaks it. |
| Week | Starts on the configured weekday (Saturday). Week 1 is the possibly partial week containing the start date. |
| Task completion | Checked / total checkboxes under `## Tasks` in daily files. |
| AI independence | Mean of `ai_weights` over days with an `ai` value. Self-reported; the trend matters, not the value. |
| Mistake resolved | Mistake note with `status: resolved` and `resolved_on`. |
| Topic closed | All four closing criteria in `roadmap.yml` hold. |

## What the dashboard compares

Trend notes only compare **complete** weeks, so a half-finished week is never read as a drop.

## Privacy

Do not paste employer code, internal URLs or secrets into this repository. Keep it private;
publish only what you would show in a portfolio.
