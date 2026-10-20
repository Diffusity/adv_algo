"""Generate report figures from aggregated benchmark data."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results" / "raw" / "full.csv"
FIG = ROOT / "report" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

COLORS = {
    "Dijkstra": "#6c757d",
    "A*": "#0072B2",
    "MXA*": "#D55E00",
    "MXA*-ID": "#009E73",
    "MXA*-inc": "#CC79A7",
}
MARKERS = {"Dijkstra": "o", "A*": "s", "MXA*": "^", "MXA*-ID": "D", "MXA*-inc": "v"}
LABELS = {
    "Dijkstra": "Dijkstra",
    "A*": "A*",
    "MXA*": "MXA* (full rebuild)",
    "MXA*-ID": "MXA*-ID (proposed)",
    "MXA*-inc": "MXA*-inc (no tie-break)",
}

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif", "Liberation Serif"],
        "font.size": 8,
        "axes.labelsize": 8,
        "axes.titlesize": 8,
        "legend.fontsize": 7,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "grid.linewidth": 0.5,
        "lines.linewidth": 1.2,
        "lines.markersize": 4.0,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.dpi": 160,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
    }
)


def load() -> pd.DataFrame:
    if not RAW.exists():
        raise SystemExit(f"missing {RAW}; run the full experiment matrix first")
    df = pd.read_csv(RAW)
    df["algorithm"] = pd.Categorical(
        df["algorithm"], categories=list(COLORS), ordered=True
    )
    return df


def panel_label(ax, text: str) -> None:
    ax.text(
        0.02,
        0.96,
        text,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8,
        fontweight="bold",
    )


def fig_density(df: pd.DataFrame) -> Path:
    sub = pd.read_csv(ROOT / "results" / "summary" / "table_density.csv")
    topologies = ["random", "maze", "rooms", "city"]
    titles = ["(a) Random", "(b) Maze (loop probability)", "(c) Rooms", "(d) City"]
    algs = ["Dijkstra", "A*", "MXA*", "MXA*-ID"]
    fig, axes = plt.subplots(2, 2, figsize=(7.1, 3.3), sharex=True)
    for ax, topo, title in zip(axes.flat, topologies, titles):
        t = sub[sub["topology"] == topo]
        ys: list[float] = []
        for alg in algs:
            a = t[t["algorithm"] == alg].sort_values("density")
            if a.empty:
                continue
            x = a["density"].to_numpy(dtype=float)
            y = a["expl"].to_numpy(dtype=float)
            ys.extend(y.tolist())
            marker_kw = {}
            if alg == "MXA*":
                marker_kw = {
                    "markersize": 6.5,
                    "markerfacecolor": "none",
                    "markeredgewidth": 0.9,
                }
            elif alg == "MXA*-ID":
                marker_kw = {"markersize": 3.2}
            ax.plot(
                x,
                y,
                color=COLORS[alg],
                marker=MARKERS[alg],
                label=LABELS[alg],
                zorder=3,
                **marker_kw,
            )
        ax.set_yscale("log")
        ax.set_xticks([0.1, 0.2, 0.3])
        ax.set_xticklabels(["0.10", "0.20", "0.30"])
        ax.set_ylim(bottom=max(1.0, min(ys) * 0.55), top=max(ys) * 2.0)
        panel_label(ax, title)
        ax.grid(True, which="major", alpha=0.25)
        ax.grid(True, which="minor", alpha=0.10)
    for ax in axes[:, 0]:
        ax.set_ylabel("Explorations (log scale)")
    for ax in axes[1, :]:
        ax.set_xlabel("Obstacle density")
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="lower center",
        ncol=4,
        frameon=False,
        bbox_to_anchor=(0.5, 0.005),
        handlelength=1.8,
        columnspacing=1.6,
    )
    fig.tight_layout(rect=(0, 0.13, 1, 1))
    out = FIG / "density.pdf"
    fig.savefig(out)
    fig.savefig(out.with_suffix(".png"))
    plt.close(fig)
    return out


def fig_multi(df: pd.DataFrame) -> Path:
    sub = df[df["experiment"] == "multi"]
    topologies = ["random", "rooms"]
    titles = ["(a) Random 64x64", "(b) Rooms 64x64"]
    fig, axes = plt.subplots(1, 2, figsize=(7.1, 2.7), sharex=True)
    for ax, topo, title in zip(axes, topologies, titles):
        t = sub[sub["topology"] == topo]
        for alg, color in [("A*", COLORS["A*"]), ("MXA*-ID", COLORS["MXA*-ID"])]:
            for mode, style, fill in [
                ("cold", "--", "white"),
                ("warm", "-", color),
            ]:
                a = (
                    t[(t["algorithm"] == alg) & (t["memory_mode"] == mode)]
                    .groupby("query_index")["cumulative_explorations"]
                    .agg(["mean", "std"])
                    .reset_index()
                )
                if a.empty:
                    continue
                label = f"{alg} {'cold' if mode == 'cold' else 'warm (memory)'}"
                ax.errorbar(
                    a["query_index"] + 1,
                    a["mean"],
                    yerr=a["std"],
                    color=color,
                    linestyle=style,
                    marker="o" if alg == "A*" else "D",
                    markerfacecolor=fill,
                    markeredgecolor=color,
                    markersize=3.2,
                    capsize=1.5,
                    elinewidth=0.6,
                    label=label,
                    zorder=3,
                )
        ax.set_title(title)
        ax.set_xlabel("Query index")
        ax.set_xticks(range(1, 11, 2))
        ax.grid(True, alpha=0.25)
    axes[0].set_ylabel("Cumulative explorations")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="lower center",
        ncol=4,
        frameon=False,
        bbox_to_anchor=(0.5, -0.01),
        handlelength=2.2,
        columnspacing=1.2,
    )
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    out = FIG / "multi_query.pdf"
    fig.savefig(out)
    fig.savefig(out.with_suffix(".png"))
    plt.close(fig)
    return out


def fig_memory(df: pd.DataFrame) -> Path:
    sub = df[df["experiment"] == "memory"]
    algs = ["Dijkstra", "A*", "MXA*", "MXA*-ID"]
    widths = [64, 128]
    fig, ax = plt.subplots(figsize=(3.45, 2.4))
    x = np.arange(len(widths))
    width = 0.18
    for i, alg in enumerate(algs):
        vals = []
        for w in widths:
            a = sub[(sub["algorithm"] == alg) & (sub["width"] == w)]["peak_memory_kb"]
            vals.append(a.mean() if not a.empty else np.nan)
        ax.bar(
            x + (i - 1.5) * width,
            vals,
            width,
            color=COLORS[alg],
            label=LABELS[alg],
            edgecolor="white",
            linewidth=0.4,
        )
    ax.set_xticks(x)
    ax.set_xticklabels([f"{w}x{w}" for w in widths])
    ax.set_ylabel("Peak traced memory (KB)")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(frameon=False, fontsize=6, ncol=2)
    fig.tight_layout()
    out = FIG / "memory.pdf"
    fig.savefig(out)
    fig.savefig(out.with_suffix(".png"))
    plt.close(fig)
    return out


def main() -> None:
    df = load()
    print(fig_density(df))
    print(fig_multi(df))
    print(fig_memory(df))


if __name__ == "__main__":
    main()
