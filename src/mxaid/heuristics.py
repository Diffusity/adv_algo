"""Static heuristics.

The GUO problem is defined on a graph, so the heuristic only needs ``h(v)``.
Dynamic heuristics (MXA*) live in :mod:`mxaid.oracles`.
"""

from __future__ import annotations

import math

from .graph import Graph


class ZeroHeuristic:
    """Dijkstra's heuristic."""

    name = "zero"

    def h(self, v: int) -> float:  # noqa: ARG002
        return 0.0

    def risk(self, v: int) -> int:  # noqa: ARG002
        return 0

    def notify_blocked(self, v: int) -> None:  # noqa: ARG002
        return None

    def stats(self) -> dict[str, int]:
        return {"oracle_builds": 0, "oracle_updates": 0, "oracle_work": 0}


class StaticHeuristic:
    """Precomputed Manhattan/octile distance (or zero without coordinates)."""

    name = "static"

    def __init__(self, graph: Graph, goal: int, mode: str = "auto") -> None:
        self.graph = graph
        self.goal = goal
        if mode == "auto":
            if graph.xs is None or graph.ys is None:
                mode = "zero"
            elif graph.diagonal:
                mode = "octile"
            else:
                mode = "manhattan"
        self.mode = mode
        self.values = [0.0] * graph.n
        if mode != "zero":
            gx, gy = graph.coord(goal)
            xs, ys = graph.xs, graph.ys
            assert xs is not None and ys is not None
            if mode == "manhattan":
                for v in range(graph.n):
                    self.values[v] = abs(xs[v] - gx) + abs(ys[v] - gy)
            elif mode == "octile":
                root2_minus_2 = math.sqrt(2.0) - 2.0
                for v in range(graph.n):
                    dx = abs(xs[v] - gx)
                    dy = abs(ys[v] - gy)
                    self.values[v] = (dx + dy) + root2_minus_2 * min(dx, dy)
            else:
                raise ValueError(f"unknown static heuristic mode: {mode}")

    def h(self, v: int) -> float:
        return self.values[v]

    def risk(self, v: int) -> int:  # noqa: ARG002
        return 0

    def notify_blocked(self, v: int) -> None:  # noqa: ARG002
        return None

    def stats(self) -> dict[str, int]:
        return {"oracle_builds": 0, "oracle_updates": 0, "oracle_work": 0}
