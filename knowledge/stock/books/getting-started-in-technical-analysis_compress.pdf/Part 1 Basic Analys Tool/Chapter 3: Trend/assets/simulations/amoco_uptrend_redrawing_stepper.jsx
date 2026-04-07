/**
 * amoco_uptrend_redrawing_stepper.jsx
 * 
 * Interactive 7-step walkthrough showing how an uptrend produces
 * multiple false sell signals as trend lines are redrawn
 * (Figure 3.10 Amoco analog — 3 progressively shallower lines).
 * 
 * Usage: Render as a React/JSX artifact in Claude.ai
 */

import { useState, useMemo } from "react";

const STEPS = [
  {
    title: "Step 1: The initial steep uptrend — Line 1 (Apr–Jun)",
    desc: "Amoco bottoms near 80 in April and rallies sharply. You draw an uptrend line connecting the April and May lows. Steep slope — price is climbing fast.",
    showLines: [0], priceEnd: 42, events: [],
  },
  {
    title: "Step 2: First penetration — mid-June",
    desc: "Price pulls back and closes BELOW Line 1. Rule 2 says SELL. A mechanical trader sells here, expecting a reversal.",
    showLines: [0], priceEnd: 48,
    events: [{ x: 45, label: "Rule 2: SELL!\n(Line 1 broken)", color: "#A32D2D", yOff: -20 }],
  },
  {
    title: "Step 3: False signal #1 — price resumes uptrend",
    desc: "Price finds support lower and resumes climbing. The sell was FALSE — the trend just decelerated. Redraw to Line 2 (shallower).",
    showLines: [0, 1], priceEnd: 65,
    events: [
      { x: 45, label: "False sell #1", color: "#BA7517", yOff: -20 },
      { x: 48, label: "New RL (Line 2 anchor)", color: "#185FA5", yOff: 12 },
    ],
  },
  {
    title: "Step 4: Second penetration — late July",
    desc: "Price breaks below Line 2. Another sell signal fires.",
    showLines: [0, 1], priceEnd: 80,
    events: [{ x: 75, label: "Rule 2: SELL!\n(Line 2 broken)", color: "#185FA5", yOff: -20 }],
  },
  {
    title: "Step 5: False signal #2 — uptrend continues AGAIN",
    desc: "The second sell was ALSO false. Redraw to Line 3 (dashed, even shallower). Two losses taken while the stock kept going up.",
    showLines: [0, 1, 2], priceEnd: 100,
    events: [
      { x: 75, label: "False sell #2", color: "#BA7517", yOff: -20 },
      { x: 78, label: "New RL (Line 3 anchor)", color: "#0F6E56", yOff: 12 },
    ],
  },
  {
    title: "Step 6: The full picture — all three lines visible",
    desc: "Only in hindsight: the uptrend is real but decelerating. Each line is shallower. Each penetration was NOT a reversal — just a pace adjustment. Two unnecessary losses.",
    showLines: [0, 1, 2], priceEnd: 119,
    events: [
      { x: 20, label: "Line 1: steep phase", color: "#A32D2D", yOff: -28 },
      { x: 55, label: "Line 2: moderate", color: "#185FA5", yOff: -28 },
      { x: 90, label: "Line 3: mature", color: "#0F6E56", yOff: -28 },
    ],
  },
  {
    title: "Step 7: The lesson — deceleration ≠ reversal",
    desc: "Figure 3.10 is the uptrend mirror of 3.11 (downtrend). Trends naturally decelerate as they mature. Each deceleration breaks the old line, producing a false signal. This is why Schwager warns against relying on trend line breaks alone, and why Ch.11's failed signals become the more reliable tool.",
    showLines: [0, 1, 2], priceEnd: 119, events: [],
  },
];

export default function AmocoRedrawingStepper() {
  const [current, setCurrent] = useState(0);
  const step = STEPS[current];

  // Generate uptrend price data
  const priceData = useMemo(() => {
    const pr = []; let p = 89;
    const d = [0.3,0.8,-0.2,0.5,0.9,-0.4,0.6,0.1,-0.7,0.4,0.8,-0.3,0.5,0.7,-0.5,0.2,0.9,-0.1,0.6,0.3];
    for (let i = 0; i < 120; i++) {
      const s = d[i % 20];
      if (i < 6) p += 0.1 + s * 0.6;
      else if (i === 6) p -= 3.5;
      else if (i < 18) p += 0.22 + s * 0.5;
      else if (i < 22) p -= 0.3 + s * 0.4;
      else if (i < 35) p += 0.2 + s * 0.5;
      else if (i < 40) p -= 0.25 + s * 0.4;
      else if (i < 55) p += 0.18 + s * 0.5;
      else if (i === 55) p -= 4.2;
      else if (i < 70) p += 0.25 + s * 0.5;
      else if (i < 76) p -= 0.2 + s * 0.4;
      else if (i < 90) p += 0.15 + s * 0.5;
      else if (i < 96) p -= 0.2 + s * 0.4;
      else if (i < 110) p += 0.18 + s * 0.5;
      else if (i < 116) p -= 0.3 + s * 0.4;
      else p += 0.12 + s * 0.5;
      pr.push(Math.max(p, 80));
    }
    return pr;
  }, []);

  const lines = [
    { x1: 10, y1: 81, x2: 40, y2: 92.5, col: "#A32D2D", dash: "" },
    { x1: 10, y1: 81, x2: 70, y2: 93, col: "#185FA5", dash: "" },
    { x1: 10, y1: 81, x2: 100, y2: 93.5, col: "#0F6E56", dash: "6,4" },
  ];

  const W = 640, H = 280, pd = { t: 30, r: 15, b: 22, l: 42 };
  const mnP = 79, mxP = 100;
  const xS = (i) => pd.l + (i / 119) * (W - pd.l - pd.r);
  const yS = (v) => pd.t + ((mxP - v) / (mxP - mnP)) * (H - pd.t - pd.b);

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", padding: "1rem" }}>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", maxWidth: 660 }}>
        <rect x={pd.l} y={pd.t} width={W - pd.l - pd.r} height={H - pd.t - pd.b}
          fill="#f8f8f8" rx="2" />
        {/* Price */}
        <polyline
          points={priceData.slice(0, step.priceEnd + 1).map((p, i) => `${xS(i)},${yS(p)}`).join(" ")}
          fill="none" stroke="#555" strokeWidth="1.2" />
        {step.priceEnd < 119 && (
          <polyline
            points={priceData.slice(step.priceEnd).map((p, i) => `${xS(step.priceEnd + i)},${yS(p)}`).join(" ")}
            fill="none" stroke="#ccc" strokeWidth="0.8" strokeDasharray="2,3" />
        )}
        {/* Trend lines */}
        {step.showLines.map((li) => {
          const tl = lines[li];
          const le = Math.min(step.priceEnd + 15, 115);
          const slope = (tl.y2 - tl.y1) / (tl.x2 - tl.x1);
          const ye = tl.y1 + slope * (le - tl.x1);
          return (
            <line key={li} x1={xS(tl.x1)} y1={yS(tl.y1)} x2={xS(le)} y2={yS(ye)}
              stroke={tl.col} strokeWidth="2" strokeDasharray={tl.dash || "none"} />
          );
        })}
        {/* Events */}
        {step.events.map((ev, i) => {
          const py = priceData[Math.min(ev.x, priceData.length - 1)];
          return (
            <g key={i}>
              <circle cx={xS(ev.x)} cy={yS(py)} r="4" fill={ev.col} />
              {ev.label.split("\n").map((line, li) => (
                <text key={li} x={xS(ev.x) + 8} y={yS(py) + ev.yOff + li * 14}
                  fill={ev.col} fontSize="11" fontWeight="500">{line}</text>
              ))}
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
