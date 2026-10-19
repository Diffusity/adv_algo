import random
from math import inf

from mxaid import GUO, grid_graph
from mxaid.reference import dijkstra_ground_truth
from mxaid.search import run_astar, run_dijkstra, run_mxa_full, run_mxa_id

ALGORITHMS = (run_dijkstra, run_astar, run_mxa_full, run_mxa_id)

rng = random.Random(2024)
for diagonal in (False, True):
    for case in range(120):
        width = rng.randint(3, 7)
        height = rng.randint(3, 7)
        graph = grid_graph(width, height, diagonal=diagonal)
        density = rng.uniform(0.0, 0.45)
        blocked = {v for v in range(graph.n) if rng.random() < density}
        start = rng.randrange(graph.n)
        goal = rng.randrange(graph.n)
        blocked.discard(start)
        blocked.discard(goal)
        truth, _ = dijkstra_ground_truth(graph, start, goal, blocked)
        print(
            f"case={case} diag={diagonal} {width}x{height} density={density:.3f} "
            f"blocked={len(blocked)} start={start} goal={goal} truth={truth}",
            flush=True,
        )
        for runner in ALGORITHMS:
            print("  ", runner.__name__, flush=True)
            guo = GUO(graph, blocked)
            r = runner(graph, guo, start, goal)
            print("     ->", r.found, r.cost, r.explorations, r.expansions, r.reopened, r.reinserted, flush=True)
print("done")
