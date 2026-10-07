# 0001: Markdown files plus a small Python CLI

- Status: accepted
- Date: 2026-10-07

## Context

I want measurable progress without maintaining a product. A React dashboard, database or backend
would become a second project and compete with the actual learning.

## Decision

Store everything as Markdown with YAML front matter. Use one Python package (stdlib + PyYAML)
to validate files, compute metrics and rewrite a marked block in `README.md`. GitHub Actions runs
the same command on push.

## Consequences

- Positive: diffable history, offline editing, no hosting, easy to test pure functions.
- Negative: no UI beyond rendered Markdown; schema changes need a small migration.
- Revisit if the data outgrows what a few hundred small files can answer.
