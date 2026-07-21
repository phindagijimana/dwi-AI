"""Diagnostics: residual checks and permutation tests for the mixed ANOVA.

Utilities here are lightweight and avoid heavy plotting deps unless needed.
"""
from __future__ import annotations

from typing import Optional, Sequence
import numpy as np
import pandas as pd

from .stats import mixed_anova


def permute_between_labels(long: pd.DataFrame, subject: str, between: Sequence[str], seed: Optional[int] = None) -> pd.DataFrame:
    """Return a copy of `long` with between-subject factor levels permuted across subjects.

    Keeps within-subject rows grouped by `subject` but shuffles the between-factor
    assignments among subjects. Useful for permutation testing of between-subject effects.
    """
    rng = np.random.default_rng(seed)
    subj_df = long.drop_duplicates(subject)[[subject] + list(between)].set_index(subject)
    subj_ids = subj_df.index.to_numpy()
    permuted = subj_df.sample(frac=1.0, replace=False, random_state=rng.bit_generator).reset_index(drop=False)
    permuted_vals = {}
    for i, sid in enumerate(subj_ids):
        row = permuted.iloc[i]
        vals = {f: row[f] for f in between}
        permuted_vals[sid] = vals

    out = long.copy()
    for sid, vals in permuted_vals.items():
        mask = out[subject] == sid
        for f, v in vals.items():
            out.loc[mask, f] = v
    return out


def permutation_test_mixed_anova(
    long: pd.DataFrame,
    subject: str,
    within_factors: Sequence[str],
    between_factors: Sequence[str],
    value: str,
    effect_name: str,
    n_permutations: int = 1000,
    seed: Optional[int] = None,
) -> dict:
    """Permutation test for a named effect in `mixed_anova`.

    Returns a dict with observed statistic and empirical p-value.
    The permutation shuffles between-subject labels (across subjects) while
    keeping within-subject structure intact.
    """
    obs_df = mixed_anova(long, subject=subject, within_factors=within_factors,
                         between_factors=between_factors, value=value)
    if effect_name not in obs_df['effect'].values:
        raise ValueError(f"Effect {effect_name} not found in observed results")
    obs_row = obs_df[obs_df['effect'] == effect_name].iloc[0]
    obs_value = float(obs_row['value'])

    rng = np.random.default_rng(seed)
    exceed = 0
    stats = []
    subj_ids = long[subject].unique()

    for i in range(n_permutations):
        perm_long = permute_between_labels(long, subject, between_factors, seed=rng.integers(0, 2**31))
        p_df = mixed_anova(perm_long, subject=subject, within_factors=within_factors,
                           between_factors=between_factors, value=value)
        if effect_name not in p_df['effect'].values:
            stats.append(np.nan)
            continue
        val = float(p_df[p_df['effect'] == effect_name].iloc[0]['value'])
        stats.append(val)
        if val >= obs_value:
            exceed += 1

    # empirical p-value (including observed) per common practice
    p_emp = (exceed + 1) / (n_permutations + 1)
    return {
        'effect': effect_name,
        'observed': obs_value,
        'p_empirical': p_emp,
        'perm_values': np.array(stats),
    }
