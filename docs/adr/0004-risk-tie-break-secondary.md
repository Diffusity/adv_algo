# Keep the risk tie-break secondary and report the negative result

We considered ordering by obstacle risk before the dynamic heuristic, but pilot
runs were unstable: a shallow low-risk node could be preferred over a much
deeper node with a better `g`-value. The final key places risk after `f` and
`h_D`, so it only reorders exact ties and cannot affect admissibility. On
eight-connected octile grids exact ties are rare, so the rule is neutral in the
benchmark.

**Consequences**: MXA*-ID and MXA*-inc have identical exploration counts on the
reported grids; MXA*-ID carries a small runtime overhead from risk lookups. We
retain the component as optional and do not claim an exploration benefit.
