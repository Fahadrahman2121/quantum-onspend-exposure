"""Experiment suite. Deterministic and reproducible on the pinned versions;
PDF creation timestamps are suppressed so figure digests reproduce too."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from qsentry_sim import POLICIES, Config, exposure_floor, simulate

MAIN = ("ecdsa-only", "falcon-only", "mldsa-only", "qsentry")
STYLE = {
    "ecdsa-only": ("#9aa0a6", "o", "ECDSA only"),
    "falcon-only": ("#74c476", "^", "FN-DSA only"),
    "mldsa-only": ("#e6a23c", "s", "ML-DSA only"),
    "hybrid-only": ("#c46bb5", "v", "hybrid only"),
    "fee-optimal": ("#3182bd", "P", "block-space optimal"),
    "qsentry": ("#756bb1", "D", "QSentry"),
    "qsentry-no-vq": ("#d62728", "X", "QSentry, fixed weight"),
}
PDF = {"bbox_inches": "tight", "metadata": {"CreationDate": None}}


def ci95(s: pd.Series) -> float:
    v = s.dropna().to_numpy(dtype=float)
    if len(v) < 2:
        return float("nan")
    return float(stats.t.ppf(0.975, len(v) - 1) * stats.sem(v))


def _run(rows, experiment, seeds, **kw):
    for seed in seeds:
        row, _ = simulate(Config(seed=seed, **kw))
        row["experiment"] = experiment
        rows.append(row)


def run(out_dir: Path, seeds: int, quick: bool):
    out_dir.mkdir(parents=True, exist_ok=True)
    sr = range(1, (5 if quick else seeds) + 1)
    rows: list[dict] = []

    for rate in (20, 26, 32, 38, 44, 50):
        for p in MAIN:
            _run(rows, "congestion", sr, policy=p, arrival_rate=rate)

    for tb in (15, 30, 60, 120, 240):
        for p in MAIN:
            _run(rows, "breaktime", sr, policy=p, break_time_s=tb)

    # Chain type.  Block capacity is held per unit time so that only the
    # interval changes, isolating the residual-block-time floor.
    for interval in (2.0, 6.0, 12.0, 60.0, 150.0, 600.0):
        for p in ("ecdsa-only", "qsentry"):
            _run(rows, "chain", sr, policy=p, block_interval_s=interval,
                 block_bytes=250_000.0 * interval / 12.0)

    for phi in (0.05, 0.15, 0.30, 0.50, 0.80):
        for p in ("ecdsa-only", "falcon-only", "qsentry"):
            _run(rows, "legacy", sr, policy=p, legacy_fraction=phi)

    for p in ("fee-optimal", "qsentry", "qsentry-no-vq", "hybrid-only"):
        _run(rows, "ablation", sr, policy=p, arrival_rate=38.0)

    for v in (1.0, 4.0, 8.0, 20.0, 60.0):
        _run(rows, "v-sweep", sr, policy="qsentry", arrival_rate=38.0, control_v=v)

    for vb in (10_000.0, 20_000.0, 40_000.0):
        for p in ("ecdsa-only", "qsentry"):
            _run(rows, "verify", sr, policy=p, verify_budget_per_block=vb)

    # Provisioning: how much block space does each policy need to hold the
    # un-migratable share below target?
    for bb in (150_000.0, 250_000.0, 400_000.0, 600_000.0, 900_000.0):
        for p in ("ecdsa-only", "falcon-only", "qsentry"):
            _run(rows, "provisioning", sr, policy=p, arrival_rate=38.0, block_bytes=bb)

    # Burstiness: exposure is created by surges, so how much of the result
    # depends on how bursty demand is?
    for sm in (1.0, 2.0, 4.0, 6.0):
        for p in ("ecdsa-only", "qsentry"):
            _run(rows, "burstiness", sr, policy=p, arrival_rate=38.0, surge_multiplier=sm)

    # Burstiness at FIXED MEAN load.  The sweep above holds the between-surge
    # rate fixed, so the long-run mean offered load rises with the multiplier
    # and the two effects are confounded.  Here the between-surge rate is
    # scaled so that the long-run mean stays constant: 38 tx/s (65% of the
    # 58.7 tx/s ECDSA capacity) and 30 tx/s (51%).  Only the shape of demand
    # changes, which is the claim the paper's premise rests on.
    c0 = Config()
    pi_surge = c0.surge_enter / (c0.surge_enter + c0.surge_leave)
    for mean in (38.0, 30.0):
        for sm in (1.0, 2.0, 4.0, 6.0):
            base = mean / (1.0 + pi_surge * (sm - 1.0))
            for p in ("ecdsa-only", "qsentry"):
                _run(rows, "burstiness-mean%d" % int(mean), sr, policy=p,
                     arrival_rate=base, surge_multiplier=sm)

    # Does the virtual queue actually enforce the target?  Theorem 4 promises
    # this only when a policy meeting it exists, so we sweep epsilon at a load
    # where one does (26 tx/s) and at a load where none does (38 tx/s).
    for eps in (0.01, 0.02, 0.05, 0.10, 0.20):
        for rate in (20.0, 32.0):
            _run(rows, "epsilon", sr, policy="qsentry",
                 arrival_rate=rate, exposure_target=eps)

    data = pd.DataFrame(rows)
    data.to_csv(out_dir / "results.csv", index=False, lineterminator="\n")

    metrics = ["inclusion_ratio", "at_risk_fraction", "at_risk_fraction_legacy",
               "window_mean_s", "window_p95_s", "window_legacy_mean_s",
               "window_legacy_p95_s", "throughput_tps", "bytes_per_tx",
               "mean_pending_tx", "exposure_floor", "verify_per_tx",
               "share_ecdsa", "share_falcon", "share_mldsa", "share_hybrid"]
    group = ["experiment", "policy", "arrival_rate", "break_time_s",
             "block_interval_s", "legacy_fraction", "control_v",
             "verify_budget_per_block", "block_bytes", "surge_multiplier",
             "exposure_target"]
    summary = data.groupby(group, dropna=False)[metrics].agg(["mean", ci95]).reset_index()
    summary.columns = ["_".join(str(x) for x in c if x).rstrip("_") for c in summary.columns]
    summary.to_csv(out_dir / "summary.csv", index=False, lineterminator="\n")

    def panel(ax, experiment, key, metric, policies, xlabel, ylabel, logx=False):
        sub = data[data.experiment == experiment]
        for policy in policies:
            chunk = sub[sub.policy == policy]
            if chunk.empty:
                continue
            x = np.array(sorted(chunk[key].unique()))
            g = chunk.groupby(key)
            y = g[metric].mean().reindex(x)
            e = g[metric].apply(ci95).reindex(x)
            c, mk, lab = STYLE[policy]
            ax.errorbar(x, y, yerr=e, marker=mk, capsize=2, color=c, label=lab, linewidth=1.4)
        if logx:
            ax.set_xscale("log")
        ax.set(xlabel=xlabel, ylabel=ylabel)
        ax.grid(alpha=0.25)

    # Figure 1: the migration paradox under congestion
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.4))
    panel(axes[0], "congestion", "arrival_rate", "at_risk_fraction", MAIN,
          r"Between-surge load $\lambda_0$ (tx/s)", "At risk, all traffic")
    panel(axes[1], "congestion", "arrival_rate", "at_risk_fraction_legacy", MAIN,
          r"Between-surge load $\lambda_0$ (tx/s)", "At risk, un-migratable")
    panel(axes[2], "congestion", "arrival_rate", "inclusion_ratio", MAIN,
          r"Between-surge load $\lambda_0$ (tx/s)", "Inclusion ratio")
    axes[0].legend(fontsize=6, frameon=False)
    fig.tight_layout()
    fig.savefig(out_dir / "paradox.pdf", **PDF)
    fig.savefig(out_dir / "paradox.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    # Figure 2: adversary capability and chain type, against the theoretical floor
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.6))
    panel(axes[0], "breaktime", "break_time_s", "at_risk_fraction_legacy", MAIN,
          r"Break time $T_b$ (s)", "At risk, un-migratable")
    panel(axes[1], "chain", "block_interval_s", "at_risk_fraction_legacy",
          ("ecdsa-only", "qsentry"), r"Block interval $\Delta$ (s)",
          "At risk, un-migratable", logx=True)
    xs = np.logspace(np.log10(2.0), np.log10(600.0), 100)
    axes[1].plot(xs, [exposure_floor(60.0, x) for x in xs], color="#d62728",
                 linestyle="--", linewidth=1.2, label=r"floor $1-T_b/\Delta$")
    axes[0].legend(fontsize=6, frameon=False)
    axes[1].legend(fontsize=6, frameon=False)
    fig.tight_layout()
    fig.savefig(out_dir / "floor.pdf", **PDF)
    fig.savefig(out_dir / "floor.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    # Figure 3: migration progress and the cost-exposure tradeoff
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.6))
    panel(axes[0], "legacy", "legacy_fraction", "at_risk_fraction_legacy",
          ("ecdsa-only", "falcon-only", "qsentry"),
          r"Un-migratable share $\varphi$", "At risk, un-migratable")
    v = data[data.experiment == "v-sweep"].groupby("control_v")
    vm = v[["bytes_per_tx", "at_risk_fraction_legacy"]].mean()
    axes[1].plot(vm.bytes_per_tx, vm.at_risk_fraction_legacy, "o-", color="#756bb1")
    for cv, r in vm.iterrows():
        axes[1].annotate(f"V={cv:g}", (r.bytes_per_tx, r.at_risk_fraction_legacy),
                         xytext=(4, 4), textcoords="offset points", fontsize=6)
    axes[1].set(xlabel="Block space per transaction (bytes)",
                ylabel="At risk, un-migratable")
    axes[1].grid(alpha=0.25)
    axes[0].legend(fontsize=6, frameon=False)
    fig.tight_layout()
    fig.savefig(out_dir / "migration.pdf", **PDF)
    fig.savefig(out_dir / "migration.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    # Figure 4: provisioning and burstiness
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.6))
    panel(axes[0], "provisioning", "block_bytes", "at_risk_fraction_legacy",
          ("ecdsa-only", "falcon-only", "qsentry"),
          "Block capacity (bytes)", "At risk, un-migratable")
    panel(axes[1], "burstiness-mean38", "surge_multiplier", "at_risk_fraction_legacy",
          ("ecdsa-only", "qsentry"), "Surge multiplier (mean load 38 tx/s)",
          "At risk, un-migratable")
    axes[0].legend(fontsize=6, frameon=False)
    axes[1].legend(fontsize=6, frameon=False)
    fig.tight_layout()
    fig.savefig(out_dir / "provisioning.pdf", **PDF)
    fig.savefig(out_dir / "provisioning.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    # Figure 5: a representative trace through two demand surges
    _, trace = simulate(Config(policy="qsentry", seed=2026, arrival_rate=38.0),
                        keep_trace=True)
    trace.to_csv(out_dir / "trace_qsentry.csv", index=False, lineterminator="\n")
    _, base = simulate(Config(policy="ecdsa-only", seed=2026, arrival_rate=38.0),
                       keep_trace=True)
    base.to_csv(out_dir / "trace_ecdsa.csv", index=False, lineterminator="\n")
    fig, ax = plt.subplots(figsize=(7.2, 2.4))
    ax.plot(base.time_s, base.vulnerable_window_s, color="#9aa0a6",
            linewidth=1.2, label="ECDSA only")
    ax.plot(trace.time_s, trace.vulnerable_window_s, color="#756bb1",
            linewidth=1.3, label="QSentry")
    ax.axhline(Config().break_time_s, color="#d62728", linestyle="--",
               linewidth=1.1, label=r"break time $T_b$")
    ax.set(xlabel="Time (s)", ylabel="Vulnerable-class window (s)")
    ax.set_yscale("log")
    ax.grid(alpha=0.25)
    ax2 = ax.twinx()
    ax2.plot(trace.time_s, trace.virtual, color="#3182bd", linewidth=1.0,
             linestyle=":", label="virtual queue")
    ax2.set_ylabel("Virtual exposure queue", fontsize=8)
    h = ax.get_legend_handles_labels()[0] + ax2.get_legend_handles_labels()[0]
    l = ax.get_legend_handles_labels()[1] + ax2.get_legend_handles_labels()[1]
    ax.legend(h, l, fontsize=6, frameon=False, ncol=4, loc="upper left")
    fig.tight_layout()
    fig.savefig(out_dir / "trace.pdf", **PDF)
    fig.savefig(out_dir / "trace.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    abl = data[data.experiment == "ablation"]
    base = abl[abl.policy == "qsentry"].sort_values("seed")
    tests = []
    for other in ("fee-optimal", "qsentry-no-vq", "hybrid-only"):
        rhs = abl[abl.policy == other].sort_values("seed")
        if rhs.empty:
            continue
        for metric in ("at_risk_fraction_legacy", "at_risk_fraction", "bytes_per_tx"):
            a, b = base[metric].to_numpy(), rhs[metric].to_numpy()
            if np.allclose(a, b):
                w, pv = float("nan"), 1.0
            else:
                w, pv = stats.wilcoxon(a, b, zero_method="wilcox", alternative="two-sided")
            pooled = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2.0)
            tests.append({"baseline": other, "metric": metric, "wilcoxon_w": w,
                          "p_value": pv, "mean_qsentry": a.mean(),
                          "mean_baseline": b.mean(),
                          "cohens_d": (a.mean() - b.mean()) / pooled if pooled else float("nan")})
    pd.DataFrame(tests).to_csv(out_dir / "statistical_tests.csv", index=False,
                               lineterminator="\n")

    # CSVs are written with explicit LF and figures carry no timestamp, so
    # every digest below reproduces on any platform, not just this one.
    manifest = {"suite": "quick" if quick else "full", "seeds": len(list(sr)),
                "model": "qsentry_sim.py", "files": {}}
    for path in sorted(out_dir.iterdir()):
        if path.is_file() and path.name != "manifest.json":
            manifest["files"][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    return data
