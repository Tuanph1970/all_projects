/**
 * Watchlist — the forward return beside each TCB proposal (Backlog #57).
 *
 * The watch screen already showed what TCB said; the ledger that shows whether it
 * worked lived only on the TCB News screen. What these protect:
 *
 *   * the horizon shown is the longest one that has actually ELAPSED, and it is
 *     labelled, so a 1-session number is never read as a 60-session one;
 *   * the index benchmark travels beside the number (EC-B7), not inside a tooltip;
 *   * an unadjusted mark is flagged rather than presented as clean (Backlog #60);
 *   * the number always belongs to a named session;
 *   * a news-service outage costs a column, never the watchlist.
 *
 * Asserts real Vietnamese copy through the shared i18n instance — see the note in
 * TcbNews.test.js (Backlog #71) for why a react-i18next stub must never come back.
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Watchlist from './Watchlist';
import httpClient from '../../services/httpClient';
import tcbNewsService from '../../services/tcbNewsService';
import i18n from '../../i18n';

jest.mock('../../services/httpClient');
jest.mock('../../services/tcbNewsService');

const ok = (data) => ({ success: true, data });

const ROW = {
  symbol: 'MSR',
  company_name: 'Masan High-Tech Materials',
  current_price: 52600,
  change_percent: 1.2,
  proposal_action: 'BUY',
  proposal_label: 'Mua',
  proposal_by: 'TCB',
  proposal_date: '2026-09-21',
};

/** A ledger row with every horizon null unless given. */
const call = (over = {}) => ({
  id: 1,
  symbol: 'MSR',
  action: 'BUY',
  label_verbatim: 'Mua',
  session_date: '2026-09-21',
  ref_close: 52.6,
  ret_1d: null,
  ret_5d: null,
  ret_20d: null,
  ret_60d: null,
  ret_1d_vs_index: null,
  ret_5d_vs_index: null,
  ret_20d_vs_index: null,
  ret_60d_vs_index: null,
  ret_adjusted: true,
  ...over,
});

beforeAll(async () => {
  await i18n.changeLanguage('vi');
});

beforeEach(() => {
  jest.resetAllMocks();
  httpClient.get = jest.fn().mockResolvedValue(ok([ROW]));
  tcbNewsService.recos = jest.fn().mockResolvedValue(ok([]));
});

const renderPage = () =>
  render(
    <MemoryRouter>
      <Watchlist />
    </MemoryRouter>
  );

describe('Watchlist — the result column', () => {
  test('shows the longest ELAPSED horizon, labelled with which horizon it is', async () => {
    tcbNewsService.recos.mockResolvedValue(
      ok([call({ ret_1d: 0.0437, ret_5d: 0.08, ret_20d: 0.2205, ret_60d: null })]));
    renderPage();

    // 20d is the longest elapsed horizon; 60d has not run and must not be invented.
    await waitFor(() => expect(screen.getByText('+22.1%')).toBeInTheDocument());
    expect(screen.getByText(/· 20d/)).toBeInTheDocument();
    expect(screen.queryByText('+4.4%')).not.toBeInTheDocument();   // not the 1d mark
  });

  test('a 1-session-old call reports 1d rather than pretending to a longer horizon', async () => {
    tcbNewsService.recos.mockResolvedValue(ok([call({ ret_1d: 0.0437 })]));
    renderPage();

    await waitFor(() => expect(screen.getByText('+4.4%')).toBeInTheDocument());
    expect(screen.getByText(/· 1d/)).toBeInTheDocument();
  });

  test('a negative result is shown as negative, not as a magnitude', async () => {
    tcbNewsService.recos.mockResolvedValue(ok([call({ ret_20d: -0.1534 })]));
    renderPage();
    await waitFor(() => expect(screen.getByText('-15.3%')).toBeInTheDocument());
  });

  test('the index benchmark travels beside the number (EC-B7)', async () => {
    tcbNewsService.recos.mockResolvedValue(
      ok([call({ ret_20d: 0.2205, ret_20d_vs_index: 0.1402 })]));
    renderPage();

    // Real Vietnamese copy, not the key: "so với chỉ số +14.0%".
    await waitFor(() =>
      expect(screen.getByText(/so với chỉ số \+14\.0%/)).toBeInTheDocument());
  });

  test('a stored call with no elapsed horizon shows a dash and says why', async () => {
    tcbNewsService.recos.mockResolvedValue(ok([call()]));
    renderPage();

    await waitFor(() => expect(screen.getByText('MSR')).toBeInTheDocument());
    expect(screen.getByTitle(/chưa đủ thời gian để tính/i)).toBeInTheDocument();
  });

  test('a symbol with no stored call is distinguished from one not yet scored', async () => {
    tcbNewsService.recos.mockResolvedValue(ok([]));
    renderPage();

    await waitFor(() => expect(screen.getByText('MSR')).toBeInTheDocument());
    expect(screen.getByTitle(/Chưa có khuyến nghị TCB nào/i)).toBeInTheDocument();
  });

  test('an unadjusted mark is flagged, not presented as clean (Backlog #60)', async () => {
    tcbNewsService.recos.mockResolvedValue(
      ok([call({ ret_20d: -0.45, ret_adjusted: false })]));
    renderPage();

    await waitFor(() => expect(screen.getByText('-45.0%')).toBeInTheDocument());
    expect(screen.getByTitle(/giá chưa điều chỉnh/i)).toBeInTheDocument();
  });

  test('an adjusted mark carries no warning marker', async () => {
    tcbNewsService.recos.mockResolvedValue(
      ok([call({ ret_20d: 0.2205, ret_adjusted: true })]));
    renderPage();

    await waitFor(() => expect(screen.getByText('+22.1%')).toBeInTheDocument());
    expect(screen.queryByTitle(/giá chưa điều chỉnh/i)).not.toBeInTheDocument();
  });
});

describe('Watchlist — which call the number belongs to', () => {
  test('prefers the call from the session the row cites, over a newer one', async () => {
    tcbNewsService.recos.mockResolvedValue(ok([
      call({ id: 1, session_date: '2026-09-21', ret_20d: 0.2205 }),   // the cited one
      call({ id: 2, session_date: '2026-10-02', ret_20d: -0.3100 }),  // newer, not cited
    ]));
    renderPage();

    await waitFor(() => expect(screen.getByText('+22.1%')).toBeInTheDocument());
    expect(screen.queryByText('-31.0%')).not.toBeInTheDocument();
  });

  test('falls back to the newest call and names its session when none matches', async () => {
    tcbNewsService.recos.mockResolvedValue(ok([
      call({ id: 1, session_date: '2026-08-01', ret_20d: 0.05 }),
      call({ id: 2, session_date: '2026-10-02', ret_20d: 0.1900 }),
    ]));
    renderPage();

    await waitFor(() => expect(screen.getByText('+19.0%')).toBeInTheDocument());
    // An unlabelled number from a different call would be worse than none.
    expect(screen.getByText(/từ khuyến nghị ngày 2026-10-02/)).toBeInTheDocument();
  });

  test('a matching session is not labelled as coming from elsewhere', async () => {
    tcbNewsService.recos.mockResolvedValue(
      ok([call({ session_date: '2026-09-21', ret_20d: 0.2205 })]));
    renderPage();

    await waitFor(() => expect(screen.getByText('+22.1%')).toBeInTheDocument());
    expect(screen.queryByText(/từ khuyến nghị ngày/)).not.toBeInTheDocument();
  });

  test('a call for a different symbol is never borrowed', async () => {
    tcbNewsService.recos.mockResolvedValue(
      ok([call({ symbol: 'VND', ret_20d: 0.2205 })]));
    renderPage();

    await waitFor(() => expect(screen.getByText('MSR')).toBeInTheDocument());
    expect(screen.queryByText('+22.1%')).not.toBeInTheDocument();
    expect(screen.getByTitle(/Chưa có khuyến nghị TCB nào/i)).toBeInTheDocument();
  });
});

describe('Watchlist — the ledger is an annotation, not a dependency', () => {
  test('a ledger failure leaves the watchlist working and shows no error', async () => {
    tcbNewsService.recos.mockResolvedValue({ success: false, error: { message: 'boom' } });
    renderPage();

    await waitFor(() => expect(screen.getByText('MSR')).toBeInTheDocument());
    expect(screen.getByText('Masan High-Tech Materials')).toBeInTheDocument();
    expect(screen.queryByText(/boom/)).not.toBeInTheDocument();
  });

  test('a ledger that rejects outright is caught rather than blanking the screen', async () => {
    tcbNewsService.recos.mockRejectedValue(new Error('network down'));
    renderPage();

    await waitFor(() => expect(screen.getByText('MSR')).toBeInTheDocument());
    expect(screen.queryByText(/network down/)).not.toBeInTheDocument();
  });

  test('the watchlist failing is still reported to the operator', async () => {
    httpClient.get = jest.fn().mockResolvedValue(
      { success: false, error: { message: 'watchlist unavailable' } });
    renderPage();

    await waitFor(() =>
      expect(screen.getByText('watchlist unavailable')).toBeInTheDocument());
  });
});
