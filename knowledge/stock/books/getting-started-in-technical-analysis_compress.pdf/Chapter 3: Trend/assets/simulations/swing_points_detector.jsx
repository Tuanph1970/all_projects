import { useState, useMemo, useCallback } from "react";

// --- Generate synthetic price data resembling a downtrend (like Dec 1992 Coffee) ---
function generateCoffeeLikeData() {
  const data = [];
  let price = 95;
  const days = 250;
  const trend = -0.15;
  for (let i = 0; i < days; i++) {
    const date = new Date(1991, 9, 1);
    date.setDate(date.getDate() + i);
    const noise = (Math.random() - 0.48) * 3.5;
    const cyclical = Math.sin(i / 18) * 4;
    price = price + trend + noise + cyclical * 0.15;
    price = Math.max(price, 42);
    const range = 1 + Math.random() * 2.5;
    const high = price + range / 2 + Math.random();
    const low = price - range / 2 - Math.random();
    data.push({
      idx: i,
      date: date.toISOString().slice(0, 10),
      open: price + (Math.random() - 0.5) * range * 0.4,
      high,
      low,
      close: price,
    });
  }
  return data;
}

// --- Core algorithm: detect Relative Highs and Lows ---
function detectSwingPoints(data, N) {
  const relativeHighs = [];
  const relativeLows = [];

  for (let i = N; i < data.length - N; i++) {
    // Relative High: high[i] > all highs in [i-N, i+N] excluding i
    let isRH = true;
    for (let j = i - N; j <= i + N; j++) {
      if (j === i) continue;
      if (data[j].high >= data[i].high) {
        isRH = false;
        break;
      }
    }
    if (isRH) relativeHighs.push(i);

    // Relative Low: low[i] < all lows in [i-N, i+N] excluding i
    let isRL = true;
    for (let j = i - N; j <= i + N; j++) {
      if (j === i) continue;
      if (data[j].low <= data[i].low) {
        isRL = false;
        break;
      }
    }
    if (isRL) relativeLows.push(i);
  }
  return { relativeHighs, relativeLows };
}

// --- Classify trend based on RH/RL sequence ---
function classifyTrend(data, relativeHighs, relativeLows) {
  const allPoints = [
    ...relativeHighs.map((i) => ({ idx: i, type: "RH", price: data[i].high })),
    ...relativeLows.map((i) => ({ idx: i, type: "RL", price: data[i].low })),
  ].sort((a, b) => a.idx - b.idx);

  const segments = [];
  for (let i = 1; i < allPoints.length; i++) {
    const prev = allPoints[i - 1];
    const curr = allPoints[i];
    let trend = "—";
    if (prev.type === "RH" && curr.type === "RH") {
      trend = curr.price > prev.price ? "Higher High ↑" : "Lower High ↓";
    } else if (prev.type === "RL" && curr.type === "RL") {
      trend = curr.price > prev.price ? "Higher Low ↑" : "Lower Low ↓";
    } else {
      trend = "swing";
    }
    segments.push({ from: prev, to: curr, trend });
  }
  return { allPoints, segments };
}

// --- Chart component ---
function PriceChart({ data, relativeHighs, relativeLows, N }) {
  const W = 900;
  const H = 420;
  const pad = { top: 30, right: 30, bottom: 40, left: 55 };
  const cw = W - pad.left - pad.right;
  const ch = H - pad.top - pad.bottom;

  const allHighs = data.map((d) => d.high);
  const allLows = data.map((d) => d.low);
  const minP = Math.floor(Math.min(...allLows) - 2);
  const maxP = Math.ceil(Math.max(...allHighs) + 2);

  const xScale = (i) => pad.left + (i / (data.length - 1)) * cw;
  const yScale = (p) => pad.top + ((maxP - p) / (maxP - minP)) * ch;

  const barW = Math.max(1, cw / data.length - 0.5);

  // Y-axis ticks
  const yTicks = [];
  const step = Math.ceil((maxP - minP) / 8);
  for (let p = Math.ceil(minP / step) * step; p <= maxP; p += step) {
    yTicks.push(p);
  }

  // X-axis ticks (every ~40 bars)
  const xTicks = [];
  const xStep = Math.max(1, Math.floor(data.length / 8));
  for (let i = 0; i < data.length; i += xStep) {
    xTicks.push(i);
  }

  const rhSet = new Set(relativeHighs);
  const rlSet = new Set(relativeLows);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", maxWidth: 900 }}>
      {/* Background */}
      <rect x={pad.left} y={pad.top} width={cw} height={ch} fill="var(--bg-chart)" rx="2" />

      {/* Grid lines */}
      {yTicks.map((p) => (
        <line key={p} x1={pad.left} x2={W - pad.right} y1={yScale(p)} y2={yScale(p)} stroke="var(--grid)" strokeWidth="0.5" />
      ))}

      {/* Candlesticks */}
      {data.map((d, i) => {
        const x = xScale(i);
        const isUp = d.close >= d.open;
        return (
          <g key={i}>
            {/* Wick */}
            <line x1={x} x2={x} y1={yScale(d.high)} y2={yScale(d.low)} stroke="var(--wick)" strokeWidth="0.7" />
            {/* Body */}
            <rect
              x={x - barW / 2}
              y={yScale(Math.max(d.open, d.close))}
              width={barW}
              height={Math.max(1, Math.abs(yScale(d.open) - yScale(d.close)))}
              fill={isUp ? "var(--candle-up)" : "var(--candle-down)"}
              rx="0.3"
            />
          </g>
        );
      })}

      {/* RH markers */}
      {relativeHighs.map((i) => (
        <g key={`rh-${i}`}>
          <circle cx={xScale(i)} cy={yScale(data[i].high) - 12} r="4" fill="var(--rh-color)" />
          <text x={xScale(i)} y={yScale(data[i].high) - 20} textAnchor="middle" fontSize="9" fontWeight="700" fill="var(--rh-color)" fontFamily="monospace">
            RH
          </text>
        </g>
      ))}

      {/* RL markers */}
      {relativeLows.map((i) => (
        <g key={`rl-${i}`}>
          <circle cx={xScale(i)} cy={yScale(data[i].low) + 12} r="4" fill="var(--rl-color)" />
          <text x={xScale(i)} y={yScale(data[i].low) + 24} textAnchor="middle" fontSize="9" fontWeight="700" fill="var(--rl-color)" fontFamily="monospace">
            RL
          </text>
        </g>
      ))}

      {/* Connect RHs with dashed line */}
      {relativeHighs.length > 1 && (
        <polyline
          points={relativeHighs.map((i) => `${xScale(i)},${yScale(data[i].high)}`).join(" ")}
          fill="none"
          stroke="var(--rh-color)"
          strokeWidth="1"
          strokeDasharray="4,3"
          opacity="0.5"
        />
      )}

      {/* Connect RLs with dashed line */}
      {relativeLows.length > 1 && (
        <polyline
          points={relativeLows.map((i) => `${xScale(i)},${yScale(data[i].low)}`).join(" ")}
          fill="none"
          stroke="var(--rl-color)"
          strokeWidth="1"
          strokeDasharray="4,3"
          opacity="0.5"
        />
      )}

      {/* Y axis labels */}
      {yTicks.map((p) => (
        <text key={p} x={pad.left - 8} y={yScale(p) + 3} textAnchor="end" fontSize="10" fill="var(--label)" fontFamily="monospace">
          {p}
        </text>
      ))}

      {/* X axis labels */}
      {xTicks.map((i) => (
        <text key={i} x={xScale(i)} y={H - pad.bottom + 18} textAnchor="middle" fontSize="9" fill="var(--label)" fontFamily="monospace">
          {data[i].date.slice(5)}
        </text>
      ))}

      {/* N-bar lag indicator */}
      <text x={W - pad.right} y={pad.top - 8} textAnchor="end" fontSize="10" fill="var(--muted)" fontFamily="monospace">
        ← {N}-bar blind zone on each end (lag)
      </text>

      {/* Blind zone shading */}
      <rect x={pad.left} y={pad.top} width={xScale(N) - pad.left} height={ch} fill="var(--blind)" />
      <rect x={xScale(data.length - 1 - N)} y={pad.top} width={W - pad.right - xScale(data.length - 1 - N)} height={ch} fill="var(--blind)" />
    </svg>
  );
}

// --- Python code display ---
const PYTHON_CODE = `import pandas as pd
import numpy as np

def detect_swing_points(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """
    Detect Relative Highs and Relative Lows using Schwager's definition.

    A Relative High at bar i:
        high[i] > high[j]  for all j in [i-n, i+n], j != i

    A Relative Low at bar i:
        low[i] < low[j]    for all j in [i-n, i+n], j != i

    Parameters
    ----------
    df : DataFrame with columns 'high' and 'low'
    n  : lookback/lookforward window (Schwager suggests 5-15)

    Returns
    -------
    DataFrame with added columns: 'is_rh', 'is_rl'

    Note: First N and last N bars cannot be classified (lag).
    """
    highs = df['high'].values
    lows  = df['low'].values
    length = len(df)

    is_rh = np.zeros(length, dtype=bool)
    is_rl = np.zeros(length, dtype=bool)

    for i in range(n, length - n):
        window = slice(i - n, i + n + 1)  # inclusive both ends

        # Relative High: this bar's high is the max in the window
        if highs[i] == np.max(highs[window]) and \\
           np.sum(highs[window] == highs[i]) == 1:
            is_rh[i] = True

        # Relative Low: this bar's low is the min in the window
        if lows[i] == np.min(lows[window]) and \\
           np.sum(lows[window] == lows[i]) == 1:
            is_rl[i] = True

    result = df.copy()
    result['is_rh'] = is_rh
    result['is_rl'] = is_rl
    return result


def classify_trend(df: pd.DataFrame) -> list[dict]:
    """
    Given a DataFrame with 'is_rh' and 'is_rl' columns,
    extract the RH/RL sequence and classify each step.

    Returns list of dicts:
        {type, idx, price, prev_type, prev_price, classification}

    Classifications:
        - "Higher High"  / "Lower High"  (comparing consecutive RHs)
        - "Higher Low"   / "Lower Low"   (comparing consecutive RLs)
    """
    points = []
    for idx, row in df.iterrows():
        if row['is_rh']:
            points.append({'type': 'RH', 'idx': idx, 'price': row['high']})
        if row['is_rl']:
            points.append({'type': 'RL', 'idx': idx, 'price': row['low']})

    points.sort(key=lambda p: p['idx'])

    last_rh = None
    last_rl = None
    classified = []

    for pt in points:
        classification = None
        if pt['type'] == 'RH':
            if last_rh is not None:
                classification = (
                    "Higher High" if pt['price'] > last_rh['price']
                    else "Lower High"
                )
            last_rh = pt
        else:
            if last_rl is not None:
                classification = (
                    "Higher Low" if pt['price'] > last_rl['price']
                    else "Lower Low"
                )
            last_rl = pt
        classified.append({**pt, 'classification': classification})

    return classified


# ─── Usage Example ───────────────────────────────────────

# import yfinance as yf
# df = yf.download("AAPL", start="2024-01-01", end="2025-01-01")
# df.columns = [c.lower() for c in df.columns]

# Or load from CSV:
# df = pd.read_csv("prices.csv", parse_dates=["date"], index_col="date")

# Detect swing points with N=10
# result = detect_swing_points(df, n=10)
# rh_dates = result[result['is_rh']].index
# rl_dates = result[result['is_rl']].index
# print(f"Found {len(rh_dates)} RH, {len(rl_dates)} RL")

# Classify trend
# trend = classify_trend(result)
# for pt in trend:
#     print(f"{pt['idx']}  {pt['type']}  {pt['price']:.2f}  {pt['classification']}")
`;

// --- Main App ---
export default function SwingPointDetector() {
  const [N, setN] = useState(10);
  const [showCode, setShowCode] = useState(false);

  const data = useMemo(() => generateCoffeeLikeData(), []);
  const { relativeHighs, relativeLows } = useMemo(() => detectSwingPoints(data, N), [data, N]);
  const { allPoints, segments } = useMemo(() => classifyTrend(data, relativeHighs, relativeLows), [data, relativeHighs, relativeLows]);

  return (
    <div style={{
      fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
      background: "var(--bg)",
      color: "var(--text)",
      minHeight: "100vh",
      padding: "24px",
    }}>
      <style>{`
        :root {
          --bg: #0d1117;
          --bg-card: #161b22;
          --bg-chart: #0d1117;
          --text: #c9d1d9;
          --muted: #484f58;
          --label: #8b949e;
          --grid: #21262d;
          --wick: #58606a;
          --candle-up: #3fb950;
          --candle-down: #f85149;
          --rh-color: #f0883e;
          --rl-color: #58a6ff;
          --blind: rgba(13,17,23,0.65);
          --accent: #f0883e;
          --code-bg: #0d1117;
          --border: #30363d;
        }
        @media (prefers-color-scheme: light) {
          :root {
            --bg: #f6f8fa;
            --bg-card: #ffffff;
            --bg-chart: #ffffff;
            --text: #1f2328;
            --muted: #656d76;
            --label: #656d76;
            --grid: #d0d7de;
            --wick: #8b949e;
            --candle-up: #1a7f37;
            --candle-down: #cf222e;
            --rh-color: #bc4c00;
            --rl-color: #0969da;
            --blind: rgba(246,248,250,0.7);
            --accent: #bc4c00;
            --code-bg: #f6f8fa;
            --border: #d0d7de;
          }
        }
      `}</style>

      {/* Header */}
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 22, fontWeight: 800, margin: 0, letterSpacing: "-0.5px" }}>
          Swing Point Detector
        </h1>
        <p style={{ color: "var(--muted)", fontSize: 12, margin: "4px 0 0" }}>
          Schwager's definition — RH/RL with configurable N parameter
        </p>
      </div>

      {/* Controls */}
      <div style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: "16px 20px",
        marginBottom: 16,
        display: "flex",
        alignItems: "center",
        gap: 24,
        flexWrap: "wrap",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <label style={{ fontSize: 13, fontWeight: 600 }}>N =</label>
          <input
            type="range"
            min={2}
            max={25}
            value={N}
            onChange={(e) => setN(parseInt(e.target.value))}
            style={{ width: 160, accentColor: "var(--accent)" }}
          />
          <span style={{
            fontSize: 20,
            fontWeight: 800,
            color: "var(--accent)",
            minWidth: 30,
            textAlign: "center",
          }}>{N}</span>
        </div>
        <div style={{ fontSize: 11, color: "var(--muted)", lineHeight: 1.5 }}>
          <span style={{ color: "var(--rh-color)", fontWeight: 700 }}>● RH × {relativeHighs.length}</span>
          {" "}&nbsp;{" "}
          <span style={{ color: "var(--rl-color)", fontWeight: 700 }}>● RL × {relativeLows.length}</span>
          {" "}&nbsp;{" "}
          <span>| Lag: {N} bars | Schwager recommends: 5–15</span>
        </div>
      </div>

      {/* Chart */}
      <div style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: 16,
        marginBottom: 16,
        overflowX: "auto",
      }}>
        <PriceChart data={data} relativeHighs={relativeHighs} relativeLows={relativeLows} N={N} />
      </div>

      {/* Trend Sequence Table */}
      <div style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: "16px 20px",
        marginBottom: 16,
      }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px" }}>RH / RL Sequence → Trend Classification</h3>
        <div style={{ overflowX: "auto" }}>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {allPoints.map((pt, i) => {
              const prev = i > 0 ? allPoints[i - 1] : null;
              let arrow = null;
              if (prev && prev.type === pt.type) {
                const up = pt.price > prev.price;
                arrow = (
                  <span style={{
                    fontSize: 10,
                    color: up ? "var(--candle-up)" : "var(--candle-down)",
                    fontWeight: 700,
                    margin: "0 2px",
                  }}>
                    {up ? "▲" : "▼"}
                  </span>
                );
              }
              return (
                <div key={i} style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 3,
                  background: pt.type === "RH" ? "rgba(240,136,62,0.1)" : "rgba(88,166,255,0.1)",
                  border: `1px solid ${pt.type === "RH" ? "rgba(240,136,62,0.3)" : "rgba(88,166,255,0.3)"}`,
                  borderRadius: 4,
                  padding: "3px 7px",
                  fontSize: 11,
                }}>
                  {arrow}
                  <span style={{
                    fontWeight: 700,
                    color: pt.type === "RH" ? "var(--rh-color)" : "var(--rl-color)",
                  }}>{pt.type}</span>
                  <span style={{ color: "var(--muted)" }}>{pt.price.toFixed(1)}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Definition Box */}
      <div style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: "16px 20px",
        marginBottom: 16,
        fontSize: 12,
        lineHeight: 1.8,
      }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 8px" }}>Algorithm</h3>
        <div style={{ color: "var(--label)" }}>
          <p style={{ margin: "0 0 8px" }}>
            <span style={{ color: "var(--rh-color)", fontWeight: 700 }}>Relative High</span> at bar <code>i</code>:&nbsp;
            <code>high[i] &gt; high[j]</code> for every <code>j</code> in <code>[i−N, i+N]</code> where <code>j ≠ i</code>
          </p>
          <p style={{ margin: "0 0 8px" }}>
            <span style={{ color: "var(--rl-color)", fontWeight: 700 }}>Relative Low</span> at bar <code>i</code>:&nbsp;
            <code>low[i] &lt; low[j]</code> for every <code>j</code> in <code>[i−N, i+N]</code> where <code>j ≠ i</code>
          </p>
          <p style={{ margin: 0, color: "var(--muted)" }}>
            Trade-off: ↑N = fewer, more significant points but more lag &nbsp;|&nbsp; ↓N = more points, noisier, less lag
          </p>
        </div>
      </div>

      {/* Python Code Toggle */}
      <div style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        overflow: "hidden",
      }}>
        <button
          onClick={() => setShowCode(!showCode)}
          style={{
            width: "100%",
            padding: "12px 20px",
            background: "transparent",
            border: "none",
            color: "var(--text)",
            fontSize: 14,
            fontWeight: 700,
            fontFamily: "inherit",
            cursor: "pointer",
            textAlign: "left",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span>Python Implementation</span>
          <span style={{ color: "var(--muted)", fontSize: 12 }}>{showCode ? "▲ hide" : "▼ show"}</span>
        </button>
        {showCode && (
          <pre style={{
            margin: 0,
            padding: "16px 20px",
            borderTop: "1px solid var(--border)",
            background: "var(--code-bg)",
            fontSize: 11.5,
            lineHeight: 1.6,
            overflowX: "auto",
            color: "var(--label)",
          }}>
            {PYTHON_CODE}
          </pre>
        )}
      </div>
    </div>
  );
}
