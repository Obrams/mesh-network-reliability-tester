"""Pytest fixtures for mesh network testing."""

import os

import pytest

from mesh_tester.mesh import VirtualMesh
from mesh_tester.storage.clickhouse import ClickHouseStorage, MockStorage


def _get_storage():
    if os.environ.get("MESH_CLICKHOUSE_ENABLED") == "1":
        try:
            return ClickHouseStorage(
                host=os.environ.get("MESH_CLICKHOUSE_HOST", "localhost"),
                port=int(os.environ.get("MESH_CLICKHOUSE_PORT", "9000")),
                database="mesh_network",
            )
        except Exception:
            return MockStorage()
    return None


@pytest.fixture
def mock_storage() -> MockStorage:
    return MockStorage()


@pytest.fixture
def clickhouse_storage():
    """Requires: docker-compose up -d"""
    try:
        storage = ClickHouseStorage(
            host=os.environ.get("MESH_CLICKHOUSE_HOST", "localhost"),
            port=int(os.environ.get("MESH_CLICKHOUSE_PORT", "9000")),
            database="mesh_network",
        )
        yield storage
        storage.close()
    except Exception as e:
        pytest.skip(f"ClickHouse not available: {e}")


@pytest.fixture
def virtual_mesh() -> VirtualMesh:
    """3 nodes, 10% loss, 10-100ms latency."""
    return VirtualMesh(
        nodes=3,
        packet_loss_rate=0.1,
        min_latency_ms=10.0,
        max_latency_ms=100.0,
        seed=42,
        storage=_get_storage(),
    )


@pytest.fixture
def reliable_mesh() -> VirtualMesh:
    """No packet loss."""
    return VirtualMesh(
        nodes=3,
        packet_loss_rate=0.0,
        min_latency_ms=5.0,
        max_latency_ms=20.0,
        seed=42,
        storage=_get_storage(),
    )


@pytest.fixture
def unreliable_mesh() -> VirtualMesh:
    """30% packet loss."""
    return VirtualMesh(
        nodes=5,
        packet_loss_rate=0.3,
        min_latency_ms=50.0,
        max_latency_ms=200.0,
        seed=42,
        storage=_get_storage(),
    )


@pytest.fixture
def large_mesh() -> VirtualMesh:
    """10 nodes for stress testing."""
    return VirtualMesh(
        nodes=10,
        packet_loss_rate=0.15,
        min_latency_ms=10.0,
        max_latency_ms=150.0,
        seed=42,
        storage=_get_storage(),
    )


@pytest.fixture
def mesh_with_storage(mock_storage: MockStorage) -> VirtualMesh:
    return VirtualMesh(
        nodes=3,
        packet_loss_rate=0.1,
        storage=mock_storage,
        seed=42,
    )


@pytest.fixture
def mesh_with_clickhouse(clickhouse_storage) -> VirtualMesh:
    return VirtualMesh(
        nodes=5,
        packet_loss_rate=0.15,
        min_latency_ms=10.0,
        max_latency_ms=100.0,
        seed=42,
        storage=clickhouse_storage,
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    )
    config.addinivalue_line(
        "markers",
        "integration: marks tests that require external services",
    )
    config.addinivalue_line(
        "markers",
        "clickhouse: marks tests that require ClickHouse",
    )


def pytest_report_header(config):
    if os.environ.get("MESH_CLICKHOUSE_ENABLED") == "1":
        host = os.environ.get("MESH_CLICKHOUSE_HOST", "localhost")
        port = os.environ.get("MESH_CLICKHOUSE_PORT", "9000")
        return [f"ClickHouse logging: ENABLED ({host}:{port})"]
    return ["ClickHouse logging: disabled (set MESH_CLICKHOUSE_ENABLED=1 to enable)"]
