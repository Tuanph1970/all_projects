/**
 * S-4 — the scanner panel inside AI Insights (D6).
 *
 * The assertions concentrate on the states that are easy to get wrong and
 * expensive when wrong: an EMPTY list rendered as a finding rather than a blank
 * screen (#135), the null rate shown beside the list (C4/EC-S5), and the
 * per-symbol diagnostic naming the clause that rejected a name.
 */
import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import MomentumScannerPanel from './MomentumScannerPanel';

// `t` echoes the key, EXCEPT for the one message that interpolates — that key
// gets a real placeholder so the interpolation path is actually exercised
// rather than silently skipped over a string with nothing to substitute.
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (k) => (k.endsWith('symbol_not_scanned') ? '{{symbol}} was not scanned' : k),
  }),
}));

jest.mock('../../services/helperService', () => ({
  __esModule: true,
  default: {
    getMomentumScan: jest.fn(),
    runMomentumScan: jest.fn(),
    getMomentumSymbol: jest.fn(),
  },
}));

import helperService from '../../services/helperService';

const EMPTY_SCAN = {
  scan_date: '2026-11-06',
  trigger: 'SCHEDULED',
  universe_total: 93,
  required_bars: 200,
  ranked_universe: 81,
  candidate_count: 0,
  accounting: {
    no_bars: 0, insufficient_history: 0, price_seam: 0, illiquid: 12,
    failed_trend: 81, failed_base: 0, candidates: 0, excess_qualified: 0,
    accounted: 93, universe_total: 93,
  },
  config: {},
  candidates: [],
  null_fpr: null,
  empty_reason: '81 of 81 ranked names failed the trend template, so none reached the base stage',
};

const POPULATED_SCAN = {
  ...EMPTY_SCAN,
  scan_date: '2024-03-31',
  candidate_count: 2,
  accounting: { ...EMPTY_SCAN.accounting, illiquid: 5, failed_trend: 38, failed_base: 34, candidates: 2, accounted: 79 },
  candidates: [
    {
      rank: 1, symbol: 'GVR', composite: 0.9655, ranked_universe: 88,
      returns: { '21': 15.9, '63': 64.1, '126': 70.0 },
      percentiles: { '21': 0.94, '63': 0.99, '126': 0.98 },
      close: 32.4, prior_advance_pct: 100.0, avg_daily_value_vnd: 121.6e9,
      base_length: 12, base_depth_pct: 13.3, range_ratio: 0.49, volume_ratio: 0.66,
      ma10_distance_pct: 0.5, ma20_distance_pct: 3.9,
      pivot: 35.0, pivot_distance_pct: 8.0, pivot_distance_atr: 2.1,
    },
    {
      rank: 2, symbol: 'PHR', composite: 0.8889, ranked_universe: 88,
      returns: { '21': 14.8, '63': 34.4, '126': 33.2 },
      percentiles: { '21': 0.92, '63': 0.92, '126': 0.83 },
      close: 32.1, prior_advance_pct: 53.0, avg_daily_value_vnd: 18.6e9,
      base_length: 11, base_depth_pct: 13.6, range_ratio: 0.36, volume_ratio: 0.66,
      ma10_distance_pct: 0.6, ma20_distance_pct: 5.1,
      pivot: 33.1, pivot_distance_pct: 3.1, pivot_distance_atr: 1.0,
    },
  ],
  null_fpr: {
    trials: 30, universe_size: 93, trials_with_candidates: 10,
    total_candidates: 14, symbols_tested: 2790,
    trial_fpr: 0.3333, symbol_fpr: 0.00502,
  },
  empty_reason: null,
};

beforeEach(() => jest.clearAllMocks());

describe('empty state — the state this screen is in most often', () => {
  test('an empty list renders the reason, not a blank table', async () => {
    helperService.getMomentumScan.mockResolvedValue(EMPTY_SCAN);
    render(<MomentumScannerPanel />);
    await waitFor(() =>
      expect(screen.getByText(/failed the trend template/)).toBeInTheDocument());
    // #135: it must read as a finding, with the note explaining that empty is valid.
    expect(screen.getByText('analysis.ai_insights.scanner.empty_title')).toBeInTheDocument();
    expect(screen.getByText('analysis.ai_insights.scanner.empty_note')).toBeInTheDocument();
  });

  test('the funnel still shows where the universe went', async () => {
    helperService.getMomentumScan.mockResolvedValue(EMPTY_SCAN);
    render(<MomentumScannerPanel />);
    await waitFor(() =>
      expect(screen.getByText('analysis.ai_insights.scanner.funnel_title')).toBeInTheDocument());
    expect(screen.getByText('81')).toBeInTheDocument();   // failed_trend
    expect(screen.getByText('12')).toBeInTheDocument();   // illiquid
    expect(screen.getByText('93 / 93')).toBeInTheDocument();
  });

  test('zero-count buckets are not listed as rows', async () => {
    helperService.getMomentumScan.mockResolvedValue(EMPTY_SCAN);
    render(<MomentumScannerPanel />);
    await waitFor(() =>
      expect(screen.getByText('analysis.ai_insights.scanner.funnel_title')).toBeInTheDocument());
    expect(screen.queryByText('analysis.ai_insights.scanner.funnel_no_bars')).toBeNull();
    expect(screen.queryByText('analysis.ai_insights.scanner.funnel_price_seam')).toBeNull();
  });

  test('a 404 reads as "nothing ran", never as "nothing qualified"', async () => {
    helperService.getMomentumScan.mockRejectedValue({ response: { status: 404 } });
    render(<MomentumScannerPanel />);
    await waitFor(() =>
      expect(screen.getByText('analysis.ai_insights.scanner.no_run_yet')).toBeInTheDocument());
    expect(screen.queryByText('analysis.ai_insights.scanner.empty_title')).toBeNull();
  });

  test('a real error is surfaced as an error', async () => {
    helperService.getMomentumScan.mockRejectedValue({ response: { status: 500 }, message: 'boom' });
    render(<MomentumScannerPanel />);
    await waitFor(() => expect(screen.getByText('boom')).toBeInTheDocument());
  });
});

describe('candidate table', () => {
  test('renders a row per candidate with its base evidence', async () => {
    helperService.getMomentumScan.mockResolvedValue(POPULATED_SCAN);
    render(<MomentumScannerPanel />);
    await waitFor(() => expect(screen.getByText('GVR')).toBeInTheDocument());
    expect(screen.getByText('PHR')).toBeInTheDocument();
    expect(screen.getByText('+15.9%')).toBeInTheDocument();      // 21-bar return
    expect(screen.getByText('0.49')).toBeInTheDocument();        // range ratio
    expect(screen.getByText('121.6')).toBeInTheDocument();       // tỷ/phiên
  });

  test('turnover is shown in billions, not raw VND', async () => {
    helperService.getMomentumScan.mockResolvedValue(POPULATED_SCAN);
    render(<MomentumScannerPanel />);
    await waitFor(() => expect(screen.getByText('GVR')).toBeInTheDocument());
    expect(screen.queryByText(/121600000000/)).toBeNull();
  });

  test('clicking a row hands the symbol to the parent', async () => {
    helperService.getMomentumScan.mockResolvedValue(POPULATED_SCAN);
    const onSelectSymbol = jest.fn();
    render(<MomentumScannerPanel onSelectSymbol={onSelectSymbol} />);
    await waitFor(() => expect(screen.getByText('GVR')).toBeInTheDocument());
    fireEvent.click(screen.getByText('GVR'));
    expect(onSelectSymbol).toHaveBeenCalledWith('GVR');
  });

  test('a row click without a parent handler does not throw', async () => {
    helperService.getMomentumScan.mockResolvedValue(POPULATED_SCAN);
    render(<MomentumScannerPanel />);
    await waitFor(() => expect(screen.getByText('GVR')).toBeInTheDocument());
    expect(() => fireEvent.click(screen.getByText('GVR'))).not.toThrow();
  });
});

describe('VT-4 null rate (C4 / EC-S5)', () => {
  test('is shown beside the candidate list, with its caveat', async () => {
    helperService.getMomentumScan.mockResolvedValue(POPULATED_SCAN);
    render(<MomentumScannerPanel />);
    await waitFor(() =>
      expect(screen.getByText('analysis.ai_insights.scanner.null_title')).toBeInTheDocument());
    // The caveat is not decoration: without it the figure reads as evidence of edge.
    expect(screen.getByText('analysis.ai_insights.scanner.null_caveat')).toBeInTheDocument();
  });

  test('is omitted rather than faked when the run did not measure it', async () => {
    helperService.getMomentumScan.mockResolvedValue(EMPTY_SCAN);
    render(<MomentumScannerPanel />);
    await waitFor(() =>
      expect(screen.getByText('analysis.ai_insights.scanner.funnel_title')).toBeInTheDocument());
    expect(screen.queryByText('analysis.ai_insights.scanner.null_title')).toBeNull();
  });
});

describe('per-symbol diagnostic', () => {
  const VIC = {
    scan_date: '2026-11-06', symbol: 'VIC', verdict: 'FAILED_TREND',
    rank: null, composite: null, failed_clauses: ['prior_advance'],
    detail: {
      trend: {
        clauses: [
          { name: 'close_above_sma50', passed: true, detail: 'close 234.50 vs SMA50 233.69' },
          { name: 'close_above_sma200', passed: true, detail: 'close 234.50 vs SMA200 198.85' },
          { name: 'sma50_above_sma200', passed: true, detail: 'SMA50 233.69 vs SMA200 198.85' },
          { name: 'prior_advance', passed: false, detail: '22.1% off the 126-bar low 192.00, need 30%' },
        ],
      },
      failed_clauses: ['prior_advance'],
    },
  };

  test('names the clause and shows the arithmetic behind it', async () => {
    helperService.getMomentumScan.mockResolvedValue(EMPTY_SCAN);
    helperService.getMomentumSymbol.mockResolvedValue(VIC);
    render(<MomentumScannerPanel />);
    await waitFor(() => expect(screen.getByText(/failed the trend template/)).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText('analysis.ai_insights.scanner.lookup_label'),
                     { target: { value: 'vic' } });
    fireEvent.click(screen.getByText('analysis.ai_insights.scanner.lookup_button'));

    await waitFor(() => expect(screen.getByText('FAILED_TREND')).toBeInTheDocument());
    // The number is the point — a rejection whose arithmetic is hidden cannot be acted on.
    expect(screen.getByText(/22.1% off the 126-bar low/)).toBeInTheDocument();
    expect(screen.getByText(/close 234.50 vs SMA200/)).toBeInTheDocument();
  });

  test('the symbol is upper-cased before the request', async () => {
    helperService.getMomentumScan.mockResolvedValue(EMPTY_SCAN);
    helperService.getMomentumSymbol.mockResolvedValue(VIC);
    render(<MomentumScannerPanel />);
    await waitFor(() => expect(screen.getByText(/failed the trend template/)).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText('analysis.ai_insights.scanner.lookup_label'),
                     { target: { value: 'vic' } });
    fireEvent.click(screen.getByText('analysis.ai_insights.scanner.lookup_button'));
    await waitFor(() =>
      expect(helperService.getMomentumSymbol).toHaveBeenCalledWith('VIC', null));
  });

  test('an unscanned symbol explains itself rather than showing nothing', async () => {
    helperService.getMomentumScan.mockResolvedValue(EMPTY_SCAN);
    helperService.getMomentumSymbol.mockRejectedValue({ response: { status: 404 } });
    render(<MomentumScannerPanel />);
    await waitFor(() => expect(screen.getByText(/failed the trend template/)).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText('analysis.ai_insights.scanner.lookup_label'),
                     { target: { value: 'ZZZZ' } });
    fireEvent.click(screen.getByText('analysis.ai_insights.scanner.lookup_button'));
    await waitFor(() =>
      expect(screen.getByText('ZZZZ was not scanned')).toBeInTheDocument());
  });

  test('an empty symbol does not fire a request', async () => {
    helperService.getMomentumScan.mockResolvedValue(EMPTY_SCAN);
    render(<MomentumScannerPanel />);
    await waitFor(() => expect(screen.getByText(/failed the trend template/)).toBeInTheDocument());
    fireEvent.click(screen.getByText('analysis.ai_insights.scanner.lookup_button'));
    expect(helperService.getMomentumSymbol).not.toHaveBeenCalled();
  });
});

describe('running a scan', () => {
  test('the run button posts and replaces the displayed scan', async () => {
    helperService.getMomentumScan.mockResolvedValue(EMPTY_SCAN);
    helperService.runMomentumScan.mockResolvedValue(POPULATED_SCAN);
    render(<MomentumScannerPanel />);
    await waitFor(() => expect(screen.getByText(/failed the trend template/)).toBeInTheDocument());
    fireEvent.click(screen.getByText('analysis.ai_insights.scanner.run_button'));
    await waitFor(() => expect(screen.getByText('GVR')).toBeInTheDocument());
  });

  test('a chosen date is passed to both the load and the run', async () => {
    helperService.getMomentumScan.mockResolvedValue(EMPTY_SCAN);
    helperService.runMomentumScan.mockResolvedValue(POPULATED_SCAN);
    render(<MomentumScannerPanel />);
    await waitFor(() => expect(screen.getByText(/failed the trend template/)).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText('analysis.ai_insights.scanner.date_label'),
                     { target: { value: '2024-03-31' } });
    fireEvent.click(screen.getByText('analysis.ai_insights.scanner.load_button'));
    await waitFor(() =>
      expect(helperService.getMomentumScan).toHaveBeenLastCalledWith('2024-03-31'));

    // The run button is relabelled to `running` while a fetch is in flight, so
    // it has to be waited for rather than grabbed straight after the load click.
    await waitFor(() =>
      expect(screen.getByText('analysis.ai_insights.scanner.run_button')).toBeInTheDocument());
    fireEvent.click(screen.getByText('analysis.ai_insights.scanner.run_button'));
    await waitFor(() =>
      expect(helperService.runMomentumScan).toHaveBeenCalledWith({ scanDate: '2024-03-31' }));
  });
});
