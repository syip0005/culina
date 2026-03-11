---
name: lint-and-format
description: Lints and formats the codebase using `uv run ruff`.
---

Lint and format.

Begin by linting:
1. `uv run ruff check --fix`
2. If you encounter errors, fix them or ask for input if they require a design decision.

Then:
3. `uv run ruff format`