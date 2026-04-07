/**
 * trend_line_redrawing_stepper.jsx
 * 
 * Interactive 6-step walkthrough showing how trend line redrawing
 * produces false signals in real time (Figure 3.11 Matif bond analog).
 * 
 * Steps:
 * 1. Initial steep downtrend line
 * 2. Price approaches the line
 * 3. The penetration (false buy signal)
 * 4. The trend resumes (loss taken)
 * 5. Redraw the trend line (hindsight)
 * 6. The lesson — hindsight vs real time
 * 
 * Usage: Render as a React/JSX artifact in Claude.ai
 * or adapt for any React environment.
 */

import { useState, useMemo } from "react";

const STEPS = [
  {
    title: "Step 1: The initial downtrend line (Aug–Nov 1993)",
    desc: "You're a trader in late 1993. Price peaked around 128 and has been making lower highs. You draw a downtrend line connecting these peaks. This is the ONLY information you have.",
    showLines: [0], priceEnd: 40, events: [],
  },
  {
    title: "Step 2: Price approaches the trend line (Jan 1994)",
    desc: "Price rallies back toward your downtrend line. According to Rule 1, this approach to a downtrend line is a potential SHORT entry.",
    showLines: [0], priceEnd: 55,
    events: [{ x: 52, label: "Rule 1: Sell?", color: "#A32D2D", yOff: -12 }],
  },
  {
    title: "Step 3: The penetration! (Feb 1994)",
    desc: "Price breaks ABOVE your downtrend line. Rule 2 says BUY. You go long around 122, thinking the downtrend is over.",
    showLines: [0], priceEnd: 65,
    events: [{ x: 62, label: "Rule 2: BUY!", color: "#185FA5", yOff: -15 }],
  },
  {
    title: "Step 4: False signal — trend resumes (Mar–May 1994)",
    desc: "The rally fizzles. Price drops from 122 to 110. Your long is underwater. The penetration was FALSE. You take a ~10% loss.",
    showLines: [0], priceEnd: 90,
    events: [
      { x: 62, label: "BUY here", color: "#185FA5", yOff: -15 },
      { x: 88, label: "STOP OUT (~10% loss)", color: "#A32D2D", yOff: 10 },
    ],
  },
  {
    title: "Step 5: Redraw the trend line (hindsight)",
    desc: "NOW you can see it. The Feb rally created a new, lower RH. You connect it to the original peak — a shallower line. But you could only draw it AFTER the false signal cost you money.",
    showLines: [0, 1], priceEnd: 90,
    events: [{ x: 62, label: "False break", color: "#BA7517", yOff: -15 }],
  },
  {
    title: "Step 6: The lesson — hindsight vs real time",
    desc: "The shallower line is 'correct' — but invisible when you needed it. Schwager: 'Trend lines work much better in hindsight than in real time.' This is why Ch.11's failed signals are so valuable.",
    showLines: [0, 1], priceEnd: 90,
    events: [
      { x: 25, label: "Only this line existed in real time", color: "#A32D2D", yOff: -30 },
      { x: 70, label: "This line only visible after the damage", color: "#0F6E56", yOff: -38 },
    ],
  },
];

// Generate synthetic downtrend price data
function generatePriceData() {
  const data = [];
  let p = 128;
  for (let i = 0; i < 100; i++) {
    if (i < 8) p += (Math.random() - 0.5) * 0.8;
    else if (i < 20) p -= 0.12 + (Math.random() - 0.3) * 0.5;
    else if (i < 35) p -= 0.08 + (Math.random() - 0.4) * 0.4;
    else if (i < 50) p -= 0.15 + (Math.random() - 0.35) * 0.5;
    else if (i < 60) p += 0.25 + (Math.random() - 0.4) * 0.4;
    else if (i < 68) p += 0.05 + (Math.random() - 0.55) * 0.5;
    else if (i < 85) p -= 0.25 + (Math.random() - 0.3) * 0.5;
    else p -= 0.1 + (Math.random() - 0.45) * 0.4;
    data.push(Math.max(p, 108));
  }
  return data;
}

const TREND_LINES = [
  { x1: 5, y1: 128, x2: 90, y2: 113, color: "#A32D2D", dash: "" },
  { x1: 5, y1: 128, x2: 90, y2: 116.5, color: "#0F6E56", dash: "6,4" },
];

export default function TrendLineRedrawingStepper() {
  const [current, setCurrent] = useState(0);
  const priceData = useMemo(() => generatePriceData(), []);
  const step = STEPS[current];

  // Chart dimensions
  const W = 640, H = 280;
  const pad = { t: 40, r: 20, b: 30, l: 45 };
  const minP = 107, maxP = 130;
  const xS = (i) => pad.l + (i / 99) * (W - pad.l - pad.r);
  const yS = (v) => pad.t + ((maxP - v) / (maxP - minP)) * (H - pad.t - pad.b);

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", padding: "1rem" }}>
      {/* Chart SVG */}
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", maxWidth: 660 }}>
        <rect x={pad.l} y={pad.t} width={W - pad.l - pad.r} height={H - pad.t - pad.b}
          fill="#f8f8f8" rx="2" />
        {/* Price line */}
        <polyline
          points={priceData.slice(0, step.priceEnd + 1).map((p, i) => `${xS(i)},${yS(p)}`).join(" ")}
          fill="none" stroke="#555" strokeWidth="1.2"
        />
        {/* Future (faded) */}
        {step.priceEnd < 99 && (
          <polyline
            points={priceData.slice(step.priceEnd).map((p, i) => `${xS(step.priceEnd + i)},${yS(p)}`).join(" ")}
            fill="none" stroke="#ccc" strokeWidth="0.8" strokeDasharray="2,3"
          />
        )}
        {/* Trend lines */}
        {step.showLines.map((li) => {
          const tl = TREND_LINES[li];
          const end = Math.min(step.priceEnd + 10, 95);
          const slope = (tl.y2 - tl.y1) / (90 - tl.x1);
          const yEnd = tl.y1 + slope * (end - tl.x1);
          return (
            <line key={li} x1={xS(tl.x1)} y1={yS(tl.y1)} x2={xS(end)} y2={yS(yEnd)}
              stroke={tl.color} strokeWidth="2" strokeDasharray={tl.dash || "none"} />
          );
        })}
        {/* Events */}
        {step.events.map((ev, i) => {
          const py = priceData[Math.min(ev.x, priceData.length - 1)];
          return (
            <g key={i}>
              <circle cx={xS(ev.x)} cy={yS(py)} r="4" fill={ev.color} />
              {ev.label.split("\n").map((line, li) => (
                <text key={li} x={xS(ev.x) + 8} y={yS(py) + ev.yOff + li * 14}
                  fill={ev.color} fontSize="11" fontWeight="500">{line}</text>
              ))}
            </g>
          );
        })}
      </svg>

      {/* Controls */}
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

      {/* Step content */}
      <div style={{ fontSize: 13, color: "#888" }}>Step {current + 1} of {STEPS.length}</div>
      <div style={{ fontSize: 16, fontWeight: 500, margin: "4px 0" }}>{step.title}</div>
      <div style={{ fontSize: 14, color: "#666", lineHeight: 1.7 }}>{step.desc}</div>
    </div>
  );
}
