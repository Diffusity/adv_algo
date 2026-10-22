# MXA*-ID: Dynamic Shortest-Path Search with Unknown Obstacles

Course project for **Advanced Algorithms**, Group 6. The project compares
Dijkstra, A*, MXA*, and a proposed optimality-preserving variant, **MXA*-ID**,
on grid graphs whose obstacles are revealed lazily as the search explores.

MXA*-ID keeps MXA*'s exact dynamic heuristic but maintains it with an
incremental reverse-Dijkstra oracle, shares discovered obstacle knowledge
across repeated queries, and optionally uses obstacle risk as a secondary
tie-break. The implementation, benchmark harness, web demo, and six-page IEEE
report are all in this repository.

## Results at a glance

- **956 validated runs** over 155 tasks; every run found a path and matched an
  omniscient Dijkstra reference. Maximum relative cost gap:
  `5.0e-16` (floating-point noise).
- **Explorations vs A***: 14--51% fewer, depending on topology and size.
- **Runtime vs full-rebuild MXA***: 3.5--13.8x faster at 64x64 and 128x128.
- **Peak memory vs full-rebuild MXA***: 7.7--17% lower at 64x64 and 128x128.
- **Repeated queries**: 20--55% fewer cumulative explorations over ten queries
  when obstacle knowledge is shared.
- **Risk tie-break**: neutral on eight-connected octile grids; the report
  includes this negative result.

The large-map (256x256) comparison is against A* and Dijkstra only;
full-rebuild MXA* was omitted because its runtime exceeded the experiment
budget.

## Quick start

Requires Python 3.11+ (the reported experiments used 3.11.2).

```powershell
python -m pip install -e ".[dev]"
python -m pytest
```

Minimal API example:

```python
from mxaid.maps import MapSpec, generate_map
from mxaid.search import run_mxa_id
from mxaid.world import GUO

spec = MapSpec(topology="maze", width=31, height=31, density=0.10, seed=3)
instance = generate_map(spec)
guo = GUO(instance.graph, instance.blocked)

result = run_mxa_id(instance.graph, guo, instance.start, instance.goal)
print(result.found, result.cost, result.explorations, result.expansions)
```

## Reproducing the experiments

The archived matrix is `results/raw/full.csv`. To rerun it:

```powershell
python experiments/run_benchmarks.py --experiment all --workers 6 `
  --out results/raw/full.csv
```

On the reported hardware (AMD Ryzen 5 5500U, 6 cores/12 threads, 31.3 GB RAM)
this takes roughly five minutes with six workers. For a smaller smoke run:

```powershell
python experiments/run_benchmarks.py --experiment size --quick `
  --out results/raw/quick.csv
```

Regenerate summary CSVs, validation statistics, and LaTeX tables:

```powershell
python experiments/aggregate.py
```

Regenerate the density figure and the optional extra figures:

```powershell
python experiments/plots.py
```

Regenerate the demo trace data and the trace figure:

```powershell
python experiments/export_demo.py
```

`aggregate.py` reads `results/raw/full.csv`, so keep that filename if you want
to reproduce the report tables directly.

## Web demo

The demo replays exploration and expansion traces exported by the Python
implementation; algorithms are **not** reimplemented in JavaScript. It needs no
build step and no network access.

```powershell
python -m http.server 8765 --directory web
```

Open <http://127.0.0.1:8765/>. You can switch between random, rooms, and maze
scenarios, play/pause/step through a search, reveal the true obstacle map, and
compare final metrics. The data are in `web/demo_data.js`; regenerate them with
`python experiments/export_demo.py` after changing the algorithms or scenarios.

## Report

The IEEE conference-style manuscript is `report/main.pdf`, with sources in
`report/main.tex`. It is six pages; page 6 contains the references and the
CRediT/task-division statement.

To rebuild it:

```powershell
cd report
tectonic -X compile main.tex
```

The vendored `report/IEEEtran.cls`, `report/figures/`, and `report/tables/`
keep the build self-contained. Tectonic 0.17.0 was used to validate the layout.
Any LaTeX installation with IEEEtran can also compile it.

## Repository layout

```
src/mxaid/              Core package: graph, GUO, heaps, oracles, search, maps
experiments/            Benchmark matrix, runner, aggregation, plots, demo export
results/raw/full.csv    Archived 956-row benchmark matrix
results/summary/        Aggregated CSVs and validation.json
report/                 IEEE report source, PDF, figures, tables, class file
web/                    Static demo (HTML, CSS, JS, generated trace data)
tests/                  Unit and integration tests (19 tests)
scripts/                Development utilities
docs/                   Agent docs, ADRs, contribution record
```

## Algorithms

| Name | Heuristic | Oracle | Tie-break | Repeated-query memory |
| --- | --- | --- | --- | --- |
| Dijkstra | zero | none | node id | no |
| A* | static octile | none | deeper `h` | A*+memory is the baseline |
| MXA* | exact dynamic `h_D` | full reverse Dijkstra after every block | deeper `h` | no (single-query baseline) |
| MXA*-inc | exact dynamic `h_D` | incremental SPT repair | deeper `h` | yes (shared GUO) |
| MXA*-ID | exact dynamic `h_D` | incremental SPT repair | `(f, h_D, risk, id)` | yes (shared GUO) |

All variants share the same lazy exploration loop: a node is explored only when
selected; a blocked node is discarded; a free node is expanded; the goal is
accepted only after it is explored and found free. Unknown nodes are passable
during planning (the free-space assumption), so the dynamic heuristic remains a
lower bound.

## Evaluation protocol

Six experiment families:

| Experiment | Purpose |
| --- | --- |
| `size` | random maps at 32x32, 64x64, 128x128, density 0.2 |
| `density` | all four topologies at 64x64, densities 0.1/0.2/0.3 |
| `ablation` | A*, MXA*, MXA*-inc, MXA*-ID on random and rooms maps |
| `memory` | peak traced memory at 64x64 and 128x128 |
| `multi` | ten repeated queries on random and rooms maps |
| `large` | 256x256 random maps; A*, Dijkstra, and the incremental variants |

Maps are deterministic synthetic grids: independent random obstacles, a
randomized depth-first maze with optional loops, wall-and-door rooms, and a
city grid. Ground truth is computed by an omniscient Dijkstra run on the true
blocked set. Cold mode gives each query a fresh GUO; warm mode shares one GUO
across the session. Runtime is oracle construction plus search; peak memory is
traced around the oracle and search, excluding the graph and GUO.

## Validation

`results/summary/validation.json` records the current check:

```json
{
  "n_runs": 956,
  "n_experiments": 6,
  "max_relative_cost_gap": 5.006505797183202e-16,
  "n_found": 956,
  "n_disconnected": 0,
  "n_mismatches": 0,
  "total_explorations": 803994
}
```

Every run also passes path validity and cost checks against the true obstacle
map. The test suite (`python -m pytest`) covers the heap, map generation, the
incremental oracle, and the shared search loop.

## Limitations

- Synthetic maps only; MovingAI and real robot logs are future work.
- Pure Python, so absolute runtimes are not comparable to optimized C++.
- Static obstacles, exact sensing, no sensor noise, single agent.
- Full-rebuild MXA* is absent from the 256x256 comparison.
- Peak memory excludes the graph and GUO.

## Team

| Student | ID | Primary area |
| --- | --- | --- |
| Astha Patel | 202611065 | Conceptualization, methodology, Introduction/Related Work, coordination |
| Hirali Desai | 202611066 | Search engine, incremental oracle, tests, demo |
| Shantanu Singh Sandu | 202611044 | Benchmark harness, experiments, formal analysis, data curation |
| Jyoti Mauriya | 202611023 | Investigation, visualization, documentation, review/editing |
| Nevil Nandasana | 202512009 | Methodology, validation, data curation, literature/reference checking |
| Parth Maharaja | 202512061 | Project administration, experiment/demo integration, review/editing |

The manuscript's CRediT section is the current task-division record. See
`docs/contributions.md` for the working version and evidence trail.
