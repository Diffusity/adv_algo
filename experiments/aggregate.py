"""Aggregate raw benchmark rows into CSVs, LaTeX tables, and validation stats."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results" / "raw" / "full.csv"
OUT = ROOT / "results" / "summary"
TABLES = ROOT / "results" / "tables"
OUT.mkdir(parents=True, exist_ok=True)
TABLES.mkdir(parents=True, exist_ok=True)

ALG_ORDER = ["Dijkstra", "A*", "MXA*", "MXA*-ID", "MXA*-inc"]
COLORS = {
    "Dijkstra": "#6c757d",
    "A*": "#0072B2",
    "MXA*": "#D55E00",
    "MXA*-ID": "#009E73",
    "MXA*-inc": "#CC79A7",
}


def mean_std(df: pd.DataFrame, col: str) -> pd.DataFrame:
    g = df.groupby(["topology", "algorithm"])[col].agg(["mean", "std"]).reset_index()
    return g


def fmt_ms(seconds: float) -> str:
    return f"{seconds * 1000.0:.1f}"


def fmt_pct(x: float) -> str:
    return f"{100.0 * x:.1f}"


def load() -> pd.DataFrame:
    if not RAW.exists():
        raise SystemExit(f"missing {RAW}; run experiments/run_benchmarks.py --experiment all")
    df = pd.read_csv(RAW)
    # Normalise booleans read as ints and keep the display order.
    df["found"] = df["found"].astype(int)
    df["memory_mode"] = df.get("memory_mode", pd.Series(index=df.index, dtype=object)).fillna("")
    df["query_index"] = df.get("query_index", pd.Series(index=df.index, dtype=float)).fillna(-1).astype(int)
    df["algorithm"] = pd.Categorical(df["algorithm"], categories=ALG_ORDER, ordered=True)
    return df


def validate(df: pd.DataFrame) -> dict:
    finite_truth = np.isfinite(df["truth_cost"])
    mismatches = 0
    for _, row in df.iterrows():
        if row["found"]:
            if not bool(finite_truth.loc[row.name]):
                mismatches += 1
            elif abs(row["cost"] - row["truth_cost"]) > 1e-8 * max(1.0, row["truth_cost"]):
                mismatches += 1
        else:
            if bool(finite_truth.loc[row.name]):
                mismatches += 1
    result = {
        "n_runs": int(len(df)),
        "n_experiments": int(df["experiment"].nunique()),
        "max_relative_cost_gap": float(df["cost_gap"].replace([np.inf, -np.inf], np.nan).max()),
        "n_found": int(df["found"].sum()),
        "n_disconnected": int((~finite_truth).sum()),
        "n_mismatches": int(mismatches),
        "total_explorations": int(df["explorations"].sum()),
        "experiments": sorted(df["experiment"].unique().tolist()),
    }
    (OUT / "validation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def table_scaling(df: pd.DataFrame) -> pd.DataFrame:
    sub = df[(df["experiment"] == "size") & (df["topology"] == "random")]
    g = (
        sub.groupby(["algorithm", "width"], observed=False)
        .agg(expl=("explorations", "mean"), expl_std=("explorations", "std"), runtime=("total_runtime_s", "mean"))
        .reset_index()
    )
    # Memory from the dedicated 64/128 memory experiment.
    mem = (
        df[df["experiment"] == "memory"]
        .groupby(["algorithm", "width"], observed=False)["peak_memory_kb"]
        .mean()
        .reset_index()
    )
    rows = []
    for alg in ["Dijkstra", "A*", "MXA*", "MXA*-ID"]:
        row = {"algorithm": alg}
        for width in (32, 64, 128):
            e = g[(g.algorithm == alg) & (g.width == width)]
            if not e.empty:
                row[f"expl_{width}"] = float(e.expl.iloc[0])
                row[f"expl_std_{width}"] = float(e.expl_std.iloc[0])
                row[f"rt_{width}"] = float(e.runtime.iloc[0])
        for width in (64, 128):
            m = mem[(mem.algorithm == alg) & (mem.width == width)]
            row[f"mem_{width}"] = float(m.peak_memory_kb.iloc[0]) if not m.empty else float("nan")
        rows.append(row)
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "table_scaling.csv", index=False)
    return out


def table_ablation(df: pd.DataFrame) -> pd.DataFrame:
    sub = df[(df["experiment"] == "ablation") & (df["topology"] == "random")]
    g = (
        sub.groupby(["algorithm", "density"], observed=False)
        .agg(
            expl=("explorations", "mean"),
            expl_std=("explorations", "std"),
            runtime=("total_runtime_s", "mean"),
            builds=("oracle_builds", "mean"),
            work=("oracle_work", "mean"),
        )
        .reset_index()
    )
    mem = (
        df[(df["experiment"] == "memory") & (df["width"] == 64)]
        .groupby("algorithm", observed=False)["peak_memory_kb"]
        .mean()
        .reset_index()
    )
    rows = []
    for alg in ["A*", "MXA*", "MXA*-inc", "MXA*-ID"]:
        row = {"algorithm": alg}
        for d in (0.2, 0.3):
            e = g[(g.algorithm == alg) & (np.isclose(g.density, d))]
            if not e.empty:
                row[f"expl_{d}"] = float(e.expl.iloc[0])
                row[f"expl_std_{d}"] = float(e.expl_std.iloc[0])
                row[f"rt_{d}"] = float(e.runtime.iloc[0])
                row[f"builds_{d}"] = float(e.builds.iloc[0])
                row[f"work_{d}"] = float(e.work.iloc[0])
        m = mem[mem.algorithm == alg]
        row["mem_64"] = float(m.peak_memory_kb.iloc[0]) if not m.empty else float("nan")
        rows.append(row)
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "table_ablation.csv", index=False)
    return out


def table_multi(df: pd.DataFrame) -> pd.DataFrame:
    sub = df[df["experiment"] == "multi"].copy()
    last = sub[
        sub["query_index"]
        == sub.groupby(["topology", "seed", "algorithm", "memory_mode"], observed=False).query_index.transform("max")
    ]
    g = (
        last.groupby(["topology", "algorithm", "memory_mode"], observed=False)
        .agg(cum=("cumulative_explorations", "mean"), cum_std=("cumulative_explorations", "std"))
        .reset_index()
    )
    rows = []
    for topo in ("random", "rooms"):
        for alg in ("A*", "MXA*-ID"):
            cold = g[(g.topology == topo) & (g.algorithm == alg) & (g.memory_mode == "cold")]
            warm = g[(g.topology == topo) & (g.algorithm == alg) & (g.memory_mode == "warm")]
            c = float(cold.cum.iloc[0])
            w = float(warm.cum.iloc[0])
            rows.append(
                {
                    "topology": topo,
                    "algorithm": alg,
                    "cold": c,
                    "cold_std": float(cold.cum_std.iloc[0]),
                    "warm": w,
                    "warm_std": float(warm.cum_std.iloc[0]),
                    "reduction": (c - w) / c,
                }
            )
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "table_multi.csv", index=False)
    return out


def table_density(df: pd.DataFrame) -> pd.DataFrame:
    sub = df[df["experiment"] == "density"]
    g = (
        sub.groupby(["topology", "density", "algorithm"], observed=False)
        .agg(expl=("explorations", "mean"), expl_std=("explorations", "std"), runtime=("total_runtime_s", "mean"))
        .reset_index()
    )
    g.to_csv(OUT / "table_density.csv", index=False)
    return g


def table_large(df: pd.DataFrame) -> pd.DataFrame:
    sub = df[df["experiment"] == "large"]
    g = (
        sub.groupby(["algorithm"], observed=False)
        .agg(
            expl=("explorations", "mean"),
            expl_std=("explorations", "std"),
            expansions=("expansions", "mean"),
            runtime=("total_runtime_s", "mean"),
            setup=("setup_s", "mean"),
            max_open=("max_open", "mean"),
        )
        .reset_index()
    )
    g.to_csv(OUT / "table_large.csv", index=False)
    return g


def write_latex(scaling: pd.DataFrame, ablation: pd.DataFrame, multi: pd.DataFrame) -> None:
    # Table I: scaling
    lines = [
        r"\begin{table*}[t]",
        r"\centering",
        r"\caption{Scaling on random octile grids at density 0.2 (mean of 5 seeds; runtime in ms, peak memory in KB).}",
        r"\label{tab:scaling}",
        r"\small",
        r"\begin{tabular}{lrrrrrrrr}",
        r"\toprule",
        r"& \multicolumn{3}{c}{Explorations} & \multicolumn{3}{c}{Runtime (ms)} & \multicolumn{2}{c}{Peak memory (KB)} \\",
        r"\cmidrule(lr){2-4}\cmidrule(lr){5-7}\cmidrule(lr){8-9}",
        r"Algorithm & $32^2$ & $64^2$ & $128^2$ & $32^2$ & $64^2$ & $128^2$ & $64^2$ & $128^2$ \\",
        r"\midrule",
    ]
    for _, row in scaling.iterrows():
        def cell(key: str) -> str:
            v = row.get(key, np.nan)
            if isinstance(v, float) and np.isnan(v):
                return "--"
            if key.startswith("rt_"):
                v *= 1000.0
            return f"{v:.1f}"
        lines.append(
            f"{row['algorithm']} & "
            f"{cell('expl_32')} & {cell('expl_64')} & {cell('expl_128')} & "
            f"{cell('rt_32')} & {cell('rt_64')} & {cell('rt_128')} & "
            f"{cell('mem_64')} & {cell('mem_128')} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table*}", ""]
    (TABLES / "scaling.tex").write_text("\n".join(lines), encoding="utf-8")

    # Table II: ablation
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Ablation on $64\times64$ random grids (mean of 5 seeds; runtime in ms).}",
        r"\label{tab:ablation}",
        r"\small",
        r"\begin{tabular}{lrrrrrr}",
        r"\toprule",
        r"& \multicolumn{2}{c}{$d=0.2$} & \multicolumn{2}{c}{$d=0.3$} & Builds & Mem. \\",
        r"\cmidrule(lr){2-3}\cmidrule(lr){4-5}",
        r"Algorithm & Expl. & ms & Expl. & ms & $d=0.2$ & KB \\",
        r"\midrule",
    ]
    for _, row in ablation.iterrows():
        def cell(key: str, fmt: str = ".1f") -> str:
            v = row.get(key, np.nan)
            if isinstance(v, float) and np.isnan(v):
                return "--"
            if key.startswith("rt_"):
                v *= 1000.0
            return format(v, fmt)
        lines.append(
            f"{row['algorithm']} & {cell('expl_0.2')} & {cell('rt_0.2')} & "
            f"{cell('expl_0.3')} & {cell('rt_0.3')} & {cell('builds_0.2')} & {cell('mem_64')} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    (TABLES / "ablation.tex").write_text("\n".join(lines), encoding="utf-8")

    # Table III: multi-query
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Cumulative explorations after 10 repeated queries (mean of 3 seeds).}",
        r"\label{tab:multi}",
        r"\small",
        r"\begin{tabular}{llrrr}",
        r"\toprule",
        r"Topology & Algorithm & Cold & Warm & Reduction \\",
        r"\midrule",
    ]
    for _, row in multi.iterrows():
        lines.append(
            f"{row['topology'].capitalize()} & {row['algorithm']} & {row['cold']:.1f} & "
            f"{row['warm']:.1f} & {fmt_pct(row['reduction'])}\\% \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    (TABLES / "multi.tex").write_text("\n".join(lines), encoding="utf-8")


def write_data_structures_table() -> None:
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Data structures used by MXA*-ID and why.}",
        r"\label{tab:structures}",
        r"\footnotesize",
        r"\begin{tabular}{p{1.45cm}p{1.6cm}p{3.4cm}}",
        r"\toprule",
        r"Component & Structure & Role and complexity \\",
        r"\midrule",
        r"Graph & adjacency list & $O(1)$ neighbour iteration; $O(V+E)$ memory. \\",
        r"OPEN & indexed binary heap & one entry/node; $O(\log V)$ push, update-key, pop; deterministic keys. \\",
        r"Search state & dense arrays & $O(1)$ $g$, parent, closed and status lookups; cache-friendly. \\",
        r"$h_D$ oracle & distance + successor arrays & $O(1)$ heuristic query; successor tree enables subtree repair. \\",
        r"Obstacle memory & byte array + set & $O(1)$ status; grows monotonically across queries. \\",
        r"Repair frontier & set + binary heap & $O((|A|+E_A)\log|A|)$ per discovered obstacle. \\",
        r"Risk cache & hash map, versioned & avoids repeated path walks; invalidated on distance changes. \\",
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
        "",
    ]
    (TABLES / "structures.tex").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    df = load()
    stats = validate(df)
    print(json.dumps(stats, indent=2))
    scaling = table_scaling(df)
    ablation = table_ablation(df)
    multi = table_multi(df)
    table_density(df)
    table_large(df)
    write_latex(scaling, ablation, multi)
    write_data_structures_table()
    print("wrote summaries to", OUT)
    print("wrote tables to", TABLES)


if __name__ == "__main__":
    main()
