"""Safety rails for SweepyCL's live policy adjustments.

The existing ``policy_adjustments.json`` flow already exists in
``ai_advisor.race_policy_hint`` / ``live_policy_summary``, and there is a
``safe_for_live_policy`` flag in ``ai_data_health.json`` that disables
adjustments when the parser is broken.  This module adds the missing pieces:

  - A bounded application function so a learned adjustment can never push
    a heuristic score by more than ``MAX_ADJUSTMENT_PCT`` of its magnitude.

  - A per-cell sample-size gate so we don't apply policy to cells with too
    few observations.

  - Drift detection: KL divergence between the cell's recent posterior and
    its long-window posterior.  If the KL exceeds a threshold the meta has
    likely shifted (game patch, new character, new support cards) and the
    learned adjustment should be frozen until enough fresh data accumulates.

All functions are pure.  Tunables live in ``PolicyGuardConfig`` so the
dashboard can expose them and tests can override them.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Tuple

from career_bot.ai_modeling import BetaPosterior


__all__ = [
    "PolicyGuardConfig",
    "GuardDecision",
    "safe_apply",
    "beta_kl_divergence",
    "compute_posterior_drift",
]


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PolicyGuardConfig:
    """Tunables for how aggressively learned policy may shift heuristic scores.

    The defaults are deliberately conservative.  Live-policy users should
    start here and only loosen one knob at a time after watching the AI
    dashboard for at least a week of runs.
    """

    max_adjustment_pct: float = 0.25
    """Hard cap on the learned adjustment as a fraction of the heuristic
    score's magnitude.  ``0.25`` means a learned hint can never push the
    underlying heuristic score by more than +/-25%."""

    min_samples_per_cell: int = 5
    """Minimum starts before policy is applied to a cell at all.  Cells
    below this threshold fall through to the unmodified heuristic."""

    drift_kl_threshold: float = 0.5
    """KL(recent || long-window) above this freezes adjustments for the
    cell.  ``0.5`` corresponds to a substantial distributional shift in the
    posterior — light drift will not trigger it."""

    drift_min_recent_samples: int = 3
    """Avoid spurious drift triggers from tiny recent windows."""

    max_absolute_adjustment: float = 50.0
    """A second ceiling in raw score units, in case the heuristic score is
    very large and ``max_adjustment_pct`` would still produce a wild swing."""


# ---------------------------------------------------------------------------
# Decision record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GuardDecision:
    """Outcome of a single ``safe_apply`` call.

    ``final_score`` is what the caller should use.  ``reason`` tells the
    dashboard which guard fired (or ``"applied"`` if the adjustment passed
    cleanly).
    """

    final_score: float
    reason: str
    requested_adjustment: float
    applied_adjustment: float
    samples: int
    drift_kl: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "final_score": round(self.final_score, 4),
            "reason": self.reason,
            "requested_adjustment": round(self.requested_adjustment, 4),
            "applied_adjustment": round(self.applied_adjustment, 4),
            "samples": int(self.samples),
            "drift_kl": None if self.drift_kl is None else round(self.drift_kl, 4),
        }


# ---------------------------------------------------------------------------
# KL divergence between Beta distributions
# ---------------------------------------------------------------------------


def beta_kl_divergence(p: BetaPosterior, q: BetaPosterior) -> float:
    """KL( Beta(p.alpha, p.beta) || Beta(q.alpha, q.beta) ).

    Uses the closed-form expression in terms of digamma and log-gamma
    functions.  Returns ``0.0`` when distributions are identical and grows
    without bound as they diverge.  Always non-negative.
    """
    from math import lgamma
    try:
        from scipy.special import digamma  # lazy import
    except ImportError:  # pragma: no cover - scipy is in requirements
        # Stand-in: a tiny rational approximation of digamma adequate for
        # alpha,beta >> 1.  Real callers always have scipy available.
        def digamma(x: float) -> float:
            result = 0.0
            while x < 6:
                result -= 1.0 / x
                x += 1.0
            return result + math.log(x) - 1.0 / (2 * x)

    a1, b1 = float(p.alpha), float(p.beta)
    a2, b2 = float(q.alpha), float(q.beta)
    t1, t2 = a1 + b1, a2 + b2

    log_B_p = lgamma(a1) + lgamma(b1) - lgamma(t1)
    log_B_q = lgamma(a2) + lgamma(b2) - lgamma(t2)

    kl = (
        (log_B_q - log_B_p)
        + (a1 - a2) * float(digamma(a1))
        + (b1 - b2) * float(digamma(b1))
        + (a2 - a1 + b2 - b1) * float(digamma(t1))
    )
    # KL is non-negative; clamp tiny negative values from float rounding.
    return max(0.0, float(kl))





# ---------------------------------------------------------------------------
# safe_apply
# ---------------------------------------------------------------------------


def compute_posterior_drift(
    recent: BetaPosterior,
    long_window: BetaPosterior,
    recent_observations: int,
    min_recent_samples: int = 3,
) -> Optional[float]:
    """KL divergence between the recent posterior and the long-window posterior.

    ``recent_observations`` is the number of **real** observations that went
    into the recent posterior (excluding the prior's pseudo-counts).  The
    caller must track this separately since the BetaPosterior fuses prior
    and data into a single (alpha, beta) pair from which the real-data count
    cannot be recovered.

    Returns ``None`` if the recent window has fewer than ``min_recent_samples``
    real observations; that lets ``safe_apply`` skip drift checks instead of
    treating thin windows as ``no drift``.
    """
    if recent_observations < int(min_recent_samples):
        return None
    return beta_kl_divergence(recent, long_window)


def safe_apply(
    heuristic_score: float,
    requested_adjustment: float,
    samples: int,
    config: Optional[PolicyGuardConfig] = None,
    recent_posterior: Optional[BetaPosterior] = None,
    long_posterior: Optional[BetaPosterior] = None,
    recent_observations: Optional[int] = None,
) -> GuardDecision:
    """Apply a learned adjustment to a heuristic score, with all guards.

    The order of checks matters:
      1. ``insufficient_samples``  - cell has fewer than the minimum starts
      2. ``drift_detected``        - posterior has shifted beyond the threshold
      3. ``clamped`` / ``applied`` - in-bounds adjustments pass through

    Either of (1) or (2) returns the unmodified heuristic score and records
    the reason.  ``clamped`` and ``applied`` differ only in whether the
    requested adjustment had to be reduced to fit within the bounds.
    """
    cfg = config or PolicyGuardConfig()

    if samples < cfg.min_samples_per_cell:
        return GuardDecision(
            final_score=heuristic_score,
            reason="insufficient_samples",
            requested_adjustment=requested_adjustment,
            applied_adjustment=0.0,
            samples=samples,
            drift_kl=None,
        )

    drift_kl: Optional[float] = None
    if recent_posterior is not None and long_posterior is not None:
        # Default the real-observation count to ``samples`` when the caller
        # doesn't supply it; that's a sensible interpretation when the same
        # cell's stats are passed in for both.
        obs = samples if recent_observations is None else int(recent_observations)
        drift_kl = compute_posterior_drift(
            recent_posterior,
            long_posterior,
            recent_observations=obs,
            min_recent_samples=cfg.drift_min_recent_samples,
        )
        if drift_kl is not None and drift_kl > cfg.drift_kl_threshold:
            return GuardDecision(
                final_score=heuristic_score,
                reason="drift_detected",
                requested_adjustment=requested_adjustment,
                applied_adjustment=0.0,
                samples=samples,
                drift_kl=drift_kl,
            )

    pct_bound = abs(heuristic_score) * cfg.max_adjustment_pct
    bound = min(pct_bound, cfg.max_absolute_adjustment)
    clamped = max(-bound, min(bound, float(requested_adjustment)))
    reason = "clamped" if clamped != requested_adjustment else "applied"

    return GuardDecision(
        final_score=heuristic_score + clamped,
        reason=reason,
        requested_adjustment=requested_adjustment,
        applied_adjustment=clamped,
        samples=samples,
        drift_kl=drift_kl,
    )
