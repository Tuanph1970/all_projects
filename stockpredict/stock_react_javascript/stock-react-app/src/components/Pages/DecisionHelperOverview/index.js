// Decision Helper — General View: static workflow flowchart
import React from 'react';
import { useTranslation } from 'react-i18next';

// ── Primitive building blocks ─────────────────────────────────────────────────

const Box = ({ label, sub, color = '#2C5F4A', bg = '#d1fae5', border = '#6ee7b7', width = 180 }) => (
  <div style={{
    width, minHeight: 52, background: bg, border: `2px solid ${border}`,
    borderRadius: 10, padding: '10px 14px', textAlign: 'center',
    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
    boxShadow: '0 2px 6px rgba(0,0,0,0.07)',
  }}>
    <div style={{ fontWeight: 700, fontSize: 13, color, lineHeight: 1.3 }}>{label}</div>
    {sub && <div style={{ fontSize: 10, color, opacity: 0.75, marginTop: 3 }}>{sub}</div>}
  </div>
);

const Diamond = ({ label, color = '#92400e', bg = '#fef9c3', border = '#fde68a' }) => (
  <div style={{ position: 'relative', width: 140, height: 70, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
    <div style={{
      position: 'absolute', width: 120, height: 60,
      background: bg, border: `2px solid ${border}`,
      transform: 'rotate(45deg)', borderRadius: 6,
    }} />
    <div style={{ position: 'relative', fontWeight: 700, fontSize: 12, color, textAlign: 'center', zIndex: 1, padding: '0 18px' }}>
      {label}
    </div>
  </div>
);

const Arrow = ({ dir = 'down', label, length = 32 }) => {
  const isHoriz = dir === 'right' || dir === 'left';
  return (
    <div style={{
      display: 'flex',
      flexDirection: isHoriz ? 'row' : 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 2,
    }}>
      {label && !isHoriz && (
        <span style={{ fontSize: 10, color: '#9ca3af', whiteSpace: 'nowrap' }}>{label}</span>
      )}
      <div style={{
        width: isHoriz ? length : 2,
        height: isHoriz ? 2 : length,
        background: '#d1d5db',
        position: 'relative',
        flexShrink: 0,
      }}>
        {/* arrowhead */}
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

const Card = ({ title, color, bg, border, children, minWidth = 280 }) => (
  <div style={{
    background: '#fff', border: `1px solid ${border || '#e5e7eb'}`,
    borderRadius: 12, padding: '16px 18px', minWidth,
    boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
  }}>
    <div style={{
      fontWeight: 700, fontSize: 13, color: color || '#111827',
      marginBottom: 10, paddingBottom: 8, borderBottom: `2px solid ${border || '#e5e7eb'}`,
    }}>{title}</div>
    {children}
  </div>
);

const Step = ({ n, label, sub, color = '#2563eb' }) => (
  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 8 }}>
    <div style={{
      width: 22, height: 22, borderRadius: '50%', background: color,
      color: '#fff', fontWeight: 700, fontSize: 11, flexShrink: 0,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }}>{n}</div>
    <div>
      <div style={{ fontWeight: 600, fontSize: 12, color: '#111827' }}>{label}</div>
      {sub && <div style={{ fontSize: 11, color: '#6b7280', marginTop: 1 }}>{sub}</div>}
    </div>
  </div>
);

const Badge = ({ label, color, bg }) => (
  <span style={{
    display: 'inline-block', padding: '2px 8px', borderRadius: 5,
    fontSize: 11, fontWeight: 700, color, background: bg,
    marginRight: 4, marginBottom: 4,
  }}>{label}</span>
);

// ── Main page ─────────────────────────────────────────────────────────────────

const DecisionHelperOverview = () => {
  const { t } = useTranslation();

  return (
    <div style={{ padding: '24px 28px', maxWidth: 1100, margin: '0 auto', color: '#111827' }}>

      {/* ── Page header ── */}
      <div style={{ marginBottom: 28, borderBottom: '1px solid #e5e7eb', paddingBottom: 16 }}>
        <h2 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>
          {t('decision_helper.overview.title')}
        </h2>
        <p style={{ margin: '6px 0 0', color: '#6b7280', fontSize: 13 }}>
          {t('decision_helper.overview.subtitle')}
        </p>
      </div>

      {/* ══════════════════════════════════════════════════════════════════
          SECTION 1 — Decision Pipeline flowchart
      ══════════════════════════════════════════════════════════════════ */}
      <div style={{ marginBottom: 32 }}>
        <SectionTitle>{t('decision_helper.overview.section_pipeline')}</SectionTitle>

        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 0 }}>

          {/* START */}
          <Box label={t('decision_helper.overview.flow_start')} color="#1e40af" bg="#dbeafe" border="#93c5fd" width={160} />
          <Arrow dir="down" length={28} />

          {/* Stage 1: Regime */}
          <Box
            label={t('decision_helper.overview.flow_regime')}
            sub={t('decision_helper.overview.flow_regime_sub')}
            color="#065f46" bg="#d1fae5" border="#6ee7b7" width={260}
          />
          <Arrow dir="down" length={28} />

          {/* Stage 2: Signal */}
          <Box
            label={t('decision_helper.overview.flow_signal')}
            sub={t('decision_helper.overview.flow_signal_sub')}
            color="#1e40af" bg="#dbeafe" border="#93c5fd" width={260}
          />
          <Arrow dir="down" length={28} />

          {/* Stage 3: Discipline check diamond */}
          <Diamond
            label={t('decision_helper.overview.flow_discipline_check')}
            color="#92400e" bg="#fef9c3" border="#fde68a"
          />

          {/* BLOCK branch */}
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 0, position: 'relative', width: 480, justifyContent: 'center' }}>
            {/* Left branch — BLOCK */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 200 }}>
              <Arrow dir="down" label={t('decision_helper.overview.flow_block_label')} length={24} />
              <Box label={t('decision_helper.overview.flow_block')} sub={t('decision_helper.overview.flow_block_sub')} color="#991b1b" bg="#fee2e2" border="#fca5a5" width={160} />
            </div>
            {/* Right branch — PASS */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 200 }}>
              <Arrow dir="down" label={t('decision_helper.overview.flow_pass_label')} length={24} />
              {/* Stage 4: Sizing */}
              <Box
                label={t('decision_helper.overview.flow_sizing')}
                sub={t('decision_helper.overview.flow_sizing_sub')}
                color="#5b21b6" bg="#ede9fe" border="#c4b5fd" width={200}
              />
              <Arrow dir="down" length={24} />
              {/* Stage 5: Recommendation */}
              <Box
                label={t('decision_helper.overview.flow_recommendation')}
                sub={t('decision_helper.overview.flow_recommendation_sub')}
                color="#065f46" bg="#d1fae5" border="#34d399" width={200}
              />
              <Arrow dir="down" length={24} />
              {/* Actions */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, justifyContent: 'center', maxWidth: 220 }}>
                <Badge label="BUY"        color="#065f46" bg="#d1fae5" />
                <Badge label="SELL SHORT" color="#92400e" bg="#fef3c7" />
                <Badge label="SELL"       color="#991b1b" bg="#fee2e2" />
                <Badge label="HOLD"       color="#374151" bg="#f3f4f6" />
                <Badge label="WAIT"       color="#6b7280" bg="#f9fafb" />
                <Badge label="REVERSE"    color="#5b21b6" bg="#ede9fe" />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════════════
          SECTION 2 — Recommended daily workflow
      ══════════════════════════════════════════════════════════════════ */}
      <div style={{ marginBottom: 32 }}>
        <SectionTitle>{t('decision_helper.overview.section_workflow')}</SectionTitle>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexWrap: 'wrap', gap: 0 }}>

          <Box label={t('decision_helper.overview.wf_discipline')} sub="/discipline" color="#7c3aed" bg="#ede9fe" border="#c4b5fd" width={150} />
          <Arrow dir="right" length={32} label={t('decision_helper.overview.wf_no_blocks')} />

          <Box label={t('decision_helper.overview.wf_heatmap')} sub="/watchlist-heatmap" color="#065f46" bg="#d1fae5" border="#6ee7b7" width={150} />
          <Arrow dir="right" length={32} label={t('decision_helper.overview.wf_spot_signal')} />

          <Box label={t('decision_helper.overview.wf_console')} sub="/decision-console" color="#1e40af" bg="#dbeafe" border="#93c5fd" width={150} />
          <Arrow dir="right" length={32} label={t('decision_helper.overview.wf_criteria_met')} />

          <Box label={t('decision_helper.overview.wf_save_plan')} sub={t('decision_helper.overview.wf_save_plan_sub')} color="#065f46" bg="#d1fae5" border="#34d399" width={150} />
          <Arrow dir="right" length={32} />

          <Box label={t('decision_helper.overview.wf_board')} sub="/decision-board" color="#374151" bg="#f9fafb" border="#d1d5db" width={150} />

        </div>

        {/* Step labels */}
        <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 14, flexWrap: 'wrap' }}>
          {[
            { n: 1, label: t('decision_helper.overview.wf_step1') },
            { n: 2, label: t('decision_helper.overview.wf_step2') },
            { n: 3, label: t('decision_helper.overview.wf_step3') },
            { n: 4, label: t('decision_helper.overview.wf_step4') },
            { n: 5, label: t('decision_helper.overview.wf_step5') },
          ].map(({ n, label }) => (
            <div key={n} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: '#6b7280', width: 150, justifyContent: 'center' }}>
              <div style={{ width: 18, height: 18, borderRadius: '50%', background: '#e5e7eb', color: '#374151', fontWeight: 700, fontSize: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>{n}</div>
              {label}
            </div>
          ))}
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════════════
          SECTION 3 — Sub-menu reference cards
      ══════════════════════════════════════════════════════════════════ */}
      <div>
        <SectionTitle>{t('decision_helper.overview.section_screens')}</SectionTitle>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 16 }}>

          <Card title={t('decision_helper.overview.screen_console_title')} color="#1e40af" border="#bfdbfe">
            <Step n={1} label={t('decision_helper.overview.screen_console_s1')} color="#1e40af" />
            <Step n={2} label={t('decision_helper.overview.screen_console_s2')} color="#1e40af" />
            <Step n={3} label={t('decision_helper.overview.screen_console_s3')} color="#1e40af" />
            <Step n={4} label={t('decision_helper.overview.screen_console_s4')} color="#1e40af" />
          </Card>

          <Card title={t('decision_helper.overview.screen_board_title')} color="#065f46" border="#6ee7b7">
            <Step n={1} label={t('decision_helper.overview.screen_board_s1')} color="#065f46" />
            <Step n={2} label={t('decision_helper.overview.screen_board_s2')} color="#065f46" />
            <Step n={3} label={t('decision_helper.overview.screen_board_s3')} color="#065f46" />
          </Card>

          <Card title={t('decision_helper.overview.screen_heatmap_title')} color="#92400e" border="#fde68a">
            <Step n={1} label={t('decision_helper.overview.screen_heatmap_s1')} color="#b45309" />
            <Step n={2} label={t('decision_helper.overview.screen_heatmap_s2')} color="#b45309" />
            <Step n={3} label={t('decision_helper.overview.screen_heatmap_s3')} color="#b45309" />
          </Card>

          <Card title={t('decision_helper.overview.screen_discipline_title')} color="#7c3aed" border="#c4b5fd">
            <Step n={1} label={t('decision_helper.overview.screen_discipline_s1')} color="#7c3aed" />
            <Step n={2} label={t('decision_helper.overview.screen_discipline_s2')} color="#7c3aed" />
            <Step n={3} label={t('decision_helper.overview.screen_discipline_s3')} color="#7c3aed" />
          </Card>

        </div>
      </div>

      {/* ── Legend ── */}
      <div style={{ marginTop: 28, paddingTop: 16, borderTop: '1px solid #e5e7eb', display: 'flex', gap: 20, flexWrap: 'wrap', fontSize: 11, color: '#6b7280' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <div style={{ width: 12, height: 12, borderRadius: 3, background: '#d1fae5', border: '1px solid #6ee7b7' }} />
          {t('decision_helper.overview.legend_go')}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <div style={{ width: 12, height: 12, borderRadius: 3, background: '#fee2e2', border: '1px solid #fca5a5' }} />
          {t('decision_helper.overview.legend_block')}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <div style={{ width: 12, height: 12, borderRadius: 3, background: '#fef9c3', border: '1px solid #fde68a' }} />
          {t('decision_helper.overview.legend_check')}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <div style={{ width: 12, height: 12, borderRadius: 3, background: '#ede9fe', border: '1px solid #c4b5fd' }} />
          {t('decision_helper.overview.legend_sizing')}
        </div>
      </div>

    </div>
  );
};

export default DecisionHelperOverview;
