// EM-1 / F2 — the compact volume verdict for the AI Insights page (FR-EM-V9).
//
// F1 put the full verdict on the Decision Console: a chip, an evidence row per
// Edwards & Magee condition, the citation. This is the compact form — name,
// verdict, and what volume did to the confidence — for a page that is already
// dense with other analysis.
//
// It shares `volumeVerdict.js` with PatternPanel, so the verdict vocabulary
// (including the suspect escalation) is defined once and cannot drift between
// the two screens.
import React from 'react';
import { render, screen, within } from '@testing-library/react';
import i18n from '../../i18n';
import ChartPatternsCompact from './ChartPatternsCompact';

beforeAll(async () => { await i18n.changeLanguage('en'); });

const pattern = (over = {}) => ({
  pattern_name: 'Head and Shoulders',
  pattern_type: 'bearish',
  found: true,
  confidence: 0.995,
  geometric_confidence: 0.917,
  volume_score: 0.783,
  volume_factor: 1.085,
  details: {},
  volume_evidence: {
    status: 'known', verdict: 'confirms', direction: 'bearish',
    components: {
      'right shoulder lighter than left': { verdict: 'confirms', value: 0.533, required: true },
    },
    baseline_window: 50,
  },
  ...over,
});

const suspect = pattern({
  pattern_name: 'Flag',
  pattern_type: 'bullish',
  confidence: 0.45,
  geometric_confidence: 0.66,
  volume_evidence: {
    // Card verdict "contradicts" with a "suspect" component — the escalation
    // case. Shared with PatternPanel via volumeVerdict.js precisely so this
    // behaves identically on both screens.
    status: 'known', verdict: 'contradicts', direction: 'bullish',
    components: {
      'flag volume markedly below the mast': { verdict: 'suspect', value: 1.273, required: true },
    },
    baseline_window: 50,
  },
});

const row = (name) => screen.getByText(name).closest('[data-testid="compact-pattern"]');

describe('ChartPatternsCompact', () => {
  test('renders a verdict per pattern', () => {
    render(<ChartPatternsCompact patterns={[pattern()]} />);
    expect(within(row('Head and Shoulders')).getByText('Volume confirms')).toBeInTheDocument();
  });

  test('shows what volume did to the confidence', () => {
    render(<ChartPatternsCompact patterns={[pattern()]} />);
    const el = row('Head and Shoulders');
    expect(within(el).getByText('92%')).toBeInTheDocument();
    expect(within(el).getByText('100%')).toBeInTheDocument();
  });

  test('shows one number when volume left the confidence alone', () => {
    const neutral = pattern({
      confidence: 0.68, geometric_confidence: 0.68,
      volume_evidence: { status: 'known', verdict: 'neutral', components: {}, baseline_window: 50 },
    });
    render(<ChartPatternsCompact patterns={[neutral]} />);
    expect(within(row('Head and Shoulders')).getAllByText('68%')).toHaveLength(1);
  });

  test('escalates to suspect exactly as the full panel does', () => {
    render(<ChartPatternsCompact patterns={[suspect]} />);
    expect(within(row('Flag')).getByText('Volume suspect')).toBeInTheDocument();
    expect(within(row('Flag')).queryByText('Volume contradicts')).not.toBeInTheDocument();
  });

  test('is compact: no evidence rows and no citation', () => {
    // The whole point of the compact form. The full evidence belongs to the
    // Decision Console, where there is room to read it.
    render(<ChartPatternsCompact patterns={[pattern()]} />);
    expect(screen.queryByText('right shoulder lighter than left')).not.toBeInTheDocument();
    expect(screen.queryByText(/E&M Ch/)).not.toBeInTheDocument();
  });

  test('a pattern with no volume evidence still lists, with no chip', () => {
    const bare = {
      pattern_name: 'Pennant', pattern_type: 'bullish', found: true,
      confidence: 0.66, details: {},
    };
    render(<ChartPatternsCompact patterns={[bare]} />);
    const el = row('Pennant');
    expect(within(el).getByText('66%')).toBeInTheDocument();
    ['Volume confirms', 'Volume neutral', 'Volume contradicts', 'Volume suspect']
      .forEach(l => expect(within(el).queryByText(l)).not.toBeInTheDocument());
    expect(within(el).queryByText('—')).not.toBeInTheDocument();
  });

  test('filters out patterns that were not found', () => {
    render(<ChartPatternsCompact patterns={[pattern({ found: false })]} />);
    expect(screen.queryByText('Head and Shoulders')).not.toBeInTheDocument();
  });

  test('renders nothing at all when there is nothing to show', () => {
    const { container } = render(<ChartPatternsCompact patterns={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  test('renders nothing before a scan has run', () => {
    const { container } = render(<ChartPatternsCompact patterns={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  test('stays silent while loading rather than flashing an empty card', () => {
    const { container } = render(<ChartPatternsCompact patterns={null} loading />);
    expect(container).toBeEmptyDOMElement();
  });

  test('a failed pattern scan does not break the page it sits on', () => {
    // This card is a best-effort extra on a page whose main content comes from
    // a different endpoint, so its own failure must be silent.
    const { container } = render(<ChartPatternsCompact patterns={null} error="boom" />);
    expect(container).toBeEmptyDOMElement();
  });

  test('surfaces a volume climax once', () => {
    const climax = { bar_index: 170, rvol_long: 6.381, progress_ratio: 0.0, window: 120 };
    render(<ChartPatternsCompact patterns={[pattern()]} volumeClimax={climax} />);
    expect(screen.getByText('Volume climax')).toBeInTheDocument();
  });

  test('translates into Vietnamese', async () => {
    await i18n.changeLanguage('vi');
    render(<ChartPatternsCompact patterns={[pattern(), suspect]} />);
    expect(screen.getByText('Khối lượng xác nhận')).toBeInTheDocument();
    expect(screen.getByText('Khối lượng đáng ngờ')).toBeInTheDocument();
    await i18n.changeLanguage('en');
  });
});
