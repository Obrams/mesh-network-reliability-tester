"""Virtual mesh network facade."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mesh_tester.metrics import NetworkStatistics
from mesh_tester.node import MockNode
from mesh_tester.router import MeshRouter

if TYPE_CHECKING:
    from mesh_tester.router import StorageProtocol


class VirtualMesh:

    def __init__(
        self,
        nodes: int = 3,
        packet_loss_rate: float = 0.0,
        min_latency_ms: float = 10.0,
        max_latency_ms: float = 100.0,
        storage: StorageProtocol | None = None,
        seed: int | None = None,
        node_names: list[str] | None = None,
    ):
        if nodes < 1:
            raise ValueError("nodes must be at least 1")

        self._router = MeshRouter(
            packet_loss_rate=packet_loss_rate,
            min_latency_ms=min_latency_ms,
            max_latency_ms=max_latency_ms,
            storage=storage,
            seed=seed,
        )

        self._nodes: list[MockNode] = []
        for i in range(nodes):
            name = node_names[i] if node_names and i < len(node_names) else None
            node = MockNode(node_id=f"node-{i}", name=name)
            self._router.register_node(node)
            self._nodes.append(node)

    @property
    def nodes(self) -> list[MockNode]:
        return self._nodes

    @property
    def router(self) -> MeshRouter:
        return self._router

    def get_node(self, node_id: str) -> MockNode | None:
        return self._router.get_node(node_id)

    def add_node(self, name: str | None = None) -> MockNode:
        node_id = f"node-{len(self._nodes)}"
        node = MockNode(node_id=node_id, name=name)
        self._router.register_node(node)
        self._nodes.append(node)
        return node

    def remove_node(self, node_id: str) -> bool:
        node = self._router.get_node(node_id)
        if node:
            self._router.unregister_node(node_id)
            self._nodes.remove(node)
            return True
        return False

    def broadcast(self, message: str, from_node: MockNode | str) -> None:
        if isinstance(from_node, str):
            node = self.get_node(from_node)
            if node is None:
                raise ValueError(f"Node {from_node} not found")
            from_node = node

        from_node.send_text(message, dest=None)

    def get_statistics(self) -> NetworkStatistics:
        return NetworkStatistics.from_router(self._router)

    def reset_statistics(self) -> None:
        self._router.clear_log()
        for node in self._nodes:
            node.clear_inbox()

    @property
    def packet_loss_rate(self) -> float:
        return self._router.packet_loss_rate

    @packet_loss_rate.setter
    def packet_loss_rate(self, value: float) -> None:
        if not 0.0 <= value <= 1.0:
            raise ValueError("packet_loss_rate must be between 0.0 and 1.0")
        self._router.packet_loss_rate = value

    def __repr__(self) -> str:
        return (
            f"VirtualMesh(nodes={len(self._nodes)}, "
            f"loss_rate={self._router.packet_loss_rate:.1%})"
        )

    def __len__(self) -> int:
        return len(self._nodes)

