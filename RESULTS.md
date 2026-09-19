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
| congestion 20 tx/s, un-migr at risk: ECDSA / ECDSA ordered / FN-DSA / ML-DSA / QSentry | 0.0300 / 0.0083 / 1.0000 / 1.0000 / 0.0082 |
| congestion 20 tx/s, inclusion: ECDSA / ECDSA ordered / FN-DSA / ML-DSA / QSentry | 0.999 / 0.999 / 0.443 / 0.160 / 0.999 |
| congestion 24 tx/s, un-migr at risk: ECDSA / ECDSA ordered / FN-DSA / ML-DSA / QSentry | 0.1547 / 0.0450 / 1.0000 / 1.0000 / 0.0417 |
| congestion 24 tx/s, inclusion: ECDSA / ECDSA ordered / FN-DSA / ML-DSA / QSentry | 0.997 / 0.997 / 0.347 / 0.112 / 0.993 |
| congestion 28 tx/s, un-migr at risk: ECDSA / ECDSA ordered / FN-DSA / ML-DSA / QSentry | 0.3211 / 0.0862 / 1.0000 / 1.0000 / 0.0798 |
| congestion 28 tx/s, inclusion: ECDSA / ECDSA ordered / FN-DSA / ML-DSA / QSentry | 0.995 / 0.995 / 0.277 / 0.077 / 0.992 |
| congestion 32 tx/s, un-migr at risk: ECDSA / ECDSA ordered / FN-DSA / ML-DSA / QSentry | 0.5039 / 0.1249 / 1.0000 / 1.0000 / 0.1203 |
| congestion 32 tx/s, inclusion: ECDSA / ECDSA ordered / FN-DSA / ML-DSA / QSentry | 0.991 / 0.991 / 0.239 / 0.063 / 0.990 |
| congestion 36 tx/s, un-migr at risk: ECDSA / ECDSA ordered / FN-DSA / ML-DSA / QSentry | 0.7185 / 0.1546 / 1.0000 / 1.0000 / 0.1532 |
| congestion 36 tx/s, inclusion: ECDSA / ECDSA ordered / FN-DSA / ML-DSA / QSentry | 0.978 / 0.978 / 0.205 / 0.046 / 0.977 |
| ablation block-space optimal: un-migr / vuln / incl / PQ incl / FN share / bytes/tx / pending end | 0.5039 / 0.5038 / 0.991 / nan / 0.0000 / 355 / 5548 |
| ablation ECDSA slack order: un-migr / vuln / incl / PQ incl / FN share / bytes/tx / pending end | 0.1249 / 0.1250 / 0.991 / nan / 0.0000 / 355 / 5548 |
| ablation QSentry: un-migr / vuln / incl / PQ incl / FN share / bytes/tx / pending end | 0.1203 / 0.1228 / 0.990 / 0.931 / 0.0220 / 385 / 6293 |
| ablation QSentry oldest first: un-migr / vuln / incl / PQ incl / FN share / bytes/tx / pending end | 0.4793 / 0.4871 / 0.990 / 0.943 / 0.0214 / 385 / 6164 |
| ablation QSentry no budget: un-migr / vuln / incl / PQ incl / FN share / bytes/tx / pending end | 0.1223 / 0.1314 / 0.967 / 0.631 / 0.0711 / 424 / 20083 |
| ablation QSentry no ordering: un-migr / vuln / incl / PQ incl / FN share / bytes/tx / pending end | 0.7177 / 0.7122 / 0.984 / 0.996 / 0.0216 / 387 / 9277 |
| ablation QSentry fixed weight: un-migr / vuln / incl / PQ incl / FN share / bytes/tx / pending end | 0.1197 / 0.1218 / 0.990 / 0.947 / 0.0190 / 381 / 6006 |
| ablation hybrid only: un-migr / vuln / incl / PQ incl / FN share / bytes/tx / pending end | 1.0000 / 1.0000 / 0.059 / 0.059 / 0.0000 / 2967 / 562203 |
| Theorem 1 floor respected (all vulnerable) | yes, all 24 points |
| chain 2 s: floor / un-migr ECDSA / ECDSA ordered / QSentry | 0.000 / 0.0779 / 0.0091 / 0.0091 |
| chain 6 s: floor / un-migr ECDSA / ECDSA ordered / QSentry | 0.000 / 0.3154 / 0.0636 / 0.0616 |
| chain 12 s: floor / un-migr ECDSA / ECDSA ordered / QSentry | 0.000 / 0.5039 / 0.1249 / 0.1203 |
| chain 60 s: floor / un-migr ECDSA / ECDSA ordered / QSentry | 0.000 / 0.7675 / 0.2636 / 0.2594 |
| chain 150 s: floor / un-migr ECDSA / ECDSA ordered / QSentry | 0.600 / 0.9123 / 0.6001 / 0.6001 |
| chain 600 s: floor / un-migr ECDSA / ECDSA ordered / QSentry | 0.900 / 0.9771 / 0.9000 / 0.9000 |
| break time 15 s: un-migr ECDSA / ECDSA ordered / QSentry | 0.7298 / 0.2352 / 0.2296 |
| break time 30 s: un-migr ECDSA / ECDSA ordered / QSentry | 0.6423 / 0.1826 / 0.1778 |
| break time 60 s: un-migr ECDSA / ECDSA ordered / QSentry | 0.5039 / 0.1249 / 0.1203 |
| break time 120 s: un-migr ECDSA / ECDSA ordered / QSentry | 0.3004 / 0.0621 / 0.0604 |
| break time 240 s: un-migr ECDSA / ECDSA ordered / QSentry | 0.1173 / 0.0201 / 0.0200 |
| break time 540 s: un-migr ECDSA / ECDSA ordered / QSentry | 0.0131 / 0.0025 / 0.0025 |
| phi 0.05/0.15/0.30/0.50/0.80, un-migr at risk, ecdsa-only | 0.5132 / 0.5194 / 0.5039 / 0.5123 / 0.5196 |
| phi 0.05/0.15/0.30/0.50/0.80, un-migr at risk, ecdsa-ordered | 0.1247 / 0.1269 / 0.1249 / 0.1259 / 0.1259 |
| phi 0.05/0.15/0.30/0.50/0.80, un-migr at risk, falcon-only | 1.0000 / 1.0000 / 1.0000 / 1.0000 / 1.0000 |
| phi 0.05/0.15/0.30/0.50/0.80, un-migr at risk, qsentry | 0.1204 / 0.1230 / 0.1203 / 0.1221 / 0.1235 |
| provisioning 150/250/400/600/900 kB, un-migr at risk, ecdsa-only | 0.9983 / 0.5039 / 0.0357 / 0.0000 / 0.0000 |
| provisioning 150/250/400/600/900 kB, un-migr at risk, ecdsa-ordered | 0.2966 / 0.1249 / 0.0092 / 0.0000 / 0.0000 |
| provisioning 150/250/400/600/900 kB, un-migr at risk, falcon-only | 1.0000 / 1.0000 / 1.0000 / 0.9978 / 0.6557 |
| provisioning 150/250/400/600/900 kB, un-migr at risk, qsentry | 0.2966 / 0.1203 / 0.0090 / 0.0000 / 0.0000 |
| verification-cost sensitivity | max spread 0.000000 |
| V in [1, 60]: un-migr at risk min / max | 0.1203 / 0.1207 |
| epsilon 0.01..0.20 at 20 tx/s: un-migr at risk | 0.0081 / 0.0082 / 0.0083 / 0.0083 / 0.0083 |
| epsilon 0.01..0.20 at 32 tx/s: un-migr at risk | 0.1203 / 0.1203 / 0.1209 / 0.1227 / 0.1246 |
| burstiness mean 38 tx/s, ecdsa-only, multipliers 1/2/4/6 | 0.0000 / 0.0000 / 0.1807 / 0.3184 |
| burstiness mean 38 tx/s, ecdsa-ordered, multipliers 1/2/4/6 | 0.0000 / 0.0000 / 0.0518 / 0.1119 |
| burstiness mean 38 tx/s, qsentry, multipliers 1/2/4/6 | 0.0000 / 0.0000 / 0.0475 / 0.1026 |
| burstiness mean 30 tx/s, ecdsa-only, multipliers 1/2/4/6 | 0.0000 / 0.0000 / 0.0220 / 0.1275 |
| burstiness mean 30 tx/s, ecdsa-ordered, multipliers 1/2/4/6 | 0.0000 / 0.0000 / 0.0060 / 0.0432 |
| burstiness mean 30 tx/s, qsentry, multipliers 1/2/4/6 | 0.0000 / 0.0000 / 0.0060 / 0.0372 |
| flood QSentry un-migr at risk, attack 0/5/10/20 | 0.0606 / 0.0743 / 0.0928 / 0.1376 |
| flood ECDSA-only un-migr at risk, attack 0/5/10/20 | 0.2277 / 0.3172 / 0.4302 / 0.8898 |
| flood ECDSA ordered un-migr at risk, attack 0/5/10/20 | 0.0661 / 0.0801 / 0.0965 / 0.1376 |
| flood QSentry PQ inclusion, attack 0/5/10/20 | 0.9444 / 0.9358 / 0.8541 / nan |
| flood attacker share of capacity at 20 tx/s (bound 0.341) | 0.3307 |
| flood reservation 0.7, no attacker: un-migr at risk / PQ incl | 0.1260 / 0.9369 |
| flood reservation 0.5, no attacker: un-migr at risk / PQ incl | 0.1415 / 0.9592 |
| conceal ecdsa-only 26 tx/s commit-reveal=False: un-migr / incl / latency s / pending end | 0.2277 / 0.997 / 40 / 1260 |
| conceal ecdsa-only 26 tx/s commit-reveal=True: un-migr / incl / latency s / pending end | 0.3288 / 0.992 / 100 / 2502 |
| conceal ecdsa-only 32 tx/s commit-reveal=False: un-migr / incl / latency s / pending end | 0.5039 / 0.991 / 102 / 5548 |
| conceal ecdsa-only 32 tx/s commit-reveal=True: un-migr / incl / latency s / pending end | 0.8122 / 0.941 / 462 / 20859 |
| conceal ecdsa-ordered 26 tx/s commit-reveal=False: un-migr / incl / latency s / pending end | 0.0661 / 0.997 / 39 / 1260 |
| conceal ecdsa-ordered 26 tx/s commit-reveal=True: un-migr / incl / latency s / pending end | 0.0000 / 0.993 / 91 / 466 |
| conceal ecdsa-ordered 32 tx/s commit-reveal=False: un-migr / incl / latency s / pending end | 0.1249 / 0.991 / 96 / 5548 |
| conceal ecdsa-ordered 32 tx/s commit-reveal=True: un-migr / incl / latency s / pending end | 0.0000 / 0.949 / 397 / 799 |
| conceal qsentry 26 tx/s commit-reveal=False: un-migr / incl / latency s / pending end | 0.0606 / 0.993 / 79 / 3208 |
| conceal qsentry 26 tx/s commit-reveal=True: un-migr / incl / latency s / pending end | 0.0000 / 0.993 / 91 / 466 |
| conceal qsentry 32 tx/s commit-reveal=False: un-migr / incl / latency s / pending end | 0.1203 / 0.990 / 112 / 6293 |
| conceal qsentry 32 tx/s commit-reveal=True: un-migr / incl / latency s / pending end | 0.0000 / 0.949 / 397 / 799 |
| conceal probes at 26 (Tb=24 | bc=50 | bc=50,Tb=120 | bc=200) | 0.0575 / 0.0073 / 0.0000 / 0.0000 |
| aging 32 tx/s wait inf/300/120/60/24: un-migr at risk | 0.1203 / 0.1599 / 0.1720 / 0.1715 / 0.1638 |
| aging 32 tx/s: PQ inclusion | 0.9312 / 0.9885 / 0.9975 / 0.9990 / 0.9992 |
| aging 26 tx/s wait inf/300/120/60/24: un-migr at risk | 0.0606 / 0.1854 / 0.2105 / 0.1946 / 0.1460 |
| aging 26 tx/s: PQ inclusion | 0.9444 / 0.9837 / 0.9921 / 0.9946 / 0.9969 |
| horizon 32 tx/s ECDSA, vuln at risk @200/1000/5000 blocks | 0.5971 / 0.5152 / 0.5028 |
| horizon 32 tx/s ECDSA, pending at end @200/1000/5000 | 4207 / 5131 / 4692 |
| horizon 32 tx/s ECDSA ordered, vuln at risk @200/1000/5000 blocks | 0.1332 / 0.1258 / 0.1229 |
| horizon 32 tx/s ECDSA ordered, pending at end @200/1000/5000 | 4207 / 5131 / 4692 |
| horizon 32 tx/s QSentry, vuln at risk @200/1000/5000 blocks | 0.1318 / 0.1222 / 0.1195 |
| horizon 32 tx/s QSentry, pending at end @200/1000/5000 | 5306 / 6311 / 6204 |
| horizon 32 tx/s QSentry no budget, vuln at risk @200/1000/5000 blocks | 0.1390 / 0.1325 / 0.1298 |
| horizon 32 tx/s QSentry no budget, pending at end @200/1000/5000 | 7677 / 21027 / 77808 |
| horizon 38 tx/s ECDSA, vuln at risk @200/1000/5000 blocks | 0.8872 / 0.8764 / 0.9088 |
| horizon 38 tx/s ECDSA, pending at end @200/1000/5000 | 20944 / 28167 / 37980 |
| horizon 38 tx/s ECDSA ordered, vuln at risk @200/1000/5000 blocks | 0.2027 / 0.1808 / 0.1708 |
| horizon 38 tx/s ECDSA ordered, pending at end @200/1000/5000 | 19424 / 28167 / 37980 |
| horizon 38 tx/s QSentry, vuln at risk @200/1000/5000 blocks | 0.2024 / 0.1807 / 0.1708 |
| horizon 38 tx/s QSentry, pending at end @200/1000/5000 | 19460 / 28204 / 37980 |
| horizon 38 tx/s QSentry no budget, vuln at risk @200/1000/5000 blocks | 0.2053 / 0.1851 / 0.1756 |
| horizon 38 tx/s QSentry no budget, pending at end @200/1000/5000 | 20553 / 40569 / 128344 |

## Paired tests at the nominal load (QSentry against each variant)

| Baseline | Metric | p | Cohen's d |
|---|---|---|---|
| fee-optimal | at_risk_fraction_legacy | 1.86e-09 | -3.71 |
| fee-optimal | at_risk_fraction_vuln | 1.86e-09 | -3.69 |
| fee-optimal | at_risk_fraction | 1.86e-09 | -3.71 |
| fee-optimal | bytes_per_tx | 1.86e-09 | +2.37 |
| fee-optimal | window_vuln_p95_s | 2.13e-06 | +1.03 |
| fee-optimal | window_vuln_p99_s | 1.86e-09 | +1.63 |
| qsentry-no-vq | at_risk_fraction_legacy | 1.63e-01 | +0.02 |
| qsentry-no-vq | at_risk_fraction_vuln | 1.59e-02 | +0.03 |
| qsentry-no-vq | at_risk_fraction | 9.74e-02 | +0.02 |
| qsentry-no-vq | bytes_per_tx | 5.43e-05 | +0.21 |
| qsentry-no-vq | window_vuln_p95_s | 2.10e-01 | -0.02 |
| qsentry-no-vq | window_vuln_p99_s | 4.42e-01 | -0.02 |
| hybrid-only | at_risk_fraction_legacy | 1.86e-09 | -39.01 |
| hybrid-only | at_risk_fraction_vuln | 1.86e-09 | -39.03 |
| hybrid-only | at_risk_fraction | 1.86e-09 | -25.65 |
| hybrid-only | bytes_per_tx | 1.86e-09 | -176.77 |
| hybrid-only | window_vuln_p95_s | 1.73e-06 | -9.26 |
| hybrid-only | window_vuln_p99_s | 1.73e-06 | -6.37 |
| qsentry-no-budget | at_risk_fraction_legacy | 1.75e-02 | -0.06 |
| qsentry-no-budget | at_risk_fraction_vuln | 1.86e-09 | -0.28 |
| qsentry-no-budget | at_risk_fraction | 1.86e-09 | -0.16 |
| qsentry-no-budget | bytes_per_tx | 1.86e-09 | -1.90 |
| qsentry-no-budget | window_vuln_p95_s | 3.81e-01 | +0.08 |
| qsentry-no-budget | window_vuln_p99_s | 7.12e-03 | +0.13 |
| qsentry-no-ordering | at_risk_fraction_legacy | 1.86e-09 | -9.37 |
| qsentry-no-ordering | at_risk_fraction_vuln | 1.86e-09 | -9.12 |
| qsentry-no-ordering | at_risk_fraction | 1.86e-09 | -8.91 |
| qsentry-no-ordering | bytes_per_tx | 2.64e-02 | -0.10 |
| qsentry-no-ordering | window_vuln_p95_s | 1.28e-02 | +0.53 |
| qsentry-no-ordering | window_vuln_p99_s | 2.55e-07 | +1.22 |
| ecdsa-ordered | at_risk_fraction_legacy | 1.86e-09 | -0.15 |
| ecdsa-ordered | at_risk_fraction_vuln | 2.02e-03 | -0.07 |
| ecdsa-ordered | at_risk_fraction | 3.73e-09 | -0.14 |
| ecdsa-ordered | bytes_per_tx | 1.86e-09 | +2.37 |
| ecdsa-ordered | window_vuln_p95_s | 7.01e-05 | -0.06 |
| ecdsa-ordered | window_vuln_p99_s | 1.63e-03 | -0.09 |
| ecdsa-ordered-newest | at_risk_fraction_legacy | 1.86e-09 | -0.15 |
| ecdsa-ordered-newest | at_risk_fraction_vuln | 2.02e-03 | -0.07 |
| ecdsa-ordered-newest | at_risk_fraction | 3.73e-09 | -0.14 |
| ecdsa-ordered-newest | bytes_per_tx | 1.86e-09 | +2.37 |
| ecdsa-ordered-newest | window_vuln_p95_s | 6.20e-06 | +0.46 |
| ecdsa-ordered-newest | window_vuln_p99_s | 2.60e-05 | -0.53 |
| qsentry-oldest-first | at_risk_fraction_legacy | 1.86e-09 | -3.25 |
| qsentry-oldest-first | at_risk_fraction_vuln | 1.86e-09 | -3.33 |
| qsentry-oldest-first | at_risk_fraction | 1.86e-09 | -3.25 |
| qsentry-oldest-first | bytes_per_tx | 3.14e-01 | +0.03 |
| qsentry-oldest-first | window_vuln_p95_s | 3.73e-09 | +1.04 |
| qsentry-oldest-first | window_vuln_p99_s | 1.86e-09 | +1.64 |

---

Generated from 10590 simulation runs across 18 experiments.
