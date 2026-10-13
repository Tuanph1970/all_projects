// EM-1 / F2 (FR-EM-V9) — the compact volume verdict, for the AI Insights page.
//
// F1 renders the full verdict on the Decision Console, where there is room for
// an evidence row per Edwards & Magee condition. This is the compact form:
// name, verdict, and what volume did to the confidence. It deliberately omits
// the evidence rows and the citation — a reader who wants those has the
// Decision Console.
//
// A note on why this component exists at all. The AI Insights page already has
// a "Pattern Recognition" section, but that renders `pattern_recognition`
// from `/insights/comprehensive/` — a separate SMA-based heuristic producing
// Uptrend/Downtrend, which are not Edwards & Magee formations and carry no
// volume fields. The EM-1 detectors live behind `/insights/patterns/{symbol}`,
// so showing their verdict on this page means fetching them, not decorating
// the existing section.
import React from 'react';
import { Activity, TrendingUp, TrendingDown, ArrowRight, AlertTriangle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { VerdictChip, cardVerdict, confidenceReadings } from './volumeVerdict';

const PatternRow = ({ pattern }) => {
  // No `t` here on purpose: every string in this row comes from VerdictChip,
  // which translates its own label.
  const isBullish = pattern.pattern_type === 'bullish';
  const isBearish = pattern.pattern_type === 'bearish';
  const color = isBullish ? '#059669' : isBearish ? '#dc2626' : '#2563eb';
  const { composite, geometric, moved } = confidenceReadings(pattern);

  return (
    <div
      data-testid="compact-pattern"
      className="flex items-center gap-2 py-1.5 border-b border-gray-100 last:border-0"
    >
      {isBullish && <TrendingUp className="w-3 h-3 flex-shrink-0" style={{ color }} />}
      {isBearish && <TrendingDown className="w-3 h-3 flex-shrink-0" style={{ color }} />}
      <span className="text-xs text-gray-700 flex-1 truncate">{pattern.pattern_name}</span>
      <VerdictChip verdict={cardVerdict(pattern.volume_evidence)} compact />
      {moved && (
        <>
          <span className="text-xs text-gray-400 tabular-nums">{geometric}%</span>
          <ArrowRight className="w-2.5 h-2.5 text-gray-400 flex-shrink-0" />
        </>
      )}
      <span className="text-xs font-semibold tabular-nums" style={{ color }}>{composite}%</span>
    </div>
  );
};

const ChartPatternsCompact = ({ patterns, loading, error, volumeClimax }) => {
  const { t } = useTranslation();

  // Silent on every non-happy path. This card is a best-effort extra on a page
  // whose main content comes from a different endpoint, so a failed or pending
  // pattern scan must not flash an empty card or an error at someone reading
  // the rest of the analysis.
  if (loading || error || !patterns) return null;
  const found = patterns.filter(p => p.found);
  if (found.length === 0) return null;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
      <h3 className="text-sm font-bold text-gray-900 mb-1 flex items-center">
        <Activity className="w-4 h-4 mr-2" />
        {t('analysis.ai_insights.chart_patterns_title')}
      </h3>
      <p className="text-xs text-gray-500 mb-2">
        {t('analysis.ai_insights.chart_patterns_subtitle')}
      </p>

      {found.map((p, i) => <PatternRow key={`${p.pattern_name}-${i}`} pattern={p} />)}

      {volumeClimax && (
        <div className="flex items-center gap-1.5 mt-2 pt-2 border-t border-gray-100">
          <AlertTriangle className="w-3 h-3 flex-shrink-0" style={{ color: '#d97706' }} />
          <span className="text-xs font-semibold" style={{ color: '#b45309' }}>
            {t('decision_helper.pattern_panel.volume_climax')}
          </span>
          <span className="text-xs" style={{ color: '#92400e' }}>
            {t('decision_helper.pattern_panel.volume_climax_detail', {
              rvol: Number(volumeClimax.rvol_long).toFixed(1),
              window: volumeClimax.window,
            })}
          </span>
        </div>
      )}
    </div>
  );
};

export default ChartPatternsCompact;
