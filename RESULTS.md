# Claims and where they come from

Every value quoted in the paper, re-derived from `results/summary.csv` by
`verify.derive()`. Regenerate with `python make_results_md.py`.

**Metrics.** Exposure is measured over the cohort of transactions broadcast after a
100-block warm-up, with no mempool reset. A vulnerable transaction still pending at the
end of the run and older than the break time counts as at risk; younger pending ones are
censored. `un-migr` is the un-migratable share (`at_risk_fraction_legacy`), `vuln` all
vulnerable (ECDSA) traffic (`at_risk_fraction_vuln`). Means over 30 seeds (10 for
`horizon`), 1,000 measured blocks unless the experiment varies the horizon.

**Load.** Offered load is the between-surge rate; the long-run mean is 1.56 times it.
The nominal 32 tx/s is a mean of 49.8 tx/s, 85% of the 58.7 tx/s ECDSA capacity. Only
`horizon` runs an overloaded chain (38 tx/s, mean 59.1).

| Claim | Value |
|---|---|
| congestion 20 tx/s, un-migr at risk: ECDSA / FN-DSA / ML-DSA / QSentry | 0.0291 / 1.0000 / 1.0000 / 0.0234 |
| congestion 20 tx/s, inclusion: ECDSA / FN-DSA / ML-DSA / QSentry | 0.999 / 0.443 / 0.160 / 0.996 |
| congestion 24 tx/s, un-migr at risk: ECDSA / FN-DSA / ML-DSA / QSentry | 0.1526 / 1.0000 / 1.0000 / 0.1307 |
| congestion 24 tx/s, inclusion: ECDSA / FN-DSA / ML-DSA / QSentry | 0.997 / 0.347 / 0.112 / 0.991 |
| congestion 28 tx/s, un-migr at risk: ECDSA / FN-DSA / ML-DSA / QSentry | 0.3184 / 1.0000 / 1.0000 / 0.2917 |
| congestion 28 tx/s, inclusion: ECDSA / FN-DSA / ML-DSA / QSentry | 0.995 / 0.277 / 0.077 / 0.993 |
| congestion 32 tx/s, un-migr at risk: ECDSA / FN-DSA / ML-DSA / QSentry | 0.5011 / 1.0000 / 1.0000 / 0.4767 |
| congestion 32 tx/s, inclusion: ECDSA / FN-DSA / ML-DSA / QSentry | 0.991 / 0.239 / 0.063 / 0.990 |
| congestion 36 tx/s, un-migr at risk: ECDSA / FN-DSA / ML-DSA / QSentry | 0.7166 / 1.0000 / 1.0000 / 0.7050 |
| congestion 36 tx/s, inclusion: ECDSA / FN-DSA / ML-DSA / QSentry | 0.978 / 0.205 / 0.046 / 0.977 |
| ablation block-space optimal: un-migr / vuln / incl / PQ incl / FN share / bytes/tx / pending end | 0.5011 / 0.5038 / 0.991 / nan / 0.0000 / 355 / 5548 |
| ablation QSentry: un-migr / vuln / incl / PQ incl / FN share / bytes/tx / pending end | 0.4767 / 0.4871 / 0.990 / 0.943 / 0.0214 / 385 / 6164 |
| ablation QSentry no budget: un-migr / vuln / incl / PQ incl / FN share / bytes/tx / pending end | 0.3629 / 0.3730 / 0.918 / 0.427 / 0.1342 / 445 / 49450 |
| ablation QSentry no ordering: un-migr / vuln / incl / PQ incl / FN share / bytes/tx / pending end | 0.7158 / 0.7120 / 0.984 / 0.996 / 0.0216 / 387 / 9325 |
| ablation QSentry fixed weight: un-migr / vuln / incl / PQ incl / FN share / bytes/tx / pending end | 0.4784 / 0.4888 / 0.990 / 0.947 / 0.0190 / 381 / 6006 |
| ablation hybrid only: un-migr / vuln / incl / PQ incl / FN share / bytes/tx / pending end | 1.0000 / 1.0000 / 0.059 / 0.059 / 0.0000 / 2966 / 562239 |
| Theorem 1 floor respected (all vulnerable) | yes, all 12 points |
| chain 2 s: floor / ECDSA vuln / QSentry vuln | 0.000 / 0.0780 / 0.0686 |
| chain 6 s: floor / ECDSA vuln / QSentry vuln | 0.000 / 0.3151 / 0.2944 |
| chain 12 s: floor / ECDSA vuln / QSentry vuln | 0.000 / 0.5038 / 0.4871 |
| chain 60 s: floor / ECDSA vuln / QSentry vuln | 0.000 / 0.7675 / 0.7662 |
| chain 150 s: floor / ECDSA vuln / QSentry vuln | 0.600 / 0.9123 / 0.9175 |
| chain 600 s: floor / ECDSA vuln / QSentry vuln | 0.900 / 0.9771 / 0.9787 |
| break time 15 s: un-migr ECDSA / QSentry | 0.7254 / 0.7067 |
| break time 30 s: un-migr ECDSA / QSentry | 0.6387 / 0.6211 |
| break time 60 s: un-migr ECDSA / QSentry | 0.5011 / 0.4767 |
| break time 120 s: un-migr ECDSA / QSentry | 0.2987 / 0.2752 |
| break time 240 s: un-migr ECDSA / QSentry | 0.1167 / 0.1078 |
| phi 0.05/0.15/0.30/0.50/0.80, un-migr at risk, ecdsa-only | 0.5096 / 0.5163 / 0.5011 / 0.5105 / 0.5188 |
| phi 0.05/0.15/0.30/0.50/0.80, un-migr at risk, falcon-only | 1.0000 / 1.0000 / 1.0000 / 1.0000 / 1.0000 |
| phi 0.05/0.15/0.30/0.50/0.80, un-migr at risk, qsentry | 0.4844 / 0.4934 / 0.4767 / 0.4895 / 0.5033 |
| provisioning 150/250/400/600/900 kB, un-migr at risk, ecdsa-only | 0.9983 / 0.5011 / 0.0347 / 0.0000 / 0.0000 |
| provisioning 150/250/400/600/900 kB, un-migr at risk, falcon-only | 1.0000 / 1.0000 / 1.0000 / 0.9977 / 0.6528 |
| provisioning 150/250/400/600/900 kB, un-migr at risk, qsentry | 0.9983 / 0.4767 / 0.0267 / 0.0000 / 0.0000 |
| verification-cost sensitivity | max spread 0.000000 |
| V in [1, 60]: un-migr at risk min / max | 0.4759 / 0.4767 |
| epsilon 0.01..0.20 at 20 tx/s: un-migr at risk | 0.0232 / 0.0234 / 0.0249 / 0.0259 / 0.0268 |
| epsilon 0.01..0.20 at 32 tx/s: un-migr at risk | 0.4764 / 0.4767 / 0.4770 / 0.4762 / 0.4773 |
| burstiness mean 38 tx/s, ecdsa-only, multipliers 1/2/4/6 | 0.0000 / 0.0000 / 0.1782 / 0.3152 |
| burstiness mean 38 tx/s, qsentry, multipliers 1/2/4/6 | 0.0000 / 0.0000 / 0.1504 / 0.2806 |
| burstiness mean 30 tx/s, ecdsa-only, multipliers 1/2/4/6 | 0.0000 / 0.0000 / 0.0213 / 0.1251 |
| burstiness mean 30 tx/s, qsentry, multipliers 1/2/4/6 | 0.0000 / 0.0000 / 0.0182 / 0.0979 |
| flood QSentry un-migr at risk, attack 0/5/10/20 | 0.1919 / 0.2838 / 0.4057 / 0.8885 |
| flood ECDSA-only un-migr at risk, attack 0/5/10/20 | 0.2253 / 0.3146 / 0.4279 / 0.8892 |
| flood QSentry PQ inclusion, attack 0/5/10/20 | 0.9368 / 0.9503 / 0.8681 / 0.5330 |
| flood attacker share of capacity at 20 tx/s (bound 0.341) | 0.3229 |
| flood reservation 0.7, no attacker: un-migr at risk / PQ incl | 0.4944 / 0.9408 |
| flood reservation 0.5, no attacker: un-migr at risk / PQ incl | 0.6922 / 0.9625 |
| conceal ecdsa-only 26 tx/s commit-reveal=False: un-migr / incl / latency s / pending end | 0.2253 / 0.997 / 40 / 1260 |
| conceal ecdsa-only 26 tx/s commit-reveal=True: un-migr / incl / latency s / pending end | 0.4290 / 0.983 / 165 / 4968 |
| conceal ecdsa-only 32 tx/s commit-reveal=False: un-migr / incl / latency s / pending end | 0.5011 / 0.991 / 102 / 5548 |
| conceal ecdsa-only 32 tx/s commit-reveal=True: un-migr / incl / latency s / pending end | 0.9038 / 0.884 / 808 / 34663 |
| conceal qsentry 26 tx/s commit-reveal=False: un-migr / incl / latency s / pending end | 0.1919 / 0.992 / 87 / 3756 |
| conceal qsentry 26 tx/s commit-reveal=True: un-migr / incl / latency s / pending end | 0.0000 / 0.985 / 151 / 750 |
| conceal qsentry 32 tx/s commit-reveal=False: un-migr / incl / latency s / pending end | 0.4767 / 0.990 / 115 / 6164 |
| conceal qsentry 32 tx/s commit-reveal=True: un-migr / incl / latency s / pending end | 0.0000 / 0.897 / 723 / 787 |
| conceal probes at 26 (Tb=24 | bc=50 | bc=50,Tb=120 | bc=200) | 0.1192 / 0.0400 / 0.0000 / 0.0000 |
| aging 32 tx/s wait inf/300/120/60/24: un-migr at risk | 0.4767 / 0.6249 / 0.6849 / 0.7101 / 0.7158 |
| aging 32 tx/s: PQ inclusion | 0.9433 / 0.9860 / 0.9959 / 0.9963 / 0.9962 |
| aging 26 tx/s wait inf/300/120/60/24: un-migr at risk | 0.1919 / 0.5704 / 0.6788 / 0.7302 / 0.7372 |
| aging 26 tx/s: PQ inclusion | 0.9368 / 0.9709 / 0.9758 / 0.9782 / 0.9788 |
| horizon 32 tx/s ECDSA, vuln at risk @200/1000/5000 blocks | 0.5971 / 0.5152 / 0.5028 |
| horizon 32 tx/s ECDSA, pending at end @200/1000/5000 | 4207 / 5131 / 4692 |
| horizon 32 tx/s QSentry, vuln at risk @200/1000/5000 blocks | 0.5760 / 0.4945 / 0.4877 |
| horizon 32 tx/s QSentry, pending at end @200/1000/5000 | 5211 / 6213 / 6204 |
| horizon 32 tx/s QSentry no budget, vuln at risk @200/1000/5000 blocks | 0.4281 / 0.3838 / 0.3681 |
| horizon 32 tx/s QSentry no budget, pending at end @200/1000/5000 | 15440 / 52344 / 221248 |
| horizon 38 tx/s ECDSA, vuln at risk @200/1000/5000 blocks | 0.8872 / 0.8764 / 0.9088 |
| horizon 38 tx/s ECDSA, pending at end @200/1000/5000 | 20944 / 28167 / 37980 |
| horizon 38 tx/s QSentry, vuln at risk @200/1000/5000 blocks | 0.8832 / 0.8736 / 0.9083 |
| horizon 38 tx/s QSentry, pending at end @200/1000/5000 | 20982 / 28204 / 37980 |
| horizon 38 tx/s QSentry no budget, vuln at risk @200/1000/5000 blocks | 0.6920 / 0.6032 / 0.5761 |
| horizon 38 tx/s QSentry no budget, pending at end @200/1000/5000 | 29639 / 83126 / 356537 |

## Paired tests at the nominal load (QSentry against each variant)

| Baseline | Metric | p | Cohen's d |
|---|---|---|---|
| fee-optimal | at_risk_fraction_legacy | 1.86e-09 | -0.16 |
| fee-optimal | at_risk_fraction_vuln | 3.54e-08 | -0.11 |
| fee-optimal | at_risk_fraction | 1.86e-09 | -0.17 |
| fee-optimal | bytes_per_tx | 1.86e-09 | +2.40 |
| qsentry-no-vq | at_risk_fraction_legacy | 5.32e-01 | -0.01 |
| qsentry-no-vq | at_risk_fraction_vuln | 8.38e-01 | -0.01 |
| qsentry-no-vq | at_risk_fraction | 2.69e-01 | -0.02 |
| qsentry-no-vq | bytes_per_tx | 9.84e-06 | +0.18 |
| hybrid-only | at_risk_fraction_legacy | 1.86e-09 | -4.84 |
| hybrid-only | at_risk_fraction_vuln | 1.86e-09 | -4.79 |
| hybrid-only | at_risk_fraction | 1.86e-09 | -3.66 |
| hybrid-only | bytes_per_tx | 1.86e-09 | -180.45 |
| qsentry-no-budget | at_risk_fraction_legacy | 1.86e-09 | +0.90 |
| qsentry-no-budget | at_risk_fraction_vuln | 1.86e-09 | +0.91 |
| qsentry-no-budget | at_risk_fraction | 1.86e-09 | +1.03 |
| qsentry-no-budget | bytes_per_tx | 1.86e-09 | -3.54 |
| qsentry-no-ordering | at_risk_fraction_legacy | 1.86e-09 | -1.93 |
| qsentry-no-ordering | at_risk_fraction_vuln | 1.86e-09 | -1.83 |
| qsentry-no-ordering | at_risk_fraction | 1.86e-09 | -1.77 |
| qsentry-no-ordering | bytes_per_tx | 6.08e-05 | -0.13 |

---

Generated from 5070 simulation runs across 15 experiments.
