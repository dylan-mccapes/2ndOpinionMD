"""
bayes.py — closed-form conjugate kernels + likelihood-spec executor for PTV UCs.

This is the deterministic Python layer described in
``reports/STRATEGY_BAYESIAN_PTV_UC_20260423.md`` §3 and §11. The closed-form
update is intentionally cheap (no MCMC, no tensors) so the 8B probe can call
it for every patient on every refresh; the larger qwen-14b reviewer only
escalates when a regime-change signal fires (band widening, evidence outside
prior support, contradiction).

Three conjugate families, three returned UCs (per ``server/eoh/uc.py``):

* ``beta_bernoulli``   — for probabilities in [0, 1]
                         (default: ``flare_30d``, ``progression_3mo``, ``taper_safety``).
* ``gamma_poisson``    — for event-rate hypotheses (events per unit time).
* ``normal_normal``    — for continuous-valued posterior means with known noise.

The ``LikelihoodSpec`` declarative DSL lets the agent express *which* event
features count as positive / negative / skip without writing Python — it walks
``GraphHandle.events`` and accumulates weighted (α, β) increments for the
Beta–Bernoulli case (or count / sum statistics for the other families).

No LLM I/O happens here. Every output is a function of inputs, so two runs on
the same evidence return identical posteriors.
"""
from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from server.eoh.uc import UncertaintyCarrier, canonical_spec_hash, confidence_from_band

from .graph import GraphHandle


__all__ = [
    "BetaPrior",
    "GammaPrior",
    "NormalNormalPrior",
    "LikelihoodSpec",
    "BetaUpdate",
    "GammaUpdate",
    "NormalNormalUpdate",
    "update_beta_bernoulli",
    "update_gamma_poisson",
    "update_normal_normal",
    "apply_likelihood_spec",
    "bayesian_update_uc",
    "DEFAULT_HYPOTHESIS_PRIORS",
    "default_likelihood_spec_for",
]


# --------------------------------------------------------------------------- #
# Prior dataclasses
# --------------------------------------------------------------------------- #

@dataclass
class BetaPrior:
    """Beta(α, β) prior on a probability."""
    alpha: float = 2.0
    beta: float = 8.0
    source: str = "weak"      # "weak" | "mkg" | "clinician"
    notes: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return {"family": "beta", "alpha": self.alpha, "beta": self.beta,
                "source": self.source, "notes": self.notes}


@dataclass
class GammaPrior:
    """Gamma(shape=α, rate=β) prior on a rate."""
    alpha: float = 1.0
    beta: float = 1.0
    source: str = "weak"
    notes: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return {"family": "gamma", "alpha": self.alpha, "beta": self.beta,
                "source": self.source, "notes": self.notes}


@dataclass
class NormalNormalPrior:
    """Normal(mu, sigma^2) prior on a mean, observation noise sigma_obs."""
    mu: float = 0.0
    sigma: float = 1.0
    sigma_obs: float = 1.0
    source: str = "weak"
    notes: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return {"family": "normal", "mu": self.mu, "sigma": self.sigma,
                "sigma_obs": self.sigma_obs, "source": self.source, "notes": self.notes}


# --------------------------------------------------------------------------- #
# Likelihood spec (declarative)
# --------------------------------------------------------------------------- #

# Each rule is one of:
#
#   {
#     "name": "<rule label>",
#     "match": {                          # AND-combined predicates
#         "event_type": "lab" | "pro" | "medication" | ...,
#         "code_index_bucket": "drugs" | "icd" | "labs" | "loinc" | "rxnorm",
#         "key_contains": ["crp", "esr"], # case-insensitive substring on code-index key
#                                          # *or* on event preview / card title / annotation labels
#         "preview_contains": ["worsening", "increased pain"],
#         "instrument_keys": ["haq2", "vas_pain"],
#         "value_above": 10.0,             # numeric thresholds applied to annotations.value or
#         "value_below": 1.0,              #   raw_score / lab numeric (best-effort extraction)
#         "value_delta_above": 0.5,        # delta vs first-seen value of the same instrument
#         "status_flag_in": ["worsening", "flare_signal"],
#     },
#     "outcome": "positive" | "negative" | "skip",
#     "weight": 1.0
#   }
#
# `weight_by` may be one of: null, "salience", "uniform".

@dataclass
class LikelihoodSpec:
    family: str = "beta_bernoulli"   # "beta_bernoulli" | "gamma_poisson" | "normal_normal"
    rules: List[Dict[str, Any]] = field(default_factory=list)
    weight_by: Optional[str] = "salience"
    description: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------- #
# Update results
# --------------------------------------------------------------------------- #

@dataclass
class BetaUpdate:
    alpha_post: float
    beta_post: float
    mean: float
    band_90: Tuple[float, float]


@dataclass
class GammaUpdate:
    alpha_post: float
    beta_post: float
    mean: float
    band_90: Tuple[float, float]


@dataclass
class NormalNormalUpdate:
    mu_post: float
    sigma_post: float
    band_90: Tuple[float, float]


# --------------------------------------------------------------------------- #
# Quantile helpers
# --------------------------------------------------------------------------- #

def _scipy_ppf_safe(family: str, q: float, *args: float) -> Optional[float]:
    """Use scipy if available; otherwise fall back to numerical inversion."""
    try:
        if family == "beta":
            from scipy.stats import beta as _beta  # type: ignore
            return float(_beta.ppf(q, args[0], args[1]))
        if family == "gamma":
            from scipy.stats import gamma as _gamma  # type: ignore
            # scipy gamma uses scale = 1/rate
            return float(_gamma.ppf(q, args[0], scale=1.0 / args[1]))
        if family == "norm":
            from scipy.stats import norm as _norm  # type: ignore
            return float(_norm.ppf(q, loc=args[0], scale=args[1]))
    except Exception:
        return None
    return None


# --- Pure-Python fallbacks (used only if scipy is unavailable) -----------

def _norm_ppf(p: float, mu: float, sigma: float) -> float:
    """Acklam's algorithm-26 inverse normal CDF (≤1e-9 absolute error)."""
    if p <= 0.0:
        return mu - 50.0 * sigma
    if p >= 1.0:
        return mu + 50.0 * sigma
    a = [
        -3.969683028665376e1, 2.209460984245205e2, -2.759285104469687e2,
        1.383577518672690e2, -3.066479806614716e1, 2.506628277459239,
    ]
    b = [
        -5.447609879822406e1, 1.615858368580409e2, -1.556989798598866e2,
        6.680131188771972e1, -1.328068155288572e1,
    ]
    c = [
        -7.784894002430293e-3, -3.223964580411365e-1, -2.400758277161838,
        -2.549732539343734, 4.374664141464968, 2.938163982698783,
    ]
    d = [
        7.784695709041462e-3, 3.224671290700398e-1, 2.445134137142996,
        3.754408661907416,
    ]
    plow = 0.02425
    phigh = 1.0 - plow
    if p < plow:
        q = math.sqrt(-2.0 * math.log(p))
        x = (((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) / \
            ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1.0)
    elif p <= phigh:
        q = p - 0.5
        r = q * q
        x = (((((a[0]*r + a[1])*r + a[2])*r + a[3])*r + a[4])*r + a[5]) * q / \
            (((((b[0]*r + b[1])*r + b[2])*r + b[3])*r + b[4])*r + 1.0)
    else:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        x = -(((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) / \
             ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1.0)
    return mu + sigma * x


def _beta_ppf_bisect(p: float, alpha: float, beta_: float) -> float:
    """Numerical inverse Beta CDF via bisection on the regularized incomplete beta."""
    if p <= 0.0:
        return 0.0
    if p >= 1.0:
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        cdf = _betainc_regularized(alpha, beta_, mid)
        if cdf < p:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-7:
            break
    return 0.5 * (lo + hi)


def _betainc_regularized(a: float, b: float, x: float) -> float:
    """I_x(a,b) — regularized incomplete beta via continued-fraction (Numerical Recipes)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    bt = math.exp(a * math.log(x) + b * math.log(1.0 - x) - lbeta)
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def _betacf(a: float, b: float, x: float, max_iter: int = 200, eps: float = 3e-7) -> float:
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def _gamma_ppf_wilson_hilferty(p: float, alpha: float, beta_: float) -> float:
    """Wilson–Hilferty cube-root approximation, then Newton refinement."""
    z = _norm_ppf(p, 0.0, 1.0)
    h = 1.0 - 1.0 / (9.0 * alpha)
    x = alpha * (h + z * math.sqrt(1.0 / (9.0 * alpha))) ** 3
    return max(0.0, x) / beta_


# --------------------------------------------------------------------------- #
# Conjugate updates
# --------------------------------------------------------------------------- #

def update_beta_bernoulli(
    prior: BetaPrior,
    *,
    n_pos: float,
    n_neg: float,
) -> BetaUpdate:
    """Closed-form Beta–Bernoulli update.

    Accepts fractional counts (weights). Returns posterior α, β, mean, 90% band.
    """
    alpha_post = max(1e-6, prior.alpha + max(0.0, n_pos))
    beta_post = max(1e-6, prior.beta + max(0.0, n_neg))
    mean = alpha_post / (alpha_post + beta_post)
    lo = _scipy_ppf_safe("beta", 0.05, alpha_post, beta_post)
    hi = _scipy_ppf_safe("beta", 0.95, alpha_post, beta_post)
    if lo is None:
        lo = _beta_ppf_bisect(0.05, alpha_post, beta_post)
    if hi is None:
        hi = _beta_ppf_bisect(0.95, alpha_post, beta_post)
    return BetaUpdate(
        alpha_post=alpha_post,
        beta_post=beta_post,
        mean=mean,
        band_90=(round(float(lo), 4), round(float(hi), 4)),
    )


def update_gamma_poisson(
    prior: GammaPrior,
    *,
    total_events: float,
    exposure: float,
) -> GammaUpdate:
    """Closed-form Gamma–Poisson rate update."""
    alpha_post = max(1e-6, prior.alpha + max(0.0, total_events))
    beta_post = max(1e-6, prior.beta + max(0.0, exposure))
    mean = alpha_post / beta_post
    lo = _scipy_ppf_safe("gamma", 0.05, alpha_post, beta_post)
    hi = _scipy_ppf_safe("gamma", 0.95, alpha_post, beta_post)
    if lo is None:
        lo = _gamma_ppf_wilson_hilferty(0.05, alpha_post, beta_post)
    if hi is None:
        hi = _gamma_ppf_wilson_hilferty(0.95, alpha_post, beta_post)
    return GammaUpdate(
        alpha_post=alpha_post,
        beta_post=beta_post,
        mean=mean,
        band_90=(round(float(lo), 4), round(float(hi), 4)),
    )


def update_normal_normal(
    prior: NormalNormalPrior,
    *,
    observations: Sequence[float],
) -> NormalNormalUpdate:
    """Conjugate Normal–Normal update with known observation variance.

    See Bishop 2006 §2.3.6: precision sums.
    """
    sig_p2 = max(1e-9, prior.sigma * prior.sigma)
    sig_o2 = max(1e-9, prior.sigma_obs * prior.sigma_obs)
    n = len(observations)
    if n == 0:
        return NormalNormalUpdate(
            mu_post=prior.mu,
            sigma_post=prior.sigma,
            band_90=(
                round(_norm_ppf(0.05, prior.mu, prior.sigma), 4),
                round(_norm_ppf(0.95, prior.mu, prior.sigma), 4),
            ),
        )
    xbar = sum(float(x) for x in observations) / n
    prec_post = 1.0 / sig_p2 + n / sig_o2
    sigma_post = math.sqrt(1.0 / prec_post)
    mu_post = (prior.mu / sig_p2 + n * xbar / sig_o2) / prec_post
    lo = _scipy_ppf_safe("norm", 0.05, mu_post, sigma_post)
    hi = _scipy_ppf_safe("norm", 0.95, mu_post, sigma_post)
    if lo is None:
        lo = _norm_ppf(0.05, mu_post, sigma_post)
    if hi is None:
        hi = _norm_ppf(0.95, mu_post, sigma_post)
    return NormalNormalUpdate(
        mu_post=round(mu_post, 4),
        sigma_post=round(sigma_post, 4),
        band_90=(round(float(lo), 4), round(float(hi), 4)),
    )


# --------------------------------------------------------------------------- #
# Event-feature extraction (best-effort, fully bounded)
# --------------------------------------------------------------------------- #

_NUMBER_RX = re.compile(r"-?\d+(?:\.\d+)?")


def _event_numeric_value(ev: Dict[str, Any]) -> Optional[float]:
    """Try the obvious annotation slots first; fall back to the first number in preview."""
    ann = ev.get("annotations") or {}
    for key in ("raw_score", "value", "value_numeric", "numeric_value", "lab_value"):
        v = ann.get(key)
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    card = ann.get("card") or {}
    for key in ("value", "lab_value"):
        v = card.get(key)
        if isinstance(v, (int, float)):
            return float(v)
    preview = ev.get("preview") or ""
    m = _NUMBER_RX.search(str(preview))
    if m:
        try:
            return float(m.group(0))
        except (TypeError, ValueError):
            return None
    return None


def _event_text_blob(ev: Dict[str, Any]) -> str:
    ann = ev.get("annotations") or {}
    card = ann.get("card") or {}
    parts = [
        ev.get("preview"),
        card.get("title"),
        card.get("one_line"),
        ann.get("instrument"),
        ann.get("instrument_key"),
    ]
    parts.extend(ann.get("status_flags") or [])
    return " ".join(str(p or "") for p in parts).lower()


def _event_in_code_bucket(gh: GraphHandle, eid: str, bucket: str, key_substrings: List[str]) -> bool:
    table = (gh.code_index or {}).get(bucket) or {}
    if not isinstance(table, dict):
        return False
    needle_set = [s.lower() for s in key_substrings if s]
    for k, rows in table.items():
        if not isinstance(rows, list):
            continue
        if needle_set and not any(s in str(k).lower() for s in needle_set):
            continue
        for r in rows:
            if isinstance(r, dict) and r.get("event_id") == eid:
                return True
    return False


def _event_salience(ev: Dict[str, Any]) -> float:
    ann = ev.get("annotations") or {}
    s = ann.get("salience")
    if isinstance(s, (int, float)):
        return max(0.0, min(10.0, float(s)))
    card = ann.get("card") or {}
    s = card.get("salience")
    if isinstance(s, (int, float)):
        return max(0.0, min(10.0, float(s)))
    return 1.0


def _rule_matches(
    gh: GraphHandle,
    eid: str,
    ev: Dict[str, Any],
    rule: Dict[str, Any],
    *,
    instrument_baseline: Dict[str, float],
) -> bool:
    match = rule.get("match") or {}
    if not isinstance(match, dict):
        return False
    et_filter = match.get("event_type")
    if et_filter and ev.get("event_type") != et_filter:
        return False

    instrument_keys = [str(s).lower() for s in (match.get("instrument_keys") or [])]
    if instrument_keys:
        ann = ev.get("annotations") or {}
        ik = str(ann.get("instrument_key") or ann.get("instrument") or "").lower()
        if not any(s in ik for s in instrument_keys):
            return False

    bucket = match.get("code_index_bucket")
    key_contains = match.get("key_contains") or []
    if isinstance(key_contains, str):
        key_contains = [key_contains]
    if bucket:
        if not _event_in_code_bucket(gh, eid, str(bucket).lower(), list(key_contains)):
            return False
    elif key_contains:
        # No bucket given — substring-match the event text blob instead.
        blob = _event_text_blob(ev)
        if not any(str(s).lower() in blob for s in key_contains):
            return False

    preview_contains = match.get("preview_contains") or []
    if isinstance(preview_contains, str):
        preview_contains = [preview_contains]
    if preview_contains:
        blob = _event_text_blob(ev)
        if not any(str(s).lower() in blob for s in preview_contains):
            return False

    status_in = match.get("status_flag_in") or []
    if status_in:
        ann = ev.get("annotations") or {}
        flags = [str(f).lower() for f in (ann.get("status_flags") or [])]
        if not any(str(s).lower() in flags for s in status_in):
            return False

    val_above = match.get("value_above")
    val_below = match.get("value_below")
    val_delta_above = match.get("value_delta_above")
    if val_above is not None or val_below is not None or val_delta_above is not None:
        n = _event_numeric_value(ev)
        if n is None:
            return False
        if val_above is not None and not (n > float(val_above)):
            return False
        if val_below is not None and not (n < float(val_below)):
            return False
        if val_delta_above is not None:
            ann = ev.get("annotations") or {}
            ik = str(ann.get("instrument_key") or "").lower()
            base = instrument_baseline.get(ik)
            if base is None or not (n - base > float(val_delta_above)):
                return False

    return True


def _establish_baselines(events: Iterable[Tuple[str, Dict[str, Any]]]) -> Dict[str, float]:
    """First-seen numeric value per instrument_key — used for value_delta_above checks."""
    baseline: Dict[str, float] = {}
    for _eid, ev in events:
        ann = ev.get("annotations") or {}
        ik = str(ann.get("instrument_key") or "").lower()
        if not ik or ik in baseline:
            continue
        n = _event_numeric_value(ev)
        if n is not None:
            baseline[ik] = n
    return baseline


# --------------------------------------------------------------------------- #
# Likelihood spec executor
# --------------------------------------------------------------------------- #

@dataclass
class LikelihoodResult:
    n_pos: float
    n_neg: float
    n_skip: float
    weighted_observations: List[float]
    rule_hits: Dict[str, int]
    matched_event_ids: List[str]
    salience_used: bool


def apply_likelihood_spec(
    gh: GraphHandle,
    spec: LikelihoodSpec,
    *,
    evidence_event_ids: Optional[Sequence[str]] = None,
    max_events: int = 5000,
) -> LikelihoodResult:
    """Walk the evidence set; classify each event positive/negative/skip per rules."""
    rules = list(spec.rules or [])
    if evidence_event_ids:
        pairs: List[Tuple[str, Dict[str, Any]]] = []
        for eid in evidence_event_ids:
            ev = gh.events.get(eid)
            if ev:
                pairs.append((eid, ev))
    else:
        pairs = list(gh.events.items())[:max_events]

    pairs.sort(key=lambda kv: str(kv[1].get("timestamp") or ""))

    baselines = _establish_baselines(pairs)
    rule_hits: Dict[str, int] = {}
    matched: List[str] = []
    n_pos = 0.0
    n_neg = 0.0
    n_skip = 0.0
    weighted_observations: List[float] = []

    use_salience = (spec.weight_by or "").lower() == "salience"

    for eid, ev in pairs:
        outcome = "skip"
        weight_extra = 1.0
        rule_label = "no_rule_match"
        for rule in rules:
            if _rule_matches(gh, eid, ev, rule, instrument_baseline=baselines):
                outcome = str(rule.get("outcome") or "skip").lower()
                weight_extra = float(rule.get("weight") or 1.0)
                rule_label = str(rule.get("name") or rule.get("outcome") or "rule")
                break

        rule_hits[rule_label] = rule_hits.get(rule_label, 0) + 1

        if outcome == "skip":
            n_skip += 1
            continue

        sal = _event_salience(ev) if use_salience else 1.0
        # Salience scales 0..10; normalize to a 0..1.5 range so high-salience events
        # contribute up to 1.5x and low-salience down to ~0.2x.
        sal_factor = 0.2 + min(1.3, sal / 7.5) if use_salience else 1.0
        w = max(0.0, weight_extra * sal_factor)

        if outcome == "positive":
            n_pos += w
            matched.append(eid)
        elif outcome == "negative":
            n_neg += w
            matched.append(eid)
        else:
            # Treat as continuous observation if the rule supplies it.
            n_val = _event_numeric_value(ev)
            if n_val is not None:
                weighted_observations.append(n_val)
                matched.append(eid)
            else:
                n_skip += 1

    return LikelihoodResult(
        n_pos=round(n_pos, 4),
        n_neg=round(n_neg, 4),
        n_skip=round(n_skip, 4),
        weighted_observations=weighted_observations,
        rule_hits=rule_hits,
        matched_event_ids=matched,
        salience_used=use_salience,
    )


# --------------------------------------------------------------------------- #
# Built-in defaults — Phase-1 hypotheses (per strategy doc §6 phase 1)
# --------------------------------------------------------------------------- #

DEFAULT_HYPOTHESIS_PRIORS: Dict[str, Dict[str, Any]] = {
    "flare_30d": {
        "family": "beta",
        "alpha": 2.0,
        "beta": 8.0,
        "source": "weak",
        "notes": "Phase-1 weak prior per strategy doc §3.2 (Beta(2,8) → mean 0.20).",
    },
    "progression_3mo": {
        "family": "beta",
        "alpha": 1.5,
        "beta": 8.5,
        "source": "weak",
        "notes": "Phase-4 weak prior per strategy doc §6 phase 4 (Beta(1.5,8.5) → mean 0.15).",
    },
    "taper_safety": {
        "family": "beta",
        "alpha": 6.0,
        "beta": 4.0,
        "source": "weak",
        "notes": "Phase-1 weak prior leaning safe (Beta(6,4) → mean 0.60 prob safe taper).",
    },
}


# Minimal Phase-1 likelihood specs — readable, debuggable, conservative.
DEFAULT_LIKELIHOOD_SPECS: Dict[str, Dict[str, Any]] = {
    "flare_30d": {
        "family": "beta_bernoulli",
        "weight_by": "salience",
        "description": "Flare-in-30-days likelihood from PRO drift, CRP/ESR rises, med escalations.",
        "rules": [
            {
                "name": "crp_high",
                "match": {
                    "event_type": "lab",
                    "code_index_bucket": "labs",
                    "key_contains": ["crp", "c-reactive"],
                    "value_above": 10.0,
                },
                "outcome": "positive",
                "weight": 1.0,
            },
            {
                "name": "esr_high",
                "match": {
                    "event_type": "lab",
                    "code_index_bucket": "labs",
                    "key_contains": ["esr", "sed rate"],
                    "value_above": 30.0,
                },
                "outcome": "positive",
                "weight": 0.8,
            },
            {
                "name": "pro_pain_worsening",
                "match": {
                    "event_type": "pro",
                    "instrument_keys": ["vas_pain", "vas_global"],
                    "value_delta_above": 15.0,
                },
                "outcome": "positive",
                "weight": 0.9,
            },
            {
                "name": "haq_worsening",
                "match": {
                    "event_type": "pro",
                    "instrument_keys": ["haq2", "haq"],
                    "value_delta_above": 0.22,
                },
                "outcome": "positive",
                "weight": 0.7,
            },
            {
                "name": "med_escalation",
                "match": {
                    "event_type": "medication",
                    "preview_contains": [
                        "increased dose", "escalation", "added", "biologic start",
                        "tnf inhibitor", "steroid burst", "prednisone",
                    ],
                },
                "outcome": "positive",
                "weight": 0.5,
            },
            {
                "name": "pro_pain_returning_to_baseline",
                "match": {
                    "event_type": "pro",
                    "instrument_keys": ["vas_pain"],
                    "value_below": 25.0,
                },
                "outcome": "negative",
                "weight": 0.6,
            },
            {
                "name": "haq_returning_to_baseline",
                "match": {
                    "event_type": "pro",
                    "instrument_keys": ["haq2", "haq"],
                    "value_below": 0.5,
                },
                "outcome": "negative",
                "weight": 0.6,
            },
        ],
    },
    "progression_3mo": {
        "family": "beta_bernoulli",
        "weight_by": "salience",
        "description": "Disease progression at 3 months — sustained PRO/lab worsening signals.",
        "rules": [
            {
                "name": "haq_progression",
                "match": {
                    "event_type": "pro",
                    "instrument_keys": ["haq2", "haq"],
                    "value_delta_above": 0.44,
                },
                "outcome": "positive",
                "weight": 1.0,
            },
            {
                "name": "vas_global_progression",
                "match": {
                    "event_type": "pro",
                    "instrument_keys": ["vas_global"],
                    "value_delta_above": 20.0,
                },
                "outcome": "positive",
                "weight": 0.8,
            },
            {
                "name": "structural_damage_imaging",
                "match": {
                    "preview_contains": ["erosion", "joint space narrowing", "structural damage",
                                         "progression on imaging", "sharp van der heijde"],
                },
                "outcome": "positive",
                "weight": 1.2,
            },
            {
                "name": "improvement_status",
                "match": {
                    "event_type": "pro",
                    "status_flag_in": ["improving", "remission", "low_disease_activity"],
                },
                "outcome": "negative",
                "weight": 0.8,
            },
        ],
    },
    "taper_safety": {
        "family": "beta_bernoulli",
        "weight_by": "salience",
        "description": "Probability taper attempt is safe — sustained low activity = positive.",
        "rules": [
            {
                "name": "sustained_low_activity",
                "match": {
                    "event_type": "pro",
                    "status_flag_in": ["remission", "low_disease_activity"],
                },
                "outcome": "positive",
                "weight": 1.0,
            },
            {
                "name": "low_pain_score",
                "match": {
                    "event_type": "pro",
                    "instrument_keys": ["vas_pain"],
                    "value_below": 20.0,
                },
                "outcome": "positive",
                "weight": 0.7,
            },
            {
                "name": "low_haq",
                "match": {
                    "event_type": "pro",
                    "instrument_keys": ["haq2", "haq"],
                    "value_below": 0.5,
                },
                "outcome": "positive",
                "weight": 0.7,
            },
            {
                "name": "recent_flare_signal",
                "match": {
                    "event_type": "pro",
                    "instrument_keys": ["vas_pain"],
                    "value_above": 50.0,
                },
                "outcome": "negative",
                "weight": 1.0,
            },
            {
                "name": "med_escalation_recent",
                "match": {
                    "event_type": "medication",
                    "preview_contains": ["increased dose", "escalation", "steroid burst"],
                },
                "outcome": "negative",
                "weight": 0.9,
            },
        ],
    },
}


def default_likelihood_spec_for(hypothesis_id: str) -> LikelihoodSpec:
    raw = DEFAULT_LIKELIHOOD_SPECS.get(hypothesis_id) or DEFAULT_LIKELIHOOD_SPECS["flare_30d"]
    return LikelihoodSpec(
        family=str(raw.get("family", "beta_bernoulli")),
        rules=list(raw.get("rules") or []),
        weight_by=raw.get("weight_by"),
        description=raw.get("description"),
    )


def _resolve_prior(hypothesis_id: str, prior_override: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    base = dict(DEFAULT_HYPOTHESIS_PRIORS.get(hypothesis_id) or DEFAULT_HYPOTHESIS_PRIORS["flare_30d"])
    if prior_override:
        for k, v in prior_override.items():
            if v is not None:
                base[k] = v
    return base


# --------------------------------------------------------------------------- #
# Top-level: bayesian_update_uc
# --------------------------------------------------------------------------- #

def bayesian_update_uc(
    gh: GraphHandle,
    *,
    hypothesis_id: str,
    evidence_event_ids: Optional[Sequence[str]] = None,
    prior: Optional[Dict[str, Any]] = None,
    likelihood_spec: Optional[Dict[str, Any]] = None,
    notes: Optional[str] = None,
) -> UncertaintyCarrier:
    """Compute a posterior UC for one hypothesis.

    The single primitive the strategy doc §3.3 specifies. Always returns a
    :class:`UncertaintyCarrier` — never raises on missing evidence (a UC with
    only the prior is valid; ``confidence`` will be low and ``basis`` will say so).
    """
    spec_dict = likelihood_spec or DEFAULT_LIKELIHOOD_SPECS.get(
        hypothesis_id, DEFAULT_LIKELIHOOD_SPECS["flare_30d"]
    )
    spec = LikelihoodSpec(
        family=str(spec_dict.get("family", "beta_bernoulli")),
        rules=list(spec_dict.get("rules") or []),
        weight_by=spec_dict.get("weight_by"),
        description=spec_dict.get("description"),
    )
    prior_dict = _resolve_prior(hypothesis_id, prior)
    family = str(prior_dict.get("family") or spec.family.split("_")[0]).lower()

    spec_hash = canonical_spec_hash({"prior": prior_dict, "likelihood": spec.as_dict()})

    likelihood_result = apply_likelihood_spec(
        gh, spec, evidence_event_ids=evidence_event_ids
    )

    basis: List[str] = []
    if prior_dict.get("notes"):
        basis.append(f"prior: {prior_dict['notes']}")
    basis.append(f"spec_hash={spec_hash}")
    basis.append(
        f"evidence: n_pos={likelihood_result.n_pos:.2f} n_neg={likelihood_result.n_neg:.2f} "
        f"n_skip={int(likelihood_result.n_skip)}"
    )
    if likelihood_result.salience_used:
        basis.append("weights = rule_weight × salience_factor (0.2..1.5)")
    if not likelihood_result.matched_event_ids:
        basis.append("no rules matched the evidence — posterior == prior")

    if family == "beta":
        prior_obj = BetaPrior(
            alpha=float(prior_dict.get("alpha", 2.0)),
            beta=float(prior_dict.get("beta", 8.0)),
            source=str(prior_dict.get("source", "weak")),
            notes=prior_dict.get("notes"),
        )
        upd = update_beta_bernoulli(prior_obj, n_pos=likelihood_result.n_pos, n_neg=likelihood_result.n_neg)
        confidence = confidence_from_band(upd.band_90, scale=1.0)
        return UncertaintyCarrier(
            hypothesis_id=hypothesis_id,
            point_estimate=round(upd.mean, 4),
            band_90=upd.band_90,
            confidence=confidence,
            basis=basis,
            evidence_event_ids=list(likelihood_result.matched_event_ids),
            method="beta_conjugate_v1",
            prior=prior_obj.as_dict(),
            posterior_params={"alpha": upd.alpha_post, "beta": upd.beta_post},
            likelihood_summary={
                "n_pos": likelihood_result.n_pos,
                "n_neg": likelihood_result.n_neg,
                "n_skip": likelihood_result.n_skip,
                "rule_hits": likelihood_result.rule_hits,
                "weight_by": spec.weight_by,
                "n_rules": len(spec.rules),
            },
            spec_hash=spec_hash,
            notes=notes,
        )
    if family == "gamma":
        prior_obj_g = GammaPrior(
            alpha=float(prior_dict.get("alpha", 1.0)),
            beta=float(prior_dict.get("beta", 1.0)),
            source=str(prior_dict.get("source", "weak")),
            notes=prior_dict.get("notes"),
        )
        # For gamma-Poisson treat n_pos as event count, n_neg as exposure (years/months).
        upd_g = update_gamma_poisson(
            prior_obj_g,
            total_events=likelihood_result.n_pos,
            exposure=max(1e-6, likelihood_result.n_neg),
        )
        # Gamma posteriors live on positive reals; scale band width for confidence relative to mean.
        scale = max(upd_g.mean * 4.0, 1e-6)
        confidence = confidence_from_band(upd_g.band_90, scale=scale)
        return UncertaintyCarrier(
            hypothesis_id=hypothesis_id,
            point_estimate=round(upd_g.mean, 4),
            band_90=upd_g.band_90,
            confidence=confidence,
            basis=basis,
            evidence_event_ids=list(likelihood_result.matched_event_ids),
            method="gamma_conjugate_v1",
            prior=prior_obj_g.as_dict(),
            posterior_params={"alpha": upd_g.alpha_post, "beta": upd_g.beta_post},
            likelihood_summary={
                "total_events": likelihood_result.n_pos,
                "exposure": likelihood_result.n_neg,
                "n_skip": likelihood_result.n_skip,
                "rule_hits": likelihood_result.rule_hits,
                "weight_by": spec.weight_by,
                "n_rules": len(spec.rules),
            },
            spec_hash=spec_hash,
            notes=notes,
        )
    if family == "normal":
        prior_obj_n = NormalNormalPrior(
            mu=float(prior_dict.get("mu", 0.0)),
            sigma=float(prior_dict.get("sigma", 1.0)),
            sigma_obs=float(prior_dict.get("sigma_obs", 1.0)),
            source=str(prior_dict.get("source", "weak")),
            notes=prior_dict.get("notes"),
        )
        upd_n = update_normal_normal(prior_obj_n, observations=likelihood_result.weighted_observations)
        scale = max(prior_obj_n.sigma * 4.0, 1e-6)
        confidence = confidence_from_band(upd_n.band_90, scale=scale)
        return UncertaintyCarrier(
            hypothesis_id=hypothesis_id,
            point_estimate=upd_n.mu_post,
            band_90=upd_n.band_90,
            confidence=confidence,
            basis=basis,
            evidence_event_ids=list(likelihood_result.matched_event_ids),
            method="normal_normal_conjugate_v1",
            prior=prior_obj_n.as_dict(),
            posterior_params={"mu": upd_n.mu_post, "sigma": upd_n.sigma_post},
            likelihood_summary={
                "n_observations": len(likelihood_result.weighted_observations),
                "n_skip": likelihood_result.n_skip,
                "rule_hits": likelihood_result.rule_hits,
                "weight_by": spec.weight_by,
                "n_rules": len(spec.rules),
            },
            spec_hash=spec_hash,
            notes=notes,
        )

    raise ValueError(f"unsupported prior family: {family!r}")
