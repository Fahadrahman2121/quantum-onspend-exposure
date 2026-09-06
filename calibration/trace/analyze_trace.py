"""What the Ethereum mainnet mempool looked like on one day.

Reads a mempool-dumpster daily CSV (https://mempool-dumpster.flashbots.net) and
reports the quantities the paper's model assumes: the distribution of the
first-seen-to-inclusion delay (the exposure window of Definition 1, measured on
the real chain), the at-risk fraction it implies at each break time, and the
burstiness of arrivals per 12-second slot against the two-state model.

    python analyze_trace.py 2026-08-19.csv.zip
"""
from __future__ import annotations

import json
import sys
import zipfile

import numpy as np
import pandas as pd

path = sys.argv[1] if len(sys.argv) > 1 else "2026-08-19.csv.zip"
with zipfile.ZipFile(path) as z:
    name = z.namelist()[0]
    with z.open(name) as f:
        df = pd.read_csv(f, usecols=["timestamp_ms", "data_size", "gas", "tx_type",
                                     "included_at_block_height", "included_block_timestamp_ms",
                                     "inclusion_delay_ms"])
print("rows", len(df))
df["t"] = (df.timestamp_ms - df.timestamp_ms.min()) / 1000.0
inc = df[df.included_at_block_height.notna()].copy()
inc["delay_s"] = inc.inclusion_delay_ms / 1000.0
print("included", len(inc), "not included", len(df) - len(inc))
print("delay: negative", int((inc.delay_s < 0).sum()), "min %.1f" % inc.delay_s.min())
d = inc.delay_s.clip(lower=0)
out = {"date": name.replace(".csv", ""), "transactions": int(len(df)), "included": int(len(inc)),
       "delay_mean_s": float(d.mean()), "delay_median_s": float(d.median()),
       "delay_p95_s": float(d.quantile(0.95)), "delay_p99_s": float(d.quantile(0.99)),
       "delay_max_s": float(d.max())}
for tb in (15, 24, 60, 120, 240, 600):
    out["at_risk_Tb_%d" % tb] = float((d > tb).mean())
print(json.dumps(out, indent=1))

# Arrivals per 12-second slot over the day: the quantity the two-state model generates.
slot = 12.0
counts = np.bincount((df.t // slot).astype(int))
counts = counts[: int(86400 // slot)]
med = np.median(counts)
burst = {"slots": int(len(counts)), "mean_per_slot": float(counts.mean()), "tx_per_s": float(counts.mean() / slot),
         "cov": float(counts.std() / counts.mean()), "p95_over_median": float(np.quantile(counts, 0.95) / med),
         "max_over_median": float(counts.max() / med), "frac_slots_above_2x_median": float((counts > 2 * med).mean())}
# Hourly profile, so a replay window can be chosen deliberately.
hours = np.bincount((df.t // 3600).astype(int))[:24]
burst["tx_per_s_by_hour"] = [round(float(h / 3600.0), 2) for h in hours]
# Bytes: an Ethereum transaction is roughly 110 bytes of envelope plus calldata.
df["bytes"] = 110 + df.data_size.fillna(0)
burst["bytes_per_tx_mean"] = float(df.bytes.mean()); burst["bytes_per_tx_median"] = float(df.bytes.median())
burst["bytes_per_tx_p95"] = float(df.bytes.quantile(0.95))
print(json.dumps(burst, indent=1))

# The same burstiness statistics for the paper's two-state model, per slot,
# at the observed mean rate, so the comparison is like for like.
rng = np.random.default_rng(1)
lam = counts.mean() / slot
n = len(counts); state = 0; sim = np.zeros(n, dtype=int)
for i in range(n):
    if state == 0 and rng.random() < 0.05: state = 1
    elif state == 1 and rng.random() < 0.22: state = 0
    sim[i] = rng.poisson(lam * (4.0 if state else 1.0) * slot)
smed = np.median(sim)
model = {"cov": float(sim.std() / sim.mean()), "p95_over_median": float(np.quantile(sim, 0.95) / smed),
         "max_over_median": float(sim.max() / smed), "frac_slots_above_2x_median": float((sim > 2 * smed).mean())}
print("model (surge x4, 18.5% occupancy, same mean rate):", json.dumps(model))
json.dump({"observed": out, "burstiness_observed": burst, "burstiness_model": model},
          open("trace_stats.json", "w"), indent=1)
# Delay histogram for the paper's figure / table.
edges = [0, 6, 12, 24, 36, 48, 60, 120, 240, 600, 3600, 1e9]
h, _ = np.histogram(d, bins=edges)
print("delay histogram (s):", list(zip([f"{edges[i]}-{edges[i+1]}" for i in range(len(edges)-1)], (h / len(d)).round(4).tolist())))
