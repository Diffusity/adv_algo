"""The shared high-level search engine.

All four algorithms use the same lazy-exploration loop; they differ only in
the heuristic provider, the tie-break key, and whether the dynamic heuristic
is re-checked before expansion (MXA*).

The loop implements the GUO model faithfully:

* a node's status is explored only when the node is selected, not when it is
  generated (lazy exploration);
* a blocked node is discarded and its outgoing edges are never traversed;
* a free node is expanded, generating all currently passable neighbours;
* the goal is accepted only after it has been explored and found free.
"""

from __future__ import annotations

import time
import tracemalloc
from dataclasses import dataclass, field
from math import inf
from typing import Any

from .graph import Graph
from .heap import IndexedMinHeap
from .heuristics import StaticHeuristic, ZeroHeuristic
from .oracles import FullOracle, IncrementalOracle
from .world import GUO

EPS = 1e-9
INF = inf


@dataclass
class SearchResult:
    algorithm: str
    found: bool
    path: list[int]
    cost: float
    explorations: int
    expansions: int
    generated: int
    reopened: int
    reinserted: int
    runtime_s: float
    setup_s: float = 0.0
    peak_memory_kb: float = 0.0
    max_open: int = 0
    oracle_builds: int = 0
    oracle_updates: int = 0
    oracle_work: int = 0
    trace: dict[str, Any] | None = None

    @property
    def path_cost(self) -> float:
        return self.cost

    def to_row(self) -> dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "found": int(self.found),
            "cost": self.cost if self.found else float("nan"),
            "path_len": len(self.path),
            "explorations": self.explorations,
            "expansions": self.expansions,
            "generated": self.generated,
            "reopened": self.reopened,
            "reinserted": self.reinserted,
            "runtime_s": self.runtime_s,
            "setup_s": self.setup_s,
            "total_runtime_s": self.runtime_s + self.setup_s,
            "peak_memory_kb": self.peak_memory_kb,
            "max_open": self.max_open,
            "oracle_builds": self.oracle_builds,
            "oracle_updates": self.oracle_updates,
            "oracle_work": self.oracle_work,
        }


class Searcher:
    """One lazy A*-style search on a GUO."""

    def __init__(
        self,
        graph: Graph,
        guo: GUO,
        start: int,
        goal: int,
        heuristic: Any,
        *,
        name: str = "search",
        tie_break: str = "h",
        recheck_h: bool = False,
        trace: bool = False,
        trace_stride: int = 1,
    ) -> None:
        self.graph = graph
        self.guo = guo
        self.start = start
        self.goal = goal
        self.heuristic = heuristic
        self.name = name
        self.tie_break = tie_break
        self.recheck_h = recheck_h
        self.trace = trace
        self.trace_stride = max(1, trace_stride)

    def _key(self, v: int, gv: float, hv: float) -> tuple:
        f = gv + hv
        if self.tie_break == "id":
            return (f, v)
        if self.tie_break == "h":
            return (f, hv, v)
        if self.tie_break == "risk":
            return (f, self.heuristic.risk(v), hv, v)
        if self.tie_break == "h_risk":
            return (f, hv, self.heuristic.risk(v), v)
        raise ValueError(f"unknown tie-break: {self.tie_break}")

    def run(self) -> SearchResult:
        t0 = time.perf_counter()
        graph = self.graph
        guo = self.guo
        heuristic = self.heuristic
        start = self.start
        goal = self.goal
        n = graph.n

        g = [INF] * n
        parent = [-1] * n
        closed_g = [INF] * n
        expanded = bytearray(n)
        heap = IndexedMinHeap(n)

        start_explorations = guo.explorations
        expansions = 0
        generated = 0
        reopened = 0
        reinserted = 0
        max_open = 0
        found = False
        cost = INF
        path: list[int] = []
        trace_data: dict[str, Any] | None = None
        if self.trace:
            trace_data = {
                "expanded": [],
                "explored": [],
                "blocked": [],
                "frames": [],
                "start": start,
                "goal": goal,
            }

        start_was_unknown = guo.is_unknown(start)
        if guo.explore(start):
            if self.trace and start_was_unknown:
                trace_data["explored"].append(start)  # type: ignore[index]
                trace_data["blocked"].append(start)  # type: ignore[index]
                self._append_frame(trace_data, expansions, heap)
        elif start == goal:
            if self.trace and start_was_unknown:
                trace_data["explored"].append(start)  # type: ignore[index]
                self._append_frame(trace_data, expansions, heap)
            return self._finish(
                t0,
                start_explorations,
                found=True,
                cost=0.0,
                path=[start],
                expansions=0,
                generated=0,
                reopened=0,
                reinserted=0,
                max_open=0,
                trace_data=trace_data,
            )
        else:
            if self.trace and start_was_unknown:
                trace_data["explored"].append(start)  # type: ignore[index]
            h0 = heuristic.h(start)
            if h0 < INF:
                g[start] = 0.0
                heap.insert(start, self._key(start, 0.0, h0))
                max_open = 1
            if self.trace:
                self._append_frame(trace_data, expansions, heap)

            while len(heap):
                u = heap.pop_min()
                if guo.is_blocked(u):
                    continue
                if expanded[u] and g[u] >= closed_g[u] - EPS:
                    continue

                h = heuristic.h(u)
                if h >= INF:
                    continue
                f = g[u] + h
                if self.recheck_h and len(heap):
                    f_min = heap.min_key()[0]
                    if f > f_min + EPS:
                        heap.insert(u, self._key(u, g[u], h))
                        reinserted += 1
                        if len(heap) > max_open:
                            max_open = len(heap)
                        continue

                was_unknown = guo.is_unknown(u)
                blocked = guo.explore(u)
                if self.trace and was_unknown:
                    trace_data["explored"].append(u)  # type: ignore[index]
                if blocked:
                    if self.trace and was_unknown:
                        trace_data["blocked"].append(u)  # type: ignore[index]
                    heuristic.notify_blocked(u)
                    if self.trace:
                        self._append_frame(trace_data, expansions, heap)
                    continue

                if u == goal:
                    found = True
                    cost = g[u]
                    path = self._reconstruct(parent, start, goal)
                    if self.trace:
                        self._append_frame(trace_data, expansions, heap)
                    break

                if expanded[u]:
                    reopened += 1
                expanded[u] = 1
                closed_g[u] = g[u]
                expansions += 1
                if self.trace:
                    trace_data["expanded"].append(u)  # type: ignore[index]

                for v, w in graph.adj[u]:
                    if guo.is_blocked(v):
                        continue
                    ng = g[u] + w
                    if ng >= g[v] - EPS:
                        continue
                    if expanded[v] and ng >= closed_g[v] - EPS:
                        continue
                    hv = heuristic.h(v)
                    if hv >= INF:
                        continue
                    if g[v] == INF:
                        generated += 1
                    g[v] = ng
                    parent[v] = u
                    key = self._key(v, ng, hv)
                    if heap.contains(v):
                        heap.update(v, key)
                    else:
                        heap.insert(v, key)
                    if len(heap) > max_open:
                        max_open = len(heap)

                if self.trace:
                    self._append_frame(trace_data, expansions, heap)

        return self._finish(
            t0,
            start_explorations,
            found=found,
            cost=cost,
            path=path,
            expansions=expansions,
            generated=generated,
            reopened=reopened,
            reinserted=reinserted,
            max_open=max_open,
            trace_data=trace_data,
        )

    def _finish(
        self,
        t0: float,
        start_explorations: int,
        *,
        found: bool,
        cost: float,
        path: list[int],
        expansions: int,
        generated: int,
        reopened: int,
        reinserted: int,
        max_open: int,
        trace_data: dict[str, Any] | None,
    ) -> SearchResult:
        runtime = time.perf_counter() - t0
        stats = self.heuristic.stats()
        if trace_data is not None:
            trace_data["path"] = path
        return SearchResult(
            algorithm=self.name,
            found=found,
            path=path,
            cost=cost,
            explorations=self.guo.explorations - start_explorations,
            expansions=expansions,
            generated=generated,
            reopened=reopened,
            reinserted=reinserted,
            runtime_s=runtime,
            max_open=max_open,
            oracle_builds=int(stats.get("oracle_builds", 0)),
            oracle_updates=int(stats.get("oracle_updates", 0)),
            oracle_work=int(stats.get("oracle_work", 0)),
            trace=trace_data,
        )

    @staticmethod
    def _append_frame(trace_data: dict[str, Any], expansions: int, heap: IndexedMinHeap) -> None:
        trace_data["frames"].append(
            {
                "explored": len(trace_data["explored"]),
                "blocked": len(trace_data["blocked"]),
                "expanded": expansions,
                "open": heap.items(),
            }
        )

    @staticmethod
    def _reconstruct(parent: list[int], start: int, goal: int) -> list[int]:
        path: list[int] = []
        cur = goal
        while cur != -1:
            path.append(cur)
            if cur == start:
                path.reverse()
                return path
            cur = parent[cur]
        raise RuntimeError("broken parent chain during path reconstruction")


# ---------------------------------------------------------------------------
# Convenience constructors used by experiments and tests
# ---------------------------------------------------------------------------

def run_dijkstra(graph: Graph, guo: GUO, start: int, goal: int, **kw: Any) -> SearchResult:
    return Searcher(
        graph, guo, start, goal, ZeroHeuristic(), name="Dijkstra", tie_break="id", **kw
    ).run()


def run_astar(graph: Graph, guo: GUO, start: int, goal: int, **kw: Any) -> SearchResult:
    h = StaticHeuristic(graph, goal)
    return Searcher(graph, guo, start, goal, h, name="A*", tie_break="h", **kw).run()


def run_mxa_full(graph: Graph, guo: GUO, start: int, goal: int, **kw: Any) -> SearchResult:
    h = FullOracle(graph, goal, guo)
    return Searcher(
        graph, guo, start, goal, h, name="MXA*", tie_break="h", recheck_h=True, **kw
    ).run()


def run_mxa_id(graph: Graph, guo: GUO, start: int, goal: int, **kw: Any) -> SearchResult:
    h = IncrementalOracle(graph, goal, guo)
    return Searcher(
        graph, guo, start, goal, h, name="MXA*-ID", tie_break="h_risk", recheck_h=True, **kw
    ).run()


def run_astar_memory(graph: Graph, guo: GUO, start: int, goal: int, **kw: Any) -> SearchResult:
    """A* with a shared knowledge base (multi-query baseline)."""
    h = StaticHeuristic(graph, goal)
    return Searcher(
        graph, guo, start, goal, h, name="A*+memory", tie_break="h", **kw
    ).run()
