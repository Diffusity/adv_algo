"""Experiment matrix definitions."""

from __future__ import annotations

MAIN_ALGORITHMS = ["dijkstra", "astar", "mxa_full", "mxa_id"]
ABLATION_ALGORITHMS = ["astar", "mxa_full", "mxa_inc", "mxa_id"]
MULTI_ALGORITHMS = ["astar", "mxa_inc", "mxa_id"]

TOPOLOGIES = ["random", "maze", "rooms", "city"]


def _task(
    experiment: str,
    topology: str,
    width: int,
    height: int,
    density: float,
    seed: int,
    algorithms: list[str],
    *,
    measure_memory: bool = False,
    n_queries: int = 0,
    query_seed: int = 999,
) -> dict:
    return {
        "experiment": experiment,
        "topology": topology,
        "width": width,
        "height": height,
        "density": density,
        "seed": seed,
        "diagonal": True,
        "algorithms": algorithms,
        "measure_memory": measure_memory,
        "n_queries": n_queries,
        "query_seed": query_seed,
    }


def build_tasks(experiment: str, *, quick: bool = False) -> list[dict]:
    if experiment == "size":
        sizes = [32, 64] if quick else [32, 64, 128]
        seeds = range(2) if quick else range(5)
        return [
            _task("size", topo, size, size, 0.2, seed, MAIN_ALGORITHMS)
            for topo in TOPOLOGIES
            for size in sizes
            for seed in seeds
        ]

    if experiment == "density":
        densities = [0.1, 0.2] if quick else [0.1, 0.2, 0.3]
        seeds = range(2) if quick else range(5)
        return [
            _task("density", topo, 64, 64, density, seed, MAIN_ALGORITHMS)
            for topo in TOPOLOGIES
            for density in densities
            for seed in seeds
        ]

    if experiment == "ablation":
        seeds = range(2) if quick else range(5)
        return [
            _task("ablation", topo, 64, 64, density, seed, ABLATION_ALGORITHMS)
            for topo in ("random", "rooms")
            for density in (0.2, 0.3)
            for seed in seeds
        ]

    if experiment == "memory":
        sizes = [64] if quick else [64, 128]
        seeds = range(2) if quick else range(3)
        return [
            _task(
                "memory",
                "random",
                size,
                size,
                0.2,
                seed,
                MAIN_ALGORITHMS,
                measure_memory=True,
            )
            for size in sizes
            for seed in seeds
        ]

    if experiment == "multi":
        seeds = range(2) if quick else range(3)
        queries = 5 if quick else 10
        return [
            _task(
                "multi",
                topo,
                64,
                64,
                0.2,
                seed,
                MULTI_ALGORITHMS,
                n_queries=queries,
                query_seed=4242,
            )
            for topo in ("random", "rooms")
            for seed in seeds
        ]

    if experiment == "large":
        return [
            _task("large", "random", 256, 256, 0.2, seed, ["dijkstra", "astar", "mxa_inc", "mxa_id"])
            for seed in (range(1) if quick else range(3))
        ]

    raise ValueError(f"unknown experiment: {experiment}")


EXPERIMENTS = ["size", "density", "ablation", "memory", "multi", "large"]
