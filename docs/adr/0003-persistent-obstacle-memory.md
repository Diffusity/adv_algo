# Share obstacle knowledge across repeated queries

The obstacles are static, and the GUO status array is monotone: a cell moves
from unknown to free or blocked and never back. We keep one GUO per session and
reuse it for later start--goal queries, rebuilding the goal-specific oracle on
the accumulated knowledge. This is sound because the true blocked set does not
change and the known graph remains a relaxation of it.

**Consequences**: later queries start with more known-free and known-blocked
cells. The report measures cold versus warm sessions and includes A* with the
same memory as a baseline, so the gain is attributed to memory rather than to
the dynamic heuristic alone.
