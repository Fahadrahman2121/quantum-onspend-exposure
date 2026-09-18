"""Experiment suite. Deterministic and reproducible on the pinned versions;
PDF creation timestamps are suppressed so figure digests reproduce too."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
from scipy import stats

from qsentry_sim import POLICIES, Config, exposure_floor, simulate

MAIN = ("ecdsa-only", "falcon-only", "mldsa-only", "qsentry")
STYLE = {
    "ecdsa-only": ("#4d4d4d", "o", "ECDSA only"),
    "falcon-only": ("#74c476", "^", "FN-DSA only"),
    "mldsa-only": ("#e6a23c", "s", "ML-DSA only"),
    "hybrid-only": ("#c46bb5", "v", "hybrid only"),
    "fee-optimal": ("#3182bd", "P", "block-space optimal"),
    "qsentry": ("#756bb1", "D", "QSentry"),
    "qsentry-no-vq": ("#d62728", "X", "QSentry, fixed weight"),
    "ecdsa-ordered": ("#9e9ac8", "d", "ECDSA, slack order"),
}
PDF = {"bbox_inches": "tight", "metadata": {"CreationDate": None}}


def legend(ax, policies, extra=(), **kw):
    """Legend handles drawn as marker + line only.  The handles matplotlib
    builds for errorbar() carry the error-bar stroke through the marker, so
    they do not look like the points in the plot."""
    handles = [Line2D([], [], color=STYLE[p][0], marker=STYLE[p][1], markersize=5,
                      linewidth=1.4, label=STYLE[p][2]) for p in policies]
    handles += list(extra)
    kw.setdefault("fontsize", 6)
    kw.setdefault("frameon", False)
    ax.legend(handles=handles, **kw)


def ci95(s: pd.Series) -> float:
    v = s.dropna().to_numpy(dtype=float)
    if len(v) < 2:
        return float("nan")
    return float(stats.t.ppf(0.975, len(v) - 1) * stats.sem(v))


def _run(rows, experiment, seeds, **kw):
    """Queue one configuration per seed; run() executes the queue in parallel.
    Each run is seeded, so the result does not depend on the execution order."""
    for seed in seeds:
        rows.append((experiment, seed, kw))


def _job(args):
    experiment, seed, kw = args
    row, _ = simulate(Config(seed=seed, **kw))
    row["experiment"] = experiment
    return row


# Corrections from the 2026-09-18 review, applied to every run by --corrected:
# earliest-deadline-first among savable vulnerable transactions, and no
# commit-reveal for the un-migratable share.
CORRECTED = {"expired_last": True, "legacy_commit_reveal": False}


def run(out_dir: Path, seeds: int, quick: bool, figures_only: bool = False,
        overrides: dict | None = None):
    out_dir.mkdir(parents=True, exist_ok=True)
    sr = range(1, (5 if quick else seeds) + 1)
    rows: list[dict] = []
    if figures_only:
        # Regenerate figures, tables and the manifest from committed results.
        data = pd.read_csv(out_dir / "results.csv")
    else:

        # Nominal load: 32 tx/s between surges, a long-run mean of 49.8 tx/s, which is
        # 85% of the 58.7 tx/s ECDSA capacity.  Every sweep below keeps ECDSA stable;
        # overload is studied separately, and explicitly, in `horizon`.
        for rate in (20.0, 24.0, 28.0, 32.0, 36.0):
            for p in MAIN:
                _run(rows, "congestion", sr, policy=p, arrival_rate=rate)
            if overrides:
                _run(rows, "congestion", sr, policy="ecdsa-ordered", arrival_rate=rate)

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

        # Ablation at the nominal load: what each mechanism contributes, including
        # the unbudgeted controller and the controller without slack ordering.
        for p in ("fee-optimal", "qsentry", "qsentry-no-vq", "hybrid-only"):
            _run(rows, "ablation", sr, policy=p)
        _run(rows, "ablation", sr, policy="qsentry", migration_budget=False)
        _run(rows, "ablation", sr, policy="qsentry", deadline_order=False)
        if overrides:
            _run(rows, "ablation", sr, policy="ecdsa-ordered")

        for v in (1.0, 4.0, 8.0, 20.0, 60.0):
            _run(rows, "v-sweep", sr, policy="qsentry", control_v=v)

        for vb in (10_000.0, 20_000.0, 40_000.0):
            for p in ("ecdsa-only", "qsentry"):
                _run(rows, "verify", sr, policy=p, verify_budget_per_block=vb)

        # Provisioning: how much block space does each policy need?
        for bb in (150_000.0, 250_000.0, 400_000.0, 600_000.0, 900_000.0):
            for p in ("ecdsa-only", "falcon-only", "qsentry"):
                _run(rows, "provisioning", sr, policy=p, block_bytes=bb)

        # Burstiness at FIXED MEAN load: the between-surge rate is scaled so that the
        # long-run mean stays at 38 tx/s (65% of ECDSA capacity) or 30 tx/s (51%), so
        # only the shape of demand changes.
        c0 = Config()
        pi_surge = c0.surge_enter / (c0.surge_enter + c0.surge_leave)
        for mean in (38.0, 30.0):
            for sm in (1.0, 2.0, 4.0, 6.0):
                base = mean / (1.0 + pi_surge * (sm - 1.0))
                for p in ("ecdsa-only", "qsentry"):
                    _run(rows, "burstiness-mean%d" % int(mean), sr, policy=p,
                         arrival_rate=base, surge_multiplier=sm)

        # Does the virtual queue enforce the target where it is feasible?
        for eps in (0.01, 0.02, 0.05, 0.10, 0.20):
            for rate in (20.0, 32.0):
                _run(rows, "epsilon", sr, policy="qsentry",
                     arrival_rate=rate, exposure_target=eps)

        # Flood attack on the ordering lever, at 26 tx/s so that the honest chain is
        # inside capacity and the attack, not congestion, is what is measured.
        for atk in (0.0, 5.0, 10.0, 20.0):
            for cap in (1.0, 0.7, 0.5):
                _run(rows, "flood", sr, policy="qsentry", arrival_rate=26.0,
                     attack_rate=atk, vulnerable_cap=cap)
            _run(rows, "flood", sr, policy="ecdsa-only", arrival_rate=26.0,
                 attack_rate=atk)

        # Bounded deferral for post-quantum transactions.
        for rate in (32.0, 26.0):
            for wait in (float("inf"), 300.0, 120.0, 60.0, 24.0):
                _run(rows, "aging", sr, policy="qsentry", arrival_rate=rate, pq_max_wait=wait)

        # Concealment by commit-reveal, alone and composed with slack ordering.  At
        # 32 tx/s the commit overhead itself lifts the byte load past capacity.
        for rate in (26.0, 32.0):
            for p in ("ecdsa-only", "qsentry") + (("ecdsa-ordered",) if overrides else ()):
                for cr in (False, True):
                    _run(rows, "conceal", sr, policy=p, arrival_rate=rate, commit_reveal=cr)
        # Probes of the deterministic window bound W < Delta ceil(b0 / b_c), at the
        # stable load: shrink the break time below it, or the commit so it grows.
        for kw in (dict(break_time_s=24.0), dict(commit_bytes=50.0),
                   dict(commit_bytes=50.0, break_time_s=120.0), dict(commit_bytes=200.0)):
            _run(rows, "conceal", sr, policy="qsentry", arrival_rate=26.0, commit_reveal=True, **kw)

        # Horizon: how the results depend on run length, in a stable regime (32 tx/s,
        # mean 49.8) and an overloaded one (38 tx/s, mean 59.1 > 58.7, where
        # Assumption 3 fails).  Ten seeds: the long unbudgeted runs are expensive.
        hr = range(1, min(10, len(sr)) + 1)
        for mb in (200, 1000, 5000):
            for rate in (32.0, 38.0):
                _run(rows, "horizon", hr, policy="ecdsa-only", arrival_rate=rate,
                     duration_blocks=100 + mb)
                _run(rows, "horizon", hr, policy="qsentry", arrival_rate=rate,
                     duration_blocks=100 + mb)
                _run(rows, "horizon", hr, policy="qsentry", arrival_rate=rate,
                     duration_blocks=100 + mb, migration_budget=False)

        if overrides:
            rows = [(e, s, {**overrides, **kw}) for e, s, kw in rows]

        from concurrent.futures import ProcessPoolExecutor
        import os
        with ProcessPoolExecutor(max_workers=max(1, os.cpu_count() or 2)) as ex:
            rows = list(ex.map(_job, rows, chunksize=2))
        data = pd.DataFrame(rows)
        data.to_csv(out_dir / "results.csv", index=False, lineterminator="\n")

    metrics = ["inclusion_ratio", "at_risk_fraction", "at_risk_fraction_legacy",
               "window_mean_s", "window_p95_s", "window_legacy_mean_s",
               "window_legacy_p95_s", "throughput_tps", "bytes_per_tx",
               "mean_pending_tx", "exposure_floor", "verify_per_tx",
               "share_ecdsa", "share_falcon", "share_mldsa", "share_hybrid",
               "inclusion_ratio_pq", "attacker_included_tps", "attacker_block_share",
               "latency_mean_s", "commit_bytes_per_tx",
               "at_risk_fraction_vuln", "window_vuln_mean_s", "window_vuln_p95_s",
               "pending_measured_end"]
    group = ["experiment", "policy", "arrival_rate", "break_time_s",
             "block_interval_s", "legacy_fraction", "control_v",
             "verify_budget_per_block", "block_bytes", "surge_multiplier",
             "exposure_target", "attack_rate", "vulnerable_cap", "pq_max_wait",
             "commit_reveal", "commit_bytes", "migration_budget", "deadline_order",
             "duration_blocks"]
    summary = data.groupby(group, dropna=False)[metrics].agg(["mean", ci95]).reset_index()
    summary.columns = ["_".join(str(x) for x in c if x).rstrip("_") for c in summary.columns]
    if not figures_only:   # a CSV round-trip would alter float formatting
        summary.to_csv(out_dir / "summary.csv", index=False, lineterminator="\n")

    def panel(ax, experiment, key, metric, policies, xlabel, ylabel, logx=False, xdiv=1.0):
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
            ax.errorbar(x / xdiv, y, yerr=e, marker=mk, markersize=5, capsize=2,
                        elinewidth=0.8, capthick=0.8, color=c, linewidth=1.4,
                        label="_nolegend_")
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
    legend(axes[0], MAIN, loc="upper left")
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
                 linestyle="--", linewidth=1.2, label="_nolegend_")
    legend(axes[0], MAIN, loc="lower left")
    legend(axes[1], ("ecdsa-only", "qsentry"),
           extra=[Line2D([], [], color="#d62728", linestyle="--", linewidth=1.2,
                         label=r"floor $1-T_b/\Delta$")], loc="upper left")
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
    legend(axes[0], ("ecdsa-only", "falcon-only", "qsentry"))
    fig.tight_layout()
    fig.savefig(out_dir / "migration.pdf", **PDF)
    fig.savefig(out_dir / "migration.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    # Figure 4: provisioning and burstiness.  Typeset at column width, so the
    # figure is drawn small with the same font sizes the wide figures use.
    fig, axes = plt.subplots(1, 2, figsize=(3.6, 1.7))
    panel(axes[0], "provisioning", "block_bytes", "at_risk_fraction_legacy",
          ("ecdsa-only", "falcon-only", "qsentry"),
          "Block capacity (kB)", "At risk, un-migratable", xdiv=1000.0)
    panel(axes[1], "burstiness-mean38", "surge_multiplier", "at_risk_fraction_legacy",
          ("ecdsa-only", "qsentry"), "Surge multiplier (mean 38 tx/s)",
          "At risk, un-migratable")
    for ax in axes:
        ax.tick_params(labelsize=6)
        ax.xaxis.label.set_size(6.5)
        ax.yaxis.label.set_size(6.5)
    legend(axes[0], ("ecdsa-only", "falcon-only", "qsentry"), loc="center right", fontsize=5.5)
    legend(axes[1], ("ecdsa-only", "qsentry"), loc="upper left", fontsize=5.5)
    fig.tight_layout(pad=0.4)
    fig.savefig(out_dir / "provisioning.pdf", **PDF)
    fig.savefig(out_dir / "provisioning.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    # Figure 5: a representative trace through two demand surges
    ov = overrides or {}
    _, trace = simulate(Config(policy="qsentry", seed=2026, arrival_rate=32.0, duration_blocks=360, **ov),
                        keep_trace=True)
    trace.to_csv(out_dir / "trace_qsentry.csv", index=False, lineterminator="\n")
    _, base = simulate(Config(policy="ecdsa-only", seed=2026, arrival_rate=32.0, duration_blocks=360, **ov),
                       keep_trace=True)
    base.to_csv(out_dir / "trace_ecdsa.csv", index=False, lineterminator="\n")
    _, nobud = simulate(Config(policy="qsentry", seed=2026, arrival_rate=32.0, duration_blocks=360,
                               migration_budget=False, **ov), keep_trace=True)
    nobud.to_csv(out_dir / "trace_qsentry_nobudget.csv", index=False, lineterminator="\n")
    fig, ax = plt.subplots(figsize=(7.2, 2.4))
    ax.plot(base.time_s, base.vulnerable_window_s, color="#4d4d4d",
            linewidth=1.2, label="ECDSA only")
    ax.plot(trace.time_s, trace.vulnerable_window_s, color="#756bb1",
            linewidth=1.3, linestyle=(0, (4, 2)), label="QSentry")
    ax.plot(nobud.time_s, nobud.vulnerable_window_s, color="#e6a23c",
            linewidth=1.2, label="QSentry, no budget")
    ax.axhline(Config().break_time_s, color="#d62728", linestyle="--",
               linewidth=1.1, label=r"break time $T_b$")
    ax.set(xlabel="Time (s)", ylabel="Vulnerable-class window (s)")
    ax.set_yscale("log")
    ax.grid(alpha=0.25)
    ax2 = ax.twinx()
    ax2.plot(nobud.time_s, nobud.drain_s, color="#e6a23c", linewidth=1.0,
             linestyle=":", label="total drain, no budget")
    ax2.plot(trace.time_s, trace.drain_s, color="#756bb1", linewidth=1.0,
             linestyle=":", label="total drain, QSentry")
    ax2.set_ylabel("Total drain time (s)", fontsize=8)
    h = ax.get_legend_handles_labels()[0] + ax2.get_legend_handles_labels()[0]
    l = ax.get_legend_handles_labels()[1] + ax2.get_legend_handles_labels()[1]
    ax.set_ylim(top=ax.get_ylim()[1] * 2.5)   # headroom so the legend clears the peaks
    ax.legend(h, l, fontsize=6, frameon=False, ncol=4, loc="upper left")
    fig.tight_layout()
    fig.savefig(out_dir / "trace.pdf", **PDF)
    fig.savefig(out_dir / "trace.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    abl = data[data.experiment == "ablation"]
    mb = abl.migration_budget.astype(bool)
    do = abl.deadline_order.astype(bool)
    base = abl[(abl.policy == "qsentry") & mb & do].sort_values("seed")
    tests = []
    variants = {"fee-optimal": abl.policy == "fee-optimal",
                "qsentry-no-vq": abl.policy == "qsentry-no-vq",
                "hybrid-only": abl.policy == "hybrid-only",
                "qsentry-no-budget": (abl.policy == "qsentry") & ~mb,
                "qsentry-no-ordering": (abl.policy == "qsentry") & ~do}
    for other, mask in variants.items():
        rhs = abl[mask].sort_values("seed")
        if rhs.empty:
            continue
        for metric in ("at_risk_fraction_legacy", "at_risk_fraction_vuln", "at_risk_fraction", "bytes_per_tx"):
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
    if not figures_only:
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
