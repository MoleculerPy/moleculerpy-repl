# MoleculerPy REPL — Interactive CLI

**Interactive console for MoleculerPy microservices.**

**Depends on**: `moleculerpy>=0.14.1`
**Status**: Beta (88% complete, 7.5/10)

## Quick Start

```bash
pip install -e ".[dev]"
pytest                    # Run tests (172 tests, 88% coverage)
mypy src/moleculerpy_repl/  # Type check
ruff check .             # Lint
```

## Architecture

| Component | File | Purpose |
|---|---|---|
| REPL | repl.py | Main REPL loop (335 LOC) |
| Runner | runner.py | Multi-worker CLI (492 LOC) |
| Commands | commands/ | 10 built-in commands |

## Available Commands

actions, bench*, cache*, call, dcall, destroy*, emit, events, load*, metrics*, nodes, services

\* = not yet implemented

## Missing Features (88% → 100%)

- Commands: `bench`, `cache`, `metrics`, `load`, `destroy`
- `broker.repl()` method in core
- `__main__.py` for standalone mode
- `dcall.py` coverage ≥ 90%

## Git Workflow

### Branches: main ← dev ← feat/*

```bash
git checkout dev && git pull origin dev
git checkout -b feat/task-name
git add file1 file2
git commit -m "feat(module): what was done"
git push origin feat/task-name -u
gh pr create --base dev
gh pr merge --merge --delete-branch=false
```

### Commits: `type(module): description`
Types: feat, fix, docs, test, refactor, chore

### Forbidden
- `git push --force`, `git reset --hard`, `git add .`
- Direct commits to main/dev

## Methodology: Route → Shape → Code → Evidence

1. **Route** — Tactical / Standard / Deep / Critical
2. **Shape** — PRD/RFC/ADR before coding (Standard+)
3. **Code** — every function = test immediately, `pytest` required
4. **Evidence** — confirm the result

## Enforcement Hooks

5 hooks in `.claude/hooks/`:

| Hook | Checks |
|---|---|
| forge-safety | Blocks dangerous commands |
| pr-todo-check | P0 checkboxes before PR |
| commit-test-check | Tests for new `def` |
| pre-code-check | Active PRD before coding |
| pre-commit-health | Blind spots |
