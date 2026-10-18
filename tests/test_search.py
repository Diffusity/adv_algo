import random
from math import inf

from mxaid import GUO, grid_graph
from mxaid.graph import from_edges
from mxaid.reference import dijkstra_ground_truth, path_cost, validate_path
from mxaid.search import run_astar, run_dijkstra, run_mxa_full, run_mxa_id

ALGORITHMS = (run_dijkstra, run_astar, run_mxa_full, run_mxa_id)


def _check_instance(graph, blocked, start, goal):
    truth_cost, _truth_path = dijkstra_ground_truth(graph, start, goal, blocked)
    for runner in ALGORITHMS:
        guo = GUO(graph, blocked)
        result = runner(graph, guo, start, goal)
        if truth_cost == inf:
            assert not result.found, (runner.__name__, result.cost)
            continue
        assert result.found, (runner.__name__, truth_cost)
        assert abs(result.cost - truth_cost) < 1e-9, (runner.__name__, result.cost, truth_cost)
        validate_path(graph, result.path, start, goal, blocked)
        assert abs(path_cost(graph, result.path) - truth_cost) < 1e-9
        assert result.explorations >= result.expansions
        assert result.generated >= 1 or start == goal


def test_random_small_grids_are_optimal():
    rng = random.Random(2024)
    for diagonal in (False, True):
        for _case in range(120):
            width = rng.randint(3, 7)
            height = rng.randint(3, 7)
            graph = grid_graph(width, height, diagonal=diagonal)
            density = rng.uniform(0.0, 0.45)
            blocked = {v for v in range(graph.n) if rng.random() < density}
            start = rng.randrange(graph.n)
            goal = rng.randrange(graph.n)
            blocked.discard(start)
            blocked.discard(goal)
            _check_instance(graph, blocked, start, goal)


def test_start_equals_goal():
    graph = grid_graph(4, 4)
    blocked = {5, 6}
    for runner in ALGORITHMS:
        guo = GUO(graph, blocked)
        result = runner(graph, guo, 0, 0)
        assert result.found and result.cost == 0.0 and result.path == [0]


def test_blocked_start_and_goal():
    graph = grid_graph(4, 4)
    for runner in ALGORITHMS:
        guo = GUO(graph, {0})
        result = runner(graph, guo, 0, 15)
        assert not result.found
        assert result.explorations == 1
    for runner in ALGORITHMS:
        guo = GUO(graph, {15})
        result = runner(graph, guo, 0, 15)
        assert not result.found


def test_weighted_undirected_graph():
    edges = [
        (0, 1, 1.0),
        (1, 2, 2.0),
        (0, 2, 5.0),
        (2, 3, 1.0),
        (1, 3, 6.0),
        (3, 4, 1.0),
    ]
    graph = from_edges(5, edges)
    blocked = {2}
    _check_instance(graph, blocked, 0, 4)
    _check_instance(graph, blocked, 0, 3)


def test_directed_graph_search():
    edges = [
        (0, 1, 1.0),
        (1, 2, 1.0),
        (0, 2, 5.0),
        (2, 3, 1.0),
        (1, 3, 4.0),
    ]
    graph = from_edges(4, edges, directed=True)
    _check_instance(graph, set(), 0, 3)
    _check_instance(graph, {1}, 0, 3)


def test_multi_query_reuses_knowledge_and_never_repeats_exploration():
    graph = grid_graph(8, 8, diagonal=True)
    rng = random.Random(5)
    blocked = {rng.randrange(graph.n) for _ in range(18)}
    free = [v for v in range(graph.n) if v not in blocked]
    assert len(free) >= 6
    guo = GUO(graph, blocked, record=True)
    queries = [(free[0], free[-1]), (free[1], free[-2]), (free[2], free[-3])]
    for start, goal in queries:
        truth_cost, _ = dijkstra_ground_truth(graph, start, goal, blocked)
        result = run_mxa_id(graph, guo, start, goal)
        if truth_cost == inf:
            assert not result.found
        else:
            assert result.found
            assert abs(result.cost - truth_cost) < 1e-9
    # The exploration log contains each first-time exploration exactly once.
    assert len(guo.explored_order) == len(set(guo.explored_order))
    assert len(guo.explored_order) == guo.explorations
    # Known status is cached: querying it again costs no exploration.
    before = guo.explorations
    for v in list(guo.blocked_order)[:3]:
        assert guo.explore(v) is True
    for v in list(guo.explored_order)[:3]:
        if not guo.is_blocked(v):
            assert guo.explore(v) is False
    assert guo.explorations == before
