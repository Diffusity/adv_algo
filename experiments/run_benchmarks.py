"""Run a benchmark experiment in parallel and write a raw CSV."""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from tqdm import tqdm

# Allow both ``python experiments/run_benchmarks.py`` and
# ``python -m experiments.run_benchmarks`` from the repo root.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from experiments.configs import EXPERIMENTS, build_tasks  # noqa: E402
from experiments.runner import run_task  # noqa: E402


def _flatten(rows: list[dict]) -> list[dict]:
    out = []
    for row in rows:
        out.append({k: v for k, v in row.items() if k != "trace"})
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", choices=EXPERIMENTS + ["all"], required=True)
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--quick", action="store_true", help="small matrix for smoke tests")
    parser.add_argument("--limit", type=int, default=None, help="run only the first N tasks")
    args = parser.parse_args()

    experiments = EXPERIMENTS if args.experiment == "all" else [args.experiment]
    tasks = []
    for experiment in experiments:
        tasks.extend(build_tasks(experiment, quick=args.quick))
    if args.limit:
        tasks = tasks[: args.limit]
    if not tasks:
        raise SystemExit("no tasks")

    out = args.out
    if out is None:
        out = Path("results/raw") / f"{args.experiment}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)

    print(f"running {len(tasks)} tasks with {args.workers} workers -> {out}", flush=True)
    started = time.perf_counter()
    all_rows: list[dict] = []
    fieldnames: list[str] | None = None

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_task, task) for task in tasks]
        with tqdm(total=len(futures), unit="task") as bar:
            for future in as_completed(futures):
                rows = future.result()
                for row in _flatten(rows):
                    if fieldnames is None:
                        fieldnames = list(row.keys())
                    else:
                        for key in row:
                            if key not in fieldnames:
                                fieldnames.append(key)
                    all_rows.append(row)
                bar.update(1)

    if not all_rows:
        raise SystemExit("no rows produced")
    assert fieldnames is not None
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})
    elapsed = time.perf_counter() - started
    print(f"wrote {len(all_rows)} rows in {elapsed:.1f}s", flush=True)


if __name__ == "__main__":
    main()
