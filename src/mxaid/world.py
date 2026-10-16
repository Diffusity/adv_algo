"""Graph with unknown obstacles (GUO) and exploration accounting.

The world owns the ground truth (``actual``).  An algorithm may only learn a
node's status through :meth:`GUO.explore`, which counts every first-time
sensor/EXP call.  Known status is cached in a byte array so repeated queries
and repeated visits do not pay twice.

This mirrors the SoCS 2024 model: *exploration* is the expensive real-world
operation, while *expansion* is ordinary CPU work.
"""

from __future__ import annotations

from typing import Iterable

UNKNOWN = 0
FREE = 1
BLOCKED = 2


class GUO:
    """A fixed obstacle realisation plus the shared, growing knowledge of it."""

    __slots__ = (
        "graph",
        "n",
        "actual",
        "status",
        "explorations",
        "record",
        "explored_order",
        "blocked_order",
    )

    def __init__(
        self,
        graph,
        actual_blocked: Iterable[int],
        *,
        record: bool = False,
    ) -> None:
        self.graph = graph
        self.n = graph.n
        actual = bytearray(graph.n)
        for v in actual_blocked:
            if not (0 <= v < graph.n):
                raise ValueError(f"blocked node out of range: {v}")
            actual[v] = 1
        self.actual = actual
        self.status = bytearray(graph.n)  # 0 unknown, 1 free, 2 blocked
        self.explorations = 0
        self.record = record
        self.explored_order: list[int] = []
        self.blocked_order: list[int] = []

    # -- exploration -----------------------------------------------------
    def explore(self, v: int) -> bool:
        """Return True iff ``v`` is blocked; count a first-time exploration."""
        s = self.status[v]
        if s == FREE:
            return False
        if s == BLOCKED:
            return True
        self.explorations += 1
        if self.record:
            self.explored_order.append(v)
        if self.actual[v]:
            self.status[v] = BLOCKED
            if self.record:
                self.blocked_order.append(v)
            return True
        self.status[v] = FREE
        return False

    # -- knowledge queries ----------------------------------------------
    def is_blocked(self, v: int) -> bool:
        return self.status[v] == BLOCKED

    def is_free(self, v: int) -> bool:
        return self.status[v] == FREE

    def is_unknown(self, v: int) -> bool:
        return self.status[v] == UNKNOWN

    def blocked_set(self) -> set[int]:
        status = self.status
        return {i for i, s in enumerate(status) if s == BLOCKED}

    def known_counts(self) -> tuple[int, int]:
        free = sum(1 for s in self.status if s == FREE)
        blocked = sum(1 for s in self.status if s == BLOCKED)
        return free, blocked

    # -- multi-query helpers --------------------------------------------
    def snapshot_exploration_count(self) -> int:
        return self.explorations

    def clone_fresh(self) -> "GUO":
        """A new GUO over the same ground truth, with empty knowledge."""
        blocked = [i for i, b in enumerate(self.actual) if b]
        return GUO(self.graph, blocked, record=self.record)
