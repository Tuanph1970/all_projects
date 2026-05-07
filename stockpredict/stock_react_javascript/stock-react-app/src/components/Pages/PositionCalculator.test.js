import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import PositionCalculator from './PositionCalculator';

// Inputs are number-type, so RTL exposes them as 'spinbutton' role.
// Order matches DOM source: equity, riskPct, entry, stop.
const NUMERIC = { equity: 0, risk: 1, entry: 2, stop: 3 };

const setInput = (which, value) => {
  const inputs = screen.getAllByRole('spinbutton');
  fireEvent.change(inputs[NUMERIC[which]], { target: { value: String(value) } });
};

const findShares = () => {
  const heading = screen.getByText(/Số cổ phiếu/i);
  return heading.parentElement.querySelector('div:nth-child(2)').textContent;
};

describe('PositionCalculator', () => {
  test('renders with sensible defaults and computes a position size', () => {
    render(<PositionCalculator />);
    // Defaults: equity=100,000,000, risk=2%, entry=100, stop=95 (long)
    // Risk amount = 100M * 0.02 = 2M
    // Per-share risk = |100 - 95| = 5
    // Shares = floor(2M / 5) = 400,000
    expect(findShares()).toBe('400.000');
  });

  test('warns when long stop is at or above entry', () => {
    render(<PositionCalculator />);
    setInput('stop', 105);
    expect(
      screen.getByText(/Long, stop phải thấp hơn giá vào/i)
    ).toBeInTheDocument();
  });

  test('switching to short with appropriate stop clears the warning', () => {
    render(<PositionCalculator />);
    fireEvent.click(screen.getByRole('button', { name: /^Short$/i }));
    setInput('entry', 100);
    setInput('stop', 105);
    expect(screen.queryByText(/Long, stop/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Short, stop/i)).not.toBeInTheDocument();
  });

  test('R-multiple targets render in correct direction', () => {
    render(<PositionCalculator />);
    // entry=100, stop=95 long: 1R=105, 2R=110, 3R=115
    expect(screen.getByText('105')).toBeInTheDocument();
    expect(screen.getByText('110')).toBeInTheDocument();
    expect(screen.getByText('115')).toBeInTheDocument();
  });

  test('zero per-share risk renders empty result', () => {
    render(<PositionCalculator />);
    setInput('stop', 100);  // same as entry
    expect(screen.getByText(/Nhập các tham số/i)).toBeInTheDocument();
  });
});
