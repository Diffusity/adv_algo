"""Graph representations shared by every search algorithm.

Nodes are dense integer ids in ``range(n)``.  Grids use ``id = y * width + x``
so that coordinates and grid neighbours can be computed without dictionaries.
Adjacency is stored as a list of ``(neighbour, weight)`` tuples, which is the
representation the searches actually traverse; no per-expansion allocation is
needed for the graph itself.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence

SQRT2 = math.sqrt(2.0)


@dataclass
class Graph:
    """A weighted graph with optional 2-D coordinates.

    ``radj`` stores predecessors and is required for the reverse Dijkstra
    distance oracle.  For undirected grids it aliases ``adj`` to avoid
    duplicating every edge.
    """

    n: int
    adj: list[list[tuple[int, float]]]
    radj: list[list[tuple[int, float]]]
    width: int | None = None
    height: int | None = None
    xs: list[int] | None = None
    ys: list[int] | None = None
    directed: bool = False
    diagonal: bool = False

    @property
    def is_grid(self) -> bool:
        return self.width is not None and self.height is not None

    def neighbors(self, v: int) -> list[tuple[int, float]]:
        return self.adj[v]

    def predecessors(self, v: int) -> list[tuple[int, float]]:
        return self.radj[v]

    def coord(self, v: int) -> tuple[int, int]:
        if self.xs is None or self.ys is None:
            raise ValueError("graph has no coordinates")
        return self.xs[v], self.ys[v]

    def node_at(self, x: int, y: int) -> int:
        if self.width is None:
            raise ValueError("graph is not a grid")
        return y * self.width + x


def grid_graph(width: int, height: int, diagonal: bool = False) -> Graph:
    """Build a 4- or 8-connected unit grid.

    4-connected edges cost 1.  8-connected diagonal edges cost sqrt(2), so the
    octile heuristic is admissible and consistent.
    """
    if width <= 0 or height <= 0:
        raise ValueError("grid dimensions must be positive")
    n = width * height
    adj: list[list[tuple[int, float]]] = [[] for _ in range(n)]
    directions: list[tuple[int, int, float]] = [
        (1, 0, 1.0),
        (-1, 0, 1.0),
        (0, 1, 1.0),
        (0, -1, 1.0),
    ]
    if diagonal:
        directions.extend(
            [
                (1, 1, SQRT2),
                (1, -1, SQRT2),
                (-1, 1, SQRT2),
                (-1, -1, SQRT2),
            ]
        )
    for y in range(height):
        row = y * width
        for x in range(width):
            u = row + x
            for dx, dy, w in directions:
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    adj[u].append((ny * width + nx, w))
    xs = [x for _y in range(height) for x in range(width)]
    ys = [y for y in range(height) for _x in range(width)]
    return Graph(
        n=n,
        adj=adj,
        radj=adj,  # undirected: predecessors == neighbours
        width=width,
        height=height,
        xs=xs,
        ys=ys,
        directed=False,
        diagonal=diagonal,
    )


def from_edges(
    n: int,
    edges: Iterable[tuple[int, int, float]],
    *,
    directed: bool = False,
    xs: Sequence[int] | None = None,
    ys: Sequence[int] | None = None,
    diagonal: bool = False,
) -> Graph:
    """Build a graph from ``(u, v, weight)`` triples."""
    adj: list[list[tuple[int, float]]] = [[] for _ in range(n)]
    radj: list[list[tuple[int, float]]] = [[] for _ in range(n)]
    for u, v, w in edges:
        if not (0 <= u < n and 0 <= v < n):
            raise ValueError(f"edge endpoint out of range: {(u, v)}")
        wf = float(w)
        adj[u].append((v, wf))
        radj[v].append((u, wf))
        if not directed:
            adj[v].append((u, wf))
            radj[u].append((v, wf))
    return Graph(
        n=n,
        adj=adj,
        radj=radj,
        width=None,
        height=None,
        xs=list(xs) if xs is not None else None,
        ys=list(ys) if ys is not None else None,
        directed=directed,
        diagonal=diagonal,
    )
