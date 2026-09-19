# Racing the block: quantum on-spend exposure as a mempool deadline-scheduling problem

Reproducibility artifact for **"Racing the Block: Quantum On-Spend Exposure as a Mempool Deadline-Scheduling Problem."**

A transaction reveals its public key the moment it is broadcast and stops being attackable
once it is recorded in a block. Recent resource estimates place a fast-clock
cryptographically relevant quantum computer within minutes of recovering a secp256k1
private key from that disclosure, which makes the interval between those two events — the
mempool residence time — the quantity that decides whether an on-spend attack succeeds.

That interval is not a property of the cipher. It is a property of the queue, and this
repository studies it as one.

## Reproducing everything

```bash
pip install -r requirements.txt
python qsentry_sim.py --out results --seeds 30      # about an hour
```

One command regenerates every figure and every table in the paper. No output is edited by
hand, and none was.

To check a fresh run against the committed results and re-derive the paper's headline
numbers:

```bash
python verify.py
```

`verify.py` reruns the suite into a temporary directory, compares every output against
`results/manifest.json`, re-derives each quoted figure from `results/summary.csv`, and
exits non-zero on any mismatch. Use `--numbers-only` to skip the rerun.

## Additions of 19 September 2026 (evening, fourth review)

One change touches reported numbers: the flood's Poisson draw now has its own random stream
(`rng_flood`), so honest arrivals are identical at every attack rate and the flood experiment is
paired; every other experiment reproduces the earlier numbers exactly. New in the model: a
capacity-limited adversary (`adversary`, post-processing with 1, 11, 100 or 1000 machines that pick
targets by value with knowledge of the future; `adv_count_k*`, `adv_value*_k*`), a heavy-tailed fee
scale for block value (`block_value_ratio_geo`, tier k pays 2^k), senders who re-bid to the top tier
as the deadline nears (`fee_model="bump"`), the tier hybrid with the forger's top fee when replacement
is kept (`forger_fee`), and adopters who win a block in proportion to its value (`adopt_by_value`).
The "oldest first" adoption variant was dropped: in an all-ECDSA pool it is arrival order.
`statistical_tests.csv` gains the paired effect size `cohens_dz`.

## Corrections of 19 September 2026

An independent review of the artifact found three things that touched reported numbers; all are
fixed and every experiment was re-run. (1) The un-migratable and the other vulnerable transactions
of a slot were queued as two cohorts, the un-migratable one always first, which favoured the headline
metric whenever a block cut a slot. They are now one cohort, and a block that cuts it takes a
hypergeometric share (`split_nl`); the two at-risk metrics now agree. (2) The expired class was served
most recently expired first, because the mempool keeps the order it was last served in; it is now
served oldest first, as the paper states (`Config.expired_order`, with `"newest"` kept for
comparison). The at-risk fraction does not change; the tail does. (3) Block filling stops at the
first entry that does not fit; this is now documented, and `Config.backfill` is there to check it.

New in the model: fee tiers on every transaction with four fee laws (`fee_tiers`, `fee_model`), the
value of each block against what fee order would have built (`block_value_ratio`), a revenue-neutral
hybrid (`ecdsa-feetriage`: fee order between tiers, triage inside a tier), a flood that pays the top
fee (`attack_fee`), a builder that assumes the wrong break time (`builder_break_time_s`), and partial
adoption (`adopt_share`): non-adopting builders order by fee and include the forgery of every
vulnerable spend pending past T_b, which is counted as lost, and each run reports the loss both when
adopters apply a first-seen rule (`lost_fraction_*`) and when they keep replacement
(`lost_fraction_norule_*`). Windows are also reported at the 99th percentile, at their maximum, and
with transactions still pending at the end counted at their age.

## Corrections of 18 September 2026

The defaults carry two corrections found in review. Slack ordering now triages: it serves
first the vulnerable transactions that can still meet their deadline, then those already past
it, then post-quantum traffic (`Config.expired_last`). The first version served the oldest
first, expired ones included, which is optimal only while nothing has expired. And the
un-migratable share can no longer use commit-reveal (`Config.legacy_commit_reveal`), since it
runs no new protocol. A new policy, `ecdsa-ordered`, uses the ordering alone with no migration,
and appears in every sweep where it separates the two levers. Two more, `falcon-ordered` and `mldsa-ordered`,
run blanket migration under the same ordering: they show that the harm blanket migration does to
senders who cannot migrate belongs to arrival order, and that under deadline order the migrants are
the ones not included. `calibration/effective_bandwidth.py` now solves for the decay rate in the log
domain; the first release stopped at a float overflow for surge multipliers up to 1.5. A further baseline, `ecdsa-fee`, serves by
fee in eight tiers, blind to the credential, which is what deployed builders do; and the break-time
sweep now runs out to the nine-minute single-machine estimate of Babbush et al. To reproduce the first submission:

```bash
python qsentry_sim.py --out results_published --seeds 30 --published
```

## What is here

| File | Contents |
|---|---|
| `qsentry_sim.py` | the model: credentials, mempool, block production, exposure accounting, and the closed-form exposure floor |
| `suite.py` | twenty experiments, six figures, paired statistical tests, and the manifest |
| `verify.py` | independent verification of both reproduction and the reported numbers |
| `results/` | committed outputs, including a SHA-256 for every file |
| `RESULTS.md` | every claim in the paper mapped to the exact number in the data |
| `make_results_md.py` | regenerates `RESULTS.md` from the data, so the mapping cannot drift |
| `calibration/` | the demand model checked against an observed Bitcoin mempool series |
| `calibration/trace/` | one day of recorded Ethereum mainnet mempool arrivals: the measured exposure window, the burstiness of real arrivals against the model, and a replay of two hours through the simulator |

## Experiments

`results/results.csv` carries an `experiment` column. The suite runs 11,310 configurations
across 30 independent seeds on 4 worker processes. Every run lasts 1,100 blocks with a 100-block
warm-up and no mempool reset; exposure is measured over the cohort broadcast after warm-up,
counting a vulnerable transaction still pending at the end and older than T_b as at risk.
The nominal load is 32 tx/s between surges (mean 49.8 tx/s, 85% of ECDSA capacity).

| Experiment | Runs | What it varies |
|---|---|---|
| `adoption` | 1350 | partial adoption: share of blocks built by adopters, four adopter orders and the tier hybrid with the forger's top fee, loss with a first-seen rule and with replacement kept |
| `congestion` | 1200 | between-surge load 20-36 tx/s, the whole stable range, arrival order, fee order, triage order, blanket migrations with and without triage, QSentry |
| `breaktime` | 1080 | adversary break time `T_b` |
| `flood` | 840 | an adversarial flood of vulnerable transactions, a per-block reservation against it, and the same flood against fee order paying like everyone or the top fee |
| `legacy` | 750 | the share of demand that cannot migrate |
| `provisioning` | 750 | block capacity |
| `chain` | 720 | block interval, isolating the theoretical floor |
| `feemodel` | 630 | seven fee models (2, 8, 64 independent tiers; surge senders bid high or low; bids follow the queue; senders re-bid to the top tier at half the break time) for fee order, the tier hybrid and triage, with block value |
| `tb-misset` | 510 | a builder that sorts by a wrong break time while exposure is counted against the true one: assumed 15 to 240 s against a true 60 s, and assumed 60 s against a true 120, 240 and 540 s |
| `burstiness-mean38` | 480 | demand surge multiplier with the long-run mean load held at 38 tx/s |
| `burstiness-mean30` | 480 | demand surge multiplier with the long-run mean load held at 30 tx/s |
| `conceal` | 480 | concealment by commit-reveal for migratable senders, alone and composed with triage ordering, plus probes |
| `adoption-value` | 360 | partial adoption when block value decides who builds: the adopter wins a block in proportion to its share times the value of the block its order would build |
| `epsilon` | 300 | the exposure target |
| `aging` | 300 | bounded deferral for post-quantum transactions (tested and rejected) |
| `horizon` | 300 | run length 200/1000/5000 blocks on a stable (32 tx/s) and an overloaded (38 tx/s) chain, 10 seeds |
| `ablation` | 270 | mechanism ablations: no budget, no ordering, fixed weight, oldest-first ordering, ordering alone |
| `verify` | 180 | verification budget (sensitivity check) |
| `adversary` | 180 | a capacity-limited adversary with 1, 11, 100 or 1000 machines that picks targets by value with knowledge of the future, under arrival, fee and triage order, at 24 and 32 tx/s |
| `v-sweep` | 150 | the cost-exposure weight `V` |

## Reference environment

Python 3.14.3, NumPy 2.4.4, pandas 3.0.2, Matplotlib 3.10.8, SciPy 1.17.1, on Windows
x86-64. Exact versions are pinned in `requirements.txt`.

Every entry in `results/manifest.json` is byte-reproducible on these versions, including
the PDFs. That required suppressing the `/CreationDate` Matplotlib writes into each PDF:
without it the figure digests change on every run even when the rendered content is
identical, which makes a manifest useless for exactly the drift check it exists to
support. Figure rendering can still differ across Matplotlib or platform versions, so on a
different environment compare `results.csv` and `summary.csv` first; `verify.py` treats a
PDF digest mismatch as a warning and a CSV mismatch as a failure, for that reason.

## Claim boundary

Please read this before reusing any number.

The adversary is modelled as an **arithmetic condition** on the exposure window, not as an
executed attack. We do not simulate Shor's algorithm and make no claim about any device;
published resource estimates are used only to motivate the scale of the break time.
Success is credited whenever the window exceeds the break time for a quantum-vulnerable
credential, ignoring interception and the work of landing a conflicting transaction, so
**reported at-risk fractions are upper bounds on realised loss**, not predictions of it.

The model is a slotted queueing model, not a client. It omits peer-to-peer propagation
delay, fee-market dynamics, builder competition, reorganisations, mempool eviction and
replacement transactions. Demand is Markov-modulated because real mempool backlogs are
episodic rather than stationary; the surge parameters are swept rather than fitted to any
particular chain. Nothing here is a measurement of Bitcoin, Ethereum or any deployed
system.

## Citation

Citation details will be added once the paper is accepted.

## License

Released under the MIT License. See `LICENSE`.

## Real-chain data

`calibration/trace/` works on one day of Ethereum mainnet mempool transactions from
Flashbots' Mempool Dumpster (https://mempool-dumpster.flashbots.net). The daily file
is not committed (126 MB); download it and check the digest before use:

    https://mempool-dumpster.flashbots.net/ethereum/mainnet/2026-08/2026-08-19.csv.zip
    sha256: 75a446963adf93e542e43aab45c1bce37cbfeae5cea1262f12fea9297818938d

`analyze_trace.py` reports the first-seen-to-inclusion delay distribution (the exposure
window of Definition 1 measured on the real chain), the at-risk fraction it implies at
each break time, and the per-slot burstiness of arrivals against the two-state model
(`trace_stats.json`). `replay.py` feeds one hour of recorded arrivals to the simulator,
fits the byte capacity so that the ECDSA-only replay reproduces the observed mean wait,
and then runs the policies on that chain and on counterfactuals provisioned to 80-100%
mean utilisation (`replay_results.json`). Envelope size is taken as 110 bytes plus
calldata; transactions larger than a block are dropped, as a builder would.
