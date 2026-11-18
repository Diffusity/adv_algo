"""Embed recorded Python search events in the offline dry run lesson."""

from __future__ import annotations

import json
import re
import sys
from math import isclose, isfinite
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.runner import build_search, run_algorithm
from mxaid import GUO, grid_graph
from mxaid.oracles import FullOracle, IncrementalOracle
from mxaid.reference import dijkstra_ground_truth, path_cost, validate_path
from mxaid.search import Searcher


def display_number(value: float) -> float | None:
    return round(value, 6) if isfinite(value) else None


def affected_cells(graph, successors, blocked: int) -> set[int]:
    affected = {blocked}
    stack = [blocked]
    while stack:
        cell = stack.pop()
        for pred, _ in graph.radj[cell]:
            if successors[pred] == cell and pred not in affected:
                stack.append(pred)
                affected.add(pred)
    return affected


class LessonSearch(Searcher):
    """Observe existing trace callbacks without changing search decisions."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.frames = []
        self.repair = None
        if isinstance(self.heuristic, IncrementalOracle):
            self.observe_repair()

    def observe_repair(self) -> None:
        oracle = self.heuristic
        notify = oracle.notify_blocked

        def record(blocked: int) -> None:
            before = oracle.dist.copy()
            affected = affected_cells(self.graph, oracle.next, blocked)
            notify(blocked)
            self.repair = {
                "affected": sorted(affected),
                "changes": [
                    [v, display_number(before[v]), display_number(oracle.dist[v])]
                    for v in sorted(affected)
                    if not isclose(before[v], oracle.dist[v], abs_tol=1e-9)
                ],
            }

        oracle.notify_blocked = record

    def _append_frame(self, trace_data, expansions, heap) -> None:
        super()._append_frame(trace_data, expansions, heap)
        oracle = self.heuristic
        frame = trace_data["frames"][-1]
        previous = self.frames[-1] if self.frames else None
        dirty = isinstance(oracle, FullOracle) and oracle._dirty
        estimates = getattr(oracle, "dist", None)
        if estimates is None:
            estimates = getattr(oracle, "values", [0] * self.graph.n)
        stats = oracle.stats()
        queue = []
        for cell in sorted(heap.items(), key=heap._keys.__getitem__):
            key = heap._keys[cell]
            stored_h = 0.0 if self.tie_break == "id" else key[1]
            g = key[0] - stored_h
            queue.append({
                "cell": cell,
                "g": display_number(g),
                "h": display_number(stored_h),
                "f": display_number(key[0]),
                "currentF": display_number(g + estimates[cell]) if not dirty else None,
                "risk": display_number(key[2]) if self.tie_break == "h_risk" else None,
            })

        kind, current = "goal", self.goal
        if previous is None:
            kind, current = "start", self.start
        elif frame["blocked"] > previous["blockedCount"]:
            kind, current = "blocked", trace_data["blocked"][-1]
        elif expansions > previous["expansions"]:
            kind, current = "expanded", trace_data["expanded"][-1]
        self.frames.append({
            "kind": kind,
            "current": current,
            "status": list(self.guo.status),
            "queue": queue,
            "h": [display_number(value) for value in estimates],
            "checks": frame["explored"],
            "expansions": expansions,
            "blockedCount": frame["blocked"],
            "builds": stats["oracle_builds"],
            "updates": stats["oracle_updates"],
            "dirty": dirty,
            "repair": self.repair,
        })
        self.repair = None


def lesson() -> dict:
    graph = grid_graph(8, 5, diagonal=True)
    start, goal = graph.node_at(1, 2), graph.node_at(6, 2)
    blocked = {graph.node_at(3, y) for y in range(1, 5)}
    truth, _ = dijkstra_ground_truth(graph, start, goal, blocked)
    runs = []
    for key in ("dijkstra", "astar", "mxa_full", "mxa_inc", "mxa_id", "warm"):
        guo = GUO(graph, blocked)
        method = "astar" if key == "warm" else key
        if key == "warm":
            run_algorithm("astar", graph, guo, goal, start)
        prior = list(guo.status)
        oracle, tie, recheck, name = build_search(method, graph, guo, goal)
        search = LessonSearch(
            graph, guo, start, goal, oracle, name=name,
            tie_break=tie, recheck_h=recheck, trace=True,
        )
        result = search.run()
        validate_path(graph, result.path, start, goal, blocked)
        if not (isclose(result.cost, truth) and isclose(path_cost(graph, result.path), truth)):
            raise ValueError(f"{key}: path cost differs from reference")
        runs.append({
            "id": key,
            "name": "A* + memory" if key == "warm" else name,
            "prior": prior,
            "frames": search.frames,
            "path": result.path,
            "cost": display_number(result.cost),
            "checks": result.explorations,
            "expansions": result.expansions,
            "builds": result.oracle_builds,
            "updates": result.oracle_updates,
            "reinserted": result.reinserted,
        })
    return {
        "width": graph.width, "height": graph.height, "start": start,
        "goal": goal, "blocked": sorted(blocked), "runs": runs,
        "optimalCost": display_number(truth),
    }


def main() -> None:
    target = ROOT / "web" / "dry-run.html"
    payload = lesson()
    source = target.read_text(encoding="utf-8")
    pattern = r'(<script id="lesson-data" type="application/json">).*?(</script>)'
    data = json.dumps(payload, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
    output, replacements = re.subn(pattern, lambda m: m[1] + "\n" + data + "\n" + m[2], source, flags=re.S)
    if replacements != 1:
        raise ValueError("Expected one embedded lesson-data block")
    target.write_text(output, encoding="utf-8")
    for run in payload["runs"]:
        print(run["name"], run["checks"], "new checks,", run["cost"], "path cost")


if __name__ == "__main__":
    main()
