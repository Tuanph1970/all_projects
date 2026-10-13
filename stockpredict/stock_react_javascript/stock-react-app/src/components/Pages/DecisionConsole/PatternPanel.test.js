// EM-1 / F1 — PatternPanel renders the volume verdict (FR-EM-V9).
//
// The backend (V4–V7) returns, per pattern: `geometric_confidence` and the
// composite `confidence`, a `volume_score`/`volume_factor`, and a
// `volume_evidence` whose `components` map is one row per Edwards & Magee
// condition with its verdict and the figure behind it. This suite pins the
// four things FR-EM-V9 asks the panel to do with that payload:
//
//   1. a verdict chip per card — confirms / neutral / contradicts / suspect;
//   2. geometric vs composite confidence shown distinctly enough that a user
//      can see volume moved the number;
//   3. a pattern with no volume evidence renders exactly as it did before —
//      no empty row, no "—" clutter;
//   4. every string in both EN and VI.
//
// Fixtures below are trimmed copies of real backend payloads (dumped from
// tests/volume_harness.py), not invented shapes, so the panel is tested
// against what the service actually sends.
import React from 'react';
import { render, screen, within } from '@testing-library/react';
import i18n from '../../../i18n';
import PatternPanel from './PatternPanel';

const setLang = (lang) => i18n.changeLanguage(lang);

// ── Fixtures ────────────────────────────────────────────────────────────────

const confirming = {
  pattern_name: 'Head and Shoulders',
  pattern_type: 'bearish',
  found: true,
  confidence: 0.995,
  geometric_confidence: 0.917,
  volume_score: 0.783,
  volume_factor: 1.085,
  neckline: 99.5,
  measured_move_target: 80.5,
  details: {},
  volume_evidence: {
    status: 'known',
    verdict: 'confirms',
    pattern: 'Head and Shoulders',
    direction: 'bearish',
    components: {
      'right shoulder lighter than left': {
        verdict: 'confirms', value: 0.533, threshold: 0.75,
        expect: 'a_lower', required: true, citation: 'E&M Ch 6',
      },
      'breakout volume': {
        verdict: 'confirms', value: 2.832, threshold: 1.5,
        required: false, breakout_bar: 107, citation: 'E&M Ch 6',
      },
    },
    baseline_window: 50,
    citation: 'E&M Ch 6',
    not_scored: 'head volume is deliberately not scored',
  },
};

const contradicting = {
  pattern_name: 'Double Top',
  pattern_type: 'bearish',
  found: true,
  confidence: 0.709,
  geometric_confidence: 0.945,
  volume_score: 0.25,
  volume_factor: 0.75,
  details: {},
  volume_evidence: {
    status: 'known',
    verdict: 'contradicts',
    pattern: 'Double Top',
    direction: 'bearish',
    components: {
      'second top lighter than the first': {
        verdict: 'contradicts', value: 1.194, threshold: 0.8,
        expect: 'a_lower', required: true, citation: 'E&M Ch 9',
      },
      // An unreadable condition: must render as ABSENT, not as a failure.
      'breakout volume': { verdict: 'unknown', reason: 'no_breakout_yet', value: null },
    },
    baseline_window: 50,
    citation: 'E&M Ch 9',
  },
};

const neutral = {
  pattern_name: 'Gap (runaway)',
  pattern_type: 'bullish',
  found: true,
  confidence: 0.68,
  geometric_confidence: 0.68,
  volume_score: 0.5,
  volume_factor: 1.0,
  details: {},
  volume_evidence: {
    status: 'known',
    verdict: 'neutral',
    pattern: 'Gap (runaway)',
    direction: 'bullish',
    components: {
      'volume on the gap': {
        verdict: 'neutral', value: 1.067, threshold: 1.5,
        expect: 'high', required: false, citation: 'E&M Ch 12',
      },
    },
    baseline_window: 50,
    citation: 'E&M Ch 12',
  },
};

// The card verdict is "contradicts" but a COMPONENT is "suspect". Suspect is a
// categorically different reading — E&M's shakeout / reversal-area inversion —
// so the card must escalate to it rather than burying it in a row.
const suspect = {
  pattern_name: 'Flag',
  pattern_type: 'bullish',
  found: true,
  confidence: 0.45,
  geometric_confidence: 0.66,
  volume_score: 0.182,
  volume_factor: 0.682,
  details: {},
  volume_evidence: {
    status: 'known',
    verdict: 'contradicts',
    pattern: 'Flag',
    direction: 'bullish',
    components: {
      'flag volume markedly below the mast': {
        verdict: 'suspect', value: 1.273, threshold: 0.6,
        expect: 'a_lower', required: true, citation: 'E&M Ch 11',
      },
      'volume dries up continuously through the flag': {
        verdict: 'unknown', reason: 'span_too_short', value: null,
      },
    },
    baseline_window: 50,
    citation: 'E&M Ch 11',
  },
};

// Pre-EM-1 shape: no volume fields at all. Must render exactly as before.
const noVolume = {
  pattern_name: 'Pennant',
  pattern_type: 'bullish',
  found: true,
  confidence: 0.66,
  neckline: 111.0,
  details: {},
};

const thinVolume = {
  pattern_name: 'Bear Trap',
  pattern_type: 'bullish',
  found: true,
  confidence: 0.8,
  geometric_confidence: 0.8,
  volume_score: null,
  volume_factor: 1.0,
  details: {},
  volume_evidence: { status: 'unknown', reason: 'insufficient_history', thin_volume: true },
};

const reclassified = {
  pattern_name: 'Gap (exhaustion)',
  pattern_type: 'bullish',
  found: true,
  confidence: 0.782,
  geometric_confidence: 0.68,
  volume_score: 1.0,
  volume_factor: 1.15,
  details: { gap_type: 'exhaustion', gap_type_before_volume: 'runaway', reclassified_by: 'volume' },
  volume_evidence: {
    status: 'known',
    verdict: 'confirms',
    pattern: 'Gap (runaway)',
    direction: 'bullish',
    components: {
      'volume on the gap': {
        verdict: 'confirms', value: 7.21, threshold: 1.5,
        expect: 'high', required: false, citation: 'E&M Ch 12',
      },
    },
    baseline_window: 50,
    citation: 'E&M Ch 12',
    reclassified_from: 'Gap (runaway)',
    reclassified_to: 'Gap (exhaustion)',
  },
};

const card = (name) => screen.getByText(name).closest('[data-testid="pattern-card"]');

// ── The four verdicts ───────────────────────────────────────────────────────

describe('volume verdict chip (FR-EM-V9)', () => {
  beforeEach(async () => { await setLang('en'); });

  test('renders "confirms" when volume supports the pattern', () => {
    render(<PatternPanel patterns={[confirming]} />);
    expect(within(card('Head and Shoulders')).getByText('Volume confirms')).toBeInTheDocument();
  });

  test('renders "contradicts" when volume argues against it', () => {
    render(<PatternPanel patterns={[contradicting]} />);
    expect(within(card('Double Top')).getByText('Volume contradicts')).toBeInTheDocument();
  });

  test('renders "neutral" when volume says nothing either way', () => {
    render(<PatternPanel patterns={[neutral]} />);
    expect(within(card('Gap (runaway)')).getByText('Volume neutral')).toBeInTheDocument();
  });

  test('escalates to "suspect" when any condition is suspect', () => {
    // The payload's own card-level verdict is "contradicts". `suspect` can
    // never appear there, because the backend derives it from a score and a
    // score cannot express "this evidence inverts the pattern's meaning". If
    // the panel showed only the card verdict, one of FR-EM-V9's four verdicts
    // would be unreachable in the UI.
    render(<PatternPanel patterns={[suspect]} />);
    expect(within(card('Flag')).getByText('Volume suspect')).toBeInTheDocument();
    expect(within(card('Flag')).queryByText('Volume contradicts')).not.toBeInTheDocument();
  });

  test('all four verdicts render together without interfering', () => {
    render(<PatternPanel patterns={[confirming, contradicting, neutral, suspect]} />);
    ['Volume confirms', 'Volume contradicts', 'Volume neutral', 'Volume suspect']
      .forEach(label => expect(screen.getByText(label)).toBeInTheDocument());
  });
});

// ── Volume moved the number ─────────────────────────────────────────────────

describe('geometric vs composite confidence', () => {
  beforeEach(async () => { await setLang('en'); });

  test('shows both readings when volume changed the confidence', () => {
    render(<PatternPanel patterns={[confirming]} />);
    const el = card('Head and Shoulders');
    expect(within(el).getByText('92%')).toBeInTheDocument();   // geometric
    expect(within(el).getByText('100%')).toBeInTheDocument();  // composite
  });

  test('names the shape as geometry, so the two numbers are distinguishable', () => {
    render(<PatternPanel patterns={[confirming]} />);
    expect(within(card('Head and Shoulders')).getByText('Shape')).toBeInTheDocument();
  });

  test('shows a single number when volume left the confidence alone', () => {
    // A neutral verdict multiplies by exactly 1.0. Printing "68% → 68%" would
    // be noise dressed up as information.
    render(<PatternPanel patterns={[neutral]} />);
    const el = card('Gap (runaway)');
    expect(within(el).getAllByText('68%')).toHaveLength(1);
    expect(within(el).queryByText('Shape')).not.toBeInTheDocument();
  });

  test('a downgrade is shown as a downgrade', () => {
    render(<PatternPanel patterns={[contradicting]} />);
    const el = card('Double Top');
    expect(within(el).getByText('95%')).toBeInTheDocument();   // geometric
    expect(within(el).getByText('71%')).toBeInTheDocument();   // composite
  });
});

// ── Evidence rows ───────────────────────────────────────────────────────────

describe('evidence rows', () => {
  beforeEach(async () => { await setLang('en'); });

  test('each readable condition is listed with the figure behind it', () => {
    render(<PatternPanel patterns={[confirming]} />);
    const el = card('Head and Shoulders');
    expect(within(el).getByText('right shoulder lighter than left')).toBeInTheDocument();
    expect(within(el).getByText('breakout volume')).toBeInTheDocument();
    expect(within(el).getByText('2.83×')).toBeInTheDocument();
  });

  test('an unreadable condition is absent, not shown as a failure', () => {
    // `breakout volume` is unknown here — the pattern has not broken out yet.
    // Rendering it as a failed condition would read as evidence against the
    // pattern, which is precisely what FR-EM-V7 forbids for unknowns.
    render(<PatternPanel patterns={[contradicting]} />);
    const el = card('Double Top');
    expect(within(el).getByText('second top lighter than the first')).toBeInTheDocument();
    expect(within(el).queryByText('breakout volume')).not.toBeInTheDocument();
  });

  test('a required condition that failed is marked as required', () => {
    render(<PatternPanel patterns={[contradicting]} />);
    expect(within(card('Double Top')).getByText('required')).toBeInTheDocument();
  });

  test('the book citation is shown so a reading is traceable', () => {
    render(<PatternPanel patterns={[confirming]} />);
    expect(within(card('Head and Shoulders')).getByText(/E&M Ch 6/)).toBeInTheDocument();
  });
});

// ── A pattern with no volume evidence looks exactly as it did ───────────────

describe('no volume evidence (EC-V3, EC-V8)', () => {
  beforeEach(async () => { await setLang('en'); });

  test('renders with no verdict chip and no empty rows', () => {
    render(<PatternPanel patterns={[noVolume]} />);
    const el = card('Pennant');
    expect(within(el).getByText('66%')).toBeInTheDocument();
    ['Volume confirms', 'Volume neutral', 'Volume contradicts', 'Volume suspect']
      .forEach(label => expect(within(el).queryByText(label)).not.toBeInTheDocument());
    expect(within(el).queryByText('—')).not.toBeInTheDocument();
    expect(within(el).queryByText('Shape')).not.toBeInTheDocument();
  });

  test('a thin ticker explains why there is no verdict', () => {
    // EC-V8: silence with a reason, rather than silence.
    render(<PatternPanel patterns={[thinVolume]} />);
    expect(within(card('Bear Trap')).getByText('Volume too thin to judge')).toBeInTheDocument();
  });

  test('the old payload shape still renders its price levels', () => {
    render(<PatternPanel patterns={[noVolume]} />);
    expect(within(card('Pennant')).getByText('111.00')).toBeInTheDocument();
  });
});

// ── Re-classification (V6b) ─────────────────────────────────────────────────

describe('a label volume changed', () => {
  beforeEach(async () => { await setLang('en'); });

  test('shows the new name and says volume re-read it', () => {
    // The one place EM-1 moves a pattern_name. Silently renaming a pattern
    // would be indistinguishable from a detector bug.
    render(<PatternPanel patterns={[reclassified]} />);
    expect(screen.getByText('Gap (exhaustion)')).toBeInTheDocument();
    expect(screen.getByText(/was Gap \(runaway\)/)).toBeInTheDocument();
  });
});

// ── Panel-level readings ────────────────────────────────────────────────────

describe('panel-level volume readings', () => {
  beforeEach(async () => { await setLang('en'); });

  test('a volume climax is surfaced once for the scan, not per card', () => {
    const climax = {
      bar_index: 170, rvol_long: 6.381, progress_ratio: 0.0, window: 120,
      reason: 'volume 6.4x the 98th percentile of 120 bars',
      citation: 'E&M Ch 10, Ch 28',
    };
    render(<PatternPanel patterns={[neutral]} volumeClimax={climax} />);
    expect(screen.getByText('Volume climax')).toBeInTheDocument();
    expect(screen.getByText(/6\.4×/)).toBeInTheDocument();
  });

  test('no climax renders nothing at all', () => {
    render(<PatternPanel patterns={[neutral]} volumeClimax={null} />);
    expect(screen.queryByText('Volume climax')).not.toBeInTheDocument();
  });
});

// ── Pre-existing behaviour must not regress ────────────────────────────────

describe('existing panel behaviour', () => {
  beforeEach(async () => { await setLang('en'); });

  test('still filters out patterns that were not found', () => {
    render(<PatternPanel patterns={[{ ...neutral, found: false }]} />);
    expect(screen.queryByText('Gap (runaway)')).not.toBeInTheDocument();
    expect(screen.getByText(/No chart patterns detected/)).toBeInTheDocument();
  });

  test('loading and error states are unchanged', async () => {
    const { unmount } = render(<PatternPanel loading />);
    expect(screen.getByText('scanning…')).toBeInTheDocument();
    unmount();
    render(<PatternPanel error="boom" />);
    expect(screen.getByText('unavailable')).toBeInTheDocument();
  });

  test('renders nothing before a scan has run', () => {
    const { container } = render(<PatternPanel patterns={null} />);
    expect(container).toBeEmptyDOMElement();
  });
});

// ── Vietnamese ──────────────────────────────────────────────────────────────

describe('Vietnamese', () => {
  afterAll(async () => { await setLang('en'); });

  test('every verdict has a Vietnamese string', async () => {
    await setLang('vi');
    render(<PatternPanel patterns={[confirming, contradicting, neutral, suspect]} />);
    ['Khối lượng xác nhận', 'Khối lượng phản bác', 'Khối lượng trung tính', 'Khối lượng đáng ngờ']
      .forEach(label => expect(screen.getByText(label)).toBeInTheDocument());
  });

  test('the shape label and the thin-volume reason are translated', async () => {
    await setLang('vi');
    const { unmount } = render(<PatternPanel patterns={[confirming]} />);
    expect(screen.getByText('Hình mẫu')).toBeInTheDocument();
    unmount();
    render(<PatternPanel patterns={[thinVolume]} />);
    expect(screen.getByText('Khối lượng quá mỏng để đánh giá')).toBeInTheDocument();
  });

  test('no English leaks into the Vietnamese card', async () => {
    await setLang('vi');
    render(<PatternPanel patterns={[confirming]} />);
    const el = card('Head and Shoulders');
    ['Volume confirms', 'Shape', 'required'].forEach(
      label => expect(within(el).queryByText(label)).not.toBeInTheDocument()
    );
  });
});
