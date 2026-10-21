"""Export compact trace playback data for the static demo.

The demo is deliberately dependency-free: it reads ``web/demo_data.js`` and
plays back the exact exploration and expansion order produced by the Python
implementation.  No algorithm is reimplemented in JavaScript.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.runner import run_algorithm
from mxaid.maps import MapSpec, generate_map
from mxaid.reference import dijkstra_ground_truth
from mxaid.world import GUO

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
FIG = ROOT / "report" / "figures"
WEB.mkdir(exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

SCENARIOS = [
    {
        "id": "random32",
        "title": "Random obstacles",
        "subtitle": "32x32, 20% blocked, seed 7",
        "topology": "random",
        "size": 32,
        "density": 0.20,
        "seed": 7,
    },
    {
        "id": "rooms32",
        "title": "Rooms",
        "subtitle": "32x32, 20% clutter, seed 5",
        "topology": "rooms",
        "size": 32,
        "density": 0.20,
        "seed": 5,
    },
    {
        "id": "maze31",
        "title": "Maze",
        "subtitle": "31x31, 10% loops, seed 3",
        "topology": "maze",
        "size": 32,
        "density": 0.10,
        "seed": 3,
    },
]

ALGORITHMS = ["dijkstra", "astar", "mxa_full", "mxa_id"]
DISPLAY = {
    "dijkstra": "Dijkstra",
    "astar": "A*",
    "mxa_full": "MXA*",
    "mxa_id": "MXA*-ID",
}


def build_scenario(spec: dict) -> dict:
    map_spec = MapSpec(
        topology=spec["topology"],
        width=spec["size"],
        height=spec["size"],
        density=spec["density"],
        seed=spec["seed"],
        diagonal=True,
        random_endpoints=spec["topology"] != "maze",
    )
    instance = generate_map(map_spec)
    graph = instance.graph
    width = graph.width or spec["size"]
    height = graph.height or spec["size"]
    truth, _ = dijkstra_ground_truth(graph, instance.start, instance.goal, instance.blocked)
    if not np.isfinite(truth):
        raise RuntimeError(f"{spec['id']}: generated instance is disconnected")

    algorithms = []
    for key in ALGORITHMS:
        guo = GUO(graph, instance.blocked)
        result = run_algorithm(key, graph, guo, instance.start, instance.goal, trace=True)
        if not result.found or abs(result.cost - truth) > 1e-8 * max(1.0, truth):
            raise RuntimeError(f"{spec['id']}/{key}: non-optimal result")
        trace = result.trace or {}
        frames = trace.get("frames", [])
        # Keep every second frame (plus the final one) to keep the JS payload
        # small while preserving smooth playback at 32x32.
        sampled = frames[::2]
        if frames and frames[-1] is not sampled[-1]:
            sampled.append(frames[-1])
        compact = [
            {
                "e": int(f["explored"]),
                "b": int(f["blocked"]),
                "x": int(f["expanded"]),
                "o": [int(v) for v in f["open"]],
            }
            for f in sampled
        ]
        algorithms.append(
            {
                "key": key,
                "name": DISPLAY[key],
                "metrics": {
                    "explorations": result.explorations,
                    "expansions": result.expansions,
                    "generated": result.generated,
                    "max_open": result.max_open,
                    "reopened": result.reopened,
                    "reinserted": result.reinserted,
                    "cost": result.cost,
                    "path_len": len(result.path),
                    "runtime_ms": (result.runtime_s + result.setup_s) * 1000.0,
                    "setup_ms": result.setup_s * 1000.0,
                    "oracle_builds": result.oracle_builds,
                },
                "frames": compact,
                "explored": [int(v) for v in trace.get("explored", [])],
                "blocked": [int(v) for v in trace.get("blocked", [])],
                "path": [int(v) for v in result.path],
            }
        )

    return {
        "id": spec["id"],
        "title": spec["title"],
        "subtitle": spec["subtitle"],
        "grid": {
            "width": width,
            "height": height,
            "start": instance.start,
            "goal": instance.goal,
            "actual_blocked": sorted(int(v) for v in instance.blocked),
        },
        "algorithms": algorithms,
    }


def draw_trace_figure(scenario: dict, path: Path) -> None:
    """Four-panel qualitative figure: final explored region and path."""
    algs = scenario["algorithms"]
    w = scenario["grid"]["width"]
    h = scenario["grid"]["height"]
    fig, axes = plt.subplots(1, 4, figsize=(7.1, 1.85))
    for ax, a in zip(axes, algs):
        img = np.ones((h, w, 3), dtype=float)
        img[:, :] = (0.92, 0.93, 0.94)
        explored = set(a["explored"])
        blocked = set(a["blocked"])
        for v in explored:
            x, y = v % w, v // w
            if v in blocked:
                img[y, x] = (0.10, 0.10, 0.12)
            else:
                img[y, x] = (0.45, 0.75, 0.95)
        ax.imshow(img, interpolation="nearest", origin="upper")
        if a["path"]:
            xs = [v % w + 0.5 for v in a["path"]]
            ys = [v // w + 0.5 for v in a["path"]]
            ax.plot(xs, ys, color="#2b8a3e", lw=1.3, solid_capstyle="round")
        sx, sy = scenario["grid"]["start"] % w, scenario["grid"]["start"] // w
        gx, gy = scenario["grid"]["goal"] % w, scenario["grid"]["goal"] // w
        ax.plot(sx + 0.5, sy + 0.5, marker="o", ms=4.0, color="#2f9e44", mec="white", mew=0.5)
        ax.plot(gx + 0.5, gy + 0.5, marker="*", ms=5.5, color="#f08c00", mec="white", mew=0.5)
        ax.set_title(f"{a['name']}\n{a['metrics']['explorations']} explorations", fontsize=7)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
    fig.tight_layout(pad=0.4)
    fig.savefig(path)
    fig.savefig(path.with_suffix(".png"))
    plt.close(fig)


def main() -> None:
    scenarios = [build_scenario(s) for s in SCENARIOS]
    payload = {"scenarios": scenarios}
    js = "window.DEMO_DATA = " + json.dumps(payload, separators=(",", ":"), ensure_ascii=False) + ";\n"
    (WEB / "demo_data.js").write_text(js, encoding="utf-8")
    # A JSON copy is useful for inspection and for non-JS tooling.
    (WEB / "demo_data.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"wrote {WEB / 'demo_data.js'} ({len(js) / 1e6:.2f} MB)")
    draw_trace_figure(scenarios[2], FIG / "traces.pdf")
    print(f"wrote {FIG / 'traces.pdf'}")


if __name__ == "__main__":
    main()
