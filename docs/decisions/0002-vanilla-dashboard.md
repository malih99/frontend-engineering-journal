# 0002: Vanilla HTML/CSS/JS dashboard, no framework

- Status: accepted
- Date: 2026-10-10

## Context

The journal needs a readable view of its data. Building it in React would turn the tracker
into a second project and compete with the learning it measures.

## Decision

Ship a static dashboard in plain HTML, CSS and ES modules. It only renders `data.json`, which
Python generates from the Markdown source of truth. A small local server (`journal serve`)
regenerates the JSON per request. Design tokens live in CSS custom properties.

## Consequences

- Positive: no build step or dependencies, trivial to host, easy to audit for accessibility.
- Negative: manual DOM code; a larger UI would need components and tests.
- Revisit if the dashboard grows past a few hundred lines per section or needs client state.
