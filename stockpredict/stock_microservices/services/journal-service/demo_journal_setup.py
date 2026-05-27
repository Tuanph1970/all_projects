"""
demo_journal_setup.py
=====================
Creates a complete demo Journal setup for tuanph1970@gmail.com:
  - 1 trading account (VND, 500M starting equity)
  - 5 trading rules (Risk / Entry / Exit / Psychology)
  - 3 closed trades (ACB LONG win, VHM LONG loss, FPT LONG win)
  - 1 open trade  (HPG LONG, still running)
  - Diary notes for each closed trade
  - 1 daily plan (today's pre-market checklist)
  - 1 weekly review (last week)
  - Equity snapshots to populate the equity-curve chart

Usage:
  python demo_journal_setup.py                          # default gateway port 18004
  python demo_journal_setup.py --base http://host:8004  # custom gateway

Run from anywhere; no extra dependencies beyond the stdlib + requests.
"""

import argparse
import json
import sys
from datetime import date, timedelta

try:
    import requests
except ImportError:
    sys.exit("Install requests first:  pip install requests")

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="Populate demo Journal data")
parser.add_argument("--base", default="http://localhost:18004/stock_helper/api/v2",
                    help="API gateway base URL (default: http://localhost:18004/stock_helper/api/v2)")
parser.add_argument("--email", default="tuanph1970@gmail.com")
parser.add_argument("--password", default="Tuan@1234")
parser.add_argument("--clean", action="store_true",
                    help="Delete the demo account before re-creating (idempotent re-run)")
args = parser.parse_args()

BASE   = args.base.rstrip("/")
AUTH   = f"{BASE}/auth"
JRNL   = f"{BASE}/journal"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
session = requests.Session()


def ok(r, label):
    if r.status_code not in (200, 201, 202, 204):
        print(f"  ✗ {label}: HTTP {r.status_code}  {r.text[:200]}")
        sys.exit(1)
    print(f"  ✓ {label}")
    return r.json() if r.text else {}


def days_ago(n):
    return (date.today() - timedelta(days=n)).isoformat()


def last_monday():
    today = date.today()
    return (today - timedelta(days=today.weekday() + 7)).isoformat()


# ---------------------------------------------------------------------------
# 1. Login
# ---------------------------------------------------------------------------
print("\n── Step 1: Login ────────────────────────────────────────────")
r = session.post(f"{AUTH}/login", json={"email": args.email, "password": args.password})
token = ok(r, f"Login as {args.email}")["access_token"]
session.headers["Authorization"] = f"Bearer {token}"

# ---------------------------------------------------------------------------
# 2. Optional clean: delete existing demo account
# ---------------------------------------------------------------------------
if args.clean:
    print("\n── Step 2: Cleanup ──────────────────────────────────────────")
    accounts = session.get(f"{JRNL}/accounts").json()
    for acc in accounts:
        if acc["account_name"] == "Demo VND Account":
            session.delete(f"{JRNL}/accounts/{acc['id']}")
            print(f"  ✓ Deleted old demo account (id={acc['id']})")

# ---------------------------------------------------------------------------
# 3. Create account
# ---------------------------------------------------------------------------
print("\n── Step 3: Create journal account ───────────────────────────")
r = session.post(f"{JRNL}/accounts", json={
    "account_name":       "Demo VND Account",
    "starting_equity":    500_000_000,
    "currency":           "VND",
    "max_risk_per_trade": 2.0,
    "max_cumulative_risk": 20.0,
})
account = ok(r, "Create account 'Demo VND Account' — 500M VND, 2% risk/trade")
acct_id = account["id"]

# ---------------------------------------------------------------------------
# 4. Add trading rules
# ---------------------------------------------------------------------------
print("\n── Step 4: Add trading rules ────────────────────────────────")
rules = [
    ("Risk",       "Never risk more than 2% of account equity on a single trade"),
    ("Risk",       "Cut losses immediately if the daily loss limit (5%) is hit"),
    ("Entry",      "Only enter on confirmed signals — no anticipation trades"),
    ("Exit",       "Let winners run to the target; do not exit early from emotion"),
    ("Psychology", "No revenge trading after a loss — wait for the next clean setup"),
]
for category, text in rules:
    r = session.post(f"{JRNL}/accounts/{acct_id}/rules",
                     json={"rule_text": text, "category": category, "sort_order": 0})
    ok(r, f"Rule [{category}]: {text[:55]}…")

# ---------------------------------------------------------------------------
# 5. Create trades
# ---------------------------------------------------------------------------
print("\n── Step 5: Create trades ────────────────────────────────────")

# Trade A — ACB LONG, closed WIN
r = session.post(f"{JRNL}/accounts/{acct_id}/trades", json={
    "entry_date":    days_ago(30),
    "market_ticker": "ACB",
    "direction":     "Long",
    "entry_price":   22_000,
    "entry_type":    "Stop",
    "initial_stop":  20_500,
    "position_size": 10_000,
    "commission":    25_000,
    "objective_1":   25_000,
    "objective_2":   27_000,
    "entry_reason":  "MA-cross breakout above 50-day SMA with strong volume",
})
trade_a = ok(r, "Trade A: ACB LONG entry @ 22,000 (10,000 shares)")
tid_a = trade_a["id"]

r = session.post(f"{JRNL}/accounts/{acct_id}/trades/{tid_a}/close",
                 params={"exit_price": 25_200, "exit_date": days_ago(15),
                         "exit_reason": "Target 1 reached; partial exit at objective_1"})
ok(r, "  → Close ACB @ 25,200 (WIN +3,200/share)")

# Trade B — VHM LONG, closed LOSS
r = session.post(f"{JRNL}/accounts/{acct_id}/trades", json={
    "entry_date":    days_ago(20),
    "market_ticker": "VHM",
    "direction":     "Long",
    "entry_price":   44_500,
    "entry_type":    "Limit",
    "initial_stop":  42_000.0,
    "position_size": 5_000,
    "commission":    15_000,
    "objective_1":   50_000,
    "entry_reason":  "Support bounce at 200-day SMA, low RSI oversold",
})
trade_b = ok(r, "Trade B: VHM LONG entry @ 44,500 (5,000 shares)")
tid_b = trade_b["id"]

r = session.post(f"{JRNL}/accounts/{acct_id}/trades/{tid_b}/stop",
                 json={"new_stop": 43_000, "reason": "Tightened after small rebound"})
ok(r, "  → Revise VHM stop 42,000 → 43,000")

r = session.post(f"{JRNL}/accounts/{acct_id}/trades/{tid_b}/close",
                 params={"exit_price": 42_800, "exit_date": days_ago(14),
                         "exit_reason": "Stop hit — support broke on news"})
ok(r, "  → Close VHM @ 42,800 (LOSS −1,700/share)")

# Trade C — FPT LONG, closed WIN
r = session.post(f"{JRNL}/accounts/{acct_id}/trades", json={
    "entry_date":    days_ago(25),
    "market_ticker": "FPT",
    "direction":     "Long",
    "entry_price":   115_000,
    "entry_type":    "Market",
    "initial_stop":  108_000,
    "position_size": 2_000,
    "commission":    15_000,
    "objective_1":   128_000,
    "objective_2":   140_000,
    "entry_reason":  "Mid-trend continuation — higher highs, 20/50 SMA fanned",
})
trade_c = ok(r, "Trade C: FPT LONG entry @ 115,000 (2,000 shares)")
tid_c = trade_c["id"]

r = session.post(f"{JRNL}/accounts/{acct_id}/trades/{tid_c}/close",
                 params={"exit_price": 130_000, "exit_date": days_ago(7),
                         "exit_reason": "Target 1 cleared; locked in profit"})
ok(r, "  → Close FPT @ 130,000 (WIN +15,000/share)")

# Trade D — HPG LONG, OPEN (still running)
r = session.post(f"{JRNL}/accounts/{acct_id}/trades", json={
    "entry_date":    days_ago(5),
    "market_ticker": "HPG",
    "direction":     "Long",
    "entry_price":   28_000,
    "entry_type":    "Stop",
    "initial_stop":  26_500,
    "position_size": 8_000,
    "commission":    20_000,
    "objective_1":   32_000,
    "objective_2":   36_000,
    "entry_reason":  "N-day breakout above 30-day high on expanding volume",
})
trade_d = ok(r, "Trade D: HPG LONG entry @ 28,000 (8,000 shares) — OPEN")
tid_d = trade_d["id"]

# ---------------------------------------------------------------------------
# 6. Diary notes for closed trades
# ---------------------------------------------------------------------------
print("\n── Step 6: Add trade diary notes ────────────────────────────")

# ACB diary
r = session.post(f"{JRNL}/trades/{tid_a}/diary", json={
    "reasons_for_trade":   "Strong MA-cross, confirmed by volume surge >150% avg",
    "chart_pattern":       "Breakout",
    "emotional_state_entry": "Confident",
})
ok(r, "Diary for ACB — entry notes + emotion (Confident)")
diary_a = r.json()
r = session.put(f"{JRNL}/trades/{tid_a}/diary", json={
    "how_it_turned_out":   "Textbook breakout; price never looked back, hit T1 clean",
    "lessons_and_mistakes": "Should have sized up — signal was high conviction",
    "emotional_state_during": "Calm",
    "emotional_state_exit": "Confident",
})
ok(r, "Diary for ACB — exit notes + lessons")

# VHM diary
r = session.post(f"{JRNL}/trades/{tid_b}/diary", json={
    "reasons_for_trade":   "Oversold bounce at key support — looked low risk",
    "chart_pattern":       "Breakdown",
    "emotional_state_entry": "Anxious",
})
ok(r, "Diary for VHM — entry notes + emotion (Anxious)")
r = session.put(f"{JRNL}/trades/{tid_b}/diary", json={
    "how_it_turned_out":   "Support failed on unexpected sector news; stop hit correctly",
    "lessons_and_mistakes": "Entry was premature — should have waited for confirmation candle. Anxious feeling was a warning sign.",
    "emotional_state_during": "Fearful",
    "emotional_state_exit": "Frustrated",
})
ok(r, "Diary for VHM — exit notes + lessons")

# FPT diary
r = session.post(f"{JRNL}/trades/{tid_c}/diary", json={
    "reasons_for_trade":   "Clear mid-trend: 20/50 SMA fanned, price above both, no supply zone overhead",
    "chart_pattern":       "Breakout",
    "emotional_state_entry": "Calm",
})
ok(r, "Diary for FPT — entry notes + emotion (Calm)")
r = session.put(f"{JRNL}/trades/{tid_c}/diary", json={
    "how_it_turned_out":   "Steady climb to T1; took profit there as volume faded",
    "lessons_and_mistakes": "Could trail stop to lock in more if volume confirms continuation",
    "emotional_state_during": "Calm",
    "emotional_state_exit": "Confident",
})
ok(r, "Diary for FPT — exit notes + lessons")

# ---------------------------------------------------------------------------
# 7. Daily planning — today's pre-market checklist
# ---------------------------------------------------------------------------
print("\n── Step 7: Today's daily plan ───────────────────────────────")
r = session.post(f"{JRNL}/accounts/{acct_id}/plans", json={
    "plan_date": date.today().isoformat(),
    "market_review": (
        "VN-Index held above 1,250 support yesterday with above-average volume. "
        "Banking and steel sectors showing relative strength. "
        "US markets closed flat — no major macro headwind overnight."
    ),
    "new_trade_ideas": (
        "HPG: already long, watching for break of 29,500 to trail stop to breakeven.\n"
        "MBB: building base near 20-day SMA — set alert at 24,800 for breakout entry.\n"
        "SSI: avoid — sector rotation risk, volume declining."
    ),
    "stop_objective_updates": (
        "HPG (open): raise stop from 26,500 → 27,200 if daily close above 29,000."
    ),
    "emotional_checkin": (
        "Feeling focused and patient. No need to force trades today — "
        "let HPG work and wait for MBB setup to mature."
    ),
})
ok(r, f"Daily plan for {date.today().isoformat()}")

# ---------------------------------------------------------------------------
# 8. Weekly review — last week
# ---------------------------------------------------------------------------
print("\n── Step 8: Last week's review ───────────────────────────────")
r = session.post(f"{JRNL}/accounts/{acct_id}/reviews", json={
    "week_start": last_monday(),
    "what_went_well": (
        "FPT trade executed cleanly — entry at right moment, held without tinkering.\n"
        "Followed the daily plan every morning; no impulsive trades."
    ),
    "what_went_wrong": (
        "VHM entry was premature. Entered on support 'hope' rather than confirmed bounce.\n"
        "Felt anxious at entry — that was a signal to wait, not enter."
    ),
    "key_adjustments": (
        "1. Only enter breakouts/bounces after a confirmed close above the trigger level.\n"
        "2. If emotional state at entry is Anxious, reduce size by 50% or skip.\n"
        "3. Always check sector context before entering a reversal trade."
    ),
})
review = ok(r, f"Weekly review for week of {last_monday()}")
rid = review["id"]

# Recalculate stats from actual trade data
r = session.post(f"{JRNL}/accounts/{acct_id}/reviews/{rid}/recalculate")
ok(r, "  → Recalculate weekly P&L + win rate from trade data")

# ---------------------------------------------------------------------------
# 9. Equity snapshots (to draw the equity curve)
# ---------------------------------------------------------------------------
print("\n── Step 9: Equity snapshots ─────────────────────────────────")
# Simulate equity growing from 500M → ~534M across the last 30 days
snapshots = [
    (days_ago(30), 500_000_000),
    (days_ago(25), 498_500_000),   # small drawdown before FPT entry
    (days_ago(20), 501_000_000),   # FPT starts gaining
    (days_ago(15), 530_000_000),   # ACB closed WIN
    (days_ago(14), 521_500_000),   # VHM closed LOSS
    (days_ago(7),  549_500_000),   # FPT closed WIN
    (days_ago(5),  548_000_000),   # HPG opened (commission hit)
    (date.today().isoformat(), 552_000_000),  # HPG floating gain
]
for snap_date, equity in snapshots:
    r = session.post(
        f"{JRNL}/accounts/{acct_id}/equity",
        params={"snapshot_date": snap_date, "equity_value": equity, "open_trade_equity": 0},
    )
    ok(r, f"Snapshot {snap_date}: {equity:,.0f} VND")

# Update current_equity on the account to match latest snapshot
r = session.put(f"{JRNL}/accounts/{acct_id}", json={"current_equity": 552_000_000})
ok(r, "Updated account current_equity → 552,000,000 VND")

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
print(f"""
╔══════════════════════════════════════════════════════════════════╗
║  Demo journal setup complete                                     ║
╠══════════════════════════════════════════════════════════════════╣
║  Account  : Demo VND Account  (id = {acct_id:<4})                     ║
║  Equity   : 500,000,000 → 552,000,000 VND  (+10.4%)            ║
║  Trades   : ACB ✓WIN  VHM ✗LOSS  FPT ✓WIN  HPG OPEN           ║
║  Rules    : 5 (Risk ×2, Entry, Exit, Psychology)                 ║
║  Diary    : 3 closed trades fully annotated                      ║
║  Daily plan  : {date.today().isoformat()}                              ║
║  Weekly review: {last_monday()} + stats recalculated          ║
║  Equity snapshots: 8 data points (last 30 days)                  ║
╠══════════════════════════════════════════════════════════════════╣
║  Open in browser → Journal > Dashboard  (select the account)    ║
║  Re-run with --clean to wipe and recreate cleanly               ║
╚══════════════════════════════════════════════════════════════════╝
""")
