# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
