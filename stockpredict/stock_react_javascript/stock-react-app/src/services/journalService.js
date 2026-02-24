// Journal Service - API calls for Trader Journal module
import httpClient from './httpClient';
import { API_ENDPOINTS } from '../constants/api';

class JournalService {

  // =========================================================================
  // Account Operations
  // =========================================================================

  async getAccounts() {
    return await httpClient.get(API_ENDPOINTS.JOURNAL_ACCOUNTS);
  }

  async getAccount(accountId) {
    return await httpClient.get(API_ENDPOINTS.JOURNAL_ACCOUNT(accountId));
  }

  async createAccount(data) {
    return await httpClient.post(API_ENDPOINTS.JOURNAL_ACCOUNTS, data);
  }

  async updateAccount(accountId, data) {
    return await httpClient.put(API_ENDPOINTS.JOURNAL_ACCOUNT(accountId), data);
  }

  async deleteAccount(accountId) {
    return await httpClient.delete(API_ENDPOINTS.JOURNAL_ACCOUNT(accountId));
  }

  // =========================================================================
  // Trading Rules Operations
  // =========================================================================

  async getRules(accountId, activeOnly = false) {
    const url = `${API_ENDPOINTS.JOURNAL_ACCOUNT_RULES(accountId)}?active_only=${activeOnly}`;
    return await httpClient.get(url);
  }

  async createRule(accountId, data) {
    return await httpClient.post(API_ENDPOINTS.JOURNAL_ACCOUNT_RULES(accountId), data);
  }

  async updateRule(accountId, ruleId, data) {
    return await httpClient.put(API_ENDPOINTS.JOURNAL_ACCOUNT_RULE(accountId, ruleId), data);
  }

  async deleteRule(accountId, ruleId) {
    return await httpClient.delete(API_ENDPOINTS.JOURNAL_ACCOUNT_RULE(accountId, ruleId));
  }

  // =========================================================================
  // Trade Operations
  // =========================================================================

  async getTrades(accountId, { status, ticker, direction, limit = 100, offset = 0 } = {}) {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    if (ticker) params.append('ticker', ticker);
    if (direction) params.append('direction', direction);
    params.append('limit', limit);
    params.append('offset', offset);
    const url = `${API_ENDPOINTS.JOURNAL_ACCOUNT_TRADES(accountId)}?${params.toString()}`;
    return await httpClient.get(url);
  }

  async getTrade(accountId, tradeId) {
    return await httpClient.get(API_ENDPOINTS.JOURNAL_TRADE(accountId, tradeId));
  }

  async createTrade(accountId, data) {
    return await httpClient.post(API_ENDPOINTS.JOURNAL_ACCOUNT_TRADES(accountId), data);
  }

  async updateTrade(accountId, tradeId, data) {
    return await httpClient.put(API_ENDPOINTS.JOURNAL_TRADE(accountId, tradeId), data);
  }

  async closeTrade(accountId, tradeId, exitPrice, exitDate, exitReason) {
    const params = new URLSearchParams();
    params.append('exit_price', exitPrice);
    if (exitDate) params.append('exit_date', exitDate);
    if (exitReason) params.append('exit_reason', exitReason);
    const url = `${API_ENDPOINTS.JOURNAL_TRADE_CLOSE(accountId, tradeId)}?${params.toString()}`;
    return await httpClient.post(url);
  }

  async reviseStop(accountId, tradeId, data) {
    return await httpClient.post(API_ENDPOINTS.JOURNAL_TRADE_STOP(accountId, tradeId), data);
  }

  async deleteTrade(accountId, tradeId) {
    return await httpClient.delete(API_ENDPOINTS.JOURNAL_TRADE(accountId, tradeId));
  }

  async getRiskInfo(accountId) {
    return await httpClient.get(API_ENDPOINTS.JOURNAL_ACCOUNT_RISK(accountId));
  }

  // =========================================================================
  // Diary Operations
  // =========================================================================

  async getDiary(tradeId) {
    return await httpClient.get(API_ENDPOINTS.JOURNAL_TRADE_DIARY(tradeId));
  }

  async createOrGetDiary(tradeId, data = null) {
    return await httpClient.post(API_ENDPOINTS.JOURNAL_TRADE_DIARY(tradeId), data || {});
  }

  async updateDiary(tradeId, data) {
    return await httpClient.put(API_ENDPOINTS.JOURNAL_TRADE_DIARY(tradeId), data);
  }

  async deleteDiary(tradeId) {
    return await httpClient.delete(API_ENDPOINTS.JOURNAL_TRADE_DIARY(tradeId));
  }

  // =========================================================================
  // Diary Chart Operations
  // =========================================================================

  async getDiaryCharts(diaryId) {
    return await httpClient.get(API_ENDPOINTS.JOURNAL_DIARY_CHARTS(diaryId));
  }

  async uploadDiaryChart(diaryId, file, caption = null, chartType = null) {
    const formData = new FormData();
    formData.append('file', file);
    if (caption) formData.append('caption', caption);
    if (chartType) formData.append('chart_type', chartType);

    const token = localStorage.getItem('token');
    try {
      const response = await fetch(API_ENDPOINTS.JOURNAL_DIARY_CHARTS(diaryId), {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });
      const data = await response.json();
      return { success: response.ok, data };
    } catch (error) {
      return { success: false, error: { message: error.message } };
    }
  }

  async deleteDiaryChart(chartId) {
    return await httpClient.delete(API_ENDPOINTS.JOURNAL_DIARY_CHART_DELETE(chartId));
  }

  // =========================================================================
  // Dashboard Operations
  // =========================================================================

  async getDashboard(accountId) {
    return await httpClient.get(API_ENDPOINTS.JOURNAL_DASHBOARD(accountId));
  }

  async getEquitySnapshots(accountId) {
    return await httpClient.get(API_ENDPOINTS.JOURNAL_EQUITY_SNAPSHOTS(accountId));
  }

  async createEquitySnapshot(accountId, snapshotDate, equityValue, openTradeEquity = 0) {
    const params = new URLSearchParams();
    params.append('snapshot_date', snapshotDate);
    params.append('equity_value', equityValue);
    params.append('open_trade_equity', openTradeEquity);
    const url = `${API_ENDPOINTS.JOURNAL_EQUITY_SNAPSHOTS(accountId)}?${params.toString()}`;
    return await httpClient.post(url);
  }

  // =========================================================================
  // Daily Plan Operations
  // =========================================================================

  async getDailyPlans(accountId, limit = 30, offset = 0) {
    const url = `${API_ENDPOINTS.JOURNAL_DAILY_PLANS(accountId)}?limit=${limit}&offset=${offset}`;
    return await httpClient.get(url);
  }

  async getDailyPlan(accountId, planId) {
    return await httpClient.get(API_ENDPOINTS.JOURNAL_DAILY_PLAN(accountId, planId));
  }

  async createDailyPlan(accountId, data) {
    return await httpClient.post(API_ENDPOINTS.JOURNAL_DAILY_PLANS(accountId), data);
  }

  async updateDailyPlan(accountId, planId, data) {
    return await httpClient.put(API_ENDPOINTS.JOURNAL_DAILY_PLAN(accountId, planId), data);
  }

  async deleteDailyPlan(accountId, planId) {
    return await httpClient.delete(API_ENDPOINTS.JOURNAL_DAILY_PLAN(accountId, planId));
  }

  // =========================================================================
  // Weekly Review Operations
  // =========================================================================

  async getWeeklyReviews(accountId, limit = 20, offset = 0) {
    const url = `${API_ENDPOINTS.JOURNAL_WEEKLY_REVIEWS(accountId)}?limit=${limit}&offset=${offset}`;
    return await httpClient.get(url);
  }

  async getWeeklyReview(accountId, reviewId) {
    return await httpClient.get(API_ENDPOINTS.JOURNAL_WEEKLY_REVIEW(accountId, reviewId));
  }

  async createWeeklyReview(accountId, data) {
    return await httpClient.post(API_ENDPOINTS.JOURNAL_WEEKLY_REVIEWS(accountId), data);
  }

  async updateWeeklyReview(accountId, reviewId, data) {
    return await httpClient.put(API_ENDPOINTS.JOURNAL_WEEKLY_REVIEW(accountId, reviewId), data);
  }

  async recalculateWeeklyStats(accountId, reviewId) {
    return await httpClient.post(API_ENDPOINTS.JOURNAL_WEEKLY_REVIEW_RECALC(accountId, reviewId));
  }

  async deleteWeeklyReview(accountId, reviewId) {
    return await httpClient.delete(API_ENDPOINTS.JOURNAL_WEEKLY_REVIEW(accountId, reviewId));
  }

  // =========================================================================
  // Utility Methods
  // =========================================================================

  formatCurrency(value, currency = 'VND') {
    if (value == null) return '—';
    if (currency === 'VND') {
      return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(value);
    }
    return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(value);
  }

  formatPercent(value) {
    if (value == null) return '—';
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  }
}

export default new JournalService();
