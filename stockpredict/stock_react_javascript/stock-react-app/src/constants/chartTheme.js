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

/** Spread onto <XAxis ...getXAxisProps() /> */
export function getXAxisProps(overrides = {}) {
  return {
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
