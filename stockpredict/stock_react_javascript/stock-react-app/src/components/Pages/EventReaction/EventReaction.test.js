// Smoke test: Event Reaction page renders in EN + VI with its input form,
// report section, and cross-sectional exposure section.
import React from 'react';
import { render, screen } from '@testing-library/react';
import i18n from '../../../i18n';
import EventReactionPage from './index';

// Avoid network: the service is only called on button clicks, but stub to be safe.
jest.mock('../../../services/eventReactionService', () => ({ __esModule: true, default: {} }));

async function setLang(lang) {
  await i18n.changeLanguage(lang);
}

describe('EventReaction page', () => {
  test('renders the measure form, report and exposure sections (EN)', async () => {
    await setLang('en');
    render(<EventReactionPage />);

    expect(screen.getByText('Measure an event')).toBeInTheDocument();
    expect(screen.getByText('Cross-sectional exposure')).toBeInTheDocument();
    // Empty-state hint before any measurement.
    expect(screen.getByText('Measure an event to add it to the report.')).toBeInTheDocument();
    // Exposure run button disabled until >=3 events.
    expect(screen.getByText('Measure at least 3 events.')).toBeInTheDocument();
  });

  test('renders Vietnamese content when language is vi', async () => {
    await setLang('vi');
    render(<EventReactionPage />);
    expect(screen.getByText('Đo một sự kiện')).toBeInTheDocument();
    expect(screen.getByText('Độ nhạy chéo')).toBeInTheDocument();
    await setLang('en');
  });
});
