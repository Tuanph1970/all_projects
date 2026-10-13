// F-101 — PatternPanel: chart-pattern overlay for Decision Console
// EM-1 / F1 (FR-EM-V9) — renders the Edwards & Magee volume verdict per card.
import React, { useState } from 'react';
import { ChevronDown, ChevronRight, TrendingUp, TrendingDown, ArrowRight, AlertTriangle } from 'lucide-react';
import { useTranslation } from 'react-i18next';

// ── Volume verdict (EM-1 / FR-EM-V9) ────────────────────────────────────────

// The four verdicts the backend can report, and how each reads on a card.
// `suspect` is deliberately the loudest: it does not mean "weak evidence", it
// means the evidence inverts the pattern's meaning — E&M's 2–3 day shakeout on
// a high-volume downside break (Ch 8), or heavy volume inside a flag turning a
// continuation into a minor reversal area (Ch 11).
const VERDICTS = {
  confirms: { color: '#059669', bg: 'rgba(5,150,105,0.10)' },
  neutral: { color: '#6b7280', bg: 'rgba(107,114,128,0.10)' },
  contradicts: { color: '#dc2626', bg: 'rgba(220,38,38,0.10)' },
  suspect: { color: '#d97706', bg: 'rgba(217,119,6,0.12)' },
};

/**
 * The verdict to show on the card.
 *
 * Escalates to `suspect` when any single condition is suspect, because the
 * backend's card-level verdict is derived from a score and a score cannot
 * express an inversion — `verdict_label` only ever returns confirms, neutral
 * or contradicts. Without this escalation one of FR-EM-V9's four verdicts
 * would be unreachable in the UI even though the backend computes it.
 */
const cardVerdict = (evidence) => {
  const components = evidence?.components ?? {};
  const anySuspect = Object.values(components).some(c => c?.verdict === 'suspect');
  return anySuspect ? 'suspect' : evidence?.verdict;
};

const VerdictChip = ({ verdict }) => {
  const { t } = useTranslation();
  const style = VERDICTS[verdict];
  if (!style) return null;
  return (
    <span
      style={{
        fontSize: 10, fontWeight: 700, color: style.color, background: style.bg,
        padding: '2px 7px', borderRadius: 4, whiteSpace: 'nowrap',
        display: 'inline-flex', alignItems: 'center', gap: 4,
      }}
    >
      {verdict === 'suspect' && <AlertTriangle size={10} />}
      {t(`decision_helper.pattern_panel.volume_verdict.${verdict}`)}
    </span>
  );
};

/**
 * One E&M condition and the figure behind it.
 *
 * A condition the backend could not read is rendered as **absent** rather than
 * as a failure: an unresolved formation has no breakout volume to judge, and
 * showing that as a failed row would read as evidence against the pattern,
 * which is exactly what FR-EM-V7 forbids for unknowns.
 */
const EvidenceRow = ({ label, detail }) => {
  const { t } = useTranslation();
  const style = VERDICTS[detail.verdict];
  if (!style || detail.value == null) return null;

  return (
    <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, fontSize: 10, lineHeight: 1.5 }}>
      <span style={{ width: 5, height: 5, borderRadius: '50%', background: style.color, flexShrink: 0 }} />
      <span style={{ color: '#4b5563', flex: 1 }}>{label}</span>
      {detail.required && detail.verdict !== 'confirms' && (
        <span style={{ color: '#9ca3af', fontSize: 9, fontStyle: 'italic' }}>
          {t('decision_helper.pattern_panel.volume_required')}
        </span>
      )}
      <span style={{ color: style.color, fontWeight: 700, fontVariantNumeric: 'tabular-nums' }}>
        {Number(detail.value).toFixed(2)}×
      </span>
    </div>
  );
};

const VolumeEvidence = ({ pattern }) => {
  const { t } = useTranslation();
  const evidence = pattern.volume_evidence;
  if (!evidence) return null;

  // EC-V8: silence with a reason beats silence. A thin ticker is a real E&M
  // shape (Ch 7's Dormant Bottom), not a data error, so it is worth saying.
  if (evidence.status !== 'known') {
    if (!evidence.thin_volume) return null;
    return (
      <div style={{ fontSize: 10, color: '#9ca3af', fontStyle: 'italic', marginTop: 6 }}>
        {t('decision_helper.pattern_panel.volume_thin')}
      </div>
    );
  }

  const components = Object.entries(evidence.components ?? {})
    .filter(([, detail]) => detail?.value != null && VERDICTS[detail.verdict]);

  return (
    <div style={{ marginTop: 7, paddingTop: 7, borderTop: '1px dashed #e5e7eb' }}>
      {evidence.reclassified_to && (
        <div style={{ fontSize: 10, color: '#d97706', marginBottom: 5 }}>
          {t('decision_helper.pattern_panel.volume_reclassified', { from: evidence.reclassified_from })}
        </div>
      )}
      {components.map(([label, detail]) => (
        <EvidenceRow key={label} label={label} detail={detail} />
      ))}
      {evidence.citation && (
        <div style={{ fontSize: 9, color: '#9ca3af', marginTop: 4 }}>{evidence.citation}</div>
      )}
    </div>
  );
};

// ── PatternCard ──────────────────────────────────────────────────────────────

const PatternCard = ({ pattern }) => {
  const { t } = useTranslation();
  const isBullish = pattern.pattern_type === 'bullish';
  const color = isBullish ? '#10b981' : '#ef4444';
  const bg = isBullish ? 'rgba(16,185,129,0.08)' : 'rgba(239,68,68,0.08)';
  const border = isBullish ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)';
  const Icon = isBullish ? TrendingUp : TrendingDown;

  const pct = Math.round((pattern.confidence ?? 0) * 100);
  const geometricPct = pattern.geometric_confidence != null
    ? Math.round(pattern.geometric_confidence * 100)
    : null;
  // Show both readings only when volume actually moved the number. A neutral
  // verdict multiplies by exactly 1.0, and printing "68% → 68%" would be noise
  // dressed up as information.
  const volumeMovedIt = geometricPct != null && geometricPct !== pct;
  const verdict = cardVerdict(pattern.volume_evidence);

  return (
    <div
      data-testid="pattern-card"
      style={{ background: bg, border: `1px solid ${border}`, borderRadius: 8, padding: '10px 13px' }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, flexWrap: 'wrap' }}>
        <Icon size={13} color={color} style={{ flexShrink: 0 }} />
        <span style={{ fontWeight: 700, fontSize: 13, color: '#111827', flex: 1 }}>
          {pattern.pattern_name}
        </span>
        <VerdictChip verdict={verdict} />
        <span style={{ fontSize: 11, fontWeight: 600, color, background: `${color}22`, padding: '2px 7px', borderRadius: 4 }}>
          {isBullish ? t('decision_helper.pattern_panel.bullish') : t('decision_helper.pattern_panel.bearish')}
        </span>
      </div>

      {/* Confidence bar. With a volume verdict the bar shows the composite and
          the geometric reading is named beside it, so a user can see what
          volume did to the number rather than only its result. */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <span style={{ fontSize: 10, color: '#6b7280', width: 68, flexShrink: 0 }}>
          {t('decision_helper.pattern_panel.confidence')}
        </span>
        <div style={{ flex: 1, height: 5, background: '#e5e7eb', borderRadius: 3, overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: 3 }} />
        </div>
        {volumeMovedIt && (
          <>
            <span style={{ fontSize: 9, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: 0.4 }}>
              {t('decision_helper.pattern_panel.volume_geometric')}
            </span>
            <span style={{ fontSize: 10, color: '#9ca3af', fontVariantNumeric: 'tabular-nums' }}>
              {geometricPct}%
            </span>
            <ArrowRight size={9} color="#9ca3af" />
          </>
        )}
        <span style={{ fontSize: 11, color, fontWeight: 600, minWidth: 32, textAlign: 'right' }}>{pct}%</span>
      </div>

      {/* Price levels */}
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        {pattern.neckline != null && (
          <div style={styles.priceCell}>
            <span style={styles.priceLabel}>{t('decision_helper.pattern_panel.neckline')}</span>
            <span style={{ ...styles.priceValue, color: '#f59e0b' }}>
              {Number(pattern.neckline).toLocaleString('en', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
        )}
        {pattern.measured_move_target != null && (
          <div style={styles.priceCell}>
            <span style={styles.priceLabel}>{t('decision_helper.pattern_panel.measured_move')}</span>
            <span style={{ ...styles.priceValue, color }}>
              {Number(pattern.measured_move_target).toLocaleString('en', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
        )}
      </div>

      <VolumeEvidence pattern={pattern} />
    </div>
  );
};

// ── Volume climax (FR-EM-V6) ────────────────────────────────────────────────

/**
 * Reported once for the scan rather than per card, because a climax is a
 * property of the series and not of any formation — which is also why the
 * backend returns it on the response and never on a PatternMatch.
 *
 * Evidence only in this slice: it says what it saw and changes no number.
 */
const ClimaxBanner = ({ climax }) => {
  const { t } = useTranslation();
  if (!climax) return null;
  return (
    <div
      style={{
        display: 'flex', alignItems: 'center', gap: 6, marginTop: 10,
        background: 'rgba(217,119,6,0.10)', border: '1px solid rgba(217,119,6,0.25)',
        borderRadius: 6, padding: '6px 9px',
      }}
    >
      <AlertTriangle size={12} color="#d97706" style={{ flexShrink: 0 }} />
      <span style={{ fontSize: 11, fontWeight: 700, color: '#b45309' }}>
        {t('decision_helper.pattern_panel.volume_climax')}
      </span>
      <span style={{ fontSize: 10, color: '#92400e' }}>
        {t('decision_helper.pattern_panel.volume_climax_detail', {
          rvol: Number(climax.rvol_long).toFixed(1),
          window: climax.window,
        })}
      </span>
    </div>
  );
};

// ── PatternPanel ─────────────────────────────────────────────────────────────

const PatternPanel = ({ patterns, loading, error, volumeClimax }) => {
  const { t } = useTranslation();
  const [open, setOpen] = useState(true);

  const found = patterns ? patterns.filter(p => p.found) : [];

  if (loading) {
    return (
      <div style={styles.shell}>
        <div style={styles.header}>
          <span style={styles.title}>{t('decision_helper.pattern_panel.title')}</span>
          <span style={{ fontSize: 11, color: '#6b7280' }}>{t('decision_helper.pattern_panel.scanning')}</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={styles.shell}>
        <div style={styles.header}>
          <span style={styles.title}>{t('decision_helper.pattern_panel.title')}</span>
          <span style={{ fontSize: 11, color: '#6b7280' }}>{t('decision_helper.pattern_panel.unavailable')}</span>
        </div>
      </div>
    );
  }

  if (!patterns) return null;

  return (
    <div style={styles.shell}>
      <button onClick={() => setOpen(o => !o)} style={styles.toggleBtn}>
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        <span style={styles.title}>{t('decision_helper.pattern_panel.title')}</span>
        {found.length > 0 ? (
          <span style={styles.badge}>{t('decision_helper.pattern_panel.detected', { count: found.length })}</span>
        ) : (
          <span style={{ fontSize: 11, color: '#6b7280', marginLeft: 6 }}>{t('decision_helper.pattern_panel.none_detected')}</span>
        )}
      </button>

      {open && found.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 10 }}>
          {found.map((p, i) => <PatternCard key={i} pattern={p} />)}
        </div>
      )}

      {open && found.length === 0 && (
        <div style={{ color: '#9ca3af', fontSize: 12, marginTop: 8, paddingLeft: 4 }}>
          {t('decision_helper.pattern_panel.no_patterns')}
        </div>
      )}

      {open && <ClimaxBanner climax={volumeClimax} />}
    </div>
  );
};

const styles = {
  shell: {
    background: '#ffffff', borderRadius: 10,
    border: '1px solid #e5e7eb', padding: 14,
  },
  header: { display: 'flex', alignItems: 'center', gap: 8 },
  toggleBtn: {
    background: 'none', border: 'none', padding: 0, cursor: 'pointer',
    display: 'flex', alignItems: 'center', gap: 6, width: '100%',
  },
  title: { fontSize: 13, fontWeight: 600, color: '#374151' },
  badge: {
    background: 'rgba(139,92,246,0.2)', color: '#a78bfa',
    fontSize: 11, fontWeight: 600, padding: '1px 8px', borderRadius: 4, marginLeft: 6,
  },
  priceCell: { display: 'flex', flexDirection: 'column', gap: 1 },
  priceLabel: { fontSize: 9, color: '#6b7280', textTransform: 'uppercase', letterSpacing: 0.5 },
  priceValue: { fontSize: 13, fontWeight: 700 },
};

export default PatternPanel;
