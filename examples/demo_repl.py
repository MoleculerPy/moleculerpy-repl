#!/usr/bin/env python3
"""Demo script to test moleculerpy-repl with a mock broker."""

import asyncio
import sys
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from moleculerpy_repl import REPL


class MockService:
    """Mock service with actions."""

    def __init__(self, name: str, version: str = "1"):
        self.name = name
        self.version = version
        self.full_name = f"{name}@{version}" if version else name
        self.actions = {}
        self.events = {}


class MockBroker:
    """Mock MoleculerPy broker for testing REPL."""

    def __init__(self, node_id: str = "demo-node"):
        self.node_id = node_id
        self.namespace = ""
        self.services = {}
        self.__version__ = "0.1.0"
        self.PROTOCOL_VERSION = "4"
        self.started_at = None

        # Register mock services
        self._setup_mock_services()

    def _setup_mock_services(self):
        """Setup mock services for demo."""
        # Math service
        math_svc = MockService("math")
        math_svc.actions = {
            "add": lambda params: params.get("a", 0) + params.get("b", 0),
            "multiply": lambda params: params.get("a", 0) * params.get("b", 0),
        }
        self.services["math"] = math_svc

        # User service
        user_svc = MockService("user")
        user_svc.actions = {
            "get": lambda params: {"id": params.get("id"), "name": "John Doe"},
            "list": lambda params: [
                {"id": "u1", "name": "John"},
                {"id": "u2", "name": "Jane"},
            ],
        }
        self.services["user"] = user_svc

        # Greeter service
        greeter_svc = MockService("greeter")
        greeter_svc.actions = {
            "hello": lambda params: f"Hello, {params.get('name', 'World')}!",
        }
        greeter_svc.events = {
            "user.created": True,
        }
        self.services["greeter"] = greeter_svc

    async def call(self, action: str, params: dict = None, **kwargs):
        """Mock action call."""
        params = params or {}

        # Parse action name
        parts = action.split(".")
        if len(parts) != 2:
            raise Exception(f"Invalid action format: {action}")

        service_name, action_name = parts

        # Find service
        if service_name not in self.services:
            raise Exception(f"Service not found: {service_name}")

        service = self.services[service_name]

        # Find action
        if action_name not in service.actions:
            raise Exception(f"Action not found: {action}")

        # Execute action
        handler = service.actions[action_name]
        return handler(params)

    async def emit(self, event: str, data: dict = None, **kwargs):
        """Mock event emit."""
        print(f"[EVENT] {event}: {data}")

    async def broadcast(self, event: str, data: dict = None, **kwargs):
        """Mock event broadcast."""
        print(f"[BROADCAST] {event}: {data}")


async def main():
    """Run demo REPL."""
    print("Creating mock broker...")
    broker = MockBroker()

    print("Starting REPL...")
    print("=" * 60)
    print("Try these commands:")
    print("  call math.add a=5 b=3")
    print("  call user.list")
    print("  call greeter.hello name=MoleculerPy")
    print("  services")
    print("  actions")
    print("  info")
    print("  help")
    print("=" * 60)

    repl = REPL(broker, delimiter="demo $ ")
    await repl.run()


if __name__ == "__main__":
    asyncio.run(main())
