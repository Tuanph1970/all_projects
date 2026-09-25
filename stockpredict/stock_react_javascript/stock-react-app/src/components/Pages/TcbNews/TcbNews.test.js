/**
 * TCB News screen — the paste → parse → confirm → save flow.
 *
 * The behaviour worth protecting is that Parse writes nothing and Save sends only the
 * ticked recommendations, so a misread ticker never reaches the watchlist silently.
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TcbNews from './index';
import tcbNewsService from '../../../services/tcbNewsService';

jest.mock('../../../services/tcbNewsService');
jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key, opts) => (opts ? `${key}:${JSON.stringify(opts)}` : key) }),
}));

const PREVIEW = {
  id: null,
  lang: 'vi',
  session_date_hint: '2026-09-21',
  vnindex_close: 1799.67,
  vnindex_change_pct: -0.88,
  vnindex_change_pts: -15.99,
  matched_value_bn: 13665.8,
  foreign_net_bn: -664.2,
  ma50: 1776.0,
  companies: [{ symbol: 'MSN', item_text: 'Công bố kết quả kinh doanh…' }],
  recos: [{ symbol: 'NTP', action: 'WATCH', label_verbatim: 'Chờ mua', rationale: 'Giá PVC…' }],
};

beforeEach(() => {
  jest.clearAllMocks();
  tcbNewsService.list.mockResolvedValue({ success: true, data: [] });
  tcbNewsService.recos.mockResolvedValue({ success: true, data: [] });
  tcbNewsService.record.mockResolvedValue({
    success: false, error: { response: { status: 409, data: { scored_calls: 0 } } } });
  tcbNewsService.preview.mockResolvedValue({ success: true, data: PREVIEW });
  tcbNewsService.save.mockResolvedValue({
    success: true,
    data: { created: true, mail: { ...PREVIEW, id: 1, session_date: '2026-09-21' },
      pushed: [{ symbol: 'NTP', ok: true }] },
  });
});

// user-event v13 in this project: no .setup(), calls are synchronous.
const paste = (text = 'some email body') =>
  userEvent.type(screen.getByLabelText('tcb_news.content_label'), text);

const click = (el) => userEvent.click(el);

test('parse sends the pasted content and stores nothing', async () => {
  render(<TcbNews />);
  paste();
  click(screen.getByText('tcb_news.parse_button'));

  await waitFor(() => expect(tcbNewsService.preview).toHaveBeenCalled());
  expect(tcbNewsService.preview.mock.calls[0][0]).toBe('some email body');
  expect(tcbNewsService.save).not.toHaveBeenCalled();
});

test('the parsed session date overrides the default date', async () => {
  render(<TcbNews />);
  paste();
  click(screen.getByText('tcb_news.parse_button'));

  await waitFor(() =>
    expect(screen.getByLabelText('tcb_news.session_date_label')).toHaveValue('2026-09-21'));
});

test('the preview shows the recommendation with its verbatim TCB wording', async () => {
  render(<TcbNews />);
  paste();
  click(screen.getByText('tcb_news.parse_button'));

  expect(await screen.findByText('NTP')).toBeInTheDocument();
  expect(screen.getByText('WATCH')).toBeInTheDocument();
  expect(screen.getByText('Chờ mua')).toBeInTheDocument();
});

test('save pushes the ticked recommendation with the confirmed session date', async () => {
  render(<TcbNews />);
  paste();
  click(screen.getByText('tcb_news.parse_button'));
  await screen.findByText('NTP');

  click(screen.getByText(/tcb_news.save_button/));
  await waitFor(() => expect(tcbNewsService.save).toHaveBeenCalled());
  expect(tcbNewsService.save.mock.calls[0][0]).toMatchObject({
    sessionDate: '2026-09-21',
    pushSymbols: ['NTP'],
  });
});

test('unticking a recommendation keeps it off the watchlist', async () => {
  render(<TcbNews />);
  paste();
  click(screen.getByText('tcb_news.parse_button'));

  const tick = await screen.findByLabelText(/tcb_news.push_aria/);
  expect(tick).toBeChecked();          // a recognised action is pre-ticked
  click(tick);

  click(screen.getByText(/tcb_news.save_button/));
  await waitFor(() => expect(tcbNewsService.save).toHaveBeenCalled());
  expect(tcbNewsService.save.mock.calls[0][0].pushSymbols).toEqual([]);
});

test('a recommendation with an unrecognised label is not pre-ticked', async () => {
  tcbNewsService.preview.mockResolvedValue({
    success: true,
    data: { ...PREVIEW, recos: [
      { symbol: 'HPG', action: null, label_verbatim: 'Xin chào', rationale: null }] },
  });
  render(<TcbNews />);
  paste();
  click(screen.getByText('tcb_news.parse_button'));

  expect(await screen.findByLabelText(/tcb_news.push_aria/)).not.toBeChecked();
  expect(screen.getByText('tcb_news.unknown_action_hint')).toBeInTheDocument();
});

test('a duplicate paste is reported without clearing the form', async () => {
  tcbNewsService.save.mockResolvedValue({
    success: true,
    data: { created: false, mail: { ...PREVIEW, id: 1, session_date: '2026-09-21' }, pushed: [] },
  });
  render(<TcbNews />);
  paste();
  click(screen.getByText('tcb_news.parse_button'));
  await screen.findByText('NTP');
  click(screen.getByText(/tcb_news.save_button/));

  expect(await screen.findByText(/tcb_news.duplicate/)).toBeInTheDocument();
  expect(screen.getByLabelText('tcb_news.content_label')).toHaveValue('some email body');
});

test('a parse failure surfaces the error and offers no save', async () => {
  tcbNewsService.preview.mockResolvedValue({
    success: false, error: { message: 'boom' } });
  render(<TcbNews />);
  paste();
  click(screen.getByText('tcb_news.parse_button'));

  expect(await screen.findByText('boom')).toBeInTheDocument();
  expect(screen.getByText(/tcb_news.save_button/).closest('button')).toBeDisabled();
});

test('save is disabled until the email has been parsed', async () => {
  render(<TcbNews />);
  paste();
  expect(screen.getByText(/tcb_news.save_button/).closest('button')).toBeDisabled();
});

// ---------------------------------------------------------------------------
// Call ledger + track record (FR-BM-SCORE, FR-BM-RECORD)
// ---------------------------------------------------------------------------

const SCORED = {
  id: 1, session_date: '2026-09-21', symbol: 'NTP', action: 'WATCH',
  label_verbatim: 'Chờ mua', ref_close: 100.0, ret_adjusted: false,
  ret_1d: 0.012, ret_5d: -0.031, ret_20d: 0.084, ret_60d: null,
  ret_20d_vs_index: 0.05,
};

const withLedger = (recos, recordResult) => {
  tcbNewsService.recos.mockResolvedValue({ success: true, data: recos });
  tcbNewsService.record.mockResolvedValue(recordResult);
};

test('the ledger shows each call with its forward returns', async () => {
  withLedger([SCORED], { success: false, error: { response: { status: 409, data: {
    scored_calls: 1, detail: 'not reportable yet' } } } });
  render(<TcbNews />);

  expect(await screen.findByText('tcb_news.ledger_title')).toBeInTheDocument();
  expect(screen.getByText('+1.2%')).toBeInTheDocument();
  expect(screen.getByText('-3.1%')).toBeInTheDocument();
  expect(screen.getByText('+8.4%')).toBeInTheDocument();
});

test('an unelapsed horizon shows a dash, never a zero', async () => {
  withLedger([SCORED], { success: false, error: { response: { data: { scored_calls: 1 } } } });
  render(<TcbNews />);
  await screen.findByText('tcb_news.ledger_title');
  // ret_60d is null -> "—"; a "0.0%" here would read as "flat" rather than "unknown".
  expect(screen.getAllByText('—').length).toBeGreaterThan(0);
  expect(screen.queryByText('+0.0%')).not.toBeInTheDocument();
});

test('the aggregate is withheld below the minimum and says how far off it is', async () => {
  withLedger([SCORED], { success: false, error: { response: { status: 409, data: {
    scored_calls: 7, detail: 'not reportable yet: 7 scored call(s), 30 required' } } } });
  render(<TcbNews />);

  expect(await screen.findByText(/tcb_news.record_not_yet/)).toBeInTheDocument();
  expect(screen.getByText(/"scored":7/)).toBeInTheDocument();
  expect(screen.queryByText('tcb_news.col_hit_rate')).not.toBeInTheDocument();
});

test('the record renders the hit rate beside its benchmark', async () => {
  withLedger([SCORED], { success: true, data: {
    total_calls: 40, scored_calls: 35, min_calls: 30, reportable: true,
    horizons: { '20d': { n: 35, mean_return: 0.042, mean_excess_return: 0.018,
      directional_n: 30, hit_rate: 0.6, benchmark_hit_rate: 0.5 } },
    by_action: {},
  } });
  render(<TcbNews />);

  expect(await screen.findByText('tcb_news.col_hit_rate')).toBeInTheDocument();
  expect(screen.getByText('60%')).toBeInTheDocument();   // TCB
  expect(screen.getByText('50%')).toBeInTheDocument();   // the benchmark it must beat
  expect(screen.getByText('+4.2%')).toBeInTheDocument();
  expect(screen.getByText('+1.8%')).toBeInTheDocument();
  expect(screen.getByText('tcb_news.record_benchmark_note')).toBeInTheDocument();
});

test('scoring now re-reads the ledger and the record', async () => {
  withLedger([SCORED], { success: false, error: { response: { data: { scored_calls: 1 } } } });
  tcbNewsService.score.mockResolvedValue({ success: true, data: { scored: 1 } });
  render(<TcbNews />);
  await screen.findByText('tcb_news.ledger_title');

  tcbNewsService.recos.mockClear();
  click(screen.getByText('tcb_news.score_now'));

  await waitFor(() => expect(tcbNewsService.score).toHaveBeenCalled());
  await waitFor(() => expect(tcbNewsService.recos).toHaveBeenCalled());
});

test('the raw-close warning fires only when a symbol lacked an adjusted close', async () => {
  withLedger([SCORED], { success: false, error: { response: { data: { scored_calls: 1 } } } });
  render(<TcbNews />);
  expect(await screen.findByText('tcb_news.unadjusted_warning')).toBeInTheDocument();
});

test('adjusted returns carry no raw-close warning', async () => {
  // The normal case after Backlog #56: stock-data-service records the adjusted close.
  withLedger([{ ...SCORED, ret_adjusted: true }],
    { success: false, error: { response: { data: { scored_calls: 1 } } } });
  render(<TcbNews />);
  await screen.findByText('tcb_news.ledger_title');
  expect(screen.queryByText('tcb_news.unadjusted_warning')).not.toBeInTheDocument();
});

test('the capital-adjusted note shows on any scored return, adjusted or not', async () => {
  withLedger([{ ...SCORED, ret_adjusted: true }],
    { success: false, error: { response: { data: { scored_calls: 1 } } } });
  render(<TcbNews />);
  expect(await screen.findByText('tcb_news.capital_adjusted_note')).toBeInTheDocument();
});

test('no caveat before anything has been scored', async () => {
  withLedger([{ ...SCORED, ref_close: null, ret_1d: null, ret_5d: null,
    ret_20d: null, ret_60d: null, ret_20d_vs_index: null }],
  { success: false, error: { response: { data: { scored_calls: 0 } } } });
  render(<TcbNews />);
  await screen.findByText('tcb_news.ledger_title');
  expect(screen.queryByText('tcb_news.unadjusted_warning')).not.toBeInTheDocument();
  expect(screen.queryByText('tcb_news.capital_adjusted_note')).not.toBeInTheDocument();
});
