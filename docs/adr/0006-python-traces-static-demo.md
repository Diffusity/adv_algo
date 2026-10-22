# Replay Python-exported traces in a dependency-free web demo

The demo must show the actual exploration and expansion order, not a separate
JavaScript approximation. The Python runner exports compact trace frames to
`web/demo_data.js`; the browser plays those frames on a canvas. There is no
algorithm implementation in JavaScript and no build step or server-side
runtime.

**Consequences**: the demo and the report share one source of truth, and a
reviewer can compare frame counts with the Python metrics. The trade-off is a
generated data file (about 0.32 MB) that must be regenerated with
`experiments/export_demo.py` after algorithm or scenario changes.
