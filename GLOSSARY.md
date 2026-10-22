# MXA*-ID Domain Glossary

This context is a dynamic shortest-path search in a grid world whose obstacles
are discovered lazily. The vocabulary below is used by the code, experiments,
report, and demo.

## Search model

**GUO (graph with unknown obstacles)**:
A graph in which the agent knows the topology and edge weights but not which
vertices are blocked; a vertex's true status is revealed only when it is
explored.
_Avoid_: unknown graph, hidden graph

**Free-space assumption**:
The planning convention that an unrevealed vertex is treated as passable, so a
plan can be optimistic until exploration proves otherwise.
_Avoid_: optimistic grid, unknown-is-free

**Exploration**:
A call that reveals the true status of one vertex, whether free or blocked.
Explorations are the primary cost metric because each one represents sensing or
a database lookup.
_Avoid_: query (reserve "query" for a full start-to-goal search)

**Expansion**:
The processing of a vertex that has been revealed free, generating its
passable neighbours. An expansion is a subset of an exploration.
_Avoid_: visit, pop

**Known graph**:
The graph containing only the obstacles revealed so far; it is a relaxation of
the true graph because unrevealed blocked vertices are still passable.
_Avoid_: current graph, partial graph

**Truth / ground truth**:
The optimal path cost computed by an omniscient Dijkstra run on the true
blocked set. Every reported path is checked against it.
_Avoid_: reference cost, oracle cost (the oracle is a different object)

**Cold query**:
A query run with a fresh GUO, so it starts with no obstacle knowledge from
earlier queries in the session.
_Avoid_: fresh query

**Warm query**:
A later query in a repeated-query session that reuses one shared, accumulated
GUO.
_Avoid_: cached query

## Algorithms and oracles

**MXA***:
The published dynamic-heuristic search that recomputes the exact
distance-to-goal table with a full reverse Dijkstra after each blocked
discovery and uses recheck/reinsert in the high-level loop.
_Avoid_: dynamic A*, D* Lite (different algorithms)

**MXA*-ID**:
The proposed variant: MXA*'s lazy dynamic-heuristic loop with an incremental
oracle, persistent obstacle memory, and an optional risk tie-break. It preserves
optimal path cost.
_Avoid_: proposed A*, improved MXA*

**MXA*-inc**:
An ablation variant with the incremental oracle and the standard deeper-`h`
tie-break, used to isolate the oracle from the risk rule.
_Avoid_: incremental MXA*

**Full oracle**:
An oracle that rebuilds the entire distance-to-goal table from scratch after
each blocked discovery.
_Avoid_: rebuild oracle

**Incremental oracle**:
An oracle that invalidates the shortest-path-tree subtree affected by a newly
blocked vertex and repairs only that subtree from valid boundary distances.
_Avoid_: dynamic Dijkstra, lazy oracle

**Affected subtree**:
The set of vertices whose stored shortest path to the goal uses the newly
blocked vertex. Their distances are invalidated before repair.
_Avoid_: dirty set, broken region

**Boundary edge**:
An edge from an affected vertex to an unaffected, non-blocked vertex that still
has a finite distance; it is a candidate entry point for repaired paths.
_Avoid_: exit edge, repair edge

**Recheck / reinsert**:
The MXA* loop step that compares a popped vertex's stored key with its current
`f` value and reinserts it if the heuristic increased after a discovery.
_Avoid_: refresh, requeue

**Reopening**:
Allowing a closed vertex to be expanded again when a cheaper `g`-value is
found. It is required for optimality in the shared loop.
_Avoid_: re-expansion, revisit

**Risk tie-break**:
A secondary ordering that prefers a stored path with fewer unknown
intermediate vertices when `f` and the dynamic heuristic are equal. It is
optional and does not affect admissibility.
_Avoid_: risk heuristic (it is not a heuristic estimate of cost)

**Cost gap**:
The relative difference between a returned path cost and the true optimum. In
this project it is used for validation, not as a suboptimality budget.
_Avoid_: error, delta

## Benchmark

**Task**:
One map, one density, one seed, and one algorithm set; a task may contain
several algorithm runs.
_Avoid_: case, instance

**Run**:
One algorithm on one task, or one query within a multi-query session. The
archived matrix has 956 runs.
_Avoid_: trial, sample

**Random**:
Independent blocked vertices at a target density.
_Avoid_: scatter, noise map

**Maze**:
A randomized depth-first maze; the density parameter opens extra walls to
create loops.
_Avoid_: labyrinth

**Rooms**:
A wall-and-door grid with four rooms per side plus random clutter.
_Avoid_: office map

**City**:
Solid building blocks on a street grid; density is the building probability.
_Avoid_: urban map

**Trace frame**:
A compact snapshot of explored/blocked/expanded vertices and the open list,
exported by Python for the web demo. The demo replays frames; it does not run
the algorithms.
_Avoid_: animation step, keyframe
