import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import { TrendingUp, TrendingDown, AlertTriangle, Brain, Activity, Shield, Target, RefreshCw, BarChart3, ChartLine } from 'lucide-react';
import UnifiedFinancialChart from '../ui/UnifiedFinancialChart';

import { API_BASE_URLS, API_ENDPOINTS } from '../../constants/api';

// eslint-disable-next-line no-unused-vars -- kept for upcoming chart palette wiring
const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6'];

// Use centralized API configuration - AI endpoints
const API_BASE_URL = API_BASE_URLS.AI_API;

const DEFAULT_HISTORY_DAYS = 206;

const isoDate = (d) => d.toISOString().slice(0, 10);

// end = today - 1, start = end - days (the auto-widen rule for indicators).
const defaultDateRange = (days) => {
  const end = new Date();
  end.setDate(end.getDate() - 1);
  const start = new Date(end);
  start.setDate(start.getDate() - days);
  return { start: isoDate(start), end: isoDate(end) };
};

export const AIInsights = () => {
  const { t } = useTranslation();
  const [selectedStock, setSelectedStock] = useState('');
  const [portfolioStocks, setPortfolioStocks] = useState([]);
  const [selectedIndicators, setSelectedIndicators] = useState({
    trend: 'MACD',
    momentum: 'RSI',
    volatility: 'BB',
    volume: 'OBV'
  });
  // Default window: the last DEFAULT_HISTORY_DAYS ending yesterday (the
  // longest requirement, MACD). A fixed historical year here meant the page
  // silently analysed stale data and the auto-widen rule never triggered.
  const [dateRange, setDateRange] = useState(() => defaultDateRange(DEFAULT_HISTORY_DAYS));
  const [availableIndicators, setAvailableIndicators] = useState({});
  const [insights, setInsights] = useState(null);
  // Set when the backend widened a too-short date range for the selected
  // indicators (end = yesterday, start = end - required length).
  const [rangeNotice, setRangeNotice] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('parameters'); // 'parameters' or 'charts'
  const [indicatorData, setIndicatorData] = useState(null);
  const [chartLoading, setChartLoading] = useState(false);

  // Fetch portfolio holdings for stock dropdown
  const fetchPortfolioHoldings = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        // If not logged in, use default stocks
        setPortfolioStocks([
          { symbol: 'VIC', name: 'Vingroup JSC' },
          { symbol: 'VNM', name: 'Vietnam Dairy Products' },
          { symbol: 'VCB', name: 'Vietcombank' },
          { symbol: 'FPT', name: 'FPT Corporation' },
          { symbol: 'HPG', name: 'Hoa Phat Group' }
        ]);
        setSelectedStock('VIC');
        return;
      }

      // First get default portfolio
      const portfolioResponse = await fetch(API_ENDPOINTS.PORTFOLIO_DEFAULT, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!portfolioResponse.ok) {
        throw new Error('Failed to fetch portfolio');
      }

      const portfolioData = await portfolioResponse.json();
      const portfolioId = portfolioData.id;

      // Then get holdings
      const holdingsResponse = await fetch(API_ENDPOINTS.PORTFOLIO_HOLDINGS(portfolioId), {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!holdingsResponse.ok) {
        throw new Error('Failed to fetch holdings');
      }

      const holdings = await holdingsResponse.json();

      if (Array.isArray(holdings) && holdings.length > 0) {
        const stocks = holdings.map(h => ({
          symbol: h.symbol,
          name: h.company_name || h.symbol
        }));
        setPortfolioStocks(stocks);
        setSelectedStock(stocks[0].symbol);
      } else {
        // Fallback to default stocks if no holdings
        setPortfolioStocks([
          { symbol: 'VIC', name: 'Vingroup JSC' },
          { symbol: 'VNM', name: 'Vietnam Dairy Products' },
          { symbol: 'VCB', name: 'Vietcombank' }
        ]);
        setSelectedStock('VIC');
      }
    } catch (err) {
      console.error('Failed to fetch portfolio holdings:', err);
      // Fallback to default stocks
      setPortfolioStocks([
        { symbol: 'VIC', name: 'Vingroup JSC' },
        { symbol: 'VNM', name: 'Vietnam Dairy Products' },
        { symbol: 'VCB', name: 'Vietcombank' }
      ]);
      setSelectedStock('VIC');
    }
  }, []);

  useEffect(() => {
    fetchAvailableIndicators();
    fetchPortfolioHoldings();
  }, [fetchPortfolioHoldings]);

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
    setRangeNotice(null);

    try {
      const response = await axios.post(`${API_BASE_URL}/insights/comprehensive/`, {
        symbol: selectedStock,
        start_date: dateRange.start,
        end_date: dateRange.end,
        selected_indicators: selectedIndicators
      });

      const payload = response.data.data || {};
      if (payload.date_range_adjusted && payload.effective_start_date && payload.effective_end_date) {
        // Reflect the window that was actually analysed in the date inputs
        // (this also re-fetches the indicator chart for the same window).
        setDateRange({ start: payload.effective_start_date, end: payload.effective_end_date });
        setRangeNotice(payload.date_range_note || t('analysis.ai_insights.range_adjusted'));
      }
      if (response.data.status === 'success') {
        setInsights(payload.insights);
      } else {
        setError(response.data.message || t('analysis.ai_insights.no_data'));
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to fetch AI insights');
    } finally {
      setLoading(false);
    }
  };

  // Days of history the current selection needs (from the backend's table,
  // carried on /insights/indicators/available as required_calendar_days).
  const requiredDaysFor = useCallback((selection, available) => {
    let required = 0;
    Object.entries(selection).forEach(([category, name]) => {
      const meta = (available[category] || []).find(i => i.name === name);
      if (meta?.required_calendar_days) required = Math.max(required, meta.required_calendar_days);
    });
    return required;
  }, []);

  // User rule: the date range follows the indicator selection. Every dropdown
  // change re-fits the window to exactly what the selection needs:
  // start = end - required days (end is kept; it defaults to yesterday). A
  // "widen only" rule is not enough here — the default window (206 days,
  // MACD) already covers SMA/EMA/WMA, so switching to them never moved the
  // start date and the analysis re-ran on the very same window. The backend
  // still widens a too-short range as a safety net when Analyze is clicked.
  const fitRangeToSelection = useCallback((selection, available) => {
    const required = requiredDaysFor(selection, available);
    if (!required) return;
    const yesterday = defaultDateRange(0).end;
    const end = dateRange.end && dateRange.end <= yesterday ? dateRange.end : yesterday;
    const start = new Date(end);
    start.setDate(start.getDate() - required);
    const next = { start: isoDate(start), end };
    if (next.start === dateRange.start && next.end === dateRange.end) return;
    setDateRange(next);
    setRangeNotice(t('analysis.ai_insights.range_adjusted_for', { days: required, end }));
  }, [requiredDaysFor, dateRange.start, dateRange.end, t]);

  const handleIndicatorChange = (category, indicator) => {
    const next = { ...selectedIndicators, [category]: indicator };
    setSelectedIndicators(next);
    fitRangeToSelection(next, availableIndicators);
  };

  // Once the indicator table arrives, check the default selection too.
  useEffect(() => {
    if (Object.keys(availableIndicators).length) {
      fitRangeToSelection(selectedIndicators, availableIndicators);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [availableIndicators]);

  // eslint-disable-next-line no-unused-vars -- preserved for the indicator-chart path
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
        // Store entire response object so indicatorData.data works correctly
        setIndicatorData(response.data);
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
    const numPoints = Math.min(days, 100);

    let basePrice = 100;
    let obv = 1000000;

    for (let i = 0; i <= numPoints; i++) {
      const date = new Date(start.getTime() + (i * (end - start) / numPoints));
      const dateStr = date.toISOString().split('T')[0];

      const priceChange = (Math.random() - 0.48) * 2;
      basePrice = Math.max(50, basePrice + priceChange);
      const bbDev = basePrice * 0.02;
      const macdVal = (Math.random() - 0.5) * 5;
      obv += (Math.random() - 0.5) * 100000;

      // Always generate all fields so every series toggle works without refetch
      data.push({
        date: dateStr,
        price: parseFloat(basePrice.toFixed(2)),
        // Moving averages (rough approximation)
        EMA: parseFloat((basePrice * (1 + (Math.random() - 0.5) * 0.03)).toFixed(2)),
        SMA: parseFloat((basePrice * (1 + (Math.random() - 0.5) * 0.02)).toFixed(2)),
        // Bollinger Bands
        BB_upper: parseFloat((basePrice + bbDev * 2).toFixed(2)),
        BB_middle: parseFloat(basePrice.toFixed(2)),
        BB_lower: parseFloat((basePrice - bbDev * 2).toFixed(2)),
        // VWAP (close approximation)
        VWAP: parseFloat((basePrice * (1 + (Math.random() - 0.5) * 0.015)).toFixed(2)),
        // Momentum (0-100)
        RSI: parseFloat((30 + Math.random() * 40).toFixed(2)),
        Stochastic: parseFloat((20 + Math.random() * 60).toFixed(2)),
        MFI: parseFloat((25 + Math.random() * 50).toFixed(2)),
        // MACD
        MACD: parseFloat(macdVal.toFixed(2)),
        MACD_signal: parseFloat((macdVal * 0.8).toFixed(2)),
        MACD_histogram: parseFloat((macdVal * 0.2).toFixed(2)),
        // Volume
        volume: Math.round(500000 + Math.random() * 1000000),
        OBV: Math.round(obv),
      });
    }

    return {
      data,
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
          // Store entire response object so indicatorData.data works correctly
          setIndicatorData(response.data);
        }
      } catch (err) {
        console.error('Failed to fetch indicator data, using mock data:', err);

        // Generate mock data for demonstration (returns object with data property)
        const mockData = generateMockIndicatorData(dateRange.start, dateRange.end, selectedIndicators);
        setIndicatorData(mockData);
      } finally {
        setChartLoading(false);
      }
    };

    loadIndicatorData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedStock, dateRange.start, dateRange.end, selectedIndicators.trend, selectedIndicators.momentum, selectedIndicators.volatility, selectedIndicators.volume]);

  // Prepare chart data for the shared UnifiedFinancialChart. The backend
  // (ai-insights-service) already returns OHLC and pre-calculated indicators in
  // canonical snake_case fields, so we pass them straight through (only aliasing
  // wma_20 -> wma). Older mock data used CamelCase names, kept here as fallbacks.
  const prepareChartData = useCallback(() => {
    const rows = indicatorData && indicatorData.data;
    if (!rows || rows.length === 0) return [];

    const num = (v) => (v === null || v === undefined || isNaN(v) ? undefined : Number(v));

    return rows.map((item) => ({
      date: item.date,
      // OHLCV (real backend data — no synthetic candles)
      open: num(item.open) ?? num(item.price),
      high: num(item.high),
      low: num(item.low),
      close: num(item.close) ?? num(item.price),
      volume: num(item.volume),
      // Price-scale overlays (left axis)
      sma_20: num(item.sma_20) ?? num(item.SMA),
      sma_50: num(item.sma_50),
      ema_12: num(item.ema_12) ?? num(item.EMA),
      wma: num(item.wma_20),
      vwap: num(item.vwap) ?? num(item.VWAP),
      bb_upper: num(item.bb_upper) ?? num(item.BB_upper),
      bb_middle: num(item.bb_middle) ?? num(item.BB_middle),
      bb_lower: num(item.bb_lower) ?? num(item.BB_lower),
      // Oscillators (right axis)
      rsi: num(item.rsi) ?? num(item.RSI),
      macd: num(item.macd) ?? num(item.MACD),
      macd_signal: num(item.macd_signal) ?? num(item.MACD_signal),
      stoch_k: num(item.stoch_k) ?? num(item.Stochastic),
      stoch_d: num(item.stoch_d),
      mfi: num(item.mfi) ?? num(item.MFI),
      atr: num(item.atr),
    }));
  }, [indicatorData]);

  // Technical-indicator chart (Charts tab) — uses the shared UnifiedFinancialChart
  const renderTechnicalIndicatorsChart = () => {
    const chartData = prepareChartData();
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">{t('analysis.ai_insights.chart_title')}</h2>
          {chartLoading && <RefreshCw className="w-5 h-5 text-blue-500 animate-spin" />}
        </div>
        {chartData.length === 0 ? (
          <div className="text-center py-8">
            <ChartLine className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <p className="text-gray-600">{t('analysis.ai_insights.no_indicator_data')}</p>
            <p className="text-sm text-gray-500 mt-2">{t('analysis.ai_insights.select_indicators_hint')}</p>
          </div>
        ) : (
          <UnifiedFinancialChart data={chartData} ticker={selectedStock} />
        )}
      </div>
    );
  };

  // eslint-disable-next-line no-unused-vars -- legacy render helper, inlined elsewhere
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

  // eslint-disable-next-line no-unused-vars -- legacy render helper, inlined elsewhere
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

  // eslint-disable-next-line no-unused-vars -- legacy render helper, inlined elsewhere
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

  // eslint-disable-next-line no-unused-vars -- legacy render helper, inlined elsewhere
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

  // eslint-disable-next-line no-unused-vars -- legacy render helper, inlined elsewhere
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
            <h1 className="text-lg font-bold text-gray-900">{t('analysis.ai_insights.title')}</h1>
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
                <Activity className={`w-4 h-4 ${activeTab === 'parameters' ? 'animate-pulse' : ''}`} />
                <span>{t('analysis.ai_insights.parameters_tab')}</span>
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
                <span>{t('analysis.ai_insights.charts_tab')}</span>
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
            {loading ? t('analysis.ai_insights.analyzing_button') : t('analysis.ai_insights.analyze_button')}
          </button>
        </div>

        {/* Stock Info Summary - 6-Column Table */}
        <table className="w-full text-sm">
          <tbody>
            <tr className="border-b border-gray-100">
              <td className="py-2 text-gray-500 w-1/6">{t('analysis.ai_insights.symbol_label')}</td>
              <td className="py-2 font-semibold text-blue-600 w-1/6">{selectedStock}</td>
              <td className="py-2 text-gray-500 w-1/6">{t('analysis.ai_insights.date_range_label')}</td>
              <td className="py-2 font-semibold w-1/6">{dateRange.start} – {dateRange.end}</td>
              <td className="py-2 text-gray-500 w-1/6">{t('analysis.ai_insights.status_label')}</td>
              <td className="py-2 font-semibold w-1/6">
                {loading ? (
                  <span className="text-yellow-600">{t('analysis.ai_insights.status_analyzing')}</span>
                ) : insights ? (
                  <span className="text-green-600">{t('analysis.ai_insights.status_ready')}</span>
                ) : (
                  <span className="text-gray-500">{t('analysis.ai_insights.status_awaiting')}</span>
                )}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Error Display */}
      {rangeNotice && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-4">
          <div className="flex items-center">
            <AlertTriangle className="w-4 h-4 text-amber-500 mr-2" />
            <span className="text-sm text-amber-800">{rangeNotice}</span>
          </div>
        </div>
      )}

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
              <Activity className="w-4 h-4 mr-2" />
              {t('analysis.ai_insights.stock_parameters_title')}
            </h3>
            <table className="w-full text-sm">
              <tbody>
                <tr className="border-b border-gray-100">
                  <td className="py-2 text-gray-500 w-1/6">{t('analysis.ai_insights.stock_symbol_label')}</td>
                  <td className="py-2 w-1/6">
                    <select
                      value={selectedStock}
                      onChange={(e) => setSelectedStock(e.target.value)}
                      className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                    >
                      {portfolioStocks.length === 0 ? (
                        <option value="">{t('analysis.ai_insights.loading_option')}</option>
                      ) : (
                        portfolioStocks.map(stock => (
                          <option key={stock.symbol} value={stock.symbol}>
                            {stock.symbol} - {stock.name}
                          </option>
                        ))
                      )}
                    </select>
                  </td>
                  <td className="py-2 text-gray-500 w-1/6">{t('analysis.ai_insights.start_date_label')}</td>
                  <td className="py-2 w-1/6">
                    <input
                      type="date"
                      value={dateRange.start}
                      onChange={(e) => setDateRange(prev => ({ ...prev, start: e.target.value }))}
                      className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </td>
                  <td className="py-2 text-gray-500 w-1/6">{t('analysis.ai_insights.end_date_label')}</td>
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
              {t('analysis.ai_insights.technical_indicators_title')}
            </h3>
            <table className="w-full text-sm">
              <tbody>
                <tr className="border-b border-gray-100">
                  <td className="py-2 text-gray-500 w-1/6">{t('analysis.ai_insights.trend_label')}</td>
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
                  <td className="py-2 text-gray-500 w-1/6">{t('analysis.ai_insights.momentum_label')}</td>
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
                  <td className="py-2 text-gray-500 w-1/6">{t('analysis.ai_insights.volatility_label')}</td>
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
                  <td className="py-2 text-gray-500">{t('analysis.ai_insights.volume_label')}</td>
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
                {t('analysis.ai_insights.ai_score_title')}
              </h3>
              <table className="w-full text-sm">
                <tbody>
                  <tr className="border-b border-gray-100">
                    <td className="py-2 text-gray-500 w-1/6">{t('analysis.ai_insights.overall_score_label')}</td>
                    <td className="py-2 font-bold text-purple-600 w-1/6">{insights.ai_score.overall_score}</td>
                    <td className="py-2 text-gray-500 w-1/6">{t('analysis.ai_insights.confidence_label')}</td>
                    <td className={`py-2 font-semibold w-1/6 ${
                      insights.ai_score.confidence_level === 'High' ? 'text-green-600' :
                      insights.ai_score.confidence_level === 'Medium' ? 'text-yellow-600' : 'text-red-600'
                    }`}>{insights.ai_score.confidence_level}</td>
                    <td className="py-2 text-gray-500 w-1/6">{t('analysis.ai_insights.pattern_score_label')}</td>
                    <td className="py-2 font-semibold text-blue-600 w-1/6">{insights.ai_score.pattern_score}</td>
                  </tr>
                  <tr>
                    <td className="py-2 text-gray-500">{t('analysis.ai_insights.sentiment_score_label')}</td>
                    <td className="py-2 font-semibold text-green-600">{insights.ai_score.sentiment_score}</td>
                    <td className="py-2 text-gray-500">{t('analysis.ai_insights.risk_score_label')}</td>
                    <td className="py-2 font-semibold text-yellow-600">{insights.ai_score.risk_score}</td>
                    <td className="py-2 text-gray-500">{t('analysis.ai_insights.prediction_score_label')}</td>
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
                {t('analysis.ai_insights.market_sentiment_title')}
              </h3>
              <table className="w-full text-sm">
                <tbody>
                  <tr className="border-b border-gray-100">
                    <td className="py-2 text-gray-500 w-1/6">{t('analysis.ai_insights.sentiment_label')}</td>
                    <td className={`py-2 font-bold w-1/6 ${
                      insights.sentiment_analysis.sentiment_type.includes('positive') ? 'text-green-600' :
                      insights.sentiment_analysis.sentiment_type.includes('negative') ? 'text-red-600' : 'text-gray-600'
                    }`}>{insights.sentiment_analysis.sentiment_type.replace('_', ' ').toUpperCase()}</td>
                    <td className="py-2 text-gray-500 w-1/6">{t('analysis.ai_insights.score_label')}</td>
                    <td className="py-2 font-semibold w-1/6">{(insights.sentiment_analysis.score * 100).toFixed(1)}%</td>
                    <td className="py-2 text-gray-500 w-1/6">{t('analysis.ai_insights.confidence_label')}</td>
                    <td className="py-2 font-semibold w-1/6">{(insights.sentiment_analysis.confidence * 100).toFixed(1)}%</td>
                  </tr>
                  <tr>
                    <td className="py-2 text-gray-500">{t('analysis.ai_insights.news_count_label')}</td>
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
                {t('analysis.ai_insights.risk_assessment_title')}
              </h3>
              <table className="w-full text-sm">
                <tbody>
                  <tr className="border-b border-gray-100">
                    <td className="py-2 text-gray-500 w-1/6">{t('analysis.ai_insights.risk_level_label')}</td>
                    <td className={`py-2 font-bold w-1/6 ${
                      insights.risk_assessment.risk_level === 'low' ? 'text-green-600' :
                      insights.risk_assessment.risk_level === 'medium' ? 'text-yellow-600' :
                      insights.risk_assessment.risk_level === 'high' ? 'text-orange-600' : 'text-red-600'
                    }`}>{insights.risk_assessment.risk_level?.toUpperCase() || 'N/A'}</td>
                    <td className="py-2 text-gray-500 w-1/6">{t('analysis.ai_insights.risk_score_label_2')}</td>
                    <td className="py-2 font-semibold w-1/6">{insights.risk_assessment.risk_score?.toFixed(1) || 'N/A'}</td>
                    <td className="py-2 text-gray-500 w-1/6">{t('analysis.ai_insights.volatility_label')}</td>
                    <td className="py-2 font-semibold text-purple-600 w-1/6">{insights.risk_assessment.volatility?.toFixed(1) || 'N/A'}%</td>
                  </tr>
                  <tr>
                    <td className="py-2 text-gray-500">{t('analysis.ai_insights.beta_label')}</td>
                    <td className="py-2 font-semibold">{insights.risk_assessment.beta?.toFixed(2) || 'N/A'}</td>
                    <td className="py-2 text-gray-500">{t('analysis.ai_insights.var_95_label')}</td>
                    <td className="py-2 font-semibold text-red-600">{insights.risk_assessment.var_95?.toFixed(2) || 'N/A'}</td>
                    <td className="py-2 text-gray-500">{t('analysis.ai_insights.risk_factors_label')}</td>
                    <td className="py-2 text-xs text-gray-600">{insights.risk_assessment.factors?.length || 0} {t('analysis.ai_insights.identified_label')}</td>
                  </tr>
                </tbody>
              </table>
              {insights.risk_assessment.factors.length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-200">
                  <div className="flex flex-wrap gap-2">
                    {insights.risk_assessment.factors.map((factor, index) => (
                      <span key={index} className="inline-flex items-center px-2 py-1 bg-white rounded text-xs text-gray-700" title={factor.description || ''}>
                        <AlertTriangle className={`w-3 h-3 mr-1 ${
                          factor.level === 'high' ? 'text-red-500' :
                          factor.level === 'medium' ? 'text-yellow-500' : 'text-green-500'
                        }`} />
                        {factor.factor || factor}
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
                {t('analysis.ai_insights.pattern_recognition_title')}
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
                                  <div className="flex items-center" title={pattern.description || ''}>
                                    {isBullish && <TrendingUp className="w-3 h-3 text-green-500 mr-1" />}
                                    {isBearish && <TrendingDown className="w-3 h-3 text-red-500 mr-1" />}
                                    {pattern.pattern_name || pattern.pattern_type.replace('_', ' ')}
                                  </div>
                                </td>
                                <td className={`py-2 font-semibold w-1/6 ${isBullish ? 'text-green-600' : isBearish ? 'text-red-600' : 'text-blue-600'}`}>
                                  {Math.round(pattern.confidence * 100)}% <span className="text-gray-400 text-xs">({pattern.signal_strength})</span>
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
                {t('analysis.ai_insights.price_predictions_title')}
              </h3>
              <table className="w-full text-sm">
                <tbody>
                  {insights.price_prediction.random_forest && (
                    <tr className="border-b border-gray-100">
                      <td className="py-2 text-gray-500 w-1/6">{t('analysis.ai_insights.random_forest_label')}</td>
                      <td className="py-2 font-bold text-blue-600 w-1/6">{insights.price_prediction.random_forest.predicted_price?.toFixed(2) || 'N/A'}</td>
                      <td className="py-2 text-gray-500 w-1/6">{t('analysis.ai_insights.confidence_label')}</td>
                      <td className="py-2 font-semibold w-1/6">{((insights.price_prediction.random_forest.confidence || 0) * 100).toFixed(1)}%</td>
                      <td className="py-2 text-gray-500 w-1/6">{t('analysis.ai_insights.range_label')}</td>
                      <td className="py-2 font-semibold text-green-600 w-1/6">
                        {insights.price_prediction.random_forest.lower_bound?.toFixed(2) || 'N/A'} - {insights.price_prediction.random_forest.upper_bound?.toFixed(2) || 'N/A'}
                      </td>
                    </tr>
                  )}
                  {insights.price_prediction.xgboost && (
                    <tr className="border-b border-gray-100">
                      <td className="py-2 text-gray-500">{t('analysis.ai_insights.xgboost_label')}</td>
                      <td className="py-2 font-bold text-purple-600">{insights.price_prediction.xgboost.predicted_price?.toFixed(2) || 'N/A'}</td>
                      <td className="py-2 text-gray-500">{t('analysis.ai_insights.confidence_label')}</td>
                      <td className="py-2 font-semibold">{((insights.price_prediction.xgboost.confidence || 0) * 100).toFixed(1)}%</td>
                      <td className="py-2 text-gray-500">{t('analysis.ai_insights.range_label')}</td>
                      <td className="py-2 font-semibold text-green-600">
                        {insights.price_prediction.xgboost.lower_bound?.toFixed(2) || 'N/A'} - {insights.price_prediction.xgboost.upper_bound?.toFixed(2) || 'N/A'}
                      </td>
                    </tr>
                  )}
                  {insights.price_prediction.ensemble && (
                    <tr>
                      <td className="py-2 text-gray-500">{t('analysis.ai_insights.ensemble_label')}</td>
                      <td className="py-2 font-bold text-green-600">{insights.price_prediction.ensemble.predicted_price?.toFixed(2) || 'N/A'}</td>
                      <td className="py-2 text-gray-500">{t('analysis.ai_insights.confidence_label')}</td>
                      <td className="py-2 font-semibold">{((insights.price_prediction.ensemble.confidence || 0) * 100).toFixed(1)}%</td>
                      <td className="py-2 text-gray-500">{t('analysis.ai_insights.direction_label')}</td>
                      <td className={`py-2 font-semibold ${
                        insights.price_prediction.ensemble.direction === 'up' ? 'text-green-600' :
                        insights.price_prediction.ensemble.direction === 'down' ? 'text-red-600' : 'text-gray-600'
                      }`}>
                        {insights.price_prediction.ensemble.direction?.toUpperCase() || 'N/A'}
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
              <p className="text-gray-600">{t('analysis.ai_insights.analyzing_message')}</p>
            </div>
          )}

          {/* Default State */}
          {!insights && !loading && !error && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 text-center">
              <Brain className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-sm font-semibold text-gray-900 mb-2">{t('analysis.ai_insights.ready_title')}</h3>
              <p className="text-xs text-gray-600">
                {t('analysis.ai_insights.ready_message')}
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
