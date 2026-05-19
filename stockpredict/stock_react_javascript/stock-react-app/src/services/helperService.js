// F-030 — Decision Helper Service API client
import httpClient from './httpClient';
import { API_ENDPOINTS } from '../constants/api';

class HelperService {

  // Run the full decision pipeline for one (ticker, bar_date)
  async recommend({ ticker, barDate, trigger = 'ON_DEMAND' }) {
    return await httpClient.post(API_ENDPOINTS.HELPER_RECOMMEND, {
      ticker,
      bar_date: barDate,
      trigger,
    });
  }

  // Run only signal analysis (Phase B endpoint, no DB write)
  async signalAnalysis({ ticker, barDate, fastMa = 10, slowMa = 50, breakoutN = 20, kDelay = 1 }) {
    return await httpClient.post(API_ENDPOINTS.HELPER_SIGNAL_ANALYSIS, {
      ticker,
      bar_date: barDate,
      fast_ma: fastMa,
      slow_ma: slowMa,
      breakout_n: breakoutN,
      k_delay: kDelay,
    });
  }

  // Get current position state for (user, ticker)
  async getPosition(ticker) {
    return await httpClient.get(API_ENDPOINTS.HELPER_POSITION(ticker));
  }

  // Get user risk preferences
  async getRiskPrefs() {
    return await httpClient.get(API_ENDPOINTS.HELPER_RISK_PREFS);
  }

  // Save / update user risk preferences
  async saveRiskPrefs({ accountEquity, riskPerTradePct, maxConcurrentPositions,
                        maxCorrelation, lossStreakSizeCut, lossStreakThreshold }) {
    return await httpClient.put(API_ENDPOINTS.HELPER_RISK_PREFS, {
      account_equity: accountEquity,
      risk_per_trade_pct: riskPerTradePct,
      max_concurrent_positions: maxConcurrentPositions,
      max_correlation: maxCorrelation,
      loss_streak_size_cut: lossStreakSizeCut,
      loss_streak_threshold: lossStreakThreshold,
    });
  }

  // F-060..F-065 — Discipline overlay
  async getDisciplineSummary() {
    return await httpClient.get(API_ENDPOINTS.HELPER_DISCIPLINE_SUMMARY);
  }

  async validatePlan({ ticker, action, stopPrice, targetPrice, entryPrice, direction, regime }) {
    return await httpClient.post(API_ENDPOINTS.HELPER_VALIDATE_PLAN, {
      ticker,
      action,
      stop_price: stopPrice,
      target_price: targetPrice,
      entry_price: entryPrice,
      direction,
      regime,
    });
  }

  // F-070 — HelperWatchlist CRUD
  async getWatchlist() {
    return await httpClient.get(API_ENDPOINTS.HELPER_WATCHLIST);
  }

  async addWatchlist({ ticker, note }) {
    return await httpClient.post(API_ENDPOINTS.HELPER_WATCHLIST, { ticker, note });
  }

  async removeWatchlist(ticker) {
    return await httpClient.delete(API_ENDPOINTS.HELPER_WATCHLIST_ITEM(ticker));
  }

  // F-071 — Manual trigger of scheduled run for the current user
  async triggerScheduledRun() {
    return await httpClient.post(API_ENDPOINTS.HELPER_WATCHLIST_RUN_ALL);
  }

  // F-073 — Scheduled runs log
  async getScheduledRuns({ limit = 50, alertsOnly = false } = {}) {
    const params = new URLSearchParams({ limit, alerts_only: alertsOnly });
    return await httpClient.get(`${API_ENDPOINTS.HELPER_SCHEDULED_RUNS}?${params}`);
  }

  // F-083 — Seed alert history from REST (called on mount before SSE connects)
  async getAlerts(limit = 20) {
    return await httpClient.get(`${API_ENDPOINTS.HELPER_ALERTS}?limit=${limit}`);
  }

  // F-100 — Fetch ai-insights pattern overlay for a symbol
  async getPatterns(symbol, lookbackBars = 100) {
    return await httpClient.get(
      `${API_ENDPOINTS.AI_PATTERNS(symbol)}?lookback_bars=${lookbackBars}`
    );
  }

  // F-050..F-054 — Run backtest / walk-forward harness
  async runBacktest({
    ticker, startDate, endDate,
    initialEquity = 100000, riskPerTradePct = 1.0,
    fastMa = 10, slowMa = 50, breakoutN = 20, kDelay = 1,
    slippageBps = 5.0, commission = 10.0,
    walkForward = false, wfWindowDays = 90,
  }) {
    return await httpClient.post(API_ENDPOINTS.HELPER_BACKTEST, {
      ticker,
      start_date: startDate,
      end_date: endDate,
      initial_equity: initialEquity,
      risk_per_trade_pct: riskPerTradePct,
      fast_ma: fastMa,
      slow_ma: slowMa,
      breakout_n: breakoutN,
      k_delay: kDelay,
      slippage_bps: slippageBps,
      commission,
      walk_forward: walkForward,
      wf_window_days: wfWindowDays,
    });
  }
}

const helperService = new HelperService();
export default helperService;
