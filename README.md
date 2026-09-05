# Quantum on-spend exposure in blockchain mempools

Reproducibility artifact for **"Securing Blockchain Transactions against Quantum On-Spend
Attacks: Exposure Bounds and Adaptive Mitigations."**

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
python qsentry_sim.py --out results --seeds 30      # ~10 minutes
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

## What is here

| File | Contents |
|---|---|
| `qsentry_sim.py` | the model: credentials, mempool, block production, exposure accounting, and the closed-form exposure floor |
| `suite.py` | twelve experiments, five figures, paired statistical tests, and the manifest |
| `verify.py` | independent verification of both reproduction and the reported numbers |
| `results/` | committed outputs, including a SHA-256 for every file |
| `RESULTS.md` | every claim in the paper mapped to the exact number in the data |
| `make_results_md.py` | regenerates `RESULTS.md` from the data, so the mapping cannot drift |
| `calibration/` | the demand model checked against an observed Bitcoin mempool series |

## Experiments

`results/results.csv` carries an `experiment` column. The suite runs 4,050 configurations
across 30 independent seeds.

| Experiment | Runs | What it varies |
|---|---|---|
| `congestion` | 720 | offered load, four policies |
| `breaktime` | 600 | adversary break time `T_b` |
| `legacy` | 450 | the share of demand that cannot migrate |
| `provisioning` | 450 | block capacity |
| `chain` | 360 | block interval, isolating the theoretical floor |
| `epsilon` | 300 | the exposure target, at feasible and infeasible loads |
| `burstiness` | 240 | demand surge multiplier at a fixed between-surge rate (mean load rises with it) |
| `burstiness-mean38` | 240 | demand surge multiplier with the long-run mean load held at 38 tx/s |
| `burstiness-mean30` | 240 | demand surge multiplier with the long-run mean load held at 30 tx/s |
| `verify` | 180 | verification budget (sensitivity check) |
| `v-sweep` | 150 | the cost–exposure weight `V` |
| `ablation` | 120 | mechanism ablations |

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
