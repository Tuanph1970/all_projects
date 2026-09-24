import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { analysisAPI } from '../../services/api';
import useUserTickers from '../../hooks/useUserTickers';
import { AlertCircle, TrendingUp, TrendingDown, Activity, BarChart2, LineChart, Target, Zap, ChevronDown } from 'lucide-react';
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

// ─── Series config for the checkbox dropdown ────────────────────────────────
const SERIES_CONFIG = [
  { key:'candles',    name:'Nến giá',        color:'#26a69a', group:'Giá' },
  { key:'sma20',      name:'SMA 20',          color:'#2563eb', group:'Giá' },
  { key:'sma50',      name:'SMA 50',          color:'#f59e0b', group:'Giá' },
  { key:'ema12',      name:'EMA 12',          color:'#10b981', group:'Giá' },
  { key:'ema26',      name:'EMA 26',          color:'#8b5cf6', group:'Giá' },
  { key:'bb',         name:'Bollinger Bands', color:'#ef4444', group:'Giá' },
  { key:'rsi',        name:'RSI 14',          color:'#6366f1', group:'Dao động (trục phải)' },
  { key:'stochastic', name:'Stochastic',      color:'#ec4899', group:'Dao động (trục phải)' },
  { key:'macd',       name:'MACD',            color:'#2563eb', group:'Bảng phụ' },
  { key:'volume',     name:'Volume',          color:'#64748b', group:'Khối lượng' },
  { key:'obv',        name:'OBV',             color:'#f59e0b', group:'Khối lượng' },
];


export const TechnicalAnalysis = () => {
  const { t } = useTranslation();
  const [selectedSymbol, setSelectedSymbol] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [analysisData, setAnalysisData] = useState(null);
  const [period, setPeriod] = useState(100);
  const [activeTab, setActiveTab] = useState('charts');

  // Which series are visible in the chart
  const [seriesVisible, setSeriesVisible] = useState({
    candles: true, sma20: true, sma50: true, ema12: false, ema26: false,
    bb: true, rsi: true, stochastic: true, macd: true, volume: true, obv: false,
  });
  const [dropdownOpen, setDropdownOpen] = useState(false);

  // Ticker dropdown options (watchlist + portfolio holdings)
  const { tickers: tickerOptions, loading: tickersLoading } = useUserTickers();

  const fetchTechnicalAnalysis = useCallback(async (symbol, p) => {
    setLoading(true);
    setError(null);
    try {
      const data = await analysisAPI.getTechnicalAnalysis(symbol, p);
      setAnalysisData(data);
    } catch (err) {
      setError('Failed to fetch technical analysis data: ' + err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedSymbol && period) {
      fetchTechnicalAnalysis(selectedSymbol, period);
    }
  }, [period, selectedSymbol, fetchTechnicalAnalysis]);

  const formatNumber = (value) => {
    if (value === null || value === undefined) return 'N/A';
    return value.toFixed(2);
  };

  const formatCurrency = (value) => {
    if (!value) return 'N/A';
    return `${value.toFixed(2)} VND`;
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

  // Series checkbox dropdown
  const SeriesDropdown = () => {
    const groups = {};
    SERIES_CONFIG.forEach(s => {
      if (!groups[s.group]) groups[s.group] = [];
      groups[s.group].push(s);
    });
    const count = Object.values(seriesVisible).filter(Boolean).length;
    return (
      <div className="relative">
        <button
          onClick={() => setDropdownOpen(o => !o)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg border border-gray-300 bg-white hover:bg-gray-50"
        >
          <BarChart2 className="w-4 h-4 text-gray-600" />
          <span>{t('analysis.technical.indicators_button')}</span>
          <span className="px-1.5 py-0.5 rounded text-xs font-bold bg-blue-100 text-blue-700">{count}</span>
          <ChevronDown className="w-3 h-3 text-gray-400" />
        </button>
        {dropdownOpen && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setDropdownOpen(false)} />
            <div className="absolute right-0 top-full mt-1 bg-white border border-gray-200 rounded-xl shadow-xl z-50 min-w-[220px] p-2">
              {Object.entries(groups).map(([grp, items]) => (
                <div key={grp} className="mb-1">
                  <div className="text-xs font-semibold text-gray-400 uppercase tracking-wide px-2 py-1">{grp}</div>
                  {items.map(s => (
                    <label key={s.key} className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-gray-50 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={!!seriesVisible[s.key]}
                        onChange={() => setSeriesVisible(p => ({ ...p, [s.key]: !p[s.key] }))}
                        className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: s.color }} />
                      <span className="text-sm text-gray-700">{s.name}</span>
                    </label>
                  ))}
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    );
  };

  // Financial Chart — dual Y-axis, inverted volume overlay, optional MACD sub-panel
  const FinancialChart = () => {
    const rawData = prepareChartData();
    if (!rawData || rawData.length === 0) return <div className="text-center py-8 text-gray-500">{t('analysis.technical.no_chart_data')}</div>;

    // Build indicator calculators
    const sma20Calc = sma().options({ windowSize: 20 }).merge((d, c) => { d.sma20 = c; }).accessor(d => d.sma20);
    const sma50Calc = sma().options({ windowSize: 50 }).merge((d, c) => { d.sma50 = c; }).accessor(d => d.sma50);
    const ema12Calc = ema().options({ windowSize: 12 }).merge((d, c) => { d.ema12 = c; }).accessor(d => d.ema12);
    const ema26Calc = ema().options({ windowSize: 26 }).merge((d, c) => { d.ema26 = c; }).accessor(d => d.ema26);
    const bbCalc    = bollingerBand().options({ windowSize: 20, multiplier: 2 }).merge((d, c) => { d.bb = c; }).accessor(d => d.bb);
    const macdCalc  = macd().options({ fast: 12, slow: 26, signal: 9 }).merge((d, c) => { d.macdVal = c; }).accessor(d => d.macdVal);
    const rsiCalc   = rsi().options({ windowSize: 14 }).merge((d, c) => { d.rsiVal = c; }).accessor(d => d.rsiVal);
    const stochCalc = stochasticOscillator().options({ windowSize: 14, kWindowSize: 3, dWindowSize: 3 }).merge((d, c) => { d.stoch = c; }).accessor(d => d.stoch);

    let calcData = rawData;
    if (seriesVisible.sma20) calcData = sma20Calc(calcData);
    if (seriesVisible.sma50) calcData = sma50Calc(calcData);
    if (seriesVisible.ema12) calcData = ema12Calc(calcData);
    if (seriesVisible.ema26) calcData = ema26Calc(calcData);
    if (seriesVisible.bb)    calcData = bbCalc(calcData);
    if (seriesVisible.macd)  calcData = macdCalc(calcData);
    if (seriesVisible.rsi)   calcData = rsiCalc(calcData);
    if (seriesVisible.stochastic) calcData = stochCalc(calcData);

    // OBV (always computed so it's ready if toggled on)
    let obvAcc = 0;
    calcData = calcData.map((d, i) => {
      if (i > 0) {
        const prev = calcData[i - 1];
        if (d.close > prev.close) obvAcc += d.volume;
        else if (d.close < prev.close) obvAcc -= d.volume;
      }
      return { ...d, obv: obvAcc };
    });

    const ScaleProvider = discontinuousTimeScaleProviderBuilder().inputDateAccessor(d => d.date);
    const { data, xScale, xAccessor, displayXAccessor } = ScaleProvider(calcData);

    const pricesDisplayFormat = format(".2f");
    const volumeFormat = format(".2s");
    const timeDisplayFormat = timeFormat("%d %b");

    const max = xAccessor(data[data.length - 1]);
    const min = xAccessor(data[Math.max(0, data.length - 100)]);
    const xExtents = [min, max + 5];

    const width = 1200;
    const margin = { left: 50, right: 70, top: 10, bottom: 30 };
    const mainHeight = 500;   // price panel — volume overlay sits inside bottom portion
    const volHeight  = 80;    // inverted volume bars occupy bottom volHeight px of mainHeight
    const macdH      = seriesVisible.macd ? 130 : 0;
    const totalH     = mainHeight + macdH;

    const openCloseColor = d => d.close > d.open ? "#26a69a" : "#ef5350";
    const volumeColor    = d => d.close > d.open ? "rgba(38,166,154,0.35)" : "rgba(239,83,80,0.35)";
    const hasOscillator  = seriesVisible.rsi || seriesVisible.stochastic;

    return (
      <ChartWrapper yAxisTitle={t('analysis.technical.price_axis_label')} xAxisTitle={t('analysis.technical.date_axis_label')}>
        <ChartCanvas
          height={totalH}
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
          {/* Chart 1: Price scale — left Y-axis */}
          <Chart
            id={1}
            height={mainHeight}
            yExtents={d => {
              const ext = [d.high, d.low];
              if (seriesVisible.bb && d.bb) ext.push(d.bb.top, d.bb.bottom);
              return ext;
            }}
          >
            <XAxis showGridLines {...getXAxisProps({ showTickLabel: !seriesVisible.macd })} />
            <YAxis showGridLines axisAt="left" orient="left" tickFormat={pricesDisplayFormat} {...getYAxisProps()} />

            {seriesVisible.candles && <CandlestickSeries />}
            {seriesVisible.bb && (
              <BollingerSeries
                yAccessor={d => d.bb}
                strokeStyle={{ top: "#ef4444", middle: "#6366f1", bottom: "#ef4444" }}
                fillStyle="rgba(239,68,68,0.08)"
              />
            )}
            {seriesVisible.sma20 && <LineSeries yAccessor={d => d.sma20} strokeStyle="#2563eb" strokeWidth={1} />}
            {seriesVisible.sma50 && <LineSeries yAccessor={d => d.sma50} strokeStyle="#f59e0b" strokeWidth={1} />}
            {seriesVisible.ema12 && <LineSeries yAccessor={d => d.ema12} strokeStyle="#10b981" strokeWidth={1} />}
            {seriesVisible.ema26 && <LineSeries yAccessor={d => d.ema26} strokeStyle="#8b5cf6" strokeWidth={1} />}

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
            {seriesVisible.bb && (
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
                seriesVisible.sma20 && { yAccessor: d => d.sma20, type: "SMA", stroke: "#2563eb", windowSize: 20 },
                seriesVisible.sma50 && { yAccessor: d => d.sma50, type: "SMA", stroke: "#f59e0b", windowSize: 50 },
                seriesVisible.ema12 && { yAccessor: d => d.ema12, type: "EMA", stroke: "#10b981", windowSize: 12 },
                seriesVisible.ema26 && { yAccessor: d => d.ema26, type: "EMA", stroke: "#8b5cf6", windowSize: 26 },
              ].filter(Boolean)}
            />
            <ZoomButtons />
            {!seriesVisible.macd && <MouseCoordinateX displayFormat={timeDisplayFormat} />}
          </Chart>

          {/* Chart 2: Oscillators 0-100 — right Y-axis, overlaid on price panel */}
          {hasOscillator && (
            <Chart id={2} height={mainHeight} yExtents={[0, 100]}>
              <YAxis axisAt="right" orient="right" tickValues={[20, 50, 80]} tickFormat={d => d} {...getYAxisProps()} />
              <StraightLine yValue={80} strokeStyle="rgba(239,68,68,0.35)" strokeDasharray="Dash" />
              <StraightLine yValue={20} strokeStyle="rgba(16,185,129,0.35)" strokeDasharray="Dash" />
              <StraightLine yValue={50} strokeStyle="rgba(156,163,175,0.3)" strokeDasharray="Dot" />
              {seriesVisible.rsi && (
                <>
                  <RSISeries yAccessor={d => d.rsiVal} strokeStyle={{ line: "#6366f1" }} />
                  <SingleValueTooltip
                    yAccessor={d => d.rsiVal}
                    yLabel={t('analysis.technical.rsi_tooltip_label')}
                    yDisplayFormat={format(".1f")}
                    origin={[8, 16]}
                  />
                </>
              )}
              {seriesVisible.stochastic && (
                <>
                  <StochasticSeries yAccessor={d => d.stoch} strokeStyle={{ kLine: "#ec4899", dLine: "#f97316" }} />
                  <SingleValueTooltip
                    yAccessor={d => d.stoch?.K}
                    yLabel={t('analysis.technical.stoch_k_tooltip_label')}
                    yDisplayFormat={format(".1f")}
                    origin={[8, seriesVisible.rsi ? 36 : 16]}
                  />
                </>
              )}
            </Chart>
          )}

          {/* Chart 3: Volume inverted at bottom of price panel (bars hang downward) */}
          {seriesVisible.volume && (
            <Chart
              id={3}
              height={volHeight}
              origin={[0, mainHeight - volHeight]}
              yExtents={d => [0, d.volume]}
            >
              <BarSeries fillStyle={volumeColor} yAccessor={d => d.volume} />
              {seriesVisible.obv && (
                <LineSeries yAccessor={d => d.obv} strokeStyle="#f59e0b" strokeWidth={1} />
              )}
              <SingleValueTooltip
                yAccessor={d => d.volume}
                yLabel={t('analysis.technical.volume_tooltip_label')}
                yDisplayFormat={volumeFormat}
                origin={[8, 4]}
              />
            </Chart>
          )}

          {/* Chart 4: MACD sub-panel below price */}
          {seriesVisible.macd && (
            <Chart
              id={4}
              height={macdH - 10}
              origin={[0, mainHeight]}
              yExtents={d => d.macdVal}
              padding={{ top: 10, bottom: 10 }}
            >
              <XAxis showGridLines {...getXAxisProps()} />
              <YAxis axisAt="left" orient="left" tickFormat={pricesDisplayFormat} {...getYAxisProps()} />
              <MACDSeries
                yAccessor={d => d.macdVal}
                strokeStyle={{ macd: "#2563eb", signal: "#ef4444" }}
                fillStyle={{ divergence: "#8b5cf6" }}
              />
              <SingleValueTooltip
                yAccessor={d => d.macdVal?.MACD}
                yLabel={t('analysis.technical.macd_tooltip_label')}
                yDisplayFormat={pricesDisplayFormat}
                origin={[8, 16]}
              />
              <SingleValueTooltip
                yAccessor={d => d.macdVal?.signal}
                yLabel={t('analysis.technical.signal_tooltip_label')}
                yDisplayFormat={pricesDisplayFormat}
                origin={[80, 16]}
              />
              <MouseCoordinateX displayFormat={timeDisplayFormat} />
              <MouseCoordinateY rectWidth={margin.right} displayFormat={pricesDisplayFormat} />
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

        {/* Ticker Dropdown */}
        <div className="flex items-center gap-2">
          <select
            value={selectedSymbol}
            onChange={(e) => {
              setAnalysisData(null);
              setError(null);
              setSelectedSymbol(e.target.value);
            }}
            disabled={tickersLoading}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 min-w-[200px] bg-white"
          >
            <option value="">-- Chọn cổ phiếu --</option>
            {tickerOptions.map(opt => (
              <option key={opt.symbol} value={opt.symbol}>
                {opt.symbol}{opt.name && opt.name !== opt.symbol ? ` · ${opt.name}` : ''}
              </option>
            ))}
          </select>
          {tickersLoading && (
            <span className="text-xs text-gray-400 animate-pulse">Đang tải...</span>
          )}
          {!tickersLoading && tickerOptions.length === 0 && (
            <span className="text-xs text-gray-400">
              (Thêm cổ phiếu vào danh sách theo dõi hoặc danh mục)
            </span>
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
      ) : !analysisData && loading ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">{t('analysis.technical.loading_message', { symbol: selectedSymbol })}</p>
        </div>
      ) : !analysisData && error ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-700 mb-2">{t('analysis.technical.error_title')}</h2>
          <p className="text-gray-500">{error}</p>
          <button
            onClick={() => fetchTechnicalAnalysis(selectedSymbol, period)}
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
                {loading && (
                  <span className="text-xs text-blue-500 animate-pulse">Đang tải…</span>
                )}
                <select
                  value={period}
                  onChange={(e) => setPeriod(Number(e.target.value))}
                  disabled={loading}
                  className="px-2 py-1 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60"
                >
                  <option value={30}>{t('analysis.technical.period_30_days')}</option>
                  <option value={60}>{t('analysis.technical.period_60_days')}</option>
                  <option value={100}>{t('analysis.technical.period_100_days')}</option>
                  <option value={200}>{t('analysis.technical.period_200_days')}</option>
                  <option value={300}>300 ngày</option>
                </select>
                {activeTab === 'charts' && <SeriesDropdown />}
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
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 overflow-x-auto">
              <div className="min-w-[1200px]">
                <FinancialChart />
              </div>
            </div>
          )}
        </div>
      ) : null}

    </div>
  );
};
