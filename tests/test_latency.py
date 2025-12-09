from mesh_tester.mesh import VirtualMesh
from mesh_tester.metrics import LatencyStats


class TestLatencySimulation:
    def test_within_bounds(self, reliable_mesh: VirtualMesh):
        sender = reliable_mesh.nodes[0]
        receiver = reliable_mesh.nodes[1]
        for i in range(50):
            sender.send_text(f"msg-{i}", dest=receiver.id)
        stats = reliable_mesh.get_statistics()
        assert stats.latency.min_ms >= 5.0
        assert stats.latency.max_ms <= 20.0

    def test_distribution(self, reliable_mesh: VirtualMesh):
        sender = reliable_mesh.nodes[0]
        receiver = reliable_mesh.nodes[1]
        for i in range(100):
            sender.send_text(f"msg-{i}", dest=receiver.id)
        stats = reliable_mesh.get_statistics()
        expected_avg = (5.0 + 20.0) / 2
        assert abs(stats.latency.avg_ms - expected_avg) < 5.0

    def test_percentiles(self, reliable_mesh: VirtualMesh):
        sender = reliable_mesh.nodes[0]
        receiver = reliable_mesh.nodes[1]
        for i in range(100):
            sender.send_text(f"msg-{i}", dest=receiver.id)
        stats = reliable_mesh.get_statistics()
        assert stats.latency.p95_ms <= stats.latency.p99_ms
        assert stats.latency.p99_ms <= stats.latency.max_ms
        assert stats.latency.min_ms <= stats.latency.median_ms <= stats.latency.max_ms


class TestLatencyStatistics:
    def test_empty_list(self):
        stats = LatencyStats.from_values([])
        assert stats.min_ms == 0.0
        assert stats.max_ms == 0.0
        assert stats.avg_ms == 0.0

    def test_single_value(self):
        stats = LatencyStats.from_values([50.0])
        assert stats.min_ms == 50.0
        assert stats.max_ms == 50.0
        assert stats.avg_ms == 50.0
        assert stats.p95_ms == 50.0

    def test_calculation(self):
        stats = LatencyStats.from_values([10.0, 20.0, 30.0, 40.0, 50.0])
        assert stats.min_ms == 10.0
        assert stats.max_ms == 50.0
        assert stats.avg_ms == 30.0
        assert stats.median_ms == 30.0


class TestHighLatencyNetwork:
    def test_high_latency(self):
        mesh = VirtualMesh(nodes=3, packet_loss_rate=0.0, min_latency_ms=500.0, max_latency_ms=1000.0, seed=42)
        sender = mesh.nodes[0]
        receiver = mesh.nodes[1]
        for i in range(20):
            sender.send_text(f"msg-{i}", dest=receiver.id)
        stats = mesh.get_statistics()
        assert stats.latency.min_ms >= 500.0
        assert stats.latency.max_ms <= 1000.0

    def test_zero_latency(self):
        mesh = VirtualMesh(nodes=3, packet_loss_rate=0.0, min_latency_ms=0.0, max_latency_ms=0.0, seed=42)
        sender = mesh.nodes[0]
        receiver = mesh.nodes[1]
        for i in range(20):
            sender.send_text(f"msg-{i}", dest=receiver.id)
        stats = mesh.get_statistics()
        assert stats.latency.min_ms == 0.0
        assert stats.latency.max_ms == 0.0


class TestLatencyWithPacketLoss:
    def test_only_count_delivered(self, virtual_mesh: VirtualMesh):
        sender = virtual_mesh.nodes[0]
        receiver = virtual_mesh.nodes[1]
        for i in range(100):
            sender.send_text(f"msg-{i}", dest=receiver.id)
        stats = virtual_mesh.get_statistics()
        assert stats.latency.min_ms >= 10.0
        assert stats.latency.max_ms <= 100.0
        assert stats.total_delivered == receiver.received_count

    def test_consistency_with_loss(self, unreliable_mesh: VirtualMesh):
        sender = unreliable_mesh.nodes[0]
        receiver = unreliable_mesh.nodes[1]
        for i in range(100):
            sender.send_text(f"msg-{i}", dest=receiver.id)
        stats = unreliable_mesh.get_statistics()
        if stats.total_delivered > 0:
            assert stats.latency.min_ms >= 50.0
            assert stats.latency.max_ms <= 200.0

