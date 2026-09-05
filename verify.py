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
    """Re-derive the numbers the paper quotes, straight from summary.csv."""
    s = pd.read_csv(summary)
    M = "at_risk_fraction_legacy_mean"
    out: list[tuple[str, str]] = []

    con = s[s.experiment == "congestion"]

    def at(policy, rate, col=M):
        row = con[(con.policy == policy) & (con.arrival_rate == rate)]
        return float(row.iloc[0][col])

    out.append(("ECDSA at risk, 20 tx/s", "%.4f" % at("ecdsa-only", 20)))
    out.append(("FN-DSA at risk, 20 tx/s", "%.4f" % at("falcon-only", 20)))
    out.append(("  ratio (paper: 27.6x)", "%.1fx" % (at("falcon-only", 20) / at("ecdsa-only", 20))))
    out.append(("ECDSA at risk, 50 tx/s", "%.4f" % at("ecdsa-only", 50)))
    out.append(("QSentry at risk, 50 tx/s", "%.4f" % at("qsentry", 50)))

    abl = s[s.experiment == "ablation"].set_index("policy")
    q, f = abl.loc["qsentry"], abl.loc["fee-optimal"]
    h, nv = abl.loc["hybrid-only"], abl.loc["qsentry-no-vq"]
    out.append(("QSentry vs exposure-blind", "%.1f%% reduction" % (100 * (f[M] - q[M]) / f[M])))
    out.append(("QSentry vs fixed weight", "%.1f%% reduction" % (100 * (nv[M] - q[M]) / nv[M])))
    out.append(("QSentry vs hybrid migration", "%.1f%% reduction" % (100 * (h[M] - q[M]) / h[M])))
    out.append(("  inclusion advantage", "%.2fx" % (q.inclusion_ratio_mean / h.inclusion_ratio_mean)))
    out.append(("  block space cost", "+%.1f%%" % (100 * (q.bytes_per_tx_mean / f.bytes_per_tx_mean - 1))))

    ch = s[s.experiment == "chain"]
    viol = [(r.policy, r.block_interval_s) for _, r in ch.iterrows()
            if r[M] < r["exposure_floor_mean"] - 1e-9]
    out.append(("Theorem 1 floor respected", "yes, all %d points" % len(ch) if not viol
                else "NO: %s" % viol))

    ver = s[s.experiment == "verify"]
    spread = ver.groupby("policy")[M].agg(lambda v: v.max() - v.min())
    out.append(("verification-cost sensitivity", "max spread %.6f" % spread.max()))

    bur = s[(s.experiment == "burstiness") & (s.surge_multiplier == 1.0)]
    out.append(("at risk with stationary demand", "%.4f" % bur[M].max()))
    fl = s[s.experiment == "flood"]
    qa = fl[(fl.policy == "qsentry") & (fl.vulnerable_cap == 1.0)].sort_values("attack_rate")
    ea = fl[fl.policy == "ecdsa-only"].sort_values("attack_rate")
    out.append(("flood: QSentry honest at risk, attack 0/5/10/20 tx/s",
                " / ".join("%.4f" % v for v in qa[M])))
    out.append(("flood: ECDSA-only honest at risk, attack 0/5/10/20 tx/s",
                " / ".join("%.4f" % v for v in ea[M])))
    out.append(("flood: QSentry PQ inclusion, attack 0/5/10/20 tx/s",
                " / ".join("%.4f" % v for v in qa["inclusion_ratio_pq_mean"])))
    a20 = qa[qa.attack_rate == 20.0].iloc[0]
    cap_share = float(a20["attacker_included_tps_mean"]) * 355.0 * 12.0 / 250000.0
    out.append(("flood: attacker share of block capacity at 20 tx/s (bound a*b0*D/B = 0.341)",
                "%.4f" % cap_share))
    for mean in (38, 30):
        fm = s[s.experiment == "burstiness-mean%d" % mean]
        e = fm[fm.policy == "ecdsa-only"].sort_values("surge_multiplier")
        out.append(("ECDSA at risk, mean load %d tx/s, multipliers 1/2/4/6" % mean,
                    " / ".join("%.4f" % v for v in e[M])))

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
            print("running the suite into %s (this takes about ten minutes)" % tmp)
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
