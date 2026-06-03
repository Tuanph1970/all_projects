// Combined, interactive decomposition chart (Plotly).
// One chart area for a decomposition result:
//   • Left Y axis  — Original series + low-frequency component (Approximation / Residue)
//   • Right Y axis — oscillatory components (Detail D1..Dj / IMF1..n / VMD modes)
// Features: checkbox-dropdown series toggles (all on by default), major + minor
// gridlines, mouse/box zoom, zoom in/out buttons, pan, autoscale (Plotly modebar).
import React, { useMemo, useState } from 'react';
import createPlotlyComponent from 'react-plotly.js/factory';
import Plotly from 'plotly.js-dist-min';
import { ChevronDown } from 'lucide-react';

const Plot = createPlotlyComponent(Plotly);

const ORIGINAL = '#111827';
const APPROX = '#3b82f6';
const RESIDUE = '#9ca3af';
const DETAILS = ['#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#84cc16', '#fb923c'];
const GRID_MAJOR = '#d1d5db';
const GRID_MINOR = '#eef2f7';
const FONT = "'Inter', -apple-system, BlinkMacSystemFont, sans-serif";

// Build the ordered series list (key/name/values/axis/color) from any method's result.
function buildSeriesDefs(method, d, series, t) {
  const defs = [{
    key: 'orig', axis: 'left', color: ORIGINAL,
    name: t('chart_decomp.decomp.original_label'), y: series,
  }];

  if (method === 'modwt') {
    defs.push({
      key: 'approx', axis: 'left', color: APPROX,
      name: t('chart_decomp.decomp.approx_label', { j: d.level }), y: d.approximation,
    });
    (d.details || []).forEach((det, i) => defs.push({
      key: `d${i + 1}`, axis: 'right', color: DETAILS[i % DETAILS.length],
      name: t('chart_decomp.decomp.detail_label', { j: i + 1 }), y: det,
    }));
  } else if (method === 'vmd') {
    (d.modes || []).forEach((m, i) => defs.push({
      key: `m${i + 1}`, axis: 'right', color: DETAILS[i % DETAILS.length],
      name: t('chart_decomp.decomp.mode_label', { j: i + 1 }), y: m,
    }));
  } else { // emd / eemd
    const imfs = d.imfs || [];
    imfs.slice(0, -1).forEach((imf, i) => defs.push({
      key: `imf${i + 1}`, axis: 'right', color: DETAILS[i % DETAILS.length],
      name: t('chart_decomp.decomp.imf_label', { j: i + 1 }), y: imf,
    }));
    if (imfs.length) defs.push({
      key: 'res', axis: 'left', color: RESIDUE,
      name: t('chart_decomp.decomp.residue_label'), y: imfs[imfs.length - 1],
    });
  }
  return defs;
}

export default function DecompCombinedChart({ method, d, series, t }) {
  const defs = useMemo(() => buildSeriesDefs(method, d, series, t), [method, d, series, t]);

  // Visibility: all series checked by default.
  const [visible, setVisible] = useState(() =>
    Object.fromEntries(defs.map(def => [def.key, true])));
  const [menuOpen, setMenuOpen] = useState(false);

  // Reset visibility when the underlying series set changes (new run / method).
  const sig = defs.map(def => def.key).join(',');
  const [lastSig, setLastSig] = useState(sig);
  if (sig !== lastSig) {
    setLastSig(sig);
    setVisible(Object.fromEntries(defs.map(def => [def.key, true])));
  }

  const x = useMemo(() => (series ? series.map((_, i) => i) : []), [series]);

  const traces = defs.map(def => ({
    x,
    y: def.y,
    type: 'scatter',            // SVG renderer so the range-slider preview renders
    mode: 'lines',
    name: def.name,
    line: { color: def.color, width: def.key === 'orig' ? 2 : 1.4 },
    yaxis: def.axis === 'right' ? 'y2' : 'y',
    visible: visible[def.key] ? true : 'legendonly',
    hovertemplate: `${def.name}: %{y:.4f}<extra></extra>`,
  }));

  const axisCommon = {
    showgrid: true, gridcolor: GRID_MAJOR, gridwidth: 1,
    zeroline: false, ticks: 'outside', tickfont: { size: 10, family: FONT },
    minor: { showgrid: true, gridcolor: GRID_MINOR, ticklen: 3, ticks: 'outside' },
  };

  const layout = {
    autosize: true,
    height: 520,
    margin: { l: 56, r: 56, t: 10, b: 40 },
    dragmode: 'pan',
    hovermode: 'x unified',
    font: { family: FONT },
    xaxis: {
      ...axisCommon,
      title: { text: t('chart_decomp.combined.x_title'), font: { size: 11 } },
      nticks: 12,
      // Overview strip with a draggable window for scrolling/zooming the range.
      rangeslider: { visible: true, thickness: 0.1, bgcolor: '#f9fafb', bordercolor: '#e5e7eb', borderwidth: 1 },
    },
    yaxis: {
      ...axisCommon,
      title: { text: t('chart_decomp.combined.axis_left_title'), font: { size: 11 } },
    },
    yaxis2: {
      title: { text: t('chart_decomp.combined.axis_right_title'), font: { size: 11 } },
      overlaying: 'y', side: 'right', zeroline: false,
      showgrid: false, tickfont: { size: 10, family: FONT },
    },
    legend: { orientation: 'h', y: -0.18, font: { size: 11, family: FONT } },
    plot_bgcolor: '#ffffff', paper_bgcolor: '#ffffff',
  };

  const config = {
    scrollZoom: true,           // wheel zoom
    displaylogo: false,
    responsive: true,
    modeBarButtonsToRemove: ['lasso2d', 'select2d'],
    // pan / box-zoom / zoomIn / zoomOut / autoscale / reset are kept by default
    toImageButtonOptions: { filename: 'decomposition' },
  };

  const toggle = (key) => setVisible(v => ({ ...v, [key]: !v[key] }));
  const shown = Object.values(visible).filter(Boolean).length;

  return (
    <div>
      {/* Series checkbox dropdown */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          {t('chart_decomp.combined.series_label')}
        </span>
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => setMenuOpen(o => !o)}
            style={{
              height: 32, border: '1px solid #e5e7eb', borderRadius: 8, background: '#fff',
              padding: '0 10px', fontSize: 12, fontFamily: FONT, cursor: 'pointer',
              display: 'inline-flex', alignItems: 'center', gap: 6, minWidth: 150, justifyContent: 'space-between',
            }}
          >
            {t('chart_decomp.combined.series_count', { n: shown, total: defs.length })}
            <ChevronDown size={14} />
          </button>
          {menuOpen && (
            <div style={{
              position: 'absolute', top: 36, left: 0, zIndex: 30, background: '#fff',
              border: '1px solid #e5e7eb', borderRadius: 8, padding: 8,
              boxShadow: '0 6px 18px rgba(0,0,0,0.12)', minWidth: 220, maxHeight: 300, overflowY: 'auto',
            }}>
              {defs.map(def => (
                <label key={def.key} style={{
                  display: 'flex', alignItems: 'center', gap: 8, padding: '5px 6px',
                  fontSize: 12, cursor: 'pointer',
                }}>
                  <input type="checkbox" checked={!!visible[def.key]} onChange={() => toggle(def.key)} />
                  <span style={{ width: 12, height: 12, borderRadius: 3, background: def.color, display: 'inline-block' }} />
                  <span style={{ color: '#374151', flex: 1 }}>{def.name}</span>
                  <span style={{
                    fontSize: 10, fontWeight: 700, color: '#6b7280', background: '#f3f4f6',
                    borderRadius: 99, padding: '1px 7px',
                  }}>
                    {def.axis === 'left' ? t('chart_decomp.combined.axis_left') : t('chart_decomp.combined.axis_right')}
                  </span>
                </label>
              ))}
            </div>
          )}
        </div>
        <span style={{ fontSize: 11, color: '#9ca3af' }}>{t('chart_decomp.combined.interact_hint')}</span>
      </div>

      <Plot
        data={traces}
        layout={layout}
        config={config}
        style={{ width: '100%' }}
        useResizeHandler
      />
    </div>
  );
}
