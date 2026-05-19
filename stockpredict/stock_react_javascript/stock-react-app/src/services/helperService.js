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
}

const helperService = new HelperService();
export default helperService;
