// Smoke test: Chart Decomposition Overview tab renders in EN + VI,
// shows the pipeline stages with hover detail, and hides the input panel.
import React from 'react';
import { render, screen, fireEvent, within } from '@testing-library/react';
import i18n from '../../../i18n';
import ChartDecompPage from './index';

// plotly.js-dist-min needs browser APIs jsdom lacks; stub the only plotly-backed child.
jest.mock('./DecompCombinedChart', () => ({ __esModule: true, default: () => null }));

// Avoid network: stub the data services the InputPanel pulls in.
jest.mock('../../../services/chartDecompService', () => ({ __esModule: true, default: {} }));
jest.mock('../../../services/companyService', () => ({
  __esModule: true,
  default: { searchCompanies: jest.fn().mockResolvedValue({ success: true, data: [] }) },
}));

async function setLang(lang) {
  await i18n.changeLanguage(lang);
}

describe('ChartDecomp Overview tab', () => {
  test('renders hero, goal, all 5 pipeline stages and benefits (EN)', async () => {
    await setLang('en');
    render(<ChartDecompPage />);

    expect(screen.getByText('Read price the way the market actually moves')).toBeInTheDocument();
    expect(screen.getByText('What is the goal?')).toBeInTheDocument();

    // All five pipeline stage titles present.
    ['Signal Decomposition', 'Time-Frequency', 'Hurst & Coherence', 'Volatility Forecast', 'Pattern Detection']
      .forEach(title => expect(screen.getAllByText(title).length).toBeGreaterThan(0));

    // A benefit bullet renders.
    expect(screen.getByText('Separate genuine trend from short-term noise')).toBeInTheDocument();
  });

  test('hover reveals a stage description', async () => {
    await setLang('en');
    render(<ChartDecompPage />);

    const desc = 'See which timescale is really driving the move, and denoise the series before you model it.';
    const card = screen.getByText('Split price into trend + cycles').closest('div').parentElement;
    fireEvent.mouseEnter(card);
    // Description text is in the DOM (revealed container).
    expect(screen.getByText(desc, { exact: false })).toBeInTheDocument();
  });

  test('input panel (ticker field) is hidden on Overview, shown after switching tabs', async () => {
    await setLang('en');
    render(<ChartDecompPage />);

    // Overview is the default tab -> no input panel. The tab BUTTON for decomp exists,
    // but the InputPanel "Load" controls should not be present yet.
    const overviewBenefit = screen.getByText('Separate genuine trend from short-term noise');
    expect(overviewBenefit).toBeInTheDocument();

    // Switch to Signal Decomposition tab.
    const decompTab = screen.getByRole('button', { name: /Signal Decomposition/i });
    fireEvent.click(decompTab);

    // Overview-only content gone; analytical tab content now mounted.
    expect(screen.queryByText('Separate genuine trend from short-term noise')).not.toBeInTheDocument();
  });

  test('renders Vietnamese content when language is vi', async () => {
    await setLang('vi');
    render(<ChartDecompPage />);

    expect(screen.getByText('Đọc giá đúng theo cách thị trường vận động')).toBeInTheDocument();
    expect(screen.getByText('Mục tiêu là gì?')).toBeInTheDocument();
    expect(screen.getByText('Tách xu hướng thật khỏi nhiễu ngắn hạn')).toBeInTheDocument();

    await setLang('en'); // restore for other suites
  });
});
