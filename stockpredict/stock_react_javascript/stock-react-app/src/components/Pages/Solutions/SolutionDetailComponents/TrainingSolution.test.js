/**
 * Backlog #106 — news as PAST covariates, from the training form.
 *
 * WHAT THESE DEFEND. Two things the operator can get wrong and one the UI must
 * not get wrong. The operator can leave news off (the default, because on
 * today's corpus the columns are zero for almost every bar) or switch it on and
 * pick a decay half-life. The UI must send both fields as set, and must never
 * offer news as a FUTURE covariate — tomorrow's coverage is not knowable today,
 * the same rule #104/#105 enforce for indicators (CLAUDE.md C1).
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import TrainingSolution from './TrainingSolution';
import httpClient from '../../../../services/httpClient';

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
jest.mock('../../../../services/httpClient');
jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k) => k }),
}));
// ModelDetail fetches on mount and is not what these tests are about.
jest.mock('../../models/ModelDetail', () => () => <div data-testid="model-detail" />);

const solution = {
  id: 7,
  start_training_date: '2023-01-01',
  end_training_date: '2026-07-31',
};

function setup() {
  httpClient.post.mockResolvedValue({ success: true, data: { status: 'training' } });
  httpClient.get.mockResolvedValue({ success: true, data: {} });
  return render(<TrainingSolution solution={solution} models={[]} />);
}

async function train() {
  fireEvent.click(screen.getByRole('button', { name: /train/i }));
  await waitFor(() => expect(httpClient.post).toHaveBeenCalled());
  return httpClient.post.mock.calls[0][1];
}

afterEach(() => jest.clearAllMocks());

describe('TrainingSolution news covariates (#106)', () => {
  it('leaves news off by default, matching the backend default', async () => {
    setup();
    const body = await train();
    expect(body.include_news).toBe(false);
  });

  it('hides the half-life until news is actually switched on', () => {
    setup();
    expect(screen.queryByLabelText('solutions.news_halflife')).toBeNull();
    fireEvent.click(screen.getByLabelText('solutions.include_news'));
    expect(screen.getByLabelText('solutions.news_halflife')).toBeInTheDocument();
  });

  it('sends include_news once the operator switches it on', async () => {
    setup();
    fireEvent.click(screen.getByLabelText('solutions.include_news'));
    const body = await train();
    expect(body.include_news).toBe(true);
  });

  it('sends the half-life the operator chose', async () => {
    setup();
    fireEvent.click(screen.getByLabelText('solutions.include_news'));
    fireEvent.change(screen.getByLabelText('solutions.news_halflife'), {
      target: { value: '9' },
    });
    const body = await train();
    expect(body.news_halflife_days).toBe(9);
  });

  it('falls back to the default rather than sending an empty half-life', async () => {
    // Clearing a number input yields '', and Number('') is 0 — which the series
    // builder refuses outright. The backend clamps too, but the UI should not
    // send a value it knows is unusable.
    setup();
    fireEvent.click(screen.getByLabelText('solutions.include_news'));
    fireEvent.change(screen.getByLabelText('solutions.news_halflife'), {
      target: { value: '' },
    });
    const body = await train();
    expect(body.news_halflife_days).toBeGreaterThan(0);
  });

  it('explains that zero means no coverage, not neutral news', () => {
    setup();
    fireEvent.click(screen.getByLabelText('solutions.include_news'));
    expect(screen.getByText(/solutions.news_covariate_note/)).toBeInTheDocument();
  });

  it('offers no way to mark news as a future covariate', () => {
    setup();
    fireEvent.click(screen.getByLabelText('solutions.include_news'));
    // A negative assertion is only meaningful once the block that would carry
    // the control is on screen — the lesson from #104/#105's vacuous guards.
    expect(screen.getByLabelText('solutions.include_news')).toBeInTheDocument();
    expect(screen.queryByText(/future/i)).toBeNull();
    expect(screen.queryByRole('combobox')).toBeNull();
  });
});
