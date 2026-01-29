import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { TrendingUp, TrendingDown, AlertTriangle, Brain, Activity, Shield, Target, Settings, RefreshCw, Calendar, BarChart3, ChartLine } from 'lucide-react';
import { format } from "d3-format";
import { timeFormat } from "d3-time-format";

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
  lastVisibleItemBasedZoomAnchor,
  ema,
  sma,
  bollingerBand,
  macd,
  rsi
} from "react-financial-charts";

import { API_BASE_URLS } from '../../constants/api';

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6'];

// Use centralized API configuration - AI endpoints
const API_BASE_URL = API_BASE_URLS.AI_API;

export const AIInsights = () => {
  const [selectedStock, setSelectedStock] = useState('VIC');
  const [selectedIndicators, setSelectedIndicators] = useState({
    trend: 'MACD',
    momentum: 'RSI',
    volatility: 'BB',
    volume: 'OBV'
  });
  const [dateRange, setDateRange] = useState({
    start: '2024-01-01',
    end: '2024-12-31'
  });
  const [availableIndicators, setAvailableIndicators] = useState({});
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('parameters'); // 'parameters' or 'charts'
  const [indicatorData, setIndicatorData] = useState(null);
  const [chartLoading, setChartLoading] = useState(false);

  useEffect(() => {
    fetchAvailableIndicators();
  }, []);

  const fetchAvailableIndicators = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/insights/indicators/available/`);
      if (response.data.status === 'success') {
        setAvailableIndicators(response.data.data.indicators_by_category);
      }
    } catch (err) {
      console.error('Failed to fetch available indicators:', err);
    }
  };

  const fetchAIInsights = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await axios.post(`${API_BASE_URL}/insights/comprehensive/`, {
        symbol: selectedStock,
        start_date: dateRange.start,
        end_date: dateRange.end,
        selected_indicators: selectedIndicators
      });

      if (response.data.status === 'success') {
        setInsights(response.data.data.insights);
      } else {
        setError(response.data.message);
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to fetch AI insights');
    } finally {
      setLoading(false);
    }
  };

  const handleIndicatorChange = (category, indicator) => {
    setSelectedIndicators(prev => ({
      ...prev,
      [category]: indicator
    }));
  };

  const fetchIndicatorData = async () => {
    if (!selectedStock || !dateRange.start || !dateRange.end) {
      return;
    }

    setChartLoading(true);
    try {
      // Try to fetch from the API endpoint
      const response = await axios.post(`${API_BASE_URL}/insights/indicators/data/`, {
        symbol: selectedStock,
        start_date: dateRange.start,
        end_date: dateRange.end,
        indicators: selectedIndicators
      });

      if (response.data.status === 'success') {
        setIndicatorData(response.data.data);
      }
    } catch (err) {
      console.error('Failed to fetch indicator data, using mock data:', err);

      // Generate mock data for demonstration
      const mockData = generateMockIndicatorData(dateRange.start, dateRange.end, selectedIndicators);
      setIndicatorData(mockData);
    } finally {
      setChartLoading(false);
    }
  };

  const generateMockIndicatorData = (startDate, endDate, indicators) => {
    const start = new Date(startDate);
    const end = new Date(endDate);
    const data = [];
    const days = Math.floor((end - start) / (1000 * 60 * 60 * 24));
    const numPoints = Math.min(days, 100); // Limit to 100 data points for performance

    let basePrice = 100;
    let obv = 1000000;

    for (let i = 0; i <= numPoints; i++) {
      const date = new Date(start.getTime() + (i * (end - start) / numPoints));
      const dateStr = date.toISOString().split('T')[0];

      // Generate realistic price movement
      const priceChange = (Math.random() - 0.48) * 2;
      basePrice = Math.max(50, basePrice + priceChange);

      const dataPoint = {
        date: dateStr,
        price: parseFloat(basePrice.toFixed(2))
      };

      // Add trend indicators
      if (indicators.trend === 'MACD') {
        const macd = (Math.random() - 0.5) * 5;
        dataPoint.MACD = parseFloat(macd.toFixed(2));
        dataPoint.MACD_signal = parseFloat((macd * 0.8).toFixed(2));
        dataPoint.MACD_histogram = parseFloat((macd - macd * 0.8).toFixed(2));
      } else if (indicators.trend === 'EMA') {
        dataPoint.EMA = parseFloat((basePrice * (1 + (Math.random() - 0.5) * 0.05)).toFixed(2));
      } else if (indicators.trend === 'SMA') {
        dataPoint.SMA = parseFloat((basePrice * (1 + (Math.random() - 0.5) * 0.03)).toFixed(2));
      } else if (indicators.trend === 'WMA') {
        dataPoint.WMA = parseFloat((basePrice * (1 + (Math.random() - 0.5) * 0.04)).toFixed(2));
      }

      // Add momentum indicators
      if (indicators.momentum === 'RSI') {
        dataPoint.RSI = parseFloat((30 + Math.random() * 40).toFixed(2));
      } else if (indicators.momentum === 'Stochastic') {
        dataPoint.Stochastic = parseFloat((20 + Math.random() * 60).toFixed(2));
      } else if (indicators.momentum === 'MFI') {
        dataPoint.MFI = parseFloat((25 + Math.random() * 50).toFixed(2));
      }

      // Add volatility indicators
      if (indicators.volatility === 'BB') {
        const bbMiddle = basePrice;
        const bbDev = basePrice * 0.02;
        dataPoint.BB_upper = parseFloat((bbMiddle + bbDev * 2).toFixed(2));
        dataPoint.BB_middle = parseFloat(bbMiddle.toFixed(2));
        dataPoint.BB_lower = parseFloat((bbMiddle - bbDev * 2).toFixed(2));
      } else if (indicators.volatility === 'ATR') {
        dataPoint.ATR = parseFloat((1 + Math.random() * 3).toFixed(2));
      }

      // Add volume indicators
      if (indicators.volume === 'OBV') {
        obv += (Math.random() - 0.5) * 100000;
        dataPoint.OBV = Math.round(obv);
      } else if (indicators.volume === 'VWAP') {
        dataPoint.VWAP = parseFloat((basePrice * (1 + (Math.random() - 0.5) * 0.02)).toFixed(2));
      }

      data.push(dataPoint);
    }

    return {
      data: data,
      indicators: {
        trend: { name: indicators.trend, description: 'Trend Indicator' },
        momentum: { name: indicators.momentum, description: 'Momentum Indicator' },
        volatility: { name: indicators.volatility, description: 'Volatility Indicator' },
        volume: { name: indicators.volume, description: 'Volume Indicator' }
      }
    };
  };

  useEffect(() => {
    const loadIndicatorData = async () => {
      if (!selectedStock || !dateRange.start || !dateRange.end) {
        return;
      }

      setChartLoading(true);
      try {
        // Try to fetch from the API endpoint
        const response = await axios.post(`${API_BASE_URL}/insights/indicators/data/`, {
          symbol: selectedStock,
          start_date: dateRange.start,
          end_date: dateRange.end,
          indicators: selectedIndicators
        });

        if (response.data.status === 'success') {
          setIndicatorData(response.data.data);
        }
      } catch (err) {
        console.error('Failed to fetch indicator data, using mock data:', err);

        // Generate mock data for demonstration
        const mockData = generateMockIndicatorData(dateRange.start, dateRange.end, selectedIndicators);
        setIndicatorData(mockData);
      } finally {
        setChartLoading(false);
      }
    };

    loadIndicatorData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedStock, dateRange.start, dateRange.end, selectedIndicators.trend, selectedIndicators.momentum, selectedIndicators.volatility, selectedIndicators.volume]);

  // Prepare chart data for react-financial-charts
  const prepareChartData = useCallback(() => {
    if (!indicatorData || !indicatorData.data || indicatorData.data.length === 0) return [];

    return indicatorData.data.map((item, index) => {
      // Parse date string to Date object properly
      let dateObj;
      if (item.date instanceof Date) {
        dateObj = item.date;
      } else if (typeof item.date === 'string') {
        // Handle various date formats
        dateObj = new Date(item.date);
        // If invalid, try parsing as ISO string
        if (isNaN(dateObj.getTime())) {
          const parts = item.date.split('-');
          if (parts.length === 3) {
            dateObj = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
          }
        }
      } else {
        // Fallback: create date based on index
        dateObj = new Date();
        dateObj.setDate(dateObj.getDate() - (indicatorData.data.length - index));
      }

      // Ensure we have a valid date
      if (isNaN(dateObj.getTime())) {
        dateObj = new Date();
        dateObj.setDate(dateObj.getDate() - (indicatorData.data.length - index));
      }

      const price = item.price || 100;

      return {
        date: dateObj,
        open: price * (1 - Math.random() * 0.01),
        high: price * (1 + Math.random() * 0.015),
        low: price * (1 - Math.random() * 0.015),
        close: price,
        volume: item.OBV ? Math.abs(item.OBV / 100) : Math.random() * 1000000 + 500000,
        // Pass through indicator values
        RSI: item.RSI,
        Stochastic: item.Stochastic,
        MFI: item.MFI,
        MACD: item.MACD,
        MACD_signal: item.MACD_signal,
        MACD_histogram: item.MACD_histogram,
        BB_upper: item.BB_upper,
        BB_middle: item.BB_middle,
        BB_lower: item.BB_lower,
        ATR: item.ATR,
        OBV: item.OBV,
        VWAP: item.VWAP,
        EMA: item.EMA,
        SMA: item.SMA,
        WMA: item.WMA
      };
    });
  }, [indicatorData]);

  // Financial Chart Component using react-financial-charts
  const FinancialIndicatorChart = () => {
    const rawData = prepareChartData();
    if (!rawData || rawData.length === 0) {
      return (
        <div className="bg-white rounded-lg p-6 border border-gray-200">
          <div className="text-center py-8">
            <ChartLine className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <p className="text-gray-600">No indicator data available</p>
            <p className="text-sm text-gray-500 mt-2">Select indicators and click Analyze to view charts</p>
          </div>
        </div>
      );
    }

    const indicators = indicatorData?.indicators || {};

    // Determine which panels to show based on selected indicators
    const showMomentumPanel = indicators.momentum && ['RSI', 'Stochastic', 'MFI'].includes(indicators.momentum.name);
    const showMACDPanel = indicators.trend && indicators.trend.name === 'MACD';
    const showVolumePanel = indicators.volume && ['OBV', 'VWAP'].includes(indicators.volume.name);
    const showBollingerBands = indicators.volatility && indicators.volatility.name === 'BB';
    const showMovingAverage = indicators.trend && ['EMA', 'SMA', 'WMA'].includes(indicators.trend.name);

    // Calculate indicators using react-financial-charts calculators
    const sma20Calculator = sma()
      .options({ windowSize: 20 })
      .merge((d, c) => { d.sma20 = c; })
      .accessor(d => d.sma20);

    const ema12Calculator = ema()
      .options({ windowSize: 12 })
      .merge((d, c) => { d.ema12 = c; })
      .accessor(d => d.ema12);

    const bbCalculator = bollingerBand()
      .options({ windowSize: 20, multiplier: 2 })
      .merge((d, c) => { d.bb = c; })
      .accessor(d => d.bb);

    const macdCalculator = macd()
      .options({ fast: 12, slow: 26, signal: 9 })
      .merge((d, c) => { d.macdCalc = c; })
      .accessor(d => d.macdCalc);

    const rsiCalculator = rsi()
      .options({ windowSize: 14 })
      .merge((d, c) => { d.rsiCalc = c; })
      .accessor(d => d.rsiCalc);

    // Apply calculators
    let calculatedData = rawData;
    if (showMovingAverage) {
      if (indicators.trend.name === 'SMA') calculatedData = sma20Calculator(calculatedData);
      if (indicators.trend.name === 'EMA') calculatedData = ema12Calculator(calculatedData);
    }
    if (showBollingerBands) calculatedData = bbCalculator(calculatedData);
    if (showMACDPanel) calculatedData = macdCalculator(calculatedData);
    if (showMomentumPanel && indicators.momentum.name === 'RSI') calculatedData = rsiCalculator(calculatedData);

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

    // Calculate panel heights
    const priceHeight = 280;
    const momentumHeight = showMomentumPanel ? 120 : 0;
    const macdHeight = showMACDPanel ? 120 : 0;
    const volumeHeight = showVolumePanel ? 100 : 0;
    const chartHeight = priceHeight + momentumHeight + macdHeight + volumeHeight + 50;

    // Calculate origins for each panel
    let currentY = priceHeight;
    const momentumOrigin = [0, currentY];
    currentY += momentumHeight;
    const macdOrigin = [0, currentY];
    currentY += macdHeight;
    const volumeOrigin = [0, currentY];

    const openCloseColor = d => d.close > d.open ? "#26a69a" : "#ef5350";
    const volumeColor = d => d.close > d.open ? "rgba(38, 166, 154, 0.5)" : "rgba(239, 83, 80, 0.5)";

    return (
      <ChartCanvas
        height={chartHeight}
        ratio={2}
        width={width}
        margin={margin}
        data={data}
        displayXAccessor={displayXAccessor}
        seriesName="AIInsights"
        xScale={xScale}
        xAccessor={xAccessor}
        xExtents={xExtents}
        zoomAnchor={lastVisibleItemBasedZoomAnchor}
      >
        {/* Panel 1: Price Chart with Overlays (Price + MA + BB - same price scale) */}
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
          <XAxis showGridLines />
          <YAxis showGridLines tickFormat={pricesDisplayFormat} />

          <CandlestickSeries />

          {/* Bollinger Bands (same scale as price) */}
          {showBollingerBands && (
            <BollingerSeries
              yAccessor={d => d.bb}
              strokeStyle={{
                top: "#8B5CF6",
                middle: "#A78BFA",
                bottom: "#8B5CF6"
              }}
              fillStyle="rgba(139, 92, 246, 0.1)"
            />
          )}

          {/* Moving Averages (same scale as price) */}
          {showMovingAverage && indicators.trend.name === 'SMA' && (
            <LineSeries yAccessor={d => d.sma20} strokeStyle="#06B6D4" strokeWidth={1.5} />
          )}
          {showMovingAverage && indicators.trend.name === 'EMA' && (
            <LineSeries yAccessor={d => d.ema12} strokeStyle="#84CC16" strokeWidth={1.5} />
          )}

          {/* VWAP overlay (same scale as price) */}
          {indicators.volume?.name === 'VWAP' && (
            <LineSeries yAccessor={d => d.VWAP} strokeStyle="#14B8A6" strokeWidth={2} strokeDasharray="5 5" />
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

          {showBollingerBands && (
            <BollingerBandTooltip
              origin={[8, 60]}
              yAccessor={d => d.bb}
              options={{ windowSize: 20, multiplier: 2 }}
              fill="#8B5CF6"
            />
          )}

          {showMovingAverage && (
            <MovingAverageTooltip
              origin={[8, 40]}
              options={[
                indicators.trend.name === 'SMA' && { yAccessor: d => d.sma20, type: "SMA", stroke: "#06B6D4", windowSize: 20 },
                indicators.trend.name === 'EMA' && { yAccessor: d => d.ema12, type: "EMA", stroke: "#84CC16", windowSize: 12 },
              ].filter(Boolean)}
            />
          )}

          <ZoomButtons />
        </Chart>

        {/* Panel 2: Momentum Indicators (RSI/Stochastic/MFI - 0-100 scale) */}
        {showMomentumPanel && (
          <Chart
            id={2}
            height={momentumHeight}
            yExtents={[0, 100]}
            origin={momentumOrigin}
            padding={{ top: 10, bottom: 10 }}
          >
            <XAxis showGridLines />
            <YAxis tickValues={[30, 50, 70]} tickFormat={d => d} />

            {/* Overbought/Oversold reference lines */}
            <StraightLine yValue={70} strokeStyle="#ef4444" strokeDasharray="Dash" />
            <StraightLine yValue={30} strokeStyle="#10b981" strokeDasharray="Dash" />
            <StraightLine yValue={50} strokeStyle="#9ca3af" strokeDasharray="Dot" />

            {indicators.momentum.name === 'RSI' && (
              <>
                <RSISeries yAccessor={d => d.rsiCalc || d.RSI} strokeStyle={{ line: "#F59E0B" }} />
                <SingleValueTooltip
                  yAccessor={d => d.rsiCalc || d.RSI}
                  yLabel="RSI(14)"
                  yDisplayFormat={format(".2f")}
                  origin={[8, 16]}
                />
              </>
            )}

            {indicators.momentum.name === 'Stochastic' && (
              <>
                <LineSeries yAccessor={d => d.Stochastic} strokeStyle="#EF4444" strokeWidth={1.5} />
                <SingleValueTooltip
                  yAccessor={d => d.Stochastic}
                  yLabel="Stochastic"
                  yDisplayFormat={format(".2f")}
                  origin={[8, 16]}
                />
              </>
            )}

            {indicators.momentum.name === 'MFI' && (
              <>
                <LineSeries yAccessor={d => d.MFI} strokeStyle="#F97316" strokeWidth={1.5} />
                <SingleValueTooltip
                  yAccessor={d => d.MFI}
                  yLabel="MFI"
                  yDisplayFormat={format(".2f")}
                  origin={[8, 16]}
                />
              </>
            )}

            <MouseCoordinateY rectWidth={margin.right} displayFormat={format(".0f")} />
          </Chart>
        )}

        {/* Panel 3: MACD (centered on zero - separate scale) */}
        {showMACDPanel && (
          <Chart
            id={3}
            height={macdHeight}
            yExtents={d => d.macdCalc}
            origin={macdOrigin}
            padding={{ top: 10, bottom: 10 }}
          >
            <XAxis showGridLines />
            <YAxis tickFormat={pricesDisplayFormat} />

            <MACDSeries
              yAccessor={d => d.macdCalc}
              strokeStyle={{
                macd: "#10B981",
                signal: "#059669"
              }}
              fillStyle={{
                divergence: "#34D399"
              }}
            />

            <SingleValueTooltip
              yAccessor={d => d.macdCalc?.MACD}
              yLabel="MACD"
              yDisplayFormat={pricesDisplayFormat}
              origin={[8, 16]}
            />
            <SingleValueTooltip
              yAccessor={d => d.macdCalc?.signal}
              yLabel="Signal"
              yDisplayFormat={pricesDisplayFormat}
              origin={[80, 16]}
            />

            <MouseCoordinateY rectWidth={margin.right} displayFormat={pricesDisplayFormat} />
          </Chart>
        )}

        {/* Panel 4: Volume (bar chart - separate scale) */}
        {showVolumePanel && (
          <Chart
            id={4}
            height={volumeHeight}
            yExtents={d => d.volume}
            origin={volumeOrigin}
            padding={{ top: 10, bottom: 10 }}
          >
            <XAxis showGridLines />
            <YAxis tickFormat={volumeFormat} />

            <BarSeries fillStyle={volumeColor} yAccessor={d => d.volume} />

            {indicators.volume.name === 'OBV' && (
              <LineSeries
                yAccessor={d => Math.abs(d.OBV / 100)}
                strokeStyle="#6366F1"
                strokeWidth={1}
              />
            )}

            <MouseCoordinateX displayFormat={timeDisplayFormat} />
            <MouseCoordinateY rectWidth={margin.right} displayFormat={volumeFormat} />

            <SingleValueTooltip
              yAccessor={d => d.volume}
              yLabel="Vol"
              yDisplayFormat={volumeFormat}
              origin={[8, 16]}
            />
          </Chart>
        )}

        <CrossHairCursor />
      </ChartCanvas>
    );
  };

  const renderTechnicalIndicatorsChart = () => {
    const indicators = indicatorData?.indicators || {};

    // Determine which panels are active for legend
    const showMomentumPanel = indicators.momentum && ['RSI', 'Stochastic', 'MFI'].includes(indicators.momentum.name);
    const showMACDPanel = indicators.trend && indicators.trend.name === 'MACD';
    const showVolumePanel = indicators.volume && ['OBV', 'VWAP'].includes(indicators.volume.name);
    const showBollingerBands = indicators.volatility && indicators.volatility.name === 'BB';
    const showMovingAverage = indicators.trend && ['EMA', 'SMA', 'WMA'].includes(indicators.trend.name);

    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Technical Indicators Chart</h2>
          <div className="flex items-center space-x-2">
            {chartLoading && (
              <RefreshCw className="w-5 h-5 text-blue-500 animate-spin" />
            )}
            <ChartLine className="w-6 h-6 text-blue-500" />
          </div>
        </div>

        {/* Legend */}
        <div className="mb-4 p-3 bg-gray-50 rounded-lg">
          <div className="flex flex-wrap gap-4 text-sm">
            <div className="flex items-center gap-2">
              <span className="font-medium text-gray-700">Price Panel:</span>
              <span className="flex items-center"><span className="w-3 h-3 bg-green-500 mr-1 rounded"></span>Candles</span>
              {showBollingerBands && (
                <span className="flex items-center"><span className="w-3 h-0.5 bg-purple-500 mr-1"></span>BB</span>
              )}
              {showMovingAverage && (
                <span className="flex items-center"><span className="w-3 h-0.5 bg-cyan-500 mr-1"></span>{indicators.trend?.name}</span>
              )}
              {indicators.volume?.name === 'VWAP' && (
                <span className="flex items-center"><span className="w-3 h-0.5 bg-teal-500 mr-1" style={{borderStyle: 'dashed'}}></span>VWAP</span>
              )}
            </div>
            {showMomentumPanel && (
              <div className="flex items-center gap-2">
                <span className="font-medium text-gray-700">Momentum:</span>
                <span className="flex items-center"><span className="w-3 h-0.5 bg-amber-500 mr-1"></span>{indicators.momentum?.name}</span>
              </div>
            )}
            {showMACDPanel && (
              <div className="flex items-center gap-2">
                <span className="font-medium text-gray-700">MACD:</span>
                <span className="flex items-center"><span className="w-3 h-0.5 bg-emerald-500 mr-1"></span>MACD</span>
                <span className="flex items-center"><span className="w-3 h-0.5 bg-emerald-700 mr-1"></span>Signal</span>
              </div>
            )}
            {showVolumePanel && (
              <div className="flex items-center gap-2">
                <span className="font-medium text-gray-700">Volume:</span>
                <span className="flex items-center"><span className="w-3 h-3 bg-gray-400 mr-1 rounded-sm"></span>Vol Bars</span>
                {indicators.volume?.name === 'OBV' && (
                  <span className="flex items-center"><span className="w-3 h-0.5 bg-indigo-500 mr-1"></span>OBV</span>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Chart Container */}
        <div className="overflow-x-auto">
          <div className="min-w-[1200px]">
            <FinancialIndicatorChart />
          </div>
        </div>

        <div className="mt-4 p-3 bg-blue-50 rounded-lg">
          <p className="text-sm text-blue-700">
            Use mouse wheel to zoom, drag to pan. Indicators with same data range are grouped in panels.
            Price overlays (MA, BB, VWAP) share the price panel. Momentum indicators (RSI, Stochastic, MFI) use 0-100 scale.
          </p>
        </div>
      </div>
    );
  };

  const renderPatternCard = (pattern, index) => {
    const getPatternIcon = (type) => {
      if (type.includes('bullish')) return <TrendingUp className="w-5 h-5 text-green-500" />;
      if (type.includes('bearish')) return <TrendingDown className="w-5 h-5 text-red-500" />;
      return <Activity className="w-5 h-5 text-blue-500" />;
    };

    const getPatternColor = (type) => {
      if (type.includes('bullish')) return 'border-green-200 bg-green-50';
      if (type.includes('bearish')) return 'border-red-200 bg-red-50';
      return 'border-blue-200 bg-blue-50';
    };

    return (
      <div key={`pattern-${index}-${pattern.pattern_type}-${pattern.start_date || index}`} className={`p-4 rounded-lg border ${getPatternColor(pattern.pattern_type)}`}>
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            {getPatternIcon(pattern.pattern_type)}
            <span className="font-medium text-sm">{pattern.pattern_type.replace('_', ' ').toUpperCase()}</span>
          </div>
          <span className="text-xs bg-white px-2 py-1 rounded-full">
            {Math.round(pattern.confidence * 100)}% confidence
          </span>
        </div>
        <p className="text-sm text-gray-600">{pattern.description}</p>
        <div className="mt-2 flex justify-between text-xs text-gray-500">
          <span>Signal: {Math.round(pattern.signal_strength * 100)}%</span>
          <span>{pattern.start_date}</span>
        </div>
      </div>
    );
  };

  const renderSentimentIndicator = (sentiment) => {
    const getSentimentColor = (type) => {
      switch (type) {
        case 'very_positive': return 'text-green-600 bg-green-100';
        case 'positive': return 'text-green-500 bg-green-50';
        case 'neutral': return 'text-gray-500 bg-gray-100';
        case 'negative': return 'text-red-500 bg-red-50';
        case 'very_negative': return 'text-red-600 bg-red-100';
        default: return 'text-gray-500 bg-gray-100';
      }
    };

    return (
      <div className="bg-white rounded-lg p-6 border border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Market Sentiment</h3>
          <Brain className="w-6 h-6 text-purple-500" />
        </div>

        <div className="text-center mb-4">
          <div className={`inline-flex px-4 py-2 rounded-full text-sm font-medium ${getSentimentColor(sentiment.sentiment_type)}`}>
            {sentiment.sentiment_type.replace('_', ' ').toUpperCase()}
          </div>
        </div>

        <div className="space-y-3">
          <div className="flex justify-between">
            <span className="text-gray-600">Score:</span>
            <span className="font-medium">{(sentiment.score * 100).toFixed(1)}%</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Confidence:</span>
            <span className="font-medium">{(sentiment.confidence * 100).toFixed(1)}%</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">News Count:</span>
            <span className="font-medium">{sentiment.news_count}</span>
          </div>
        </div>

        <div className="mt-4 p-3 bg-gray-50 rounded-lg">
          <p className="text-sm text-gray-600">{sentiment.summary}</p>
        </div>
      </div>
    );
  };

  const renderRiskAssessment = (risk) => {
    const getRiskColor = (level) => {
      switch (level) {
        case 'low': return 'text-green-600 bg-green-100';
        case 'medium': return 'text-yellow-600 bg-yellow-100';
        case 'high': return 'text-orange-600 bg-orange-100';
        case 'critical': return 'text-red-600 bg-red-100';
        default: return 'text-gray-600 bg-gray-100';
      }
    };

    return (
      <div className="bg-white rounded-lg p-6 border border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Risk Assessment</h3>
          <Shield className="w-6 h-6 text-red-500" />
        </div>

        <div className="text-center mb-4">
          <div className={`inline-flex px-4 py-2 rounded-full text-sm font-medium ${getRiskColor(risk.risk_level)}`}>
            {risk.risk_level.toUpperCase()} RISK
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="text-lg font-bold text-gray-900">{(risk.volatility * 100).toFixed(1)}%</div>
            <div className="text-xs text-gray-600">Volatility</div>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="text-lg font-bold text-gray-900">{risk.beta.toFixed(2)}</div>
            <div className="text-xs text-gray-600">Beta</div>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="text-lg font-bold text-gray-900">{(risk.var_95 * 100).toFixed(1)}%</div>
            <div className="text-xs text-gray-600">VaR (95%)</div>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="text-lg font-bold text-gray-900">{risk.risk_score.toFixed(2)}</div>
            <div className="text-xs text-gray-600">Risk Score</div>
          </div>
        </div>

        <div className="space-y-2">
          <h4 className="font-medium text-gray-900">Risk Factors:</h4>
          {risk.factors.map((factor, index) => (
            <div key={index} className="flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 text-yellow-500" />
              <span className="text-sm text-gray-600">{factor}</span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderPredictionResults = (predictions) => {
    const modelData = [];

    if (predictions.random_forest) {
      modelData.push({
        name: 'Random Forest',
        accuracy: (predictions.random_forest.accuracy_score * 100).toFixed(1),
        prediction: predictions.random_forest.predicted_price.toFixed(2),
        confidence_low: predictions.random_forest.confidence_interval[0].toFixed(2),
        confidence_high: predictions.random_forest.confidence_interval[1].toFixed(2)
      });
    }

    if (predictions.xgboost) {
      modelData.push({
        name: 'XGBoost',
        accuracy: (predictions.xgboost.accuracy_score * 100).toFixed(1),
        prediction: predictions.xgboost.predicted_price.toFixed(2),
        confidence_low: predictions.xgboost.confidence_interval[0].toFixed(2),
        confidence_high: predictions.xgboost.confidence_interval[1].toFixed(2)
      });
    }

    return (
      <div className="bg-white rounded-lg p-6 border border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Price Predictions</h3>
          <Target className="w-6 h-6 text-blue-500" />
        </div>

        <div className="space-y-4">
          {modelData.map((model, index) => (
            <div key={model.name} className="p-4 bg-gray-50 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-medium text-gray-900">{model.name}</h4>
                <span className="text-sm text-gray-600">R² Score: {model.accuracy}%</span>
              </div>

              <div className="grid grid-cols-3 gap-4 text-center">
                <div>
                  <div className="text-lg font-bold text-blue-600">{model.prediction}</div>
                  <div className="text-xs text-gray-600">Predicted Price</div>
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-700">{model.confidence_low}</div>
                  <div className="text-xs text-gray-600">Lower Bound</div>
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-700">{model.confidence_high}</div>
                  <div className="text-xs text-gray-600">Upper Bound</div>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-4 p-3 bg-blue-50 rounded-lg">
          <p className="text-sm text-blue-700">{predictions.model_comparison}</p>
        </div>
      </div>
    );
  };

  const renderAIScore = (aiScore) => {
    const scoreData = [
      { name: 'Pattern', value: aiScore.pattern_score, color: '#3B82F6' },
      { name: 'Sentiment', value: aiScore.sentiment_score, color: '#10B981' },
      { name: 'Risk', value: aiScore.risk_score, color: '#F59E0B' },
      { name: 'Prediction', value: aiScore.prediction_score, color: '#EF4444' }
    ];

    return (
      <div className="bg-white rounded-lg p-6 border border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">AI Confidence Score</h3>
          <BarChart3 className="w-6 h-6 text-purple-500" />
        </div>

        <div className="text-center mb-6">
          <div className="text-4xl font-bold text-purple-600">{aiScore.overall_score}</div>
          <div className="text-sm text-gray-600">Overall Score</div>
          <div className={`inline-flex px-3 py-1 rounded-full text-sm font-medium mt-2 ${
            aiScore.confidence_level === 'High' ? 'bg-green-100 text-green-700' :
            aiScore.confidence_level === 'Medium' ? 'bg-yellow-100 text-yellow-700' :
            'bg-red-100 text-red-700'
          }`}>
            {aiScore.confidence_level} Confidence
          </div>
        </div>

        <div className="space-y-3">
          {scoreData.map((item, index) => (
            <div key={item.name} className="flex items-center justify-between">
              <span className="text-sm text-gray-600">{item.name}:</span>
              <div className="flex items-center space-x-2">
                <div className="w-20 bg-gray-200 rounded-full h-2">
                  <div
                    className="h-2 rounded-full"
                    style={{
                      width: `${item.value}%`,
                      backgroundColor: item.color
                    }}
                  ></div>
                </div>
                <span className="text-sm font-medium w-12">{item.value}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="p-4">
      {/* Header with Title and Tab Controls */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 mb-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-4">
            <h1 className="text-lg font-bold text-gray-900">AI Insights</h1>
            {/* Professional Tab Controls */}
            <div className="flex items-center rounded-2xl p-1.5" style={{ background: 'linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%)', boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.06)' }}>
              <button
                onClick={() => setActiveTab('parameters')}
                className="flex items-center space-x-2 px-5 py-2 text-sm font-semibold rounded-xl transition-all duration-300"
                style={activeTab === 'parameters'
                  ? { background: 'linear-gradient(135deg, #3b82f6 0%, #6366f1 100%)', color: '#ffffff', boxShadow: '0 4px 15px rgba(99, 102, 241, 0.4)', transform: 'scale(1.02)' }
                  : { background: 'transparent', color: '#4b5563' }
                }
              >
                <Settings className={`w-4 h-4 ${activeTab === 'parameters' ? 'animate-pulse' : ''}`} />
                <span>Parameters & Indicators</span>
              </button>
              <button
                onClick={() => setActiveTab('charts')}
                className="flex items-center space-x-2 px-5 py-2 text-sm font-semibold rounded-xl transition-all duration-300"
                style={activeTab === 'charts'
                  ? { background: 'linear-gradient(135deg, #10b981 0%, #14b8a6 100%)', color: '#ffffff', boxShadow: '0 4px 15px rgba(16, 185, 129, 0.4)', transform: 'scale(1.02)' }
                  : { background: 'transparent', color: '#4b5563' }
                }
              >
                <ChartLine className={`w-4 h-4 ${activeTab === 'charts' ? 'animate-pulse' : ''}`} />
                <span>Chart & Series</span>
              </button>
            </div>
          </div>
          <button
            onClick={fetchAIInsights}
            disabled={loading}
            className="flex items-center px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          >
            {loading ? (
              <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Brain className="w-4 h-4 mr-2" />
            )}
            {loading ? 'Analyzing...' : 'Analyze'}
          </button>
        </div>

        {/* Stock Info Summary - 6-Column Table */}
        <table className="w-full text-sm">
          <tbody>
            <tr className="border-b border-gray-100">
              <td className="py-2 text-gray-500 w-1/6">Symbol</td>
              <td className="py-2 font-semibold text-blue-600 w-1/6">{selectedStock}</td>
              <td className="py-2 text-gray-500 w-1/6">Date Range</td>
              <td className="py-2 font-semibold w-1/6">{dateRange.start} to {dateRange.end}</td>
              <td className="py-2 text-gray-500 w-1/6">Status</td>
              <td className="py-2 font-semibold w-1/6">
                {loading ? (
                  <span className="text-yellow-600">Analyzing...</span>
                ) : insights ? (
                  <span className="text-green-600">Ready</span>
                ) : (
                  <span className="text-gray-500">Awaiting Analysis</span>
                )}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
          <div className="flex items-center">
            <AlertTriangle className="w-4 h-4 text-red-500 mr-2" />
            <span className="text-sm text-red-700">{error}</span>
          </div>
        </div>
      )}

      {/* Tab 1: Stock Parameters & Indicators */}
      {activeTab === 'parameters' && (
        <div className="space-y-4">
          {/* Controls - 6-Column Table Layout */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <h3 className="text-sm font-bold text-gray-900 mb-3 flex items-center">
              <Settings className="w-4 h-4 mr-2" />
              Stock Parameters
            </h3>
            <table className="w-full text-sm">
              <tbody>
                <tr className="border-b border-gray-100">
                  <td className="py-2 text-gray-500 w-1/6">Stock Symbol</td>
                  <td className="py-2 w-1/6">
                    <input
                      type="text"
                      value={selectedStock}
                      onChange={(e) => setSelectedStock(e.target.value.toUpperCase())}
                      className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                      placeholder="e.g., VIC"
                    />
                  </td>
                  <td className="py-2 text-gray-500 w-1/6">Start Date</td>
                  <td className="py-2 w-1/6">
                    <input
                      type="date"
                      value={dateRange.start}
                      onChange={(e) => setDateRange(prev => ({ ...prev, start: e.target.value }))}
                      className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </td>
                  <td className="py-2 text-gray-500 w-1/6">End Date</td>
                  <td className="py-2 w-1/6">
                    <input
                      type="date"
                      value={dateRange.end}
                      onChange={(e) => setDateRange(prev => ({ ...prev, end: e.target.value }))}
                      className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Indicator Selection - 6-Column Table Layout */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <h3 className="text-sm font-bold text-gray-900 mb-3 flex items-center">
              <Activity className="w-4 h-4 mr-2" />
              Technical Indicators
            </h3>
            <table className="w-full text-sm">
              <tbody>
                <tr className="border-b border-gray-100">
                  <td className="py-2 text-gray-500 w-1/6">Trend</td>
                  <td className="py-2 w-1/6">
                    <select
                      value={selectedIndicators.trend}
                      onChange={(e) => handleIndicatorChange('trend', e.target.value)}
                      className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                    >
                      {availableIndicators.trend?.map(indicator => (
                        <option key={indicator.name} value={indicator.name}>{indicator.name}</option>
                      ))}
                    </select>
                  </td>
                  <td className="py-2 text-gray-500 w-1/6">Momentum</td>
                  <td className="py-2 w-1/6">
                    <select
                      value={selectedIndicators.momentum}
                      onChange={(e) => handleIndicatorChange('momentum', e.target.value)}
                      className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                    >
                      {availableIndicators.momentum?.map(indicator => (
                        <option key={indicator.name} value={indicator.name}>{indicator.name}</option>
                      ))}
                    </select>
                  </td>
                  <td className="py-2 text-gray-500 w-1/6">Volatility</td>
                  <td className="py-2 w-1/6">
                    <select
                      value={selectedIndicators.volatility}
                      onChange={(e) => handleIndicatorChange('volatility', e.target.value)}
                      className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                    >
                      {availableIndicators.volatility?.map(indicator => (
                        <option key={indicator.name} value={indicator.name}>{indicator.name}</option>
                      ))}
                    </select>
                  </td>
                </tr>
                <tr>
                  <td className="py-2 text-gray-500">Volume</td>
                  <td className="py-2">
                    <select
                      value={selectedIndicators.volume}
                      onChange={(e) => handleIndicatorChange('volume', e.target.value)}
                      className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                    >
                      {availableIndicators.volume?.map(indicator => (
                        <option key={indicator.name} value={indicator.name}>{indicator.name}</option>
                      ))}
                    </select>
                  </td>
                  <td className="py-2"></td>
                  <td className="py-2"></td>
                  <td className="py-2"></td>
                  <td className="py-2"></td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* AI Score - 6-Column Table Layout */}
          {insights?.ai_score && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
              <h3 className="text-sm font-bold text-gray-900 mb-3 flex items-center">
                <BarChart3 className="w-4 h-4 mr-2" />
                AI Confidence Score
              </h3>
              <table className="w-full text-sm">
                <tbody>
                  <tr className="border-b border-gray-100">
                    <td className="py-2 text-gray-500 w-1/6">Overall Score</td>
                    <td className="py-2 font-bold text-purple-600 w-1/6">{insights.ai_score.overall_score}</td>
                    <td className="py-2 text-gray-500 w-1/6">Confidence</td>
                    <td className={`py-2 font-semibold w-1/6 ${
                      insights.ai_score.confidence_level === 'High' ? 'text-green-600' :
                      insights.ai_score.confidence_level === 'Medium' ? 'text-yellow-600' : 'text-red-600'
                    }`}>{insights.ai_score.confidence_level}</td>
                    <td className="py-2 text-gray-500 w-1/6">Pattern Score</td>
                    <td className="py-2 font-semibold text-blue-600 w-1/6">{insights.ai_score.pattern_score}</td>
                  </tr>
                  <tr>
                    <td className="py-2 text-gray-500">Sentiment Score</td>
                    <td className="py-2 font-semibold text-green-600">{insights.ai_score.sentiment_score}</td>
                    <td className="py-2 text-gray-500">Risk Score</td>
                    <td className="py-2 font-semibold text-yellow-600">{insights.ai_score.risk_score}</td>
                    <td className="py-2 text-gray-500">Prediction Score</td>
                    <td className="py-2 font-semibold text-red-600">{insights.ai_score.prediction_score}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}

          {/* Sentiment Analysis - 6-Column Table Layout */}
          {insights?.sentiment_analysis && (
            <div className={`rounded-xl shadow-sm border border-gray-200 p-4 ${
              insights.sentiment_analysis.sentiment_type.includes('positive') ? 'bg-green-50' :
              insights.sentiment_analysis.sentiment_type.includes('negative') ? 'bg-red-50' : 'bg-gray-50'
            }`}>
              <h3 className="text-sm font-bold text-gray-900 mb-3 flex items-center">
                <Brain className="w-4 h-4 mr-2" />
                Market Sentiment
              </h3>
              <table className="w-full text-sm">
                <tbody>
                  <tr className="border-b border-gray-100">
                    <td className="py-2 text-gray-500 w-1/6">Sentiment</td>
                    <td className={`py-2 font-bold w-1/6 ${
                      insights.sentiment_analysis.sentiment_type.includes('positive') ? 'text-green-600' :
                      insights.sentiment_analysis.sentiment_type.includes('negative') ? 'text-red-600' : 'text-gray-600'
                    }`}>{insights.sentiment_analysis.sentiment_type.replace('_', ' ').toUpperCase()}</td>
                    <td className="py-2 text-gray-500 w-1/6">Score</td>
                    <td className="py-2 font-semibold w-1/6">{(insights.sentiment_analysis.score * 100).toFixed(1)}%</td>
                    <td className="py-2 text-gray-500 w-1/6">Confidence</td>
                    <td className="py-2 font-semibold w-1/6">{(insights.sentiment_analysis.confidence * 100).toFixed(1)}%</td>
                  </tr>
                  <tr>
                    <td className="py-2 text-gray-500">News Count</td>
                    <td className="py-2 font-semibold">{insights.sentiment_analysis.news_count}</td>
                    <td className="py-2 text-gray-500" colSpan="4">
                      <span className="text-gray-600 text-xs">{insights.sentiment_analysis.summary}</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}

          {/* Risk Assessment - 6-Column Table Layout */}
          {insights?.risk_assessment && (
            <div className={`rounded-xl shadow-sm border border-gray-200 p-4 ${
              insights.risk_assessment.risk_level === 'low' ? 'bg-green-50' :
              insights.risk_assessment.risk_level === 'medium' ? 'bg-yellow-50' :
              insights.risk_assessment.risk_level === 'high' ? 'bg-orange-50' : 'bg-red-50'
            }`}>
              <h3 className="text-sm font-bold text-gray-900 mb-3 flex items-center">
                <Shield className="w-4 h-4 mr-2" />
                Risk Assessment
              </h3>
              <table className="w-full text-sm">
                <tbody>
                  <tr className="border-b border-gray-100">
                    <td className="py-2 text-gray-500 w-1/6">Risk Level</td>
                    <td className={`py-2 font-bold w-1/6 ${
                      insights.risk_assessment.risk_level === 'low' ? 'text-green-600' :
                      insights.risk_assessment.risk_level === 'medium' ? 'text-yellow-600' :
                      insights.risk_assessment.risk_level === 'high' ? 'text-orange-600' : 'text-red-600'
                    }`}>{insights.risk_assessment.risk_level.toUpperCase()}</td>
                    <td className="py-2 text-gray-500 w-1/6">Risk Score</td>
                    <td className="py-2 font-semibold w-1/6">{insights.risk_assessment.risk_score.toFixed(2)}</td>
                    <td className="py-2 text-gray-500 w-1/6">Volatility</td>
                    <td className="py-2 font-semibold text-purple-600 w-1/6">{(insights.risk_assessment.volatility * 100).toFixed(1)}%</td>
                  </tr>
                  <tr>
                    <td className="py-2 text-gray-500">Beta</td>
                    <td className="py-2 font-semibold">{insights.risk_assessment.beta.toFixed(2)}</td>
                    <td className="py-2 text-gray-500">VaR (95%)</td>
                    <td className="py-2 font-semibold text-red-600">{(insights.risk_assessment.var_95 * 100).toFixed(1)}%</td>
                    <td className="py-2 text-gray-500">Factors</td>
                    <td className="py-2 text-xs text-gray-600">{insights.risk_assessment.factors.length} identified</td>
                  </tr>
                </tbody>
              </table>
              {insights.risk_assessment.factors.length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-200">
                  <div className="flex flex-wrap gap-2">
                    {insights.risk_assessment.factors.map((factor, index) => (
                      <span key={index} className="inline-flex items-center px-2 py-1 bg-white rounded text-xs text-gray-700">
                        <AlertTriangle className="w-3 h-3 text-yellow-500 mr-1" />
                        {factor}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Pattern Recognition - 6-Column Table Layout */}
          {insights?.pattern_recognition && insights.pattern_recognition.patterns.length > 0 && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
              <h3 className="text-sm font-bold text-gray-900 mb-3 flex items-center">
                <Activity className="w-4 h-4 mr-2" />
                Pattern Recognition
              </h3>
              <p className="text-xs text-gray-600 mb-3">{insights.pattern_recognition.summary}</p>
              <table className="w-full text-sm">
                <tbody>
                  {(() => {
                    const patterns = insights.pattern_recognition.patterns;
                    const rows = [];
                    for (let i = 0; i < patterns.length; i += 3) {
                      rows.push(
                        <tr key={i} className={i < patterns.length - 3 ? "border-b border-gray-100" : ""}>
                          {[0, 1, 2].map(offset => {
                            const pattern = patterns[i + offset];
                            if (!pattern) return <React.Fragment key={offset}><td className="py-2 w-1/6"></td><td className="py-2 w-1/6"></td></React.Fragment>;
                            const isBullish = pattern.pattern_type.includes('bullish');
                            const isBearish = pattern.pattern_type.includes('bearish');
                            return (
                              <React.Fragment key={offset}>
                                <td className="py-2 text-gray-500 w-1/6">
                                  <div className="flex items-center">
                                    {isBullish && <TrendingUp className="w-3 h-3 text-green-500 mr-1" />}
                                    {isBearish && <TrendingDown className="w-3 h-3 text-red-500 mr-1" />}
                                    {pattern.pattern_type.replace('_', ' ')}
                                  </div>
                                </td>
                                <td className={`py-2 font-semibold w-1/6 ${isBullish ? 'text-green-600' : isBearish ? 'text-red-600' : 'text-blue-600'}`}>
                                  {Math.round(pattern.confidence * 100)}% <span className="text-gray-400 text-xs">({Math.round(pattern.signal_strength * 100)}%)</span>
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

          {/* Price Predictions - 6-Column Table Layout */}
          {insights?.price_prediction && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
              <h3 className="text-sm font-bold text-gray-900 mb-3 flex items-center">
                <Target className="w-4 h-4 mr-2" />
                Price Predictions
              </h3>
              <table className="w-full text-sm">
                <tbody>
                  {insights.price_prediction.random_forest && (
                    <tr className="border-b border-gray-100">
                      <td className="py-2 text-gray-500 w-1/6">Random Forest</td>
                      <td className="py-2 font-bold text-blue-600 w-1/6">${insights.price_prediction.random_forest.predicted_price.toFixed(2)}</td>
                      <td className="py-2 text-gray-500 w-1/6">R² Score</td>
                      <td className="py-2 font-semibold w-1/6">{(insights.price_prediction.random_forest.accuracy_score * 100).toFixed(1)}%</td>
                      <td className="py-2 text-gray-500 w-1/6">Confidence</td>
                      <td className="py-2 font-semibold text-green-600 w-1/6">
                        ${insights.price_prediction.random_forest.confidence_interval[0].toFixed(2)} - ${insights.price_prediction.random_forest.confidence_interval[1].toFixed(2)}
                      </td>
                    </tr>
                  )}
                  {insights.price_prediction.xgboost && (
                    <tr>
                      <td className="py-2 text-gray-500">XGBoost</td>
                      <td className="py-2 font-bold text-purple-600">${insights.price_prediction.xgboost.predicted_price.toFixed(2)}</td>
                      <td className="py-2 text-gray-500">R² Score</td>
                      <td className="py-2 font-semibold">{(insights.price_prediction.xgboost.accuracy_score * 100).toFixed(1)}%</td>
                      <td className="py-2 text-gray-500">Confidence</td>
                      <td className="py-2 font-semibold text-green-600">
                        ${insights.price_prediction.xgboost.confidence_interval[0].toFixed(2)} - ${insights.price_prediction.xgboost.confidence_interval[1].toFixed(2)}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
              {insights.price_prediction.model_comparison && (
                <div className="mt-3 p-2 bg-blue-50 rounded text-xs text-blue-700">
                  {insights.price_prediction.model_comparison}
                </div>
              )}
            </div>
          )}

          {/* Loading State */}
          {loading && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 text-center">
              <RefreshCw className="w-8 h-8 text-blue-500 animate-spin mx-auto mb-4" />
              <p className="text-gray-600">Analyzing market data with AI models...</p>
            </div>
          )}

          {/* Default State */}
          {!insights && !loading && !error && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 text-center">
              <Brain className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-sm font-semibold text-gray-900 mb-2">Ready for AI Analysis</h3>
              <p className="text-xs text-gray-600">
                Configure parameters above and click Analyze to get comprehensive AI insights.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Chart & Series */}
      {activeTab === 'charts' && (
        <div className="space-y-4">
          {renderTechnicalIndicatorsChart()}
        </div>
      )}
    </div>
  );
};
