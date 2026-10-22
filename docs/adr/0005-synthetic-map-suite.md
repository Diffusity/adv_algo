# Use a controlled synthetic map suite, not MovingAI, for the main study

The main study needs independent control of size, obstacle density, and
topology, plus reproducible connectivity and ground truth. We therefore use
four deterministic synthetic generators: random obstacles, a randomized
depth-first maze with optional loops, wall-and-door rooms, and a city grid.
MovingAI maps are downloaded but not integrated into the reported results.

**Consequences**: the scaling trends are clean and reproducible, but external
validity against standard benchmarks is untested. The manuscript lists
MovingAI evaluation as future work and does not claim standard-benchmark
coverage.
