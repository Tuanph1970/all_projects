/**
 * Chart analyst — rendered, not grepped.
 *
 * The other test file in this folder checks source text and i18n coverage. This
 * one mounts the component and asserts on the DOM, which is the only way to
 * catch the things that matter in a browser: that the date fields arrive
 * prefilled, that the narrative sentences actually render with their numbers
 * substituted, and that they render in Vietnamese when the app is in Vietnamese.
 *
 * Uses the REAL i18n instance, per the note in Watchlist.test.js — a
 * react-i18next stub would make every assertion below vacuous, because a stub
 * returns the key and the key always "renders".
 */
import React from 'react';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import ChartNarrator from './index';
import { analysisAPI, stockAPI } from '../../../services/api';
import i18n from '../../../i18n';

jest.mock('../../../services/api');

const LATEST = '2026-11-03';

/** A narrative response shaped exactly like the live endpoint's. */
const RESPONSE = {
  symbol: 'FPT',
  as_of: LATEST,
  bars: 216,
  data_ok: true,
  levels: [{ price: 55.85, kind: 'resistance', touches: 2, role_reversed: true }],
  chart: [
    { date: '2025-12-18', open: 90, high: 91, low: 89, close: 90, volume: 1e6,
      ma20: 90.5, ma50: 92, ma200: 90.22 },
    { date: LATEST, open: 52.4, high: 52.5, low: 50.1, close: 50.2, volume: 12293400,
      ma20: 56.59, ma50: 61.77, ma200: 68.53 },
  ],
  sections: [
    { key: 'data', findings: [{ code: 'narrative.data.clean', params: {}, severity: 'info' }] },
    { key: 'trend', findings: [{
      code: 'narrative.trend.down_full_stack',
      params: { price: 50.2, ma20: 56.59, ma50: 61.77, ma200: 68.53 },
      severity: 'bearish' }] },
    { key: 'levels', findings: [{
      code: 'narrative.levels.nearest_resistance',
      params: { price: 55.85, distance_pct: 11.26, touches: 2, age_bars: 13 },
      severity: 'info' }] },
    { key: 'indicators', findings: [{
      code: 'narrative.indicator.rsi_oversold', params: { value: 21.0 },
      severity: 'bullish' }] },
    { key: 'patterns', findings: [{
      code: 'narrative.candle.shooting_star', params: { date: '2026-10-30', bars_ago: 1 },
      severity: 'bearish' }] },
    { key: 'chart_patterns', findings: [{
      code: 'narrative.pattern.not_noteworthy',
      params: { count: 1, names: 'Head & Shoulders', best_name: 'Head & Shoulders',
                best_percentile: 7.5, threshold: 95.0, expected_in_noise: 0.45 },
      severity: 'info' }] },
    { key: 'channel', findings: [{
      code: 'narrative.channel.falling',
      params: { upper_now: 62.25, lower_now: 57.68, upper_slope: -0.1,
                lower_slope: -0.08, position_pct: 0, pivots_used: 55 },
      severity: 'info' }] },
    { key: 'strategy', findings: [
      { code: 'narrative.strategy.against_trend', params: {}, severity: 'warning' },
      { code: 'narrative.strategy.wait', params: { reason: '' }, severity: 'info' }] },
  ],
};

beforeEach(async () => {
  jest.clearAllMocks();
  stockAPI.getLatestSessionDate.mockResolvedValue(LATEST);
  stockAPI.getWatchlist.mockResolvedValue([
    { symbol: 'FPT', name: 'CTCP FPT' },
    { symbol: 'HPG', name: 'Hoa Phat' },
    { symbol: 'POW', name: 'PV Power' },
    { symbol: 'VIC', name: 'Vingroup' },
  ]);
  analysisAPI.getNarrative.mockResolvedValue(RESPONSE);
  await i18n.changeLanguage('en');
});

async function mounted() {
  const view = render(<ChartNarrator />);
  // The dates are populated asynchronously; the Analysis button stays disabled
  // until they are, so waiting on the field is waiting on readiness.
  await waitFor(() => expect(screen.getByDisplayValue(LATEST)).toBeInTheDocument());
  return view;
}

/**
 * Assert a sentence is on screen, tolerating nested wrappers.
 *
 * Each finding renders as <li><span>text</span></li>, so BOTH elements' text
 * content matches and getByText throws "Found multiple elements" — a failure
 * that reads as "the narrative did not render" when it rendered perfectly and
 * the query was simply too strict. getAllByText is the right tool for text
 * inside a styled wrapper.
 */
function seen(pattern) {
  const hits = screen.getAllByText(pattern);
  expect(hits.length).toBeGreaterThan(0);
  return hits[0];
}

/**
 * Pick a symbol and press Analysis, flushing the async state update.
 *
 * The click must be wrapped in act(): `setResult(data)` lands in a promise
 * microtask after the mocked fetch resolves, and under React 19 a bare
 * fireEvent leaves that update unflushed — waitFor then retries for a full
 * second against a tree that never re-renders, and the failure reads as
 * "the narrative did not render" when the component is perfectly fine.
 * Verified by probe: the DOM does contain the sentence once act flushes.
 */
async function pressAnalysis(label = /Analysis/i) {
  fireEvent.change(screen.getByRole('combobox'), { target: { value: 'FPT' } });
  await act(async () => {
    fireEvent.click(screen.getByRole('button', { name: label }));
  });
}

describe('Chart analyst — the date range the user sees', () => {
  it('prefills the end date with the newest session, not today', async () => {
    await mounted();
    expect(screen.getByDisplayValue(LATEST)).toBeInTheDocument();
    expect(stockAPI.getLatestSessionDate).toHaveBeenCalled();
  });

  it('prefills the start date 320 days back, covering MA200 in bars', async () => {
    await mounted();
    // 2026-11-03 minus ceil(200 * 1.6) = 320 days.
    expect(screen.getByDisplayValue('2025-12-18')).toBeInTheDocument();
  });

  it('enables Analysis once the dates are in place', async () => {
    await mounted();
    const btn = screen.getByRole('button', { name: /Analysis/i });
    // Still needs a symbol — the dates alone are not enough.
    expect(btn).toBeDisabled();
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'FPT' } });
    await waitFor(() => expect(btn).toBeEnabled());
  });

  it('lists the watched symbols in the picker', async () => {
    await mounted();
    for (const s of ['FPT', 'HPG', 'POW', 'VIC']) {
      expect(screen.getByRole('option', { name: new RegExp(s) })).toBeInTheDocument();
    }
  });

  it('sends the prefilled dates to the backend when Analysis is pressed', async () => {
    await mounted();
    await pressAnalysis();
    await waitFor(() => expect(analysisAPI.getNarrative).toHaveBeenCalled());
    const [sym, opts] = analysisAPI.getNarrative.mock.calls[0];
    expect(sym).toBe('FPT');
    expect(opts.endDate).toBe(LATEST);
    expect(opts.startDate).toBe('2025-12-18');
  });

  it('restores the defaults after the user edits a date', async () => {
    await mounted();
    const start = screen.getByDisplayValue('2025-12-18');
    fireEvent.change(start, { target: { value: '2026-06-01' } });
    expect(screen.getByDisplayValue('2026-06-01')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Reset dates/i }));
    await waitFor(() =>
      expect(screen.getByDisplayValue('2025-12-18')).toBeInTheDocument());
  });

  it('refuses an inverted range instead of silently reordering it', async () => {
    await mounted();
    // Put the start AFTER the end.
    fireEvent.change(screen.getByDisplayValue('2025-12-18'),
                     { target: { value: '2026-12-01' } });
    await waitFor(() => expect(
      screen.getByRole('button', { name: /Analysis/i })).toBeDisabled());
    seen(/start date is after the end date/i);
  });
});

describe('Chart analyst — the narrative the user reads', () => {
  async function analysed() {
    await mounted();
    await pressAnalysis();
    await waitFor(() => seen(/Downtrend/i));
  }

  it('renders real sentences with the numbers substituted, not raw keys', async () => {
    await analysed();
    // The trend sentence, with its four moving averages interpolated.
    seen(/Downtrend\. Price 50\.2 is below MA20 56\.59/);
    // And nothing anywhere should be a dotted i18n key.
    expect(screen.queryByText(/narrative\.[a-z_]+\./)).not.toBeInTheDocument();
  });

  it('shows the resistance level and its distance', async () => {
    await analysed();
    seen(/Nearest resistance 55\.85, 11\.26% above/);
  });

  it('says a chart pattern is no stronger than chance, with the percentile', async () => {
    await analysed();
    // THE HONESTY RULE, rendered. A head-and-shoulders at the 7.5th percentile
    // must reach the user as "not stronger than chance", not as a signal.
    seen(/NONE of them is stronger than chance/);
    seen(/7\.5th percentile/);
  });

  it('warns that the setup is against the trend and offers no trade', async () => {
    await analysed();
    seen(/against the dominant trend/i);
    seen(/Waiting is a position too/i);
  });

  it('shows the as-of date and bar count', async () => {
    await analysed();
    seen(/Bars through 2026-11-03 \(216 sessions\)/);
  });

  it('carries the disclaimer', async () => {
    await analysed();
    seen(/not a forecast and not investment advice/i);
  });
});

describe('Chart analyst — in Vietnamese', () => {
  it('renders the narrative in Vietnamese when the app is in Vietnamese', async () => {
    await i18n.changeLanguage('vi');
    render(<ChartNarrator />);
    await waitFor(() => expect(screen.getByDisplayValue(LATEST)).toBeInTheDocument());
    await pressAnalysis(/Phân tích/i);
    await waitFor(() => seen(/Xu hướng giảm/));
    // The numbers must survive the Vietnamese template too.
    seen(/Giá 50\.2 nằm dưới MA20 56\.59/);
    seen(/Kháng cự gần nhất 55\.85/);
    seen(/KHÔNG mẫu nào mạnh hơn mức ngẫu nhiên/);
    await i18n.changeLanguage('en');
  });
});

describe('Chart analyst — the contaminated-data banner', () => {
  it('warns loudly and withholds the plan when data_ok is false', async () => {
    analysisAPI.getNarrative.mockResolvedValue({
      ...RESPONSE,
      data_ok: false,
      sections: [
        { key: 'data', findings: [{
          code: 'narrative.data.corporate_action_gap',
          params: { count: 1, date: '2026-10-27', move_pct: -33.82,
                    prev_close: 33.8, close: 22.37, ratio: 1.511 },
          severity: 'warning' }] },
        { key: 'strategy', findings: [{
          code: 'narrative.strategy.contaminated', params: {}, severity: 'warning' }] },
      ],
    });
    await mounted();
    await pressAnalysis();
    await waitFor(() => seen(/unadjusted corporate action/i));
    seen(/almost certainly a stock dividend or split/i);
    seen(/No plan is offered/i);
  });
});

describe('Chart analyst — when things go wrong', () => {
  it('tells the user when the watchlist is empty rather than showing a dead picker', async () => {
    stockAPI.getWatchlist.mockResolvedValue([]);
    render(<ChartNarrator />);
    await waitFor(() => seen(/not watching any symbol yet/i));
  });

  it('shows the failure reason when the analysis call fails', async () => {
    analysisAPI.getNarrative.mockRejectedValue(new Error('Not enough price history'));
    await mounted();
    await pressAnalysis();
    await waitFor(() => seen(/Not enough price history/));
  });

  it('still prefills dates when the session lookup fails', async () => {
    // A failed lookup must not leave the form unusable; it falls back to today.
    stockAPI.getLatestSessionDate.mockResolvedValue(null);
    render(<ChartNarrator />);
    await waitFor(() => {
      const dates = document.querySelectorAll('input[type="date"]');
      expect(dates).toHaveLength(2);
      expect(dates[0].value).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(dates[1].value).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    });
  });
});
