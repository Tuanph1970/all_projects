// F-101 — PatternPanel: chart-pattern overlay for Decision Console
import React, { useState } from 'react';
import { ChevronDown, ChevronRight, TrendingUp, TrendingDown } from 'lucide-react';

// ── PatternCard ──────────────────────────────────────────────────────────────

const PatternCard = ({ pattern }) => {
  const isBullish = pattern.pattern_type === 'bullish';
  const color = isBullish ? '#10b981' : '#ef4444';
  const bg = isBullish ? 'rgba(16,185,129,0.08)' : 'rgba(239,68,68,0.08)';
  const border = isBullish ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)';
  const Icon = isBullish ? TrendingUp : TrendingDown;
  const pct = Math.round((pattern.confidence ?? 0) * 100);

  return (
    <div style={{ background: bg, border: `1px solid ${border}`, borderRadius: 8, padding: '10px 13px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <Icon size={13} color={color} style={{ flexShrink: 0 }} />
        <span style={{ fontWeight: 700, fontSize: 13, color: '#f9fafb', flex: 1 }}>
          {pattern.pattern_name}
        </span>
        <span style={{ fontSize: 11, fontWeight: 600, color, background: `${color}22`, padding: '2px 7px', borderRadius: 4 }}>
          {isBullish ? 'Bullish' : 'Bearish'}
        </span>
      </div>

      {/* Confidence bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <span style={{ fontSize: 10, color: '#9ca3af', width: 68, flexShrink: 0 }}>Confidence</span>
        <div style={{ flex: 1, height: 5, background: '#374151', borderRadius: 3, overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: 3 }} />
        </div>
        <span style={{ fontSize: 11, color, fontWeight: 600, width: 32, textAlign: 'right' }}>{pct}%</span>
      </div>

      {/* Price levels */}
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        {pattern.neckline != null && (
          <div style={styles.priceCell}>
            <span style={styles.priceLabel}>Neckline / Breakout</span>
            <span style={{ ...styles.priceValue, color: '#f59e0b' }}>
              {Number(pattern.neckline).toLocaleString('en', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
        )}
        {pattern.measured_move_target != null && (
          <div style={styles.priceCell}>
            <span style={styles.priceLabel}>Measured Move</span>
            <span style={{ ...styles.priceValue, color }}>
              {Number(pattern.measured_move_target).toLocaleString('en', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

// ── PatternPanel ─────────────────────────────────────────────────────────────

const PatternPanel = ({ patterns, loading, error }) => {
  const [open, setOpen] = useState(true);

  const found = patterns ? patterns.filter(p => p.found) : [];

  if (loading) {
    return (
      <div style={styles.shell}>
        <div style={styles.header}>
          <span style={styles.title}>Chart Patterns</span>
          <span style={{ fontSize: 11, color: '#6b7280' }}>scanning…</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={styles.shell}>
        <div style={styles.header}>
          <span style={styles.title}>Chart Patterns</span>
          <span style={{ fontSize: 11, color: '#6b7280' }}>unavailable</span>
        </div>
      </div>
    );
  }

  if (!patterns) return null;

  return (
    <div style={styles.shell}>
      <button onClick={() => setOpen(o => !o)} style={styles.toggleBtn}>
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        <span style={styles.title}>Chart Patterns</span>
        {found.length > 0 ? (
          <span style={styles.badge}>{found.length} detected</span>
        ) : (
          <span style={{ fontSize: 11, color: '#6b7280', marginLeft: 6 }}>none detected</span>
        )}
      </button>

      {open && found.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 10 }}>
          {found.map((p, i) => <PatternCard key={i} pattern={p} />)}
        </div>
      )}

      {open && found.length === 0 && (
        <div style={{ color: '#6b7280', fontSize: 12, marginTop: 8, paddingLeft: 4 }}>
          No chart patterns detected in the lookback window.
        </div>
      )}
    </div>
  );
};

const styles = {
  shell: {
    background: '#1f2937', borderRadius: 10,
    border: '1px solid #374151', padding: 14,
  },
  header: { display: 'flex', alignItems: 'center', gap: 8 },
  toggleBtn: {
    background: 'none', border: 'none', padding: 0, cursor: 'pointer',
    display: 'flex', alignItems: 'center', gap: 6, width: '100%',
  },
  title: { fontSize: 13, fontWeight: 600, color: '#d1d5db' },
  badge: {
    background: 'rgba(139,92,246,0.2)', color: '#a78bfa',
    fontSize: 11, fontWeight: 600, padding: '1px 8px', borderRadius: 4, marginLeft: 6,
  },
  priceCell: { display: 'flex', flexDirection: 'column', gap: 1 },
  priceLabel: { fontSize: 9, color: '#6b7280', textTransform: 'uppercase', letterSpacing: 0.5 },
  priceValue: { fontSize: 13, fontWeight: 700 },
};

export default PatternPanel;
