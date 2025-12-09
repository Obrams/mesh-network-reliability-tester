"""Mesh router with simulated packet loss and latency."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from mesh_tester.node import Message, MockNode


class StorageProtocol(Protocol):
    def log_packet(
        self,
        message_id: str,
        from_node: str,
        to_node: str | None,
        payload_hash: str,
        delivered: bool,
        latency_ms: float,
    ) -> None: ...


@dataclass
class PacketLog:
    message_id: str
    from_node: str
    to_node: str | None
    payload_hash: str
    timestamp: float
    delivered: bool
    latency_ms: float


class MeshRouter:
    def __init__(
        self,
        packet_loss_rate: float = 0.0,
        min_latency_ms: float = 10.0,
        max_latency_ms: float = 100.0,
        storage: StorageProtocol | None = None,
        seed: int | None = None,
    ):
        if not 0.0 <= packet_loss_rate <= 1.0:
            raise ValueError("packet_loss_rate must be between 0.0 and 1.0")

        self.packet_loss_rate = packet_loss_rate
        self.min_latency_ms = min_latency_ms
        self.max_latency_ms = max_latency_ms
        self._storage = storage
        self._rng = random.Random(seed)

        self._nodes: dict[str, MockNode] = {}
        self._packet_log: list[PacketLog] = []
        self._total_sent = 0
        self._total_delivered = 0

    def register_node(self, node: MockNode) -> None:
        self._nodes[node.node_id] = node
        node.router = self

    def unregister_node(self, node_id: str) -> None:
        if node_id in self._nodes:
            self._nodes[node_id]._router = None
            del self._nodes[node_id]

    def get_node(self, node_id: str) -> MockNode | None:
        return self._nodes.get(node_id)

    @property
    def nodes(self) -> list[MockNode]:
        return list(self._nodes.values())

    def route_packet(self, message: Message) -> bool:
        self._total_sent += 1

        # Determine target nodes
        if message.to_node is None:
            # Broadcast to all nodes except sender
            targets = [n for n in self._nodes.values() if n.node_id != message.from_node]
        else:
            # Unicast to specific node
            target = self._nodes.get(message.to_node)
            targets = [target] if target else []

        any_delivered = False

        for target in targets:
            # Simulate packet loss
            is_lost = self._rng.random() < self.packet_loss_rate

            # Simulate latency
            latency_ms = self._rng.uniform(self.min_latency_ms, self.max_latency_ms)

            # Log the transmission attempt
            log_entry = PacketLog(
                message_id=message.id,
                from_node=message.from_node,
                to_node=target.node_id,
                payload_hash=str(hash(message.payload)),
                timestamp=time.time(),
                delivered=not is_lost,
                latency_ms=latency_ms,
            )
            self._packet_log.append(log_entry)

            # Persist to storage if available
            if self._storage:
                self._storage.log_packet(
                    message_id=log_entry.message_id,
                    from_node=log_entry.from_node,
                    to_node=log_entry.to_node,
                    payload_hash=log_entry.payload_hash,
                    delivered=log_entry.delivered,
                    latency_ms=log_entry.latency_ms,
                )

            if not is_lost:
                # Deliver the message
                target.receive(message)
                self._total_delivered += 1
                any_delivered = True

        return any_delivered

    def get_packet_log(self) -> list[PacketLog]:
        return self._packet_log.copy()

    def clear_log(self) -> None:
        self._packet_log.clear()
        self._total_sent = 0
        self._total_delivered = 0

    @property
    def total_sent(self) -> int:
        return self._total_sent

    @property
    def total_delivered(self) -> int:
        return self._total_delivered

    @property
    def delivery_rate(self) -> float:
        if self._total_sent == 0:
            return 1.0
        return self._total_delivered / self._total_sent

    def __repr__(self) -> str:
        return (
            f"MeshRouter(nodes={len(self._nodes)}, "
            f"loss_rate={self.packet_loss_rate}, "
            f"pdr={self.delivery_rate:.2%})"
        )

