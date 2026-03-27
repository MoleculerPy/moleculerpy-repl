# MoleculerPy REPL — Architecture

## System Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              Terminal                                     │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ mol $ call math.add a=5 b=3                                        │  │
│  │ Result: 8                                                          │  │
│  │ mol $ _                                                            │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                           MoleculerPyREPL                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │   cmd.Cmd   │  │  ArgParser  │  │ Autocomplete│  │  OutputFormatter│  │
│  │  (readline) │  │  (prefix)   │  │  (readline) │  │     (rich)      │  │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘  │
│         │                │                │                   │          │
│         └────────────────┼────────────────┼───────────────────┘          │
│                          │                │                              │
│                          ▼                ▼                              │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                       Command Registry                               │ │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐    │ │
│  │  │actions│ │services│ │nodes│ │call │ │emit │ │bench │ │ ... │    │ │
│  │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘    │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                       MoleculerPy ServiceBroker                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │   Registry  │  │   Transit   │  │  Lifecycle  │  │    Services     │  │
│  │  (actions)  │  │   (NATS)    │  │  (contexts) │  │  (math, user)   │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. MoleculerPyREPL (Main Class)

**File**: `src/repl.py`

```python
class MoleculerPyREPL(cmd.Cmd):
    """
    Main REPL class that extends Python's cmd.Cmd.

    Responsibilities:
    - Manage command loop
    - Bridge async broker methods to sync cmd.Cmd
    - Handle readline for history/autocomplete
    - Delegate to command handlers
    """

    def __init__(self, broker: Broker, prompt: str = "mol $ "):
        self.broker = broker
        self.prompt = prompt
        self.loop = asyncio.get_event_loop()
        self.commands = CommandRegistry()
        self.parser = ArgParser()
        self.formatter = OutputFormatter()
```

**Key Methods:**
- `cmdloop()` — Main REPL loop (inherited from cmd.Cmd)
- `precmd(line)` — Pre-process input before execution
- `default(line)` — Handle unknown commands
- `completedefault()` — Tab completion handler
- `run_async(coro)` — Run async coroutine from sync context

### 2. AsyncBridge

**Challenge**: `cmd.Cmd` is synchronous, but MoleculerPy broker is async.

**Solution**: Use `asyncio.run()` or event loop for each command:

```python
class AsyncBridge:
    """Bridge between sync cmd.Cmd and async broker."""

    def __init__(self, loop: asyncio.AbstractEventLoop = None):
        self.loop = loop or asyncio.new_event_loop()

    def run(self, coro):
        """Run async coroutine and return result."""
        return self.loop.run_until_complete(coro)
```

**Alternative**: Use `prompt_toolkit` which is natively async.

### 3. ArgParser

**File**: `src/parser.py`

```python
@dataclass
class ParsedArgs:
    """Parsed command arguments."""
    payload: dict          # Regular params
    meta: dict             # #prefixed params
    options: dict          # $prefixed params
    flags: dict            # --flag params
    positional: list       # Positional args

class ArgParser:
    """
    Parse command arguments with prefix support.

    Syntax:
        key=value           → payload
        #key=value          → meta
        $key=value          → options
        --flag              → flags[flag] = True
        --key=value         → flags[key] = value
        --json '{...}'      → merge into payload
    """

    def parse(self, args: str) -> ParsedArgs:
        tokens = shlex.split(args)
        # ... parsing logic
```

**Prefix Routing:**

| Prefix | Destination | Example | Result |
|--------|-------------|---------|--------|
| (none) | `payload` | `a=5` | `payload["a"] = 5` |
| `#` | `meta` | `#userId=123` | `meta["userId"] = 123` |
| `$` | `options` | `$timeout=5000` | `options["timeout"] = 5000` |
| `--` | `flags` | `--verbose` | `flags["verbose"] = True` |

### 4. CommandRegistry

**File**: `src/commands/__init__.py`

```python
class CommandRegistry:
    """
    Registry for REPL commands.

    Commands are auto-discovered from src/commands/*.py
    """

    def __init__(self):
        self._commands: dict[str, BaseCommand] = {}

    def register(self, cmd: BaseCommand):
        self._commands[cmd.name] = cmd

    def get(self, name: str) -> BaseCommand | None:
        return self._commands.get(name)

    def all(self) -> list[BaseCommand]:
        return list(self._commands.values())

    def load_all(self):
        """Auto-load all commands from commands/ directory."""
        for module in discover_command_modules():
            cmd = module.create_command()
            self.register(cmd)
```

### 5. BaseCommand

**File**: `src/commands/base.py`

```python
@dataclass
class CommandResult:
    """Result of command execution."""
    success: bool
    data: Any = None
    error: str | None = None
    output: str | None = None  # Pre-formatted output

class BaseCommand(ABC):
    """
    Base class for all REPL commands.

    Each command must implement:
    - name: Command name (e.g., "call")
    - description: Short description for help
    - execute(): Main logic
    """

    name: str
    description: str
    usage: str = ""
    aliases: list[str] = field(default_factory=list)

    @abstractmethod
    async def execute(
        self,
        broker: Broker,
        args: ParsedArgs
    ) -> CommandResult:
        """Execute the command."""
        pass

    def get_completions(
        self,
        broker: Broker,
        text: str
    ) -> list[str]:
        """Return tab completion suggestions."""
        return []
```

### 6. OutputFormatter

**File**: `src/output.py`

```python
class OutputFormatter:
    """
    Format command output for terminal display.

    Uses 'rich' library for:
    - Tables
    - Colors
    - JSON pretty-printing
    - Progress bars
    """

    def __init__(self, use_colors: bool = True):
        self.console = Console() if use_colors else Console(force_terminal=False)

    def table(self, headers: list[str], rows: list[list], title: str = None):
        """Render a table."""
        table = Table(title=title)
        for h in headers:
            table.add_column(h)
        for row in rows:
            table.add_row(*row)
        self.console.print(table)

    def json(self, data: Any):
        """Pretty-print JSON."""
        self.console.print_json(data=data)

    def success(self, msg: str):
        self.console.print(f"[green]✓[/green] {msg}")

    def error(self, msg: str):
        self.console.print(f"[red]✗[/red] {msg}")
```

### 7. Autocomplete

**File**: `src/autocomplete.py`

```python
class Autocompleter:
    """
    Provide tab completion suggestions.

    Context-aware completions:
    - Empty input → command names
    - "call " → action names
    - "emit " → event names
    - "dcall " → node IDs
    """

    def __init__(self, broker: Broker, registry: CommandRegistry):
        self.broker = broker
        self.registry = registry

    def complete(self, text: str, state: int) -> str | None:
        """
        readline completer function.

        Args:
            text: Current word being typed
            state: Index of suggestion (0, 1, 2, ...)

        Returns:
            Suggestion string or None
        """
        line = readline.get_line_buffer()
        suggestions = self._get_suggestions(line, text)

        if state < len(suggestions):
            return suggestions[state]
        return None

    def _get_suggestions(self, line: str, text: str) -> list[str]:
        parts = line.split()

        # No command yet - suggest command names
        if not parts or (len(parts) == 1 and not line.endswith(" ")):
            return [c.name for c in self.registry.all()
                    if c.name.startswith(text)]

        # Have command - delegate to command's completer
        cmd_name = parts[0]
        cmd = self.registry.get(cmd_name)
        if cmd:
            return cmd.get_completions(self.broker, text)

        return []
```

---

## Command Implementation Examples

### actions.py

```python
class ActionsCommand(BaseCommand):
    name = "actions"
    description = "List available actions"
    usage = "actions [-a] [--skipInternal]"

    async def execute(self, broker: Broker, args: ParsedArgs) -> CommandResult:
        show_all = args.flags.get("a", False)
        skip_internal = args.flags.get("skipInternal", True)

        actions = broker.registry.get_action_list()

        if skip_internal:
            actions = [a for a in actions if not a["name"].startswith("$")]

        rows = []
        for action in actions:
            rows.append([
                action["name"],
                str(action.get("nodeCount", 1)),
                "OK" if action.get("available") else "N/A"
            ])

        return CommandResult(
            success=True,
            data=actions,
            output=self._format_table(rows)
        )
```

### call.py

```python
class CallCommand(BaseCommand):
    name = "call"
    description = "Call a service action"
    usage = "call <action> [params...] [#meta...] [$options...]"

    async def execute(self, broker: Broker, args: ParsedArgs) -> CommandResult:
        if not args.positional:
            return CommandResult(success=False, error="Action name required")

        action_name = args.positional[0]

        try:
            result = await broker.call(
                action_name,
                args.payload,
                meta=args.meta,
                **args.options
            )
            return CommandResult(success=True, data=result)
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def get_completions(self, broker: Broker, text: str) -> list[str]:
        """Suggest action names."""
        actions = broker.registry.get_action_list()
        return [a["name"] for a in actions if a["name"].startswith(text)]
```

---

## Async Integration Pattern

### Pattern 1: run_until_complete (Simple)

```python
class MoleculerPyREPL(cmd.Cmd):
    def __init__(self, broker):
        self.broker = broker
        self.loop = asyncio.new_event_loop()

    def do_call(self, args):
        """Call action."""
        async def _call():
            return await self.broker.call(action, params)

        result = self.loop.run_until_complete(_call())
        print(result)
```

### Pattern 2: Dedicated Thread (Background broker)

```python
class MoleculerPyREPL(cmd.Cmd):
    def __init__(self, broker):
        self.broker = broker
        self.loop = asyncio.new_event_loop()

        # Run event loop in background thread
        self.loop_thread = threading.Thread(
            target=self.loop.run_forever,
            daemon=True
        )
        self.loop_thread.start()

    def run_async(self, coro):
        """Run coroutine in background loop."""
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result(timeout=30)

    def do_call(self, args):
        result = self.run_async(self.broker.call(action, params))
        print(result)
```

### Pattern 3: prompt_toolkit (Native async)

```python
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

class AsyncREPL:
    def __init__(self, broker):
        self.broker = broker
        self.session = PromptSession()

    async def run(self):
        while True:
            with patch_stdout():
                line = await self.session.prompt_async("mol $ ")

            if line == "quit":
                break

            await self.execute(line)
```

---

## Data Flow

### Example: `call math.add a=5 b=3`

```
1. User Input
   └─► "call math.add a=5 b=3"

2. cmd.Cmd.onecmd()
   └─► Splits: cmd="call", args="math.add a=5 b=3"

3. do_call(args)
   └─► ArgParser.parse("math.add a=5 b=3")
       └─► ParsedArgs(
             positional=["math.add"],
             payload={"a": 5, "b": 3},
             meta={},
             options={}
           )

4. CallCommand.execute(broker, parsed_args)
   └─► await broker.call("math.add", {"a": 5, "b": 3})
       └─► Transit → NATS → Remote Service
           └─► Return: 8

5. OutputFormatter.json(8)
   └─► "Result: 8"
```

---

## Error Handling

```python
class REPLError(Exception):
    """Base REPL error."""
    pass

class CommandNotFoundError(REPLError):
    """Unknown command."""
    pass

class ParseError(REPLError):
    """Argument parsing failed."""
    pass

class ExecutionError(REPLError):
    """Command execution failed."""
    pass
```

**Error Display:**
```
mol $ call unknown.action
✗ Error: Service 'unknown' is not available

mol $ call math.add
✗ Error: Missing required parameter 'a'

mol $ invalid command
✗ Unknown command: 'invalid'. Type 'help' for available commands.
```

---

## Configuration

```python
@dataclass
class REPLConfig:
    """REPL configuration."""

    # Prompt
    prompt: str = "mol $ "

    # History
    history_file: str = "~/.moleculerpy_repl_history"
    history_size: int = 1000

    # Output
    use_colors: bool = True
    table_style: str = "rounded"  # rounded, simple, minimal

    # Behavior
    auto_connect: bool = True
    default_timeout: float = 30.0

    # Custom commands
    custom_commands: list[type[BaseCommand]] = field(default_factory=list)
```

---

## Testing Strategy

### Unit Tests

```python
# test_parser.py
def test_parse_basic_params():
    parser = ArgParser()
    result = parser.parse("a=5 b=hello")
    assert result.payload == {"a": 5, "b": "hello"}

def test_parse_meta_prefix():
    parser = ArgParser()
    result = parser.parse("#userId=123 #source=api")
    assert result.meta == {"userId": 123, "source": "api"}
```

### Integration Tests

```python
# test_repl.py
@pytest.mark.asyncio
async def test_call_command():
    broker = MockBroker()
    repl = MoleculerPyREPL(broker)

    output = repl.onecmd("call math.add a=5 b=3")

    assert broker.call_history[-1] == ("math.add", {"a": 5, "b": 3})
```

---

## Dependencies Graph

```
moleculerpy-repl
├── moleculerpy (required)
│   └── nats-py
├── rich (optional, for pretty output)
└── prompt_toolkit (optional, for advanced REPL)
```
