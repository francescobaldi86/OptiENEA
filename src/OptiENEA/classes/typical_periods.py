# optienea/typical_periods.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple, Callable, Any
import numpy as np
import pandas as pd


# -----------------------------
# Data containers
# -----------------------------

@dataclass(frozen=True)
class TypicalPeriodSet:
    """
    Represents a reduced time series set:
      - profiles: dict var -> array [K, L] (K typical periods, L hours per period)
      - weights: array [K] (occurrence counts or fractional weights)
      - representatives: array [K] (original period index chosen as medoid; -1 if synthetic)
      - assignment: array [P] mapping each original period p -> typical index k
      - period_index: DatetimeIndex or PeriodIndex for original periods (length P)
      - meta: quality metrics or settings
    """
    profiles: Dict[str, np.ndarray]
    weights: np.ndarray
    representatives: np.ndarray
    assignment: np.ndarray
    period_index: pd.Index
    hours_per_period: int
    period: str
    meta: Dict[str, Any] = field(default_factory=dict)

    @property
    def K(self) -> int:
        return int(self.weights.shape[0])

    @property
    def L(self) -> int:
        return int(self.hours_per_period)

    def to_long_dataframe(self) -> pd.DataFrame:
        """Return long-form DataFrame: columns = [k, t, var, value]."""
        rows = []
        for var, arr in self.profiles.items():
            K, L = arr.shape
            kk = np.repeat(np.arange(K), L)
            tt = np.tile(np.arange(L), K)
            rows.append(pd.DataFrame({"k": kk, "t": tt, "var": var, "value": arr.reshape(-1)}))
        return pd.concat(rows, ignore_index=True)

    def to_ampl_params(self) -> Dict[str, Any]:
        """
        Produces structures convenient for AMPL data export:
          - sets: K, T
          - params: w[k], and each var[k,t]
        """
        K = self.K
        L = self.L
        out: Dict[str, Any] = {
            "sets": {
                "K": list(range(1, K + 1)),
                "T": list(range(1, L + 1)),
            },
            "params": {
                "w": {k + 1: float(self.weights[k]) for k in range(K)},
            },
        }
        for var, arr in self.profiles.items():
            out["params"][var] = {(k + 1, t + 1): float(arr[k, t]) for k in range(K) for t in range(L)}
        return out


# -----------------------------
# 1) Segmentation
# -----------------------------

class PeriodSegmenter:
    """
    Segments an hourly DateTimeIndex series into periods of length L.
    Supports:
      - period="day" (24)
      - period="week" (168) (ISO weeks)
      - custom hours_per_period (e.g. 12, 48, etc.)
    """

    def __init__(self, period: str = "day", hours_per_period: Optional[int] = None, tz_aware_ok: bool = True):
        self.period = period.lower()
        if hours_per_period is None:
            if self.period == "day":
                self.hours_per_period = 24
            elif self.period == "week":
                self.hours_per_period = 168
            else:
                raise ValueError("hours_per_period must be provided for custom period types.")
        else:
            self.hours_per_period = int(hours_per_period)
        self.tz_aware_ok = tz_aware_ok

    def segment(self, series: pd.Series) -> Tuple[np.ndarray, pd.Index]:
        """
        Returns:
          X: array [P, L] where P is number of periods, L=hours_per_period
          period_index: index identifying each period (e.g., each date / week start)
        """
        if not isinstance(series.index, pd.DatetimeIndex):
            series.index = pd.date_range(start = pd.to_datetime('2023-01-01 00:00'), periods=len(series.index.values), freq = 'H')

        s = series.sort_index()
        if not self.tz_aware_ok and s.index.tz is not None:
            raise ValueError("Timezone-aware indices are not allowed (set tz_aware_ok=True or localize/convert).")

        # Ensure hourly frequency (or at least regular). We won’t fill gaps silently.
        diffs = s.index.to_series().diff().dropna()
        if not (diffs == pd.Timedelta(hours=1)).all():
            raise ValueError("Series must be strictly hourly with no gaps (diff != 1h found).")

        # Custom: chunk from first timestamp
        L = self.hours_per_period
        n = len(s)
        P = n // L
        if P == 0:
            return np.empty((0, L)), pd.DatetimeIndex([])
        trimmed = s.iloc[: P * L]
        X = trimmed.values.reshape(P, L)
        # period labels = start time of each chunk
        idx = trimmed.index[::L]
        return X, pd.DatetimeIndex(idx)


class MultiSeriesSegmenter:
    """Segments multiple named series consistently (same time index expected)."""

    def __init__(self, segmenter: PeriodSegmenter):
        self.segmenter = segmenter

    def segment(self, data: pd.DataFrame) -> Tuple[Dict[str, np.ndarray], pd.Index]:
        if not isinstance(data, pd.DataFrame):
            raise TypeError("df must be a pandas DataFrame.")
        if data.empty:
            raise ValueError("df is empty.")
        if data.columns.size == 0:
            raise ValueError("df has no columns.")
        # Initialize the output
        segmented: Dict[str, np.ndarray] = {}
        period_index: Optional[pd.Index] = None
        # Proceed with the segmentation
        for col in data.columns:
            s = data[col]
            X, pidx = self.segmenter.segment(s)
            segmented[col] = X
            if period_index is None:
                period_index = pidx

        assert period_index is not None
        return segmented, period_index


# -----------------------------
# 2) Feature building
# -----------------------------

@dataclass
class FeatureConfig:
    include_shape: bool = True
    include_level_mean: bool = True
    include_level_max: bool = False
    include_level_min: bool = False
    # per-variable weights in distance space
    var_weights: Dict[str, float] = field(default_factory=dict)
    # standardize features globally
    standardize: bool = True
    eps: float = 1e-9


class FeatureBuilder:
    """
    Build per-period feature vectors from segmented arrays [P, L] for each variable.
    Default: shape (normalized by period mean) + period mean level.
    """

    def __init__(self, config: FeatureConfig):
        self.cfg = config
        self._mu: Optional[np.ndarray] = None
        self._sigma: Optional[np.ndarray] = None

    def fit_transform(self, segmented: Dict[str, np.ndarray]) -> np.ndarray:
        F = self._build_raw(segmented)
        if self.cfg.standardize:
            self._mu = F.mean(axis=0)
            self._sigma = F.std(axis=0) + self.cfg.eps
            return (F - self._mu) / self._sigma
        return F

    def transform(self, segmented: Dict[str, np.ndarray]) -> np.ndarray:
        F = self._build_raw(segmented)
        if self.cfg.standardize:
            if self._mu is None or self._sigma is None:
                raise RuntimeError("FeatureBuilder not fitted.")
            return (F - self._mu) / self._sigma
        return F

    def _build_raw(self, segmented: Dict[str, np.ndarray]) -> np.ndarray:
        feats = []
        P = None
        for var, X in segmented.items():
            if P is None:  # Getting the number of periods
                P = X.shape[0]
            if X.ndim != 2:  # Checking that the data has exactly two dimensions
                raise ValueError(f"Segmented array for {var} must be 2D [P,L].")
            w = float(self.cfg.var_weights.get(var, 1.0))  # Gets the weight of the variable

            # shape features
            if self.cfg.include_shape:
                mean = X.mean(axis=1, keepdims=True)  # Calculates the mean for each period
                shape = X / (mean + self.cfg.eps) # Adimensionalizes each value by dividing it by the period mean
                feats.append(w * shape) # Each value is multiplied by the weight assigned to the feature

            # level features
            level_cols = []
            if self.cfg.include_level_mean:
                level_cols.append(X.mean(axis=1, keepdims=True))  # First element of level_cols is a vector with the mean of each day
            if self.cfg.include_level_max:
                level_cols.append(X.max(axis=1, keepdims=True))  # Second element is the maximum value for each day
            if self.cfg.include_level_min:
                level_cols.append(X.min(axis=1, keepdims=True))  # Third element (if selected) is the minimum value for each day
            if level_cols:
                level = np.hstack(level_cols)  # Horizontally stacks the lists, getting a numpy array
                feats.append(w * level) # Again we multiply the result by the weight

        if P is None:
            raise ValueError("No variables in segmented data.")
        return np.hstack(feats)


# -----------------------------
# 3) Clustering: k-medoids (PAM)
# -----------------------------

@dataclass
class KMedoidsResult:
    medoids: np.ndarray         # [K] indices in 0..P-1
    assignment: np.ndarray      # [P] cluster id
    inertia: float              # sum distances to medoid


def pairwise_distances(X: np.ndarray) -> np.ndarray:
    """Euclidean pairwise distances (P x P)."""
    # For P <= 400 this is fine; for very large P consider approximate / chunking.
    G = X @ X.T
    sq = np.clip(np.diag(G)[:, None] - 2 * G + np.diag(G)[None, :], 0.0, None)
    return np.sqrt(sq)


class KMedoidsPAM:
    """
    Simple PAM implementation:
      - build full pairwise distance matrix
      - initialize medoids (greedy)
      - swap improvement
    For P~365 days, this is fast enough.
    """

    def __init__(self, random_state: int = 0, max_iter: int = 200):
        self.random_state = int(random_state)
        self.max_iter = int(max_iter)

    def fit(self, X: np.ndarray, K: int) -> KMedoidsResult:
        rng = np.random.default_rng(self.random_state)
        P = X.shape[0]
        if K <= 0 or K > P:
            raise ValueError("K must be in 1..P.")

        D = pairwise_distances(X)

        # --- init: greedy farthest-first
        medoids = [int(rng.integers(0, P))]
        while len(medoids) < K:
            dist_to_set = D[:, medoids].min(axis=1)
            # choose the point with max distance to current medoids
            cand = int(np.argmax(dist_to_set))
            if cand in medoids:
                cand = int(rng.integers(0, P))
            medoids.append(cand)
        medoids = np.array(medoids, dtype=int)

        # helper for assignment & cost
        def assign_cost(meds: np.ndarray) -> Tuple[np.ndarray, float]:
            dist = D[:, meds]  # P x K
            assignment = dist.argmin(axis=1)
            cost = dist[np.arange(P), assignment].sum()
            return assignment, float(cost)

        assignment, best_cost = assign_cost(medoids)

        # --- PAM swaps
        for _ in range(self.max_iter):
            improved = False
            for mi in range(K):
                m = medoids[mi]
                # try swapping medoid m with each non-medoid point
                non_medoids = [i for i in range(P) if i not in set(medoids)]
                for h in non_medoids:
                    trial = medoids.copy()
                    trial[mi] = h
                    _, cost = assign_cost(trial)
                    if cost + 1e-12 < best_cost:
                        medoids = trial
                        assignment, best_cost = assign_cost(medoids)
                        improved = True
                        break
                if improved:
                    break
            if not improved:
                break

        return KMedoidsResult(medoids=medoids, assignment=assignment, inertia=best_cost)


# -----------------------------
# 4) Extremes selection
# -----------------------------

@dataclass
class ExtremeCriterion:
    """
    A criterion identifies a period index to force-include.
    score_fn returns a score per period p; argmax or argmin selected.
    """
    name: str
    score_fn: Callable[[Dict[str, np.ndarray]], np.ndarray]
    mode: str = "max"  # "max" or "min"
    take: int = 1      # number of extreme periods to take


class ExtremeSelector:
    def __init__(self, criteria: Sequence[ExtremeCriterion]):
        self.criteria = list(criteria)

    def select(self, segmented: Dict[str, np.ndarray]) -> List[int]:
        P = next(iter(segmented.values())).shape[0]  # Number of periods
        chosen: List[int] = []
        for c in self.criteria:
            scores = c.score_fn(segmented)
            if scores.shape != (P,):
                raise ValueError(f"Criterion {c.name} must return shape (P,).")
            order = np.argsort(scores)
            if c.mode == "max":
                order = order[::-1]
            picks = []
            for idx in order:
                if int(idx) not in chosen:
                    picks.append(int(idx))
                if len(picks) >= c.take:
                    break
            chosen.extend(picks)
        return chosen


# -----------------------------
# 5) Build typical periods
# -----------------------------

@dataclass
class TypicalPeriodConfig:
    K: int
    period: str = "day"
    hours_per_period: Optional[int] = None
    random_state: int = 0
    max_iter: int = 200

    # energy correction:
    #  - "none"
    #  - "global" (single alpha per var)
    #  - "clusterwise" (alpha per cluster per var)
    energy_correction: str = "clusterwise"

    # add extreme periods?
    extreme_selector: Optional[ExtremeSelector] = None
    # If extremes are added, how to handle weights?
    #  - "deduct": deduct those occurrences from clusters (keeps total periods constant)
    #  - "append": keep clusters as-is and add extreme periods on top (total weight increases)
    extreme_weight_mode: str = "deduct"


class TypicalPeriodBuilder:
    def __init__(self, feature_config: FeatureConfig, typical_config: TypicalPeriodConfig):
        self.feature_config = feature_config
        self.typical_config = typical_config

    def build(self, data: Dict[str, pd.Series]) -> TypicalPeriodSet:
        # 1) segment
        seg = PeriodSegmenter(self.typical_config.period, self.typical_config.hours_per_period)
        mseg = MultiSeriesSegmenter(seg)
        segmented, period_index = mseg.segment(data)  # var -> [P,L]
        P = next(iter(segmented.values())).shape[0]
        L = seg.hours_per_period

        if P == 0:
            raise ValueError("No full periods found (check completeness and frequency).")

        # 2) features
        fb = FeatureBuilder(self.feature_config)
        X = fb.fit_transform(segmented)

        # 3) choose extremes (optional)
        forced = []
        if self.typical_config.extreme_selector is not None:
            forced = self.typical_config.extreme_selector.select(segmented)

        # 4) cluster with PAM (on non-forced if using deduct)
        all_idx = np.arange(P)
        forced_set = set(forced)

        if forced and self.typical_config.extreme_weight_mode == "deduct":
            pool = np.array([i for i in all_idx if i not in forced_set], dtype=int)
            X_pool = X[pool]
            K_eff = self.typical_config.K
            if K_eff > len(pool):
                raise ValueError(f"K too large relative to remaining periods after forcing extremes. You provided a value for K equal to {K_eff}, but the remaining number of periods is {len(pool)}")
            pam = KMedoidsPAM(random_state=self.typical_config.random_state, max_iter=self.typical_config.max_iter)
            res = pam.fit(X_pool, K_eff)
            medoids = pool[res.medoids]
            assignment = np.full(P, -1, dtype=int)
            assignment_pool = res.assignment
            assignment[pool] = assignment_pool
            # forced periods become their own clusters appended at end
            forced_clusters = {p: (K_eff + j) for j, p in enumerate(forced)}
            for p, k in forced_clusters.items():
                assignment[p] = k
            K_total = K_eff + len(forced)
            representatives = np.concatenate([medoids, np.array(forced, dtype=int)])
        else:
            # cluster everything first
            pam = KMedoidsPAM(random_state=self.typical_config.random_state, max_iter=self.typical_config.max_iter)
            res = pam.fit(X, self.typical_config.K)
            assignment = res.assignment.copy()
            representatives = res.medoids.copy()
            K_total = self.typical_config.K
            # optionally append extremes as additional clusters
            if forced and self.typical_config.extreme_weight_mode == "append":
                # each forced becomes its own cluster appended; keep original assignment
                forced_clusters = {p: (K_total + j) for j, p in enumerate(forced)}
                assignment2 = assignment.copy()
                for p, k in forced_clusters.items():
                    assignment2[p] = k
                assignment = assignment2
                representatives = np.concatenate([representatives, np.array(forced, dtype=int)])
                K_total = K_total + len(forced)

        # 5) compute weights as counts
        weights = np.zeros(K_total, dtype=float)
        for k in range(K_total):
            weights[k] = float(np.sum(assignment == k))

        # 6) build representative profiles (use medoids)
        profiles: Dict[str, np.ndarray] = {}
        for var, Xvar in segmented.items():
            prof = np.zeros((K_total, L), dtype=float)
            for k in range(K_total):
                # representative is medoid if defined; else fall back to cluster mean
                rep = int(representatives[k]) if k < len(representatives) else -1
                if rep >= 0:
                    prof[k, :] = Xvar[rep, :]
                else:
                    members = np.where(assignment == k)[0]
                    prof[k, :] = Xvar[members].mean(axis=0)
            profiles[var] = prof

        # 7) energy correction
        mode = self.typical_config.energy_correction.lower()
        if mode not in ("none", "global", "clusterwise"):
            raise ValueError("energy_correction must be one of: none, global, clusterwise")

        if mode != "none":
            for var, Xvar in segmented.items():
                E_orig = float(Xvar.sum())
                E_recon = float((profiles[var] * weights[:, None]).sum())
                if E_recon <= 0:
                    continue

                if mode == "global":
                    alpha = E_orig / E_recon
                    profiles[var] *= alpha

                elif mode == "clusterwise":
                    # scale each cluster so its energy matches the sum of original periods assigned to it
                    for k in range(K_total):
                        members = np.where(assignment == k)[0]
                        if len(members) == 0:
                            continue
                        E_k_orig = float(Xvar[members].sum())
                        E_k_recon = float(weights[k] * profiles[var][k, :].sum())
                        if E_k_recon > 0:
                            profiles[var][k, :] *= (E_k_orig / E_k_recon)

        # 8) basic metrics (you can extend)
        meta = {
            "period": self.typical_config.period,
            "hours_per_period": L,
            "K_requested": self.typical_config.K,
            "K_total": K_total,
            "forced_extremes": forced,
        }
        # energy error check (post-correction should be ~0)
        energy_errors = {}
        for var, Xvar in segmented.items():
            E_orig = float(Xvar.sum())
            E_recon = float((profiles[var] * weights[:, None]).sum())
            energy_errors[var] = (E_recon - E_orig)
        meta["energy_errors"] = energy_errors

        return TypicalPeriodSet(
            profiles=profiles,
            weights=weights,
            representatives=np.array(representatives, dtype=int),
            assignment=np.array(assignment, dtype=int),
            period_index=period_index,
            hours_per_period=L,
            period = self.typical_config.period,
            meta=meta,
        )


@dataclass
class ErrorReport:
    """
    metrics[var] -> dict of metric name -> value
    reconstructed[var] -> pd.Series (hourly reconstructed)
    """
    metrics: Dict[str, Dict[str, float]]
    reconstructed: Dict[str, pd.Series]
    meta: Dict[str, Any] = field(default_factory=dict)


def _rmse(a: np.ndarray, b: np.ndarray) -> float:
    d = a - b
    return float(np.sqrt(np.mean(d * d)))


def _mae(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean(np.abs(a - b)))


def _mape(a: np.ndarray, b: np.ndarray, eps: float = 1e-9) -> float:
    # MAPE is dangerous when a ~ 0; we guard it.
    denom = np.maximum(np.abs(a), eps)
    return float(np.mean(np.abs((a - b) / denom)))


def _energy_error(a: np.ndarray, b: np.ndarray) -> float:
    # relative energy error
    ea = float(a.sum())
    eb = float(b.sum())
    if abs(ea) < 1e-9:
        return float("nan")
    return float((eb - ea) / ea)


def _peak_error(a: np.ndarray, b: np.ndarray) -> float:
    pa = float(np.max(a))
    pb = float(np.max(b))
    if abs(pa) < 1e-9:
        return float("nan")
    return float((pb - pa) / pa)


def _duration_curve_rmse(a: np.ndarray, b: np.ndarray) -> float:
    # Compare sorted values (ignores chronology)
    sa = np.sort(a)[::-1]
    sb = np.sort(b)[::-1]
    return _rmse(sa, sb)


def _top_quantile_rmse(a: np.ndarray, b: np.ndarray, q: float = 0.01) -> float:
    # RMSE on top q fraction (e.g., 1%) of original values
    if not (0.0 < q < 1.0):
        raise ValueError("q must be in (0,1)")
    thresh = np.quantile(a, 1.0 - q)
    mask = a >= thresh
    if mask.sum() == 0:
        return float("nan")
    return _rmse(a[mask], b[mask])


class TypicalPeriodEvaluator:
    """
    Reconstructs a synthetic hourly year by mapping each original period to its typical representative,
    and computes error metrics between original and reconstructed.

    Works if:
      - you can provide the original hourly data (DataFrame) used to build typical periods
      - TypicalPeriodSet.assignment exists (mapping from period p to cluster k)
    """

    def __init__(self, start: str = "2019-01-01 00:00"):
        self.start = start

    def reconstruct(self, tp: TypicalPeriodSet, original_df: pd.DataFrame) -> Dict[str, pd.Series]:
        """
        Returns reconstructed hourly series per variable.
        """
        # Segment original to know which hours belong to which period
        seg = PeriodSegmenter(period=tp.period, hours_per_period=tp.hours_per_period)
        L = seg.hours_per_period

        # We'll segment by using one column to derive period_index + ensure full periods only
        first_col = original_df.columns[0]
        _, period_index = seg.segment(original_df[first_col])

        P = len(period_index)
        if P != len(tp.assignment):
            raise ValueError(
                f"TypicalPeriodSet.assignment length ({len(tp.assignment)}) does not match "
                f"number of full periods in data ({P})."
            )

        reconstructed: Dict[str, pd.Series] = {}

        # Build a reconstructed block [P, L] for each var, then flatten back to hourly
        for var in tp.profiles.keys():
            if var not in original_df.columns:
                # you might have clustered on subset; skip if not in original
                continue

            # Segment original for alignment and to get which periods are "kept"
            Xorig, pidx2 = seg.segment(original_df[var])
            if not pidx2.equals(period_index):
                raise ValueError(f"Period segmentation mismatch for var '{var}'.")

            # Replace each period p with its assigned typical profile
            Xrec = np.zeros_like(Xorig, dtype=float)
            for p in range(P):
                k = int(tp.assignment[p])
                Xrec[p, :] = tp.profiles[var][k, :]

            # Flatten to hourly and attach datetime index corresponding to the kept full periods
            # Rebuild hourly index from period starts
            hour_index = pd.date_range(start=period_index[0], periods=P * L, freq="H")
            # reconstructed[var] = pd.Series(Xrec.reshape(-1), index=hour_index, name=var)
            reconstructed[var] = pd.Series(Xrec.reshape(-1),name=var)

        return reconstructed

    def evaluate(
        self,
        typical_periods: TypicalPeriodSet,
        original_data: pd.DataFrame,
        metrics: Optional[List[str]] = None,
        top_q: float = 0.01,
    ) -> ErrorReport:
        """
        Compute error metrics per variable between original and reconstructed series.

        Metrics supported:
          - rmse, mae, mape
          - energy_rel_error
          - peak_rel_error
          - duration_curve_rmse
          - topq_rmse  (RMSE over top_q fraction of original values)
        """
        if metrics is None:
            metrics = [
                "rmse",
                "mae",
                "mape",
                "energy_rel_error",
                "peak_rel_error",
                "duration_curve_rmse",
                "topq_rmse",
            ]

        rec = self.reconstruct(typical_periods, original_data)

        out_metrics: Dict[str, Dict[str, float]] = {}

        for var, rec_s in rec.items():
            # Align original to reconstructed range (because segmentation may drop partial last period)
            orig_s = original_data[var].loc[rec_s.index.min() : rec_s.index.max()]
            orig_s = orig_s.reindex(rec_s.index)

            a = orig_s.to_numpy(dtype=float)
            b = rec_s.to_numpy(dtype=float)

            # Guard NaNs
            mask = np.isfinite(a) & np.isfinite(b)
            a = a[mask]
            b = b[mask]
            if len(a) == 0:
                continue

            md: Dict[str, float] = {}
            for m in metrics:
                if m == "rmse":
                    md[m] = _rmse(a, b)
                elif m == "mae":
                    md[m] = _mae(a, b)
                elif m == "mape":
                    md[m] = _mape(a, b)
                elif m == "energy_rel_error":
                    md[m] = _energy_error(a, b)
                elif m == "peak_rel_error":
                    md[m] = _peak_error(a, b)
                elif m == "duration_curve_rmse":
                    md[m] = _duration_curve_rmse(a, b)
                elif m == "topq_rmse":
                    md[m] = _top_quantile_rmse(a, b, q=top_q)
                else:
                    raise ValueError(f"Unknown metric: {m}")

            out_metrics[var] = md

        meta = {
            "period": self.period,
            "hours_per_period": self.hours_per_period,
            "top_q": top_q,
            "note": "Reconstruction replaces each original period by its assigned typical profile; chronology within periods is preserved, across periods is approximated.",
        }

        return ErrorReport(metrics=out_metrics, reconstructed=rec, meta=meta)



# -----------------------------
# Helpers: common extreme criteria
# -----------------------------

def extreme_peak(var: str, take: int = 1) -> ExtremeCriterion:
    def score(seg: Dict[str, np.ndarray]) -> np.ndarray:
        X = seg[var]  # [P,L]
        return X.max(axis=1)
    return ExtremeCriterion(name=f"peak_{var}", score_fn=score, mode="max", take=take)


def extreme_min_sum(var: str, take: int = 1) -> ExtremeCriterion:
    def score(seg: Dict[str, np.ndarray]) -> np.ndarray:
        X = seg[var]
        return X.sum(axis=1)
    return ExtremeCriterion(name=f"min_energy_{var}", score_fn=score, mode="min", take=take)


def extreme_netload_peak(demand_var: str, supply_var: str, take: int = 1) -> ExtremeCriterion:
    """
    netload = demand - supply. Peak netload days often drive capacity.
    """
    def score(seg: Dict[str, np.ndarray]) -> np.ndarray:
        d = seg[demand_var]
        s = seg[supply_var]
        net = d - s
        return net.max(axis=1)
    return ExtremeCriterion(name=f"peak_netload_{demand_var}_minus_{supply_var}", score_fn=score, mode="max", take=take)
