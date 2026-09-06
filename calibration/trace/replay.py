"""Replay recorded Ethereum mempool arrivals through the simulator.

Takes one hour of first-seen transactions from a mempool-dumpster day, feeds
them to the simulator as the arrival process (each transaction with its own
envelope size), and asks three questions:

1. With byte capacity B fitted so that the ECDSA-only replay reproduces the
   observed mean inclusion delay of that hour, how close is the replayed window
   distribution to the observed one?  (A check of the model, not a result.)
2. On that fitted chain, what does QSentry change?
3. On the same demand hitting a chain provisioned to 80, 90, 95 and 100 percent
   mean utilisation, the congested counterfactuals, what do ECDSA-only and
   QSentry give?

    python replay.py 2026-08-19.csv.zip
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import qsentry_sim as m  # noqa: E402

path = sys.argv[1] if len(sys.argv) > 1 else "2026-08-19.csv.zip"
with zipfile.ZipFile(path) as z:
    with z.open(z.namelist()[0]) as f:
        df = pd.read_csv(f, usecols=["timestamp_ms", "data_size", "included_block_timestamp_ms",
                                     "inclusion_delay_ms"])
t0 = df.timestamp_ms.min()
df["t"] = (df.timestamp_ms - t0) / 1000.0
df["bytes"] = 110 + df.data_size.fillna(0)
df["delay_s"] = (df.inclusion_delay_ms / 1000.0).clip(lower=0)

SEEDS = 10
WARM = 60          # blocks of warm-up, fed from the 12 minutes before the hour
HOUR_BLOCKS = 300  # one hour at 12 s
CFG = dict(duration_blocks=WARM + HOUR_BLOCKS, warmup_blocks=WARM)


def window(hour: int):
    start = hour * 3600.0 - WARM * 12.0
    sub = df[(df.t >= start) & (df.t < hour * 3600.0 + HOUR_BLOCKS * 12.0)]
    tr = np.column_stack([(sub.t.values - start), sub.bytes.values]).astype(float)
    obs = df[(df.t >= hour * 3600.0) & (df.t < hour * 3600.0 + HOUR_BLOCKS * 12.0)].delay_s
    return tr, obs


def run(name, policy, B, seeds=SEEDS, **kw):
    rows = [m.simulate(m.Config(policy=policy, seed=s, block_bytes=B, trace_name=name, **CFG, **kw))[0]
            for s in range(1, seeds + 1)]
    keys = ["at_risk_fraction", "at_risk_fraction_legacy", "inclusion_ratio", "window_mean_s",
            "window_p95_s", "window_legacy_mean_s", "mean_offered_tps", "bytes_per_tx", "share_falcon"]
    return {k: float(np.mean([r[k] for r in rows])) for k in keys}


def fit_capacity(name, obs_mean, seeds=3):
    """Smallest B (bytes/block) whose ECDSA-only replay mean window is within
    the observed mean; bisection on log B."""
    lo, hi = 1e5, 5e7
    for _ in range(22):
        mid = np.sqrt(lo * hi)
        w = run(name, "ecdsa-only", mid, seeds=seeds)["window_mean_s"]
        if w > obs_mean:
            lo = mid
        else:
            hi = mid
    return hi


out = {}
for label, hour in (("busiest hour (10:00 UTC)", 10), ("quiet hour (03:00 UTC)", 3)):
    tr, obs = window(hour)
    name = "eth-%02d" % hour
    m.TRACES[name] = tr
    o = {"tx": int(len(obs)), "tx_per_s": float(len(obs) / 3600.0),
         "observed_mean_s": float(obs.mean()), "observed_median_s": float(obs.median()),
         "observed_p95_s": float(obs.quantile(0.95)),
         "observed_at_risk_60": float((obs > 60).mean()), "observed_at_risk_15": float((obs > 15).mean()),
         "bytes_per_s": float(tr[tr[:, 0] >= WARM * 12.0][:, 1].sum() / 3600.0)}
    B = fit_capacity(name, o["observed_mean_s"])
    o["fitted_block_bytes"] = float(B)
    o["fitted_utilisation"] = float(o["bytes_per_s"] * 12.0 / B)
    # Counterfactuals: the same hour's demand on a chain provisioned to a
    # target mean utilisation (offered bytes per block over block bytes).
    caps = [("fitted", B)] + [("util-%.2f" % u, o["bytes_per_s"] * 12.0 / u) for u in (0.80, 0.90, 0.95, 1.00)]
    for tag, cap in caps:
        for policy in ("ecdsa-only", "qsentry"):
            o["%s_%s" % (tag, policy)] = run(name, policy, cap)
            o["%s_%s" % (tag, policy)]["block_bytes"] = float(cap)
    out[label] = o
    print(label, json.dumps(o, indent=1))
json.dump(out, open("replay_results.json", "w"), indent=1)
print("wrote replay_results.json")
