# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.1] - 2026-04-05

### Fixed
- **3 bugs found by live broker testing:**
  - `cache keys`: sync/async mismatch — `cacher.keys()` is sync
  - `destroy`: use `registry.__services__` fallback (broker has no `destroyService` yet)
  - `load`: use `broker.register()` (broker has no `addLocalService`)

## [0.3.0] - 2026-04-05

### Added
- **9 new REPL commands** (PRD-004: REPL to Production)
  - `bench <action>` — benchmark action performance (req/sec, min/avg/max latency)
  - `cache keys/clear` — cache management (list keys, clear by pattern)
  - `cls` — clear terminal screen
  - `destroy <service>` — destroy a local service at runtime
  - `env` — display environment variables
  - `listener add/remove/list` — subscribe to events and print live
  - `load <path>` — load service from .py file at runtime
  - `metrics [-f pattern]` — display collected metrics
  - `quit` / `exit` — graceful broker stop and exit
- Total commands: 18 (was 10) — 95%+ parity with Node.js moleculer-repl (19 commands)
- Python-unique commands: `dcall` (direct call), `loglevel` (runtime log level)

## [0.14.1] - 2026-02-11

### Added
- Interactive REPL console with 10 built-in commands
- Tab completion for actions, events, services, nodes
- Multi-worker runner with CLI entry point
- Commands: actions, call, dcall, emit, events, nodes, services
- Colored output and table formatting

### Known Issues
- Beta status (88% complete)
- Missing commands: bench, cache, metrics, load, destroy
- dcall.py coverage at 67% (target: 90%)
