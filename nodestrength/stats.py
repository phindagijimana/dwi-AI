"""Mixed-design GLM with Pillai's trace and partial eta-squared.

Implements the "wide multivariate" form of a repeated-measures ANOVA used by
SPSS GLM, which is what Piper et al. 2026 rely on (Section 2.6: *"Pillai's
trace was used to report the multivariate tests"*).

Mathematics (cf. Rencher, *Methods of Multivariate Analysis*, 3e, Ch. 6):

Given a multivariate linear model ``Y = X B + E`` with ``Y`` (n × p_resp),
``X`` (n × r), and a general hypothesis ``L B M = 0`` where ``L`` (h × r) and
``M`` (p_resp × k):

* Fit ``B = (X'X)^{-1} X' Y`` and ``E_mat = Y - X B``.
* Hypothesis SSP ``H = M' B' L' (L (X'X)^{-1} L')^{-1} L B M``.
* Error SSP ``S = M' E_mat' E_mat M`` with ``df_error = n - rank(X)``.
* Pillai's trace ``V = trace(H (H + S)^{-1})``.
* ``s = min(h, k)``,
  ``m = (|h - k| - 1) / 2``, ``n_ = (df_error - k - 1) / 2``.
* ``F = ((2 n_ + s + 1) / (2 m + s + 1)) · V / (s - V)``,
  ``df1 = s (2 m + s + 1)``, ``df2 = s (2 n_ + s + 1)``.
* Partial eta-squared (multivariate) ``= V / s`` (Bakeman 2005), which is
  what SPSS reports in its multivariate-tests table.

Within-subject effects are handled by choosing ``M`` as an orthonormal
contrast on the repeated-measures cells (e.g. the 4-nucleus × 2-side wide
matrix); between-subject effects use ``M = I`` and ``L`` picking the
factor's design columns. Mixed effects use both.

The intercept column is the first column of ``X``.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from scipy import stats


# ---------------------------------------------------------------------------
# Core multivariate test
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MultivariateResult:
    effect: str
    statistic: str        # "Pillai"
    value: float          # Pillai's trace V
    f: float
    df_num: float
    df_den: float
    p_value: float
    partial_eta_sq: float


def _pillai_from_HE(H: np.ndarray, S: np.ndarray) -> float:
    """Pillai's trace V = trace(H @ inv(H + S)). Robust to (near-)singular H+S."""
    HS = H + S
    try:
        return float(np.trace(H @ np.linalg.solve(HS, np.eye(HS.shape[0]))))
    except np.linalg.LinAlgError:
        return float(np.trace(H @ np.linalg.pinv(HS)))


def multivariate_test(
    Y: np.ndarray,
    X: np.ndarray,
    L: np.ndarray,
    M: Optional[np.ndarray] = None,
    effect_name: str = "effect",
) -> MultivariateResult:
    """Pillai's trace test of L B M = 0 in the model Y = X B + E."""
    n, _ = Y.shape
    if M is None:
        M = np.eye(Y.shape[1])

    Ym = Y @ M
    k = Ym.shape[1]

    XtX = X.T @ X
    XtX_inv = np.linalg.pinv(XtX)
    B = XtX_inv @ X.T @ Y           # (r, p_resp)

    BM = B @ M                      # (r, k)
    resid = Ym - X @ BM             # (n, k)
    S = resid.T @ resid             # error SSP, (k, k)

    LB = L @ BM                              # (h, k)
    middle = L @ XtX_inv @ L.T               # (h, h)
    H = LB.T @ np.linalg.pinv(middle) @ LB   # hypothesis SSP, (k, k)

    h = np.linalg.matrix_rank(L)
    rank_X = np.linalg.matrix_rank(X)
    df_error = n - rank_X

    V = _pillai_from_HE(H, S)

    s = min(h, k)
    if s == 0:
        return MultivariateResult(effect_name, "Pillai", float(V), float("nan"),
                                  0.0, 0.0, float("nan"), 0.0)

    m_par = (abs(h - k) - 1) / 2.0
    n_par = (df_error - k - 1) / 2.0
    df_num = s * (2 * m_par + s + 1)
    df_den = s * (2 * n_par + s + 1)

    eps = 1e-12
    if abs(s - V) < eps or df_den <= 0:
        F = float("inf") if V > eps else 0.0
        p = 0.0 if V > eps else 1.0
    else:
        F = ((2 * n_par + s + 1) / (2 * m_par + s + 1)) * (V / (s - V))
        p = float(stats.f.sf(F, df_num, df_den)) if df_num > 0 and df_den > 0 else float("nan")

    eta = float(V / s)
    return MultivariateResult(
        effect=effect_name,
        statistic="Pillai",
        value=float(V),
        f=float(F),
        df_num=float(df_num),
        df_den=float(df_den),
        p_value=float(p),
        partial_eta_sq=eta,
    )


# ---------------------------------------------------------------------------
# Helpers: wide-form layout and within-subject contrasts
# ---------------------------------------------------------------------------

def pivot_wide(
    long: pd.DataFrame,
    subject: str,
    within_factors: Sequence[str],
    value: str,
) -> Tuple[pd.DataFrame, List[Tuple[str, ...]], Dict[str, List[str]]]:
    """Pivot long → wide for the multivariate model.

    Returns
    -------
    wide : pd.DataFrame, one row per subject, columns indexed by within cells.
    cell_keys : list of within-cell tuples in column order.
    levels : per-factor ordered list of levels.
    """
    levels: Dict[str, List[str]] = {}
    for f in within_factors:
        levels[f] = sorted(long[f].astype(str).unique().tolist())

    wide = long.pivot_table(
        index=subject,
        columns=list(within_factors),
        values=value,
        aggfunc="mean",
    )
    # Order columns canonically.
    cell_keys: List[Tuple[str, ...]] = []
    for combo in _cartesian(levels[f] for f in within_factors):
        cell_keys.append(combo)
    cell_keys = [c if isinstance(c, tuple) else (c,) for c in cell_keys]
    wide = wide.reindex(columns=cell_keys if len(within_factors) > 1 else [c[0] for c in cell_keys])
    return wide, cell_keys, levels


def _cartesian(iterables):
    """Cartesian product of an iterable of iterables, returning tuples."""
    pools = [list(it) for it in iterables]
    result = [()]
    for pool in pools:
        result = [r + (x,) for r in result for x in pool]
    return result


def _helmert_contrast(k: int) -> np.ndarray:
    """k × (k-1) Helmert contrast matrix (orthonormal columns)."""
    if k < 2:
        return np.zeros((k, 0))
    C = np.zeros((k, k - 1))
    for j in range(k - 1):
        for i in range(k):
            if i <= j:
                C[i, j] = 1.0
            elif i == j + 1:
                C[i, j] = -(j + 1)
            else:
                C[i, j] = 0.0
        C[:, j] /= np.linalg.norm(C[:, j])
    return C


def _avg_contrast(k: int) -> np.ndarray:
    """k × 1 averaging contrast (normalized)."""
    if k == 0:
        return np.zeros((0, 1))
    return np.full((k, 1), 1.0 / np.sqrt(k))


def within_contrast(
    cell_keys: Sequence[Tuple[str, ...]],
    within_factors: Sequence[str],
    main_for: Optional[str] = None,
    interaction_for: Optional[Sequence[str]] = None,
) -> np.ndarray:
    """Build the wide-form contrast M for a within main effect or interaction.

    ``main_for`` selects a single within factor; ``interaction_for`` selects a
    set of within factors whose interaction we want. Other within factors are
    averaged via ``_avg_contrast``.
    """
    factor_levels: Dict[str, List[str]] = {f: [] for f in within_factors}
    for key in cell_keys:
        for f, v in zip(within_factors, key):
            if v not in factor_levels[f]:
                factor_levels[f].append(v)

    chosen: Sequence[str]
    if main_for is not None:
        chosen = [main_for]
    elif interaction_for is not None:
        chosen = list(interaction_for)
    else:
        # Overall (cell-mean) contrast — usually unused.
        return _avg_contrast(len(cell_keys))

    # Kronecker assembly per factor, in within_factors order.
    parts: List[np.ndarray] = []
    for f in within_factors:
        k = len(factor_levels[f])
        if f in chosen:
            parts.append(_helmert_contrast(k))
        else:
            parts.append(_avg_contrast(k))

    M = parts[0]
    for p_ in parts[1:]:
        M = np.kron(M, p_)
    return M


# ---------------------------------------------------------------------------
# Between-subjects design matrix
# ---------------------------------------------------------------------------

def _design_between(df: pd.DataFrame,
                    between_factors: Sequence[str]) -> Tuple[np.ndarray, List[str], Dict[str, List[int]]]:
    """Intercept + dummy-coded between factors. Returns X, column names, factor→col-idx map."""
    n = len(df)
    cols: List[np.ndarray] = [np.ones(n)]
    names: List[str] = ["Intercept"]
    factor_idx: Dict[str, List[int]] = {f: [] for f in between_factors}

    for f in between_factors:
        levels = sorted(df[f].astype(str).unique().tolist())
        for lev in levels[1:]:           # drop first as reference
            cols.append((df[f].astype(str) == lev).to_numpy(dtype=float))
            names.append(f"{f}[{lev}]")
            factor_idx[f].append(len(names) - 1)

    X = np.column_stack(cols) if cols else np.zeros((n, 0))
    return X, names, factor_idx


def _L_for_factor(n_cols: int, idx: Sequence[int]) -> np.ndarray:
    """Selector matrix L with rows = unit vectors at ``idx``."""
    L = np.zeros((len(idx), n_cols))
    for r, c in enumerate(idx):
        L[r, c] = 1.0
    return L


# ---------------------------------------------------------------------------
# Repeated-measures driver
# ---------------------------------------------------------------------------

def mixed_anova(
    long: pd.DataFrame,
    subject: str,
    within_factors: Sequence[str],
    between_factors: Sequence[str],
    value: str,
) -> pd.DataFrame:
    """Mixed-design (split-plot) repeated-measures GLM with Pillai's trace.

    Parameters
    ----------
    long : long-form dataframe with one row per (subject, within-cell).
    subject : column name identifying subjects.
    within_factors : list of within-subject factor column names.
    between_factors : list of between-subject factor column names.
    value : the response column (e.g. ``"strength"`` or ``"volume_mm3"``).

    Returns
    -------
    DataFrame with one row per effect: between main, within main, mixed
    interactions. Columns: effect, statistic, value, F, df_num, df_den,
    p, partial_eta_sq.
    """
    wide, cell_keys, _ = pivot_wide(long, subject=subject,
                                    within_factors=within_factors, value=value)
    # Align between covariates to the wide subject index.
    bdf = long.drop_duplicates(subject)[[subject] + list(between_factors)].set_index(subject)
    bdf = bdf.loc[wide.index]

    Y = wide.to_numpy(dtype=float)
    X, x_names, factor_idx = _design_between(bdf.reset_index(drop=True), between_factors)

    results: List[MultivariateResult] = []

    # Between-subject main effects -- M averages across within cells.
    M_avg = _avg_contrast(Y.shape[1])
    for f in between_factors:
        L = _L_for_factor(X.shape[1], factor_idx[f])
        results.append(multivariate_test(Y, X, L, M=M_avg, effect_name=f))

    # Within-subject main effects -- intercept-only L, M = Helmert for that factor.
    L_int = _L_for_factor(X.shape[1], [0])
    for f in within_factors:
        M = within_contrast(cell_keys, within_factors, main_for=f)
        results.append(multivariate_test(Y, X, L_int, M=M, effect_name=f))

    # Within × within interactions.
    for r in range(2, len(within_factors) + 1):
        for combo in combinations(within_factors, r):
            M = within_contrast(cell_keys, within_factors, interaction_for=combo)
            results.append(multivariate_test(Y, X, L_int, M=M,
                                             effect_name=" x ".join(combo)))

    # Between × within interactions (mixed).
    for bf in between_factors:
        L = _L_for_factor(X.shape[1], factor_idx[bf])
        for f in within_factors:
            M = within_contrast(cell_keys, within_factors, main_for=f)
            results.append(multivariate_test(Y, X, L, M=M,
                                             effect_name=f"{bf} x {f}"))
        for r in range(2, len(within_factors) + 1):
            for combo in combinations(within_factors, r):
                M = within_contrast(cell_keys, within_factors, interaction_for=combo)
                results.append(multivariate_test(Y, X, L, M=M,
                                                 effect_name=f"{bf} x " + " x ".join(combo)))

    # Between × between interactions (mixed/multivariate).
    for r in range(2, len(between_factors) + 1):
        for combo in combinations(between_factors, r):
            idx = sum((factor_idx[bf] for bf in combo), [])
            L = _L_for_factor(X.shape[1], idx)
            results.append(multivariate_test(Y, X, L, M=M_avg,
                                             effect_name=" x ".join(combo)))

    return pd.DataFrame([r.__dict__ for r in results])
