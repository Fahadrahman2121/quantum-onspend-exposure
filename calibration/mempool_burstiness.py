"""Calibration check: how bursty is a real mempool?

The paper models demand as a two-state Markov-modulated process. This script
retrieves a public Bitcoin mempool-size series and computes the statistics the
paper quotes, so the claim that our surge parameters are conservative can be
checked rather than taken on trust.

    python mempool_burstiness.py                 # fetch and compute
    python mempool_burstiness.py --compare       # also diff against committed values

Note: on machines behind a TLS-intercepting proxy the fetch may fail certificate
validation. The same series can be retrieved by opening the URL below in a
browser and saving the JSON, then passing it with --from-file.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import statistics
import urllib.request

URL = ("https://api.blockchain.info/charts/mempool-size"
       "?timespan=180days&format=json")
HERE = pathlib.Path(__file__).parent


def load(from_file: str | None):
    if from_file:
        return json.loads(pathlib.Path(from_file).read_text(encoding="utf-8"))
    with urllib.request.urlopen(URL, timeout=60) as r:
        return json.load(r)


def stats(doc) -> dict:
    pts = [(p["x"], p["y"]) for p in doc["values"] if p["y"] > 0]
    xs = [p[0] for p in pts]
    y = [p[1] for p in pts]
    n = len(y)
    s = sorted(y)

    def q(p):
        return s[min(n - 1, int(p * n))]

    mean = statistics.fmean(y)
    sd = statistics.stdev(y)
    med = q(0.50)

    # A "surge" is a sample above twice the median, matching the two-state
    # model in the paper.
    above = [v > 2 * med for v in y]
    runs, cur = [], 0
    for a in above:
        if a:
            cur += 1
        elif cur:
            runs.append(cur)
            cur = 0
    if cur:
        runs.append(cur)

    sample_s = (xs[-1] - xs[0]) / (n - 1)
    return {
        "source": URL,
        "samples": n,
        "span_days": round((xs[-1] - xs[0]) / 86400, 1),
        "sample_interval_min": round(sample_s / 60),
        "mean_MB": round(mean / 1e6, 2),
        "median_MB": round(med / 1e6, 2),
        "sd_MB": round(sd / 1e6, 2),
        "coefficient_of_variation": round(sd / mean, 3),
        "p95_over_median": round(q(0.95) / med, 2),
        "max_over_median": round(s[-1] / med, 1),
        "fraction_above_2x_median": round(sum(above) / n, 3),
        "mean_surge_length_hours": round(
            (statistics.fmean(runs) if runs else 0) * sample_s / 3600, 1),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-file")
    ap.add_argument("--compare", action="store_true")
    args = ap.parse_args()

    got = stats(load(args.from_file))
    for k, v in got.items():
        print("  %-28s %s" % (k, v))

    if args.compare:
        ref = json.loads((HERE / "mempool_stats.json").read_text(encoding="utf-8"))
        print("\n  committed values were retrieved %s" % ref["retrieved"])
        drift = {k: (ref["statistics"][k], got[k])
                 for k in got
                 if k in ref["statistics"] and ref["statistics"][k] != got[k]}
        if drift:
            print("  the series has moved since; this is expected for live data:")
            for k, (a, b) in drift.items():
                print("    %-26s %s -> %s" % (k, a, b))
        else:
            print("  identical to the committed values")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
