"""Mock mesh network node implementation."""

from __future__ import annotations

import time
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mesh_tester.router import MeshRouter


@dataclass
class Message:
    id: str
    payload: str
    from_node: str
    to_node: str | None
    timestamp: float
    hop_count: int = 0

    @classmethod
    def create(cls, payload: str, from_node: str, to_node: str | None = None) -> Message:
        return cls(
            id=str(uuid.uuid4()),
            payload=payload,
            from_node=from_node,
            to_node=to_node,
            timestamp=time.time(),
        )


OnReceiveCallback = Callable[[Message], None]


class MockNode:
    def __init__(
        self,
        node_id: str | None = None,
        name: str | None = None,
        max_inbox_size: int = 1000,
    ):
        self.node_id = node_id or str(uuid.uuid4())[:8]
        self.name = name or f"Node-{self.node_id}"
        self._inbox: deque[Message] = deque(maxlen=max_inbox_size)
        self._router: MeshRouter | None = None
        self._on_receive_callbacks: list[OnReceiveCallback] = []
        self._sent_count = 0
        self._received_count = 0

    @property
    def id(self) -> str:
        return self.node_id

    @property
    def router(self) -> MeshRouter | None:
        return self._router

    @router.setter
    def router(self, router: MeshRouter) -> None:
        self._router = router

    def send_text(self, message: str, dest: str | None = None) -> Message | None:
        if self._router is None:
            raise RuntimeError(f"Node {self.node_id} is not connected to a router")

        msg = Message.create(
            payload=message,
            from_node=self.node_id,
            to_node=dest,
        )
        self._sent_count += 1
        self._router.route_packet(msg)
        return msg

    def receive(self, message: Message) -> None:
        self._inbox.append(message)
        self._received_count += 1
        for callback in self._on_receive_callbacks:
            callback(message)

    def on_receive(self, callback: OnReceiveCallback) -> None:
        self._on_receive_callbacks.append(callback)

    def has_message(self, text: str) -> bool:
        return any(msg.payload == text for msg in self._inbox)

    def get_messages(self, limit: int | None = None) -> list[Message]:
        messages = list(self._inbox)
        if limit:
            return messages[-limit:]
        return messages

    def clear_inbox(self) -> None:
        self._inbox.clear()

    @property
    def sent_count(self) -> int:
        return self._sent_count

    @property
    def received_count(self) -> int:
        return self._received_count

    def __repr__(self) -> str:
        return f"MockNode(id={self.node_id!r}, name={self.name!r})"

