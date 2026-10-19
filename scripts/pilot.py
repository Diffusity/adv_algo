"""Quick pilot: compare tie-break variants before fixing the experiment matrix."""

import statistics
import time

from mxaid import GUO
from mxaid.heuristics import StaticHeuristic
from mxaid.maps import MapSpec, generate_map
from mxaid.oracles import FullOracle, IncrementalOracle
from mxaid.reference import dijkstra_ground_truth
from mxaid.search import Searcher


def run(graph, guo, start, goal, heuristic, tie, name):
    return Searcher(
        graph,
        guo,
        start,
        goal,
        heuristic,
        name=name,
        tie_break=tie,
        recheck_h=name != "A*",
    ).run()


configs = [
    ("A*", "h"),
    ("MXA*", "h"),
    ("ID-risk", "risk"),
    ("ID-h-risk", "h_risk"),
]

for size, density, diagonal in ((64, 0.2, True), (64, 0.35, True), (128, 0.2, True), (128, 0.35, True), (64, 0.2, False), (64, 0.35, False), (128, 0.2, False)):
    rows = {c[0]: [] for c in configs}
    times = {c[0]: [] for c in configs}
    for seed in range(3):
        spec = MapSpec("random", size, size, density=density, seed=100 + seed, diagonal=diagonal)
        m = generate_map(spec)
        truth, _ = dijkstra_ground_truth(m.graph, m.start, m.goal, m.blocked)
        for name, tie in configs:
            guo = GUO(m.graph, m.blocked)
            if name == "A*":
                h = StaticHeuristic(m.graph, m.goal)
            elif name == "MXA*":
                h = FullOracle(m.graph, m.goal, guo)
            else:
                h = IncrementalOracle(m.graph, m.goal, guo)
            t = time.perf_counter()
            r = run(m.graph, guo, m.start, m.goal, h, tie, name)
            times[name].append(time.perf_counter() - t)
            assert r.found and abs(r.cost - truth) < 1e-9
            rows[name].append(r.explorations)
    print(f"{size}x{size} d={density} diag={diagonal}", flush=True)
    for name, _ in configs:
        print(
            f"  {name:10s} expl={statistics.mean(rows[name]):8.1f} "
            f"time={statistics.mean(times[name]):7.3f}s",
            flush=True,
        )
