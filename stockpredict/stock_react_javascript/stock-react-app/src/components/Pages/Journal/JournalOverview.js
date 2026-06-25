// Trade Journal — Overview: why journaling matters + a journaling pipeline diagram.
// Mirrors the look of DecisionHelperOverview (General View).
import React from 'react';
import { useTranslation } from 'react-i18next';

// ── Primitive building blocks (same visual language as DecisionHelperOverview) ──

const Box = ({ label, sub, color = '#2C5F4A', bg = '#d1fae5', border = '#6ee7b7', width = 180 }) => (
  <div style={{
    width, minHeight: 56, background: bg, border: `2px solid ${border}`,
    borderRadius: 10, padding: '10px 14px', textAlign: 'center',
    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
    boxShadow: '0 2px 6px rgba(0,0,0,0.07)',
  }}>
    <div style={{ fontWeight: 700, fontSize: 13, color, lineHeight: 1.3 }}>{label}</div>
    {sub && <div style={{ fontSize: 10, color, opacity: 0.75, marginTop: 3 }}>{sub}</div>}
  </div>
);

const Arrow = ({ dir = 'down', label, length = 32 }) => {
  const isHoriz = dir === 'right' || dir === 'left';
  return (
    <div style={{
      display: 'flex', flexDirection: isHoriz ? 'row' : 'column',
      alignItems: 'center', justifyContent: 'center', gap: 2,
    }}>
      {label && !isHoriz && (
        <span style={{ fontSize: 10, color: '#9ca3af', whiteSpace: 'nowrap' }}>{label}</span>
      )}
      <div style={{
        width: isHoriz ? length : 2, height: isHoriz ? 2 : length,
        background: '#d1d5db', position: 'relative', flexShrink: 0,
      }}>
        <div style={{
          position: 'absolute',
          ...(dir === 'down'  ? { bottom: -5, left: '50%', transform: 'translateX(-50%)',
              borderLeft: '5px solid transparent', borderRight: '5px solid transparent', borderTop: '6px solid #9ca3af' } : {}),
          ...(dir === 'up'    ? { top: -5, left: '50%', transform: 'translateX(-50%)',
              borderLeft: '5px solid transparent', borderRight: '5px solid transparent', borderBottom: '6px solid #9ca3af' } : {}),
          ...(dir === 'right' ? { right: -5, top: '50%', transform: 'translateY(-50%)',
              borderTop: '5px solid transparent', borderBottom: '5px solid transparent', borderLeft: '6px solid #9ca3af' } : {}),
          ...(dir === 'left'  ? { left: -5, top: '50%', transform: 'translateY(-50%)',
              borderTop: '5px solid transparent', borderBottom: '5px solid transparent', borderRight: '6px solid #9ca3af' } : {}),
        }} />
      </div>
      {label && isHoriz && (
        <span style={{ fontSize: 10, color: '#9ca3af', whiteSpace: 'nowrap' }}>{label}</span>
      )}
    </div>
  );
};

const SectionTitle = ({ children }) => (
  <div style={{
    fontFamily: 'var(--font-mono, monospace)', fontSize: 10, fontWeight: 700,
    letterSpacing: '0.1em', textTransform: 'uppercase',
    color: '#9ca3af', marginBottom: 12, textAlign: 'center',
  }}>
    {children}
  </div>
);

// ── Main page ─────────────────────────────────────────────────────────────────

const JournalOverview = () => {
  const { t } = useTranslation();
  const benefits = t('journal.overview.benefits', { returnObjects: true });
  const benefitList = Array.isArray(benefits) ? benefits : [];

  // Journaling loop stages (mirrors the actual sub-menus / routes)
  const STAGES = [
    { label: t('journal.overview.flow_plan'),    sub: '/daily-planning', color: '#1e40af', bg: '#dbeafe', border: '#93c5fd' },
    { label: t('journal.overview.flow_execute'), sub: t('journal.overview.flow_execute_sub'), color: '#5b21b6', bg: '#ede9fe', border: '#c4b5fd' },
    { label: t('journal.overview.flow_log'),     sub: '/trade-log',      color: '#065f46', bg: '#d1fae5', border: '#6ee7b7' },
    { label: t('journal.overview.flow_reflect'), sub: '/trade-diary',    color: '#92400e', bg: '#fef9c3', border: '#fde68a' },
    { label: t('journal.overview.flow_review'),  sub: '/weekly-review',  color: '#1e40af', bg: '#dbeafe', border: '#93c5fd' },
    { label: t('journal.overview.flow_improve'), sub: t('journal.overview.flow_improve_sub'), color: '#065f46', bg: '#d1fae5', border: '#34d399' },
  ];

  return (
    <div style={{ padding: '24px 28px', maxWidth: 1100, margin: '0 auto', color: '#111827' }}>

      {/* ── Page header ── */}
      <div style={{ marginBottom: 28, borderBottom: '1px solid #e5e7eb', paddingBottom: 16 }}>
        <h2 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>
          {t('journal.overview.title')}
        </h2>
        <p style={{ margin: '6px 0 0', color: '#6b7280', fontSize: 13 }}>
          {t('journal.overview.subtitle')}
        </p>
      </div>

      {/* ── Why it matters (static paragraph) ── */}
      <div style={{
        background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12,
        padding: '18px 22px', marginBottom: 28, boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
      }}>
        <h3 style={{ margin: '0 0 10px', fontSize: 15, fontWeight: 700, color: '#111827' }}>
          {t('journal.overview.why_title')}
        </h3>
        <p style={{ margin: 0, fontSize: 13.5, lineHeight: 1.7, color: '#374151' }}>
          {t('journal.overview.why_body')}
        </p>
      </div>

      {/* ── Benefits ── */}
      <div style={{ marginBottom: 32 }}>
        <SectionTitle>{t('journal.overview.benefits_title')}</SectionTitle>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
          {benefitList.map((b, i) => (
            <div key={i} style={{
              display: 'flex', gap: 10, alignItems: 'flex-start',
              background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10, padding: '12px 14px',
            }}>
              <span style={{
                flexShrink: 0, width: 22, height: 22, borderRadius: '50%',
                background: '#d1fae5', color: '#065f46', fontWeight: 800, fontSize: 13,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>✓</span>
              <span style={{ fontSize: 12.5, lineHeight: 1.55, color: '#374151' }}>{b}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Journaling pipeline ── */}
      <div style={{ marginBottom: 24 }}>
        <SectionTitle>{t('journal.overview.pipeline_title')}</SectionTitle>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexWrap: 'wrap', gap: 0 }}>
          {STAGES.map((st, i) => (
            <React.Fragment key={i}>
              <Box label={st.label} sub={st.sub} color={st.color} bg={st.bg} border={st.border} width={150} />
              {i < STAGES.length - 1 && <Arrow dir="right" length={30} />}
            </React.Fragment>
          ))}
        </div>

        {/* Continuous-improvement loop note */}
        <div style={{ display: 'flex', justifyContent: 'center', marginTop: 16 }}>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 8,
            background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 999,
            padding: '6px 16px', fontSize: 12, fontWeight: 600, color: '#1e40af',
          }}>
            <span style={{ fontSize: 15 }}>↻</span>
            {t('journal.overview.loop_note')}
          </div>
        </div>
      </div>

      {/* ── Legend ── */}
      <div style={{ marginTop: 8, paddingTop: 16, borderTop: '1px solid #e5e7eb', display: 'flex', gap: 20, flexWrap: 'wrap', fontSize: 11, color: '#6b7280' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <div style={{ width: 12, height: 12, borderRadius: 3, background: '#dbeafe', border: '1px solid #93c5fd' }} />
          {t('journal.overview.legend_plan')}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <div style={{ width: 12, height: 12, borderRadius: 3, background: '#d1fae5', border: '1px solid #6ee7b7' }} />
          {t('journal.overview.legend_record')}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <div style={{ width: 12, height: 12, borderRadius: 3, background: '#fef9c3', border: '1px solid #fde68a' }} />
          {t('journal.overview.legend_reflect')}
        </div>
      </div>

    </div>
  );
};

export default JournalOverview;
