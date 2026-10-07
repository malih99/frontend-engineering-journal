# Frontend Engineering Journal

Personal learning journal for becoming a stronger Frontend Engineer.

**Goal:** practical depth in JavaScript, TypeScript, React, debugging, frontend architecture,
design patterns, live coding and problem solving, plus typing and technical English.

Daily files are plain Markdown. A small CLI validates them and derives the dashboard below.
Metric definitions and design notes: [docs/DESIGN.md](docs/DESIGN.md).

## Dashboard

<!-- dashboard:start -->

|  |  |
| --- | --- |
| Program | Week 1 of 25 |
| Current phase | JavaScript |
| Streak | 0 days (longest 0) |
| Focused time | 0m |
| Topics closed | 0 / 43 |

#### Weekly trend

| Week | Active days | Focused | Tasks done | AI independence | Mistakes fixed |
| --- | ---: | ---: | ---: | ---: | ---: |
| W1 * | 0 / 1 | 0m | - | - | 0 / 1 |

\* week in progress. AI independence is self-reported.

#### Roadmap

| Phase | Closed | Progress |
| --- | ---: | --- |
| JavaScript | 0 / 8 | `░░░░░░░░░░` 0% |
| TypeScript | 0 / 6 | `░░░░░░░░░░` 0% |
| Debugging and live coding | 0 / 7 | `░░░░░░░░░░` 0% |
| React architecture | 0 / 6 | `░░░░░░░░░░` 0% |
| Design patterns | 0 / 9 | `░░░░░░░░░░` 0% |
| Engineering project | 0 / 7 | `░░░░░░░░░░` 0% |

#### Skills vs baseline

|  | Baseline | Latest | Target |
| --- | ---: | ---: | ---: |
| Typing | - | - | 60 WPM |
| Benchmarks solved without AI | - | - | - |

#### Mistakes

|  |  |
| --- | --- |
| Documented | 1 |
| Resolved | 0 (0%) |
| Repeated | 0 |
| Most common areas | react 1 |

#### Last 12 weeks

```text
Sat                         
Sun                         
Mon                         
Tue                         
Wed                        ·
Thu                         
Fri                         

· none   ░ partial   ▒ minimum   ▓ good   █ excellent   ○ excused
```

#### Notes

- No entries yet. Run `journal new` to create today's log.

<sub>Last entry: none</sub>

<!-- dashboard:end -->

## Roadmap

Six four-week phases, tracked topic by topic in [roadmap.yml](roadmap.yml):
JavaScript, TypeScript, debugging and live coding, React architecture, design patterns,
and an engineering project. A topic is closed only when all four criteria in that file hold.

## Daily minimum

Targets live in [config.yml](config.yml). On a hard day, this is enough to keep the habit:

- 15 minutes of typing
- one 30-minute block of coding or study
- one sentence of what I learned

## AI rule

| Level | Situation | What I do |
|---|---|---|
| independent | I can solve it | Solve without AI |
| hint | I am stuck | Try for 20-30 minutes, then ask AI for a hint only |
| explained | I do not understand the concept | Ask for an explanation, close it, implement again from scratch |

Log the level in each daily file (`ai:`). The dashboard tracks the trend.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Daily workflow

```bash
git pull --rebase
journal new                       # creates daily/YYYY-MM-DD.md
# work, then fill in minutes, tasks and one "learned" line
journal mistake "Stale closure in useEffect" --area react
journal validate
git add . && git commit -m "journal: 2026-10-07" && git push
```

Pushing to `main` runs GitHub Actions, which validates the files and refreshes the dashboard.

## Weekly and phase rhythm

```bash
journal review week               # last full week, numbers pre-filled
journal review phase              # current phase, numbers pre-filled
```

Write the reflection by hand. Update `roadmap.yml` only when a topic is truly closed.

## Layout

| Path | Purpose |
|---|---|
| `daily/` | One file per day: minutes, tasks, one-line learning |
| `mistakes/` | Root-cause notes, one file per mistake |
| `knowledge/` | Distilled notes per topic |
| `reviews/` | Weekly and phase reviews |
| `assessments/` | Baseline and checkpoints (timed, no AI) |
| `roadmap.yml`, `config.yml` | Topics and status; targets and thresholds |
| `journal/`, `tests/` | The CLI and its tests |
| `templates/` | Source for new files |

## Conventions

- English for notes, comments and commits.
- Commit prefixes: `journal:`, `study:`, `debug:`, `review:`, `chore:`.
- Never commit employer code, internal URLs or secrets.

## Principle

> Learn less. Build more.
> Understand the reason behind the code, not only the syntax.
