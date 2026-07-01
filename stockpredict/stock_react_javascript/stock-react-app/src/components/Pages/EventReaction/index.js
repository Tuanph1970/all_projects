// Event-Reaction viewer — price reaction to the SURPRISE of discrete events.
// Measures one event (surprise + market-model abnormal returns + Lee-Mykland jump),
// accumulates measured events into a report table, then runs the cross-sectional
// exposure regression (CAR ~ surprise) across them.
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Activity, Zap, TrendingUp, BarChart2, Play, Trash2, Info, Check, ArrowRight, Target, ListChecks } from 'lucide-react';
import eventReactionService from '../../../services/eventReactionService';

// ── Palette & theme (mirrors ChartDecomp) ────────────────────────────────────
const COLORS = {
  bg: '#f9fafb', card: '#ffffff', border: '#e5e7eb', grid: '#e5e7eb',
  text: '#111827', muted: '#6b7280', accent: '#6366f1', accentLight: '#eef2ff',
  success: '#10b981', warn: '#f59e0b', danger: '#ef4444', blue: '#3b82f6',
};
const FONT = "'Inter', -apple-system, BlinkMacSystemFont, sans-serif";

// httpClient returns { success, data } | { success:false, error } and never throws.
function unwrap(resp) {
  if (!resp || !resp.success) {
    const err = resp?.error;
    throw new Error(err?.data?.detail ?? err?.message ?? 'Request failed');
  }
  return resp.data;
}

const fmt = (x, d = 3) => (x === null || x === undefined || Number.isNaN(x) ? '—' : Number(x).toFixed(d));
const pct = (x, d = 3) => (x === null || x === undefined || Number.isNaN(x) ? '—' : `${(Number(x) * 100).toFixed(d)}%`);

const s = {
  page: { background: COLORS.bg, minHeight: '100vh', padding: '10px 14px', fontFamily: FONT, color: COLORS.text },
  h1: { fontSize: 18, fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: 8 },
  sub: { fontSize: 12, color: COLORS.muted, marginTop: 2 },
  card: { background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: 10, padding: 14, marginTop: 12 },
  cardTitle: { fontSize: 13, fontWeight: 700, marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 10 },
  field: { display: 'flex', flexDirection: 'column', gap: 4 },
  label: { fontSize: 11, color: COLORS.muted, fontWeight: 600 },
  input: { padding: '7px 9px', border: `1px solid ${COLORS.border}`, borderRadius: 7, fontSize: 13, fontFamily: FONT },
  btn: (disabled) => ({
    padding: '8px 14px', border: 'none', borderRadius: 7, fontSize: 13, fontWeight: 600,
    background: disabled ? '#c7d2fe' : COLORS.accent, color: '#fff',
    cursor: disabled ? 'not-allowed' : 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6,
  }),
  btnGhost: { padding: '7px 12px', border: `1px solid ${COLORS.border}`, borderRadius: 7, fontSize: 12,
    background: '#fff', color: COLORS.muted, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6 },
  err: { background: '#fef2f2', border: `1px solid ${COLORS.danger}`, color: COLORS.danger, borderRadius: 8, padding: '8px 12px', fontSize: 12, marginTop: 10 },
  statGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 10 },
  stat: { background: COLORS.bg, border: `1px solid ${COLORS.border}`, borderRadius: 8, padding: '8px 10px' },
  statLabel: { fontSize: 10, color: COLORS.muted, fontWeight: 600, textTransform: 'uppercase' },
  statValue: { fontSize: 16, fontWeight: 700, marginTop: 2 },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 12 },
  th: { textAlign: 'left', padding: '7px 8px', borderBottom: `2px solid ${COLORS.border}`, color: COLORS.muted, fontWeight: 700 },
  td: { padding: '7px 8px', borderBottom: `1px solid ${COLORS.grid}` },
  badge: (c) => ({ display: 'inline-block', padding: '1px 8px', borderRadius: 10, fontSize: 11, fontWeight: 700, color: '#fff', background: c }),
  tabBar: { display: 'flex', gap: 0, borderBottom: `2px solid ${COLORS.border}`, marginTop: 12 },
  tab: (active) => ({
    padding: '9px 16px', border: 'none', background: 'transparent', cursor: 'pointer',
    fontSize: 13, fontWeight: 700, fontFamily: FONT,
    color: active ? COLORS.accent : COLORS.muted,
    borderBottom: `2px solid ${active ? COLORS.accent : 'transparent'}`,
    marginBottom: -2, display: 'inline-flex', alignItems: 'center', gap: 6,
  }),
};

function Stat({ label, value, color }) {
  return (
    <div style={s.stat}>
      <div style={s.statLabel}>{label}</div>
      <div style={{ ...s.statValue, color: color || COLORS.text }}>{value}</div>
    </div>
  );
}

// ── Overview tab — static, bilingual (EN + VI) "what & how" guide ──────────────
// Deliberately language-independent: both English and Vietnamese are shown side by
// side so the page reads the same regardless of the app's active i18n language.

// Why this menu is useful — one benefit per row, EN + VI.
const BENEFITS = [
  { en: 'Measure how a stock reacts to the SURPRISE in an event (earnings, rate decision, macro release) — not the headline itself. Markets price what they did not already expect.',
    vi: 'Đo phản ứng của cổ phiếu với phần BẤT NGỜ của sự kiện (KQKD, quyết định lãi suất, số liệu vĩ mô) — không phải bản tin. Thị trường định giá phần chưa được kỳ vọng.' },
  { en: 'Strip out the market-wide move (β × market) so you see the stock’s genuine abnormal return (CAR), not just “everything went up today”.',
    vi: 'Loại bỏ phần biến động chung của thị trường (β × thị trường) để thấy lợi suất bất thường thực sự của cổ phiếu (CAR), không chỉ là “hôm nay mọi thứ đều tăng”.' },
  { en: 'Tell a real price jump from ordinary volatility with the Lee–Mykland jump test, and calibrate its false-positive rate.',
    vi: 'Phân biệt một cú nhảy giá thật với biến động thông thường bằng kiểm định nhảy Lee–Mykland, và hiệu chỉnh tỷ lệ báo động giả.' },
  { en: 'Quantify your portfolio’s exposure to surprises (γ₁): how systematically your names move per unit of surprise, with clustering-robust inference for same-day events.',
    vi: 'Định lượng độ nhạy của danh mục với bất ngờ (γ₁): các mã của bạn phản ứng có hệ thống ra sao trên mỗi đơn vị bất ngờ, với suy diễn bền vững theo cụm cho các sự kiện cùng ngày.' },
  { en: 'No look-ahead bias: only the observed surprise and the post-event window are used — nothing from the future leaks in.',
    vi: 'Không nhìn trước tương lai: chỉ dùng phần bất ngờ quan sát được và cửa sổ sau sự kiện — không có dữ liệu tương lai rò rỉ vào.' },
];

// How to use the GUI to reach the goal — ordered steps, EN + VI.
const STEPS = [
  { en_t: 'Measure an event', vi_t: 'Đo một sự kiện',
    en: 'On the Analysis tab, fill in Symbol, Market index, Event kind, Event date, Actual and Consensus, then click Measure. Surprise = Actual − Consensus.',
    vi: 'Ở thẻ Phân tích, nhập Mã CK, Chỉ số thị trường, Loại sự kiện, Ngày sự kiện, Giá trị thực tế và Đồng thuận, rồi bấm Đo. Bất ngờ = Thực tế − Đồng thuận.' },
  { en_t: 'Read the latest measurement', vi_t: 'Đọc kết quả đo mới nhất',
    en: 'The result card shows Surprise (σ, standardized), CAR (abnormal return), Beta, and whether the reaction was a Jump. Green = positive, red = negative.',
    vi: 'Thẻ kết quả hiển thị Bất ngờ (σ, đã chuẩn hoá), CAR (lợi suất bất thường), Beta, và liệu phản ứng có phải một cú Nhảy. Xanh = dương, đỏ = âm.' },
  { en_t: 'Build up at least 3 events', vi_t: 'Tích luỹ tối thiểu 3 sự kiện',
    en: 'Each measurement is appended to the “Measured events” table. Measure several events (same or different symbols) to form a cross-section.',
    vi: 'Mỗi lần đo được thêm vào bảng “Sự kiện đã đo”. Hãy đo nhiều sự kiện (cùng hoặc khác mã) để tạo thành một lát cắt chéo.' },
  { en_t: 'Run cross-sectional exposure', vi_t: 'Chạy độ nhạy chéo',
    en: 'Pick an Inference mode (cluster by event date / portfolio / iid), then click Run exposure. Read γ₁ (exposure), its t-stat, and R².',
    vi: 'Chọn kiểu Suy diễn (gom cụm theo ngày sự kiện / danh mục / iid), rồi bấm Chạy độ nhạy. Đọc γ₁ (độ nhạy), giá trị t, và R².' },
  { en_t: 'Optional: calibrate the jump test', vi_t: 'Tuỳ chọn: hiệu chỉnh kiểm định nhảy',
    en: 'Tick “Compute jump null-FPR” before measuring to estimate the jump test’s false-positive rate under a no-jump null.',
    vi: 'Tích “Tính null-FPR cho nhảy” trước khi đo để ước lượng tỷ lệ báo động giả của kiểm định nhảy dưới giả thuyết không có nhảy.' },
];

// Compact glossary of the metrics shown on the Analysis tab — EN + VI.
const GLOSSARY = [
  { term: 'Surprise (σ)', en: 'Standardized surprise: how many standard deviations Actual beat/missed Consensus.',
    vi: 'Bất ngờ chuẩn hoá: Thực tế vượt/hụt Đồng thuận bao nhiêu độ lệch chuẩn.' },
  { term: 'CAR', en: 'Cumulative Abnormal Return over the event window, after removing the market move.',
    vi: 'Lợi suất bất thường luỹ kế trong cửa sổ sự kiện, sau khi loại bỏ biến động thị trường.' },
  { term: 'Jump', en: 'Lee–Mykland test flag: was the move a genuine discontinuity, not normal noise?',
    vi: 'Cờ kiểm định Lee–Mykland: cú biến động có phải bước nhảy thật, không phải nhiễu thường?' },
  { term: 'Exposure (γ₁)', en: 'Slope of CAR on surprise across events — the systematic reaction per unit of surprise.',
    vi: 'Hệ số góc của CAR theo bất ngờ qua các sự kiện — phản ứng hệ thống trên mỗi đơn vị bất ngờ.' },
];

function LangTag({ children, color }) {
  return (
    <span style={{ fontSize: 9.5, fontWeight: 800, letterSpacing: '0.06em', color: '#fff',
      background: color, borderRadius: 4, padding: '1px 5px', flexShrink: 0 }}>{children}</span>
  );
}

function OverviewTab() {
  const ov = {
    hero: { background: 'linear-gradient(135deg, #eef2ff 0%, #f0f9ff 100%)', border: `1px solid ${COLORS.border}`,
      borderRadius: 12, padding: '18px 22px', marginTop: 12 },
    heroTitle: { fontSize: 19, fontWeight: 800, color: COLORS.text, margin: 0 },
    heroTitleVi: { fontSize: 14, fontWeight: 700, color: COLORS.accent, margin: '4px 0 0' },
    heroSub: { fontSize: 12.5, color: '#4b5563', lineHeight: 1.6, marginTop: 8, maxWidth: 900 },
    twoCol: { display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 12 },
    col: { flex: '1 1 380px', background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: 10, padding: '14px 16px' },
    sectionTitle: { fontSize: 12, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#374151',
      marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 },
    biRow: { marginBottom: 12 },
    biLine: { display: 'flex', gap: 7, alignItems: 'flex-start', fontSize: 12, lineHeight: 1.5, marginBottom: 3 },
    stepNum: { width: 20, height: 20, borderRadius: 99, background: COLORS.accentLight, color: COLORS.accent,
      fontSize: 11, fontWeight: 800, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
    stepTitle: { fontSize: 12.5, fontWeight: 700, color: COLORS.text },
    stepTitleVi: { fontSize: 11.5, fontWeight: 600, color: COLORS.accent },
    gloss: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 10, marginTop: 12 },
    glossCard: { background: COLORS.bg, border: `1px solid ${COLORS.border}`, borderRadius: 8, padding: '10px 12px' },
    glossTerm: { fontSize: 12, fontWeight: 800, color: COLORS.accent, marginBottom: 4 },
  };

  return (
    <div>
      {/* Hero */}
      <div style={ov.hero}>
        <h2 style={ov.heroTitle}>Trade the surprise, not the headline</h2>
        <p style={ov.heroTitleVi}>Giao dịch phần bất ngờ, không phải bản tin</p>
        <p style={ov.heroSub}>
          <strong>EN — </strong>This screen measures how a stock’s price reacts to the <em>surprise</em> in an
          event — the part the market did not already expect — and how systematically your portfolio is exposed to it.
        </p>
        <p style={{ ...ov.heroSub, marginTop: 4 }}>
          <strong>VI — </strong>Màn hình này đo cách giá cổ phiếu phản ứng với phần <em>bất ngờ</em> của một sự
          kiện — phần mà thị trường chưa kỳ vọng — và mức độ danh mục của bạn nhạy cảm với nó một cách có hệ thống.
        </p>
      </div>

      <div style={ov.twoCol}>
        {/* Benefits */}
        <div style={ov.col}>
          <div style={ov.sectionTitle}><Target size={14} color={COLORS.accent} /> What it does for you · Lợi ích</div>
          {BENEFITS.map((b, i) => (
            <div key={i} style={ov.biRow}>
              <div style={ov.biLine}><Check size={14} style={{ color: COLORS.success, flexShrink: 0, marginTop: 1 }} />
                <span><LangTag color={COLORS.blue}>EN</LangTag> {b.en}</span></div>
              <div style={{ ...ov.biLine, marginLeft: 21, color: '#4b5563' }}>
                <span><LangTag color={COLORS.success}>VI</LangTag> {b.vi}</span></div>
            </div>
          ))}
        </div>

        {/* How to use */}
        <div style={ov.col}>
          <div style={ov.sectionTitle}><ListChecks size={14} color={COLORS.accent} /> How to use the GUI · Cách dùng</div>
          {STEPS.map((st, i) => (
            <div key={i} style={{ ...ov.biRow, display: 'flex', gap: 9 }}>
              <div style={ov.stepNum}>{i + 1}</div>
              <div>
                <div style={ov.stepTitle}>{st.en_t} <span style={ov.stepTitleVi}>· {st.vi_t}</span></div>
                <div style={{ fontSize: 12, color: '#374151', lineHeight: 1.5, marginTop: 2 }}>
                  <LangTag color={COLORS.blue}>EN</LangTag> {st.en}</div>
                <div style={{ fontSize: 12, color: '#4b5563', lineHeight: 1.5, marginTop: 2 }}>
                  <LangTag color={COLORS.success}>VI</LangTag> {st.vi}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Flow strip */}
      <div style={{ ...ov.col, marginTop: 12, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        {['Measure event · Đo sự kiện', 'Read CAR / Jump · Đọc CAR / Nhảy', 'Collect ≥3 · Gom ≥3', 'Run exposure γ₁ · Chạy độ nhạy γ₁'].map((label, i, arr) => (
          <React.Fragment key={i}>
            <span style={{ fontSize: 11.5, fontWeight: 700, color: COLORS.text, background: COLORS.accentLight,
              borderRadius: 7, padding: '6px 10px' }}>{label}</span>
            {i < arr.length - 1 && <ArrowRight size={16} color="#cbd5e1" />}
          </React.Fragment>
        ))}
      </div>

      {/* Glossary */}
      <div style={{ ...ov.col, marginTop: 12 }}>
        <div style={ov.sectionTitle}><Info size={14} color={COLORS.accent} /> Metrics glossary · Chú giải chỉ số</div>
        <div style={ov.gloss}>
          {GLOSSARY.map((g, i) => (
            <div key={i} style={ov.glossCard}>
              <div style={ov.glossTerm}>{g.term}</div>
              <div style={{ fontSize: 11.5, color: '#374151', lineHeight: 1.45, marginBottom: 3 }}>
                <LangTag color={COLORS.blue}>EN</LangTag> {g.en}</div>
              <div style={{ fontSize: 11.5, color: '#4b5563', lineHeight: 1.45 }}>
                <LangTag color={COLORS.success}>VI</LangTag> {g.vi}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function EventReactionPage() {
  const { t } = useTranslation();

  const [activeTab, setActiveTab] = useState('overview');
  const [form, setForm] = useState({
    symbol: 'FPT', market_symbol: 'VNINDEX', kind: 'rate_decision',
    date: '2023-06-01', actual: '0.50', consensus: '0.25',
  });
  const [computeNull, setComputeNull] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [latest, setLatest] = useState(null);
  const [rows, setRows] = useState([]);

  const [cluster, setCluster] = useState('event_date');
  const [expLoading, setExpLoading] = useState(false);
  const [exposure, setExposure] = useState(null);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  async function measure() {
    setLoading(true); setError('');
    try {
      const ts = `${form.date}T00:00:00Z`;
      const body = {
        symbol: form.symbol.trim().toUpperCase(),
        market_symbol: form.market_symbol.trim().toUpperCase(),
        method: 'consensus',
        jump_n_null: computeNull ? 200 : 0,
        event: {
          event_id: `${form.symbol}-${form.date}-${rows.length + 1}`,
          ts_utc: ts,
          kind: form.kind.trim() || 'event',
          actual: parseFloat(form.actual),
          consensus: parseFloat(form.consensus),
        },
      };
      const data = unwrap(await eventReactionService.measure(body));
      setLatest({ ...data, symbol: body.symbol, date: form.date, kind: body.event.kind });
      setRows((r) => [
        ...r,
        {
          asset: body.symbol, event_date: ts, date: form.date, kind: body.event.kind,
          surprise: data.surprise.s, sign: data.surprise.sign,
          car: data.abnormal.car, is_jump: data.jump.is_jump, statistic: data.jump.statistic,
        },
      ]);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function runExposure() {
    setExpLoading(true); setError('');
    try {
      const payloadRows = rows.map((r) => ({
        asset: r.asset, event_date: r.event_date, surprise: r.surprise, car: r.car,
      }));
      const data = unwrap(await eventReactionService.crossSection({ rows: payloadRows, cluster }));
      setExposure(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setExpLoading(false);
    }
  }

  const canExpose = rows.length >= 3;

  return (
    <div style={s.page}>
      <div>
        <h1 style={s.h1}><Activity size={20} color={COLORS.accent} /> {t('event_reaction.title')}</h1>
        <div style={s.sub}>{t('event_reaction.subtitle')}</div>
      </div>

      {/* Tabs */}
      <div style={s.tabBar}>
        <button style={s.tab(activeTab === 'overview')} onClick={() => setActiveTab('overview')}>
          <Info size={15} /> {t('event_reaction.tab_overview')}
        </button>
        <button style={s.tab(activeTab === 'analysis')} onClick={() => setActiveTab('analysis')}>
          <Zap size={15} /> {t('event_reaction.tab_analysis')}
        </button>
      </div>

      {activeTab === 'overview' && <OverviewTab />}

      {activeTab === 'analysis' && (
      <>
      {/* Input */}
      <div style={s.card}>
        <div style={s.cardTitle}><Zap size={15} color={COLORS.accent} /> {t('event_reaction.measure_title')}</div>
        <div style={s.grid}>
          <div style={s.field}><span style={s.label}>{t('event_reaction.symbol')}</span>
            <input style={s.input} value={form.symbol} onChange={set('symbol')} /></div>
          <div style={s.field}><span style={s.label}>{t('event_reaction.market')}</span>
            <input style={s.input} value={form.market_symbol} onChange={set('market_symbol')} /></div>
          <div style={s.field}><span style={s.label}>{t('event_reaction.kind')}</span>
            <input style={s.input} value={form.kind} onChange={set('kind')} /></div>
          <div style={s.field}><span style={s.label}>{t('event_reaction.date')}</span>
            <input type="date" style={s.input} value={form.date} onChange={set('date')} /></div>
          <div style={s.field}><span style={s.label}>{t('event_reaction.actual')}</span>
            <input type="number" step="0.01" style={s.input} value={form.actual} onChange={set('actual')} /></div>
          <div style={s.field}><span style={s.label}>{t('event_reaction.consensus')}</span>
            <input type="number" step="0.01" style={s.input} value={form.consensus} onChange={set('consensus')} /></div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginTop: 12, flexWrap: 'wrap' }}>
          <button style={s.btn(loading)} onClick={measure} disabled={loading}>
            <Play size={14} /> {loading ? t('event_reaction.running') : t('event_reaction.measure')}
          </button>
          <label style={{ fontSize: 12, color: COLORS.muted, display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <input type="checkbox" checked={computeNull} onChange={(e) => setComputeNull(e.target.checked)} />
            {t('event_reaction.compute_null')}
          </label>
          <span style={{ fontSize: 11, color: COLORS.muted }}>{t('event_reaction.method_note')}</span>
        </div>
        {error && <div style={s.err}>{error}</div>}
      </div>

      {/* Latest measurement detail */}
      {latest && (
        <div style={s.card}>
          <div style={s.cardTitle}><TrendingUp size={15} color={COLORS.blue} />
            {t('event_reaction.latest')}: {latest.symbol} · {latest.date}</div>
          <div style={s.statGrid}>
            <Stat label={t('event_reaction.surprise_std')} value={fmt(latest.surprise.s, 2)}
              color={latest.surprise.sign > 0 ? COLORS.success : latest.surprise.sign < 0 ? COLORS.danger : COLORS.muted} />
            <Stat label={t('event_reaction.surprise_raw')} value={fmt(latest.surprise.s_raw)} />
            <Stat label={t('event_reaction.expected')} value={fmt(latest.surprise.expected)} />
            <Stat label={t('event_reaction.car')} value={pct(latest.abnormal.car)}
              color={latest.abnormal.car >= 0 ? COLORS.success : COLORS.danger} />
            <Stat label={t('event_reaction.beta')} value={fmt(latest.abnormal.beta, 2)} />
            <Stat label={t('event_reaction.sigma_ar')} value={pct(latest.abnormal.sigma_ar)} />
            <Stat label={t('event_reaction.jump')} value={latest.jump.is_jump ? t('event_reaction.yes') : t('event_reaction.no')}
              color={latest.jump.is_jump ? COLORS.warn : COLORS.muted} />
            <Stat label={t('event_reaction.statistic')} value={fmt(latest.jump.statistic, 2)} />
            {computeNull && <Stat label={t('event_reaction.null_fpr')}
              value={latest.jump.null_fpr === null ? '—' : pct(latest.jump.null_fpr, 1)} />}
          </div>
        </div>
      )}

      {/* Report table */}
      <div style={s.card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={s.cardTitle}><BarChart2 size={15} color={COLORS.accent} /> {t('event_reaction.report')} ({rows.length})</div>
          {rows.length > 0 && (
            <button style={s.btnGhost} onClick={() => { setRows([]); setExposure(null); }}>
              <Trash2 size={13} /> {t('event_reaction.clear')}
            </button>
          )}
        </div>
        {rows.length === 0 ? (
          <div style={{ fontSize: 12, color: COLORS.muted, padding: '8px 0' }}>{t('event_reaction.no_rows')}</div>
        ) : (
          <table style={s.table}>
            <thead><tr>
              {['symbol', 'date', 'kind', 'surprise_std', 'car', 'jump', 'statistic'].map((c) => (
                <th key={c} style={s.th}>{t(`event_reaction.col_${c}`)}</th>
              ))}
            </tr></thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  <td style={{ ...s.td, fontWeight: 600 }}>{r.asset}</td>
                  <td style={s.td}>{r.date}</td>
                  <td style={s.td}>{r.kind}</td>
                  <td style={{ ...s.td, color: r.sign > 0 ? COLORS.success : r.sign < 0 ? COLORS.danger : COLORS.muted, fontWeight: 600 }}>{fmt(r.surprise, 2)}</td>
                  <td style={{ ...s.td, color: r.car >= 0 ? COLORS.success : COLORS.danger }}>{pct(r.car)}</td>
                  <td style={s.td}>{r.is_jump ? <span style={s.badge(COLORS.warn)}>{t('event_reaction.yes')}</span> : <span style={{ color: COLORS.muted }}>{t('event_reaction.no')}</span>}</td>
                  <td style={s.td}>{fmt(r.statistic, 2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Cross-sectional exposure */}
      <div style={s.card}>
        <div style={s.cardTitle}><TrendingUp size={15} color={COLORS.success} /> {t('event_reaction.exposure_title')}</div>
        <div style={{ fontSize: 12, color: COLORS.muted, marginBottom: 10 }}>{t('event_reaction.exposure_hint')}</div>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 12, flexWrap: 'wrap' }}>
          <div style={s.field}><span style={s.label}>{t('event_reaction.cluster')}</span>
            <select style={s.input} value={cluster} onChange={(e) => setCluster(e.target.value)}>
              <option value="event_date">{t('event_reaction.cluster_event_date')}</option>
              <option value="portfolio">{t('event_reaction.cluster_portfolio')}</option>
              <option value="iid">{t('event_reaction.cluster_iid')}</option>
            </select>
          </div>
          <button style={s.btn(!canExpose || expLoading)} onClick={runExposure} disabled={!canExpose || expLoading}>
            <Play size={14} /> {expLoading ? t('event_reaction.running') : t('event_reaction.run_exposure')}
          </button>
          {!canExpose && <span style={{ fontSize: 11, color: COLORS.muted }}>{t('event_reaction.need_three')}</span>}
        </div>
        {exposure && (
          <div style={{ ...s.statGrid, marginTop: 12 }}>
            <Stat label={t('event_reaction.gamma1')} value={fmt(exposure.gamma1, 4)} color={COLORS.accent} />
            <Stat label={t('event_reaction.se')} value={fmt(exposure.se_gamma1, 4)} />
            <Stat label="t" value={exposure.se_gamma1 ? fmt(exposure.gamma1 / exposure.se_gamma1, 2) : '—'} />
            <Stat label={t('event_reaction.gamma0')} value={fmt(exposure.gamma0, 4)} />
            <Stat label={t('event_reaction.r_squared')} value={fmt(exposure.r_squared, 3)} />
            <Stat label={t('event_reaction.n_events')} value={exposure.n_event_dates} />
          </div>
        )}
      </div>
      </>
      )}
    </div>
  );
}
