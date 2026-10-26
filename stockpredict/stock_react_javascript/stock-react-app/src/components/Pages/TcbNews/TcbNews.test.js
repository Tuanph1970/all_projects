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
import i18n from '../../../i18n';


jest.mock('../../../services/tcbNewsService');

// Backlog #71. The root cause was not a missing import — this suite
// MOCKED react-i18next with a stub whose `t()` returned the key:
//
//   jest.mock('react-i18next', () => ({
//     useTranslation: () => ({ t: (key, opts) => ... key) }),
//   }));
//
// The stub is gone. Do not reinstate it: it is what made the suite
// self-confirming. This suite used to query the raw i18n KEYS
// (`getByText('Phân tích')`) and passed only because it never
// initialised the shared instance — uninitialised, react-i18next's `t()`
// returns the key, so the component rendered the key and the assertion
// matched it. Eighteen green tests that proved nothing about what a user
// sees, and they would have flipped red the moment anyone added the import.
//
// With the real module and the shared instance initialised, every query
// below goes through the real Vietnamese copy. A missing or renamed
// translation now FAILS this suite, which is the point.
//
// Long notes are matched on a distinctive fragment rather than the full
// string: the assertion should survive a copy edit (the #58 rewrite of
// `capital_adjusted_note` is exactly that case) while still proving the
// translated text reached the DOM. Interpolated strings — {{count}},
// {{symbol}}, {{date}}, {{scored}} — must be regexes for the same reason.
beforeAll(async () => {
  await i18n.changeLanguage('vi');
});

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
  userEvent.type(screen.getByLabelText('Nội dung email'), text);

const click = (el) => userEvent.click(el);

test('parse sends the pasted content and stores nothing', async () => {
  render(<TcbNews />);
  paste();
  click(screen.getByText('Phân tích'));

  await waitFor(() => expect(tcbNewsService.preview).toHaveBeenCalled());
  expect(tcbNewsService.preview.mock.calls[0][0]).toBe('some email body');
  expect(tcbNewsService.save).not.toHaveBeenCalled();
});

test('the parsed session date overrides the default date', async () => {
  render(<TcbNews />);
  paste();
  click(screen.getByText('Phân tích'));

  await waitFor(() =>
    expect(screen.getByLabelText('Phiên giao dịch')).toHaveValue('2026-09-21'));
});

test('the preview shows the recommendation with its verbatim TCB wording', async () => {
  render(<TcbNews />);
  paste();
  click(screen.getByText('Phân tích'));

  // Backlog #55 made the ticker and action editable, so these are form controls now,
  // not text nodes — a correction has to be possible without re-pasting the mail.
  expect(await screen.findByDisplayValue('NTP')).toBeInTheDocument();
  expect(screen.getByLabelText(/Hành động cho NTP/)).toHaveValue('WATCH');
  // The verbatim wording stays plain text and stays uneditable (EC-B4).
  expect(screen.getByText('Chờ mua')).toBeInTheDocument();
});

test('save pushes the ticked recommendation with the confirmed session date', async () => {
  render(<TcbNews />);
  paste();
  click(screen.getByText('Phân tích'));
  await screen.findByDisplayValue('NTP');

  click(screen.getByText(/Lưu & thêm/));
  await waitFor(() => expect(tcbNewsService.save).toHaveBeenCalled());
  expect(tcbNewsService.save.mock.calls[0][0]).toMatchObject({
    sessionDate: '2026-09-21',
    pushSymbols: ['NTP'],
  });
});

test('unticking a recommendation keeps it off the watchlist', async () => {
  render(<TcbNews />);
  paste();
  click(screen.getByText('Phân tích'));

  const tick = await screen.findByLabelText(/vào danh mục theo dõi/);
  expect(tick).toBeChecked();          // a recognised action is pre-ticked
  click(tick);

  click(screen.getByText(/Lưu & thêm/));
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
  click(screen.getByText('Phân tích'));

  expect(await screen.findByLabelText(/vào danh mục theo dõi/)).not.toBeChecked();
  expect(screen.getByText(/chưa nhận diện được/)).toBeInTheDocument();
});

test('a duplicate paste is reported without clearing the form', async () => {
  tcbNewsService.save.mockResolvedValue({
    success: true,
    data: { created: false, mail: { ...PREVIEW, id: 1, session_date: '2026-09-21' }, pushed: [] },
  });
  render(<TcbNews />);
  paste();
  click(screen.getByText('Phân tích'));
  await screen.findByDisplayValue('NTP');
  click(screen.getByText(/Lưu & thêm/));

  expect(await screen.findByText(/đã được lưu trước đó/)).toBeInTheDocument();
  expect(screen.getByLabelText('Nội dung email')).toHaveValue('some email body');
});

test('a parse failure surfaces the error and offers no save', async () => {
  tcbNewsService.preview.mockResolvedValue({
    success: false, error: { message: 'boom' } });
  render(<TcbNews />);
  paste();
  click(screen.getByText('Phân tích'));

  expect(await screen.findByText('boom')).toBeInTheDocument();
  expect(screen.getByText(/Lưu & thêm/).closest('button')).toBeDisabled();
});

test('save is disabled until the email has been parsed', async () => {
  render(<TcbNews />);
  paste();
  expect(screen.getByText(/Lưu & thêm/).closest('button')).toBeDisabled();
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

  expect(await screen.findByText('Nhật ký khuyến nghị')).toBeInTheDocument();
  expect(screen.getByText('+1.2%')).toBeInTheDocument();
  expect(screen.getByText('-3.1%')).toBeInTheDocument();
  expect(screen.getByText('+8.4%')).toBeInTheDocument();
});

test('an unelapsed horizon shows a dash, never a zero', async () => {
  withLedger([SCORED], { success: false, error: { response: { data: { scored_calls: 1 } } } });
  render(<TcbNews />);
  await screen.findByText('Nhật ký khuyến nghị');
  // ret_60d is null -> "—"; a "0.0%" here would read as "flat" rather than "unknown".
  expect(screen.getAllByText('—').length).toBeGreaterThan(0);
  expect(screen.queryByText('+0.0%')).not.toBeInTheDocument();
});

test('the aggregate is withheld below the minimum and says how far off it is', async () => {
  withLedger([SCORED], { success: false, error: { response: { status: 409, data: {
    scored_calls: 7, detail: 'not reportable yet: 7 scored call(s), 30 required' } } } });
  render(<TcbNews />);

  expect(await screen.findByText(/Chưa đủ dữ liệu để công bố/)).toBeInTheDocument();
  // Was `getByText(/"scored":7/)` — the removed stub serialised the
  // interpolation options as JSON, so this asserted on a string that never
  // reached a user. The real sentence names both the count so far and the
  // threshold, which is what "says how far off it is" meant.
  expect(screen.getByText(/mới có 7 khuyến nghị/)).toBeInTheDocument();
  expect(screen.getByText(/đủ 30/)).toBeInTheDocument();
  expect(screen.queryByText('Tỷ lệ đúng của TCB')).not.toBeInTheDocument();
});

test('the record renders the hit rate beside its benchmark', async () => {
  withLedger([SCORED], { success: true, data: {
    total_calls: 40, scored_calls: 35, min_calls: 30, reportable: true,
    horizons: { '20d': { n: 35, mean_return: 0.042, mean_excess_return: 0.018,
      directional_n: 30, hit_rate: 0.6, benchmark_hit_rate: 0.5 } },
    by_action: {},
  } });
  render(<TcbNews />);

  expect(await screen.findByText('Tỷ lệ đúng của TCB')).toBeInTheDocument();
  expect(screen.getByText('60%')).toBeInTheDocument();   // TCB
  expect(screen.getByText('50%')).toBeInTheDocument();   // the benchmark it must beat
  expect(screen.getByText('+4.2%')).toBeInTheDocument();
  expect(screen.getByText('+1.8%')).toBeInTheDocument();
  // A fragment unique to the note: "Chuẩn so sánh" alone also opens the
  // col_benchmark column header, so it matches two elements.
  expect(screen.getByText(/chỉ thực sự có năng lực/)).toBeInTheDocument();
});

test('scoring now re-reads the ledger and the record', async () => {
  withLedger([SCORED], { success: false, error: { response: { data: { scored_calls: 1 } } } });
  tcbNewsService.score.mockResolvedValue({ success: true, data: { scored: 1 } });
  render(<TcbNews />);
  await screen.findByText('Nhật ký khuyến nghị');

  tcbNewsService.recos.mockClear();
  click(screen.getByText('Chấm điểm ngay'));

  await waitFor(() => expect(tcbNewsService.score).toHaveBeenCalled());
  await waitFor(() => expect(tcbNewsService.recos).toHaveBeenCalled());
});

test('the raw-close warning fires only when a symbol lacked an adjusted close', async () => {
  withLedger([SCORED], { success: false, error: { response: { data: { scored_calls: 1 } } } });
  render(<TcbNews />);
  expect(await screen.findByText(/giá đóng cửa thô/)).toBeInTheDocument();
});

test('adjusted returns carry no raw-close warning', async () => {
  // The normal case after Backlog #56: stock-data-service records the adjusted close.
  withLedger([{ ...SCORED, ret_adjusted: true }],
    { success: false, error: { response: { data: { scored_calls: 1 } } } });
  render(<TcbNews />);
  await screen.findByText('Nhật ký khuyến nghị');
  expect(screen.queryByText(/giá đóng cửa thô/)).not.toBeInTheDocument();
});

test('the capital-adjusted note shows on any scored return, adjusted or not', async () => {
  withLedger([{ ...SCORED, ret_adjusted: true }],
    { success: false, error: { response: { data: { scored_calls: 1 } } } });
  render(<TcbNews />);
  expect(await screen.findByText(/điều chỉnh theo sự kiện thay đổi số lượng/)).toBeInTheDocument();
});

test('no caveat before anything has been scored', async () => {
  withLedger([{ ...SCORED, ref_close: null, ret_1d: null, ret_5d: null,
    ret_20d: null, ret_60d: null, ret_20d_vs_index: null }],
  { success: false, error: { response: { data: { scored_calls: 0 } } } });
  render(<TcbNews />);
  await screen.findByText('Nhật ký khuyến nghị');
  expect(screen.queryByText(/giá đóng cửa thô/)).not.toBeInTheDocument();
  expect(screen.queryByText(/điều chỉnh theo sự kiện thay đổi số lượng/)).not.toBeInTheDocument();
});


// ---------------------------------------------------------------------------
// Correcting a misparsed call (Backlog #55)
//
// Unticking a wrong ticker does not fix the call, it LOSES it: the mail still stores
// the recommendation and the watchlist never sees it. These protect the fix path, and
// in particular that an edit actually reaches the server — which re-parses `content`,
// so a correction left out of the payload is silently discarded.
// ---------------------------------------------------------------------------

const parseAndWait = async () => {
  render(<TcbNews />);
  paste();
  click(screen.getByText('Phân tích'));
  return screen.findByDisplayValue('NTP');
};

test('a corrected ticker is sent as a correction, not just displayed', async () => {
  const ticker = await parseAndWait();
  await userEvent.clear(ticker);
  await userEvent.type(ticker, 'NTL');

  click(screen.getByText(/Lưu & thêm/));
  await waitFor(() => expect(tcbNewsService.save).toHaveBeenCalled());

  const sent = tcbNewsService.save.mock.calls[0][0];
  expect(sent.corrections).toEqual([
    { index: 0, from_symbol: 'NTP', symbol: 'NTL' },
  ]);
});

test('the CORRECTED ticker is what gets pushed to the watchlist', async () => {
  const ticker = await parseAndWait();
  await userEvent.clear(ticker);
  await userEvent.type(ticker, 'NTL');

  click(screen.getByText(/Lưu & thêm/));
  await waitFor(() => expect(tcbNewsService.save).toHaveBeenCalled());

  // Pushing the parser's wrong ticker would defeat the point of fixing it.
  expect(tcbNewsService.save.mock.calls[0][0].pushSymbols).toEqual(['NTL']);
});

test('correcting a ticker does not lose its tick', async () => {
  // The selection used to be keyed by symbol, so renaming the ticker silently
  // deselected the call — the exact failure this feature exists to prevent.
  const ticker = await parseAndWait();
  await userEvent.clear(ticker);
  await userEvent.type(ticker, 'NTL');

  expect(screen.getByLabelText(/Đưa NTL vào danh mục|NTL/)).toBeChecked();
});

test('a corrected action is sent and reaches the push', async () => {
  await parseAndWait();
  await userEvent.selectOptions(screen.getByLabelText(/Hành động cho NTP/), 'BUY');

  click(screen.getByText(/Lưu & thêm/));
  await waitFor(() => expect(tcbNewsService.save).toHaveBeenCalled());

  expect(tcbNewsService.save.mock.calls[0][0].corrections).toEqual([
    { index: 0, from_symbol: 'NTP', action: 'BUY' },
  ]);
});

test('an unknown action can be resolved, and the warning then clears', async () => {
  tcbNewsService.preview.mockResolvedValue({
    success: true,
    data: { ...PREVIEW, recos: [{ symbol: 'NTP', action: null, label_verbatim: 'Mua gom dần' }] },
  });
  await parseAndWait();
  expect(screen.getByText(/chưa nhận diện được/i)).toBeInTheDocument();

  await userEvent.selectOptions(screen.getByLabelText(/Hành động cho NTP/), 'BUY');

  // A warning that survives its own fix teaches people to ignore warnings.
  await waitFor(() =>
    expect(screen.queryByText(/chưa nhận diện được/i)).not.toBeInTheDocument());
});

test('an untouched preview sends no corrections at all', async () => {
  await parseAndWait();
  click(screen.getByText(/Lưu & thêm/));
  await waitFor(() => expect(tcbNewsService.save).toHaveBeenCalled());

  expect(tcbNewsService.save.mock.calls[0][0].corrections).toEqual([]);
});

test('retyping the same ticker is not reported as a correction', async () => {
  const ticker = await parseAndWait();
  await userEvent.clear(ticker);
  await userEvent.type(ticker, 'NTP');

  click(screen.getByText(/Lưu & thêm/));
  await waitFor(() => expect(tcbNewsService.save).toHaveBeenCalled());

  // The audit trail only means something if it records real changes.
  expect(tcbNewsService.save.mock.calls[0][0].corrections).toEqual([]);
});

test('a pending correction is announced before saving', async () => {
  const ticker = await parseAndWait();
  await userEvent.clear(ticker);
  await userEvent.type(ticker, 'NTL');

  expect(await screen.findByText(/chỉnh sửa sẽ được lưu/)).toBeInTheDocument();
});

test('the verbatim label has no editable control (EC-B4)', async () => {
  await parseAndWait();
  // "Chờ mua" is what TCBS wrote; a correction changes our normalisation, never that.
  expect(screen.getByText('Chờ mua').tagName).toBe('TD');
  expect(screen.queryByDisplayValue('Chờ mua')).not.toBeInTheDocument();
});
