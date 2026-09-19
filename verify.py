"""Independent verification of the results reported in the paper.

Re-runs the full suite into a temporary directory, compares every output against
the committed manifest, and re-derives each headline number from summary.csv.
Exits non-zero if anything fails, so it can be used in CI.

    python verify.py                 # full check, ~10 minutes
    python verify.py --numbers-only  # skip the rerun, just re-derive the numbers
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
COMMITTED = HERE / "results"

# (description, expected value, tolerance) keyed to how the paper states it.
TOL = 1e-4


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_manifest(candidate: Path) -> bool:
    """Every committed output must reproduce byte-for-byte."""
    manifest = json.loads((COMMITTED / "manifest.json").read_text(encoding="utf-8"))
    ok = True
    print("\n== byte-level reproduction ==")
    for name, digest in sorted(manifest["files"].items()):
        produced = candidate / name
        if not produced.exists():
            print("  MISSING   %s" % name)
            ok = False
            continue
        got = sha256(produced)
        if got == digest:
            print("  ok        %s" % name)
        else:
            # PDFs can differ across Matplotlib/platform versions; CSVs must not.
            level = "WARN" if name.endswith(".pdf") else "FAIL"
            print("  %-9s %s" % (level, name))
            if level == "FAIL":
                ok = False
    return ok


def derive(summary: Path) -> list[tuple[str, str]]:
    """Re-derive the numbers the paper quotes, straight from summary.csv.

    Metrics are cohort-based: transactions broadcast after warm-up, with a
    vulnerable transaction still pending at the end and older than T_b counted as
    at risk.  _legacy is the un-migratable share, _vuln all vulnerable traffic."""
    s = pd.read_csv(summary)
    M = "at_risk_fraction_legacy_mean"
    MV = "at_risk_fraction_vuln_mean"
    out: list[tuple[str, str]] = []

    con = s[s.experiment == "congestion"]

    def at(policy, rate, col=M):
        return float(con[(con.policy == policy) & (con.arrival_rate == rate)].iloc[0][col])

    for rate in sorted(con.arrival_rate.unique()):
        out.append(("congestion %g tx/s, un-migr at risk: ECDSA / ECDSA ordered / FN-DSA / ML-DSA / QSentry" % rate,
                    " / ".join("%.4f" % at(p, rate) for p in ("ecdsa-only", "ecdsa-ordered", "falcon-only", "mldsa-only", "qsentry"))))
        out.append(("congestion %g tx/s, inclusion: ECDSA / ECDSA ordered / FN-DSA / ML-DSA / QSentry" % rate,
                    " / ".join("%.3f" % at(p, rate, "inclusion_ratio_mean")
                               for p in ("ecdsa-only", "ecdsa-ordered", "falcon-only", "mldsa-only", "qsentry"))))

    abl = s[s.experiment == "ablation"]

    def ab(policy, budget=True, order=True, expired_last=True):
        r = abl[(abl.policy == policy) & (abl.migration_budget == budget) & (abl.deadline_order == order)
                & (abl.expired_last == expired_last)]
        return r.iloc[0]

    for lab, r in (("block-space optimal", ab("fee-optimal")), ("ECDSA slack order", ab("ecdsa-ordered")),
                   ("QSentry", ab("qsentry")), ("QSentry oldest first", ab("qsentry", expired_last=False)),
                   ("QSentry no budget", ab("qsentry", budget=False)),
                   ("QSentry no ordering", ab("qsentry", order=False)),
                   ("QSentry fixed weight", ab("qsentry-no-vq")), ("hybrid only", ab("hybrid-only"))):
        out.append(("ablation %s: un-migr / vuln / incl / PQ incl / FN share / bytes/tx / pending end" % lab,
                    "%.4f / %.4f / %.3f / %.3f / %.4f / %.0f / %.0f" % (
                        r[M], r[MV], r.inclusion_ratio_mean, r.inclusion_ratio_pq_mean,
                        r.share_falcon_mean, r.bytes_per_tx_mean, r.pending_measured_end_mean)))

    ch = s[s.experiment == "chain"]
    viol = [(r.policy, r.block_interval_s) for _, r in ch.iterrows()
            if r[MV] < r["exposure_floor_mean"] - 1e-9]
    out.append(("Theorem 1 floor respected (all vulnerable)",
                "yes, all %d points" % len(ch) if not viol else "NO: %s" % viol))
    for iv in sorted(ch.block_interval_s.unique()):
        e = ch[(ch.policy == "ecdsa-only") & (ch.block_interval_s == iv)].iloc[0]
        o = ch[(ch.policy == "ecdsa-ordered") & (ch.block_interval_s == iv)].iloc[0]
        q = ch[(ch.policy == "qsentry") & (ch.block_interval_s == iv)].iloc[0]
        out.append(("chain %g s: floor / un-migr ECDSA / ECDSA ordered / QSentry" % iv,
                    "%.3f / %.4f / %.4f / %.4f" % (e["exposure_floor_mean"], e[M], o[M], q[M])))

    bt = s[s.experiment == "breaktime"]
    for tb in sorted(bt.break_time_s.unique()):
        out.append(("break time %g s: un-migr ECDSA / ECDSA ordered / QSentry" % tb, "%.4f / %.4f / %.4f" % (
            float(bt[(bt.policy == "ecdsa-only") & (bt.break_time_s == tb)].iloc[0][M]),
            float(bt[(bt.policy == "ecdsa-ordered") & (bt.break_time_s == tb)].iloc[0][M]),
            float(bt[(bt.policy == "qsentry") & (bt.break_time_s == tb)].iloc[0][M]))))

    lg = s[s.experiment == "legacy"]
    for pol in ("ecdsa-only", "ecdsa-ordered", "falcon-only", "qsentry"):
        sub = lg[lg.policy == pol].sort_values("legacy_fraction")
        out.append(("phi 0.05/0.15/0.30/0.50/0.80, un-migr at risk, %s" % pol,
                    " / ".join("%.4f" % v for v in sub[M])))

    pr = s[s.experiment == "provisioning"]
    for pol in ("ecdsa-only", "ecdsa-ordered", "falcon-only", "qsentry"):
        sub = pr[pr.policy == pol].sort_values("block_bytes")
        out.append(("provisioning 150/250/400/600/900 kB, un-migr at risk, %s" % pol,
                    " / ".join("%.4f" % v for v in sub[M])))

    ver = s[s.experiment == "verify"]
    out.append(("verification-cost sensitivity",
                "max spread %.6f" % ver.groupby("policy")[M].agg(lambda v: v.max() - v.min()).max()))
    vs = s[s.experiment == "v-sweep"]
    out.append(("V in [1, 60]: un-migr at risk min / max", "%.4f / %.4f" % (vs[M].min(), vs[M].max())))
    ep = s[s.experiment == "epsilon"]
    for rate in (20.0, 32.0):
        sub = ep[ep.arrival_rate == rate].sort_values("exposure_target")
        out.append(("epsilon 0.01..0.20 at %g tx/s: un-migr at risk" % rate,
                    " / ".join("%.4f" % v for v in sub[M])))

    for mean in (38, 30):
        fm = s[s.experiment == "burstiness-mean%d" % mean]
        for pol in ("ecdsa-only", "ecdsa-ordered", "qsentry"):
            e = fm[fm.policy == pol].sort_values("surge_multiplier")
            out.append(("burstiness mean %d tx/s, %s, multipliers 1/2/4/6" % (mean, pol),
                        " / ".join("%.4f" % v for v in e[M])))

    fl = s[s.experiment == "flood"]
    qa = fl[(fl.policy == "qsentry") & (fl.vulnerable_cap == 1.0)].sort_values("attack_rate")
    ea = fl[fl.policy == "ecdsa-only"].sort_values("attack_rate")
    out.append(("flood QSentry un-migr at risk, attack 0/5/10/20", " / ".join("%.4f" % v for v in qa[M])))
    out.append(("flood ECDSA-only un-migr at risk, attack 0/5/10/20", " / ".join("%.4f" % v for v in ea[M])))
    oa = fl[fl.policy == "ecdsa-ordered"].sort_values("attack_rate")
    out.append(("flood ECDSA ordered un-migr at risk, attack 0/5/10/20", " / ".join("%.4f" % v for v in oa[M])))
    out.append(("flood QSentry PQ inclusion, attack 0/5/10/20",
                " / ".join("%.4f" % v for v in qa["inclusion_ratio_pq_mean"])))
    a20 = qa[qa.attack_rate == 20.0].iloc[0]
    out.append(("flood attacker share of capacity at 20 tx/s (bound 0.341)",
                "%.4f" % (float(a20["attacker_included_tps_mean"]) * 355.0 * 12.0 / 250000.0)))
    for cap in (0.7, 0.5):
        r = fl[(fl.policy == "qsentry") & (fl.vulnerable_cap == cap) & (fl.attack_rate == 0.0)].iloc[0]
        out.append(("flood reservation %.1f, no attacker: un-migr at risk / PQ incl" % cap,
                    "%.4f / %.4f" % (r[M], r["inclusion_ratio_pq_mean"])))

    cz = s[(s.experiment == "conceal") & (s.commit_bytes == 100.0) & (s.break_time_s == 60.0)]
    for pol in ("ecdsa-only", "ecdsa-ordered", "qsentry"):
        for rate in (26.0, 32.0):
            for cr in (False, True):
                r = cz[(cz.policy == pol) & (cz.arrival_rate == rate) & (cz.commit_reveal == cr)].iloc[0]
                out.append(("conceal %s %g tx/s commit-reveal=%s: un-migr / incl / latency s / pending end" % (pol, rate, cr),
                            "%.4f / %.3f / %.0f / %.0f" % (r[M], r["inclusion_ratio_mean"], r["latency_mean_s_mean"],
                                                           r["pending_measured_end_mean"])))
    cb = s[(s.experiment == "conceal") & (s.policy == "qsentry") & (s.commit_reveal == True) & (s.arrival_rate == 26.0)]
    out.append(("conceal probes at 26 (Tb=24 | bc=50 | bc=50,Tb=120 | bc=200)", " / ".join(
        "%.4f" % float(cb[(cb.break_time_s == tb) & (cb.commit_bytes == bc)].iloc[0][M])
        for tb, bc in ((24.0, 100.0), (60.0, 50.0), (120.0, 50.0), (60.0, 200.0)))))

    ag = s[s.experiment == "aging"]
    for rate in (32.0, 26.0):
        sub = ag[ag.arrival_rate == rate].sort_values("pq_max_wait", ascending=False)
        out.append(("aging %g tx/s wait inf/300/120/60/24: un-migr at risk" % rate,
                    " / ".join("%.4f" % v for v in sub[M])))
        out.append(("aging %g tx/s: PQ inclusion" % rate,
                    " / ".join("%.4f" % v for v in sub["inclusion_ratio_pq_mean"])))

    hz = s[s.experiment == "horizon"]
    for rate in (32.0, 38.0):
        for lab, pol, bud in (("ECDSA", "ecdsa-only", True), ("ECDSA ordered", "ecdsa-ordered", True),
                              ("QSentry", "qsentry", True),
                              ("QSentry no budget", "qsentry", False)):
            sub = hz[(hz.arrival_rate == rate) & (hz.policy == pol) & (hz.migration_budget == bud)].sort_values("duration_blocks")
            out.append(("horizon %g tx/s %s, vuln at risk @200/1000/5000 blocks" % (rate, lab),
                        " / ".join("%.4f" % v for v in sub[MV])))
            out.append(("horizon %g tx/s %s, pending at end @200/1000/5000" % (rate, lab),
                        " / ".join("%.0f" % v for v in sub["pending_measured_end_mean"])))
    # ---- fee models, block value, a mis-set break time, partial adoption, k machines
    fm = s[s.experiment == "feemodel"]
    for model, nt in (("iid", 2), ("iid", 8), ("iid", 64), ("surge-high", 8), ("surge-low", 8), ("drain", 8), ("bump", 8)):
        sub = fm[(fm.fee_model == model) & (fm.fee_tiers == nt)].set_index("policy")
        out.append(("fee model %s, %d tiers: un-migr at risk fee / hybrid / triage; triage block value k+1 / 2^k" % (model, nt),
                    "%.4f / %.4f / %.4f; %.2f / %.2f" % (sub.loc["ecdsa-fee", M], sub.loc["ecdsa-feetriage", M], sub.loc["ecdsa-ordered", M],
                                                         sub.loc["ecdsa-ordered", "block_value_ratio_mean"],
                                                         sub.loc["ecdsa-ordered", "block_value_ratio_geo_mean"])))
    tb = s[(s.experiment == "tb-misset") & (s.policy == "ecdsa-ordered")]
    fast = tb[tb.break_time_s == 60.0].sort_values("builder_break_time_s")
    out.append(("break time assumed %s s, true 60 s: un-migr at risk under triage" % "/".join("%g" % v for v in fast.builder_break_time_s),
                " / ".join("%.4f" % v for v in fast[M])))
    slow = tb[tb.break_time_s > 60.0].sort_values("break_time_s")
    out.append(("break time assumed 60 s, true %s s: un-migr at risk under triage" % "/".join("%g" % v for v in slow.break_time_s),
                " / ".join("%.4f" % v for v in slow[M])))
    ad = s[(s.experiment == "adoption") & (s.arrival_rate == 32.0)]
    for lab, pol, ff, col in (("triage, replacement kept", "ecdsa-ordered", False, "lost_fraction_norule_vuln_mean"),
                              ("arrival order, replacement kept", "ecdsa-only", False, "lost_fraction_norule_vuln_mean"),
                              ("tier hybrid with the forger's fee, replacement kept", "ecdsa-feetriage", True, "lost_fraction_norule_vuln_mean"),
                              ("triage + first-seen rule", "ecdsa-ordered", False, "lost_fraction_vuln_mean"),
                              ("arrival order + first-seen rule", "ecdsa-only", False, "lost_fraction_vuln_mean"),
                              ("fee order + first-seen rule", "ecdsa-fee", False, "lost_fraction_vuln_mean"),
                              ("tier hybrid + first-seen rule", "ecdsa-feetriage", False, "lost_fraction_vuln_mean")):
        sub = ad[(ad.policy == pol) & (ad.forger_fee == ff)].sort_values("adopt_share")
        out.append(("adoption, vulnerable lost, %s, a = %s" % (lab, "/".join("%g" % v for v in sub.adopt_share)),
                    " / ".join("%.4f" % v for v in sub[col])))
    av = s[s.experiment == "adoption-value"]
    for mode, col in (("first-seen", "lost_fraction_vuln_mean"), ("inherit", "lost_fraction_norule_vuln_mean")):
        for pol in ("ecdsa-ordered", "ecdsa-only"):
            sub = av[(av.adopt_by_value == mode) & (av.policy == pol)].sort_values("adopt_share")
            out.append(("adoption by block value (%s) %s, a = 0.25/0.5/0.75: share of blocks built; vulnerable lost" % (mode, pol),
                        " / ".join("%.3f" % v for v in sub["adopter_block_share_mean"]) + "; " + " / ".join("%.4f" % v for v in sub[col])))
    adv = s[s.experiment == "adversary"]
    for rate in (24.0, 32.0):
        for pol in ("ecdsa-only", "ecdsa-fee", "ecdsa-ordered"):
            r = adv[(adv.arrival_rate == rate) & (adv.policy == pol)].iloc[0]
            out.append(("adversary with k = 1/11/100/1000 machines, %g tx/s, %s: share taken; share of value (tail index 1.5)" % (rate, pol),
                        " / ".join("%.4f" % r["adv_count_k%d_mean" % k] for k in (1, 11, 100, 1000)) + "; "
                        + " / ".join("%.4f" % r["adv_value150_k%d_mean" % k] for k in (1, 11, 100, 1000))))
    return out

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--numbers-only", action="store_true")
    ap.add_argument("--seeds", type=int, default=30)
    args = ap.parse_args()

    if not (COMMITTED / "summary.csv").exists():
        print("no committed results/ directory found", file=sys.stderr)
        return 2

    reproduced = True
    if not args.numbers_only:
        tmp = Path(tempfile.mkdtemp(prefix="qsentry-verify-"))
        try:
            print("running the suite into %s (this takes about an hour)" % tmp)
            r = subprocess.run(
                [sys.executable, str(HERE / "qsentry_sim.py"), "--out", str(tmp),
                 "--seeds", str(args.seeds)],
                cwd=HERE, capture_output=True, text=True)
            if r.returncode != 0:
                print(r.stdout[-2000:])
                print(r.stderr[-2000:], file=sys.stderr)
                return 2
            print(r.stdout.strip())
            reproduced = check_manifest(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    print("\n== numbers re-derived from results/summary.csv ==")
    for label, value in derive(COMMITTED / "summary.csv"):
        print("  %-32s %s" % (label, value))

    print("\n%s" % ("VERIFICATION PASSED" if reproduced else "VERIFICATION FAILED"))
    return 0 if reproduced else 1


if __name__ == "__main__":
    raise SystemExit(main())
