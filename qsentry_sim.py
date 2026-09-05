"""Reproducible discrete-event evaluation of quantum on-spend exposure in
blockchain mempools.

A transaction reveals its public key the moment it is broadcast and stops being
attackable once it is recorded in a block.  The interval between those two
events -- the mempool residence time -- is therefore the window inside which a
fast-clock cryptographically relevant quantum computer would have to recover
the key.  That window is not a property of the cipher.  It is a property of the
queue, and this artifact studies it as one.

Everything here is a simulation result.  It is not a measurement of Bitcoin,
Ethereum or any deployed chain, and no number should be read as one.  We do not
simulate Shor's algorithm; the adversary is modelled as an arithmetic condition
on the window, using published resource estimates only to motivate its scale.
All pseudo-randomness is seeded and the suite is deterministic.
"""

from __future__ import annotations

import argparse
import math
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd


# Credential classes.  Sizes are the standardised signature and public-key
# lengths in bytes; "ecdsa" is secp256k1 with a compressed public key.  A hybrid
# credential carries both an ECDSA and an ML-DSA signature, so a quantum forger
# must break both, at the cost of both sizes.
#
# verify_rel is verification work relative to ECDSA.  Block space, not
# verification, is the binding resource in this model, and the suite sweeps the
# verification budget to demonstrate that the conclusions do not depend on it.
CREDENTIALS = {
    "ecdsa": {"sig": 72, "pk": 33, "verify_rel": 1.00, "vulnerable": True},
    "falcon": {"sig": 666, "pk": 897, "verify_rel": 0.55, "vulnerable": False},
    "mldsa": {"sig": 2420, "pk": 1312, "verify_rel": 0.70, "vulnerable": False},
    "hybrid": {"sig": 72 + 2420, "pk": 33 + 1312, "verify_rel": 1.70, "vulnerable": False},
}
CRED_NAMES = tuple(CREDENTIALS)

POLICIES = (
    "ecdsa-only",       # status quo
    "falcon-only",      # blanket migration to the compact lattice credential
    "mldsa-only",       # blanket migration to the standard lattice credential
    "hybrid-only",      # blanket migration preserving backward compatibility
    "fee-optimal",      # block-space optimal, blind to exposure
    "qsentry",          # proposed
    "qsentry-no-vq",    # ablation: fixed penalty weight instead of a virtual queue
)


@dataclass(frozen=True)
class Config:
    arrival_rate: float = 40.0          # transactions/s offered
    payload_bytes: int = 250
    legacy_fraction: float = 0.30       # share that cannot leave ECDSA
    block_interval_s: float = 12.0
    block_bytes: float = 250_000.0
    slots_per_block: int = 10
    duration_blocks: int = 260
    warmup_blocks: int = 60
    policy: str = "qsentry"
    seed: int = 1
    control_v: float = 8.0
    break_time_s: float = 60.0          # fast-clock CRQC key-recovery time
    exposure_target: float = 0.02       # epsilon
    verify_budget_per_block: float = 40_000.0   # ECDSA-equivalent verifications
    # Mempool backlogs are episodic rather than stationary: demand arrives in
    # surges (fee spikes, mints, liquidation cascades) and drains between them.
    # A two-state Markov-modulated Poisson process reproduces that shape with
    # three interpretable parameters.
    surge_multiplier: float = 4.0
    surge_enter: float = 0.05           # per-block probability of entering a surge
    surge_leave: float = 0.22           # per-block probability of leaving one
    deadline_order: bool = True         # order by slack rather than by fee
    fixed_penalty: float = 400.0        # weight used by the no-virtual-queue ablation
    # Adversarial flood on the ordering lever: an attacker broadcasts ECDSA
    # transactions at this rate (tx/s) purely to occupy the vulnerable class,
    # which slack ordering serves first.  They are excluded from every honest
    # metric but the builder cannot tell them apart, so they do enter the
    # virtual queue.  0 disables the attacker and leaves the RNG stream intact.
    attack_rate: float = 0.0
    # Reservation against that flood: while post-quantum transactions are
    # waiting, the vulnerable class may take at most this fraction of a block.
    # 1.0 is no reservation.  Work-conserving: leftover space is not wasted.
    vulnerable_cap: float = 1.0


def tx_bytes(name: str, payload: int) -> float:
    c = CREDENTIALS[name]
    return float(payload + c["sig"] + c["pk"])


def exposure_floor(break_time_s: float, block_interval_s: float) -> float:
    """Fraction of vulnerable traffic that no mempool policy can protect.

    A transaction broadcast uniformly within a block period waits a residual
    block time before the next block can possibly include it, so its window is
    at least that residual.  With Poisson arrivals the residual is uniform on
    [0, block_interval), giving the closed form below.  See Theorem 1.
    """
    if block_interval_s <= 0.0:
        return 0.0
    return max(0.0, 1.0 - break_time_s / block_interval_s)


def _feasible(policy: str, is_legacy: bool) -> tuple[str, ...]:
    """A legacy transaction is authorised by a key that cannot be rotated --
    a dormant or un-upgraded account -- so its credential is ECDSA whatever the
    protective layer would prefer.  This is what makes the problem non-trivial:
    the operator cannot migrate its way out of exposure."""
    if is_legacy:
        return ("ecdsa",)
    return {
        "ecdsa-only": ("ecdsa",),
        "falcon-only": ("falcon",),
        "mldsa-only": ("mldsa",),
        "hybrid-only": ("hybrid",),
        "fee-optimal": CRED_NAMES,
        "qsentry": CRED_NAMES,
        "qsentry-no-vq": CRED_NAMES,
    }[policy]


def simulate(config: Config, keep_trace: bool = False):
    if config.policy not in POLICIES:
        raise ValueError(f"unknown policy: {config.policy}")
    rng = np.random.default_rng(config.seed)

    slot_s = config.block_interval_s / config.slots_per_block
    total_slots = config.duration_blocks * config.slots_per_block
    warmup_slots = config.warmup_blocks * config.slots_per_block

    size = {c: tx_bytes(c, config.payload_bytes) for c in CRED_NAMES}
    # Pending transactions, each a [arrival_time, credential index] cohort of 1
    # aggregated into (time, count, credential) groups to keep the suite fast.
    mempool: deque[list] = deque()
    pending_bytes = 0.0
    # Tracked incrementally rather than summed each slot: under an
    # infeasible target the mempool is unbounded and an O(n) scan per slot
    # would make the suite quadratic in a regime the model expects to visit.
    pending_tx = 0

    edges = np.linspace(0.0, 3600.0, 1801)
    hist = np.zeros(len(edges) - 1, dtype=np.int64)
    hist_legacy = np.zeros(len(edges) - 1, dtype=np.int64)

    virtual = 0.0
    in_surge = False
    generated = generated_legacy = 0
    included = included_legacy = 0
    generated_pq = included_pq = 0
    attacker_generated = attacker_included = 0
    attacker_bytes = 0.0
    at_risk = at_risk_legacy = 0
    window_sum = window_sum_legacy = 0.0
    total_bytes = total_verify = 0.0
    cred_counts = np.zeros(len(CRED_NAMES), dtype=np.int64)
    backlog_area = 0.0
    trace = []

    for slot in range(total_slots):
        now = slot * slot_s
        measuring = slot >= warmup_slots
        if slot == warmup_slots:
            # Start measurement from an empty mempool so that inclusion ratios
            # and windows describe the measured interval rather than carry-over.
            mempool.clear()
            pending_bytes = 0.0
            pending_tx = 0

        # ---------------- arrivals and credential assignment ----------------
        if slot % config.slots_per_block == 0:
            if in_surge:
                in_surge = rng.random() >= config.surge_leave
            else:
                in_surge = rng.random() < config.surge_enter
        rate = config.arrival_rate * (config.surge_multiplier if in_surge else 1.0)
        n = int(rng.poisson(rate * slot_s))
        if n > 0:
            n_legacy = int(rng.binomial(n, config.legacy_fraction))
            if measuring:
                generated += n
                generated_legacy += n_legacy
            queue_seconds = pending_bytes / (config.block_bytes / config.block_interval_s)
            for is_legacy, count in ((True, n_legacy), (False, n - n_legacy)):
                if count <= 0:
                    continue
                best = None
                for cred in _feasible(config.policy, is_legacy):
                    b = size[cred]
                    vulnerable = CREDENTIALS[cred]["vulnerable"]
                    # Predicted window: residual block time plus the drain time
                    # of everything already queued plus this cohort's own bytes.
                    drain = queue_seconds + count * b / (config.block_bytes / config.block_interval_s)
                    predicted = 0.5 * config.block_interval_s + drain
                    risk = 1.0 if (vulnerable and predicted > config.break_time_s) else 0.0
                    cost = count * b / 1000.0
                    if config.policy == "fee-optimal":
                        score = config.control_v * cost + queue_seconds * cost
                    elif config.policy == "qsentry":
                        score = (config.control_v * cost + queue_seconds * cost
                                 + virtual * count * (risk - config.exposure_target))
                    elif config.policy == "qsentry-no-vq":
                        score = (config.control_v * cost + queue_seconds * cost
                                 + config.fixed_penalty * count * risk)
                    else:
                        score = cost
                    if best is None or score < best[0]:
                        best = (score, cred)
                cred = best[1]
                mempool.append([now, count, CRED_NAMES.index(cred), size[cred], 0])
                pending_bytes += count * size[cred]
                pending_tx += count
                if measuring:
                    cred_counts[CRED_NAMES.index(cred)] += count
                    if not CREDENTIALS[cred]["vulnerable"]:
                        generated_pq += count

        # ---------------- adversarial flood ----------------
        if config.attack_rate > 0.0:
            na = int(rng.poisson(config.attack_rate * slot_s))
            if na > 0:
                mempool.append([now, na, CRED_NAMES.index("ecdsa"), size["ecdsa"], 1])
                pending_bytes += na * size["ecdsa"]
                pending_tx += na
                if measuring:
                    attacker_generated += na

        # ---------------- block production ----------------
        if (slot + 1) % config.slots_per_block == 0:
            if config.deadline_order and config.policy in ("qsentry", "qsentry-no-vq") \
                    and len(mempool) > 1:
                # Vulnerable transactions carry a deadline at the break time;
                # post-quantum ones do not, so they yield.  This reordering
                # costs no block space at all.
                # Both classes are already in arrival order, so partitioning
                # reproduces slack order exactly without a comparison sort.
                # Under an infeasible target the mempool grows without bound
                # (Remark 3) and an O(n log n) sort per block would make the
                # artifact degrade where the model itself does not.
                vulnerable, other = deque(), deque()
                for entry in mempool:
                    if CREDENTIALS[CRED_NAMES[entry[2]]]["vulnerable"]:
                        vulnerable.append(entry)
                    else:
                        other.append(entry)
                if config.vulnerable_cap < 1.0 and other:
                    # Reservation: the vulnerable class goes first only up to
                    # vulnerable_cap of the block; post-quantum transactions
                    # then get the remainder; any vulnerable leftover follows
                    # so that no block space is wasted.
                    cap_bytes = config.vulnerable_cap * config.block_bytes
                    head: deque[list] = deque()
                    used = 0.0
                    while vulnerable:
                        e = vulnerable[0]
                        room = int((cap_bytes - used) // e[3]) if e[3] > 0 else int(e[1])
                        if room <= 0:
                            break
                        if room >= int(e[1]):
                            head.append(vulnerable.popleft())
                            used += e[1] * e[3]
                        else:
                            head.append([e[0], room, e[2], e[3], e[4]])
                            e[1] -= room
                            used += room * e[3]
                            break
                    head.extend(other)
                    head.extend(vulnerable)
                    ordered = head
                else:
                    vulnerable.extend(other)
                    ordered = vulnerable
            else:
                ordered = mempool
            budget = config.block_bytes
            vbudget = config.verify_budget_per_block
            block_risky = block_total = 0
            remaining: deque[list] = deque()
            while ordered:
                arrival, count, cred_i, per, atk = ordered.popleft()
                rel = CREDENTIALS[CRED_NAMES[cred_i]]["verify_rel"]
                take = min(int(count),
                           int(budget // per) if per > 0 else int(count),
                           int(vbudget // rel) if rel > 0 else int(count))
                if take <= 0:
                    remaining.append([arrival, count, cred_i, per, atk])
                    remaining.extend(ordered)
                    break
                budget -= take * per
                vbudget -= take * rel
                pending_bytes -= take * per
                pending_tx -= take
                window = (now + slot_s) - arrival
                name = CRED_NAMES[cred_i]
                risky = CREDENTIALS[name]["vulnerable"] and window > config.break_time_s
                block_total += take
                block_risky += take if risky else 0
                if atk:
                    # The builder cannot tell a flood from honest traffic, so it
                    # counts towards the virtual queue above; it is kept out of
                    # every honest metric below.
                    if measuring:
                        attacker_included += take
                        attacker_bytes += take * per
                    if take < int(count):
                        remaining.append([arrival, count - take, cred_i, per, atk])
                        remaining.extend(ordered)
                        break
                    continue
                if measuring:
                    included += take
                    window_sum += window * take
                    idx = min(max(int(np.searchsorted(edges, window, side="right") - 1), 0),
                              len(hist) - 1)
                    hist[idx] += take
                    total_bytes += take * per
                    total_verify += take * rel
                    if risky:
                        at_risk += take
                    if name == "ecdsa":
                        included_legacy += take
                        window_sum_legacy += window * take
                        hist_legacy[idx] += take
                        if risky:
                            at_risk_legacy += take
                    else:
                        included_pq += take
                if take < int(count):
                    remaining.append([arrival, count - take, cred_i, per, atk])
                    remaining.extend(ordered)
                    break
            else:
                pass
            mempool = remaining
            excess = (block_risky - config.exposure_target * block_total) if block_total else 0.0
            virtual = max(0.0, virtual + excess / max(config.arrival_rate, 1.0))

        if measuring:
            backlog_area += pending_tx * slot_s
        if keep_trace and slot % config.slots_per_block == 0:
            rate = config.block_bytes / config.block_interval_s
            drain = pending_bytes / rate
            # Under slack ordering the vulnerable class is served ahead of the
            # rest, so the window that decides exposure is set by the vulnerable
            # backlog alone.  Total drain is the wrong quantity for a policy that
            # defers post-quantum traffic deliberately.
            vuln_bytes = sum(e[1] * e[3] for e in mempool
                             if CREDENTIALS[CRED_NAMES[e[2]]]["vulnerable"])
            vuln_drain = vuln_bytes / rate
            trace.append({"time_s": now,
                          "pending_tx": pending_tx,
                          "drain_s": drain,
                          "vulnerable_drain_s": vuln_drain,
                          "predicted_window_s": 0.5 * config.block_interval_s + drain,
                          "vulnerable_window_s": 0.5 * config.block_interval_s + vuln_drain,
                          "virtual": virtual})

    measured_s = (config.duration_blocks - config.warmup_blocks) * config.block_interval_s
    total_cred = max(cred_counts.sum(), 1)

    def pct(h, q):
        tot = h.sum()
        if tot <= 0:
            return float("nan")
        i = int(np.searchsorted(np.cumsum(h), q * tot, side="left"))
        i = min(i, len(edges) - 2)
        return float((edges[i] + edges[i + 1]) / 2.0)

    result = {
        **asdict(config),
        "throughput_tps": included / measured_s,
        "inclusion_ratio": included / max(generated, 1),
        "at_risk_fraction": at_risk / max(included, 1),
        "at_risk_fraction_legacy": at_risk_legacy / max(included_legacy, 1),
        "exposure_floor": exposure_floor(config.break_time_s, config.block_interval_s),
        "window_mean_s": window_sum / max(included, 1),
        "window_p95_s": pct(hist, 0.95),
        "window_legacy_mean_s": window_sum_legacy / max(included_legacy, 1),
        "window_legacy_p95_s": pct(hist_legacy, 0.95),
        "mean_pending_tx": backlog_area / measured_s,
        "bytes_per_tx": total_bytes / max(included, 1),
        "verify_per_tx": total_verify / max(included, 1),
        "generated": generated,
        "mean_offered_tps": generated / measured_s,
        # Honest post-quantum traffic and the adversarial flood (item 3).
        "inclusion_ratio_pq": included_pq / max(generated_pq, 1) if generated_pq else float("nan"),
        "attacker_included_tps": attacker_included / measured_s,
        "attacker_block_share": attacker_bytes / max(total_bytes + attacker_bytes, 1.0),
    }
    for i, name in enumerate(CRED_NAMES):
        result[f"share_{name}"] = float(cred_counts[i]) / total_cred
    return result, pd.DataFrame(trace)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("results"))
    parser.add_argument("--seeds", type=int, default=30)
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()
    import suite

    data = suite.run(args.out, args.seeds, args.quick)
    print(f"wrote {len(data)} simulation runs to {args.out}")


if __name__ == "__main__":
    main()
