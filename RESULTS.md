# Claims and where they come from

Every figure quoted in the paper, with the experiment and column that produces it.
Regenerate this file with `python make_results_md.py`; all values are read from
`results/summary.csv`, which is itself produced by `python qsentry_sim.py`.

Unless stated otherwise, the metric is the at-risk fraction of **un-migratable**
transactions (`at_risk_fraction_legacy`), reported as a mean over 30 seeds with a
two-sided 95% Student-t confidence interval.

## The migration paradox

| Offered load (tx/s) | ECDSA only | FN-DSA only | ML-DSA only | QSentry |
|---|---|---|---|---|
| 20 | 0.0337 | 0.9304 | 0.9640 | **0.0296** | 
| 26 | 0.2011 | 0.9538 | 0.9686 | **0.1525** | 
| 32 | 0.3814 | 0.9623 | 0.9703 | **0.2791** | 
| 38 | 0.6346 | 0.9647 | 0.9690 | **0.5105** | 
| 44 | 0.7746 | 0.9656 | 0.9703 | **0.6253** | 
| 50 | 0.8218 | 0.9683 | 0.9738 | **0.7306** | 

At the lowest load tested, ECDSA leaves 0.0337 of vulnerable transactions at risk and
blanket FN-DSA migration leaves 0.9304, a factor of 27.6 worse, while inclusion falls
from 0.998 to 0.479. Migration alone pushes an uncongested chain past its stability
boundary.

## The exposure floor (Theorem 1)

No scheduling policy can drive the at-risk fraction below `max(0, 1 - T_b/D)`.
Every measured point must therefore lie at or above its floor.

| Block interval (s) | Floor | ECDSA only | QSentry | Recovered by control |
|---|---|---|---|---|
| 2 | 0.0000 | 0.1668 | 0.1572 | 0.0095 |
| 6 | 0.0000 | 0.5492 | 0.4741 | 0.0751 |
| 12 | 0.0000 | 0.6857 | 0.5216 | 0.1641 |
| 60 | 0.0000 | 0.8447 | 0.7333 | 0.1114 |
| 150 | 0.6000 | 0.9378 | 0.8780 | 0.0598 |
| 600 | 0.9000 | 0.9837 | 0.9661 | 0.0176 |

Floor violations across all 12 points: **0**.

## Mechanism ablation at 38 tx/s

| Policy | Un-migratable at risk | All at risk | Inclusion | Bytes/tx |
|---|---|---|---|---|
| fee-optimal | 0.6346 | 0.6346 | 0.912 | 355 |
| hybrid-only | 0.9689 | 0.2910 | 0.118 | 2966 |
| qsentry-no-vq | 0.5921 | 0.5847 | 0.895 | 379 |
| qsentry | 0.5105 | 0.5001 | 0.865 | 389 |

- against the exposure-blind controller: **19.6%** relative reduction, for 9.6% more block space
- against the fixed-weight ablation: **13.8%** (this is what the virtual queue contributes)
- against hybrid migration: **47.3%**, while including **7.32x** as many transactions

Paired two-sided Wilcoxon signed-rank tests on matched seeds:

| Baseline | Metric | p | Cohen's d |
|---|---|---|---|
| fee-optimal | at_risk_fraction_legacy | 1.30e-08 | -0.58 |
| fee-optimal | at_risk_fraction | 1.86e-09 | -0.62 |
| fee-optimal | bytes_per_tx | 2.56e-06 | +2.40 |
| qsentry-no-vq | at_risk_fraction_legacy | 5.97e-06 | -0.38 |
| qsentry-no-vq | at_risk_fraction | 3.24e-06 | -0.39 |
| qsentry-no-vq | bytes_per_tx | 3.13e-04 | +0.51 |
| hybrid-only | at_risk_fraction_legacy | 1.86e-09 | -3.22 |
| hybrid-only | at_risk_fraction | 1.22e-05 | +1.47 |
| hybrid-only | bytes_per_tx | 1.86e-09 | -144.66 |

## Provisioning

| Block capacity (B) | ECDSA only | FN-DSA only | QSentry |
|---|---|---|---|
| 150000 | 0.8981 | 0.9700 | 0.8791 |
| 250000 | 0.6346 | 0.9647 | 0.5105 |
| 400000 | 0.1399 | 0.9509 | 0.1168 |
| 600000 | 0.0000 | 0.8917 | 0.0000 |
| 900000 | 0.0000 | 0.7193 | 0.0000 |

ECDSA and QSentry both reach exactly zero at 600 kB, roughly 2.4x nominal capacity.
Blanket FN-DSA migration is still at 0.7193 with 900 kB, 3.6x nominal: it cannot be
provisioned out of the problem on any comparable scale.

## Sensitivity checks

**Burstiness.** With stationary demand (multiplier 1) the at-risk fraction is exactly
0.0000 for every policy: all measured exposure is produced by congestion episodes.
Section "Calibrating the Demand Model" in the paper compares the modelled burstiness
against an observed mempool; see `calibration/`.

**Burstiness at fixed mean load.** The `burstiness` sweep holds the between-surge rate
fixed, so mean load rises with the multiplier. `burstiness-mean38` and `burstiness-mean30`
scale the between-surge rate so the long-run mean stays at 38 and 30 tx/s (65% and 51%
of ECDSA capacity); only the shape of demand changes.

| Surge multiplier | ECDSA, mean 38 | QSentry, mean 38 | ECDSA, mean 30 | QSentry, mean 30 |
|---|---|---|---|---|
| 1 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 2 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 4 | 0.1673 | 0.1338 | 0.0128 | 0.0140 |
| 6 | 0.2956 | 0.2513 | 0.1499 | 0.1315 |

**Verification cost.** Varying the verification budget fourfold changes the at-risk
fraction by at most 0.000000, confirming that block space rather than verification is the
binding resource. This is checked, not assumed.

**Control parameter.** Across V in [1, 60] the at-risk fraction moves only from 0.5094
to 0.5160, so the result does not depend on tuning V.

## The flood attack on the ordering lever

An attacker broadcasts ECDSA transactions to occupy the vulnerable class that slack
ordering serves first (`flood`, 26 tx/s between surges so the honest chain is inside
capacity). Honest metrics exclude the attacker's transactions; the builder cannot.

| Attack (tx/s) | ECDSA-only, honest un-migr. at risk | QSentry, honest un-migr. at risk | QSentry, PQ inclusion | attacker share of block capacity |
|---|---|---|---|---|
| 0 | 0.2011 | 0.1525 | 0.5797 | 0.0000 |
| 5 | 0.2483 | 0.1830 | 0.5418 | 0.0846 |
| 10 | 0.2769 | 0.1880 | 0.3934 | 0.1690 |
| 20 | 0.5146 | 0.3229 | 0.1867 | 0.3337 |

The attacker's share of block capacity never exceeds what its own offered bytes would
fill (a*b0*Delta/B = 0.341 at 20 tx/s): ordering gives the flood precedence, not
amplification. What it displaces is post-quantum traffic.

A per-block reservation for post-quantum traffic (`vulnerable_cap`) was tested and
rejected: with no attacker it raises honest exposure from 0.1525 (no cap) to 0.2899 (cap 0.7)
and 0.4243 (cap 0.5), because the virtual queue answers the extra exposure by migrating
more traffic, which deepens the post-quantum backlog the reservation was meant to protect.

## Concealment by commit-reveal, alone and with ordering

`conceal`: the transaction is disclosed only when its reveal is broadcast, after its
commit (100 bytes) is included. The window is measured from the reveal.

| Load (tx/s) | Policy | Commit-reveal | un-migr. at risk | inclusion | latency (s) |
|---|---|---|---|---|---|
| 26 | ecdsa-only | no | 0.2011 | 0.993 | 36.4 |
| 26 | ecdsa-only | yes | 0.3106 | 0.961 | 109.6 |
| 26 | qsentry | no | 0.1525 | 0.953 | 63.1 |
| 26 | qsentry | yes | 0.0000 | 0.964 | 101.5 |
| 38 | ecdsa-only | no | 0.6346 | 0.912 | 148.8 |
| 38 | ecdsa-only | yes | 0.7592 | 0.732 | 354.1 |
| 38 | qsentry | no | 0.5105 | 0.865 | 125.9 |
| 38 | qsentry | yes | 0.0000 | 0.759 | 320.7 |

Concealment alone raises exposure (the commit costs block space and the reveal still
queues). Concealment with slack ordering drives it to zero: reveals go first, and the
commit's cost throttles disclosure, so W < Delta (1 + ceil(b0/bc)). Probes of the bound:

| break time (s) | commit bytes | bound (s) | un-migr. at risk |
|---|---|---|---|
| 60 | 50 | 108 | 0.0620 |
| 120 | 50 | 108 | 0.0000 |
| 24 | 100 | 60 | 0.1309 |
| 60 | 100 | 60 | 0.0000 |
| 60 | 200 | 36 | 0.0000 |

## Bounded deferral (tested and rejected)

`aging` promotes a post-quantum transaction into the front class once it has waited
`pq_max_wait` seconds. It buys post-quantum inclusion with honest exposure and with
overall inclusion, because each promoted post-quantum transaction displaces about five
vulnerable ones and the virtual queue then migrates more.

| Load (tx/s) | Wait (s) | honest un-migr. at risk | inclusion, all | PQ inclusion | bytes/tx |
|---|---|---|---|---|---|
| 38 | inf | 0.5105 | 0.865 | 0.203 | 389 |
| 38 | 300 | 0.7163 | 0.696 | 0.558 | 488 |
| 38 | 120 | 0.7596 | 0.683 | 0.559 | 497 |
| 38 | 60 | 0.7701 | 0.678 | 0.565 | 501 |
| 38 | 24 | 0.7722 | 0.678 | 0.566 | 501 |
| 26 | inf | 0.1525 | 0.953 | 0.580 | 449 |
| 26 | 300 | 0.3510 | 0.841 | 0.630 | 526 |
| 26 | 120 | 0.4365 | 0.807 | 0.626 | 550 |
| 26 | 60 | 0.4682 | 0.800 | 0.617 | 556 |
| 26 | 24 | 0.4709 | 0.799 | 0.617 | 557 |

## What these results do not show

- QSentry never drives exposure to zero and cannot; at 38 tx/s it still leaves
  0.5105 of un-migratable transactions at risk.
- Its absolute advantage over doing nothing ranges from 0.0041 to 0.1493 across the load
  sweep, and is not monotone in load.
- It costs inclusion: 0.865 against 0.912 for the exposure-blind controller.
- Raising block capacity is a more effective mitigation than the controller, and the
  only one of the two that terminates.

---

Generated from 5190 simulation runs across 15 experiments.
