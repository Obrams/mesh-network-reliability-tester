"""ClickHouse and mock storage backends."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass


@dataclass
class PacketRecord:
    timestamp: float
    message_id: str
    from_node: str
    to_node: str | None
    payload_hash: str
    delivered: bool
    latency_ms: float


_TABLE_NAME_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


class MockStorage:
    """In-memory storage for testing without external services."""

    def __init__(self) -> None:
        self._records: list[PacketRecord] = []

    def log_packet(
        self,
        message_id: str,
        from_node: str,
        to_node: str | None,
        payload_hash: str,
        delivered: bool,
        latency_ms: float,
    ) -> None:
        record = PacketRecord(
            timestamp=time.time(),
            message_id=message_id,
            from_node=from_node,
            to_node=to_node,
            payload_hash=payload_hash,
            delivered=delivered,
            latency_ms=latency_ms,
        )
        self._records.append(record)

    def get_pdr(self) -> float:
        if not self._records:
            return 1.0
        delivered = sum(1 for r in self._records if r.delivered)
        return delivered / len(self._records)

    def get_avg_latency(self) -> float:
        delivered = [r.latency_ms for r in self._records if r.delivered]
        if not delivered:
            return 0.0
        return sum(delivered) / len(delivered)

    def get_records(self, limit: int | None = None) -> list[PacketRecord]:
        if limit:
            return self._records[-limit:]
        return self._records.copy()

    def clear(self) -> None:
        self._records.clear()

    @property
    def record_count(self) -> int:
        return len(self._records)


class ClickHouseStorage:
    """ClickHouse storage backend for packet logging."""

    CREATE_TABLE_SQL = """
        CREATE TABLE IF NOT EXISTS {table} (
            timestamp DateTime64(3),
            message_id String,
            from_node String,
            to_node Nullable(String),
            payload_hash String,
            delivered UInt8,
            latency_ms Float64
        ) ENGINE = MergeTree()
        ORDER BY (timestamp, from_node)
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 9000,
        database: str = "default",
        table: str = "packets",
        user: str = "default",
        password: str = "",
        auto_create_table: bool = True,
    ) -> None:
        try:
            from clickhouse_driver import Client
        except ImportError as e:
            raise ImportError("clickhouse-driver required: pip install clickhouse-driver") from e

        if not _TABLE_NAME_PATTERN.match(table):
            raise ValueError(f"Invalid table name: {table}")

        self._host = host
        self._port = port
        self._database = database
        self._table = table
        self._client = Client(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
        )

        if auto_create_table:
            self._create_table()

    def _create_table(self) -> None:
        self._client.execute(self.CREATE_TABLE_SQL.format(table=self._table))

    def log_packet(
        self,
        message_id: str,
        from_node: str,
        to_node: str | None,
        payload_hash: str,
        delivered: bool,
        latency_ms: float,
    ) -> None:
        from datetime import datetime

        self._client.execute(
            f"INSERT INTO {self._table} VALUES",
            [(
                datetime.now(),
                message_id,
                from_node,
                to_node,
                payload_hash,
                1 if delivered else 0,
                latency_ms,
            )],
        )

    def get_pdr(self) -> float:
        result = self._client.execute(
            f"SELECT countIf(delivered = 1) / count() FROM {self._table}"
        )
        if result and result[0]:
            return float(result[0][0])
        return 1.0

    def get_avg_latency(self) -> float:
        result = self._client.execute(
            f"SELECT avg(latency_ms) FROM {self._table} WHERE delivered = 1"
        )
        if result and result[0] and result[0][0] is not None:
            return float(result[0][0])
        return 0.0

    def get_records(self, limit: int | None = None) -> list[PacketRecord]:
        query = f"""
            SELECT timestamp, message_id, from_node, to_node,
                   payload_hash, delivered, latency_ms
            FROM {self._table}
            ORDER BY timestamp DESC
        """
        if limit:
            query += f" LIMIT {int(limit)}"

        rows = self._client.execute(query)
        return [
            PacketRecord(
                timestamp=row[0].timestamp() if hasattr(row[0], 'timestamp') else row[0],
                message_id=row[1],
                from_node=row[2],
                to_node=row[3],
                payload_hash=row[4],
                delivered=bool(row[5]),
                latency_ms=row[6],
            )
            for row in rows
        ]

    def get_statistics(self) -> dict:
        result = self._client.execute(f"""
            SELECT
                count() as total,
                countIf(delivered = 1) as delivered,
                avg(if(delivered = 1, latency_ms, null)) as avg_latency,
                min(if(delivered = 1, latency_ms, null)) as min_latency,
                max(if(delivered = 1, latency_ms, null)) as max_latency,
                quantile(0.95)(if(delivered = 1, latency_ms, null)) as p95_latency,
                quantile(0.99)(if(delivered = 1, latency_ms, null)) as p99_latency
            FROM {self._table}
        """)

        if result and result[0]:
            row = result[0]
            total = row[0] or 0
            delivered = row[1] or 0
            return {
                "total_sent": total,
                "total_delivered": delivered,
                "total_lost": total - delivered,
                "delivery_rate": delivered / total if total > 0 else 1.0,
                "latency": {
                    "avg_ms": row[2] or 0.0,
                    "min_ms": row[3] or 0.0,
                    "max_ms": row[4] or 0.0,
                    "p95_ms": row[5] or 0.0,
                    "p99_ms": row[6] or 0.0,
                },
            }
        return {
            "total_sent": 0,
            "total_delivered": 0,
            "total_lost": 0,
            "delivery_rate": 1.0,
            "latency": {
                "avg_ms": 0.0,
                "min_ms": 0.0,
                "max_ms": 0.0,
                "p95_ms": 0.0,
                "p99_ms": 0.0,
            },
        }

    def clear(self) -> None:
        self._client.execute(f"TRUNCATE TABLE {self._table}")

    def close(self) -> None:
        self._client.disconnect()


def create_storage(backend: str = "mock", **kwargs) -> MockStorage | ClickHouseStorage:
    if backend == "mock":
        return MockStorage()
    elif backend == "clickhouse":
        return ClickHouseStorage(**kwargs)
    else:
        raise ValueError(f"Unknown storage backend: {backend}")

