"""Distance oracles for the dynamic heuristic hD.

Both oracles compute the exact shortest-path distance to the goal in the
*known* graph: known blocked states are removed, known free states are
passable, and unknown states are assumed free (the free-space assumption).
The result is an admissible lower bound on the true remaining cost.

``FullOracle`` rebuilds a reverse Dijkstra from scratch whenever the blocked
set changes.  ``IncrementalOracle`` maintains the same distances under
monotone obstacle insertions: when a node is blocked, only its ancestors in
the shortest-path tree can increase, and those increases are propagated with
a work queue.
"""

from __future__ import annotations

import heapq
from collections import deque
from math import inf

from .graph import Graph
from .world import BLOCKED, FREE, UNKNOWN, GUO

EPS = 1e-9
INF = inf


def reverse_dijkstra(
    graph: Graph,
    goal: int,
    status: bytearray,
    *,
    prefer_free: bool = True,
) -> tuple[list[float], list[int]]:
    """Exact distance-to-goal and a shortest-path successor for every node.

    ``status`` is the GUO status byte array (UNKNOWN/FREE/BLOCKED).  Unknown
    nodes are passable, blocked nodes are not.  Ties in the shortest-path DAG
    prefer known-free successors, which makes the stored paths less risky for
    the tie-breaker; this changes no distances.
    """
    n = graph.n
    dist = [INF] * n
    nxt = [-1] * n
    if status[goal] == BLOCKED:
        return dist, nxt
    dist[goal] = 0.0
    heap: list[tuple[float, int]] = [(0.0, goal)]
    heappop = heapq.heappop
    heappush = heapq.heappush
    while heap:
        d, v = heappop(heap)
        if d > dist[v] + EPS:
            continue
        for p, w in graph.radj[v]:
            if status[p] == BLOCKED:
                continue
            nd = d + w
            dp = dist[p]
            if nd < dp - EPS:
                dist[p] = nd
                nxt[p] = v
                heappush(heap, (nd, p))
            elif abs(nd - dp) <= EPS and nd < INF:
                old = nxt[p]
                if old == -1:
                    nxt[p] = v
                elif prefer_free and status[v] == FREE and status[old] != FREE:
                    nxt[p] = v
                elif status[v] == status[old] and v < old:
                    nxt[p] = v
    return dist, nxt


class _RiskMixin:
    """Shared path-risk computation: unknown cells on the stored shortest path."""

    graph: Graph
    guo: GUO
    goal: int
    n: int
    next: list[int]
    version: int

    _risk_cache: dict[int, float]
    _risk_version: int

    def _risk(self, v: int) -> float:
        status = self.guo.status
        if self.version != self._risk_version:
            self._risk_cache.clear()
            self._risk_version = self.version
        cached = self._risk_cache.get(v)
        if cached is not None:
            return cached
        count = 0
        u = v
        steps = 0
        while u != self.goal:
            s = self.next[u]
            if s < 0:
                count = INF
                break
            if status[s] == UNKNOWN and s != self.goal:
                count += 1
            u = s
            steps += 1
            if steps > self.n:
                count = INF
                break
        self._risk_cache[v] = count
        return count


class FullOracle(_RiskMixin):
    """Rebuild the whole distance table after every discovered obstacle."""

    name = "dynamic-full"

    def __init__(self, graph: Graph, goal: int, guo: GUO) -> None:
        self.graph = graph
        self.goal = goal
        self.guo = guo
        self.n = graph.n
        self.dist: list[float] = [INF] * graph.n
        self.next: list[int] = [-1] * graph.n
        self.builds = 0
        self.version = 0
        self._dirty = True
        self._risk_cache = {}
        self._risk_version = -1
        self.rebuild()

    def rebuild(self) -> None:
        self.dist, self.next = reverse_dijkstra(self.graph, self.goal, self.guo.status)
        self.builds += 1
        self.version += 1
        self._dirty = False

    def h(self, v: int) -> float:
        if self._dirty:
            self.rebuild()
        return self.dist[v]

    def risk(self, v: int) -> float:
        if self._dirty:
            self.rebuild()
        return self._risk(v)

    def notify_blocked(self, v: int) -> None:  # noqa: ARG002
        self._dirty = True
        self.version += 1

    def stats(self) -> dict[str, int]:
        return {"oracle_builds": self.builds, "oracle_updates": 0, "oracle_work": 0}


class IncrementalOracle(_RiskMixin):
    """Maintain hD incrementally under obstacle insertions."""

    name = "dynamic-incremental"

    def __init__(self, graph: Graph, goal: int, guo: GUO) -> None:
        self.graph = graph
        self.goal = goal
        self.guo = guo
        self.n = graph.n
        self.status = guo.status
        self.dist, self.next = reverse_dijkstra(graph, goal, guo.status)
        self.builds = 1
        self.updates = 0
        self.work = 0
        self.decreases = 0  # must stay zero for a monotone increase-only update
        self.version = 1
        self._risk_cache = {}
        self._risk_version = -1

    def h(self, v: int) -> float:
        return self.dist[v]

    def risk(self, v: int) -> float:
        return self._risk(v)

    def notify_blocked(self, v: int) -> None:
        self.updates += 1
        self._block(v)

    def _block(self, v: int) -> None:
        """Remove ``v`` and repair the shortest-path tree.

        A naive "recompute my neighbours" fixpoint is wrong: two nodes in a
        cycle that just lost its only connection to the goal can keep giving
        each other finite (but ever-growing) distances.  The correct
        increase-only update first invalidates the whole subtree of the
        shortest-path tree that used ``v``, then runs Dijkstra on that subtree
        with boundary edges into the still-valid part of the tree.  Nodes with
        no boundary path correctly become infinite.
        """
        if self.status[v] != BLOCKED:
            return

        graph = self.graph
        status = self.status
        dist = self.dist
        nxt = self.next

        # 1. Collect every node whose current shortest path uses v.  The next
        #    pointers form a tree rooted at the goal, so this is the subtree
        #    rooted at v when traversed backwards.
        affected: set[int] = {v}
        stack = [v]
        while stack:
            x = stack.pop()
            for p, _w in graph.radj[x]:
                if p not in affected and nxt[p] == x:
                    affected.add(p)
                    stack.append(p)

        # 2. Invalidate the subtree.
        for p in affected:
            dist[p] = INF
            nxt[p] = -1

        # 3. Boundary candidates: edges from the subtree to nodes whose
        #    distances are still valid.
        heap: list[tuple[float, int, int]] = []
        for p in affected:
            if p == self.goal or status[p] == BLOCKED:
                continue
            for s, w in graph.adj[p]:
                if s in affected or status[s] == BLOCKED:
                    continue
                if dist[s] < INF:
                    heapq.heappush(heap, (w + dist[s], p, s))
            self.work += 1

        # 4. Dijkstra repair inside the subtree, using boundary distances.
        while heap:
            d, p, s = heapq.heappop(heap)
            if dist[p] < INF:
                continue
            if status[p] == BLOCKED:
                continue
            dist[p] = d
            nxt[p] = s
            self.work += 1
            for q, w in graph.radj[p]:
                if q in affected and dist[q] == INF and status[q] != BLOCKED:
                    heapq.heappush(heap, (w + d, q, p))

        self.version += 1

    def stats(self) -> dict[str, int]:
        return {
            "oracle_builds": self.builds,
            "oracle_updates": self.updates,
            "oracle_work": self.work,
        }
