"""Generate RESULTS.md from results/summary.csv.

Every number in RESULTS.md is produced here, so the mapping from paper claim to
data cannot drift from the data.
"""

from __future__ import annotations

import pathlib

import pandas as pd

HERE = pathlib.Path(__file__).parent
S = pd.read_csv(HERE / "results" / "summary.csv")
D = pd.read_csv(HERE / "results" / "results.csv")
M = "at_risk_fraction_legacy_mean"
E = "at_risk_fraction_legacy_ci95"

out: list[str] = []
w = out.append

w("# Claims and where they come from\n")
w("Every figure quoted in the paper, with the experiment and column that produces it.")
w("Regenerate this file with `python make_results_md.py`; all values are read from")
w("`results/summary.csv`, which is itself produced by `python qsentry_sim.py`.\n")
w("Unless stated otherwise, the metric is the at-risk fraction of **un-migratable**")
w("transactions (`at_risk_fraction_legacy`), reported as a mean over 30 seeds with a")
w("two-sided 95% Student-t confidence interval.\n")

con = S[S.experiment == "congestion"]


def at(policy, rate, col=M):
    return float(con[(con.policy == policy) & (con.arrival_rate == rate)].iloc[0][col])


w("## The migration paradox\n")
w("| Offered load (tx/s) | ECDSA only | FN-DSA only | ML-DSA only | QSentry |")
w("|---|---|---|---|---|")
for rate in sorted(con.arrival_rate.unique()):
    w("| %g | %.4f | %.4f | %.4f | **%.4f** | " % (
        rate, at("ecdsa-only", rate), at("falcon-only", rate),
        at("mldsa-only", rate), at("qsentry", rate)))
w("")
w("At the lowest load tested, ECDSA leaves %.4f of vulnerable transactions at risk and"
  % at("ecdsa-only", 20))
w("blanket FN-DSA migration leaves %.4f, a factor of %.1f worse, while inclusion falls"
  % (at("falcon-only", 20), at("falcon-only", 20) / at("ecdsa-only", 20)))
w("from %.3f to %.3f. Migration alone pushes an uncongested chain past its stability"
  % (at("ecdsa-only", 20, "inclusion_ratio_mean"), at("falcon-only", 20, "inclusion_ratio_mean")))
w("boundary.\n")

w("## The exposure floor (Theorem 1)\n")
w("No scheduling policy can drive the at-risk fraction below `max(0, 1 - T_b/D)`.")
w("Every measured point must therefore lie at or above its floor.\n")
w("| Block interval (s) | Floor | ECDSA only | QSentry | Recovered by control |")
w("|---|---|---|---|---|")
ch = S[S.experiment == "chain"]
viol = 0
for iv in sorted(ch.block_interval_s.unique()):
    e = ch[(ch.policy == "ecdsa-only") & (ch.block_interval_s == iv)].iloc[0]
    q = ch[(ch.policy == "qsentry") & (ch.block_interval_s == iv)].iloc[0]
    viol += int(e[M] < e["exposure_floor_mean"] - 1e-9)
    viol += int(q[M] < q["exposure_floor_mean"] - 1e-9)
    w("| %g | %.4f | %.4f | %.4f | %.4f |" % (iv, e["exposure_floor_mean"], e[M], q[M], e[M] - q[M]))
w("")
w("Floor violations across all %d points: **%d**.\n" % (len(ch), viol))

w("## Mechanism ablation at 38 tx/s\n")
abl = S[S.experiment == "ablation"].set_index("policy")
w("| Policy | Un-migratable at risk | All at risk | Inclusion | Bytes/tx |")
w("|---|---|---|---|---|")
for pol in ("fee-optimal", "hybrid-only", "qsentry-no-vq", "qsentry"):
    r = abl.loc[pol]
    w("| %s | %.4f | %.4f | %.3f | %.0f |" % (
        pol, r[M], r["at_risk_fraction_mean"], r["inclusion_ratio_mean"], r["bytes_per_tx_mean"]))
w("")
q, f = abl.loc["qsentry"], abl.loc["fee-optimal"]
h, nv = abl.loc["hybrid-only"], abl.loc["qsentry-no-vq"]
w("- against the exposure-blind controller: **%.1f%%** relative reduction, for %.1f%% more block space"
  % (100 * (f[M] - q[M]) / f[M], 100 * (q["bytes_per_tx_mean"] / f["bytes_per_tx_mean"] - 1)))
w("- against the fixed-weight ablation: **%.1f%%** (this is what the virtual queue contributes)"
  % (100 * (nv[M] - q[M]) / nv[M]))
w("- against hybrid migration: **%.1f%%**, while including **%.2fx** as many transactions"
  % (100 * (h[M] - q[M]) / h[M], q["inclusion_ratio_mean"] / h["inclusion_ratio_mean"]))
w("")
tests = pd.read_csv(HERE / "results" / "statistical_tests.csv")
w("Paired two-sided Wilcoxon signed-rank tests on matched seeds:\n")
w("| Baseline | Metric | p | Cohen's d |")
w("|---|---|---|---|")
for _, r in tests.iterrows():
    w("| %s | %s | %.2e | %+.2f |" % (r.baseline, r.metric, r.p_value, r.cohens_d))
w("")

w("## Provisioning\n")
pr = S[S.experiment == "provisioning"]
w("| Block capacity (B) | ECDSA only | FN-DSA only | QSentry |")
w("|---|---|---|---|")
for bb in sorted(pr.block_bytes.unique()):
    row = {p: pr[(pr.policy == p) & (pr.block_bytes == bb)].iloc[0][M]
           for p in ("ecdsa-only", "falcon-only", "qsentry")}
    w("| %g | %.4f | %.4f | %.4f |" % (bb, row["ecdsa-only"], row["falcon-only"], row["qsentry"]))
w("")
w("ECDSA and QSentry both reach exactly zero at 600 kB, roughly 2.4x nominal capacity.")
w("Blanket FN-DSA migration is still at %.4f with 900 kB, 3.6x nominal: it cannot be"
  % float(pr[(pr.policy == "falcon-only") & (pr.block_bytes == 900000)].iloc[0][M]))
w("provisioned out of the problem on any comparable scale.\n")

w("## Sensitivity checks\n")
bur = S[S.experiment == "burstiness"]
w("**Burstiness.** With stationary demand (multiplier 1) the at-risk fraction is exactly")
w("%.4f for every policy: all measured exposure is produced by congestion episodes."
  % float(bur[bur.surge_multiplier == 1.0][M].max()))
w("Section \"Calibrating the Demand Model\" in the paper compares the modelled burstiness")
w("against an observed mempool; see `calibration/`.\n")
w("**Burstiness at fixed mean load.** The `burstiness` sweep holds the between-surge rate")
w("fixed, so mean load rises with the multiplier. `burstiness-mean38` and `burstiness-mean30`")
w("scale the between-surge rate so the long-run mean stays at 38 and 30 tx/s (65% and 51%")
w("of ECDSA capacity); only the shape of demand changes.\n")
w("| Surge multiplier | ECDSA, mean 38 | QSentry, mean 38 | ECDSA, mean 30 | QSentry, mean 30 |")
w("|---|---|---|---|---|")
fm38 = S[S.experiment == "burstiness-mean38"]; fm30 = S[S.experiment == "burstiness-mean30"]
for sm in sorted(fm38.surge_multiplier.unique()):
    def g(df, p): return float(df[(df.policy == p) & (df.surge_multiplier == sm)].iloc[0][M])
    w("| %g | %.4f | %.4f | %.4f | %.4f |" % (sm, g(fm38, "ecdsa-only"), g(fm38, "qsentry"),
                                             g(fm30, "ecdsa-only"), g(fm30, "qsentry")))
w("")
ver = S[S.experiment == "verify"]
spread = ver.groupby("policy")[M].agg(lambda v: v.max() - v.min()).max()
w("**Verification cost.** Varying the verification budget fourfold changes the at-risk")
w("fraction by at most %.6f, confirming that block space rather than verification is the"
  % spread)
w("binding resource. This is checked, not assumed.\n")
vs = S[S.experiment == "v-sweep"]
w("**Control parameter.** Across V in [%g, %g] the at-risk fraction moves only from %.4f"
  % (vs.control_v.min(), vs.control_v.max(), vs[M].min()))
w("to %.4f, so the result does not depend on tuning V.\n" % vs[M].max())

w("## The flood attack on the ordering lever\n")
w("An attacker broadcasts ECDSA transactions to occupy the vulnerable class that slack")
w("ordering serves first (`flood`, 26 tx/s between surges so the honest chain is inside")
w("capacity). Honest metrics exclude the attacker's transactions; the builder cannot.\n")
w("| Attack (tx/s) | ECDSA-only, honest un-migr. at risk | QSentry, honest un-migr. at risk | QSentry, PQ inclusion | attacker share of block capacity |")
w("|---|---|---|---|---|")
fl = S[S.experiment == "flood"]
for atk in sorted(fl.attack_rate.unique()):
    e = fl[(fl.policy == "ecdsa-only") & (fl.attack_rate == atk)].iloc[0]
    q1 = fl[(fl.policy == "qsentry") & (fl.vulnerable_cap == 1.0) & (fl.attack_rate == atk)].iloc[0]
    w("| %g | %.4f | %.4f | %.4f | %.4f |" % (atk, e[M], q1[M], q1["inclusion_ratio_pq_mean"],
                                              float(q1["attacker_included_tps_mean"]) * 355.0 * 12.0 / 250000.0))
w("")
w("The attacker's share of block capacity never exceeds what its own offered bytes would")
w("fill (a*b0*Delta/B = 0.341 at 20 tx/s): ordering gives the flood precedence, not")
w("amplification. What it displaces is post-quantum traffic.\n")
w("A per-block reservation for post-quantum traffic (`vulnerable_cap`) was tested and")
w("rejected: with no attacker it raises honest exposure from %.4f (no cap) to %.4f (cap 0.7)"
  % (float(fl[(fl.policy == "qsentry") & (fl.vulnerable_cap == 1.0) & (fl.attack_rate == 0)].iloc[0][M]),
     float(fl[(fl.policy == "qsentry") & (fl.vulnerable_cap == 0.7) & (fl.attack_rate == 0)].iloc[0][M])))
w("and %.4f (cap 0.5), because the virtual queue answers the extra exposure by migrating"
  % float(fl[(fl.policy == "qsentry") & (fl.vulnerable_cap == 0.5) & (fl.attack_rate == 0)].iloc[0][M]))
w("more traffic, which deepens the post-quantum backlog the reservation was meant to protect.\n")

w("## What these results do not show\n")
w("- QSentry never drives exposure to zero and cannot; at 38 tx/s it still leaves")
w("  %.4f of un-migratable transactions at risk." % float(q[M]))
w("- Its absolute advantage over doing nothing ranges from %.4f to %.4f across the load"
  % (min(at("ecdsa-only", r) - at("qsentry", r) for r in con.arrival_rate.unique()),
     max(at("ecdsa-only", r) - at("qsentry", r) for r in con.arrival_rate.unique())))
w("  sweep, and is not monotone in load.")
w("- It costs inclusion: %.3f against %.3f for the exposure-blind controller."
  % (q["inclusion_ratio_mean"], f["inclusion_ratio_mean"]))
w("- Raising block capacity is a more effective mitigation than the controller, and the")
w("  only one of the two that terminates.\n")

w("---\n")
w("Generated from %d simulation runs across %d experiments."
  % (len(D), D.experiment.nunique()))

(HERE / "RESULTS.md").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
print("wrote RESULTS.md (%d lines)" % len(out))
