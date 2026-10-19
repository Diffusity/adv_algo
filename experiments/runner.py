"""Execute one benchmark instance or one repeated-query session."""

from __future__ import annotations

import random
import time
import tracemalloc
from math import inf, isfinite

from mxaid import GUO
from mxaid.heuristics import StaticHeuristic, ZeroHeuristic
from mxaid.maps import MapSpec, generate_map
from mxaid.oracles import FullOracle, IncrementalOracle
from mxaid.reference import dijkstra_ground_truth
from mxaid.search import SearchResult, Searcher

ALGORITHM_LABELS = {
    "dijkstra": "Dijkstra",
    "astar": "A*",
    "mxa_full": "MXA*",
    "mxa_inc": "MXA*-inc",
    "mxa_id": "MXA*-ID",
}


def build_search(key: str, graph, guo: GUO, goal: int):
    """Return ``(heuristic, tie_break, recheck_h, label)``."""
    if key == "dijkstra":
        return ZeroHeuristic(), "id", False, ALGORITHM_LABELS[key]
    if key == "astar":
        return StaticHeuristic(graph, goal), "h", False, ALGORITHM_LABELS[key]
    if key == "mxa_full":
        return FullOracle(graph, goal, guo), "h", True, ALGORITHM_LABELS[key]
    if key == "mxa_inc":
        return IncrementalOracle(graph, goal, guo), "h", True, ALGORITHM_LABELS[key]
    if key == "mxa_id":
        return IncrementalOracle(graph, goal, guo), "h_risk", True, ALGORITHM_LABELS[key]
    raise ValueError(f"unknown algorithm: {key}")


def run_algorithm(
    key: str,
    graph,
    guo: GUO,
    start: int,
    goal: int,
    *,
    measure_memory: bool = False,
    trace: bool = False,
    trace_stride: int = 1,
) -> SearchResult:
    """Run one algorithm, timing oracle construction separately from search."""
    if measure_memory and tracemalloc.is_tracing():
        raise RuntimeError("tracemalloc already tracing")

    if measure_memory:
        tracemalloc.start()

    t_setup = time.perf_counter()
    heuristic, tie_break, recheck_h, label = build_search(key, graph, guo, goal)
    setup_s = time.perf_counter() - t_setup

    result = Searcher(
        graph,
        guo,
        start,
        goal,
        heuristic,
        name=label,
        tie_break=tie_break,
        recheck_h=recheck_h,
        trace=trace,
        trace_stride=trace_stride,
    ).run()
    result.setup_s = setup_s

    if measure_memory:
        peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        result.peak_memory_kb = peak / 1024.0
    return result


def _base_row(task: dict, instance, truth_cost: float) -> dict:
    return {
        "experiment": task["experiment"],
        "topology": task["topology"],
        "width": task["width"],
        "height": task["height"],
        "density": task["density"],
        "actual_density": instance.density,
        "seed": task["seed"],
        "diagonal": int(task["diagonal"]),
        "start": instance.start,
        "goal": instance.goal,
        "n_nodes": instance.graph.n,
        "n_edges": sum(len(a) for a in instance.graph.adj),
        "truth_cost": truth_cost,
    }


def _result_row(base: dict, key: str, result: SearchResult) -> dict:
    row = dict(base)
    row.update(result.to_row())
    row["algorithm_key"] = key
    if not result.found:
        row["cost_gap"] = 0.0 if base["truth_cost"] == inf else inf
    elif base["truth_cost"] == 0:
        row["cost_gap"] = 0.0
    else:
        row["cost_gap"] = abs(result.cost - base["truth_cost"]) / base["truth_cost"]
    return row


def _validate(base: dict, key: str, result: SearchResult) -> None:
    truth = base["truth_cost"]
    if truth == inf:
        if result.found:
            raise AssertionError(f"{key}: found a path although the instance is disconnected")
    else:
        if not result.found:
            raise AssertionError(f"{key}: failed to find a path with cost {truth}")
        if abs(result.cost - truth) > 1e-8 * max(1.0, truth):
            raise AssertionError(f"{key}: cost {result.cost} != truth {truth}")


def run_single_task(task: dict) -> list[dict]:
    spec = MapSpec(
        topology=task["topology"],
        width=task["width"],
        height=task["height"],
        density=task["density"],
        seed=task["seed"],
        diagonal=task["diagonal"],
        random_endpoints=task["topology"] != "maze",
    )
    instance = generate_map(spec)
    truth_cost, _ = dijkstra_ground_truth(
        instance.graph, instance.start, instance.goal, instance.blocked
    )
    base = _base_row(task, instance, truth_cost)
    rows: list[dict] = []
    for key in task["algorithms"]:
        guo = GUO(instance.graph, instance.blocked)
        result = run_algorithm(
            key,
            instance.graph,
            guo,
            instance.start,
            instance.goal,
            measure_memory=task.get("measure_memory", False),
            trace=task.get("trace", False),
            trace_stride=task.get("trace_stride", 1),
        )
        _validate(base, key, result)
        rows.append(_result_row(base, key, result))
    return rows


def _pick_queries(instance, count: int, seed: int) -> list[tuple[int, int]]:
    """Pick distinct, connected start/goal pairs from the actual free cells."""
    rng = random.Random(seed)
    free = [v for v in range(instance.graph.n) if v not in instance.blocked]
    queries: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    attempts = 0
    while len(queries) < count and attempts < count * 200:
        attempts += 1
        a, b = rng.sample(free, 2)
        if (a, b) in seen:
            continue
        truth, _ = dijkstra_ground_truth(instance.graph, a, b, instance.blocked)
        if truth < inf:
            seen.add((a, b))
            queries.append((a, b))
    if len(queries) < count:
        raise RuntimeError(f"could only build {len(queries)} connected queries")
    return queries


def run_multi_task(task: dict) -> list[dict]:
    spec = MapSpec(
        topology=task["topology"],
        width=task["width"],
        height=task["height"],
        density=task["density"],
        seed=task["seed"],
        diagonal=task["diagonal"],
        random_endpoints=task["topology"] != "maze",
    )
    instance = generate_map(spec)
    queries = _pick_queries(instance, task["n_queries"], task["query_seed"] + task["seed"])
    rows: list[dict] = []

    for mode in ("cold", "warm"):
        for key in task["algorithms"]:
            shared = GUO(instance.graph, instance.blocked) if mode == "warm" else None
            cumulative = 0
            for qi, (start, goal) in enumerate(queries):
                truth_cost, _ = dijkstra_ground_truth(
                    instance.graph, start, goal, instance.blocked
                )
                guo = shared if shared is not None else GUO(instance.graph, instance.blocked)
                result = run_algorithm(
                    key,
                    instance.graph,
                    guo,
                    start,
                    goal,
                    measure_memory=False,
                )
                cumulative += result.explorations
                base = _base_row(task, instance, truth_cost)
                base["start"] = start
                base["goal"] = goal
                base["memory_mode"] = mode
                base["query_index"] = qi
                base["cumulative_explorations"] = cumulative
                known_free, known_blocked = guo.known_counts()
                base["known_free"] = known_free
                base["known_blocked"] = known_blocked
                _validate(base, key, result)
                rows.append(_result_row(base, key, result))
    return rows


def run_task(task: dict) -> list[dict]:
    if task.get("n_queries"):
        return run_multi_task(task)
    return run_single_task(task)
