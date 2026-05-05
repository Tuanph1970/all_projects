"""
Chapter 9 — Concept 5: Flag / Pennant Stop
Place the stop at the opposite end of the consolidation pattern.
Returns to that end invalidate the continuation premise.
"""
from dataclasses import dataclass


@dataclass
class FlagStop:
    flag_high: float
    flag_low: float
    flagpole_start: float
    flagpole_top: float

    def is_valid_flag(self) -> bool:
        pole = self.flagpole_top - self.flagpole_start
        retracement = self.flagpole_top - self.flag_low
        return 0 < retracement / pole < 0.50    # < 50% retrace

    def upside_entry(self) -> float:
        return self.flag_high * 1.001

    def upside_stop(self) -> float:
        return self.flag_low * 0.999

    def risk_per_share(self) -> float:
        return self.upside_entry() - self.upside_stop()


if __name__ == "__main__":
    f = FlagStop(flag_high=40.0, flag_low=38.5,
                 flagpole_start=30.0, flagpole_top=40.0)
    if f.is_valid_flag():
        print(f"Entry      : ${f.upside_entry():.2f}")
        print(f"Stop       : ${f.upside_stop():.2f}")
        print(f"Risk/share : ${f.risk_per_share():.2f}")
    else:
        print("Not a healthy flag; skip the trade.")
