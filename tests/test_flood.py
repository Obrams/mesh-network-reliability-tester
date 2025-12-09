import pytest

from mesh_tester.mesh import VirtualMesh
from mesh_tester.storage.clickhouse import MockStorage


class TestFloodBasic:
    def test_100_messages(self, virtual_mesh: VirtualMesh):
        sender = virtual_mesh.nodes[0]
        receiver = virtual_mesh.nodes[2]
        for i in range(100):
            sender.send_text(f"flood-{i}", dest=receiver.id)
        stats = virtual_mesh.get_statistics()
        assert stats.total_sent == 100
        assert stats.delivery_rate >= 0.80

    @pytest.mark.slow
    def test_1000_messages(self, virtual_mesh: VirtualMesh):
        sender = virtual_mesh.nodes[0]
        receiver = virtual_mesh.nodes[1]
        for i in range(1000):
            sender.send_text(f"flood-{i}", dest=receiver.id)
        stats = virtual_mesh.get_statistics()
        assert stats.total_sent == 1000
        assert 0.85 <= stats.delivery_rate <= 0.95


class TestFloodConditions:
    @pytest.mark.parametrize("loss_rate", [0.1, 0.3, 0.5])
    def test_different_loss_rates(self, loss_rate: float):
        mesh = VirtualMesh(nodes=5, packet_loss_rate=loss_rate, seed=42)
        sender = mesh.nodes[0]
        receiver = mesh.nodes[4]
        for i in range(200):
            sender.send_text(f"msg-{i}", dest=receiver.id)
        stats = mesh.get_statistics()
        expected_min = (1 - loss_rate) - 0.15
        expected_max = (1 - loss_rate) + 0.15
        assert expected_min <= stats.delivery_rate <= expected_max

    @pytest.mark.parametrize("node_count", [3, 5, 10])
    def test_different_network_sizes(self, node_count: int):
        mesh = VirtualMesh(nodes=node_count, packet_loss_rate=0.1, seed=42)
        sender = mesh.nodes[0]
        for i in range(50):
            sender.send_text(f"broadcast-{i}")
        stats = mesh.get_statistics()
        assert stats.total_sent == 50 * (node_count - 1)


class TestFloodBroadcast:
    def test_broadcast_flood(self, large_mesh: VirtualMesh):
        sender = large_mesh.nodes[0]
        for i in range(50):
            sender.send_text(f"broadcast-{i}")
        stats = large_mesh.get_statistics()
        assert stats.total_sent == 50 * (len(large_mesh.nodes) - 1)
        for node in large_mesh.nodes[1:]:
            assert node.received_count > 0

    def test_multi_sender_broadcast(self, large_mesh: VirtualMesh):
        for sender in large_mesh.nodes:
            for i in range(10):
                sender.send_text(f"from-{sender.id}-{i}")
        for node in large_mesh.nodes:
            assert node.received_count > 0


class TestFloodWithStorage:
    def test_storage_logging(self, mesh_with_storage: VirtualMesh, mock_storage: MockStorage):
        sender = mesh_with_storage.nodes[0]
        receiver = mesh_with_storage.nodes[1]
        for i in range(100):
            sender.send_text(f"msg-{i}", dest=receiver.id)
        assert mock_storage.record_count == 100
        storage_pdr = mock_storage.get_pdr()
        mesh_stats = mesh_with_storage.get_statistics()
        assert abs(storage_pdr - mesh_stats.delivery_rate) < 0.01

    def test_storage_latency(self, mesh_with_storage: VirtualMesh, mock_storage: MockStorage):
        sender = mesh_with_storage.nodes[0]
        receiver = mesh_with_storage.nodes[1]
        for i in range(50):
            sender.send_text(f"msg-{i}", dest=receiver.id)
        avg_latency = mock_storage.get_avg_latency()
        records = mock_storage.get_records()
        for record in records:
            assert record.latency_ms >= 0
        assert avg_latency >= 10.0


class TestFloodStress:
    @pytest.mark.slow
    def test_heavy_flood(self):
        import random
        mesh = VirtualMesh(nodes=20, packet_loss_rate=0.2, seed=42)
        rng = random.Random(42)
        for sender in mesh.nodes:
            for _ in range(50):
                receiver = rng.choice([n for n in mesh.nodes if n != sender])
                sender.send_text("stress-test", dest=receiver.id)
        stats = mesh.get_statistics()
        assert stats.total_sent == 1000
        assert 0.70 <= stats.delivery_rate <= 0.90

    def test_sustained_flood(self, virtual_mesh: VirtualMesh):
        sender = virtual_mesh.nodes[0]
        receiver = virtual_mesh.nodes[1]
        round_pdrs = []
        for _ in range(5):
            virtual_mesh.reset_statistics()
            for i in range(100):
                sender.send_text(f"round-msg-{i}", dest=receiver.id)
            stats = virtual_mesh.get_statistics()
            round_pdrs.append(stats.delivery_rate)
        avg_pdr = sum(round_pdrs) / len(round_pdrs)
        for pdr in round_pdrs:
            assert abs(pdr - avg_pdr) < 0.20

