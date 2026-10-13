import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import TradeLog from './TradeLog';
import journalService from '../../../services/journalService';
import i18n from '../../../i18n';

jest.mock('../../../services/journalService');

const ok = (data) => ({ success: true, data });
const today = new Date().toISOString().split('T')[0];

beforeEach(() => {
  jest.resetAllMocks();
  journalService.getAccounts = jest.fn().mockResolvedValue(ok([{ id: 1, account_name: 'Main' }]));
  journalService.getTrades = jest.fn().mockResolvedValue(ok([]));
  journalService.getRiskInfo = jest.fn().mockResolvedValue(ok({}));
  journalService.getDailyPlans = jest.fn().mockResolvedValue(ok([]));
});

const renderPage = () =>
  render(
    <MemoryRouter>
      <TradeLog />
    </MemoryRouter>
  );

// This suite asserts on Vietnamese copy, so it must initialise the shared
// i18n instance and pin the language explicitly. Without the import,
// react-i18next runs uninitialised and `t('a.b.c')` returns the KEY, so every
// query for a translated string fails; without the explicit changeLanguage,
// the browser language detector decides, and jsdom reports en-US.
// (These components were internationalised in May 2026 — commits d4dcc00d and
// 2a3c7ce4 — and the tests, written earlier against hardcoded Vietnamese
// literals, were never given the harness to resolve them.)
beforeAll(async () => {
  await i18n.changeLanguage('vi');
});

describe("TradeLog — today's plan card", () => {
  test("renders today's plan when one exists for today", async () => {
    journalService.getDailyPlans.mockResolvedValue(
      ok([
        {
          id: 11,
          plan_date: today,
          new_trade_ideas: 'FPT breakout watch above 120; VNM mean-reversion',
          market_review: 'VN-Index oversold on daily; banking sector lagging',
        },
        {
          id: 10,
          plan_date: '2026-05-01',
          new_trade_ideas: 'Old plan from earlier',
        },
      ])
    );

    renderPage();

    const card = await screen.findByTestId('today-plan');
    expect(card).toBeInTheDocument();
    expect(screen.getByText(/FPT breakout watch above 120/)).toBeInTheDocument();
    expect(screen.getByText(/VN-Index oversold/)).toBeInTheDocument();
    // The older plan should not leak into the card
    expect(screen.queryByText(/Old plan from earlier/)).not.toBeInTheDocument();
  });

  test('shows the empty prompt when no plan exists for today', async () => {
    journalService.getDailyPlans.mockResolvedValue(
      ok([{ id: 10, plan_date: '2026-05-01', new_trade_ideas: 'older plan' }])
    );

    renderPage();
    await waitFor(() => expect(journalService.getDailyPlans).toHaveBeenCalled());

    expect(await screen.findByTestId('today-plan-empty')).toBeInTheDocument();
    expect(screen.getByText(/Chưa có kế hoạch cho hôm nay/)).toBeInTheDocument();
    expect(screen.queryByTestId('today-plan')).not.toBeInTheDocument();
  });

  test('renders no card at all when there is no selected account', async () => {
    journalService.getAccounts.mockResolvedValue(ok([]));

    renderPage();
    // Page renders the no-accounts CTA; the plan-card effect short-circuits
    // on missing selectedAccountId so getDailyPlans must not be called.
    await waitFor(() => expect(journalService.getAccounts).toHaveBeenCalled());
    expect(journalService.getDailyPlans).not.toHaveBeenCalled();
    expect(screen.queryByTestId('today-plan')).not.toBeInTheDocument();
    expect(screen.queryByTestId('today-plan-empty')).not.toBeInTheDocument();
  });
});
