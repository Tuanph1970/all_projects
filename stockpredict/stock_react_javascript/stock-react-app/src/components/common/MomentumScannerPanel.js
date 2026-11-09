import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, Info, RefreshCw, Search, Telescope } from 'lucide-react';
import helperService from '../../services/helperService';

/**
 * FR-SCAN-API — the momentum & base scanner, as a panel inside AI Insights (D6).
 *
 * THE EMPTY STATE IS THE PRIMARY STATE, not an edge case. The funnel returns
 * zero candidates whenever the market is not offering the setup, and on
 * 2026-11-06 that is exactly what it does: 81 of 81 ranked names fail the trend
 * template. Backlog #135 is about this — a blank screen that looks identical to
 * a broken one is how a working filter gets loosened until it stops filtering.
 * So `empty_reason` is rendered as a finding, with the funnel counts beside it.
 *
 * The VT-4 null rate is shown whenever the stored run carries one (C4/EC-S5): a
 * candidate list without it invites the reader to assume a selectivity nobody
 * measured. It is labelled as selectivity against noise, never as edge.
 */

const pct = (v, digits = 1) =>
  v === null || v === undefined ? '—' : `${v >= 0 ? '+' : ''}${v.toFixed(digits)}%`;
const num = (v, digits = 2) =>
  v === null || v === undefined ? '—' : v.toFixed(digits);
const billions = (vnd) =>
  vnd === null || vnd === undefined ? '—' : (vnd / 1e9).toFixed(1);

// Verdicts the backend can return, mapped to a tone. Anything unmapped renders
// grey rather than throwing — a new verdict server-side must not blank the page.
const VERDICT_TONE = {
  CANDIDATE: 'text-green-700 bg-green-50 border-green-200',
  QUALIFIED_BEYOND_CUT: 'text-green-700 bg-green-50 border-green-200',
  FAILED_BASE: 'text-amber-700 bg-amber-50 border-amber-200',
  FAILED_TREND: 'text-amber-700 bg-amber-50 border-amber-200',
  ILLIQUID: 'text-gray-700 bg-gray-50 border-gray-200',
  PRICE_SEAM: 'text-red-700 bg-red-50 border-red-200',
  SHORT_HISTORY: 'text-gray-700 bg-gray-50 border-gray-200',
  NO_BARS: 'text-gray-700 bg-gray-50 border-gray-200',
};

const FUNNEL_ROWS = [
  ['no_bars', 'no_bars'],
  ['insufficient_history', 'short_history'],
  ['price_seam', 'price_seam'],
  ['illiquid', 'illiquid'],
  ['failed_trend', 'failed_trend'],
  ['failed_base', 'failed_base'],
  ['excess_qualified', 'excess_qualified'],
  ['candidates', 'candidates'],
];

export const MomentumScannerPanel = ({ onSelectSymbol }) => {
  const { t } = useTranslation();
  const [scan, setScan] = useState(null);
  const [loading, setLoading] = useState(false);
  // Messages are held as i18n KEYS and translated at render, never as already
  // translated strings. Two reasons: a stored string does not follow a language
  // switch, and keeping `t` out of the fetch callback is what stops the mount
  // effect from re-firing forever — `t` is a new function on every render, so a
  // callback that depends on it changes identity every render too.
  const [notice, setNotice] = useState(null);           // i18n key | null
  const [serverError, setServerError] = useState(null); // { code } | { text } | null
  const [scanDate, setScanDate] = useState('');
  const [lookupSymbol, setLookupSymbol] = useState('');
  const [lookup, setLookup] = useState(null);
  const [lookupError, setLookupError] = useState(null); // { code, symbol? } | { text }

  const key = (k) => t(`analysis.ai_insights.scanner.${k}`);

  const load = useCallback(async (date) => {
    setLoading(true);
    setServerError(null);
    setNotice(null);
    try {
      const data = await helperService.getMomentumScan(date || null);
      setScan(data);
    } catch (err) {
      // A 404 is not a failure: it means nobody has run a scan for that date.
      // Saying so is the difference between "nothing qualified" and "nothing ran".
      const status = err?.response?.status ?? err?.status;
      if (status === 404) {
        setScan(null);
        setNotice('no_run_yet');
      } else {
        setServerError(err?.message ? { text: err.message } : { code: 'load_failed' });
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(''); }, [load]);

  const runScan = async () => {
    setLoading(true);
    setServerError(null);
    setNotice(null);
    try {
      setScan(await helperService.runMomentumScan({ scanDate: scanDate || null }));
    } catch (err) {
      setServerError(err?.message ? { text: err.message } : { code: 'run_failed' });
    } finally {
      setLoading(false);
    }
  };

  const runLookup = async () => {
    const sym = lookupSymbol.trim().toUpperCase();
    if (!sym) return;
    setLookupError(null);
    setLookup(null);
    try {
      setLookup(await helperService.getMomentumSymbol(sym, scanDate || null));
    } catch (err) {
      const status = err?.response?.status ?? err?.status;
      setLookupError(
        status === 404 ? { code: 'symbol_not_scanned', symbol: sym }
                       : (err?.message ? { text: err.message } : { code: 'lookup_failed' })
      );
    }
  };

  const candidates = scan?.candidates || [];
  const accounting = scan?.accounting || {};
  const nullFpr = scan?.null_fpr;

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center text-gray-700 font-semibold">
            <Telescope className="w-4 h-4 mr-2 text-indigo-500" />
            {key('title')}
          </div>
          <input
            type="date"
            aria-label={key('date_label')}
            value={scanDate}
            onChange={(e) => setScanDate(e.target.value)}
            className="px-2 py-1.5 text-sm border border-gray-300 rounded-lg"
          />
          <button
            onClick={() => load(scanDate)}
            disabled={loading}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
          >
            {key('load_button')}
          </button>
          <button
            onClick={runScan}
            disabled={loading}
            className="flex items-center px-3 py-1.5 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:opacity-50"
          >
            {loading
              ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
              : <Telescope className="w-4 h-4 mr-2" />}
            {loading ? key('running') : key('run_button')}
          </button>
        </div>
        <p className="mt-2 text-xs text-gray-500">{key('subtitle')}</p>
      </div>

      {notice && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <div className="flex items-center">
            <Info className="w-4 h-4 text-blue-500 mr-2" />
              <span className="text-sm text-blue-800">{key(notice)}</span>
          </div>
        </div>
      )}

      {serverError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3">
          <div className="flex items-center">
            <AlertTriangle className="w-4 h-4 text-red-500 mr-2" />
            <span className="text-sm text-red-700">
              {serverError.text || key(serverError.code)}
            </span>
          </div>
        </div>
      )}

      {scan && (
        <>
          {/* Run summary */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <table className="w-full text-sm">
              <tbody>
                <tr className="border-b border-gray-100">
                  <td className="py-2 text-gray-500 w-1/6">{key('scan_date_label')}</td>
                  <td className="py-2 font-semibold w-1/6">{scan.scan_date}</td>
                  <td className="py-2 text-gray-500 w-1/6">{key('universe_label')}</td>
                  <td className="py-2 font-semibold w-1/6">
                    {scan.ranked_universe} / {scan.universe_total}
                  </td>
                  <td className="py-2 text-gray-500 w-1/6">{key('candidates_label')}</td>
                  <td className="py-2 font-semibold w-1/6">{scan.candidate_count}</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Empty state — a reading, not a failure (#135) */}
          {candidates.length === 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
              <div className="flex items-start">
                <Info className="w-4 h-4 text-amber-600 mr-2 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-sm font-semibold text-amber-900">
                    {key('empty_title')}
                  </p>
                  {scan.empty_reason && (
                    <p className="mt-1 text-sm text-amber-800">{scan.empty_reason}</p>
                  )}
                  <p className="mt-2 text-xs text-amber-700">{key('empty_note')}</p>
                </div>
              </div>
            </div>
          )}

          {/* Candidates */}
          {candidates.length > 0 && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500 border-b border-gray-200">
                    <th className="py-2 pr-2">#</th>
                    <th className="py-2 pr-2">{key('col_symbol')}</th>
                    <th className="py-2 pr-2 text-right">{key('col_composite')}</th>
                    <th className="py-2 pr-2 text-right">1M</th>
                    <th className="py-2 pr-2 text-right">3M</th>
                    <th className="py-2 pr-2 text-right">6M</th>
                    <th className="py-2 pr-2 text-right">{key('col_base')}</th>
                    <th className="py-2 pr-2 text-right">{key('col_depth')}</th>
                    <th className="py-2 pr-2 text-right">{key('col_range_ratio')}</th>
                    <th className="py-2 pr-2 text-right">{key('col_volume_ratio')}</th>
                    <th className="py-2 pr-2 text-right">MA10</th>
                    <th className="py-2 pr-2 text-right">{key('col_pivot')}</th>
                    <th className="py-2 pr-2 text-right">{key('col_turnover')}</th>
                  </tr>
                </thead>
                <tbody>
                  {candidates.map((c) => (
                    <tr
                      key={c.symbol}
                      onClick={() => onSelectSymbol && onSelectSymbol(c.symbol)}
                      className="border-b border-gray-100 hover:bg-indigo-50 cursor-pointer"
                      title={key('row_hint')}
                    >
                      <td className="py-2 pr-2 text-gray-500">{c.rank}</td>
                      <td className="py-2 pr-2 font-semibold text-blue-600">{c.symbol}</td>
                      <td className="py-2 pr-2 text-right font-semibold">{num(c.composite)}</td>
                      <td className="py-2 pr-2 text-right">{pct(c.returns?.['21'])}</td>
                      <td className="py-2 pr-2 text-right">{pct(c.returns?.['63'])}</td>
                      <td className="py-2 pr-2 text-right">{pct(c.returns?.['126'])}</td>
                      <td className="py-2 pr-2 text-right">{c.base_length ?? '—'}</td>
                      <td className="py-2 pr-2 text-right">{pct(c.base_depth_pct)}</td>
                      <td className="py-2 pr-2 text-right">{num(c.range_ratio)}</td>
                      <td className="py-2 pr-2 text-right">{num(c.volume_ratio)}</td>
                      <td className="py-2 pr-2 text-right">{pct(c.ma10_distance_pct)}</td>
                      <td className="py-2 pr-2 text-right">
                        {num(c.pivot, 1)}
                        <span className="text-gray-400"> ({pct(c.pivot_distance_pct)})</span>
                      </td>
                      <td className="py-2 pr-2 text-right">{billions(c.avg_daily_value_vnd)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="mt-2 text-xs text-gray-500">{key('table_note')}</p>
            </div>
          )}

          {/* Funnel — where the universe went */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <p className="text-sm font-semibold text-gray-700 mb-2">{key('funnel_title')}</p>
            <table className="w-full text-sm">
              <tbody>
                {FUNNEL_ROWS.filter(([k]) => (accounting[k] ?? 0) > 0).map(([k, label]) => (
                  <tr key={k} className="border-b border-gray-100">
                    <td className="py-1.5 text-gray-500">{key(`funnel_${label}`)}</td>
                    <td className="py-1.5 text-right font-semibold w-20">{accounting[k]}</td>
                  </tr>
                ))}
                <tr>
                  <td className="py-1.5 text-gray-500">{key('funnel_accounted')}</td>
                  <td className="py-1.5 text-right font-semibold w-20">
                    {accounting.accounted} / {accounting.universe_total}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* VT-4 — reported beside the list, never instead of it (C4/EC-S5) */}
          {nullFpr && (
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
              <p className="text-sm font-semibold text-slate-700">{key('null_title')}</p>
              <p className="mt-1 text-sm text-slate-700">
                {key('null_body')
                  .replace('{{trials}}', nullFpr.trials)
                  .replace('{{universes}}', nullFpr.trials_with_candidates)
                  .replace('{{trial_pct}}', (nullFpr.trial_fpr * 100).toFixed(1))
                  .replace('{{symbol_pct}}', (nullFpr.symbol_fpr * 100).toFixed(2))}
              </p>
              <p className="mt-1 text-xs text-slate-500">{key('null_caveat')}</p>
            </div>
          )}
        </>
      )}

      {/* Per-symbol diagnostic */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <p className="text-sm font-semibold text-gray-700 mb-2">{key('lookup_title')}</p>
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="text"
            aria-label={key('lookup_label')}
            placeholder={key('lookup_placeholder')}
            value={lookupSymbol}
            onChange={(e) => setLookupSymbol(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && runLookup()}
            className="px-2 py-1.5 text-sm border border-gray-300 rounded-lg uppercase w-32"
          />
          <button
            onClick={runLookup}
            className="flex items-center px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <Search className="w-4 h-4 mr-2" />
            {key('lookup_button')}
          </button>
        </div>

        {lookupError && (
          <p className="mt-2 text-sm text-red-700">
            {lookupError.text
              || key(lookupError.code).replace('{{symbol}}', lookupError.symbol || '')}
          </p>
        )}

        {lookup && (
          <div className="mt-3">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-blue-600">{lookup.symbol}</span>
              <span
                className={`px-2 py-0.5 text-xs rounded border ${
                  VERDICT_TONE[lookup.verdict] || 'text-gray-700 bg-gray-50 border-gray-200'
                }`}
              >
                {lookup.verdict}
              </span>
              <span className="text-xs text-gray-500">{lookup.scan_date}</span>
            </div>
            {lookup.failed_clauses?.length > 0 && (
              <p className="mt-1 text-sm text-gray-700">
                {key('lookup_failed_on')}: {lookup.failed_clauses.join(', ')}
              </p>
            )}
            {/* Every clause with its numbers — a rejection the user cannot see
                the arithmetic of is a rejection they cannot act on. */}
            {['trend', 'base'].map((section) => {
              const clauses = lookup.detail?.[section]?.clauses;
              if (!clauses?.length) return null;
              return (
                <table key={section} className="w-full text-sm mt-2">
                  <tbody>
                    {clauses.map((cl) => (
                      <tr key={cl.name} className="border-b border-gray-100">
                        <td className="py-1.5 w-8">
                          <span className={cl.passed ? 'text-green-600' : 'text-red-600'}>
                            {cl.passed ? '✓' : '✗'}
                          </span>
                        </td>
                        <td className="py-1.5 text-gray-700 w-1/4">{cl.name}</td>
                        <td className="py-1.5 text-gray-500">{cl.detail}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default MomentumScannerPanel;
