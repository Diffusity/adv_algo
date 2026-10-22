# Repair the shortest-path tree incrementally

A full reverse-Dijkstra rebuild after every blocked discovery dominates MXA*'s
runtime. Obstacles are only inserted, so distances to the goal can only
increase. We invalidate the stored shortest-path-tree subtree that used the new
obstacle, seed a heap from valid boundary edges, and repair only the affected
subtree. Invalidating the whole subtree first is essential: repairing
neighbours in place can let two affected vertices in a cycle support each
other's finite distances after their only connection to the goal is removed.

**Consequences**: the worst case is still a full-graph repair, but benchmark
subtrees are small. The oracle keeps one build and local repairs instead of
24--31 rebuilds, which is the main source of the reported 3.5--13.8x speedup.
