// Smoke test: Event Reaction page renders its Overview tab (default) in the active
// language only — driven by the app's EN/VI switcher, not shown both at once — and,
// after switching to the Analysis tab, its input form, report and exposure sections.
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import i18n from '../../../i18n';
import EventReactionPage from './index';

// Avoid network: the service is only called on button clicks, but stub to be safe.
jest.mock('../../../services/eventReactionService', () => ({ __esModule: true, default: {} }));

async function setLang(lang) {
  await i18n.changeLanguage(lang);
}

describe('EventReaction page', () => {
  test('lands on the Overview tab in English, one language at a time', async () => {
    await setLang('en');
    render(<EventReactionPage />);

    // English overview is shown; the Vietnamese hero is NOT on the page.
    expect(screen.getByText('Trade the surprise, not the headline')).toBeInTheDocument();
    expect(screen.queryByText('Giao dịch phần bất ngờ, không phải bản tin')).not.toBeInTheDocument();
    // Analysis form is not mounted on the Overview tab.
    expect(screen.queryByText('Cross-sectional exposure')).not.toBeInTheDocument();
  });

  test('renders the measure form, report and exposure sections after switching to Analysis (EN)', async () => {
    await setLang('en');
    render(<EventReactionPage />);

    fireEvent.click(screen.getByRole('button', { name: /Analysis/i }));

    expect(screen.getByText('Measure an event')).toBeInTheDocument();
    expect(screen.getByText('Cross-sectional exposure')).toBeInTheDocument();
    // Empty-state hint before any measurement.
    expect(screen.getByText('Measure an event to add it to the report.')).toBeInTheDocument();
    // Exposure run button disabled until >=3 events.
    expect(screen.getByText('Measure at least 3 events.')).toBeInTheDocument();
  });

  test('Overview follows the switcher: shows Vietnamese when language is vi', async () => {
    await setLang('vi');
    render(<EventReactionPage />);

    // Vietnamese overview hero shown; the English hero is NOT present.
    expect(screen.getByText('Giao dịch phần bất ngờ, không phải bản tin')).toBeInTheDocument();
    expect(screen.queryByText('Trade the surprise, not the headline')).not.toBeInTheDocument();

    // Analysis tab content also localizes.
    fireEvent.click(screen.getByRole('button', { name: /Phân tích/i }));
    expect(screen.getByText('Đo một sự kiện')).toBeInTheDocument();
    expect(screen.getByText('Độ nhạy chéo')).toBeInTheDocument();
    await setLang('en');
  });
});
