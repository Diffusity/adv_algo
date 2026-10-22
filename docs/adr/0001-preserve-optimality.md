# Preserve optimality rather than accept a cost gap

The assignment allows a suboptimal modification if the path-cost gap is
reported. We considered trading a bounded gap for fewer explorations, but chose
an optimality-preserving design so that every path can be checked against the
omniscient Dijkstra reference and the comparison isolates the heuristic and
oracle. Any future bounded-suboptimal variant must report its measured gap
explicitly and must not be presented as MXA*-ID.

**Consequences**: no weight inflation or suboptimality budget is used; the
manuscript states the maximum observed gap (5.0e-16, floating-point noise) and
does not claim a speed/quality trade-off.
