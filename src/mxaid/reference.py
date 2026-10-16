"""Omniscient reference search.

This is *not* a GUO algorithm: it is allowed to read the ground-truth blocked
set.  It provides the optimal path cost used to validate every online search.
"""

from __future__ import annotations

import heapq
from math import inf
from typing import Iterable

from .graph import Graph


def dijkstra_ground_truth(
    graph: Graph,
    start: int,
    goal: int,
    blocked: Iterable[int],
) -> tuple[float, list[int]]:
    """Shortest path with full knowledge.  Returns ``(inf, [])`` if none."""
    blocked_set = set(blocked)
    if start in blocked_set or goal in blocked_set:
        return inf, []
    n = graph.n
    dist = [inf] * n
    parent = [-1] * n
    dist[start] = 0.0
    heap: list[tuple[float, int]] = [(0.0, start)]
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist[u]:
            continue
        if u == goal:
            break
        for v, w in graph.adj[u]:
            if v in blocked_set:
                continue
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                parent[v] = u
                heapq.heappush(heap, (nd, v))
    if dist[goal] == inf:
        return inf, []
    path: list[int] = []
    cur = goal
    while cur != -1:
        path.append(cur)
        if cur == start:
            break
        cur = parent[cur]
    path.reverse()
    return dist[goal], path


def path_cost(graph: Graph, path: list[int]) -> float:
    total = 0.0
    for a, b in zip(path, path[1:]):
        for v, w in graph.adj[a]:
            if v == b:
                total += w
                break
        else:
            raise ValueError(f"path uses non-edge {a} -> {b}")
    return total


def validate_path(
    graph: Graph,
    path: list[int],
    start: int,
    goal: int,
    blocked: Iterable[int],
) -> None:
    """Raise ``ValueError`` if a returned path is not a valid free path."""
    blocked_set = set(blocked)
    if not path:
        raise ValueError("empty path")
    if path[0] != start or path[-1] != goal:
        raise ValueError("path endpoints do not match start/goal")
    for v in path:
        if v in blocked_set:
            raise ValueError(f"path contains blocked node {v}")
    for a, b in zip(path, path[1:]):
        if all(v != b for v, _ in graph.adj[a]):
            raise ValueError(f"path uses non-edge {a} -> {b}")
