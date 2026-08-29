"""Exact decay rate for the mempool backlog under Markov-modulated arrivals.

The naive Lundberg equation assumes i.i.d. arrivals and predicts a negligible
tail here, which is correct for a Poisson stream and wrong for this model: the
demand process is modulated, and it is the modulation that produces exposure.

For a Markov-modulated source served at a constant B bytes per block, the
stationary backlog satisfies P(M > m) ~ C exp(-theta m) where theta solves

    sp( diag(phi_i(theta)) P ) = exp(theta B),

with P the transition matrix of the modulating chain and

    phi_i(theta) = E[exp(theta A_i)] = exp(lambda_i * Delta * (M_b(theta) - 1))

the moment generating function of the compound-Poisson arrivals in state i.
sp(.) is the Perron root. This is the standard effective-bandwidth
characterisation; the credential mix enters through M_b, so theta depends on
migration, and the modulating chain enters through P, so theta depends on
burstiness. Both dependencies are visible in the output below.
"""
from __future__ import annotations

import math
import sys

import numpy as np
from scipy.optimize import brentq

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
import qsentry_sim as m  # noqa: E402

C = m.Config()
DELTA, B, PHI = C.block_interval_s, C.block_bytes, C.legacy_fraction
b0 = m.tx_bytes("ecdsa", C.payload_bytes)


def mgf_b(theta: float, x: float, b1: float) -> float:
    """E[exp(theta b)] for the two-point credential mix."""
    p = (1.0 - PHI) * x
    return (1 - p) * math.exp(theta * b0) + p * math.exp(theta * b1)


def perron(theta: float, lam: float, x: float, b1: float,
           kappa: float, p01: float, p10: float) -> float:
    mb = mgf_b(theta, x, b1) - 1.0
    phi0 = math.exp(lam * DELTA * mb)
    phi1 = math.exp(kappa * lam * DELTA * mb)
    P = np.array([[1 - p01, p01], [p10, 1 - p10]])
    A = np.diag([phi0, phi1]) @ P
    return float(max(abs(np.linalg.eigvals(A))))


def decay_rate(lam: float, x: float, b1: float,
               kappa: float | None = None,
               p01: float | None = None, p10: float | None = None) -> float | None:
    kappa = C.surge_multiplier if kappa is None else kappa
    p01 = C.surge_enter if p01 is None else p01
    p10 = C.surge_leave if p10 is None else p10

    # mean rate must be inside capacity or no positive root exists
    frac_surge = p01 / (p01 + p10)
    mean_lam = lam * (1 + frac_surge * (kappa - 1))
    mean_b = (1 - (1 - PHI) * x) * b0 + (1 - PHI) * x * b1
    if mean_lam * DELTA * mean_b >= B:
        return None

    def f(t):
        try:
            return math.log(perron(t, lam, x, b1, kappa, p01, p10)) - t * B
        except (OverflowError, ValueError):
            return float("inf")

    lo, hi = 1e-12, 1e-9
    while f(hi) < 0:
        hi *= 1.6
        if hi > 1e-2:
            return None
    try:
        return brentq(f, lo, hi, xtol=1e-20, rtol=1e-14)
    except ValueError:
        return None


def at_risk(theta: float | None, tb: float) -> float:
    """P(R + Q > T_b), R uniform on [0, Delta), Q with rate theta*B/Delta."""
    if theta is None:
        return 1.0
    rate = theta * B / DELTA
    if tb >= DELTA:
        return (math.exp(-rate * (tb - DELTA)) - math.exp(-rate * tb)) / (rate * DELTA)
    return (1 - tb / DELTA) + (1 - math.exp(-rate * tb)) / (rate * DELTA)


b_fal = m.tx_bytes("falcon", C.payload_bytes)
b_mld = m.tx_bytes("mldsa", C.payload_bytes)

print("== burstiness drives the decay rate (lambda=38, x=0, ECDSA only) ==")
print("  %-10s %-14s %-14s" % ("kappa", "theta", "predicted P(W>Tb)"))
for k in (1.0, 2.0, 4.0, 6.0):
    t = decay_rate(38.0, 0.0, b_fal, kappa=k)
    print("  %-10.1f %-14s %-14.4f" % (k, "%.4e" % t if t else "unstable", at_risk(t, C.break_time_s)))

print("\n== migration lowers the decay rate (lambda=38, kappa=4) ==")
print("  %-8s %-16s %-16s" % ("x", "theta (FN-DSA)", "theta (ML-DSA)"))
for x in (0.0, 0.05, 0.10, 0.15, 0.20, 0.40, 1.0):
    t1 = decay_rate(38.0, x, b_fal)
    t2 = decay_rate(38.0, x, b_mld)
    print("  %-8.2f %-16s %-16s" % (
        x, "%.4e" % t1 if t1 else "unstable", "%.4e" % t2 if t2 else "unstable"))

print("\n== analytic prediction vs simulation, ECDSA only ==")
print("  %-8s %-14s %-14s" % ("lambda", "predicted", "simulated"))
for lam in (20.0, 26.0, 32.0, 38.0, 44.0, 50.0):
    t = decay_rate(lam, 0.0, b_fal)
    pred = at_risk(t, C.break_time_s)
    vals = [m.simulate(m.Config(policy="ecdsa-only", arrival_rate=lam, seed=s))[0]["at_risk_fraction"]
            for s in range(1, 11)]
    print("  %-8.0f %-14.4f %-14.4f" % (lam, pred, sum(vals) / len(vals)))
