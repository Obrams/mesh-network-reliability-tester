import pytest

from mesh_tester.mesh import VirtualMesh


class TestMessageDelivery:
    def test_basic(self, reliable_mesh: VirtualMesh):
        sender = reliable_mesh.nodes[0]
        receiver = reliable_mesh.nodes[1]
        sender.send_text("Hello, mesh!", dest=receiver.id)
        assert receiver.has_message("Hello, mesh!")
        assert receiver.received_count == 1

    def test_multiple(self, reliable_mesh: VirtualMesh):
        sender = reliable_mesh.nodes[0]
        receiver = reliable_mesh.nodes[2]
        for i in range(10):
            sender.send_text(f"Message {i}", dest=receiver.id)
        assert receiver.received_count == 10
        for i in range(10):
            assert receiver.has_message(f"Message {i}")

    def test_broadcast(self, reliable_mesh: VirtualMesh):
        sender = reliable_mesh.nodes[0]
        sender.send_text("Broadcast message")
        for node in reliable_mesh.nodes[1:]:
            assert node.has_message("Broadcast message")

    def test_self_exclusion_from_broadcast(self, reliable_mesh: VirtualMesh):
        sender = reliable_mesh.nodes[0]
        sender.send_text("Broadcast message")
        assert not sender.has_message("Broadcast message")


class TestDeliveryReliability:
    def test_pdr_with_10pct_loss(self, virtual_mesh: VirtualMesh):
        sender = virtual_mesh.nodes[0]
        receiver = virtual_mesh.nodes[2]
        for i in range(100):
            sender.send_text(f"msg-{i}", dest=receiver.id)
        stats = virtual_mesh.get_statistics()
        assert stats.delivery_rate >= 0.85

    def test_pdr_with_30pct_loss(self, unreliable_mesh: VirtualMesh):
        sender = unreliable_mesh.nodes[0]
        receiver = unreliable_mesh.nodes[4]
        for i in range(100):
            sender.send_text(f"msg-{i}", dest=receiver.id)
        stats = unreliable_mesh.get_statistics()
        assert 0.50 <= stats.delivery_rate <= 0.90

    def test_no_loss_full_delivery(self, reliable_mesh: VirtualMesh):
        sender = reliable_mesh.nodes[0]
        receiver = reliable_mesh.nodes[1]
        for i in range(50):
            sender.send_text(f"msg-{i}", dest=receiver.id)
        stats = reliable_mesh.get_statistics()
        assert stats.delivery_rate == 1.0

    def test_statistics_consistency(self, virtual_mesh: VirtualMesh):
        sender = virtual_mesh.nodes[0]
        receiver = virtual_mesh.nodes[1]
        for i in range(50):
            sender.send_text(f"msg-{i}", dest=receiver.id)
        stats = virtual_mesh.get_statistics()
        assert stats.total_sent == 50
        assert stats.total_delivered + stats.total_lost == stats.total_sent
        assert stats.delivery_rate == stats.total_delivered / stats.total_sent


class TestNodeCommunication:
    def test_bidirectional(self, reliable_mesh: VirtualMesh):
        node_a = reliable_mesh.nodes[0]
        node_b = reliable_mesh.nodes[1]
        node_a.send_text("Hello from A", dest=node_b.id)
        node_b.send_text("Hello from B", dest=node_a.id)
        assert node_b.has_message("Hello from A")
        assert node_a.has_message("Hello from B")

    def test_all_pairs(self, reliable_mesh: VirtualMesh):
        nodes = reliable_mesh.nodes
        for i, sender in enumerate(nodes):
            for j, receiver in enumerate(nodes):
                if i != j:
                    sender.send_text(f"From {i} to {j}", dest=receiver.id)
        for node in nodes:
            assert node.received_count == len(nodes) - 1

    def test_message_ordering(self, reliable_mesh: VirtualMesh):
        sender = reliable_mesh.nodes[0]
        receiver = reliable_mesh.nodes[1]
        for i in range(10):
            sender.send_text(f"msg-{i}", dest=receiver.id)
        messages = receiver.get_messages()
        for i, msg in enumerate(messages):
            assert msg.payload == f"msg-{i}"


class TestEdgeCases:
    def test_send_to_nonexistent_node(self, virtual_mesh: VirtualMesh):
        sender = virtual_mesh.nodes[0]
        msg = sender.send_text("Hello", dest="nonexistent-node")
        assert msg is not None

    def test_empty_message(self, reliable_mesh: VirtualMesh):
        sender = reliable_mesh.nodes[0]
        receiver = reliable_mesh.nodes[1]
        sender.send_text("", dest=receiver.id)
        assert receiver.has_message("")

    def test_large_message(self, reliable_mesh: VirtualMesh):
        sender = reliable_mesh.nodes[0]
        receiver = reliable_mesh.nodes[1]
        large_msg = "x" * 10000
        sender.send_text(large_msg, dest=receiver.id)
        assert receiver.has_message(large_msg)

    def test_node_not_connected_to_router(self):
        from mesh_tester.node import MockNode
        node = MockNode()
        with pytest.raises(RuntimeError, match="not connected to a router"):
            node.send_text("Hello")

