import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import axios from 'axios';
import i18n from '../../i18n';
import { AIInsights } from './AIInsights';
import helperService from '../../services/helperService';

// A factory mock, not the auto-mock: `helperService` pulls in `httpClient`,
// which calls `axios.create(...).interceptors.request.use(...)` at import
// time. The auto-mock returns undefined from `create()` and the module blows
// up before a single test runs.
jest.mock('axios', () => {
  const interceptors = {
    request: { use: jest.fn() },
    response: { use: jest.fn() },
  };
  const instance = {
    interceptors,
    defaults: { headers: { common: {} } },
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
  };
  const mocked = {
    interceptors,
    defaults: instance.defaults,
    get: jest.fn(),
    post: jest.fn(),
    create: jest.fn(() => instance),
  };
  mocked.default = mocked;
  return mocked;
});
jest.mock('../../services/helperService');

// The real chart pulls in a charting library and a canvas; here it only needs
// to report WHETHER it was rendered and with how many rows, which is exactly
// the thing under test.
jest.mock('../ui/UnifiedFinancialChart', () => ({ data, ticker }) => (
  <div data-testid="chart" data-rows={data.length} data-ticker={ticker} />
));
jest.mock('../common/ChartPatternsCompact', () => () => <div />);

const realRows = [
  { date: '2026-10-01', close: 100.5, rsi_14: 55.2, volume: 1200000 },
  { date: '2026-10-02', close: 101.25, rsi_14: 57.1, volume: 1310000 },
];

const openChartsTab = async () => {
  // selectedStock is populated by the holdings fetch; the charts tab is not
  // the default one.
  await waitFor(() => expect(axios.get).toHaveBeenCalled());
  fireEvent.click(screen.getByText(i18n.t('analysis.ai_insights.charts_tab')));
};

beforeEach(async () => {
  jest.clearAllMocks();   // clear calls, keep create()'s implementation
  await i18n.changeLanguage('vi');

  // Holdings come over plain fetch; failing it exercises the component's own
  // default-symbol path and gives us a deterministic selectedStock.
  global.fetch = jest.fn().mockRejectedValue(new Error('offline'));
  helperService.getPatterns = jest.fn().mockResolvedValue({ success: false });
  axios.get.mockResolvedValue({ data: { status: 'success', data: { indicators_by_category: {} } } });
});

afterEach(() => {
  delete global.fetch;
});

describe('AIInsights — a failed indicator fetch must not invent a chart', () => {
  test('renders no chart at all when the indicator request fails', async () => {
    // The defect this replaces: the catch block synthesised a Math.random()
    // walk from a base price of 100 — price, EMA, SMA, Bollinger Bands, VWAP,
    // RSI, Stochastic, MFI, MACD, OBV — and charted it as the selected
    // symbol's real indicators, with only a console.error to say otherwise.
    axios.post.mockRejectedValue(new Error('network down'));

    render(<AIInsights />);
    await openChartsTab();

    await waitFor(() =>
      expect(screen.getByText(i18n.t('analysis.ai_insights.chart_unavailable'))).toBeInTheDocument()
    );
    expect(screen.queryByTestId('chart')).not.toBeInTheDocument();
  });

  test('says why, and does not show the "select indicators" hint instead', async () => {
    // The generic empty state tells the user to pick indicators and click
    // Analyze. After a network failure that is misleading — it blames the
    // user for the app's problem — so the error state has to win.
    axios.post.mockRejectedValue(new Error('network down'));

    render(<AIInsights />);
    await openChartsTab();

    await waitFor(() =>
      expect(screen.getByText(i18n.t('analysis.ai_insights.chart_unavailable'))).toBeInTheDocument()
    );
    expect(
      screen.queryByText(i18n.t('analysis.ai_insights.select_indicators_hint'))
    ).not.toBeInTheDocument();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  test('surfaces the server message when it sends one', async () => {
    axios.post.mockRejectedValue({ response: { data: { message: 'Symbol not covered' } } });

    render(<AIInsights />);
    await openChartsTab();

    await waitFor(() => expect(screen.getByText('Symbol not covered')).toBeInTheDocument());
    expect(screen.queryByTestId('chart')).not.toBeInTheDocument();
  });

  test('a non-success response clears the chart instead of leaving stale data', async () => {
    // There was no `else` on the success check, so a non-success response left
    // the PREVIOUS symbol's series on screen under the new symbol's name —
    // arguably worse than an error, because it looks like real data.
    axios.post.mockResolvedValue({ data: { status: 'error', message: 'No data for range' } });

    render(<AIInsights />);
    await openChartsTab();

    await waitFor(() => expect(screen.getByText('No data for range')).toBeInTheDocument());
    expect(screen.queryByTestId('chart')).not.toBeInTheDocument();
  });

  test('real data still renders, and reaches the chart unchanged', async () => {
    axios.post.mockResolvedValue({ data: { status: 'success', data: realRows } });

    render(<AIInsights />);
    await openChartsTab();

    const chart = await screen.findByTestId('chart');
    expect(chart).toHaveAttribute('data-rows', String(realRows.length));
    expect(
      screen.queryByText(i18n.t('analysis.ai_insights.chart_unavailable'))
    ).not.toBeInTheDocument();
  });
});

describe('AIInsights — the generator is gone, not merely unused', () => {
  test('no indicator series is ever derived from Math.random()', () => {
    // A source-level guard, because "we deleted the function" stays true only
    // until someone reintroduces it to fill an empty chart.
    //
    // COMMENTS ARE STRIPPED FIRST. Without that the guard trips on the
    // comment in AIInsights.js that explains what used to be there — i.e. it
    // would fail for describing the fix, and the obvious "fix" would be to
    // delete the explanation. A guard has to assert about code.
    // eslint-disable-next-line global-require
    const raw = require('fs').readFileSync(
      require('path').join(__dirname, 'AIInsights.js'), 'utf8'
    );
    const code = raw
      .replace(/\/\*[\s\S]*?\*\//g, '')   // block comments
      .replace(/^\s*\/\/.*$/gm, '');       // whole-line comments

    expect(code).not.toMatch(/generateMockIndicatorData/);
    expect(code).not.toMatch(/Math\.random/);
    expect(code).not.toMatch(/using mock data/);
    // ...and prove the stripping works, so the assertions above cannot pass
    // by accidentally blanking the whole file.
    expect(code).toMatch(/setIndicatorData\(null\)/);
    expect(code).toMatch(/setChartError/);
  });
});
