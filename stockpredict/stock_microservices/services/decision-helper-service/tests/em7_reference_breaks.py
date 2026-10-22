"""EM-7 H-T8 helper — run analysis-service's shipped detect_breaks.

Invoked as a SUBPROCESS by `tests/test_level_breaks.py`, never imported.

Both services define a top-level `app` package, so putting analysis-service on
`sys.path` inside the test session would shadow decision-helper's own `app`
and corrupt every test after it. A subprocess is the only way to compare the
two implementations without that risk.

Reads a JSON job on stdin, writes a JSON break list on stdout.
"""
from __future__ import annotations

import json
import os
import sys


def main() -> None:
    job = json.load(sys.stdin)
    sys.path.insert(0, os.path.abspath(job["service_path"]))

    import pandas as pd

    from app.services.sr_volume import detect_breaks  # analysis-service's

    frame = pd.DataFrame(job["bars"])
    atr = pd.Series(job["atr"], dtype=float)
    breaks = detect_breaks(
        frame,
        level_price=job["level_price"],
        first_bar=job["first_bar"],
        declared_type=job["declared_type"],
        atr=atr,
    )
    json.dump(
        [{"direction": b.direction, "bar_index": b.bar_index} for b in breaks],
        sys.stdout,
    )


if __name__ == "__main__":
    main()
