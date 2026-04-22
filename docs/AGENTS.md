# AGENTS

## Scope

This file applies to documentation under `docs/` and top-level markdown files.

## Documentation Rules

- Use the canonical repository URLs under `Revilo91/comfoclime` for issues, discussions, releases, and badges.
- Prefer `uv sync --group dev` and `uv run ...` commands over references to removed `requirements_test.txt` workflows.
- Keep release instructions consistent with the GitHub workflows in `.github/workflows/`.

## When Updating Docs

1. Check whether the same guidance appears in `README.md`, `.github/copilot-instructions.md`, and troubleshooting docs.
2. Update supporting version numbers when HACS minimums or dev dependency baselines change.
3. Avoid duplicating outdated fork URLs from feature branches or personal remotes.