"""Synthetic GUO benchmark maps.

Four topologies are provided so the evaluation is not tied to one obstacle
pattern:

* ``random``  - independent obstacles at a target density.
* ``maze``    - a perfect randomized-DFS maze, optionally with loops.
* ``rooms``   - wall-and-door rooms with extra clutter inside rooms.
* ``city``    - solid building blocks separated by a connected street grid.

Every generator returns a connected instance: the start and goal are free and
a path exists in the ground-truth graph.  Generation is deterministic from
``MapSpec.seed``.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable

from .graph import Graph, grid_graph


@dataclass(frozen=True)
class MapSpec:
    topology: str
    width: int
    height: int
    density: float = 0.2
    seed: int = 0
    diagonal: bool = True
    random_endpoints: bool = True

    @property
    def name(self) -> str:
        return f"{self.topology}-{self.width}x{self.height}-d{self.density:g}-s{self.seed}"


@dataclass
class MapInstance:
    spec: MapSpec
    graph: Graph
    blocked: set[int]
    start: int
    goal: int

    @property
    def density(self) -> float:
        return len(self.blocked) / self.graph.n


def _reachable(graph: Graph, start: int, goal: int, blocked: set[int]) -> bool:
    if start in blocked or goal in blocked:
        return False
    seen = bytearray(graph.n)
    seen[start] = 1
    stack = [start]
    adj = graph.adj
    while stack:
        u = stack.pop()
        if u == goal:
            return True
        for v, _w in adj[u]:
            if not seen[v] and v not in blocked:
                seen[v] = 1
                stack.append(v)
    return False


def _pick_endpoints(graph: Graph, blocked: set[int], rng: random.Random) -> tuple[int, int]:
    free = [v for v in range(graph.n) if v not in blocked]
    if len(free) < 2:
        raise ValueError("map has fewer than two free cells")
    # Prefer endpoints that are reasonably far apart; this avoids trivial
    # instances where the path is a single step.
    min_dist = max(2, (graph.width or 2) // 3)
    width = graph.width or 1
    for _ in range(100):
        a, b = rng.sample(free, 2)
        ax, ay = a % width, a // width
        bx, by = b % width, b // width
        if abs(ax - bx) + abs(ay - by) >= min_dist:
            return a, b
    return a, b


def _carve_corridor(
    graph: Graph, blocked: set[int], start: int, goal: int
) -> None:
    """Last-resort connectivity repair: clear an L-shaped corridor."""
    width = graph.width
    assert width is not None
    sx, sy = start % width, start // width
    gx, gy = goal % width, goal // width
    x, y = sx, sy
    while x != gx:
        x += 1 if gx > x else -1
        blocked.discard(y * width + x)
    while y != gy:
        y += 1 if gy > y else -1
        blocked.discard(y * width + x)


def random_map(spec: MapSpec) -> MapInstance:
    graph = grid_graph(spec.width, spec.height, diagonal=spec.diagonal)
    rng = random.Random(spec.seed)
    density = spec.density
    for _attempt in range(60):
        blocked = {v for v in range(graph.n) if rng.random() < density}
        if spec.random_endpoints:
            start, goal = _pick_endpoints(graph, blocked, rng)
        else:
            start, goal = 0, graph.n - 1
        blocked.discard(start)
        blocked.discard(goal)
        if _reachable(graph, start, goal, blocked):
            return MapInstance(spec, graph, blocked, start, goal)
        density *= 0.97
    # Fallback for very high density: clear a corridor.
    if not spec.random_endpoints:
        start, goal = 0, graph.n - 1
    else:
        start, goal = _pick_endpoints(graph, blocked, rng)
    _carve_corridor(graph, blocked, start, goal)
    return MapInstance(spec, graph, blocked, start, goal)


def maze_map(spec: MapSpec) -> MapInstance:
    """Randomized depth-first maze on odd cells, with optional loops.

    ``density`` is interpreted as the fraction of interior walls opened to
    create loops; 0 gives a perfect maze.
    """
    width = spec.width if spec.width % 2 == 1 else spec.width - 1
    height = spec.height if spec.height % 2 == 1 else spec.height - 1
    if width < 3 or height < 3:
        raise ValueError("maze needs at least 3x3 cells")
    graph = grid_graph(width, height, diagonal=spec.diagonal)
    rng = random.Random(spec.seed)
    blocked = {v for v in range(graph.n)}
    start = 1 * width + 1
    goal = (height - 2) * width + (width - 2)

    def idx(x: int, y: int) -> int:
        return y * width + x

    stack = [start]
    blocked.discard(start)
    visited = {start}
    while stack:
        x, y = stack[-1] % width, stack[-1] // width
        candidates = []
        for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
            nx, ny = x + dx, y + dy
            if 1 <= nx < width - 1 and 1 <= ny < height - 1:
                nv = idx(nx, ny)
                if nv not in visited:
                    candidates.append((dx, dy, nv))
        if not candidates:
            stack.pop()
            continue
        dx, dy, nv = rng.choice(candidates)
        blocked.discard(idx(x + dx // 2, y + dy // 2))
        blocked.discard(nv)
        visited.add(nv)
        stack.append(nv)

    # Open extra walls to create loops, keeping the border intact.
    loop_prob = min(0.5, max(0.0, spec.density))
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            v = idx(x, y)
            if v in blocked and rng.random() < loop_prob:
                free_neighbors = 0
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nv = idx(x + dx, y + dy)
                    if nv not in blocked:
                        free_neighbors += 1
                if free_neighbors >= 2:
                    blocked.discard(v)

    blocked.discard(start)
    blocked.discard(goal)
    if not _reachable(graph, start, goal, blocked):
        _carve_corridor(graph, blocked, start, goal)
    return MapInstance(spec, graph, blocked, start, goal)


def rooms_map(spec: MapSpec) -> MapInstance:
    graph = grid_graph(spec.width, spec.height, diagonal=spec.diagonal)
    rng = random.Random(spec.seed + 7919)
    width, height = spec.width, spec.height
    room = max(4, min(width, height) // 4)
    blocked: set[int] = set()

    # Wall grid with one door per wall segment.
    for x in range(room, width, room):
        door_y = rng.randrange(1, max(2, height - 1))
        for y in range(height):
            if abs(y - door_y) > 0:
                blocked.add(y * width + x)
    for y in range(room, height, room):
        door_x = rng.randrange(1, max(2, width - 1))
        for x in range(width):
            if abs(x - door_x) > 0:
                blocked.add(y * width + x)

    # Clutter inside rooms, but never on the wall grid (doors stay open).
    for v in range(graph.n):
        x, y = v % width, v // width
        on_wall = (x % room == 0 and x != 0) or (y % room == 0 and y != 0)
        if not on_wall and rng.random() < spec.density:
            blocked.add(v)

    if spec.random_endpoints:
        start, goal = _pick_endpoints(graph, blocked, rng)
    else:
        start, goal = 0, graph.n - 1
    blocked.discard(start)
    blocked.discard(goal)
    if not _reachable(graph, start, goal, blocked):
        _carve_corridor(graph, blocked, start, goal)
    return MapInstance(spec, graph, blocked, start, goal)


def city_map(spec: MapSpec) -> MapInstance:
    graph = grid_graph(spec.width, spec.height, diagonal=spec.diagonal)
    rng = random.Random(spec.seed + 104729)
    width, height = spec.width, spec.height
    block = max(4, min(width, height) // 8)
    blocked: set[int] = set()

    # Solid buildings on a street grid.  ``density`` is the probability that a
    # building block is present; streets themselves remain free.
    for by in range(1, height - 1, block):
        for bx in range(1, width - 1, block):
            if rng.random() >= spec.density:
                continue
            for y in range(by, min(by + block - 1, height - 1)):
                for x in range(bx, min(bx + block - 1, width - 1)):
                    blocked.add(y * width + x)

    if spec.random_endpoints:
        free = [v for v in range(graph.n) if v not in blocked]
        # Keep endpoints on the outer street ring where possible.
        ring = [
            v
            for v in free
            if (v % width in (0, width - 1)) or (v // width in (0, height - 1))
        ]
        pool = ring if len(ring) >= 2 else free
        start, goal = rng.sample(pool, 2)
    else:
        start, goal = 0, graph.n - 1
    blocked.discard(start)
    blocked.discard(goal)
    if not _reachable(graph, start, goal, blocked):
        _carve_corridor(graph, blocked, start, goal)
    return MapInstance(spec, graph, blocked, start, goal)


_GENERATORS = {
    "random": random_map,
    "maze": maze_map,
    "rooms": rooms_map,
    "city": city_map,
}


def generate_map(spec: MapSpec) -> MapInstance:
    try:
        generator = _GENERATORS[spec.topology]
    except KeyError as exc:
        raise ValueError(f"unknown topology: {spec.topology}") from exc
    return generator(spec)
