import random
from math import inf

from mxaid import GUO, grid_graph
from mxaid.graph import from_edges
from mxaid.oracles import EPS, IncrementalOracle, reverse_dijkstra
from mxaid.reference import dijkstra_ground_truth
from mxaid.world import BLOCKED, UNKNOWN


def _discover_blocked(guo: GUO, nodes: list[int]) -> None:
    for v in nodes:
        assert guo.explore(v) is True


def _same(a: float, b: float) -> bool:
    if a == inf or b == inf:
        return a == b
    return abs(a - b) < 1e-9


def test_reverse_dijkstra_matches_ground_truth_on_undirected_grid():
    rng = random.Random(7)
    graph = grid_graph(7, 6, diagonal=True)
    blocked = {rng.randrange(graph.n) for _ in range(10)}
    goal = 0
    blocked.discard(goal)
    status = bytearray(graph.n)
    for v in blocked:
        status[v] = BLOCKED
    dist, nxt = reverse_dijkstra(graph, goal, status)
    assert dist[goal] == 0.0
    for v in range(graph.n):
        if status[v] == BLOCKED:
            assert dist[v] == inf
            continue
        truth, _ = dijkstra_ground_truth(graph, v, goal, blocked)
        assert abs(dist[v] - truth) < 1e-9, (v, dist[v], truth)
        if dist[v] < inf:
            # Follow the stored shortest-path tree to the goal.
            u = v
            total = 0.0
            steps = 0
            while u != goal:
                s = nxt[u]
                assert s >= 0
                total += next(w for x, w in graph.adj[u] if x == s)
                u = s
                steps += 1
                assert steps <= graph.n
            assert abs(total - dist[v]) < 1e-9


def test_incremental_matches_full_after_each_discovery():
    rng = random.Random(11)
    graph = grid_graph(8, 8, diagonal=True)
    actual_blocked = {rng.randrange(graph.n) for _ in range(14)}
    goal = graph.n - 1
    actual_blocked.discard(0)
    actual_blocked.discard(goal)
    guo = GUO(graph, actual_blocked)
    oracle = IncrementalOracle(graph, goal, guo)
    order = list(actual_blocked)
    rng.shuffle(order)
    for v in order:
        _discover_blocked(guo, [v])
        oracle.notify_blocked(v)
        full, _ = reverse_dijkstra(graph, goal, guo.status)
        for u in range(graph.n):
            assert _same(oracle.dist[u], full[u]), (v, u, oracle.dist[u], full[u])
    assert oracle.decreases == 0


def test_incremental_matches_full_with_free_discoveries():
    rng = random.Random(19)
    graph = grid_graph(6, 6, diagonal=False)
    actual_blocked = {rng.randrange(graph.n) for _ in range(7)}
    goal = 0
    actual_blocked.discard(goal)
    guo = GUO(graph, actual_blocked)
    oracle = IncrementalOracle(graph, goal, guo)
    # Explore a mixture of free and blocked nodes in random order.
    order = list(range(graph.n))
    rng.shuffle(order)
    for v in order[:25]:
        guo.explore(v)
        if guo.is_blocked(v):
            oracle.notify_blocked(v)
        full, _ = reverse_dijkstra(graph, goal, guo.status)
        for u in range(graph.n):
            assert _same(oracle.dist[u], full[u])


def test_risk_is_consistent_with_stored_path():
    rng = random.Random(23)
    graph = grid_graph(6, 6, diagonal=True)
    actual_blocked = {rng.randrange(graph.n) for _ in range(6)}
    goal = graph.n - 1
    actual_blocked.discard(goal)
    guo = GUO(graph, actual_blocked)
    oracle = IncrementalOracle(graph, goal, guo)
    for v in range(graph.n):
        if oracle.dist[v] == inf:
            continue
        # Count unknown intermediate nodes on the stored path directly.
        count = 0
        u = v
        steps = 0
        while u != goal:
            s = oracle.next[u]
            assert s >= 0
            assert guo.status[s] != BLOCKED
            if guo.status[s] == UNKNOWN and s != goal:
                count += 1
            u = s
            steps += 1
            assert steps <= graph.n
        assert oracle.risk(v) == count


def test_directed_graph_distances():
    # A tiny directed graph: 0 -> 1 -> 2, 0 -> 2 (expensive), 2 is goal.
    graph = from_edges(3, [(0, 1, 1.0), (1, 2, 1.0), (0, 2, 5.0)], directed=True)
    status = bytearray(3)
    dist, nxt = reverse_dijkstra(graph, 2, status)
    assert dist == [2.0, 1.0, 0.0]
    assert nxt[0] == 1
