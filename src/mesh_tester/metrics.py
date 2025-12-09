"""Network metrics and statistics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mesh_tester.router import MeshRouter, PacketLog


@dataclass
class LatencyStats:
    min_ms: float
    max_ms: float
    avg_ms: float
    median_ms: float
    p95_ms: float
    p99_ms: float

    @classmethod
    def from_values(cls, latencies: list[float]) -> LatencyStats:
        if not latencies:
            return cls(
                min_ms=0.0,
                max_ms=0.0,
                avg_ms=0.0,
                median_ms=0.0,
                p95_ms=0.0,
                p99_ms=0.0,
            )

        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)

        return cls(
            min_ms=sorted_latencies[0],
            max_ms=sorted_latencies[-1],
            avg_ms=sum(latencies) / n,
            median_ms=sorted_latencies[n // 2],
            p95_ms=sorted_latencies[int(n * 0.95)] if n > 1 else sorted_latencies[0],
            p99_ms=sorted_latencies[int(n * 0.99)] if n > 1 else sorted_latencies[0],
        )


@dataclass
class NodeStats:
    node_id: str
    sent_count: int
    received_count: int
    delivery_rate: float


@dataclass
class NetworkStatistics:
    total_sent: int
    total_delivered: int
    total_lost: int
    delivery_rate: float
    loss_rate: float
    latency: LatencyStats
    node_stats: list[NodeStats]
    packet_log_size: int

    @classmethod
    def from_router(cls, router: MeshRouter) -> NetworkStatistics:
        packet_log = router.get_packet_log()

        total_sent = len(packet_log)
        total_delivered = sum(1 for p in packet_log if p.delivered)
        total_lost = total_sent - total_delivered

        delivery_rate = total_delivered / total_sent if total_sent > 0 else 1.0
        loss_rate = 1.0 - delivery_rate

        delivered_latencies = [p.latency_ms for p in packet_log if p.delivered]
        latency_stats = LatencyStats.from_values(delivered_latencies)

        node_stats = []
        for node in router.nodes:
            sent = sum(1 for p in packet_log if p.from_node == node.node_id)
            received = node.received_count
            sent_delivered = sum(
                1 for p in packet_log if p.from_node == node.node_id and p.delivered
            )
            node_delivery_rate = sent_delivered / sent if sent > 0 else 1.0

            node_stats.append(
                NodeStats(
                    node_id=node.node_id,
                    sent_count=sent,
                    received_count=received,
                    delivery_rate=node_delivery_rate,
                )
            )

        return cls(
            total_sent=total_sent,
            total_delivered=total_delivered,
            total_lost=total_lost,
            delivery_rate=delivery_rate,
            loss_rate=loss_rate,
            latency=latency_stats,
            node_stats=node_stats,
            packet_log_size=len(packet_log),
        )

    def to_dict(self) -> dict:
        return {
            "total_sent": self.total_sent,
            "total_delivered": self.total_delivered,
            "total_lost": self.total_lost,
            "delivery_rate": self.delivery_rate,
            "loss_rate": self.loss_rate,
            "latency": {
                "min_ms": self.latency.min_ms,
                "max_ms": self.latency.max_ms,
                "avg_ms": self.latency.avg_ms,
                "median_ms": self.latency.median_ms,
                "p95_ms": self.latency.p95_ms,
                "p99_ms": self.latency.p99_ms,
            },
            "node_stats": [
                {
                    "node_id": ns.node_id,
                    "sent_count": ns.sent_count,
                    "received_count": ns.received_count,
                    "delivery_rate": ns.delivery_rate,
                }
                for ns in self.node_stats
            ],
            "packet_log_size": self.packet_log_size,
        }

    def __str__(self) -> str:
        return (
            f"NetworkStatistics(\n"
            f"  PDR: {self.delivery_rate:.2%}\n"
            f"  Total: {self.total_sent} sent, {self.total_delivered} delivered, "
            f"{self.total_lost} lost\n"
            f"  Latency: avg={self.latency.avg_ms:.1f}ms, "
            f"p95={self.latency.p95_ms:.1f}ms, p99={self.latency.p99_ms:.1f}ms\n"
            f")"
        )


def calculate_pdr(packet_log: list[PacketLog]) -> float:
    if not packet_log:
        return 1.0
    delivered = sum(1 for p in packet_log if p.delivered)
    return delivered / len(packet_log)


def calculate_avg_latency(packet_log: list[PacketLog]) -> float:
    delivered = [p.latency_ms for p in packet_log if p.delivered]
    if not delivered:
        return 0.0
    return sum(delivered) / len(delivered)

