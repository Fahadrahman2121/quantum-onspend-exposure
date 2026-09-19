"""Refresh README.md's run counts and experiment table from results/results.csv, and
state the corrected defaults.  Run after the suite; it only rewrites the README."""
import pathlib, re
import pandas as pd

HERE = pathlib.Path(__file__).parent
r = pd.read_csv(HERE / "results" / "results.csv", usecols=["experiment"])
counts = r.experiment.value_counts()
readme = HERE / "README.md"
t = readme.read_text(encoding="utf-8")

WHAT = {
    "congestion": "between-surge load 20-36 tx/s, the whole stable range, arrival order, fee order, triage order, blanket migrations with and without triage, QSentry",
    "breaktime": "adversary break time `T_b`",
    "legacy": "the share of demand that cannot migrate",
    "provisioning": "block capacity",
    "chain": "block interval, isolating the theoretical floor",
    "epsilon": "the exposure target",
    "burstiness-mean38": "demand surge multiplier with the long-run mean load held at 38 tx/s",
    "burstiness-mean30": "demand surge multiplier with the long-run mean load held at 30 tx/s",
    "ablation": "mechanism ablations: no budget, no ordering, fixed weight, oldest-first ordering, ordering alone",
    "v-sweep": "the cost-exposure weight `V`",
    "verify": "verification budget (sensitivity check)",
    "flood": "an adversarial flood of vulnerable transactions, a per-block reservation against it, and the same flood against fee order paying like everyone or the top fee",
    "aging": "bounded deferral for post-quantum transactions (tested and rejected)",
    "conceal": "concealment by commit-reveal for migratable senders, alone and composed with triage ordering, plus probes",
    "adoption": "partial adoption: share of blocks built by adopters, four adopter orders and the tier hybrid with the forger's top fee, loss with a first-seen rule and with replacement kept",
    "adoption-value": "partial adoption when block value decides who builds: the adopter wins a block in proportion to its share times the value of the block its order would build",
    "adversary": "a capacity-limited adversary with 1, 11, 100 or 1000 machines that picks targets by value with knowledge of the future, under arrival, fee and triage order, at 24 and 32 tx/s",
    "feemodel": "seven fee models (2, 8, 64 independent tiers; surge senders bid high or low; bids follow the queue; senders re-bid to the top tier at half the break time) for fee order, the tier hybrid and triage, with block value",
    "tb-misset": "a builder that sorts by a wrong break time while exposure is counted against the true one: assumed 15 to 240 s against a true 60 s, and assumed 60 s against a true 120, 240 and 540 s",
    "horizon": "run length 200/1000/5000 blocks on a stable (32 tx/s) and an overloaded (38 tx/s) chain, 10 seeds",
}
rows = "\n".join("| `%s` | %d | %s |" % (e, counts[e], WHAT[e]) for e in counts.sort_values(ascending=False).index)
i = t.index("| Experiment | Runs | What it varies |")
j = t.index("\n\n", i)
t = t[:i] + "| Experiment | Runs | What it varies |\n|---|---|---|\n" + rows + t[j:]
t = t.replace("# Quantum exposure of blockchain transactions in transit", "# Racing the block: quantum on-spend exposure as a mempool deadline-scheduling problem")
t = t.replace('**"Quantum Exposure of Blockchain Transactions in Transit:\nFundamental Bounds and Adaptive Mempool Control."**',
              '**"Racing the Block: Quantum On-Spend Exposure as a Mempool Deadline-Scheduling Problem."**')
t = re.sub(r"\| `suite.py` \| \w+(-\w+)? experiments,", "| `suite.py` | %s experiments," % {18: "eighteen", 19: "nineteen", 20: "twenty"}[counts.size], t)
t = re.sub(r"The suite runs [\d,]+ configurations", "The suite runs {:,} configurations".format(len(r)), t)
t = t.replace("python qsentry_sim.py --out results --seeds 30      # ~10 minutes",
              "python qsentry_sim.py --out results --seeds 30      # about an hour")
t = t.replace("| `suite.py` | fifteen experiments, five figures,", "| `suite.py` | %s experiments, five figures," %
              {15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen", 19: "nineteen", 20: "twenty"}[counts.size])
NOTE = """## Corrections of 18 September 2026

The defaults carry two corrections found in review. Slack ordering now triages: it serves
first the vulnerable transactions that can still meet their deadline, then those already past
it, then post-quantum traffic (`Config.expired_last`). The first version served the oldest
first, expired ones included, which is optimal only while nothing has expired. And the
un-migratable share can no longer use commit-reveal (`Config.legacy_commit_reveal`), since it
runs no new protocol. A new policy, `ecdsa-ordered`, uses the ordering alone with no migration,
and appears in every sweep where it separates the two levers. To reproduce the first submission:

```bash
python qsentry_sim.py --out results_published --seeds 30 --published
```

"""
if "## Corrections of 18 September 2026" not in t:
    t = t.replace("## What is here", NOTE + "## What is here")
readme.write_text(t, encoding="utf-8", newline="\n")
print("README updated:", len(r), "runs,", counts.size, "experiments")
