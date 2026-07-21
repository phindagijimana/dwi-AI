import pandas as pd
from nodestrength.normative import fit_strength_model, save_model, load_model
from pathlib import Path


def test_save_load_normative_model(tmp_path):
    # create tiny controls long-form
    rows = []
    for i in range(5):
        for nucleus in ("AV", "CM"):
            for side in ("L", "R"):
                rows.append({
                    "subject": f"C{i}", "nucleus": nucleus, "side": side,
                    "strength": 10.0 + i, "age": 10 + i, "sex": "M", "mean_brain_strength": 1.0, "motion": 0.5
                })
    df = pd.DataFrame(rows)
    model = fit_strength_model(df)
    p = tmp_path / "model.pkl"
    save_model(p, model)
    loaded = load_model(p)
    assert isinstance(loaded, type(model))
    assert loaded.target == model.target
