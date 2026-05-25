import React from "react";

export const DRAWING_TOOLS = ["cursor", "trend", "hline", "fib"];

const TOOL_LABELS = {
  cursor: "Cursor",
  trend:  "Trend",
  hline:  "H-line",
  fib:    "Fib",
};

const styles = {
  group: {
    display: "flex",
    gap: 2,
    background: "#1F2937",
    border: "1px solid #374151",
    borderRadius: 4,
    padding: 2,
  },
  tab: (active) => ({
    padding: "3px 8px",
    fontSize: 11,
    fontFamily: "Inter, sans-serif",
    background: active ? "#3B82F6" : "transparent",
    color: active ? "#F9FAFB" : "#9CA3AF",
    border: "none",
    borderRadius: 3,
    cursor: "pointer",
    userSelect: "none",
  }),
  clear: {
    padding: "3px 8px",
    fontSize: 11,
    fontFamily: "Inter, sans-serif",
    background: "transparent",
    color: "#F87171",
    border: "none",
    borderRadius: 3,
    cursor: "pointer",
    userSelect: "none",
  },
};

export default function DrawingToolbar({ activeTool, onSelectTool, onClearAll, hasDrawings }) {
  return (
    <div style={styles.group}>
      {DRAWING_TOOLS.map((tool) => (
        <button
          key={tool}
          style={styles.tab(activeTool === tool)}
          onClick={() => onSelectTool(tool)}
          title={TOOL_LABELS[tool]}
        >
          {TOOL_LABELS[tool]}
        </button>
      ))}
      <button
        style={styles.clear}
        onClick={onClearAll}
        disabled={!hasDrawings}
        title="Clear all drawings"
      >
        ✕
      </button>
    </div>
  );
}
