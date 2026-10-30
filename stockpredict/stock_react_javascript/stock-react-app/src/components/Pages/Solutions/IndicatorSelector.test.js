/**
 * Backlog #104 / #105 — the covariate footgun, closed and asserted.
 *
 * WHAT THESE TESTS DEFEND. The selector used to offer 'past', 'future' and
 * 'both' for a technical indicator whenever the chosen model advertised
 * future-covariate support. A technical indicator can never be a future
 * covariate — SMA/RSI/MACD/Bollinger are deterministic functions of price, so
 * knowing them over the forecast horizon means knowing the future prices.
 *
 * The damage is not cosmetic. In a backtest the whole history is on hand, so a
 * 'future' indicator CAN be supplied and the model trains on information that
 * will not exist live: the backtest flatters itself and the live path
 * collapses. That is the leakage CLAUDE.md C1 forbids.
 *
 * The server refuses such a solution (plan_covariates). These tests assert the
 * UI cannot construct one in the first place, so the refusal is unreachable
 * rather than being the operator's first sight of the rule.
 */
import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import IndicatorSelector from './IndicatorSelector';
import indicatorService from '../../../services/indicatorService';

// Factory mock, not the auto-mock: indicatorService pulls in httpClient, which
// calls axios.create(...).interceptors.request.use(...) at import time. The
// auto-mock returns undefined from create() and the module throws before any
// test runs. (Same reason as AIInsights.test.js.)
jest.mock('axios', () => {
  const interceptors = { request: { use: jest.fn() }, response: { use: jest.fn() } };
  const instance = {
    interceptors,
    defaults: { headers: { common: {} } },
    get: jest.fn(), post: jest.fn(), put: jest.fn(), delete: jest.fn(),
  };
  const mocked = {
    interceptors, defaults: instance.defaults,
    get: jest.fn(), post: jest.fn(), create: jest.fn(() => instance),
  };
  mocked.default = mocked;
  return mocked;
});
jest.mock('../../../services/indicatorService');

// i18n is not initialised in the test env, so `t` returns the KEY. That is
// useful here: asserting on the key proves which string the component chose,
// independently of its wording in en.json or vi.json.
jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key, opts) => (opts?.type ? `${key}:${opts.type}` : key) }),
}));

const INDICATORS = [
  { id: 1, name: 'SMA', description: 'Simple moving average', type: 'trend',
    default_parameters: {} },
  { id: 2, name: 'RSI', description: 'Relative strength', type: 'momentum',
    default_parameters: {} },
];

const renderSelector = async (modelCovariateConfig) => {
  indicatorService.getAllIndicators.mockResolvedValue({
    trend: [INDICATORS[0]],
    momentum: [INDICATORS[1]],
    volatility: [],
    volume: [],
  });
  indicatorService.getSolutionIndicators.mockResolvedValue({});
  const utils = render(
    <IndicatorSelector solutionId={null} onIndicatorsChange={() => {}}
                       modelCovariateConfig={modelCovariateConfig} />
  );
  // Wait for the SELECT to exist, not merely for the fetch to have been
  // called: the component renders a loading state first, and asserting on the
  // call let one test pass on timing luck while its twin failed.
  await waitFor(() =>
    expect(utils.container.querySelector('.indicator-select')).not.toBeNull());
  return utils;
};

/** Choose an indicator, which is what makes the covariate block render. */
const pickIndicator = async (container, value = '1') => {
  fireEvent.change(container.querySelector('.indicator-select'), { target: { value } });
  await waitFor(() =>
    expect(document.querySelector('.covariate-type-fixed')).not.toBeNull());
};

const BOTH = { hasPastCovariate: true, hasFutureCovariate: true };
const PAST_ONLY = { hasPastCovariate: true, hasFutureCovariate: false };
const FUTURE_ONLY = { hasPastCovariate: false, hasFutureCovariate: true };

describe('IndicatorSelector covariate type (#104/#105)', () => {
  beforeEach(() => jest.clearAllMocks());

  test('offers no covariate-type dropdown at all', async () => {
    // THE REGRESSION GUARD. A model advertising BOTH capabilities was the case
    // that produced ['past','future','both']; there must now be no selectable
    // covariate control, because there is nothing to select between.
    //
    // `pickIndicator` IS LOAD-BEARING. The first draft of this test asserted
    // on the DOM without choosing an indicator — but the covariate block only
    // renders once one is chosen, so it asserted on a region that did not
    // exist and passed vacuously. Mutation-checked: restoring the old
    // three-option <select> left all eight tests green. With the pick, the
    // same mutation fails this test and the next.
    const { container } = await renderSelector(BOTH);
    await pickIndicator(container);
    expect(document.querySelector('.covariate-type-select')).toBeNull();
  });

  test('never renders a future or both option, even for a both-capable model', async () => {
    const { container } = await renderSelector(BOTH);
    await pickIndicator(container);
    const options = Array.from(document.querySelectorAll('.covariate-type-selector option'))
      .map(o => (o.getAttribute('value') || '').toLowerCase());
    expect(options).not.toContain('future');
    expect(options).not.toContain('both');
  });

  test('a future-capable model is told where future covariates come from', async () => {
    // #104's substance: "this model supports future covariates" must not read
    // as an invitation to mark an indicator 'future'. The calendar is the real
    // source and the server adds it automatically.
    await renderSelector(BOTH);
    expect(screen.getByText(/indicator_selector\.calendar_future_note/))
      .toBeInTheDocument();
  });

  test('a past-only model gets no calendar note', async () => {
    // It would be false there: the model cannot take future covariates at all.
    await renderSelector(PAST_ONLY);
    expect(screen.queryByText(/indicator_selector\.calendar_future_note/))
      .toBeNull();
  });

  test('no model selected renders neither the note nor a warning', async () => {
    await renderSelector(null);
    expect(screen.queryByText(/calendar_future_note/)).toBeNull();
    expect(screen.queryByText(/model_rejects_indicators/)).toBeNull();
  });
});

describe('IndicatorSelector future-only models (#105)', () => {
  beforeEach(() => jest.clearAllMocks());

  test('warns that a future-only model cannot use indicators', async () => {
    // Found in Phase 2b by fitting: darts 0.48.1 RNNModel takes FUTURE
    // covariates and not past ones. Since an indicator can only be a past
    // covariate, such a solution has its indicators refused by the server.
    // Saying so here beats letting the operator configure four and fail later.
    const { container } = await renderSelector(FUTURE_ONLY);
    await pickIndicator(container);
    expect(screen.getByRole('alert')).toHaveTextContent(
      /indicator_selector\.model_rejects_indicators/);
  });

  test('a past-capable model shows no such warning', async () => {
    const { container } = await renderSelector(PAST_ONLY);
    await pickIndicator(container);
    expect(screen.queryByRole('alert')).toBeNull();
  });
});

describe('IndicatorSelector saved payload (#105)', () => {
  beforeEach(() => jest.clearAllMocks());

  test("a legacy 'future' row is coerced to past rather than re-sent", async () => {
    // Solutions saved before this change can carry covariate_type 'future' or
    // 'both' in solution_indicators. Re-sending that verbatim would hit the
    // server's refusal; the operator should see the corrected value instead.
    indicatorService.getAllIndicators.mockResolvedValue({
      trend: [INDICATORS[0]], momentum: [], volatility: [], volume: [],
    });
    // `covariate_type: 'future'` is the stored legacy value under test. The
    // loader reads `.id` (not `.indicator_id`), and getSolutionIndicators only
    // runs when a solutionId is present — hence the id below.
    indicatorService.getSolutionIndicators.mockResolvedValue({
      trend: { id: 1, covariate_type: 'future', parameters: {} },
    });
    render(
      <IndicatorSelector solutionId={7} onIndicatorsChange={() => {}}
                         modelCovariateConfig={BOTH} />
    );
    await waitFor(() => expect(indicatorService.getSolutionIndicators).toHaveBeenCalledWith(7));
    await waitFor(() => {
      expect(document.querySelector('.covariate-type-fixed')).not.toBeNull();
    });
    // Whatever was stored, the UI now states past — the only truthful value.
    expect(document.querySelector('.covariate-type-fixed').textContent)
      .toMatch(/indicator_selector\.past_label/);
  });
});
