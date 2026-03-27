"""Shared fixtures for moleculerpy-repl tests."""

from __future__ import annotations

from typing import Any

import pytest


class MockService:
    """Mock service for testing."""

    def __init__(self, name: str, version: str | None = None):
        self.name = name
        self.version = version
        self.full_name = f"v{version}.{name}" if version else name
        self.actions: dict[str, Any] = {}
        self.events: dict[str, Any] = {}

    def add_action(self, name: str, handler: Any = None) -> None:
        """Add action to service."""
        self.actions[name] = handler or (lambda params: params)

    def add_event(self, name: str, handler: Any = None) -> None:
        """Add event to service."""
        self.events[name] = handler or (lambda params: None)


class MockBroker:
    """Mock broker for testing REPL commands."""

    def __init__(self) -> None:
        self.id = "test-node-001"
        self.node_id = "test-node-001"
        self.started_at = 1704067200.0  # 2024-01-01 00:00:00
        self.services: dict[str, MockService] = {}
        self._call_results: dict[str, Any] = {}
        self._emitted_events: list[dict] = []
        self._broadcast_events: list[dict] = []

    def add_service(self, service: MockService) -> None:
        """Register a service."""
        self.services[service.name] = service

    def set_call_result(self, action: str, result: Any) -> None:
        """Set result for action call."""
        self._call_results[action] = result

    async def call(self, action: str, params: dict | None = None, **kwargs: Any) -> Any:
        """Mock action call."""
        if action in self._call_results:
            result = self._call_results[action]
            if callable(result):
                return result(params)
            return result
        return {"action": action, "params": params}

    async def emit(self, event: str, payload: dict | None = None, **kwargs: Any) -> None:
        """Mock event emit."""
        self._emitted_events.append({"event": event, "payload": payload, "kwargs": kwargs})

    async def broadcast(self, event: str, payload: dict | None = None, **kwargs: Any) -> None:
        """Mock broadcast."""
        self._broadcast_events.append({"event": event, "payload": payload, "kwargs": kwargs})


@pytest.fixture
def mock_broker() -> MockBroker:
    """Provide a mock broker with sample services."""
    broker = MockBroker()

    # Add math service
    math_svc = MockService("math")
    math_svc.add_action("add")
    math_svc.add_action("multiply")
    broker.add_service(math_svc)
    broker.set_call_result("math.add", lambda p: p.get("a", 0) + p.get("b", 0))
    broker.set_call_result("math.multiply", lambda p: p.get("a", 0) * p.get("b", 0))

    # Add user service
    user_svc = MockService("user", version="1")
    user_svc.add_action("get")
    user_svc.add_action("list")
    user_svc.add_event("created")
    broker.add_service(user_svc)
    broker.set_call_result("user.get", {"id": "u1", "name": "John"})
    broker.set_call_result("user.list", [{"id": "u1"}, {"id": "u2"}])

    return broker


@pytest.fixture
def parser():
    """Provide parser instance."""
    from moleculerpy_repl.parser import ArgParser

    return ArgParser()


@pytest.fixture
def output_formatter():
    """Provide output formatter (no colors for testing)."""
    from moleculerpy_repl.output import OutputFormatter

    return OutputFormatter(use_colors=False)


@pytest.fixture
def command_registry():
    """Provide command registry with all commands."""
    from moleculerpy_repl.commands import create_default_registry

    return create_default_registry()
