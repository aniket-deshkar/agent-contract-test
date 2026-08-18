# Contributing

## Development Workflow

1. Create a focused branch from `main`.
2. Install with `python -m pip install -e ".[dev]"` in a virtual environment.
3. Add deterministic tests for contract semantics and stable check codes.
4. Run `ruff format --check .`, `ruff check .`, `pytest`, and `python -m build`.
5. Open a pull request describing compatibility and report-schema impact.

Use conventional commit subjects. Do not commit virtual environments, build distributions, provider credentials, live transcripts, or generated reports containing sensitive data.

## Compatibility

Contract and report schema changes require explicit versioning. Adapters must return only normalized `AgentRun` values and must not make normal tests depend on a real model or paid service.
