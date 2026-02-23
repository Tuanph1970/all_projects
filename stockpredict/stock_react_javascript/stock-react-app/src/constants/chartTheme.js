/**
 * Shared chart theme constants for react-financial-charts components.
 * Provides consistent styling across all chart pages.
 */

const FONT_FAMILY = "Inter, -apple-system, BlinkMacSystemFont, sans-serif";

export const chartTheme = {
  grid: {
    strokeStyle: "#C4C8D0",
    strokeDasharray: "3 3",
  },
  axis: {
    fontFamily: FONT_FAMILY,
    fontSize: 11,
    tickStrokeStyle: "#9CA3AF",
    strokeStyle: "#D1D5DB",
    tickLabelFill: "#6B7280",
  },
};

/** Shared candlestick / volume colors */
export const chartColors = {
  greenCandle: "#26a69a",
  redCandle: "#ef5350",
  greenVolume: "rgba(38, 166, 154, 0.3)",
  redVolume: "rgba(239, 83, 80, 0.3)",
};

/** Default margins for react-financial-charts (left space for Y-axis labels) */
export const chartMargin = { left: 50, right: 48, top: 10, bottom: 24 };

/** Spread onto <XAxis ...getXAxisProps() /> */
export function getXAxisProps(overrides = {}) {
  return {
    showGridLines: true,
    fontFamily: chartTheme.axis.fontFamily,
    fontSize: chartTheme.axis.fontSize,
    tickStrokeStyle: chartTheme.axis.tickStrokeStyle,
    strokeStyle: chartTheme.axis.strokeStyle,
    tickLabelFill: chartTheme.axis.tickLabelFill,
    gridLinesStrokeStyle: chartTheme.grid.strokeStyle,
    gridLinesStrokeDasharray: chartTheme.grid.strokeDasharray,
    ...overrides,
  };
}

/** Spread onto <YAxis ...getYAxisProps() /> */
export function getYAxisProps(overrides = {}) {
  return {
    showGridLines: true,
    fontFamily: chartTheme.axis.fontFamily,
    fontSize: chartTheme.axis.fontSize,
    tickStrokeStyle: chartTheme.axis.tickStrokeStyle,
    strokeStyle: chartTheme.axis.strokeStyle,
    tickLabelFill: chartTheme.axis.tickLabelFill,
    gridLinesStrokeStyle: chartTheme.grid.strokeStyle,
    gridLinesStrokeDasharray: chartTheme.grid.strokeDasharray,
    ...overrides,
  };
}

/** Props for recharts <CartesianGrid /> and axis ticks (SimulationDashboard) */
export function getRechartsGridProps() {
  return {
    grid: {
      stroke: chartTheme.grid.strokeStyle,
      strokeDasharray: chartTheme.grid.strokeDasharray,
    },
    tick: {
      fontSize: chartTheme.axis.fontSize,
      fontFamily: chartTheme.axis.fontFamily,
      fill: chartTheme.axis.tickLabelFill,
    },
  };
}
