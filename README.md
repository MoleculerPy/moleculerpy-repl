# MoleculerPy REPL

Interactive CLI shell for [MoleculerPy](https://github.com/MoleculerPy/moleculerpy) microservices framework.

[![CI](https://github.com/MoleculerPy/moleculerpy-repl/workflows/CI/badge.svg)](https://github.com/MoleculerPy/moleculerpy-repl/actions)
[![PyPI version](https://img.shields.io/pypi/v/moleculerpy-repl.svg)](https://pypi.org/project/moleculerpy-repl/)
[![Python versions](https://img.shields.io/pypi/pyversions/moleculerpy-repl.svg)](https://pypi.org/project/moleculerpy-repl/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

---

## Features

- 🖥️ **Interactive Shell** — Command-line interface for MoleculerPy brokers
- 📞 **Call Actions** — Invoke service actions with params
- 📨 **Emit Events** — Publish events to the cluster
- 🔍 **Inspect Cluster** — List actions, services, nodes, events
- ⚡ **Tab Completion** — Autocomplete for actions, events, nodes
- 🎨 **Rich Output** — Beautiful tables and colors (optional)
- 🔧 **Extensible** — Add custom commands easily

---

## Quick Start

### Installation

```bash
cd sources/moleculerpy-repl
pip install -e .

# Optional: rich for better output
pip install rich
```

### Usage with Mock Broker

```bash
python3 examples/demo_repl.py
```

### Usage with MoleculerPy

```python
import asyncio
from moleculerpy import Broker
from moleculerpy_repl import REPL

async def main():
    broker = Broker("node-1", transporter="nats://localhost:4222")
    await broker.start()

    # Start REPL
    repl = REPL(broker)
    await repl.run()

asyncio.run(main())
```

---

## Commands

| Command | Alias | Description | Example |
|---------|-------|-------------|---------|
| `actions` | `a` | List available actions | `actions` |
| `services` | `s` | List registered services | `services` |
| `nodes` | `n` | List cluster nodes | `nodes -d` |
| `events` | `ev` | List event subscriptions | `events` |
| `info` | `i` | System information | `info` |
| `call` | `c` | Call a service action | `call math.add a=5 b=3` |
| `emit` | `e` | Emit an event | `emit user.created name=Bob` |
| `broadcast` | `b` | Broadcast event to all | `broadcast system.shutdown` |
| `help` | — | Show help | `help call` |
| `clear` | `cls` | Clear screen | `clear` |
| `quit` | `exit` | Exit REPL | `quit` |

---

## Parameter Syntax

```bash
# Basic parameters → payload
mol $ call math.add a=5 b=3

# Meta parameters (prefix #) → context metadata
mol $ emit user.created name=Bob #userId=123 #source=api

# Options (prefix $) → call options
mol $ call slow.action $timeout=30000 $retries=3

# JSON parameters
mol $ call user.create --json '{"name": "Bob", "age": 30}'

# Load from file
mol $ call user.create --load params.json

# Force string with @ prefix
mol $ call search query=@123  # "123" as string, not int
```

---

## Example Session

```
$ python3 examples/demo_repl.py

🚀 MoleculerPy REPL v0.1.0
   Node ID: demo-node
   Type 'help' for available commands.

demo $ services
Services:
Service                        Version    State      Nodes
------------------------------------------------------------
greeter                        1          OK         1
math                           1          OK         1
user                           1          OK         1

demo $ actions
Actions:
Action                                   Nodes      State
------------------------------------------------------------
greeter.hello                            1          OK
math.add                                 1          OK
math.multiply                            1          OK
user.get                                 1          OK
user.list                                1          OK

demo $ call math.add a=10 b=25
>> Response (0.00ms):
Result: 35

demo $ call user.list
>> Response (0.00ms):
[
  {"id": "u1", "name": "John"},
  {"id": "u2", "name": "Jane"}
]

demo $ emit user.created name=Charlie #userId=u4
[EVENT] user.created: {'name': 'Charlie'}
Event emitted: user.created

demo $ info
Broker Information:
----------------------------------------
  Node ID:         demo-node
  Namespace:       (none)
  Version:         0.1.0
  Protocol:        4

Transport:
----------------------------------------
  Transporter:     None
  Serializer:      JSON

Statistics:
----------------------------------------
  Services:        3
  Actions:         5
  Events:          1

demo $ quit
Goodbye! 👋
```

---

## Custom Commands

```python
from moleculerpy_repl import REPL, BaseCommand, CommandResult

class HelloCommand(BaseCommand):
    name = "hello"
    description = "Say hello"
    usage = "hello [name]"
    aliases = ["hi"]

    async def execute(self, broker, args):
        name = args.positional[0] if args.positional else "World"
        return CommandResult(
            success=True,
            output=f"Hello, {name}!"
        )

repl = REPL(broker, custom_commands=[HelloCommand])
```

---

## Architecture

```
moleculerpy-repl/
├── src/moleculerpy_repl/
│   ├── __init__.py          # Public API: REPL, BaseCommand, etc.
│   ├── repl.py              # Main REPL class (extends cmd.Cmd)
│   ├── parser.py            # Argument parser with prefix system
│   ├── output.py            # Formatter (uses rich if available)
│   └── commands/
│       ├── base.py          # BaseCommand, CommandResult, Registry
│       ├── actions.py       # `actions` command
│       ├── services.py      # `services` command
│       ├── nodes.py         # `nodes` command
│       ├── events.py        # `events` command
│       ├── info.py          # `info` command
│       ├── call.py          # `call` command
│       └── emit.py          # `emit`, `broadcast` commands
├── examples/
│   └── demo_repl.py         # Demo with mock broker
└── docs/
    ├── PLAN.md              # Implementation status
    ├── ARCHITECTURE.md
    └── COMMANDS.md
```

---

## Documentation

- [Implementation Plan](docs/PLAN.md) — Status and roadmap
- [Architecture](docs/ARCHITECTURE.md) — Design decisions
- [Command Reference](docs/COMMANDS.md) — Full command documentation

---

## Development Status

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | Core REPL module | ✅ Complete |
| Phase 2 | Discovery commands | ✅ Complete |
| Phase 3 | Action commands | ✅ Complete |
| Phase 4 | Advanced commands | ⏳ Pending |
| Phase 5 | MoleculerPy integration | ⏳ Pending |
| Phase 6 | DX polish | ✅ Partial |

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgments

Inspired by [moleculer-repl](https://github.com/moleculerjs/moleculer-repl) for Moleculer.js.
