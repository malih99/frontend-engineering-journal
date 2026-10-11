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

## Web dashboard

```text
daily/*.md, mistakes/*.md, roadmap.yml, ...   source of truth (Markdown + YAML)
        |  journal/parse.py  (strict validation)
        v
journal/metrics.py + journal/export.py        pure functions, tested
        |
        v
data.json  (generated, git-ignored)  ->  dashboard/ (HTML + CSS + vanilla JS, view only)
```

- `journal serve` generates `/data.json` on every request, so a refresh shows your latest edits
  and a broken file produces a readable error instead of wrong numbers.
- `journal export` writes the same JSON to `dashboard/data.json` for static hosting or CI checks.
- The page is one document with section navigation. No router, no framework, no build step.
- Values from the data are inserted as text, never as HTML.

### Design rules

| Area | Rule |
|---|---|
| Color | One accent (`#2563EB`). Status colors only on badges and fills; text uses darker variants to keep contrast above 4.5:1. |
| Type | Inter / IBM Plex Sans, JetBrains Mono for code. Sizes: 26 / 17 / 14 / 13 / 12 px. |
| Space | Tokens `--space-1..8` (4 to 32 px), radii 4 and 8 px. |
| Structure | Dividers and whitespace first; panels only where grouping helps. No shadows, gradients or animation beyond 120 ms hover and focus transitions. |
| Accessibility | Semantic landmarks, skip link, visible focus, real buttons, charts with a text summary and a data table, `prefers-reduced-motion`. |
| Scope | Light theme only. Responsive: single column under 800 px; charts and tables scroll inside their own container. |

### What the dashboard deliberately leaves out

- A composite daily score. Self-rated, weighted scores look precise but are not; the dashboard
  shows measured minutes, task completion and an explicit consistency level instead.
- Streak decoration, levels, XP. The streak is one row of text.
- Reading or editing notes. Notes stay in Markdown; the page links to them.

### Windows used by the signals

| Signal | Window |
|---|---|
| Task completion, AI independence | Rolling last 7 days |
| AI usage distribution | All logged days |
| Typing | Latest sample (daily file or assessment) |
| Weekly trend | Last 8 weeks; the current week is marked in progress |
