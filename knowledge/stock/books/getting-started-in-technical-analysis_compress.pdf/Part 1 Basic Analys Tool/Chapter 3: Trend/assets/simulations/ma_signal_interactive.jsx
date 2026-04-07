/**
 * ma_signal_interactive.jsx
 * 
 * Interactive tool for exploring Schwager's MA direction-change signal method.
 * - Switch between Trending / Sideways / Mixed market regimes
 * - Adjust MA period (N) and threshold (T) with sliders
 * - Live signal generation with win/loss/P&L statistics
 * - Demonstrates that no parameter combination works in both regimes
 * 
 * Usage: Render as a React/JSX artifact in Claude.ai
 */

import { useState, useMemo, useCallback } from "react";

function generateData(type, len = 140) {
  const d = [];
  let p = 100;
  for (let i = 0; i < len; i++) {
    const r = (Math.sin((i + 42) * 137.508) * 10000) % 1;
    const noise = (r - 0.5) * 2;
    if (type === "trend") {
      if (i < 40) p += 0.05 + noise * 0.6;
      else if (i < 80) p -= 0.3 + noise * 0.5;
      else if (i < 90) p += 0.1 + noise * 0.6;
      else p -= 0.35 + noise * 0.5;
    } else if (type === "sideways") {
      p += Math.sin(i / 7) * 0.6 + noise * 0.8;
      p = Math.max(p, 94);
      p = Math.min(p, 106);
    } else {
      if (i < 50) p -= 0.25 + noise * 0.5;
      else if (i < 90) p += Math.sin(i / 6) * 0.5 + noise * 0.7;
      else p += 0.2 + noise * 0.5;
    }
    d.push(p);
  }
  return d;
}

function computeSMA(data, n) {
  return data.map((_, i) => {
    if (i < n - 1) return null;
    let s = 0;
    for (let j = i - n + 1; j <= i; j++) s += data[j];
    return s / n;
  });
}

function computeSignals(ma, threshold) {
  const sigs = [];
  let maHigh = null, maLow = null, state = 0;
  for (let i = 0; i < ma.length; i++) {
    if (ma[i] === null) continue;
    if (maHigh === null) { maHigh = ma[i]; maLow = ma[i]; continue; }
    if (ma[i] > maHigh) maHigh = ma[i];
    if (ma[i] < maLow) maLow = ma[i];
    if (state <= 0 && ma[i] - maLow >= threshold) {
      sigs.push({ bar: i, type: "buy" });
      state = 1; maHigh = ma[i];
    } else if (state >= 0 && maHigh - ma[i] >= threshold) {
      sigs.push({ bar: i, type: "sell" });
      state = -1; maLow = ma[i];
    }
  }
  return sigs;
}

export default function MASignalInteractive() {
  const [regime, setRegime] = useState("trend");
  const [maPeriod, setMaPeriod] = useState(20);
  const [threshold, setThreshold] = useState(1.0);

  const prices = useMemo(() => generateData(regime), [regime]);
  const ma = useMemo(() => computeSMA(prices, maPeriod), [prices, maPeriod]);
  const signals = useMemo(() => computeSignals(ma, threshold), [ma, threshold]);

  // Stats
  let wins = 0, losses = 0, totalPL = 0;
  for (let si = 1; si < signals.length; si++) {
    const prev = signals[si - 1];
    const curr = signals[si];
    const pl = prev.type === "buy"
      ? prices[curr.bar] - prices[prev.bar]
      : prices[prev.bar] - prices[curr.bar];
    totalPL += pl;
    if (pl > 0) wins++; else losses++;
  }
  const winRate = wins + losses > 0 ? Math.round((wins / (wins + losses)) * 100) : 0;

  // Chart
  const W = 640, H = 240, pd = { t: 24, r: 15, b: 22, l: 42 };
  const mnP = Math.min(...prices) - 3, mxP = Math.max(...prices) + 3;
  const xS = (i) => pd.l + (i / (prices.length - 1)) * (W - pd.l - pd.r);
  const yS = (v) => pd.t + ((mxP - v) / (mxP - mnP)) * (H - pd.t - pd.b);

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", padding: "1rem" }}>
      {/* Regime buttons */}
      <div style={{ display: "flex", gap: 8, marginBottom: "1rem" }}>
        {[["trend", "Trending"], ["sideways", "Sideways"], ["mixed", "Mixed"]].map(([key, label]) => (
          <button key={key} onClick={() => setRegime(key)}
            style={{
              padding: "6px 14px", fontSize: 13, cursor: "pointer",
              background: regime === key ? "#e6f1fb" : "transparent",
              border: `1px solid ${regime === key ? "#378ADD" : "#ccc"}`,
              borderRadius: 6, color: regime === key ? "#185FA5" : "#666",
              fontWeight: regime === key ? 500 : 400,
            }}>{label}</button>
        ))}
      </div>

      {/* Sliders */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8, fontSize: 14, color: "#666" }}>
        <label>MA period (N)</label>
        <input type="range" min={5} max={60} value={maPeriod} step={1}
          onChange={(e) => setMaPeriod(parseInt(e.target.value))}
          style={{ flex: 1 }} />
        <span style={{ fontWeight: 500, minWidth: 30, textAlign: "right", color: "#333" }}>{maPeriod}</span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: "1rem", fontSize: 14, color: "#666" }}>
        <label>Threshold (T)</label>
        <input type="range" min={0} max={4} value={threshold} step={0.1}
          onChange={(e) => setThreshold(parseFloat(e.target.value))}
          style={{ flex: 1 }} />
        <span style={{ fontWeight: 500, minWidth: 30, textAlign: "right", color: "#333" }}>{threshold.toFixed(1)}</span>
      </div>

      {/* Chart */}
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", maxWidth: 660 }}>
        <rect x={pd.l} y={pd.t} width={W - pd.l - pd.r} height={H - pd.t - pd.b}
          fill="#f8f8f8" rx="2" />
        {/* Price */}
        <polyline
          points={prices.map((p, i) => `${xS(i)},${yS(p)}`).join(" ")}
          fill="none" stroke="#999" strokeWidth="0.8" opacity="0.6" />
        {/* MA */}
        <polyline
          points={ma.filter(v => v !== null).map((v, i) => {
            const idx = prices.length - ma.filter(x => x !== null).length + i;
            return `${xS(maPeriod - 1 + i)},${yS(v)}`;
          }).join(" ")}
          fill="none" stroke="#534AB7" strokeWidth="2" />
        {/* Signals */}
        {signals.map((s, i) => {
          const py = prices[s.bar];
          const col = s.type === "buy" ? "#1D9E75" : "#A32D2D";
          const yOff = s.type === "buy" ? 12 : -12;
          return (
            <g key={i}>
              {s.type === "buy" ? (
                <path d={`M${xS(s.bar) - 5},${yS(py) + 16} L${xS(s.bar)},${yS(py) + 8} L${xS(s.bar) + 5},${yS(py) + 16}`}
                  fill={col} opacity="0.8" />
              ) : (
                <path d={`M${xS(s.bar) - 5},${yS(py) - 16} L${xS(s.bar)},${yS(py) - 8} L${xS(s.bar) + 5},${yS(py) - 16}`}
                  fill={col} opacity="0.8" />
              )}
            </g>
          );
        })}
        {/* Trade lines */}
        {signals.slice(1).map((s, i) => {
          const prev = signals[i];
          const pl = prev.type === "buy"
            ? prices[s.bar] - prices[prev.bar]
            : prices[prev.bar] - prices[s.bar];
          const col = pl > 0 ? "#1D9E75" : "#A32D2D";
          return (
            <line key={i} x1={xS(prev.bar)} y1={yS(prices[prev.bar])}
              x2={xS(s.bar)} y2={yS(prices[s.bar])}
              stroke={col} strokeWidth="0.5" strokeDasharray="3,3" opacity="0.4" />
          );
        })}
      </svg>

      {/* Stats */}
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", margin: "0.75rem 0" }}>
        {[
          { label: "Signals", val: signals.length, col: "#333" },
          { label: "Wins", val: wins, col: "#1D9E75" },
          { label: "Losses", val: losses, col: "#A32D2D" },
          { label: "Net P/L", val: `${totalPL >= 0 ? "+" : ""}${totalPL.toFixed(1)}`, col: totalPL >= 0 ? "#1D9E75" : "#A32D2D" },
          { label: "Win rate", val: `${winRate}%`, col: "#333" },
        ].map((s, i) => (
          <div key={i} style={{ background: "#f5f5f5", borderRadius: 6, padding: "6px 12px", minWidth: 70 }}>
            <div style={{ fontSize: 11, color: "#888" }}>{s.label}</div>
            <div style={{ fontSize: 18, fontWeight: 500, color: s.col }}>{s.val}</div>
          </div>
        ))}
      </div>

      {/* Explanation */}
      <div style={{ fontSize: 13, color: "#888", lineHeight: 1.7 }}>
        {regime === "trend" && signals.length <= 4 && "Few signals in a trending market — the MA captures big moves with minimal noise. This is the Figure 3.20 scenario."}
        {regime === "trend" && signals.length > 4 && "Many signals suggest the threshold is too small or the MA too short. Try increasing either parameter."}
        {regime === "sideways" && losses > wins + 1 && "Classic Figure 3.21 disaster: the MA oscillates without direction, each reversal triggers a signal, every trade is a small loss."}
        {regime === "sideways" && losses <= wins + 1 && signals.length <= 2 && "High threshold or long MA is suppressing most signals. Good for avoiding losses, but you'd also miss any real breakout."}
        {regime === "mixed" && "Mixed regime: the same parameters work well in the trending phase and poorly in the sideways phase. The MA cannot distinguish between regimes."}
      </div>
    </div>
  );
}
