// EM-1 (FR-EM-V9) — the volume-verdict vocabulary, shared by every screen
// that renders one.
//
// Lives here rather than in a component because two screens show the verdict —
// the Decision Console's PatternPanel in full (F1) and the AI Insights page in
// compact form (F2) — and the escalation rule below is subtle enough that two
// copies would drift apart.
import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { useTranslation } from 'react-i18next';

// The four verdicts the backend can report, and how each reads. `suspect` is
// deliberately the loudest: it does not mean "weak evidence", it means the
// evidence inverts the pattern's meaning — E&M's 2–3 day shakeout on a
// high-volume downside break (Ch 8), or heavy volume inside a flag turning a
// continuation into a minor reversal area (Ch 11).
export const VERDICTS = {
  confirms: { color: '#059669', bg: 'rgba(5,150,105,0.10)' },
  neutral: { color: '#6b7280', bg: 'rgba(107,114,128,0.10)' },
  contradicts: { color: '#dc2626', bg: 'rgba(220,38,38,0.10)' },
  suspect: { color: '#d97706', bg: 'rgba(217,119,6,0.12)' },
};

/**
 * The verdict to show for a pattern.
 *
 * Escalates to `suspect` when any single condition is suspect, because the
 * backend's card-level verdict is derived from a score and a score cannot
 * express an inversion — `verdict_label` only ever returns confirms, neutral
 * or contradicts. Without this escalation one of FR-EM-V9's four verdicts
 * would be unreachable in the UI even though the backend computes it.
 */
export const cardVerdict = (evidence) => {
  const components = evidence?.components ?? {};
  const anySuspect = Object.values(components).some(c => c?.verdict === 'suspect');
  return anySuspect ? 'suspect' : evidence?.verdict;
};

/**
 * Geometric and composite confidence as whole percents, plus whether volume
 * actually moved the number.
 *
 * `moved` is false when the rounded percentages match, because a neutral
 * verdict multiplies by exactly 1.0 and showing "68% → 68%" would be noise
 * dressed up as information.
 */
export const confidenceReadings = (pattern) => {
  const composite = Math.round((pattern?.confidence ?? 0) * 100);
  const geometric = pattern?.geometric_confidence != null
    ? Math.round(pattern.geometric_confidence * 100)
    : null;
  return { composite, geometric, moved: geometric != null && geometric !== composite };
};

export const VerdictChip = ({ verdict, compact = false }) => {
  const { t } = useTranslation();
  const style = VERDICTS[verdict];
  if (!style) return null;
  return (
    <span
      style={{
        fontSize: compact ? 9 : 10, fontWeight: 700,
        color: style.color, background: style.bg,
        padding: compact ? '1px 5px' : '2px 7px', borderRadius: 4,
        whiteSpace: 'nowrap', display: 'inline-flex', alignItems: 'center', gap: 4,
      }}
    >
      {verdict === 'suspect' && <AlertTriangle size={compact ? 9 : 10} />}
      {t(`decision_helper.pattern_panel.volume_verdict.${verdict}`)}
    </span>
  );
};
