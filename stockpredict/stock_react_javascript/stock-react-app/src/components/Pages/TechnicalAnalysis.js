import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { analysisAPI, stockAPI } from '../../services/api';
import { AlertCircle, TrendingUp, TrendingDown, Activity, BarChart2, LineChart, Target, Zap, Search, Settings, ChevronDown, ChevronUp, X, Check, RotateCcw } from 'lucide-react';
import { format } from "d3-format";
import { timeFormat } from "d3-time-format";
import { getXAxisProps, getYAxisProps } from "../../constants/chartTheme";
import ChartWrapper from "../ui/ChartWrapper";

import {
  discontinuousTimeScaleProviderBuilder,
  Chart,
  ChartCanvas,
  CandlestickSeries,
  LineSeries,
  BarSeries,
  StraightLine,
  XAxis,
  YAxis,
  CrossHairCursor,
  EdgeIndicator,
  MouseCoordinateX,
  MouseCoordinateY,
  ZoomButtons,
  OHLCTooltip,
  SingleValueTooltip,
  MovingAverageTooltip,
  BollingerSeries,
  BollingerBandTooltip,
  MACDSeries,
  RSISeries,
  StochasticSeries,
  lastVisibleItemBasedZoomAnchor,
  ema,
  sma,
  bollingerBand,
  macd,
  rsi,
  stochasticOscillator
} from "react-financial-charts";

// Comprehensive Technical Indicators Configuration
const ALL_INDICATORS = {
  movingAverages: {
    name: "Moving Averages",
    icon: "📈",
    description: "Trend-following indicators",
    indicators: {
      sma5: { name: "SMA (5)", shortName: "SMA5", color: "#3b82f6", enabled: false, period: 5, type: "overlay" },
      sma10: { name: "SMA (10)", shortName: "SMA10", color: "#8b5cf6", enabled: false, period: 10, type: "overlay" },
      sma20: { name: "SMA (20)", shortName: "SMA20", color: "#2563eb", enabled: true, period: 20, type: "overlay" },
      sma50: { name: "SMA (50)", shortName: "SMA50", color: "#f59e0b", enabled: true, period: 50, type: "overlay" },
      sma100: { name: "SMA (100)", shortName: "SMA100", color: "#10b981", enabled: false, period: 100, type: "overlay" },
      sma200: { name: "SMA (200)", shortName: "SMA200", color: "#ef4444", enabled: false, period: 200, type: "overlay" },
      ema5: { name: "EMA (5)", shortName: "EMA5", color: "#06b6d4", enabled: false, period: 5, type: "overlay" },
      ema10: { name: "EMA (10)", shortName: "EMA10", color: "#14b8a6", enabled: false, period: 10, type: "overlay" },
      ema12: { name: "EMA (12)", shortName: "EMA12", color: "#10b981", enabled: false, period: 12, type: "overlay" },
      ema20: { name: "EMA (20)", shortName: "EMA20", color: "#22c55e", enabled: false, period: 20, type: "overlay" },
      ema26: { name: "EMA (26)", shortName: "EMA26", color: "#8b5cf6", enabled: false, period: 26, type: "overlay" },
      ema50: { name: "EMA (50)", shortName: "EMA50", color: "#a855f7", enabled: false, period: 50, type: "overlay" },
      wma10: { name: "WMA (10)", shortName: "WMA10", color: "#ec4899", enabled: false, period: 10, type: "overlay" },
      wma20: { name: "WMA (20)", shortName: "WMA20", color: "#f43f5e", enabled: false, period: 20, type: "overlay" },
      dema20: { name: "DEMA (20)", shortName: "DEMA20", color: "#84cc16", enabled: false, period: 20, type: "overlay" },
      tema20: { name: "TEMA (20)", shortName: "TEMA20", color: "#eab308", enabled: false, period: 20, type: "overlay" },
    }
  },
  trendIndicators: {
    name: "Trend Indicators",
    icon: "📊",
    description: "Identify trend direction and strength",
    indicators: {
      parabolicSar: { name: "Parabolic SAR", shortName: "PSAR", color: "#f97316", enabled: false, type: "overlay" },
      supertrend: { name: "Supertrend", shortName: "ST", color: "#22c55e", colorDown: "#ef4444", enabled: false, type: "overlay" },
      ichimoku: { name: "Ichimoku Cloud", shortName: "ICHI", enabled: false, type: "overlay", colors: { tenkan: "#2563eb", kijun: "#ef4444", senkouA: "#22c55e", senkouB: "#f97316", chikou: "#8b5cf6" } },
      adx: { name: "ADX (14)", shortName: "ADX", color: "#6366f1", enabled: false, period: 14, type: "separate" },
      aroon: { name: "Aroon (25)", shortName: "AROON", colorUp: "#22c55e", colorDown: "#ef4444", enabled: false, period: 25, type: "separate" },
      vortex: { name: "Vortex Indicator", shortName: "VI", colorUp: "#22c55e", colorDown: "#ef4444", enabled: false, type: "separate" },
    }
  },
  momentum: {
    name: "Momentum Indicators",
    icon: "⚡",
    description: "Measure speed of price changes",
    indicators: {
      rsi: { name: "RSI (14)", shortName: "RSI", color: "#6366f1", enabled: true, period: 14, type: "separate", range: [0, 100] },
      rsi7: { name: "RSI (7)", shortName: "RSI7", color: "#8b5cf6", enabled: false, period: 7, type: "separate", range: [0, 100] },
      rsi21: { name: "RSI (21)", shortName: "RSI21", color: "#a855f7", enabled: false, period: 21, type: "separate", range: [0, 100] },
      macd: { name: "MACD (12,26,9)", shortName: "MACD", enabled: true, fast: 12, slow: 26, signal: 9, type: "separate", colors: { macd: "#2563eb", signal: "#ef4444", histogram: "#8b5cf6" } },
      stochastic: { name: "Stochastic (14,3,3)", shortName: "STOCH", colorK: "#2563eb", colorD: "#ef4444", enabled: true, kPeriod: 14, dPeriod: 3, type: "separate", range: [0, 100] },
      stochasticRsi: { name: "Stochastic RSI", shortName: "SRSI", colorK: "#10b981", colorD: "#f59e0b", enabled: false, type: "separate", range: [0, 100] },
      cci: { name: "CCI (20)", shortName: "CCI", color: "#f59e0b", enabled: false, period: 20, type: "separate" },
      momentum: { name: "Momentum (10)", shortName: "MOM", color: "#3b82f6", enabled: false, period: 10, type: "separate" },
      roc: { name: "Rate of Change (12)", shortName: "ROC", color: "#14b8a6", enabled: false, period: 12, type: "separate" },
      williamR: { name: "Williams %R (14)", shortName: "W%R", color: "#ec4899", enabled: false, period: 14, type: "separate", range: [-100, 0] },
      tsi: { name: "True Strength Index", shortName: "TSI", color: "#8b5cf6", colorSignal: "#ef4444", enabled: false, type: "separate" },
      ultimateOsc: { name: "Ultimate Oscillator", shortName: "UO", color: "#f97316", enabled: false, type: "separate", range: [0, 100] },
      awesome: { name: "Awesome Oscillator", shortName: "AO", enabled: false, type: "separate" },
    }
  },
  volatility: {
    name: "Volatility Indicators",
    icon: "🌊",
    description: "Measure market volatility",
    indicators: {
      bollingerBands: { name: "Bollinger Bands (20,2)", shortName: "BB", color: "#ef4444", enabled: true, period: 20, stdDev: 2, type: "overlay" },
      bollingerBands3: { name: "Bollinger Bands (20,3)", shortName: "BB3", color: "#f97316", enabled: false, period: 20, stdDev: 3, type: "overlay" },
      atr: { name: "ATR (14)", shortName: "ATR", color: "#8b5cf6", enabled: false, period: 14, type: "separate" },
      atr20: { name: "ATR (20)", shortName: "ATR20", color: "#a855f7", enabled: false, period: 20, type: "separate" },
      keltnerChannel: { name: "Keltner Channel", shortName: "KC", color: "#06b6d4", enabled: false, type: "overlay" },
      donchianChannel: { name: "Donchian Channel (20)", shortName: "DC", color: "#0ea5e9", enabled: false, period: 20, type: "overlay" },
      stdDev: { name: "Standard Deviation", shortName: "STDDEV", color: "#64748b", enabled: false, type: "separate" },
      historicalVol: { name: "Historical Volatility", shortName: "HV", color: "#475569", enabled: false, type: "separate" },
    }
  },
  volume: {
    name: "Volume Indicators",
    icon: "📦",
    description: "Analyze trading volume",
    indicators: {
      volume: { name: "Volume", shortName: "VOL", enabled: true, type: "separate" },
      obv: { name: "On Balance Volume", shortName: "OBV", color: "#f59e0b", enabled: false, type: "separate" },
      vwap: { name: "VWAP", shortName: "VWAP", color: "#8b5cf6", enabled: false, type: "overlay" },
      mfi: { name: "Money Flow Index (14)", shortName: "MFI", color: "#22c55e", enabled: false, period: 14, type: "separate", range: [0, 100] },
      adLine: { name: "A/D Line", shortName: "AD", color: "#3b82f6", enabled: false, type: "separate" },
      chaikinMf: { name: "Chaikin Money Flow", shortName: "CMF", color: "#14b8a6", enabled: false, type: "separate" },
      chaikinOsc: { name: "Chaikin Oscillator", shortName: "CHO", color: "#06b6d4", enabled: false, type: "separate" },
      volumeOsc: { name: "Volume Oscillator", shortName: "VOSC", color: "#84cc16", enabled: false, type: "separate" },
      eom: { name: "Ease of Movement", shortName: "EOM", color: "#eab308", enabled: false, type: "separate" },
      forceIndex: { name: "Force Index", shortName: "FI", color: "#f97316", enabled: false, type: "separate" },
      nvi: { name: "Negative Volume Index", shortName: "NVI", color: "#ef4444", enabled: false, type: "separate" },
      pvi: { name: "Positive Volume Index", shortName: "PVI", color: "#22c55e", enabled: false, type: "separate" },
    }
  },
  supportResistance: {
    name: "Support & Resistance",
    icon: "🎯",
    description: "Key price levels",
    indicators: {
      pivotPoints: { name: "Pivot Points", shortName: "PP", enabled: false, type: "overlay" },
      fibonacciRet: { name: "Fibonacci Retracement", shortName: "FIB", enabled: false, type: "overlay" },
      fibonacciExt: { name: "Fibonacci Extension", shortName: "FIBEXT", enabled: false, type: "overlay" },
    }
  },
  priceTransform: {
    name: "Price Transform",
    icon: "🔄",
    description: "Modified price displays",
    indicators: {
      heikinAshi: { name: "Heikin Ashi", shortName: "HA", enabled: false, type: "candle" },
      renko: { name: "Renko", shortName: "RENKO", enabled: false, type: "candle" },
      typicalPrice: { name: "Typical Price", shortName: "TP", color: "#64748b", enabled: false, type: "overlay" },
      medianPrice: { name: "Median Price", shortName: "MP", color: "#94a3b8", enabled: false, type: "overlay" },
      weightedClose: { name: "Weighted Close", shortName: "WC", color: "#cbd5e1", enabled: false, type: "overlay" },
    }
  },
  billWilliams: {
    name: "Bill Williams",
    icon: "🐊",
    description: "Bill Williams indicators",
    indicators: {
      alligator: { name: "Alligator", shortName: "GATOR", enabled: false, type: "overlay", colors: { jaw: "#2563eb", teeth: "#ef4444", lips: "#22c55e" } },
      fractal: { name: "Fractals", shortName: "FRAC", enabled: false, type: "overlay" },
      gatorOsc: { name: "Gator Oscillator", shortName: "GATOROSC", enabled: false, type: "separate" },
      mfi_bw: { name: "Market Facilitation Index", shortName: "MFIBW", enabled: false, type: "separate" },
      accelerator: { name: "Accelerator Oscillator", shortName: "AC", enabled: false, type: "separate" },
    }
  },
};

// Legacy indicator groups for backward compatibility with existing chart
const INDICATOR_GROUPS = {
  priceOverlay: {
    name: "Price Overlay",
    description: "Indicators on price scale",
    indicators: {
      sma20: { name: "SMA 20", color: "#2563eb", enabled: true },
      sma50: { name: "SMA 50", color: "#f59e0b", enabled: true },
      ema12: { name: "EMA 12", color: "#10b981", enabled: false },
      ema26: { name: "EMA 26", color: "#8b5cf6", enabled: false },
      bollingerBands: { name: "Bollinger Bands", color: "#ef4444", enabled: true }
    }
  },
  oscillators: {
    name: "Oscillators (0-100)",
    description: "RSI, Stochastic",
    indicators: {
      rsi: { name: "RSI (14)", color: "#6366f1", enabled: true },
      stochastic: { name: "Stochastic", colorK: "#2563eb", colorD: "#ef4444", enabled: true }
    }
  },
  momentum: {
    name: "Momentum",
    description: "MACD, centered on zero",
    indicators: {
      macd: { name: "MACD", enabled: true }
    }
  },
  volume: {
    name: "Volume",
    description: "Volume-based indicators",
    indicators: {
      volume: { name: "Volume", enabled: true },
      obv: { name: "OBV", color: "#f59e0b", enabled: false }
    }
  }
};

export const TechnicalAnalysis = () => {
  const { t } = useTranslation();
  const [selectedSymbol, setSelectedSymbol] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [analysisData, setAnalysisData] = useState(null);
  const [period, setPeriod] = useState(100);
  const [activeTab, setActiveTab] = useState('charts');

  // Indicator settings
  const [indicatorSettings, setIndicatorSettings] = useState(INDICATOR_GROUPS);
  const [showSettings, setShowSettings] = useState(false);

  // All indicators popup state
  const [showIndicatorPopup, setShowIndicatorPopup] = useState(false);
  const [allIndicators, setAllIndicators] = useState(ALL_INDICATORS);
  const [searchIndicator, setSearchIndicator] = useState('');
  const [expandedCategories, setExpandedCategories] = useState(
    Object.keys(ALL_INDICATORS).reduce((acc, key) => ({ ...acc, [key]: false }), {})
  );

  // Chart panels visibility
  const [panels, setPanels] = useState({
    price: true,
    oscillators: true,
    macd: true,
    volume: true
  });

  // Stock search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [showResults, setShowResults] = useState(false);
  const [isSearching, setIsSearching] = useState(false);

  useEffect(() => {
    if (selectedSymbol && period) {
      fetchTechnicalAnalysis(selectedSymbol);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period, selectedSymbol]);

  const fetchTechnicalAnalysis = async (symbol) => {
    setLoading(true);
    setError(null);
    try {
      const data = await analysisAPI.getTechnicalAnalysis(symbol, period);
      setAnalysisData(data);
    } catch (err) {
      setError('Failed to fetch technical analysis data: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  // Stock search functionality
  const handleSearch = async (query) => {
    if (!query.trim()) {
      setSearchResults([]);
      setShowResults(false);
      return;
    }
    setIsSearching(true);
    try {
      const results = await stockAPI.searchStock(query);
      setSearchResults(results);
      setShowResults(true);
    } catch (error) {
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const handleSearchChange = (e) => {
    const value = e.target.value;
    setSearchQuery(value);
    if (window.searchTimeout) clearTimeout(window.searchTimeout);
    window.searchTimeout = setTimeout(() => handleSearch(value), 300);
  };

  const handleStockSelect = (stock) => {
    setSearchQuery(stock.symbol);
    setShowResults(false);
    setSelectedSymbol(stock.symbol);
  };

  const toggleIndicator = (group, indicator) => {
    setIndicatorSettings(prev => ({
      ...prev,
      [group]: {
        ...prev[group],
        indicators: {
          ...prev[group].indicators,
          [indicator]: {
            ...prev[group].indicators[indicator],
            enabled: !prev[group].indicators[indicator].enabled
          }
        }
      }
    }));
  };

  const togglePanel = (panel) => {
    setPanels(prev => ({ ...prev, [panel]: !prev[panel] }));
  };

  // Toggle indicator in ALL_INDICATORS
  const toggleAllIndicator = (category, indicatorKey) => {
    setAllIndicators(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        indicators: {
          ...prev[category].indicators,
          [indicatorKey]: {
            ...prev[category].indicators[indicatorKey],
            enabled: !prev[category].indicators[indicatorKey].enabled
          }
        }
      }
    }));
  };

  // Toggle category expansion
  const toggleCategory = (category) => {
    setExpandedCategories(prev => ({
      ...prev,
      [category]: !prev[category]
    }));
  };

  // Select all indicators in a category
  const selectAllInCategory = (category) => {
    setAllIndicators(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        indicators: Object.fromEntries(
          Object.entries(prev[category].indicators).map(([key, ind]) => [key, { ...ind, enabled: true }])
        )
      }
    }));
  };

  // Deselect all indicators in a category
  const deselectAllInCategory = (category) => {
    setAllIndicators(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        indicators: Object.fromEntries(
          Object.entries(prev[category].indicators).map(([key, ind]) => [key, { ...ind, enabled: false }])
        )
      }
    }));
  };

  // Reset all indicators to default
  const resetAllIndicators = () => {
    setAllIndicators(ALL_INDICATORS);
  };

  // Map keys from the comprehensive ALL_INDICATORS popup to the subset that
  // the chart actually knows how to render (INDICATOR_GROUPS / indicatorSettings).
  // Keys not listed here are visible in the popup but not yet renderable; we
  // surface them in the "skipped" toast below so the UX is honest.
  const APPLY_MAP = {
    'movingAverages.sma20':       ['priceOverlay', 'sma20'],
    'movingAverages.sma50':       ['priceOverlay', 'sma50'],
    'movingAverages.ema12':       ['priceOverlay', 'ema12'],
    'movingAverages.ema26':       ['priceOverlay', 'ema26'],
    'volatility.bollingerBands':  ['priceOverlay', 'bollingerBands'],
    'momentum.rsi':               ['oscillators',  'rsi'],
    'momentum.stochastic':        ['oscillators',  'stochastic'],
    'momentum.macd':              ['momentum',     'macd'],
    'volume.volume':              ['volume',       'volume'],
    'volume.obv':                 ['volume',       'obv'],
  };

  const applyIndicators = () => {
    // Snapshot the current chart settings, then walk every popup selection
    // and flip its mapped chart setting to match.
    const next = JSON.parse(JSON.stringify(indicatorSettings));
    const skipped = [];

    Object.entries(allIndicators).forEach(([category, group]) => {
      Object.entries(group.indicators).forEach(([key, ind]) => {
        const mapped = APPLY_MAP[`${category}.${key}`];
        if (mapped) {
          const [chartGroup, chartKey] = mapped;
          if (next[chartGroup]?.indicators?.[chartKey]) {
            next[chartGroup].indicators[chartKey].enabled = !!ind.enabled;
          }
        } else if (ind.enabled) {
          skipped.push(ind.shortName || ind.name || key);
        }
      });
    });

    setIndicatorSettings(next);
    setShowIndicatorPopup(false);

    if (skipped.length > 0) {
      // Lightweight feedback — chart can't render every catalogue entry yet.
      // eslint-disable-next-line no-console
      console.info(
        `Selected indicators not yet renderable on chart: ${skipped.join(', ')}`
      );
    }
  };

  // Get count of selected indicators
  const getSelectedCount = () => {
    let count = 0;
    Object.values(allIndicators).forEach(category => {
      Object.values(category.indicators).forEach(ind => {
        if (ind.enabled) count++;
      });
    });
    return count;
  };

  // Get count of selected indicators in a category
  const getCategorySelectedCount = (category) => {
    let count = 0;
    Object.values(allIndicators[category].indicators).forEach(ind => {
      if (ind.enabled) count++;
    });
    return count;
  };

  // Filter indicators by search query
  const filterIndicators = (category) => {
    if (!searchIndicator.trim()) return Object.entries(allIndicators[category].indicators);
    return Object.entries(allIndicators[category].indicators).filter(([key, ind]) =>
      ind.name.toLowerCase().includes(searchIndicator.toLowerCase()) ||
      ind.shortName.toLowerCase().includes(searchIndicator.toLowerCase())
    );
  };

  const formatNumber = (value) => {
    if (value === null || value === undefined) return 'N/A';
    return value.toFixed(2);
  };

  const formatCurrency = (value) => {
    if (!value) return 'N/A';
    return `$${value.toFixed(2)}`;
  };

  const formatVolume = (value) => {
    if (!value) return 'N/A';
    if (value >= 1e9) return `${(value / 1e9).toFixed(2)}B`;
    if (value >= 1e6) return `${(value / 1e6).toFixed(2)}M`;
    if (value >= 1e3) return `${(value / 1e3).toFixed(2)}K`;
    return value.toString();
  };

  const getSignalColor = (signal) => {
    switch (signal) {
      case 'BUY':
      case 'STRONG BUY':
        return 'text-green-600';
      case 'SELL':
      case 'STRONG SELL':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const getSignalBgColor = (signal) => {
    switch (signal) {
      case 'BUY':
      case 'STRONG BUY':
        return 'bg-green-50';
      case 'SELL':
      case 'STRONG SELL':
        return 'bg-red-50';
      default:
        return 'bg-gray-50';
    }
  };

  const getRecommendationIcon = (recommendation) => {
    switch (recommendation) {
      case 'STRONG BUY':
        return <TrendingUp className="w-8 h-8 text-green-600" />;
      case 'BUY':
        return <TrendingUp className="w-6 h-6 text-green-500" />;
      case 'STRONG SELL':
        return <TrendingDown className="w-8 h-8 text-red-600" />;
      case 'SELL':
        return <TrendingDown className="w-6 h-6 text-red-500" />;
      default:
        return <Activity className="w-6 h-6 text-gray-500" />;
    }
  };

  // Prepare chart data for react-financial-charts
  const prepareChartData = useCallback(() => {
    if (!analysisData?.chart_data) return [];

    const { dates, prices, volumes, opens, highs, lows } = analysisData.chart_data;

    return dates.map((date, index) => ({
      date: new Date(date),
      open: opens?.[index] ?? prices[index],
      high: highs?.[index] ?? prices[index],
      low: lows?.[index] ?? prices[index],
      close: prices[index],
      volume: volumes?.[index] ?? 0
    }));
  }, [analysisData]);

  // Indicator checkbox component
  const IndicatorCheckbox = ({ group, indicatorKey, indicator }) => (
    <label className="flex items-center space-x-2 cursor-pointer hover:bg-gray-50 p-1 rounded">
      <input
        type="checkbox"
        checked={indicator.enabled}
        onChange={() => toggleIndicator(group, indicatorKey)}
        className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
      />
      <span className="text-sm text-gray-700">{indicator.name}</span>
      {indicator.color && (
        <span className="w-3 h-3 rounded-full" style={{ backgroundColor: indicator.color }}></span>
      )}
    </label>
  );

  // Settings Panel component
  const SettingsPanel = () => (
    <div className="bg-white rounded-xl shadow-lg border border-gray-200 p-4 mb-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-bold text-gray-900 flex items-center">
          <Settings className="w-4 h-4 mr-2" />
          {t('analysis.technical.indicator_settings_title')}
        </h3>
        <button onClick={() => setShowSettings(false)} className="text-gray-400 hover:text-gray-600">
          <ChevronUp className="w-5 h-5" />
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Object.entries(indicatorSettings).map(([groupKey, group]) => (
          <div key={groupKey} className="border border-gray-200 rounded-lg p-3">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-xs font-semibold text-gray-800">{group.name}</h4>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={panels[groupKey === 'priceOverlay' ? 'price' : groupKey === 'oscillators' ? 'oscillators' : groupKey === 'momentum' ? 'macd' : 'volume']}
                  onChange={() => togglePanel(groupKey === 'priceOverlay' ? 'price' : groupKey === 'oscillators' ? 'oscillators' : groupKey === 'momentum' ? 'macd' : 'volume')}
                  className="w-3 h-3 rounded border-gray-300 text-blue-600 mr-1"
                />
                <span className="text-xs text-gray-500">{t('analysis.technical.panel_label')}</span>
              </label>
            </div>
            <p className="text-xs text-gray-500 mb-2">{group.description}</p>
            <div className="space-y-1">
              {Object.entries(group.indicators).map(([key, indicator]) => (
                <IndicatorCheckbox
                  key={key}
                  group={groupKey}
                  indicatorKey={key}
                  indicator={indicator}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  // Indicator Selection Popup Component
  const IndicatorSelectionPopup = () => {
    if (!showIndicatorPopup) return null;

    // Close popup when clicking outside
    const handleBackdropClick = (e) => {
      if (e.target === e.currentTarget) {
        setShowIndicatorPopup(false);
      }
    };

    return (
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        onClick={handleBackdropClick}
      >
        <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl flex flex-col" style={{ maxHeight: 'calc(100vh - 40px)', height: '90vh' }}>
          {/* Header */}
          <div className="bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-500 p-4 text-white flex-shrink-0 rounded-t-2xl">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold flex items-center gap-2">
                  <BarChart2 className="w-6 h-6" />
                  {t('analysis.technical.indicators_popup_title')}
                </h2>
                <p className="text-white/80 text-sm mt-1">
                  {t('analysis.technical.indicators_popup_subtitle', { count: getSelectedCount() })}
                </p>
              </div>
              <button
                onClick={() => setShowIndicatorPopup(false)}
                className="p-2 rounded-lg transition-colors"
                style={{ backgroundColor: 'rgba(255,255,255,0.2)', color: '#ffffff' }}
                title={t('analysis.technical.close_button')}
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            {/* Search Bar */}
            <div className="mt-4 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-white/60" />
              <input
                type="text"
                placeholder={t('analysis.technical.search_indicators_placeholder')}
                value={searchIndicator}
                onChange={(e) => setSearchIndicator(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-white/20 border border-white/30 rounded-xl text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-white/50"
              />
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-between px-4 py-2 bg-gray-50 border-b border-gray-200 flex-shrink-0">
            <div className="flex items-center gap-2">
              <button
                onClick={resetAllIndicators}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg transition-colors font-medium"
                style={{ backgroundColor: '#e5e7eb', color: '#374151', border: '1px solid #d1d5db' }}
              >
                <RotateCcw className="w-4 h-4" />
                {t('analysis.technical.reset_to_default_button')}
              </button>
            </div>
            <div className="text-sm" style={{ color: '#4b5563' }}>
              {t('analysis.technical.popup_hint')}
            </div>
          </div>

          {/* Categories and Indicators - Scrollable Area */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3" style={{ minHeight: 0 }}>
            {Object.entries(allIndicators).map(([categoryKey, category]) => {
              const filteredIndicators = filterIndicators(categoryKey);
              if (searchIndicator && filteredIndicators.length === 0) return null;

              const selectedCount = getCategorySelectedCount(categoryKey);
              const totalCount = Object.keys(category.indicators).length;

              return (
                <div key={categoryKey} className="border border-gray-200 rounded-xl overflow-hidden bg-white">
                  {/* Category Header */}
                  <div
                    className="flex items-center justify-between p-3 bg-gradient-to-r from-gray-50 to-gray-100 cursor-pointer hover:from-gray-100 hover:to-gray-200 transition-colors"
                    onClick={() => toggleCategory(categoryKey)}
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-2xl">{category.icon}</span>
                      <div>
                        <h3 className="font-semibold text-gray-800">{category.name}</h3>
                        <p className="text-xs text-gray-500">{category.description}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`text-sm px-2 py-0.5 rounded-full border ${selectedCount > 0 ? 'bg-blue-100 text-blue-700 border-blue-300' : 'bg-white text-gray-500 border-gray-200'}`}>
                        {selectedCount}/{totalCount}
                      </span>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={(e) => { e.stopPropagation(); selectAllInCategory(categoryKey); }}
                          className="px-2 py-1 text-xs rounded transition-colors font-medium"
                          style={{ backgroundColor: '#dbeafe', color: '#1d4ed8', border: '1px solid #93c5fd' }}
                        >
                          {t('analysis.technical.select_all_button')}
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); deselectAllInCategory(categoryKey); }}
                          className="px-2 py-1 text-xs rounded transition-colors font-medium"
                          style={{ backgroundColor: '#f3f4f6', color: '#374151', border: '1px solid #d1d5db' }}
                        >
                          {t('analysis.technical.select_none_button')}
                        </button>
                      </div>
                      <div className={`p-1 rounded transition-colors ${expandedCategories[categoryKey] ? 'bg-blue-100' : 'bg-gray-200'}`}>
                        {expandedCategories[categoryKey] ? (
                          <ChevronUp className="w-5 h-5 text-blue-600" />
                        ) : (
                          <ChevronDown className="w-5 h-5 text-gray-500" />
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Indicators Grid */}
                  {expandedCategories[categoryKey] && (
                    <div className="p-3 bg-white border-t border-gray-100">
                      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
                        {filteredIndicators.map(([indicatorKey, indicator]) => (
                          <label
                            key={indicatorKey}
                            className={`flex items-center gap-2 p-2.5 rounded-lg border cursor-pointer transition-all ${
                              indicator.enabled
                                ? 'bg-blue-50 border-blue-300 shadow-sm'
                                : 'bg-gray-50 border-gray-200 hover:bg-gray-100'
                            }`}
                          >
                            <input
                              type="checkbox"
                              checked={indicator.enabled}
                              onChange={() => toggleAllIndicator(categoryKey, indicatorKey)}
                              className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                            />
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-1.5">
                                {indicator.color && (
                                  <span
                                    className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                                    style={{ backgroundColor: indicator.color }}
                                  />
                                )}
                                <span className={`text-sm font-medium truncate ${indicator.enabled ? 'text-blue-700' : 'text-gray-700'}`}>
                                  {indicator.name}
                                </span>
                              </div>
                              <div className="flex items-center gap-1 mt-0.5">
                                <span className={`text-xs px-1.5 py-0.5 rounded ${
                                  indicator.type === 'overlay'
                                    ? 'bg-green-100 text-green-700'
                                    : indicator.type === 'candle'
                                    ? 'bg-orange-100 text-orange-700'
                                    : 'bg-purple-100 text-purple-700'
                                }`}>
                                  {indicator.type === 'overlay' ? t('analysis.technical.overlay_badge') : indicator.type === 'candle' ? t('analysis.technical.candle_badge') : t('analysis.technical.panel_badge')}
                                </span>
                              </div>
                            </div>
                            {indicator.enabled && (
                              <Check className="w-4 h-4 text-blue-600 flex-shrink-0" />
                            )}
                          </label>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Footer */}
          <div className="p-4 bg-gray-50 border-t border-gray-200 flex items-center justify-between flex-shrink-0 rounded-b-2xl">
            <div className="text-sm" style={{ color: '#4b5563' }}>
              {t('analysis.technical.indicators_count_label', { count: getSelectedCount() })}
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setShowIndicatorPopup(false)}
                className="px-5 py-2.5 rounded-lg transition-colors font-medium"
                style={{ backgroundColor: '#e5e7eb', color: '#374151', border: '1px solid #d1d5db' }}
              >
                {t('analysis.technical.close_button')}
              </button>
              <button
                onClick={applyIndicators}
                className="px-6 py-2.5 font-semibold rounded-lg transition-all shadow-md hover:shadow-lg"
                style={{ backgroundColor: '#4f46e5', color: '#ffffff' }}
              >
                {t('analysis.technical.apply_indicators_button')}
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // Financial Chart Component with zoom/pan
  const FinancialChart = () => {
    const rawData = prepareChartData();
    if (!rawData || rawData.length === 0) return <div>{t('analysis.technical.no_chart_data')}</div>;

    const priceOverlay = indicatorSettings.priceOverlay.indicators;
    const oscillators = indicatorSettings.oscillators.indicators;
    const momentum = indicatorSettings.momentum.indicators;
    const volumeIndicators = indicatorSettings.volume.indicators;

    // Calculate indicators
    const sma20Calculator = sma()
      .options({ windowSize: 20 })
      .merge((d, c) => { d.sma20 = c; })
      .accessor(d => d.sma20);

    const sma50Calculator = sma()
      .options({ windowSize: 50 })
      .merge((d, c) => { d.sma50 = c; })
      .accessor(d => d.sma50);

    const ema12Calculator = ema()
      .options({ windowSize: 12 })
      .merge((d, c) => { d.ema12 = c; })
      .accessor(d => d.ema12);

    const ema26Calculator = ema()
      .options({ windowSize: 26 })
      .merge((d, c) => { d.ema26 = c; })
      .accessor(d => d.ema26);

    const bbCalculator = bollingerBand()
      .options({ windowSize: 20, multiplier: 2 })
      .merge((d, c) => { d.bb = c; })
      .accessor(d => d.bb);

    const macdCalculator = macd()
      .options({ fast: 12, slow: 26, signal: 9 })
      .merge((d, c) => { d.macd = c; })
      .accessor(d => d.macd);

    const rsiCalculator = rsi()
      .options({ windowSize: 14 })
      .merge((d, c) => { d.rsi = c; })
      .accessor(d => d.rsi);

    const stochCalculator = stochasticOscillator()
      .options({ windowSize: 14, kWindowSize: 3, dWindowSize: 3 })
      .merge((d, c) => { d.stoch = c; })
      .accessor(d => d.stoch);

    // Apply all calculators
    let calculatedData = rawData;
    if (priceOverlay.sma20.enabled) calculatedData = sma20Calculator(calculatedData);
    if (priceOverlay.sma50.enabled) calculatedData = sma50Calculator(calculatedData);
    if (priceOverlay.ema12.enabled) calculatedData = ema12Calculator(calculatedData);
    if (priceOverlay.ema26.enabled) calculatedData = ema26Calculator(calculatedData);
    if (priceOverlay.bollingerBands.enabled) calculatedData = bbCalculator(calculatedData);
    if (momentum.macd.enabled) calculatedData = macdCalculator(calculatedData);
    if (oscillators.rsi.enabled) calculatedData = rsiCalculator(calculatedData);
    if (oscillators.stochastic.enabled) calculatedData = stochCalculator(calculatedData);

    // Calculate OBV
    let obv = 0;
    calculatedData = calculatedData.map((d, i) => {
      if (i > 0) {
        const prevClose = calculatedData[i - 1].close;
        if (d.close > prevClose) obv += d.volume;
        else if (d.close < prevClose) obv -= d.volume;
      }
      return { ...d, obv };
    });

    const ScaleProvider = discontinuousTimeScaleProviderBuilder()
      .inputDateAccessor(d => d.date);

    const { data, xScale, xAccessor, displayXAccessor } = ScaleProvider(calculatedData);

    const pricesDisplayFormat = format(".2f");
    const volumeFormat = format(".2s");
    const dateTimeFormat = "%d %b";
    const timeDisplayFormat = timeFormat(dateTimeFormat);

    const max = xAccessor(data[data.length - 1]);
    const min = xAccessor(data[Math.max(0, data.length - 100)]);
    const xExtents = [min, max + 5];

    const width = 1200;
    const margin = { left: 50, right: 70, top: 10, bottom: 30 };

    // Calculate heights based on visible panels
    const visiblePanels = Object.values(panels).filter(Boolean).length;
    const totalHeight = 600;
    const priceHeight = panels.price ? (visiblePanels === 1 ? totalHeight : totalHeight * 0.45) : 0;
    const oscillatorHeight = panels.oscillators ? 120 : 0;
    const macdHeight = panels.macd ? 120 : 0;
    const volumeHeight = panels.volume ? 100 : 0;
    const chartHeight = priceHeight + oscillatorHeight + macdHeight + volumeHeight + 50;

    // Calculate origins
    let currentY = priceHeight;
    const oscillatorOrigin = [0, currentY];
    currentY += oscillatorHeight;
    const macdOrigin = [0, currentY];
    currentY += macdHeight;
    const volumeOrigin = [0, currentY];

    // eslint-disable-next-line no-unused-vars -- preserved for the candle chart panel
    const candleChartExtents = d => [d.high, d.low];
    const volumeChartExtents = d => d.volume;

    const openCloseColor = d => d.close > d.open ? "#26a69a" : "#ef5350";
    const volumeColor = d => d.close > d.open ? "rgba(38, 166, 154, 0.5)" : "rgba(239, 83, 80, 0.5)";

    return (
      <ChartWrapper yAxisTitle={t('analysis.technical.price_axis_label')} xAxisTitle={t('analysis.technical.date_axis_label')}>
      <ChartCanvas
        height={chartHeight}
        ratio={2}
        width={width}
        margin={margin}
        data={data}
        displayXAccessor={displayXAccessor}
        seriesName="Technical"
        xScale={xScale}
        xAccessor={xAccessor}
        xExtents={xExtents}
        zoomAnchor={lastVisibleItemBasedZoomAnchor}
      >
        {/* Panel 1: Price Chart with Overlays */}
        {panels.price && (
          <Chart
            id={1}
            height={priceHeight}
            yExtents={d => {
              const extents = [d.high, d.low];
              if (d.bb) {
                extents.push(d.bb.top, d.bb.bottom);
              }
              return extents;
            }}
          >
            <XAxis showGridLines {...getXAxisProps()} />
            <YAxis showGridLines tickFormat={pricesDisplayFormat} {...getYAxisProps()} />

            <CandlestickSeries />

            {/* Bollinger Bands */}
            {priceOverlay.bollingerBands.enabled && (
              <BollingerSeries
                yAccessor={d => d.bb}
                strokeStyle={{
                  top: "#ef4444",
                  middle: "#6366f1",
                  bottom: "#ef4444"
                }}
                fillStyle="rgba(239, 68, 68, 0.1)"
              />
            )}

            {/* Moving Averages */}
            {priceOverlay.sma20.enabled && (
              <LineSeries yAccessor={d => d.sma20} strokeStyle={priceOverlay.sma20.color} strokeWidth={1} />
            )}
            {priceOverlay.sma50.enabled && (
              <LineSeries yAccessor={d => d.sma50} strokeStyle={priceOverlay.sma50.color} strokeWidth={1} />
            )}
            {priceOverlay.ema12.enabled && (
              <LineSeries yAccessor={d => d.ema12} strokeStyle={priceOverlay.ema12.color} strokeWidth={1} />
            )}
            {priceOverlay.ema26.enabled && (
              <LineSeries yAccessor={d => d.ema26} strokeStyle={priceOverlay.ema26.color} strokeWidth={1} />
            )}

            <MouseCoordinateY rectWidth={margin.right} displayFormat={pricesDisplayFormat} />
            <EdgeIndicator
              itemType="last"
              rectWidth={margin.right}
              fill={openCloseColor}
              lineStroke={openCloseColor}
              displayFormat={pricesDisplayFormat}
              yAccessor={d => d.close}
            />

            <OHLCTooltip origin={[8, 16]} />

            {priceOverlay.bollingerBands.enabled && (
              <BollingerBandTooltip
                origin={[8, 60]}
                yAccessor={d => d.bb}
                options={{ windowSize: 20, multiplier: 2 }}
                fill="#ef4444"
              />
            )}

            <MovingAverageTooltip
              origin={[8, 40]}
              options={[
                priceOverlay.sma20.enabled && { yAccessor: d => d.sma20, type: "SMA", stroke: priceOverlay.sma20.color, windowSize: 20 },
                priceOverlay.sma50.enabled && { yAccessor: d => d.sma50, type: "SMA", stroke: priceOverlay.sma50.color, windowSize: 50 },
                priceOverlay.ema12.enabled && { yAccessor: d => d.ema12, type: "EMA", stroke: priceOverlay.ema12.color, windowSize: 12 },
                priceOverlay.ema26.enabled && { yAccessor: d => d.ema26, type: "EMA", stroke: priceOverlay.ema26.color, windowSize: 26 },
              ].filter(Boolean)}
            />

            <ZoomButtons />
          </Chart>
        )}

        {/* Panel 2: Oscillators (RSI + Stochastic) - Bounded 0-100 */}
        {panels.oscillators && (oscillators.rsi.enabled || oscillators.stochastic.enabled) && (
          <Chart
            id={2}
            height={oscillatorHeight}
            yExtents={[0, 100]}
            origin={oscillatorOrigin}
            padding={{ top: 10, bottom: 10 }}
          >
            <XAxis showGridLines {...getXAxisProps()} />
            <YAxis tickValues={[30, 50, 70]} tickFormat={d => d} {...getYAxisProps()} />

            {/* Overbought/Oversold lines */}
            <StraightLine yValue={70} strokeStyle="#ef4444" strokeDasharray="Dash" />
            <StraightLine yValue={30} strokeStyle="#10b981" strokeDasharray="Dash" />
            <StraightLine yValue={50} strokeStyle="#9ca3af" strokeDasharray="Dot" />

            {oscillators.rsi.enabled && (
              <>
                <RSISeries yAccessor={d => d.rsi} strokeStyle={{ line: oscillators.rsi.color }} />
                <SingleValueTooltip
                  yAccessor={d => d.rsi}
                  yLabel={t('analysis.technical.rsi_tooltip_label')}
                  yDisplayFormat={format(".2f")}
                  origin={[8, 16]}
                />
              </>
            )}

            {oscillators.stochastic.enabled && (
              <>
                <StochasticSeries
                  yAccessor={d => d.stoch}
                  strokeStyle={{
                    kLine: oscillators.stochastic.colorK,
                    dLine: oscillators.stochastic.colorD
                  }}
                />
                <SingleValueTooltip
                  yAccessor={d => d.stoch?.K}
                  yLabel={t('analysis.technical.stoch_k_tooltip_label')}
                  yDisplayFormat={format(".2f")}
                  origin={[8, oscillators.rsi.enabled ? 36 : 16]}
                />
              </>
            )}

            <MouseCoordinateY rectWidth={margin.right} displayFormat={format(".0f")} />
          </Chart>
        )}

        {/* Panel 3: MACD - Centered on Zero */}
        {panels.macd && momentum.macd.enabled && (
          <Chart
            id={3}
            height={macdHeight}
            yExtents={d => d.macd}
            origin={macdOrigin}
            padding={{ top: 10, bottom: 10 }}
          >
            <XAxis showGridLines {...getXAxisProps()} />
            <YAxis tickFormat={pricesDisplayFormat} {...getYAxisProps()} />

            <MACDSeries
              yAccessor={d => d.macd}
              strokeStyle={{
                macd: "#2563eb",
                signal: "#ef4444"
              }}
              fillStyle={{
                divergence: "#8b5cf6"
              }}
            />

            <SingleValueTooltip
              yAccessor={d => d.macd?.MACD}
              yLabel={t('analysis.technical.macd_tooltip_label')}
              yDisplayFormat={pricesDisplayFormat}
              origin={[8, 16]}
            />
            <SingleValueTooltip
              yAccessor={d => d.macd?.signal}
              yLabel={t('analysis.technical.signal_tooltip_label')}
              yDisplayFormat={pricesDisplayFormat}
              origin={[80, 16]}
            />

            <MouseCoordinateY rectWidth={margin.right} displayFormat={pricesDisplayFormat} />
          </Chart>
        )}

        {/* Panel 4: Volume */}
        {panels.volume && volumeIndicators.volume.enabled && (
          <Chart
            id={4}
            height={volumeHeight}
            yExtents={volumeChartExtents}
            origin={volumeOrigin}
            padding={{ top: 10, bottom: 10 }}
          >
            <XAxis showGridLines {...getXAxisProps()} />
            <YAxis tickFormat={volumeFormat} {...getYAxisProps()} />

            <BarSeries fillStyle={volumeColor} yAccessor={d => d.volume} />

            {volumeIndicators.obv.enabled && (
              <LineSeries
                yAccessor={d => d.obv}
                strokeStyle={volumeIndicators.obv.color}
                strokeWidth={1}
              />
            )}

            <MouseCoordinateX displayFormat={timeDisplayFormat} />
            <MouseCoordinateY rectWidth={margin.right} displayFormat={volumeFormat} />

            <SingleValueTooltip
              yAccessor={d => d.volume}
              yLabel={t('analysis.technical.volume_tooltip_label')}
              yDisplayFormat={volumeFormat}
              origin={[8, 16]}
            />
          </Chart>
        )}

        <CrossHairCursor />
      </ChartCanvas>
      </ChartWrapper>
    );
  };

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-lg font-bold text-gray-900">{t('analysis.technical.title')}</h1>

        {/* Stock Search */}
        <div className="relative">
          <div className="flex items-center bg-white border border-gray-300 rounded-lg px-3 py-2 focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500">
            <Search className="w-5 h-5 text-gray-400 mr-2" />
            <input
              type="text"
              placeholder={t('analysis.search_placeholder')}
              value={searchQuery}
              onChange={handleSearchChange}
              onFocus={() => searchQuery && setShowResults(true)}
              onBlur={() => setTimeout(() => setShowResults(false), 300)}
              className="outline-none flex-1 min-w-0 w-64"
            />
          </div>

          {showResults && (
            <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-300 rounded-lg shadow-lg z-50 max-h-60 overflow-y-auto">
              {isSearching ? (
                <div className="p-3 text-center text-gray-500">{t('analysis.searching')}</div>
              ) : searchResults.length > 0 ? (
                searchResults.map((stock) => (
                  <button
                    key={stock.symbol}
                    className="w-full text-left px-3 py-2 hover:bg-gray-50 border-b border-gray-100 last:border-b-0"
                    onMouseDown={(e) => {
                      e.preventDefault();
                      handleStockSelect(stock);
                    }}
                  >
                    <div className="flex justify-between items-center">
                      <div>
                        <div className="font-semibold text-gray-900">{stock.symbol}</div>
                        <div className="text-sm text-gray-600">{stock.name}</div>
                      </div>
                      <div className="font-semibold text-blue-600">${stock.price}</div>
                    </div>
                  </button>
                ))
              ) : (
                <div className="p-3 text-center text-gray-500">{t('analysis.no_results')}</div>
              )}
            </div>
          )}
        </div>
      </div>

      {!selectedSymbol ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
          <AlertCircle className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-700 mb-2">{t('analysis.technical.no_selection_title')}</h2>
          <p className="text-gray-500">
            {t('analysis.technical.no_selection_message')}
          </p>
        </div>
      ) : loading ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">{t('analysis.technical.loading_message', { symbol: selectedSymbol })}</p>
        </div>
      ) : error ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-700 mb-2">{t('analysis.technical.error_title')}</h2>
          <p className="text-gray-500">{error}</p>
          <button
            onClick={() => fetchTechnicalAnalysis(selectedSymbol)}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            {t('analysis.common.retry_button')}
          </button>
        </div>
      ) : analysisData ? (
        <div className="space-y-4">
          {/* Header with Symbol, Period, Tab Controls, and Settings */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-4">
                <h2 className="text-lg font-bold text-gray-900">{selectedSymbol}</h2>
                {/* Tab Controls */}
                <div className="flex items-center rounded-2xl p-1.5" style={{ background: 'linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%)', boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.06)' }}>
                  <button
                    onClick={() => setActiveTab('indicators')}
                    className="flex items-center space-x-2 px-5 py-2 text-sm font-semibold rounded-xl transition-all duration-300"
                    style={activeTab === 'indicators'
                      ? { background: 'linear-gradient(135deg, #8b5cf6 0%, #9333ea 100%)', color: '#ffffff', boxShadow: '0 4px 15px rgba(139, 92, 246, 0.4)', transform: 'scale(1.02)' }
                      : { background: 'transparent', color: '#4b5563' }
                    }
                  >
                    <Zap className={`w-4 h-4 ${activeTab === 'indicators' ? 'animate-pulse' : ''}`} />
                    <span>{t('analysis.technical.indicators_tab')}</span>
                  </button>
                  <button
                    onClick={() => setActiveTab('charts')}
                    className="flex items-center space-x-2 px-5 py-2 text-sm font-semibold rounded-xl transition-all duration-300"
                    style={activeTab === 'charts'
                      ? { background: 'linear-gradient(135deg, #06b6d4 0%, #2563eb 100%)', color: '#ffffff', boxShadow: '0 4px 15px rgba(6, 182, 212, 0.4)', transform: 'scale(1.02)' }
                      : { background: 'transparent', color: '#4b5563' }
                    }
                  >
                    <LineChart className={`w-4 h-4 ${activeTab === 'charts' ? 'animate-pulse' : ''}`} />
                    <span>{t('analysis.technical.charts_tab')}</span>
                  </button>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <select
                  value={period}
                  onChange={(e) => setPeriod(Number(e.target.value))}
                  className="px-2 py-1 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value={30}>{t('analysis.technical.period_30_days')}</option>
                  <option value={60}>{t('analysis.technical.period_60_days')}</option>
                  <option value={100}>{t('analysis.technical.period_100_days')}</option>
                  <option value={200}>{t('analysis.technical.period_200_days')}</option>
                </select>
                {activeTab === 'charts' && (
                  <>
                    <button
                      onClick={() => setShowIndicatorPopup(true)}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg transition-all shadow-sm hover:shadow-md"
                      style={{ backgroundColor: '#4f46e5', color: '#ffffff' }}
                    >
                      <BarChart2 className="w-4 h-4" />
                      {t('analysis.technical.indicators_button')}
                      <span
                        className="px-1.5 py-0.5 rounded text-xs font-bold"
                        style={{ backgroundColor: '#e0e7ff', color: '#3730a3' }}
                      >
                        {getSelectedCount()}
                      </span>
                    </button>
                    <button
                      onClick={() => setShowSettings(!showSettings)}
                      className={`p-2 rounded-lg transition-colors ${showSettings ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
                    >
                      <Settings className="w-5 h-5" />
                    </button>
                  </>
                )}
              </div>
            </div>

            {/* Current Price Summary */}
            <table className="w-full text-sm">
              <tbody>
                <tr className="border-b border-gray-100">
                  <td className="py-2 text-gray-500 w-1/6">{t('analysis.technical.price_label')}</td>
                  <td className="py-2 font-semibold text-blue-600 w-1/6">{formatCurrency(analysisData.current_price?.price)}</td>
                  <td className="py-2 text-gray-500 w-1/6">{t('analysis.technical.volume_label')}</td>
                  <td className="py-2 font-semibold w-1/6">{formatVolume(analysisData.current_price?.volume)}</td>
                  <td className="py-2 text-gray-500 w-1/6">{t('analysis.technical.open_label')}</td>
                  <td className="py-2 font-semibold w-1/6">{formatCurrency(analysisData.current_price?.open)}</td>
                </tr>
                <tr>
                  <td className="py-2 text-gray-500">{t('analysis.technical.high_label')}</td>
                  <td className="py-2 font-semibold text-green-600">{formatCurrency(analysisData.current_price?.high)}</td>
                  <td className="py-2 text-gray-500">{t('analysis.technical.low_label')}</td>
                  <td className="py-2 font-semibold text-red-600">{formatCurrency(analysisData.current_price?.low)}</td>
                  <td className="py-2"></td>
                  <td className="py-2"></td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Indicators Tab Content */}
          {activeTab === 'indicators' && (
            <div className="space-y-4">
              {/* Trading Recommendation */}
              {analysisData.trading_analysis && (
                <div className={`rounded-xl shadow-sm border border-gray-200 p-4 ${getSignalBgColor(analysisData.trading_analysis.recommendation)}`}>
                  <div className="flex items-center justify-between mb-3">
                    <h2 className="text-sm font-bold text-gray-900">{t('analysis.technical.trading_analysis_title')}</h2>
                    <div className="flex items-center space-x-2">
                      {getRecommendationIcon(analysisData.trading_analysis.recommendation)}
                      <span className={`text-lg font-bold ${getSignalColor(analysisData.trading_analysis.recommendation)}`}>
                        {analysisData.trading_analysis.recommendation}
                      </span>
                      <span className="text-xs text-gray-500">
                        (Điểm: {analysisData.trading_analysis.score > 0 ? '+' : ''}{analysisData.trading_analysis.score})
                      </span>
                    </div>
                  </div>
                  <table className="w-full text-sm">
                    <tbody>
                      {(() => {
                        const signals = analysisData.trading_analysis.signals || [];
                        const rows = [];
                        for (let i = 0; i < signals.length; i += 3) {
                          rows.push(
                            <tr key={i} className={i < signals.length - 3 ? "border-b border-gray-200" : ""}>
                              {[0, 1, 2].map(offset => {
                                const signal = signals[i + offset];
                                if (!signal) return <td key={offset} className="py-2 w-1/6"></td>;
                                return (
                                  <React.Fragment key={offset}>
                                    <td className="py-2 text-gray-500 w-1/6">{signal.indicator}</td>
                                    <td className={`py-2 font-semibold w-1/6 ${getSignalColor(signal.signal)}`}>
                                      {signal.signal} {signal.value !== undefined && <span className="text-gray-400 text-xs">({typeof signal.value === 'number' ? formatNumber(signal.value) : signal.value})</span>}
                                    </td>
                                  </React.Fragment>
                                );
                              })}
                            </tr>
                          );
                        }
                        return rows;
                      })()}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Technical Indicators */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
                <h3 className="text-sm font-bold text-gray-900 mb-3 flex items-center">
                  <Zap className="w-4 h-4 mr-2" />
                  {t('analysis.technical.indicators_title')}
                </h3>
                <table className="w-full text-sm">
                  <tbody>
                    <tr className="border-b border-gray-100">
                      <td className="py-2 text-gray-500 w-1/6">{t('analysis.technical.rsi_label')}</td>
                      <td className="py-2 font-semibold w-1/6">{formatNumber(analysisData.momentum_indicators?.RSI)} <span className="text-xs text-gray-400">({analysisData.momentum_indicators?.RSI > 70 ? 'OB' : analysisData.momentum_indicators?.RSI < 30 ? 'OS' : 'N'})</span></td>
                      <td className="py-2 text-gray-500 w-1/6">{t('analysis.technical.macd_label')}</td>
                      <td className="py-2 font-semibold w-1/6">{formatNumber(analysisData.momentum_indicators?.MACD)} <span className="text-xs text-gray-400">({analysisData.momentum_indicators?.MACD > analysisData.momentum_indicators?.MACD_Signal ? 'Bull' : 'Bear'})</span></td>
                      <td className="py-2 text-gray-500 w-1/6">{t('analysis.technical.stoch_k_label')}</td>
                      <td className="py-2 font-semibold w-1/6">{formatNumber(analysisData.momentum_indicators?.Stoch_K)} <span className="text-xs text-gray-400">({analysisData.momentum_indicators?.Stoch_K > 80 ? 'OB' : analysisData.momentum_indicators?.Stoch_K < 20 ? 'OS' : 'N'})</span></td>
                    </tr>
                    <tr>
                      <td className="py-2 text-gray-500">{t('analysis.technical.sma20_label')}</td>
                      <td className="py-2 font-semibold">{formatCurrency(analysisData.moving_averages?.SMA_20)} <span className="text-xs text-gray-400">({analysisData.current_price?.price > analysisData.moving_averages?.SMA_20 ? '↑' : '↓'})</span></td>
                      <td className="py-2 text-gray-500">{t('analysis.technical.sma50_label')}</td>
                      <td className="py-2 font-semibold">{formatCurrency(analysisData.moving_averages?.SMA_50)} <span className="text-xs text-gray-400">({analysisData.current_price?.price > analysisData.moving_averages?.SMA_50 ? '↑' : '↓'})</span></td>
                      <td className="py-2 text-gray-500">{t('analysis.technical.sma200_label')}</td>
                      <td className="py-2 font-semibold">{formatCurrency(analysisData.moving_averages?.SMA_200)} <span className="text-xs text-gray-400">({analysisData.current_price?.price > analysisData.moving_averages?.SMA_200 ? '↑' : '↓'})</span></td>
                    </tr>
                  </tbody>
                </table>
              </div>

              {/* Support, Resistance & Fibonacci */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
                <h3 className="text-sm font-bold text-gray-900 mb-3 flex items-center">
                  <Target className="w-4 h-4 mr-2" />
                  {t('analysis.technical.support_resistance_title')}
                </h3>
                <table className="w-full text-sm">
                  <tbody>
                    {(() => {
                      const resistance = analysisData.support_resistance?.resistance_levels || [];
                      const support = analysisData.support_resistance?.support_levels || [];
                      const fib = Object.entries(analysisData.fibonacci_levels || {});
                      const maxRows = Math.max(resistance.length, support.length, Math.ceil(fib.length / 2));
                      const rows = [];
                      for (let i = 0; i < maxRows; i++) {
                        rows.push(
                          <tr key={i} className={i < maxRows - 1 ? "border-b border-gray-100" : ""}>
                            <td className="py-2 text-gray-500 w-1/6">{resistance[i] !== undefined ? `R${i + 1}` : ''}</td>
                            <td className="py-2 font-semibold text-red-600 w-1/6">{resistance[i] !== undefined ? formatCurrency(resistance[i]) : ''}</td>
                            <td className="py-2 text-gray-500 w-1/6">{support[i] !== undefined ? `S${i + 1}` : ''}</td>
                            <td className="py-2 font-semibold text-green-600 w-1/6">{support[i] !== undefined ? formatCurrency(support[i]) : ''}</td>
                            <td className="py-2 text-gray-500 w-1/6">{fib[i] ? fib[i][0] : ''}</td>
                            <td className="py-2 font-semibold text-purple-600 w-1/6">{fib[i] ? formatCurrency(fib[i][1]) : ''}</td>
                          </tr>
                        );
                      }
                      return rows;
                    })()}
                  </tbody>
                </table>
              </div>

              {/* Volatility & Volume Indicators */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
                <h3 className="text-sm font-bold text-gray-900 mb-3 flex items-center">
                  <Activity className="w-4 h-4 mr-2" />
                  {t('analysis.technical.volatility_volume_title')}
                </h3>
                <table className="w-full text-sm">
                  <tbody>
                    <tr className="border-b border-gray-100">
                      <td className="py-2 text-gray-500 w-1/6">{t('analysis.technical.bb_upper_label')}</td>
                      <td className="py-2 font-semibold text-blue-600 w-1/6">{formatCurrency(analysisData.volatility_indicators?.BB_Upper)}</td>
                      <td className="py-2 text-gray-500 w-1/6">{t('analysis.technical.bb_middle_label')}</td>
                      <td className="py-2 font-semibold w-1/6">{formatCurrency(analysisData.volatility_indicators?.BB_Middle)}</td>
                      <td className="py-2 text-gray-500 w-1/6">{t('analysis.technical.bb_lower_label')}</td>
                      <td className="py-2 font-semibold text-blue-600 w-1/6">{formatCurrency(analysisData.volatility_indicators?.BB_Lower)}</td>
                    </tr>
                    <tr>
                      <td className="py-2 text-gray-500">{t('analysis.technical.atr_label')}</td>
                      <td className="py-2 font-semibold text-purple-600">{formatNumber(analysisData.volatility_indicators?.ATR)}</td>
                      <td className="py-2 text-gray-500">{t('analysis.technical.obv_label')}</td>
                      <td className="py-2 font-semibold text-yellow-600">{formatVolume(analysisData.volume_indicators?.OBV)}</td>
                      <td className="py-2 text-gray-500">{t('analysis.technical.avg_vol_20_label')}</td>
                      <td className="py-2 font-semibold text-green-600">{formatVolume(analysisData.volume_indicators?.volume_avg_20)}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Charts Tab Content */}
          {activeTab === 'charts' && (
            <div className="space-y-4">
              {/* Settings Panel */}
              {showSettings && <SettingsPanel />}

              {/* Financial Chart */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 overflow-x-auto">
                <div className="min-w-[1200px]">
                  <FinancialChart />
                </div>
              </div>

              {/* Chart Legend */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
                <h3 className="text-sm font-bold text-gray-900 mb-3">{t('analysis.technical.chart_legend_title')}</h3>
                <div className="flex flex-wrap gap-4 text-sm">
                  {panels.price && (
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-700">{t('analysis.technical.price_panel_label')}</span>
                      {indicatorSettings.priceOverlay.indicators.sma20.enabled && (
                        <span className="flex items-center"><span className="w-3 h-0.5 bg-blue-600 mr-1"></span>{t('analysis.technical.sma20_short')}</span>
                      )}
                      {indicatorSettings.priceOverlay.indicators.sma50.enabled && (
                        <span className="flex items-center"><span className="w-3 h-0.5 bg-amber-500 mr-1"></span>{t('analysis.technical.sma50_short')}</span>
                      )}
                      {indicatorSettings.priceOverlay.indicators.bollingerBands.enabled && (
                        <span className="flex items-center"><span className="w-3 h-0.5 bg-red-500 mr-1"></span>{t('analysis.technical.bb_short')}</span>
                      )}
                    </div>
                  )}
                  {panels.oscillators && (
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-700">{t('analysis.technical.oscillators_panel_label')}</span>
                      {indicatorSettings.oscillators.indicators.rsi.enabled && (
                        <span className="flex items-center"><span className="w-3 h-0.5 bg-indigo-500 mr-1"></span>{t('analysis.technical.rsi_short')}</span>
                      )}
                      {indicatorSettings.oscillators.indicators.stochastic.enabled && (
                        <span className="flex items-center"><span className="w-3 h-0.5 bg-blue-600 mr-1"></span>{t('analysis.technical.stoch_short')}</span>
                      )}
                    </div>
                  )}
                  {panels.macd && (
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-700">{t('analysis.technical.macd_panel_label')}</span>
                      <span className="flex items-center"><span className="w-3 h-0.5 bg-blue-600 mr-1"></span>{t('analysis.technical.macd_short')}</span>
                      <span className="flex items-center"><span className="w-3 h-0.5 bg-red-500 mr-1"></span>{t('analysis.technical.signal_short')}</span>
                    </div>
                  )}
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  {t('analysis.technical.chart_hint')}
                </p>
              </div>
            </div>
          )}
        </div>
      ) : null}

      {/* Indicator Selection Popup */}
      <IndicatorSelectionPopup />
    </div>
  );
};
