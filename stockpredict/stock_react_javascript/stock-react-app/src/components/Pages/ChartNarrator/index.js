import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Area, Bar, CartesianGrid, ComposedChart, Legend, Line, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import {
  AlertTriangle, BarChart2, CheckCircle2, Info, Play, RotateCcw,
  TrendingDown, TrendingUp,
} from 'lucide-react';
import { analysisAPI, stockAPI } from '../../../services/api';
import useWatchedTickers from '../../../hooks/useWatchedTickers';

/**
 * Backlog #118 — the chart narrator.
 *
 * On demand, per symbol: pick a WATCHED symbol, optionally bound the window
 * with two dates, press Analysis, and get the text together with the chart it
 * is describing.
 *
 * Every sentence on this page comes from an i18n `narrative.*` key filled with
 * numbers the backend measured. Nothing here composes prose from its own
 * judgement — if a finding has no translation it renders as a visible raw key
 * rather than as a plausible English sentence, which is the failure mode we
 * want to be loud.
 */

/**
 * THE LONGEST INDICATOR WINDOW ON THIS PAGE, in trading bars.
 *
 * MA200 is the binding one at 200 bars. MACD — the obvious candidate — needs
 * only 26 + 9 = 35, and RSI/ATR/Stochastic 14, so none of them constrains the
 * default window.
 *
 * Note the backend does NOT need this to compute MA200: it fetches 200 warmup
 * bars BEFORE start_date, so the line is correct even on a one-month window.
 * What a short window costs is VISIBILITY — you see the MA200 value without
 * seeing where it came from. Defaulting the range to the longest window means
 * every line drawn has its own history on screen.
 */
const MAX_INDICATOR_BARS = 200;

/**
 * Calendar days per trading bar, matching the backend's own constant
 * (analysis_service.CALENDAR_DAYS_PER_BAR). The VN market trades about five
 * days in seven, minus holidays, so 200 BARS is roughly 320 CALENDAR DAYS —
 * subtracting 200 days from the end date would give only ~140 bars and quietly
 * cut a quarter off the window the default is meant to cover.
 */
const CALENDAR_DAYS_PER_BAR = 1.6;

const DEFAULT_WINDOW_DAYS = Math.ceil(MAX_INDICATOR_BARS * CALENDAR_DAYS_PER_BAR);

/** `YYYY-MM-DD` for a Date, in local terms (the input[type=date] format). */
function isoDate(d) {
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/**
 * A real calendar date, not merely a `YYYY-MM-DD`-shaped string.
 *
 * The shape check alone is not enough, and the gap is not theoretical:
 * "2026-13-99" matches /^\d{4}-\d{2}-\d{2}$/ perfectly while being month 13
 * and day 99. `new Date()` returns Invalid Date for it, and the subtraction
 * below then produced a literal "NaN-NaN-NaN" in the date input. Round-tripping
 * through isoDate is what rejects month 13, day 99 and 30 February alike.
 */
function isRealDate(value) {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const d = new Date(`${value}T00:00:00`);
  return !Number.isNaN(d.getTime()) && isoDate(d) === value;
}

/** The default range: `end` back by the longest indicator window. */
export function defaultRange(endIso) {
  const end = isRealDate(endIso) ? endIso : isoDate(new Date());
  const start = new Date(`${end}T00:00:00`);
  start.setDate(start.getDate() - DEFAULT_WINDOW_DAYS);
  return { startDate: isoDate(start), endDate: end };
}

const SEVERITY_STYLE = {
  bullish: { row: 'border-l-4 border-emerald-500 bg-emerald-50', text: 'text-emerald-900', Icon: TrendingUp },
  bearish: { row: 'border-l-4 border-rose-500 bg-rose-50', text: 'text-rose-900', Icon: TrendingDown },
  warning: { row: 'border-l-4 border-amber-500 bg-amber-50', text: 'text-amber-900', Icon: AlertTriangle },
  info: { row: 'border-l-4 border-slate-300 bg-slate-50', text: 'text-slate-700', Icon: Info },
};

const SECTION_ORDER = ['data', 'trend', 'levels', 'indicators', 'patterns', 'chart_patterns', 'channel', 'strategy'];

export default function ChartNarrator() {
  const { t } = useTranslation();
  const { tickers, loading: tickersLoading, error: tickersError } = useWatchedTickers();

  const [symbol, setSymbol] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [datesReady, setDatesReady] = useState(false);
  const [result, setResult] = useState(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);

  // Prefill the range from the newest session the data actually holds, not from
  // `today` — today is wrong on a weekend, a holiday, and before the close.
  // Falls back to today if the lookup fails, which the backend then clamps to
  // the last bar at or before it, so a too-late end date is harmless.
  const applyDefaults = useCallback(async () => {
    const latest = await stockAPI.getLatestSessionDate();
    const { startDate: s, endDate: e } = defaultRange(latest);
    setStartDate(s);
    setEndDate(e);
    setDatesReady(true);
  }, []);

  useEffect(() => { applyDefaults(); }, [applyDefaults]);

  const run = useCallback(async () => {
    if (!symbol) return;
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const data = await analysisAPI.getNarrative(symbol, {
        startDate: startDate || undefined,
        endDate: endDate || undefined,
      });
      setResult(data);
    } catch (e) {
      setError(e.message || 'failed');
    } finally {
      setRunning(false);
    }
  }, [symbol, startDate, endDate]);

  // Dates are validated here rather than silently swapped: reordering what the
  // user typed would answer a question they did not ask.
  const datesInverted = Boolean(startDate && endDate && startDate > endDate);

  const sections = useMemo(() => {
    if (!result?.sections) return [];
    const byKey = new Map(result.sections.map((s) => [s.key, s]));
    return SECTION_ORDER.map((k) => byKey.get(k)).filter(Boolean);
  }, [result]);

  const chartData = useMemo(
    () => (result?.chart || []).map((b) => ({ ...b, date: b.date })),
    [result],
  );

  return (
    <div className="p-4 space-y-4">
      <div>
        <h1 className="text-lg font-bold text-gray-900 flex items-center gap-2">
          <BarChart2 className="w-5 h-5 text-blue-600" />
          {t('narrative.ui.title')}
        </h1>
        <p className="text-sm text-gray-500 mt-1">{t('narrative.ui.subtitle')}</p>
      </div>

      {/* ---- controls ---- */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1">
            <span className="text-xs font-medium text-gray-600">{t('narrative.ui.symbol_label')}</span>
            <select
              value={symbol}
              onChange={(e) => { setSymbol(e.target.value); setResult(null); setError(null); }}
              disabled={tickersLoading || tickers.length === 0}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white min-w-[220px] focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">{t('narrative.ui.symbol_placeholder')}</option>
              {tickers.map((o) => (
                <option key={o.symbol} value={o.symbol}>
                  {o.symbol}{o.name && o.name !== o.symbol ? ` · ${o.name}` : ''}
                </option>
              ))}
            </select>
          </label>

          <label className="flex flex-col gap-1">
            <span className="text-xs font-medium text-gray-600">{t('narrative.ui.start_date')}</span>
            <input
              type="date" value={startDate} max={endDate || undefined}
              onChange={(e) => setStartDate(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </label>

          <label className="flex flex-col gap-1">
            <span className="text-xs font-medium text-gray-600">{t('narrative.ui.end_date')}</span>
            <input
              type="date" value={endDate} min={startDate || undefined}
              onChange={(e) => setEndDate(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </label>

          <button
            type="button" onClick={run}
            disabled={!symbol || running || datesInverted || !datesReady}
            className="px-5 py-2 rounded-lg text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <Play className="w-4 h-4" />
            {running ? t('narrative.ui.analysing') : t('narrative.ui.analyse')}
          </button>
        </div>

        {datesInverted && (
          <p className="text-xs text-rose-600 mt-2">{t('narrative.ui.dates_inverted')}</p>
        )}
        <div className="flex items-center gap-3 mt-2 flex-wrap">
          <p className="text-xs text-gray-400">
            {t('narrative.ui.date_hint', { bars: MAX_INDICATOR_BARS })}
          </p>
          <button
            type="button" onClick={applyDefaults}
            className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
          >
            <RotateCcw className="w-3 h-3" />
            {t('narrative.ui.reset_dates')}
          </button>
        </div>

        {!tickersLoading && tickersError && (
          <p className="text-xs text-rose-600 mt-2">{t('narrative.ui.watchlist_failed')}</p>
        )}
        {!tickersLoading && !tickersError && tickers.length === 0 && (
          <p className="text-xs text-gray-500 mt-2">{t('narrative.ui.no_watched')}</p>
        )}
      </div>

      {error && (
        <div className="bg-rose-50 border border-rose-200 rounded-lg p-4 text-sm text-rose-800">
          {t('narrative.ui.failed', { symbol, reason: error })}
        </div>
      )}

      {!result && !error && !running && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-10 text-center text-gray-500">
          {t('narrative.ui.empty')}
        </div>
      )}

      {result && (
        <>
          {/* A contaminated window is said once, loudly, at the top — not left
              to be discovered three sections down. */}
          {result.data_ok === false && (
            <div className="bg-amber-50 border-2 border-amber-400 rounded-xl p-4 flex gap-3">
              <AlertTriangle className="w-6 h-6 text-amber-600 flex-shrink-0" />
              <div className="text-sm text-amber-900 font-medium">
                {t('narrative.ui.data_warning_banner')}
              </div>
            </div>
          )}

          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <div className="flex items-baseline justify-between flex-wrap gap-2 mb-3">
              <h2 className="text-sm font-semibold text-gray-800">
                {t('narrative.ui.chart_title', { symbol: result.symbol })}
              </h2>
              <span className="text-xs text-gray-500">
                {t('narrative.ui.as_of', { date: result.as_of, bars: result.bars })}
              </span>
            </div>
            <NarratorChart data={chartData} levels={result.levels || []} t={t} />
          </div>

          <div className="space-y-4">
            {sections.map((s) => (
              <section key={s.key} className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
                <h3 className="text-sm font-bold text-gray-800 mb-3">
                  {t(`narrative.section.${s.key}`)}
                </h3>
                <ul className="space-y-2">
                  {s.findings.map((f, i) => {
                    const style = SEVERITY_STYLE[f.severity] || SEVERITY_STYLE.info;
                    const { Icon } = style;
                    return (
                      <li key={`${f.code}-${i}`} className={`${style.row} rounded px-3 py-2 flex gap-2`}>
                        <Icon className={`w-4 h-4 mt-0.5 flex-shrink-0 ${style.text}`} />
                        <span className={`text-sm leading-relaxed ${style.text}`}>
                          {t(f.code, f.params)}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              </section>
            ))}
          </div>

          <p className="text-xs text-gray-400 italic flex items-start gap-2 px-1">
            <CheckCircle2 className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
            {t('narrative.disclaimer')}
          </p>
        </>
      )}
    </div>
  );
}

/**
 * Price, the three moving averages, volume, and a horizontal line for EVERY
 * level the text names.
 *
 * The lines come from `result.levels`, which is the same object the text is
 * built from, so the chart cannot draw a level the narration does not mention
 * or vice versa.
 */
export function NarratorChart({ data, levels, t }) {
  if (!data || data.length === 0) {
    return <div className="h-72 flex items-center justify-center text-sm text-gray-400">
      {t('narrative.ui.no_chart_data')}
    </div>;
  }
  const closes = data.map((d) => d.close).filter((v) => v != null);
  const lows = data.map((d) => d.low).filter((v) => v != null);
  const highs = data.map((d) => d.high).filter((v) => v != null);
  const levelPrices = (levels || []).map((l) => l.price);
  const lo = Math.min(...lows, ...levelPrices, ...closes);
  const hi = Math.max(...highs, ...levelPrices, ...closes);
  const pad = (hi - lo) * 0.06 || 1;

  return (
    <div className="space-y-2">
      <ResponsiveContainer width="100%" height={320}>
        <ComposedChart data={data} margin={{ top: 5, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
          <XAxis dataKey="date" tick={{ fontSize: 10 }} minTickGap={48} />
          <YAxis domain={[lo - pad, hi + pad]} tick={{ fontSize: 10 }} width={52}
                 tickFormatter={(v) => v.toFixed(0)} />
          <Tooltip contentStyle={{ fontSize: 12 }} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Area type="monotone" dataKey="close" name={t('narrative.ui.series_close')}
                stroke="#2563eb" fill="#dbeafe" strokeWidth={1.6} dot={false} />
          <Line type="monotone" dataKey="ma20" name="MA20" stroke="#f59e0b"
                dot={false} strokeWidth={1.2} connectNulls />
          <Line type="monotone" dataKey="ma50" name="MA50" stroke="#8b5cf6"
                dot={false} strokeWidth={1.2} connectNulls />
          <Line type="monotone" dataKey="ma200" name="MA200" stroke="#64748b"
                dot={false} strokeWidth={1.2} connectNulls />
          {(levels || []).map((l, i) => (
            <ReferenceLine
              key={`${l.price}-${i}`} y={l.price}
              stroke={l.kind === 'support' ? '#059669' : '#dc2626'}
              strokeDasharray="5 4"
              label={{
                value: `${t(`narrative.ui.level_${l.kind}`)} ${l.price}`,
                position: 'insideTopLeft', fontSize: 10,
                fill: l.kind === 'support' ? '#047857' : '#b91c1c',
              }}
            />
          ))}
        </ComposedChart>
      </ResponsiveContainer>

      <ResponsiveContainer width="100%" height={90}>
        <ComposedChart data={data} margin={{ top: 0, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
          <XAxis dataKey="date" tick={{ fontSize: 9 }} minTickGap={64} />
          <YAxis tick={{ fontSize: 9 }} width={52}
                 tickFormatter={(v) => (v >= 1e6 ? `${(v / 1e6).toFixed(0)}M` : v)} />
          <Tooltip contentStyle={{ fontSize: 12 }} />
          <Bar dataKey="volume" name={t('narrative.ui.series_volume')} fill="#94a3b8" />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
