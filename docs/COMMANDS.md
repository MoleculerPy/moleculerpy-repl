# MoleculerPy REPL — Command Reference

## Starting REPL

### Method 1: Via Broker (like Moleculer.js)

```python
import asyncio
from moleculerpy import Broker

async def main():
    broker = Broker("node-1", transporter="nats://localhost:4222")
    await broker.start()

    # Start REPL (blocks until quit)
    await broker.repl()

asyncio.run(main())
```

### Method 2: CLI Entry Point

```bash
# Start with REPL flag
moleculerpy-runner --repl services/

# Or standalone REPL connecting to running broker
moleculerpy-repl --transporter nats://localhost:4222
```

### Method 3: Programmatic

```python
from moleculerpy_repl import REPL

repl = REPL(broker, delimiter="mol $ ")
await repl.run()
```

---

## How It Works (Moleculer.js Pattern)

```
                    CLI
                     │
                     ▼
            ┌────────────────┐
            │ moleculerpy-runner│
            │   --repl flag  │
            └───────┬────────┘
                    │
                    ▼
            ┌────────────────┐
            │     Broker     │
            │   .repl()      │──────────────┐
            └───────┬────────┘              │
                    │                       │
                    ▼                       ▼
            ┌────────────────┐     ┌────────────────┐
            │   Services     │     │ moleculerpy-repl │
            │   Running      │     │    REPL()      │
            └────────────────┘     └────────────────┘
                    │                       │
                    └───────────┬───────────┘
                                │
                                ▼
                        ┌────────────────┐
                        │  Interactive   │
                        │    Console     │
                        │   mol $ _      │
                        └────────────────┘
```

---

## Command Reference

### Information Commands

#### `help [command]`
Show help for all commands or a specific command.

```
mol $ help
Available commands:
  actions    List available actions
  services   List registered services
  ...

mol $ help call
Usage: call <action> [params...]

Call a service action.
...
```

#### `info`
Display system information.

```
mol $ info
┌────────────────────┬───────────────────────┐
│ Property           │ Value                 │
├────────────────────┼───────────────────────┤
│ Node ID            │ node-1                │
│ Moleculer Version  │ 0.14.35               │
│ Python Version     │ 3.12.0                │
│ Uptime             │ 5m 23s                │
│ Memory Usage       │ 45.2 MB               │
│ Services           │ 3                     │
│ Actions            │ 12                    │
│ Events             │ 5                     │
└────────────────────┴───────────────────────┘
```

#### `env`
Show environment variables and broker configuration.

```
mol $ env
Broker Settings:
  transporter: nats://localhost:4222
  namespace: default
  request_timeout: 30.0
  ...
```

---

### Discovery Commands

#### `services [-a]`
List registered services.

| Flag | Description |
|------|-------------|
| `-a` | Show all (including internal) |

```
mol $ services
┌──────────┬─────────┬─────────┐
│ Service  │ Version │ Actions │
├──────────┼─────────┼─────────┤
│ math     │ 1.0.0   │ 3       │
│ users    │ 2.0.0   │ 4       │
│ gateway  │ 1.0.0   │ 2       │
└──────────┴─────────┴─────────┘
```

#### `actions [-a] [--skipInternal]`
List available actions.

| Flag | Description |
|------|-------------|
| `-a` | Show all details |
| `--skipInternal` | Skip $node actions (default: true) |

```
mol $ actions
┌─────────────────────┬───────┬────────┐
│ Action              │ Nodes │ State  │
├─────────────────────┼───────┼────────┤
│ math.add            │ 1     │   OK   │
│ math.multiply       │ 1     │   OK   │
│ users.get           │ 2     │   OK   │
│ users.create        │ 2     │   OK   │
└─────────────────────┴───────┴────────┘
```

#### `nodes [-a] [--raw]`
List cluster nodes.

| Flag | Description |
|------|-------------|
| `-a` | Show all details |
| `--raw` | Output raw JSON |

```
mol $ nodes
┌──────────┬────────┬──────────┬─────────┐
│ Node ID  │ State  │ Services │ CPU     │
├──────────┼────────┼──────────┼─────────┤
│ node-1   │ online │ 2        │ ██░░░ 25%│
│ node-2   │ online │ 1        │ ███░░ 60%│
└──────────┴────────┴──────────┴─────────┘
```

#### `events [-a]`
List event subscriptions.

```
mol $ events
┌─────────────────┬───────────┬───────┐
│ Event           │ Service   │ Nodes │
├─────────────────┼───────────┼───────┤
│ user.created    │ users     │ 2     │
│ order.completed │ orders    │ 1     │
└─────────────────┴───────────┴───────┘
```

---

### Action Commands

#### `call <action> [params...]`
Call a service action.

**Syntax:**
```
call <action> [key=value...] [#meta...] [$options...]
```

| Prefix | Destination | Example |
|--------|-------------|---------|
| (none) | `params` | `a=5` |
| `#` | `meta` | `#userId=123` |
| `$` | `options` | `$timeout=5000` |

**Examples:**
```bash
# Basic call
mol $ call math.add a=5 b=3
Result: 8

# With meta
mol $ call users.get id=u1 #tenant=acme
Result: {"id": "u1", "name": "Alice"}

# With options
mol $ call slow.action $timeout=60000 $retries=3

# JSON params
mol $ call user.create --json '{"name": "Bob", "age": 30}'

# Load from file
mol $ call user.create --load user.params.json
```

#### `dcall <nodeId> <action> [params...]`
Direct call to a specific node.

```
mol $ dcall node-2 math.add a=1 b=2
Result: 3
```

#### `emit <event> [params...]`
Emit an event.

```
mol $ emit user.created name=Bob #userId=u123
Event emitted: user.created
```

#### `broadcast <event> [params...]`
Broadcast event to all nodes.

```
mol $ broadcast system.shutdown reason=maintenance
Broadcast sent: system.shutdown
```

---

### Performance Commands

#### `bench <action> [--iter N] [--time S]`
Benchmark an action.

| Option | Description | Default |
|--------|-------------|---------|
| `--iter N` | Number of iterations | 1000 |
| `--time S` | Run for N seconds | - |

```
mol $ bench math.add a=1 b=1 --iter 1000
Benchmarking math.add (1000 iterations)...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌────────────┬──────────┐
│ Metric     │ Value    │
├────────────┼──────────┤
│ Total time │ 1.234s   │
│ Avg time   │ 1.234ms  │
│ Min time   │ 0.891ms  │
│ Max time   │ 5.432ms  │
│ Req/sec    │ 810.37   │
└────────────┴──────────┘
```

---

### Cache Commands

#### `cache keys [pattern]`
List cached keys.

```
mol $ cache keys user:*
Cached keys:
  - user:u1
  - user:u2
  - user:u3
```

#### `cache clear [pattern]`
Clear cache entries.

```
mol $ cache clear user:*
Cleared 3 cache entries.

mol $ cache clear
Cleared all cache entries.
```

---

### Metrics Commands

#### `metrics [--filter pattern]`
Display metrics.

```
mol $ metrics --filter moleculer.request
┌──────────────────────────┬────────┬─────────┐
│ Metric                   │ Type   │ Value   │
├──────────────────────────┼────────┼─────────┤
│ moleculer.request.total  │ counter│ 1523    │
│ moleculer.request.active │ gauge  │ 2       │
│ moleculer.request.time   │ hist   │ 1.2ms   │
└──────────────────────────┴────────┴─────────┘
```

---

### Service Management

#### `load <path>`
Load services from file or directory.

```
mol $ load ./services/math.py
Service loaded: math

mol $ load ./services/
Loaded 3 services from ./services/
```

#### `destroy <service>`
Stop and unregister a service.

```
mol $ destroy math
Service 'math' destroyed.
```

---

### Utility Commands

#### `clear` / `cls`
Clear the terminal screen.

#### `quit` / `exit`
Exit the REPL and stop the broker.

```
mol $ quit
Stopping broker...
Goodbye! 👋
```

---

## Custom Commands

Register custom commands:

```python
from moleculerpy_repl import REPL, BaseCommand

class MyCommand(BaseCommand):
    name = "hello"
    description = "Say hello"
    usage = "hello [name]"

    async def execute(self, broker, args):
        name = args.positional[0] if args.positional else "World"
        return f"Hello, {name}!"

repl = REPL(broker, custom_commands=[MyCommand])
```

Usage:
```
mol $ hello Alice
Hello, Alice!
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Tab` | Autocomplete |
| `Ctrl+C` | Cancel current command |
| `Ctrl+D` | Exit REPL |
| `↑` / `↓` | Navigate history |
| `Ctrl+R` | Search history |
