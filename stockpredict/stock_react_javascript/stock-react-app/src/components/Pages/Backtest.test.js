import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import i18n from '../../i18n';
import Backtest from './Backtest';
import modelService from '../../services/modelService';

jest.mock('../../services/modelService');

const sampleResult = {
  symbol: 'FPT',
  model_type: 'xgboost',
  period: '2025-11-01 → 2026-05-01',
  total_predictions: 120,
  correct_direction: 78,
  direction_accuracy: 65.0, // backend returns a percentage (0–100), not a fraction
  mean_absolute_error: 0.5421,
  root_mean_squared_error: 0.7812,
  average_confidence: 0.74,
};

beforeEach(async () => {
  jest.resetAllMocks();
  // i18n is bootstrapped on import but jsdom's navigator would resolve to
  // English; these tests assert against the app's Vietnamese default copy.
  await i18n.changeLanguage('vi');
});

describe('Backtest page', () => {
  test('submits the form and renders metrics on success', async () => {
    modelService.runBacktest = jest.fn().mockResolvedValue({
      success: true,
      data: sampleResult,
    });

    render(<Backtest />);

    fireEvent.change(screen.getByLabelText(/Mã cổ phiếu/i), { target: { value: 'fpt' } });
    fireEvent.click(screen.getByRole('button', { name: /Chạy backtest/i }));

    const results = await screen.findByTestId('bt-results');
    expect(results).toBeInTheDocument();
    expect(screen.getByTestId('bt-direction-accuracy').textContent).toBe('65.00%');
    expect(screen.getByText(/78 \/ 120 dự đoán/)).toBeInTheDocument();
    expect(screen.getByText('0.5421')).toBeInTheDocument(); // MAE
    expect(screen.getByText('0.7812')).toBeInTheDocument(); // RMSE

    expect(modelService.runBacktest).toHaveBeenCalledWith(
      expect.objectContaining({ symbol: 'FPT', model_type: 'xgboost', prediction_horizon: 5 })
    );
  });

  test('shows the error message when the service fails', async () => {
    modelService.runBacktest = jest.fn().mockResolvedValue({
      success: false,
      error: 'No historical predictions found for backtest',
    });

    render(<Backtest />);
    fireEvent.click(screen.getByRole('button', { name: /Chạy backtest/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/No historical predictions/i);
    });
    expect(screen.queryByTestId('bt-results')).not.toBeInTheDocument();
  });

  test('rejects invalid date range without calling the service', async () => {
    modelService.runBacktest = jest.fn();

    render(<Backtest />);
    fireEvent.change(screen.getByLabelText(/Từ ngày/i), { target: { value: '2026-05-10' } });
    fireEvent.change(screen.getByLabelText(/Đến ngày/i), { target: { value: '2026-05-01' } });
    fireEvent.click(screen.getByRole('button', { name: /Chạy backtest/i }));

    expect(screen.getByRole('alert')).toHaveTextContent(/Ngày bắt đầu phải trước/i);
    expect(modelService.runBacktest).not.toHaveBeenCalled();
  });
});
