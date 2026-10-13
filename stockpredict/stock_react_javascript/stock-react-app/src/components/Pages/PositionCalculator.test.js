import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import PositionCalculator from './PositionCalculator';
import i18n from '../../i18n';

// Inputs now have htmlFor/id linkage, so we can use the accessible
// getByLabelText API instead of indexing into role queries.
const LABELS = {
  equity: /Vốn tài khoản/i,
  risk: /Rủi ro tối đa/i,
  entry: /Giá vào/i,
  stop: /Giá stop/i,
};

const setInput = (which, value) => {
  const input = screen.getByLabelText(LABELS[which]);
  fireEvent.change(input, { target: { value: String(value) } });
};

const findShares = () => screen.getByTestId('pc-shares').textContent;

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
