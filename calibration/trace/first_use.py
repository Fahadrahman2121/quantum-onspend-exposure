"""On-spend exposure restricted to first key use, on one Ethereum day.

An account-based chain discloses an account's public key with its first
signed transaction (nonce 0).  Every later transaction from that account
reveals nothing new: the key is already public, and exposed at rest.  The
on-spend window of Definition 1 therefore applies to nonce-0 transactions
only.  This script reports the window statistics for all traffic and for the
first-use subset, and the first-use exposure as a share of all traffic.

    python first_use.py 2026-08-19.csv.zip
"""
from __future__ import annotations

import json
import sys
import zipfile

import numpy as np
import pandas as pd

path = sys.argv[1] if len(sys.argv) > 1 else "2026-08-19.csv.zip"
with zipfile.ZipFile(path) as z:
    with z.open(z.namelist()[0]) as f:
        df = pd.read_csv(f, usecols=["nonce", "inclusion_delay_ms", "tx_type"])
df = df.dropna(subset=["inclusion_delay_ms"])
df["w"] = (df.inclusion_delay_ms / 1000.0).clip(lower=0)


def describe(w: pd.Series) -> dict:
    return {"n": int(len(w)),
            "median_s": float(w.median()), "mean_s": float(w.mean()),
            "p95_s": float(w.quantile(0.95)), "p99_s": float(w.quantile(0.99)),
            "over_15s": float((w > 15).mean()), "over_24s": float((w > 24).mean()),
            "over_60s": float((w > 60).mean())}


first = df[df.nonce == 0]
out = {
    "all": describe(df.w),
    "first_use_nonce0": describe(first.w),
    "first_use_share": float(len(first) / len(df)),
    # On-spend exposure of the chain: first-use transactions that waited past
    # T_b, as a share of ALL transactions (the figure comparable to "all").
    "on_spend_over_60s_share_of_all": float((first.w > 60).sum() / len(df)),
    "on_spend_over_15s_share_of_all": float((first.w > 15).sum() / len(df)),
    "first_use_tx_types": {str(k): int(v) for k, v in first.tx_type.value_counts().items()},
}
json.dump(out, open("first_use_stats.json", "w"), indent=1)
print(json.dumps(out, indent=1))
