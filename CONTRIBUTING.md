# Contributing to MoleculerPy REPL

Thank you for your interest in contributing!

## Development Setup

```bash
git clone https://github.com/MoleculerPy/moleculer-repl.git
cd moleculer-repl
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Workflow

1. Fork the repository
2. Create a feature branch from `dev`: `git checkout -b feat/my-feature`
3. Write code + tests (every new function needs a test)
4. Run: `pytest && mypy moleculerpy_repl/ && ruff check .`
5. Commit: `git commit -m "feat(command): description"`
6. Push and create PR to `dev` branch

## Commit Format

```
type(scope): description

Types: feat, fix, docs, test, refactor, chore
Scopes: repl, runner, commands, completion
```

## Rules

- Merge commit, not squash
- `git add file1 file2` — never `git add .`
- All public functions must have type hints and tests
- Minimum 80% coverage for new code
