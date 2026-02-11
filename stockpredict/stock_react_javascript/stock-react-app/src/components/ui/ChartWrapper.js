import React from "react";

/**
 * Wraps a react-financial-charts canvas and overlays axis titles
 * using absolutely-positioned CSS labels.
 *
 * Props:
 *  - yAxisTitle  (string)  label rotated on the left   e.g. "Price (VND)"
 *  - xAxisTitle  (string)  label centered at the bottom e.g. "Date"
 *  - children    the <ChartCanvas> tree
 */
export default function ChartWrapper({ yAxisTitle, xAxisTitle, children }) {
  return (
    <div style={{ position: "relative" }}>
      {yAxisTitle && (
        <div
          style={{
            position: "absolute",
            left: 0,
            top: "50%",
            transform: "rotate(-90deg) translateX(-50%)",
            transformOrigin: "0 0",
            fontSize: 11,
            fontFamily: "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
            color: "#6B7280",
            pointerEvents: "none",
            whiteSpace: "nowrap",
          }}
        >
          {yAxisTitle}
        </div>
      )}
      {children}
      {xAxisTitle && (
        <div
          style={{
            textAlign: "center",
            fontSize: 11,
            fontFamily: "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
            color: "#6B7280",
            marginTop: 2,
            pointerEvents: "none",
          }}
        >
          {xAxisTitle}
        </div>
      )}
    </div>
  );
}
