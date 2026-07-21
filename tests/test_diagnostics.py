import pandas as pd
from nodestrength.diagnostics import permutation_test_mixed_anova


def make_cohort():
    rows = []
    for sid in range(10):
        group = "control" if sid < 5 else "patient"
        for nucleus in ("AV", "CM"):
            for side in ("L", "R"):
                rows.append({
                    "subject": f"S{sid}", "nucleus": nucleus, "side": side,
                    "strength": 10.0 + (sid >= 5) * 1.0 + (1.0 if nucleus == "CM" else 0.0),
                    "group": group,
                })
    return pd.DataFrame(rows)


def test_permutation_small():
    df = make_cohort()
    res = permutation_test_mixed_anova(
        long=df, subject="subject", within_factors=("nucleus", "side"),
        between_factors=("group",), value="strength", effect_name="group", n_permutations=100, seed=42
    )
    assert "p_empirical" in res
    assert 0.0 <= res["p_empirical"] <= 1.0
