"""F-026 — Position state machine (Schwager Ch 8, 14).

Per (user, ticker) the position is always in one of three states:
    FLAT   — no open position
    LONG   — long position open
    SHORT  — short position open (or "short-bias" for VN cash markets)

v1 constraint: LONG → SHORT must pass through FLAT.
A reversal fires action=REVERSE and sets state_after=FLAT.
The opposite-direction entry is triggered on the next orchestrator call
once the position has been confirmed closed.

Stop / target hit detection:
    LONG:  stop_hit  when close ≤ current_stop
           target_hit when close ≥ current_target
    SHORT: stop_hit  when close ≥ current_stop
           target_hit when close ≤ current_target
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class StateTransition:
    """Output of next_state() for a single bar."""
    action: str              # BUY | SELL | SELL_SHORT | COVER | HOLD | WAIT | REVERSE
    state_before: str        # FLAT | LONG | SHORT
    state_after: str         # FLAT | LONG | SHORT
    entry_price: Optional[float] = None   # set when opening a new leg
    exit_price: Optional[float] = None    # set when closing
    reason: str = ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def next_state(
    current_state: str,
    signal_direction: Optional[str],
    current_close: float,
    current_stop: Optional[float],
    current_target: Optional[float],
    signal_confirmed: bool = False,
) -> StateTransition:
    """Determine the action and next state for one bar.

    Args:
        current_state:     "FLAT" | "LONG" | "SHORT".
        signal_direction:  "LONG" | "SHORT" | None (no confirmed signal).
        current_close:     Bar close price (used for stop/target check and entry price).
        current_stop:      Active stop price (None when FLAT).
        current_target:    Active target price (None when FLAT).
        signal_confirmed:  True only when the best signal passed the confirmation layer.
    """
    stop_hit, target_hit = _check_exits(
        current_state, current_close, current_stop, current_target
    )

    if current_state == "FLAT":
        return _from_flat(signal_direction, current_close, signal_confirmed)

    if current_state == "LONG":
        return _from_long(
            signal_direction, current_close,
            current_stop, current_target,
            stop_hit, target_hit, signal_confirmed,
        )

    if current_state == "SHORT":
        return _from_short(
            signal_direction, current_close,
            current_stop, current_target,
            stop_hit, target_hit, signal_confirmed,
        )

    # Unrecognised state — passthrough WAIT
    return StateTransition(
        action="WAIT",
        state_before=current_state,
        state_after=current_state,
        reason=f"Unrecognised state '{current_state}' — no action",
    )


# ---------------------------------------------------------------------------
# Branch helpers
# ---------------------------------------------------------------------------

def _from_flat(
    signal_direction: Optional[str],
    close: float,
    confirmed: bool,
) -> StateTransition:
    if signal_direction == "LONG" and confirmed:
        return StateTransition(
            action="BUY",
            state_before="FLAT",
            state_after="LONG",
            entry_price=close,
            reason="Confirmed LONG signal — entering LONG",
        )
    if signal_direction == "SHORT" and confirmed:
        return StateTransition(
            action="SELL_SHORT",
            state_before="FLAT",
            state_after="SHORT",
            entry_price=close,
            reason="Confirmed SHORT signal — entering SHORT",
        )
    return StateTransition(
        action="WAIT",
        state_before="FLAT",
        state_after="FLAT",
        reason="No confirmed signal — remaining FLAT",
    )


def _from_long(
    signal_direction: Optional[str],
    close: float,
    current_stop: Optional[float],
    current_target: Optional[float],
    stop_hit: bool,
    target_hit: bool,
    confirmed: bool,
) -> StateTransition:
    if stop_hit:
        return StateTransition(
            action="SELL",
            state_before="LONG",
            state_after="FLAT",
            exit_price=current_stop,
            reason=f"Stop triggered at {current_stop:.4f} — exiting LONG",
        )
    if target_hit:
        return StateTransition(
            action="SELL",
            state_before="LONG",
            state_after="FLAT",
            exit_price=current_target,
            reason=f"Target reached at {current_target:.4f} — exiting LONG",
        )
    if signal_direction == "SHORT" and confirmed:
        # v1: reverse through FLAT; SHORT entry fires next bar
        return StateTransition(
            action="REVERSE",
            state_before="LONG",
            state_after="FLAT",
            exit_price=close,
            reason="Reversal: confirmed SHORT signal while LONG — closing position "
                   "(SHORT entry will trigger on next bar)",
        )
    return StateTransition(
        action="HOLD",
        state_before="LONG",
        state_after="LONG",
        reason="Holding LONG — no exit trigger fired",
    )


def _from_short(
    signal_direction: Optional[str],
    close: float,
    current_stop: Optional[float],
    current_target: Optional[float],
    stop_hit: bool,
    target_hit: bool,
    confirmed: bool,
) -> StateTransition:
    if stop_hit:
        return StateTransition(
            action="COVER",
            state_before="SHORT",
            state_after="FLAT",
            exit_price=current_stop,
            reason=f"Stop triggered at {current_stop:.4f} — covering SHORT",
        )
    if target_hit:
        return StateTransition(
            action="COVER",
            state_before="SHORT",
            state_after="FLAT",
            exit_price=current_target,
            reason=f"Target reached at {current_target:.4f} — covering SHORT",
        )
    if signal_direction == "LONG" and confirmed:
        return StateTransition(
            action="REVERSE",
            state_before="SHORT",
            state_after="FLAT",
            exit_price=close,
            reason="Reversal: confirmed LONG signal while SHORT — covering position "
                   "(LONG entry will trigger on next bar)",
        )
    return StateTransition(
        action="HOLD",
        state_before="SHORT",
        state_after="SHORT",
        reason="Holding SHORT — no exit trigger fired",
    )


def _check_exits(
    state: str,
    close: float,
    stop: Optional[float],
    target: Optional[float],
) -> tuple[bool, bool]:
    """Return (stop_hit, target_hit) for the current bar."""
    if state == "LONG":
        return (
            bool(stop and close <= stop),
            bool(target and close >= target),
        )
    if state == "SHORT":
        return (
            bool(stop and close >= stop),
            bool(target and close <= target),
        )
    return False, False
