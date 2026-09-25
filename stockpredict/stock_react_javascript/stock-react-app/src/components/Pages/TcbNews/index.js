/**
 * TCB News — paste the daily TCBS research email, review what the parser found,
 * then save it and send the confirmed recommendations to the watchlist.
 *
 * Deliberately two-step: Parse writes nothing, so a misread ticker or a wrong session
 * date is fixable before a single row exists. Save commits the mail and pushes only
 * the ticked recommendations (proposal_by = "TCB").
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Mail, Trash2, RefreshCw, Search, Save, AlertTriangle, CheckCircle2, Activity } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import tcbNewsService from '../../../services/tcbNewsService';

const ACTION_COLORS = {
  BUY: { bg: '#dcfce7', fg: '#166534' },
  SELL: { bg: '#fee2e2', fg: '#991b1b' },
  HOLD: { bg: '#e0e7ff', fg: '#3730a3' },
  WATCH: { bg: '#fef3c7', fg: '#92400e' },
};

const todayIso = () => new Date().toISOString().slice(0, 10);

/** Returns are stored as fractions (0.031 = +3.1%). Null means the horizon has not
 *  elapsed — shown as a dash, never as zero, which would read as "flat". */
const pct = (v, digits = 1) =>
  v == null ? '—' : `${v > 0 ? '+' : ''}${(v * 100).toFixed(digits)}%`;

const returnColor = (v) => (v == null ? '#9ca3af' : v < 0 ? '#dc2626' : '#16a34a');

const ActionBadge = ({ action, label }) => {
  const { t } = useTranslation();
  const palette = ACTION_COLORS[action] || { bg: '#f3f4f6', fg: '#6b7280' };
  return (
    <span
      title={label || ''}
      style={{
        background: palette.bg, color: palette.fg, borderRadius: 4,
        padding: '2px 8px', fontSize: 12, fontWeight: 600, whiteSpace: 'nowrap',
      }}
    >
      {action || t('tcb_news.action_unknown')}
    </span>
  );
};

/** One labelled number in the market-internals grid. */
const Stat = ({ label, value, unit, signed }) => {
  const missing = value === null || value === undefined;
  const color = !signed || missing ? '#111827' : value < 0 ? '#dc2626' : '#16a34a';
  const shown = missing
    ? '—'
    : `${signed && value > 0 ? '+' : ''}${new Intl.NumberFormat('vi-VN', {
      maximumFractionDigits: 2,
    }).format(value)}${unit ? ` ${unit}` : ''}`;
  return (
    <div style={{ padding: '8px 12px', background: '#f9fafb', borderRadius: 6 }}>
      <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 15, fontWeight: 600, color }}>{shown}</div>
    </div>
  );
};

const Banner = ({ tone, children }) => {
  const tones = {
    error: { bg: '#fef2f2', border: '#fecaca', fg: '#991b1b', Icon: AlertTriangle },
    success: { bg: '#f0fdf4', border: '#bbf7d0', fg: '#166534', Icon: CheckCircle2 },
    warn: { bg: '#fffbeb', border: '#fde68a', fg: '#92400e', Icon: AlertTriangle },
  };
  const { bg, border, fg, Icon } = tones[tone] || tones.warn;
  return (
    <div style={{
      display: 'flex', alignItems: 'flex-start', gap: 8, background: bg,
      border: `1px solid ${border}`, color: fg, borderRadius: 6,
      padding: '10px 12px', marginBottom: 16, fontSize: 14,
    }}>
      <Icon size={16} style={{ flexShrink: 0, marginTop: 2 }} />
      <div>{children}</div>
    </div>
  );
};

/**
 * TCB's track record. Withheld until enough calls are scored (FR-BM-RECORD) — a hit
 * rate over a handful of calls is noise dressed as evidence, so the panel shows the
 * progress towards reportability instead of a number that cannot be relied on.
 */
const TrackRecord = ({ record, notReportable, onScore, scoring, t }) => (
  <div style={{ marginTop: 32 }}>
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
      <h2 style={{ fontSize: 16, margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
        <Activity size={18} color="#2563eb" />
        {t('tcb_news.record_title')}
      </h2>
      <button onClick={onScore} className="btn-secondary" disabled={scoring}
        style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <RefreshCw size={14} className={scoring ? 'animate-spin' : ''} />
        {scoring ? t('tcb_news.scoring') : t('tcb_news.score_now')}
      </button>
    </div>

    {notReportable && (
      <p style={{ fontSize: 13, color: '#6b7280' }}>
        {t('tcb_news.record_not_yet', notReportable)}
      </p>
    )}

    {record && (
      <>
        <p style={{ fontSize: 12, color: '#6b7280', marginBottom: 8 }}>
          {t('tcb_news.record_hint', { scored: record.scored_calls, total: record.total_calls })}
        </p>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>
              <th style={{ padding: '6px 8px' }}>{t('tcb_news.col_horizon')}</th>
              <th style={{ padding: '6px 8px', textAlign: 'right' }}>{t('tcb_news.col_n')}</th>
              <th style={{ padding: '6px 8px', textAlign: 'right' }}>{t('tcb_news.col_hit_rate')}</th>
              <th style={{ padding: '6px 8px', textAlign: 'right' }}>{t('tcb_news.col_benchmark')}</th>
              <th style={{ padding: '6px 8px', textAlign: 'right' }}>{t('tcb_news.col_mean_return')}</th>
              <th style={{ padding: '6px 8px', textAlign: 'right' }}>{t('tcb_news.col_mean_excess')}</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(record.horizons).map(([horizon, h]) => {
              // Skill is the gap to the benchmark, not the hit rate itself (EC-B7).
              const beatsBenchmark =
                h.hit_rate != null && h.benchmark_hit_rate != null &&
                h.hit_rate > h.benchmark_hit_rate;
              return (
                <tr key={horizon} style={{ borderBottom: '1px solid #f3f4f6' }}>
                  <td style={{ padding: '6px 8px', fontWeight: 600 }}>{horizon}</td>
                  <td style={{ padding: '6px 8px', textAlign: 'right' }}>{h.n}</td>
                  <td style={{
                    padding: '6px 8px', textAlign: 'right',
                    fontWeight: beatsBenchmark ? 600 : 400,
                    color: beatsBenchmark ? '#16a34a' : '#111827',
                  }}>
                    {h.hit_rate == null ? '—' : `${(h.hit_rate * 100).toFixed(0)}%`}
                  </td>
                  <td style={{ padding: '6px 8px', textAlign: 'right', color: '#6b7280' }}>
                    {h.benchmark_hit_rate == null
                      ? '—' : `${(h.benchmark_hit_rate * 100).toFixed(0)}%`}
                  </td>
                  <td style={{ padding: '6px 8px', textAlign: 'right', color: returnColor(h.mean_return) }}>
                    {pct(h.mean_return)}
                  </td>
                  <td style={{ padding: '6px 8px', textAlign: 'right', color: returnColor(h.mean_excess_return) }}>
                    {pct(h.mean_excess_return)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <p style={{ fontSize: 12, color: '#6b7280', marginTop: 8 }}>
          {t('tcb_news.record_benchmark_note')}
        </p>
      </>
    )}
  </div>
);

const TcbNews = () => {
  const { t } = useTranslation();

  const [content, setContent] = useState('');
  const [sessionDate, setSessionDate] = useState(todayIso());
  const [preview, setPreview] = useState(null);
  const [selected, setSelected] = useState({});      // symbol -> boolean
  const [parsing, setParsing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const [ledger, setLedger] = useState([]);
  const [record, setRecord] = useState(null);
  const [notReportable, setNotReportable] = useState(null);
  const [scoring, setScoring] = useState(false);

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    const res = await tcbNewsService.list({ limit: 20 });
    setHistory(res.success && Array.isArray(res.data) ? res.data : []);
    setHistoryLoading(false);
  }, []);

  const loadLedger = useCallback(async () => {
    const [recos, rec] = await Promise.all([
      tcbNewsService.recos({ limit: 100 }),
      tcbNewsService.record(),
    ]);
    setLedger(recos.success && Array.isArray(recos.data) ? recos.data : []);
    if (rec.success) {
      setRecord(rec.data);
      setNotReportable(null);
    } else {
      // 409 is the designed answer below the minimum, not a failure to report.
      setRecord(null);
      setNotReportable({
        scored: rec.error?.response?.data?.scored_calls ?? null,
        detail: rec.error?.response?.data?.detail || '',
      });
    }
  }, []);

  useEffect(() => { loadHistory(); loadLedger(); }, [loadHistory, loadLedger]);

  const handleScore = async () => {
    setScoring(true);
    const res = await tcbNewsService.score();
    setScoring(false);
    if (!res.success) setError(errorMessage(res, 'tcb_news.score_error'));
    else loadLedger();
  };

  const errorMessage = (res, fallbackKey) =>
    res.error?.response?.data?.detail || res.error?.message || t(fallbackKey);

  const handleParse = async () => {
    if (!content.trim()) return;
    setParsing(true);
    setError(null);
    setResult(null);
    const res = await tcbNewsService.preview(content, sessionDate);
    setParsing(false);
    if (!res.success) {
      setPreview(null);
      setError(errorMessage(res, 'tcb_news.parse_error'));
      return;
    }
    setPreview(res.data);
    // The parser's date guess wins over today's date — it read the session out of the
    // macro paragraphs. Still editable before saving.
    if (res.data.session_date_hint) setSessionDate(res.data.session_date_hint);
    // Pre-tick every call we could normalise; an unknown label stays unticked so it
    // cannot reach the watchlist without the operator looking at it.
    setSelected(Object.fromEntries(
      (res.data.recos || []).map((r) => [r.symbol, Boolean(r.action)])
    ));
  };

  const handleSave = async () => {
    if (!preview) return;
    setSaving(true);
    setError(null);
    const pushSymbols = (preview.recos || [])
      .filter((r) => selected[r.symbol])
      .map((r) => r.symbol);
    const res = await tcbNewsService.save({ content, sessionDate, pushSymbols });
    setSaving(false);
    if (!res.success) {
      setError(errorMessage(res, 'tcb_news.save_error'));
      return;
    }
    setResult(res.data);
    if (res.data.created) {
      setContent('');
      setPreview(null);
      setSelected({});
    }
    loadHistory();
  };

  const handleDelete = async (id) => {
    const res = await tcbNewsService.remove(id);
    if (res.success) setHistory((prev) => prev.filter((m) => m.id !== id));
    else setError(errorMessage(res, 'tcb_news.delete_error'));
  };

  // Memoised so the `|| []` fallback doesn't hand useMemo a fresh array each render.
  const recos = useMemo(() => preview?.recos || [], [preview]);
  const selectedCount = useMemo(
    () => recos.filter((r) => selected[r.symbol]).length,
    [recos, selected],
  );

  return (
    <div style={{ padding: 24, maxWidth: 1100, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <h1 style={{ display: 'flex', alignItems: 'center', gap: 12, margin: 0 }}>
          <Mail color="#2563eb" />
          {t('tcb_news.title')}
        </h1>
      </div>
      <p style={{ color: '#6b7280', marginTop: 0, marginBottom: 20 }}>{t('tcb_news.subtitle')}</p>

      {error && <Banner tone="error">{error}</Banner>}

      {result && (
        <Banner tone={result.created ? 'success' : 'warn'}>
          {result.created
            ? t('tcb_news.saved', {
              date: result.mail.session_date,
              pushed: result.pushed.filter((p) => p.ok).length,
            })
            : t('tcb_news.duplicate', { date: result.mail.session_date })}
          {result.pushed?.some((p) => !p.ok) && (
            <div style={{ marginTop: 6 }}>
              {t('tcb_news.push_failed', {
                symbols: result.pushed.filter((p) => !p.ok).map((p) => p.symbol).join(', '),
              })}
            </div>
          )}
        </Banner>
      )}

      {/* ---- Paste ---- */}
      <label htmlFor="tcb-content" style={{ display: 'block', fontWeight: 600, marginBottom: 6 }}>
        {t('tcb_news.content_label')}
      </label>
      <textarea
        id="tcb-content"
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder={t('tcb_news.content_placeholder')}
        rows={12}
        style={{
          width: '100%', padding: 12, border: '1px solid #d1d5db', borderRadius: 6,
          fontFamily: 'inherit', fontSize: 13, lineHeight: 1.5, resize: 'vertical',
        }}
      />

      <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end', marginTop: 12, flexWrap: 'wrap' }}>
        <div>
          <label htmlFor="tcb-date" style={{ display: 'block', fontSize: 12, color: '#6b7280', marginBottom: 4 }}>
            {t('tcb_news.session_date_label')}
          </label>
          <input
            id="tcb-date"
            type="date"
            value={sessionDate}
            onChange={(e) => setSessionDate(e.target.value)}
            style={{ padding: 8, border: '1px solid #d1d5db', borderRadius: 6 }}
          />
        </div>
        <button
          onClick={handleParse}
          className="btn-secondary"
          disabled={parsing || !content.trim()}
          style={{ display: 'flex', alignItems: 'center', gap: 6 }}
        >
          <Search size={16} />
          {parsing ? t('tcb_news.parsing') : t('tcb_news.parse_button')}
        </button>
        <button
          onClick={handleSave}
          className="btn-primary"
          disabled={saving || !preview}
          style={{ display: 'flex', alignItems: 'center', gap: 6 }}
        >
          <Save size={16} />
          {saving ? t('tcb_news.saving') : t('tcb_news.save_button', { count: selectedCount })}
        </button>
      </div>

      {/* ---- Preview ---- */}
      {preview && (
        <div style={{ marginTop: 24, border: '1px solid #e5e7eb', borderRadius: 8, padding: 16 }}>
          <h2 style={{ fontSize: 16, marginTop: 0, marginBottom: 4 }}>{t('tcb_news.preview_title')}</h2>
          <p style={{ fontSize: 12, color: '#6b7280', marginTop: 0 }}>
            {t('tcb_news.preview_hint', { lang: preview.lang === 'vi' ? 'Tiếng Việt' : 'English' })}
          </p>

          <h3 style={{ fontSize: 14, marginBottom: 8 }}>{t('tcb_news.section_market')}</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 8 }}>
            <Stat label={t('tcb_news.vnindex_close')} value={preview.vnindex_close} />
            <Stat label={t('tcb_news.change_pct')} value={preview.vnindex_change_pct} unit="%" signed />
            <Stat label={t('tcb_news.change_pts')} value={preview.vnindex_change_pts} unit="đ" signed />
            <Stat label={t('tcb_news.matched_value')} value={preview.matched_value_bn} unit="tỷ" />
            <Stat label={t('tcb_news.matched_volume')} value={preview.matched_volume_m} unit="tr" />
            <Stat label={t('tcb_news.putthrough')} value={preview.putthrough_bn} unit="tỷ" />
            <Stat label={t('tcb_news.total_value')} value={preview.total_value_bn} unit="tỷ" />
            <Stat label={t('tcb_news.foreign_net')} value={preview.foreign_net_bn} unit="tỷ" signed />
            <Stat label={t('tcb_news.foreign_buy')} value={preview.foreign_buy_bn} unit="tỷ" />
            <Stat label={t('tcb_news.foreign_sell')} value={preview.foreign_sell_bn} unit="tỷ" />
            <Stat label={t('tcb_news.foreign_ytd')} value={preview.foreign_ytd_net_bn} unit="tỷ" signed />
            <Stat label="MA5" value={preview.ma5} />
            <Stat label="MA10" value={preview.ma10} />
            <Stat label="MA20" value={preview.ma20} />
            <Stat label="MA50" value={preview.ma50} />
          </div>

          {(preview.foreign_top_buy || preview.foreign_top_sell) && (
            <div style={{ marginTop: 12, fontSize: 13 }}>
              {preview.foreign_top_buy && (
                <div><strong>{t('tcb_news.top_buy')}:</strong> {preview.foreign_top_buy}</div>
              )}
              {preview.foreign_top_sell && (
                <div><strong>{t('tcb_news.top_sell')}:</strong> {preview.foreign_top_sell}</div>
              )}
            </div>
          )}

          {/* Recommendations — what reaches the watch screen */}
          <h3 style={{ fontSize: 14, marginTop: 20, marginBottom: 8 }}>
            {t('tcb_news.section_recos')}
          </h3>
          {recos.length === 0 ? (
            <p style={{ color: '#6b7280', fontSize: 13 }}>{t('tcb_news.no_recos')}</p>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>
                  <th style={{ padding: '6px 8px', width: 40 }}>{t('tcb_news.col_push')}</th>
                  <th style={{ padding: '6px 8px' }}>{t('tcb_news.col_symbol')}</th>
                  <th style={{ padding: '6px 8px' }}>{t('tcb_news.col_action')}</th>
                  <th style={{ padding: '6px 8px' }}>{t('tcb_news.col_label')}</th>
                  <th style={{ padding: '6px 8px' }}>{t('tcb_news.col_rationale')}</th>
                </tr>
              </thead>
              <tbody>
                {recos.map((r) => (
                  <tr key={r.symbol} style={{ borderBottom: '1px solid #f3f4f6' }}>
                    <td style={{ padding: '6px 8px' }}>
                      <input
                        type="checkbox"
                        checked={Boolean(selected[r.symbol])}
                        onChange={(e) =>
                          setSelected((prev) => ({ ...prev, [r.symbol]: e.target.checked }))}
                        aria-label={t('tcb_news.push_aria', { symbol: r.symbol })}
                      />
                    </td>
                    <td style={{ padding: '6px 8px', fontWeight: 600 }}>{r.symbol}</td>
                    <td style={{ padding: '6px 8px' }}>
                      <ActionBadge action={r.action} label={r.label_verbatim} />
                    </td>
                    <td style={{ padding: '6px 8px' }}>{r.label_verbatim}</td>
                    <td style={{ padding: '6px 8px', color: '#4b5563' }}>{r.rationale}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {recos.some((r) => !r.action) && (
            <p style={{ fontSize: 12, color: '#92400e', marginTop: 8 }}>
              {t('tcb_news.unknown_action_hint')}
            </p>
          )}

          {/* Corporate items */}
          {preview.companies?.length > 0 && (
            <>
              <h3 style={{ fontSize: 14, marginTop: 20, marginBottom: 8 }}>
                {t('tcb_news.section_companies')}
              </h3>
              <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, color: '#4b5563' }}>
                {preview.companies.map((c, i) => (
                  <li key={`${c.symbol}-${i}`} style={{ marginBottom: 6 }}>
                    <strong style={{ color: '#111827' }}>{c.symbol}:</strong> {c.item_text}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}

      {/* ---- Call ledger + track record ---- */}
      {ledger.length > 0 && (
        <div style={{ marginTop: 32 }}>
          <h2 style={{ fontSize: 16, margin: '0 0 8px' }}>{t('tcb_news.ledger_title')}</h2>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>
                  <th style={{ padding: '6px 8px' }}>{t('tcb_news.col_session')}</th>
                  <th style={{ padding: '6px 8px' }}>{t('tcb_news.col_symbol')}</th>
                  <th style={{ padding: '6px 8px' }}>{t('tcb_news.col_action')}</th>
                  <th style={{ padding: '6px 8px', textAlign: 'right' }}>1d</th>
                  <th style={{ padding: '6px 8px', textAlign: 'right' }}>5d</th>
                  <th style={{ padding: '6px 8px', textAlign: 'right' }}>20d</th>
                  <th style={{ padding: '6px 8px', textAlign: 'right' }}>60d</th>
                  <th style={{ padding: '6px 8px', textAlign: 'right' }}>
                    {t('tcb_news.col_vs_index_20d')}
                  </th>
                </tr>
              </thead>
              <tbody>
                {ledger.map((r) => (
                  <tr key={r.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                    <td style={{ padding: '6px 8px' }}>{r.session_date}</td>
                    <td style={{ padding: '6px 8px', fontWeight: 600 }}>{r.symbol}</td>
                    <td style={{ padding: '6px 8px' }}>
                      <ActionBadge action={r.action} label={r.label_verbatim} />
                    </td>
                    {['ret_1d', 'ret_5d', 'ret_20d', 'ret_60d', 'ret_20d_vs_index'].map((f) => (
                      <td key={f} style={{
                        padding: '6px 8px', textAlign: 'right', color: returnColor(r[f]),
                      }}>
                        {pct(r[f])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {/* The orange warning is now the exception: stock-data-service records the
              adjusted close, so it fires only where a symbol genuinely lacked one. The
              grey note below is true of every scored return and always shows. */}
          {ledger.some((r) => r.ret_adjusted === false && r.ref_close != null) && (
            <p style={{ fontSize: 12, color: '#92400e', marginTop: 8 }}>
              {t('tcb_news.unadjusted_warning')}
            </p>
          )}
          {ledger.some((r) => r.ref_close != null) && (
            <p style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>
              {t('tcb_news.capital_adjusted_note')}
            </p>
          )}
        </div>
      )}

      <TrackRecord record={record} notReportable={notReportable} onScore={handleScore}
        scoring={scoring} t={t} />

      {/* ---- Stored emails ---- */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 32 }}>
        <h2 style={{ fontSize: 16, margin: 0 }}>{t('tcb_news.history_title')}</h2>
        <button onClick={loadHistory} className="btn-secondary" disabled={historyLoading}
          style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <RefreshCw size={14} className={historyLoading ? 'animate-spin' : ''} />
          {t('tcb_news.refresh')}
        </button>
      </div>

      {history.length === 0 ? (
        <p style={{ color: '#6b7280', fontSize: 13 }}>{t('tcb_news.history_empty')}</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, marginTop: 8 }}>
          <thead>
            <tr style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>
              <th style={{ padding: '6px 8px' }}>{t('tcb_news.col_session')}</th>
              <th style={{ padding: '6px 8px' }}>VN-Index</th>
              <th style={{ padding: '6px 8px' }}>{t('tcb_news.col_change')}</th>
              <th style={{ padding: '6px 8px' }}>{t('tcb_news.foreign_net')}</th>
              <th style={{ padding: '6px 8px' }}>{t('tcb_news.section_recos')}</th>
              <th style={{ padding: '6px 8px', width: 40 }} />
            </tr>
          </thead>
          <tbody>
            {history.map((m) => (
              <tr key={m.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                <td style={{ padding: '6px 8px', fontWeight: 600 }}>{m.session_date}</td>
                <td style={{ padding: '6px 8px' }}>{m.vnindex_close ?? '—'}</td>
                <td style={{
                  padding: '6px 8px',
                  color: (m.vnindex_change_pct ?? 0) < 0 ? '#dc2626' : '#16a34a',
                }}>
                  {m.vnindex_change_pct == null
                    ? '—'
                    : `${m.vnindex_change_pct > 0 ? '+' : ''}${m.vnindex_change_pct}%`}
                </td>
                <td style={{
                  padding: '6px 8px',
                  color: (m.foreign_net_bn ?? 0) < 0 ? '#dc2626' : '#16a34a',
                }}>
                  {m.foreign_net_bn ?? '—'}
                </td>
                <td style={{ padding: '6px 8px', display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {(m.recos || []).map((r) => (
                    <span key={r.id} style={{ display: 'inline-flex', gap: 4, alignItems: 'center' }}>
                      <strong>{r.symbol}</strong>
                      <ActionBadge action={r.action} label={r.label_verbatim} />
                    </span>
                  ))}
                </td>
                <td style={{ padding: '6px 8px' }}>
                  <button
                    onClick={() => handleDelete(m.id)}
                    className="btn-icon"
                    title={t('tcb_news.delete_tooltip')}
                    aria-label={t('tcb_news.delete_tooltip')}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#dc2626' }}
                  >
                    <Trash2 size={16} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default TcbNews;
