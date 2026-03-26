/**
 * td_lines_stepper.jsx
 * 
 * Interactive 6-step walkthrough showing how TD Lines (DeMark)
 * are constructed: detect RLs → find qualifying pair → draw → auto-redraw.
 * 
 * Usage: Render as a React/JSX artifact in Claude.ai
 */

import { useState, useMemo } from "react";

const STEPS = [
  {
    title: "Step 1: Detect relative lows (N=8)",
    desc: "First, detect all RLs using Schwager's definition with parameter N. With N=8, each RL must have a low lower than the 8 preceding and 8 succeeding bars. Five RLs found (blue circles). These are the only candidate anchor points.",
    showRLs: [0,1,2,3,4], tdLine: null, highlight: null, searchArrow: null,
  },
  {
    title: "Step 2: Find the most recent RL",
    desc: "The algorithm starts from the right. The most recent RL is RL₅ (highlighted in orange). This is the first anchor candidate. Now walk backward to find a qualifying second anchor.",
    showRLs: [0,1,2,3,4], tdLine: null, highlight: 4, searchArrow: null,
  },
  {
    title: "Step 3: Walk back to find a preceding LOWER RL",
    desc: "DeMark's rule: the second anchor must be the most recent preceding RL that is LOWER than RL₅. Walk backward: RL₄ — is it lower? Yes! This confirms a higher-lows pattern. RL₄ becomes the second anchor.",
    showRLs: [0,1,2,3,4], tdLine: null, highlight: 3, searchArrow: { from: 4, to: 3 },
  },
  {
    title: "Step 4: Draw the TD uptrend line",
    desc: "Connect RL₄ to RL₅ and extend forward. This is the current TD uptrend line. Fully objective — given N=8 and this data, every analyst gets this exact line.",
    showRLs: [0,1,2,3,4], tdLine: { a: 3, b: 4 }, highlight: null, searchArrow: null,
  },
  {
    title: "Step 5: What the PREVIOUS TD line looked like",
    desc: "Before RL₅ formed, the TD line connected RL₃ and RL₄ (faded amber). Notice the different slope — steeper, because the earlier uptrend phase was rising faster. When RL₅ appeared, the line automatically redrew. This is DeMark's built-in solution to the redrawing problem.",
    showRLs: [0,1,2,3,4], tdLine: { a: 3, b: 4 }, prevLine: { a: 2, b: 3 }, highlight: null, searchArrow: null,
  },
  {
    title: "Step 6: The N parameter trade-off",
    desc: "Schwager (p.42): 'TD lines are highly dependent on the value of N.' N=4 → more RLs, faster signals, more noise. N=12 → fewer RLs, more significant lines, slower signals. The choice of N is the ONE subjective decision in an otherwise fully objective method.",
    showRLs: [0,1,2,3,4], tdLine: { a: 3, b: 4 }, highlight: null, searchArrow: null,
  },
];

export default function TDLinesStepper() {
  const [current, setCurrent] = useState(0);

  const priceData = useMemo(() => {
    const pr = []; let p = 50;
    const drift = [0.3,0.5,-0.2,0.4,0.6,-0.3,0.5,0.2,-0.6,0.3,0.7,-0.4,0.4,0.6,-0.5,0.2,0.8,-0.1,0.5,0.3];
    for (let i = 0; i < 130; i++) {
      const d = drift[i % 20];
      if (i < 12) p += 0.15 + d * 0.7;
      else if (i < 18) p -= 0.25 + d * 0.4;
      else if (i < 32) p += 0.2 + d * 0.6;
      else if (i < 40) p -= 0.2 + d * 0.4;
      else if (i < 55) p += 0.18 + d * 0.6;
      else if (i < 63) p -= 0.15 + d * 0.4;
      else if (i < 80) p += 0.15 + d * 0.6;
      else if (i < 88) p -= 0.2 + d * 0.4;
      else if (i < 105) p += 0.12 + d * 0.5;
      else if (i < 113) p -= 0.18 + d * 0.4;
      else p += 0.1 + d * 0.5;
      pr.push(p);
    }
    return pr;
  }, []);

  const rlBars = [15, 37, 60, 85, 110];
  const rlPrices = rlBars.map(i => priceData[i]);

  const step = STEPS[current];
  const W = 640, H = 280, pd = { t: 30, r: 15, b: 28, l: 42 };
  const mnP = Math.min(...priceData) - 2, mxP = Math.max(...priceData) + 3;
  const xS = (i) => pd.l + (i / 129) * (W - pd.l - pd.r);
  const yS = (v) => pd.t + ((mxP - v) / (mxP - mnP)) * (H - pd.t - pd.b);

  function lineY(a, b, x) {
    const ax = rlBars[a], bx = rlBars[b];
    const ay = rlPrices[a], by = rlPrices[b];
    const slope = (by - ay) / (bx - ax);
    return ay + slope * (x - ax);
  }

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", padding: "1rem" }}>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", maxWidth: 660 }}>
        <rect x={pd.l} y={pd.t} width={W - pd.l - pd.r} height={H - pd.t - pd.b}
          fill="#f8f8f8" rx="2" />
        {/* Grid */}
        {Array.from({ length: 6 }, (_, i) => {
          const v = Math.ceil(mnP / 5) * 5 + i * 5;
          return v <= mxP ? (
            <g key={i}>
              <line x1={pd.l} x2={W - pd.r} y1={yS(v)} y2={yS(v)} stroke="#e8e8e8" strokeWidth="0.5" />
              <text x={pd.l - 5} y={yS(v) + 4} textAnchor="end" fontSize="10" fill="#999">{Math.round(v)}</text>
            </g>
          ) : null;
        })}
        {/* Price */}
        <polyline
          points={priceData.map((p, i) => `${xS(i)},${yS(p)}`).join(" ")}
          fill="none" stroke="#888" strokeWidth="1" />
        {/* Previous TD line (faded) */}
        {step.prevLine && (() => {
          const { a, b } = step.prevLine;
          const le = Math.min(rlBars[b] + 25, 129);
          return (
            <line x1={xS(rlBars[a])} y1={yS(rlPrices[a])}
              x2={xS(le)} y2={yS(lineY(a, b, le))}
              stroke="#BA7517" strokeWidth="1.5" strokeDasharray="4,4" opacity="0.5" />
          );
        })()}
        {/* Current TD line */}
        {step.tdLine && (() => {
          const { a, b } = step.tdLine;
          const le = Math.min(rlBars[b] + 25, 129);
          return (
            <g>
              <line x1={xS(rlBars[a])} y1={yS(rlPrices[a])}
                x2={xS(le)} y2={yS(lineY(a, b, le))}
                stroke="#0F6E56" strokeWidth="2.5" />
              <circle cx={xS(rlBars[a])} cy={yS(rlPrices[a])} r="7"
                fill="none" stroke="#0F6E56" strokeWidth="2" />
              <circle cx={xS(rlBars[b])} cy={yS(rlPrices[b])} r="7"
                fill="none" stroke="#0F6E56" strokeWidth="2" />
            </g>
          );
        })()}
        {/* Search arrow */}
        {step.searchArrow && (() => {
          const { from, to } = step.searchArrow;
          const fx = rlBars[from], tx = rlBars[to];
          const fy = rlPrices[from], ty = rlPrices[to];
          return (
            <g>
              <path d={`M${xS(fx)} ${yS(fy) + 16} C${xS(fx)} ${yS(fy) + 40} ${xS(tx)} ${yS(ty) + 40} ${xS(tx)} ${yS(ty) + 16}`}
                fill="none" stroke="#534AB7" strokeWidth="1.5" strokeDasharray="4,3" />
              <text x={xS((fx + tx) / 2)} y={yS(Math.min(fy, ty)) + 48}
                textAnchor="middle" fill="#534AB7" fontSize="11" fontWeight="500">
                Walk back: RL₄ &lt; RL₅? Yes!
              </text>
            </g>
          );
        })()}
        {/* RL markers */}
        {step.showRLs.map((idx) => {
          const bx = rlBars[idx];
          const py = rlPrices[idx];
          const isHL = step.highlight === idx;
          return (
            <g key={idx}>
              <circle cx={xS(bx)} cy={yS(py)} r={isHL ? 6 : 4}
                fill={isHL ? "#D85A30" : "#185FA5"} />
              <text x={xS(bx)} y={yS(py) + 16} textAnchor="middle"
                fill={isHL ? "#D85A30" : "#185FA5"} fontSize="10" fontWeight="500">
                RL{idx + 1}
              </text>
              <text x={xS(bx)} y={yS(py) + 28} textAnchor="middle"
                fill="#aaa" fontSize="9">
                {Math.round(py * 10) / 10}
              </text>
            </g>
          );
        })}
      </svg>

      <div style={{ display: "flex", alignItems: "center", gap: 12, margin: "1rem 0" }}>
        <button onClick={() => setCurrent(c => c - 1)} disabled={current === 0}
          style={{ padding: "6px 14px" }}>Previous</button>
        <div style={{ display: "flex", gap: 4 }}>
          {STEPS.map((_, i) => (
            <span key={i} style={{
              width: 10, height: 10, borderRadius: "50%",
              background: i === current ? "#333" : "#ccc", display: "inline-block"
            }} />
          ))}
        </div>
        <button onClick={() => setCurrent(c => c + 1)} disabled={current === STEPS.length - 1}
          style={{ padding: "6px 14px" }}>Next</button>
      </div>
      <div style={{ fontSize: 13, color: "#888" }}>Step {current + 1} of {STEPS.length}</div>
      <div style={{ fontSize: 16, fontWeight: 500, margin: "4px 0" }}>{step.title}</div>
      <div style={{ fontSize: 14, color: "#666", lineHeight: 1.7 }}>{step.desc}</div>
    </div>
  );
}
