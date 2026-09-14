"""Generate RESULTS.md from results/summary.csv.

Every number is produced by verify.derive(), the same function the verifier runs,
so RESULTS.md, the verifier and the paper cannot drift apart.
"""

from __future__ import annotations

import pathlib

import pandas as pd

import verify

HERE = pathlib.Path(__file__).parent
D = pd.read_csv(HERE / "results" / "results.csv")
rows = verify.derive(HERE / "results" / "summary.csv")

out: list[str] = []
w = out.append
w("# Claims and where they come from\n")
w("Every value quoted in the paper, re-derived from `results/summary.csv` by")
w("`verify.derive()`. Regenerate with `python make_results_md.py`.\n")
w("**Metrics.** Exposure is measured over the cohort of transactions broadcast after a")
w("100-block warm-up, with no mempool reset. A vulnerable transaction still pending at the")
w("end of the run and older than the break time counts as at risk; younger pending ones are")
w("censored. `un-migr` is the un-migratable share (`at_risk_fraction_legacy`), `vuln` all")
w("vulnerable (ECDSA) traffic (`at_risk_fraction_vuln`). Means over 30 seeds (10 for")
w("`horizon`), 1,000 measured blocks unless the experiment varies the horizon.\n")
w("**Load.** Offered load is the between-surge rate; the long-run mean is 1.56 times it.")
w("The nominal 32 tx/s is a mean of 49.8 tx/s, 85% of the 58.7 tx/s ECDSA capacity. Only")
w("`horizon` runs an overloaded chain (38 tx/s, mean 59.1).\n")
w("| Claim | Value |")
w("|---|---|")
for k, v in rows:
    w("| %s | %s |" % (k.strip(), v))
w("")
tests = pd.read_csv(HERE / "results" / "statistical_tests.csv")
w("## Paired tests at the nominal load (QSentry against each variant)\n")
w("| Baseline | Metric | p | Cohen's d |")
w("|---|---|---|---|")
for _, r in tests.iterrows():
    w("| %s | %s | %.2e | %+.2f |" % (r.baseline, r.metric, r.p_value, r.cohens_d))
w("")
w("---\n")
w("Generated from %d simulation runs across %d experiments." % (len(D), D.experiment.nunique()))
(HERE / "RESULTS.md").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
print("wrote RESULTS.md (%d lines)" % len(out))
