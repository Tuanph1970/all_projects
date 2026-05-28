"""
Playwright Demo — Trader Journal
=================================
Full end-to-end walkthrough of the Journal Trader feature:
  1. Login (or register a demo account on first run)
  2. Journal Accounts   — create an account with risk rules
  3. Daily Planning     — write today's pre-market plan
  4. Trade Log          — add a Long trade, then close it profitably
  5. Trade Diary        — attach notes and chart pattern to the trade
  6. Weekly Review      — reflect on the week
  7. Journal Dashboard  — inspect equity curve and stats

Usage:
    python playwright_demos/journal_trader_demo.py

Optional env vars:
    DEMO_USERNAME   (default: demo_trader)
    DEMO_PASSWORD   (default: Demo1234!)
    DEMO_EMAIL      (default: demo@stockhelper.local)
    APP_URL         (default: http://localhost:3004/stock-app/)
    HEADLESS        (default: false  — set to "true" to run headless)
    SLOW_MO_MS      (default: 600   — milliseconds between actions)

Screenshots are saved to playwright_demos/screenshots/.
"""

import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
USERNAME   = os.getenv("DEMO_USERNAME", "demo_trader")
PASSWORD   = os.getenv("DEMO_PASSWORD", "Demo1234!")
EMAIL      = os.getenv("DEMO_EMAIL",    "demo@stockhelper.local")
APP_URL    = os.getenv("APP_URL",       "http://localhost:3004/stock-app/")
HEADLESS   = os.getenv("HEADLESS", "false").lower() == "true"
SLOW_MO    = int(os.getenv("SLOW_MO_MS", "600"))

SCREENSHOT_DIR = Path(__file__).parent / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

TODAY      = date.today().isoformat()            # YYYY-MM-DD
MONDAY     = (date.today() - timedelta(days=date.today().weekday())).isoformat()

# ---------------------------------------------------------------------------
# Demo data
# ---------------------------------------------------------------------------
ACCOUNT_NAME      = "Demo SSI 2024"
STARTING_EQUITY   = "500000000"   # 500 triệu VND
TICKER            = "VNM"
ENTRY_PRICE       = "78500"
INITIAL_STOP      = "76000"
POSITION_SIZE     = "1000"
COMMISSION        = "75000"
OBJECTIVE_1       = "83000"
OBJECTIVE_2       = "87000"
ENTRY_REASON      = (
    "VNM tạo đáy thứ 2 trên vùng hỗ trợ 76,000, khối lượng co lại, "
    "MA20 đang phẳng — mua breakout tháng 3."
)
EXIT_PRICE        = "83500"       # closed at objective-1
EXIT_REASON       = "Đạt mục tiêu 1, cổ phiếu gặp kháng cự vùng 83,000–84,000."
DAILY_MARKET      = (
    "VN-Index vẫn nằm trên MA50. Nhóm tiêu dùng — thực phẩm dẫn đầu. "
    "Thanh khoản ổn định ~15,000 tỷ. Xu hướng ngắn hạn bullish."
)
DAILY_IDEAS       = "VNM: breakout mô hình 2 đáy; VIC: theo dõi đột phá kháng cự 52,000."
WEEKLY_WELL       = "Tuân thủ stop loss; không chase breakout muộn; ghi chép đầy đủ."
WEEKLY_WRONG      = "Vào lệnh hơi sớm trên VNM, chưa chờ xác nhận nến chốt tuần."
WEEKLY_ADJ        = "Chờ close tuần trên vùng breakout trước khi vào lệnh ngày thứ 2."
DIARY_ANALYSIS    = (
    "VNM tạo đáy đôi ở 75,800 và 76,200. Nến hammer tuần trước trên MA50 "
    "là tín hiệu tốt. Khối lượng ngày vào 120% trung bình 20 ngày — xác nhận lực cầu."
)
DIARY_LESSONS     = (
    "Cần kiên nhẫn hơn — có thể chờ đến ngày 2 để thấy follow-through. "
    "Tuy nhiên risk/reward ≥ 2:1 nên quyết định vào lệnh là hợp lý."
)
TRADING_RULE      = "Không vào lệnh mới khi thị trường đang trong downtrend rõ ràng (VN-Index < MA200)"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_step = 0
def step(msg: str):
    global _step
    _step += 1
    print(f"\n{'='*60}")
    print(f"  STEP {_step}: {msg}")
    print(f"{'='*60}")


def screenshot(page, name: str):
    path = SCREENSHOT_DIR / f"{_step:02d}_{name}.png"
    page.screenshot(path=str(path))
    print(f"  📸  {path.name}")


def nav_to_journal(page, submenu_text: str):
    """Open the Journal sidebar group then click a submenu item."""
    journal_btn = page.locator("button.nav-button", has_text="Nhật ký giao dịch")

    # Expand if the submenu is not yet visible
    if not page.locator("button.nav-submenu-item").first.is_visible():
        journal_btn.click()
        page.wait_for_timeout(400)

    page.locator("button.nav-submenu-item", has_text=submenu_text).click()
    page.wait_for_timeout(800)


def wait_for_network(page, timeout=8000):
    """Wait for in-flight XHR/fetch to settle."""
    page.wait_for_load_state("networkidle", timeout=timeout)


# ---------------------------------------------------------------------------
# Main demo
# ---------------------------------------------------------------------------

def run(playwright):
    print("\n" + "="*60)
    print("  JOURNAL TRADER — PLAYWRIGHT DEMO")
    print(f"  App : {APP_URL}")
    print(f"  User: {USERNAME}")
    print("="*60)

    browser = playwright.chromium.launch(
        headless=HEADLESS,
        slow_mo=SLOW_MO,
        args=["--start-maximized"],
    )
    context = browser.new_context(
        viewport={"width": 1440, "height": 900},
        record_video_dir=str(SCREENSHOT_DIR),
        record_video_size={"width": 1440, "height": 900},
    )
    page = context.new_page()

    try:
        # ------------------------------------------------------------------ #
        # 1. Open the app
        # ------------------------------------------------------------------ #
        step("Open the app")
        page.goto(APP_URL, wait_until="domcontentloaded", timeout=20_000)
        page.wait_for_timeout(1500)
        screenshot(page, "app_opened")

        # ------------------------------------------------------------------ #
        # 2. Login / Register
        # ------------------------------------------------------------------ #
        step("Login (register on first run)")
        page.wait_for_selector("#lf-username", timeout=10_000)
        page.fill("#lf-username", USERNAME)
        page.fill('input[name="password"]', PASSWORD)
        screenshot(page, "login_filled")
        page.click("button.auth-button")

        # Check if login failed (wrong credentials → try registering)
        page.wait_for_timeout(2000)
        if page.locator("#lf-username").is_visible():
            print("  → Login failed. Registering demo account…")
            page.click("text=Đăng ký")  # switch to register tab
            page.wait_for_timeout(500)
            page.fill("#lf-username", USERNAME)
            page.fill('input[name="email"]', EMAIL)
            page.fill('input[name="password"]', PASSWORD)
            page.fill('input[name="confirmPassword"]', PASSWORD)
            screenshot(page, "register_filled")
            page.click("button.auth-button")
            page.wait_for_timeout(2500)
            # Now login with the new account
            page.fill("#lf-username", USERNAME)
            page.fill('input[name="password"]', PASSWORD)
            page.click("button.auth-button")
            page.wait_for_timeout(2000)

        # Wait for the main app to load (sidebar should appear)
        page.wait_for_selector("nav", timeout=12_000)
        screenshot(page, "logged_in")
        print(f"  ✓  Logged in as {USERNAME}")

        # ------------------------------------------------------------------ #
        # 3. Journal Accounts — create account + add a trading rule
        # ------------------------------------------------------------------ #
        step("Journal Accounts — create account")
        nav_to_journal(page, "Tài khoản")
        wait_for_network(page)
        screenshot(page, "accounts_page")

        # Click the add / create button — the label differs if no accounts yet
        add_btn = page.locator(
            "button.btn-primary",
            has_text="Tạo tài khoản"
        ).first
        if not add_btn.is_visible():
            add_btn = page.locator("button.btn-primary").first
        add_btn.click()
        page.wait_for_selector(".journal-modal", timeout=5000)
        page.wait_for_timeout(400)

        # Fill in the account form
        page.get_by_placeholder("VD: Tài khoản SSI").fill(ACCOUNT_NAME)
        page.get_by_placeholder("100000000").fill(STARTING_EQUITY)
        # Currency is already VND by default; Max risk defaults 2/25 — leave as-is
        screenshot(page, "account_form_filled")
        page.locator(".journal-modal button.btn-primary").click()
        wait_for_network(page)
        page.wait_for_timeout(800)
        screenshot(page, "account_created")
        print(f"  ✓  Account '{ACCOUNT_NAME}' created")

        # Add a trading rule
        step("Journal Accounts — add a trading rule")
        add_rule_btn = page.locator("button", has_text="Thêm quy tắc").first
        if add_rule_btn.is_visible():
            add_rule_btn.click()
            page.wait_for_timeout(400)
            page.get_by_placeholder("Nhập quy tắc giao dịch...").fill(TRADING_RULE)
            # Category select — keep default "General"
            screenshot(page, "rule_form_filled")
            page.locator("button", has_text="Thêm").last.click()
            wait_for_network(page)
            page.wait_for_timeout(600)
            screenshot(page, "rule_added")
            print("  ✓  Trading rule added")

        # ------------------------------------------------------------------ #
        # 4. Daily Planning — write today's plan
        # ------------------------------------------------------------------ #
        step("Daily Planning — write today's pre-market plan")
        nav_to_journal(page, "Kế hoạch hàng ngày")
        wait_for_network(page)
        page.wait_for_timeout(600)
        screenshot(page, "daily_planning_page")

        # Check if a plan for today already exists
        today_plan_exists = page.locator(".plan-item, .plan-date-tab", has_text=TODAY).is_visible()
        if not today_plan_exists:
            # Open new plan form
            new_plan_btn = page.locator("button", has_text="Kế hoạch").first
            if new_plan_btn.is_visible():
                new_plan_btn.click()
                page.wait_for_timeout(400)

        # Fill plan fields — use get_by_label since labels are adjacent to textareas
        mkt_review = page.locator("textarea").nth(0)
        trade_ideas = page.locator("textarea").nth(1)
        stop_obj    = page.locator("textarea").nth(2)
        emo_checkin = page.locator("textarea").nth(3)

        mkt_review.fill(DAILY_MARKET)
        trade_ideas.fill(DAILY_IDEAS)
        stop_obj.fill("VNM: dời stop lên 78,000 nếu giá đóng cửa trên 80,000.")
        emo_checkin.fill("Calm và tự tin. Ngủ đủ giấc, không bị áp lực P&L.")
        screenshot(page, "daily_plan_filled")

        save_btn = page.locator("button", has_text="Lưu").first
        save_btn.click()
        wait_for_network(page)
        page.wait_for_timeout(800)
        screenshot(page, "daily_plan_saved")
        print("  ✓  Daily plan saved")

        # ------------------------------------------------------------------ #
        # 5. Trade Log — add a Long trade
        # ------------------------------------------------------------------ #
        step("Trade Log — add a Long trade on VNM")
        nav_to_journal(page, "Sổ giao dịch")
        wait_for_network(page)
        page.wait_for_timeout(600)
        screenshot(page, "trade_log_page")

        # Click "Thêm giao dịch"
        page.locator("button.btn-primary", has_text="Thêm giao dịch").click()
        page.wait_for_selector(".journal-modal-wide", timeout=5000)
        page.wait_for_timeout(400)

        # Entry date defaults to today — leave it
        # Ticker
        page.get_by_placeholder("VD: VNM").fill(TICKER)
        # Direction — Long button (already selected by default)
        long_btn = page.locator("button.direction-btn", has_text="Long")
        if not "active" in (long_btn.get_attribute("class") or ""):
            long_btn.click()

        # Prices
        modal = page.locator(".journal-modal-wide")
        inputs = modal.locator("input[type='number']")
        inputs.nth(0).fill(ENTRY_PRICE)    # Entry price
        inputs.nth(1).fill(INITIAL_STOP)   # Initial stop
        inputs.nth(2).fill(POSITION_SIZE)  # Position size
        inputs.nth(3).fill(COMMISSION)     # Commission
        inputs.nth(4).fill(OBJECTIVE_1)    # Objective 1
        inputs.nth(5).fill(OBJECTIVE_2)    # Objective 2

        # Entry reason
        modal.locator("textarea").fill(ENTRY_REASON)
        page.wait_for_timeout(600)
        screenshot(page, "new_trade_form_filled")

        # Submit
        modal.locator("button.btn-primary").click()
        wait_for_network(page)
        page.wait_for_timeout(1000)
        screenshot(page, "trade_created")
        print(f"  ✓  Long trade on {TICKER} @ {ENTRY_PRICE} created")

        # ------------------------------------------------------------------ #
        # 6. Trade Log — close the trade at target
        # ------------------------------------------------------------------ #
        step("Trade Log — close trade at Objective 1")
        page.wait_for_timeout(500)

        # Click the close (✓) button on the first Open trade row
        close_btn = page.locator("button[title='Đóng lệnh']").first
        close_btn.wait_for(state="visible", timeout=5000)
        close_btn.click()
        page.wait_for_selector(".journal-modal", timeout=5000)
        page.wait_for_timeout(400)

        close_modal = page.locator(".journal-modal")
        close_modal.locator("input[type='number']").fill(EXIT_PRICE)
        # exit date defaults to today — OK
        close_modal.locator("textarea").fill(EXIT_REASON)
        screenshot(page, "close_trade_form")

        close_modal.locator("button.btn-primary").click()
        wait_for_network(page)
        page.wait_for_timeout(1000)
        screenshot(page, "trade_closed")
        print(f"  ✓  Trade closed @ {EXIT_PRICE}  →  R = (83500-78500)/(78500-76000) = +2.0R")

        # ------------------------------------------------------------------ #
        # 7. Trade Diary — attach chart pattern + emotional state + analysis
        # ------------------------------------------------------------------ #
        step("Trade Diary — annotate the closed trade")
        nav_to_journal(page, "Nhật ký")
        wait_for_network(page)
        page.wait_for_timeout(600)
        screenshot(page, "trade_diary_page")

        # Select the trade from the dropdown (first trade)
        trade_select = page.locator("select").first
        if trade_select.is_visible():
            trade_select.select_option(index=0)
            page.wait_for_timeout(600)

        # Select chart pattern — "Double Bottom" (Đáy đôi)
        pattern_select = page.locator("select", has=page.locator("option[value='Double Bottom']"))
        if pattern_select.count() > 0:
            pattern_select.select_option("Double Bottom")

        # Select emotional state — "Confident"
        confident_btn = page.locator("button", has_text="💪")
        if not confident_btn.is_visible():
            confident_btn = page.locator("button", has_text="Confident")
        if confident_btn.count() > 0:
            confident_btn.first.click()

        # Fill analysis and lessons textareas
        textareas = page.locator("textarea")
        if textareas.count() >= 2:
            textareas.nth(0).fill(DIARY_ANALYSIS)
            textareas.nth(1).fill(DIARY_LESSONS)

        screenshot(page, "trade_diary_filled")

        # Save
        save_btn = page.locator("button.btn-primary", has_text="Lưu").first
        if save_btn.is_visible():
            save_btn.click()
            wait_for_network(page)
            page.wait_for_timeout(800)
        screenshot(page, "trade_diary_saved")
        print("  ✓  Trade diary entry saved")

        # ------------------------------------------------------------------ #
        # 8. Weekly Review — reflect on the week
        # ------------------------------------------------------------------ #
        step("Weekly Review — write end-of-week reflection")
        nav_to_journal(page, "Tổng kết tuần")
        wait_for_network(page)
        page.wait_for_timeout(600)
        screenshot(page, "weekly_review_page")

        # Open new review form if no review exists yet
        new_review_btn = page.locator("button", has_text="Tổng kết mới")
        if not new_review_btn.is_visible():
            new_review_btn = page.locator("button.btn-primary").first
        new_review_btn.click()
        page.wait_for_timeout(500)

        # Fill the three reflection fields
        textareas = page.locator("textarea")
        n = textareas.count()
        if n >= 1:
            textareas.nth(0).fill(WEEKLY_WELL)
        if n >= 2:
            textareas.nth(1).fill(WEEKLY_WRONG)
        if n >= 3:
            textareas.nth(2).fill(WEEKLY_ADJ)

        screenshot(page, "weekly_review_filled")

        save_btn = page.locator("button.btn-primary", has_text="Lưu").first
        if save_btn.is_visible():
            save_btn.click()
            wait_for_network(page)
            page.wait_for_timeout(800)
        screenshot(page, "weekly_review_saved")
        print("  ✓  Weekly review saved")

        # ------------------------------------------------------------------ #
        # 9. Journal Dashboard — view analytics
        # ------------------------------------------------------------------ #
        step("Journal Dashboard — view performance analytics")
        nav_to_journal(page, "Tổng quan")
        wait_for_network(page)
        page.wait_for_timeout(1500)   # charts need time to render
        screenshot(page, "dashboard_overview")

        # Scroll down to see all sections
        page.evaluate("window.scrollBy(0, 500)")
        page.wait_for_timeout(800)
        screenshot(page, "dashboard_charts")

        page.evaluate("window.scrollBy(0, 600)")
        page.wait_for_timeout(800)
        screenshot(page, "dashboard_ticker_analysis")

        print("  ✓  Dashboard loaded and captured")

        # ------------------------------------------------------------------ #
        # Done
        # ------------------------------------------------------------------ #
        print("\n" + "="*60)
        print("  DEMO COMPLETE")
        print(f"  {_step} steps, screenshots in: {SCREENSHOT_DIR}")
        print("="*60 + "\n")

        page.wait_for_timeout(2000)

    except PlaywrightTimeoutError as e:
        screenshot(page, "ERROR_timeout")
        print(f"\n  ❌ Timeout: {e}", file=sys.stderr)
        raise
    except Exception as e:
        screenshot(page, "ERROR_unexpected")
        print(f"\n  ❌ Error: {e}", file=sys.stderr)
        raise
    finally:
        context.close()
        browser.close()


def main():
    with sync_playwright() as pw:
        run(pw)


if __name__ == "__main__":
    main()
