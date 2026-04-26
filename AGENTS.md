# AGENTS

## Scope

This file guides coding agents working anywhere in this repository.

## Project Facts

- Home Assistant custom integration lives in `custom_components/comfoclime/`.
- Canonical project repository is `https://github.com/Revilo91/comfoclime`.
- The integration targets Home Assistant `2026.2.0+` and Python `3.14+`.
- Package and integration versions must stay aligned between `pyproject.toml` and `custom_components/comfoclime/manifest.json`.

## Default Workflow

1. Read `custom_components/comfoclime/AGENTS.md` before changing integration code.
2. Read `docs/AGENTS.md` before changing repository documentation.
3. Install tooling with `uv sync --group dev`.
4. Run focused tests first, then broader validation if the change touches shared paths.

## Required Checks

- Python tests: `uv run pytest tests/ -v`
- Lint: `uv run ruff check .`
- Format check: `uv run ruff format --check .`

## Guardrails

- Keep async API code fully awaitable; do not introduce blocking I/O.
- Update or add tests for every behavior or metadata change.
- Keep HACS metadata, README installation guidance, and GitHub workflow behavior in sync.