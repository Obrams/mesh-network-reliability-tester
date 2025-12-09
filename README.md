# Mesh Network Reliability Tester

Python framework for automated testing of mesh networks. Designed for LoRa mesh (Meshtastic) testing without physical hardware.

## Features

- Virtual mesh simulation with configurable packet loss and latency
- Runs in CI/CD pipelines using mock devices
- PDR, latency percentiles, and per-node statistics
- Optional ClickHouse + Grafana for analytics

## Installation

```bash
git clone https://github.com/daryozerova/mesh-network-reliability-tester.git
cd mesh-network-reliability-tester
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

## Usage

```python
from mesh_tester import VirtualMesh

mesh = VirtualMesh(nodes=5, packet_loss_rate=0.1)

sender = mesh.nodes[0]
receiver = mesh.nodes[4]

for i in range(100):
    sender.send_text(f"Message {i}", dest=receiver.id)

stats = mesh.get_statistics()
print(f"PDR: {stats.delivery_rate:.2%}")
print(f"Avg Latency: {stats.latency.avg_ms:.1f}ms")
```

## Tests

```bash
pytest                    # Run all tests
pytest --cov=src/mesh_tester  # With coverage
pytest -m slow            # Stress tests only
```

## Fixtures

```python
def test_delivery(reliable_mesh):
    sender = reliable_mesh.nodes[0]
    receiver = reliable_mesh.nodes[1]
    sender.send_text("Hello!", dest=receiver.id)
    assert receiver.has_message("Hello!")
```

Available fixtures: `virtual_mesh` (10% loss), `reliable_mesh` (0% loss), `unreliable_mesh` (30% loss), `large_mesh` (10 nodes).

## Monitoring (Optional)

```bash
docker-compose up -d
open http://localhost:3000  # admin / meshtest123
```

## Architecture

```
src/mesh_tester/
├── node.py      # MockNode - virtual network node
├── router.py    # MeshRouter - packet routing with loss simulation
├── mesh.py      # VirtualMesh - high-level facade
├── metrics.py   # Statistics calculation
└── storage/
    └── clickhouse.py  # Storage backends
```

## License

MIT
