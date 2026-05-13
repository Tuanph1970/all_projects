import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import DailyPlanning from './DailyPlanning';
import journalService from '../../../services/journalService';

jest.mock('../../../services/journalService');

const ok = (data) => ({ success: true, data });

const sampleAccount = { id: 1, account_name: 'Main' };

beforeEach(() => {
  jest.resetAllMocks();
  journalService.getAccounts = jest.fn().mockResolvedValue(ok([sampleAccount]));
  journalService.getDailyPlans = jest.fn().mockResolvedValue(ok([]));
  journalService.getWeeklyReviews = jest.fn().mockResolvedValue(ok([]));
});

const renderPage = () =>
  render(
    <MemoryRouter>
      <DailyPlanning />
    </MemoryRouter>
  );

describe('DailyPlanning — last-week adjustments carry-forward', () => {
  test('renders adjustments as bullets when the latest weekly review has them', async () => {
    journalService.getWeeklyReviews.mockResolvedValue(
      ok([
        {
          id: 7,
          week_start: '2026-05-04',
          key_adjustments:
            'Tighten stops on breakouts\nAvoid trading the first 30 minutes\nSize down on choppy days',
        },
      ])
    );

    renderPage();

    const card = await screen.findByTestId('last-adjustments');
    expect(card).toBeInTheDocument();
    expect(screen.getByText(/Tighten stops on breakouts/)).toBeInTheDocument();
    expect(screen.getByText(/Avoid trading the first 30 minutes/)).toBeInTheDocument();
    expect(screen.getByText(/Size down on choppy days/)).toBeInTheDocument();

    // Asks for the most recent review only (limit=1)
    expect(journalService.getWeeklyReviews).toHaveBeenCalledWith(1, 1, 0);
  });

  test('does not render the card when there are no reviews', async () => {
    journalService.getWeeklyReviews.mockResolvedValue(ok([]));

    renderPage();

    // Wait for page to settle (accounts loaded → header rendered)
    await screen.findByText(/Kế Hoạch Hàng Ngày/);
    await waitFor(() => expect(journalService.getWeeklyReviews).toHaveBeenCalled());

    expect(screen.queryByTestId('last-adjustments')).not.toBeInTheDocument();
  });

  test('does not render the card when key_adjustments is empty', async () => {
    journalService.getWeeklyReviews.mockResolvedValue(
      ok([{ id: 1, week_start: '2026-05-04', key_adjustments: '' }])
    );

    renderPage();
    await screen.findByText(/Kế Hoạch Hàng Ngày/);
    await waitFor(() => expect(journalService.getWeeklyReviews).toHaveBeenCalled());

    expect(screen.queryByTestId('last-adjustments')).not.toBeInTheDocument();
  });
});
