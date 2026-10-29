"""Which covariate kinds each model type can actually accept (Backlog #107).

Why this exists
---------------
`model_instances.past_covariate` / `.future_covariate` are the flags the
Solutions UI reads (`SolutionModal` -> `IndicatorSelector`'s `hasPastCovariate`
/ `hasFutureCovariate`) to decide which covariate choices to offer. They were
**never populated**: the create path at `routes.py` inserts
`model_instances` without them, so every instance fell to the column default of
`0` and the UI concluded that no model accepts any covariate. Measured before
fixing: instance 1 is BlockRNN with `0/0` while `solution_1` has four past
covariates attached to it.

The distinction is not cosmetic. A *future* covariate must be known over the
forecast horizon at prediction time; offering one where the model cannot take
it — or where the series cannot be known ahead — is how look-ahead bias gets
configured in by hand (Backlog #104, #105).

Source, and its limit — stated rather than implied
--------------------------------------------------
The table encodes **documented Darts semantics**. It is NOT machine-verified,
because **darts is not a dependency of this repo** — `import darts` appears
nowhere, no `requirements.txt` lists it, and no `model_instances` row has a
`file_path` or a `last_training_date`. The model catalogue in
`MODEL_TYPE_MAP` is inherited from the WebAPI original and is currently
aspirational.

So treat this as the single auditable place to correct, not as ground truth. If
darts is ever added, replace the literals with the library's own
`supports_past_covariates` / `supports_future_covariates` class attributes and
delete the table — `test_model_capabilities.py` pins the shape so that swap is
safe.

The asymmetry worth knowing: `BlockRNNModel` takes **past** covariates only,
while `RNNModel` takes **future** covariates only. They are easy to confuse and
the existing `tbl_model_field` seed gets both wrong (it offers both kinds for
each) — see the note at the end of this module.
"""
from __future__ import annotations

from typing import Dict, Tuple

#: canonical model type -> (accepts past covariates, accepts future covariates)
#:
#: Keys are the VALUES of `routes.MODEL_TYPE_MAP`, i.e. the canonical names
#: stored in `model_instances.model_type`.
MODEL_COVARIATE_SUPPORT: Dict[str, Tuple[bool, bool]] = {
    # Torch sequence models
    "BlockRNN":     (True,  False),   # past only
    "RNN":          (False, True),    # future only — the asymmetry above
    "TCN":          (True,  False),
    "Transformer":  (True,  False),
    "NBeats":       (True,  False),
    "NHits":        (True,  False),
    "TFT":          (True,  True),
    "DLinear":      (True,  True),
    "NLinear":      (True,  True),
    "TiDE":         (True,  True),
    # Regression models — all take both, plus lags
    "XGBoost":      (True,  True),
    "LightGBM":     (True,  True),
    "RandomForest": (True,  True),
    "CatBoost":     (True,  True),
}


def covariate_support(model_type: str | None) -> Tuple[bool, bool]:
    """`(past, future)` for a canonical model type.

    An unrecognised or missing type returns `(False, False)`. That is the
    conservative direction on purpose: offering a covariate slot the model
    cannot use invites a configuration that silently cannot train, or — for a
    future covariate — one that leaks. Refusing a legitimate slot is visible
    and complainable; permitting an illegitimate one is not.
    """
    if not model_type:
        return (False, False)
    return MODEL_COVARIATE_SUPPORT.get(model_type.strip(), (False, False))


#: `tbl_model_field` (seeded in `main.py`) offers a "Use past covariates" /
#: "Use future covariates" CHECKBOX per model type, and it disagrees with the
#: table above for five types: it offers BOTH kinds for BlockRNN, RNN, TCN and
#: Transformer, and omits TiDE entirely. Those are config form fields rather
#: than capability truth, and correcting seeded rows needs an idempotent
#: migration, so it is deliberately left to a follow-up rather than folded in
#: here. Recorded so the disagreement is not discovered a third time.
SEED_DISAGREEMENTS = ("BlockRNN", "RNN", "TCN", "Transformer", "TiDE")
