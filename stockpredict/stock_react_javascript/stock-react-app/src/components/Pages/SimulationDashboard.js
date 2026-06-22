import React, { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import httpClient from "../../services/httpClient";
import { API_ENDPOINTS } from "../../constants/api";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from "recharts";
import { Settings, TrendingUp, BarChart3 } from "lucide-react";
import { getRechartsGridProps } from "../../constants/chartTheme";
import "./SimulationDashboard.css";

const SimulationDashboard = () => {
  const { t } = useTranslation();
  // State management
  const [tickers, setTickers] = useState([]);
  const [models, setModels] = useState([]);
  const [trainedSolutions, setTrainedSolutions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("parameters");

  // Form state
  const [formData, setFormData] = useState({
    ticker: "",
    startDate: "2023-01-01",
    endDate: "2024-01-01",
    modelType: "XGBoost",
    usePretrainedModel: false,
    pretrainedSolutionId: "",
    initialCapital: 100000000,
    thresholdBuy: 2.0,
    thresholdSell: -1.0,
    positionSize: 30,
    useIndicators: false
  });

  // Load initial data
  useEffect(() => {
    loadTickers();
    loadModels();
    loadTrainedSolutions();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadTickers = async () => {
    try {
      // First get the default portfolio
      const portfolioResult = await httpClient.get(API_ENDPOINTS.PORTFOLIO_DEFAULT);
      if (!portfolioResult.success || !portfolioResult.data) {
        console.error("Error loading default portfolio:", portfolioResult.error);
        setTickers([]);
        return;
      }

      const portfolioId = portfolioResult.data.id;

      // Then fetch holdings from the portfolio
      const holdingsResult = await httpClient.get(API_ENDPOINTS.PORTFOLIO_HOLDINGS(portfolioId));
      if (holdingsResult.success && Array.isArray(holdingsResult.data)) {
        // Map holdings to expected format {ticker, name}
        const tickerList = holdingsResult.data.map(holding => ({
          ticker: holding.symbol,
          name: holding.company_name || holding.symbol
        }));
        setTickers(tickerList);

        // Auto-select first ticker if available
        if (tickerList.length > 0 && !formData.ticker) {
          setFormData(prev => ({ ...prev, ticker: tickerList[0].ticker }));
        }
      } else {
        console.error("Error loading holdings:", holdingsResult.error);
        setTickers([]);
      }
    } catch (err) {
      console.error("Error loading tickers:", err);
      setTickers([]);
    }
  };

  const loadModels = async () => {
    try {
      const result = await httpClient.get(API_ENDPOINTS.SIMULATION_MODELS);
      if (result.success && result.data) {
        setModels(result.data);
      }
    } catch (err) {
      console.error("Error loading models:", err);
    }
  };

  const loadTrainedSolutions = async () => {
    try {
      const result = await httpClient.get(API_ENDPOINTS.SIMULATION_TRAINED_SOLUTIONS);
      if (result.success && result.data) {
        setTrainedSolutions(result.data);
      }
    } catch (err) {
      console.error("Error loading trained solutions:", err);
    }
  };

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const payload = {
        ticker: formData.ticker,
        start_date: formData.startDate,
        end_date: formData.endDate,
        initial_capital: parseFloat(formData.initialCapital),
        trading_params: {
          threshold_buy: parseFloat(formData.thresholdBuy) / 100,
          threshold_sell: parseFloat(formData.thresholdSell) / 100,
          position_size: parseFloat(formData.positionSize) / 100
        },
        use_indicators: formData.useIndicators
      };

      // Add pretrained model info or model type
      if (formData.usePretrainedModel && formData.pretrainedSolutionId) {
        payload.use_pretrained_model = true;
        payload.pretrained_solution_id = parseInt(formData.pretrainedSolutionId);
      } else {
        payload.use_pretrained_model = false;
        payload.model_type = formData.modelType;
      }

      const result = await httpClient.post(API_ENDPOINTS.SIMULATION_RUN, payload);
      if (result.success && result.data) {
        setResults(result.data);
        setActiveTab("result"); // Auto-switch to Result tab on success
      } else {
        setError(result.error?.message || "An error occurred during simulation");
        setActiveTab("result");
      }
    } catch (err) {
      setError(err.message || "An error occurred during simulation");
      console.error("Simulation error:", err);
      setActiveTab("result"); // Also switch to Result tab to show error
    } finally {
      setLoading(false);
    }
  };

  const numLocale = 'vi-VN';
  const formatCurrency = (value) => {
    return new Intl.NumberFormat(numLocale, {
      style: 'currency',
      currency: 'VND'
    }).format(value);
  };

  const formatPercent = (value) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  return (
    <div className="simulation-dashboard">
      <div className="dashboard-header">
        <h1>{t('simulation.title')}</h1>
        <p>{t('simulation.subtitle')}</p>
      </div>

      <div className="dashboard-content">
        {/* Tab Navigation */}
        <div className="tab-container">
          <div className="tab-navigation" style={{ background: 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)', padding: '12px 16px', gap: '8px', borderRadius: '16px' }}>
            <button
              className="tab-button"
              onClick={() => setActiveTab("parameters")}
              style={activeTab === "parameters"
                ? { background: 'linear-gradient(135deg, #3b82f6 0%, #6366f1 100%)', color: '#ffffff', boxShadow: '0 4px 15px rgba(99, 102, 241, 0.4)', transform: 'scale(1.02)', borderRadius: '12px' }
                : { background: 'transparent', color: '#64748b', borderRadius: '12px' }
              }
            >
              <Settings className={`tab-icon ${activeTab === "parameters" ? "animate-pulse" : ""}`} size={18} />
              <span>{t('simulation.tab_parameters')}</span>
            </button>
            <button
              className="tab-button"
              onClick={() => setActiveTab("trading")}
              style={activeTab === "trading"
                ? { background: 'linear-gradient(135deg, #8b5cf6 0%, #d946ef 100%)', color: '#ffffff', boxShadow: '0 4px 15px rgba(139, 92, 246, 0.4)', transform: 'scale(1.02)', borderRadius: '12px' }
                : { background: 'transparent', color: '#64748b', borderRadius: '12px' }
              }
            >
              <TrendingUp className={`tab-icon ${activeTab === "trading" ? "animate-pulse" : ""}`} size={18} />
              <span>{t('simulation.tab_trading')}</span>
            </button>
            <button
              className="tab-button"
              onClick={() => setActiveTab("result")}
              disabled={!results}
              style={activeTab === "result"
                ? { background: 'linear-gradient(135deg, #10b981 0%, #14b8a6 100%)', color: '#ffffff', boxShadow: '0 4px 15px rgba(16, 185, 129, 0.4)', transform: 'scale(1.02)', borderRadius: '12px' }
                : { background: 'transparent', color: !results ? '#94a3b8' : '#64748b', borderRadius: '12px', opacity: !results ? 0.4 : 1 }
              }
            >
              <BarChart3 className={`tab-icon ${activeTab === "result" ? "animate-pulse" : ""}`} size={18} />
              <span>{t('simulation.tab_results')}</span>
            </button>
          </div>

          <form onSubmit={handleSubmit}>
            {/* Tab 1: Parameters */}
            <div className={`tab-content ${activeTab === "parameters" ? "active" : ""}`}>
              <div className="configuration-panel">
                {/* Stock Selection */}
                <div className="form-section">
                  <h3>{t('simulation.section_stock_time')}</h3>
                  {tickers.length === 0 ? (
                    <div className="empty-portfolio-warning" style={{
                      backgroundColor: '#fff3cd',
                      border: '1px solid #ffc107',
                      borderRadius: '8px',
                      padding: '16px',
                      marginBottom: '16px'
                    }}>
                      <h4 style={{ color: '#856404', marginBottom: '8px' }}>{t('simulation.empty_portfolio_title')}</h4>
                      <p style={{ color: '#856404', marginBottom: '8px' }}>
                        {t('simulation.empty_portfolio_message')}
                      </p>
                      <a href="/portfolio" style={{ color: '#0d6efd' }}>{t('simulation.go_to_portfolio_link')}</a>
                    </div>
                  ) : (
                  <div className="form-row">
                    <div className="form-group">
                      <label>{t('simulation.label_ticker')}</label>
                      <select
                        name="ticker"
                        value={formData.ticker}
                        onChange={handleInputChange}
                        required
                      >
                        <option value="">{t('simulation.select_stock_placeholder')}</option>
                        {tickers.map((ticker) => (
                          <option key={ticker.ticker} value={ticker.ticker}>
                            {ticker.ticker} - {ticker.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  )}

                  <div className="form-row">
                    <div className="form-group">
                      <label>{t('simulation.label_start_date')}</label>
                      <input
                        type="date"
                        name="startDate"
                        value={formData.startDate}
                        onChange={handleInputChange}
                        required
                      />
                    </div>
                    <div className="form-group">
                      <label>{t('simulation.label_end_date')}</label>
                      <input
                        type="date"
                        name="endDate"
                        value={formData.endDate}
                        onChange={handleInputChange}
                        required
                      />
                    </div>
                  </div>
                </div>

                {/* ML Model Selection */}
                <div className="form-section">
                  <h3>{t('simulation.section_ml_model')}</h3>

                  <div className="form-group checkbox-group">
                    <label>
                      <input
                        type="checkbox"
                        name="usePretrainedModel"
                        checked={formData.usePretrainedModel}
                        onChange={handleInputChange}
                      />
                      {t('simulation.label_use_pretrained')}
                    </label>
                  </div>

                  {formData.usePretrainedModel ? (
                    <div className="form-group">
                      <label>{t('simulation.label_select_solution')}</label>
                      <select
                        name="pretrainedSolutionId"
                        value={formData.pretrainedSolutionId}
                        onChange={handleInputChange}
                        required
                      >
                        <option value="">{t('simulation.select_solution_placeholder')}</option>
                        {trainedSolutions.map((solution) => (
                          <option key={solution.solution_id} value={solution.solution_id}>
                            {solution.solution_name} - {solution.model_name} ({solution.ticker}) - {solution.training_period}
                          </option>
                        ))}
                      </select>
                      <small>{t('simulation.hint_pretrained_skip')}</small>
                    </div>
                  ) : (
                    <div className="form-group">
                      <label>{t('simulation.label_new_model')}</label>
                      <select
                        name="modelType"
                        value={formData.modelType}
                        onChange={handleInputChange}
                        required
                      >
                        {models.map((model) => (
                          <option key={model.model_type} value={model.model_type}>
                            {model.model_type} - {model.description}
                          </option>
                        ))}
                      </select>
                      <small>{t('simulation.hint_new_training')}</small>
                    </div>
                  )}

                  <div className="form-group checkbox-group">
                    <label>
                      <input
                        type="checkbox"
                        name="useIndicators"
                        checked={formData.useIndicators}
                        onChange={handleInputChange}
                      />
                      {t('simulation.label_use_indicators')}
                    </label>
                  </div>
                </div>

                <div className="tab-actions">
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={() => setActiveTab("trading")}
                  >
                    {t('simulation.btn_next_trading')}
                  </button>
                </div>
              </div>
            </div>

            {/* Tab 2: Trading Strategy */}
            <div className={`tab-content ${activeTab === "trading" ? "active" : ""}`}>
              <div className="configuration-panel">
                <div className="form-section">
                  <h3>{t('simulation.section_capital_position')}</h3>
                  <div className="form-group">
                    <label>{t('simulation.label_initial_capital')}</label>
                    <input
                      type="number"
                      name="initialCapital"
                      value={formData.initialCapital}
                      onChange={handleInputChange}
                      required
                      min="1000000"
                      step="1000000"
                    />
                  </div>

                  <div className="form-group">
                    <label>{t('simulation.label_position_size')}</label>
                    <input
                      type="number"
                      name="positionSize"
                      value={formData.positionSize}
                      onChange={handleInputChange}
                      min="1"
                      max="100"
                      step="1"
                    />
                    <small>{t('simulation.hint_position_size')}</small>
                  </div>
                </div>

                <div className="form-section">
                  <h3>{t('simulation.section_buy_sell_threshold')}</h3>
                  <div className="form-row">
                    <div className="form-group">
                      <label>{t('simulation.label_threshold_buy')}</label>
                      <input
                        type="number"
                        name="thresholdBuy"
                        value={formData.thresholdBuy}
                        onChange={handleInputChange}
                        step="0.1"
                        min="0"
                      />
                      <small>{t('simulation.hint_buy_threshold')}</small>
                    </div>
                    <div className="form-group">
                      <label>{t('simulation.label_threshold_sell')}</label>
                      <input
                        type="number"
                        name="thresholdSell"
                        value={formData.thresholdSell}
                        onChange={handleInputChange}
                        step="0.1"
                        max="0"
                      />
                      <small>{t('simulation.hint_sell_threshold')}</small>
                    </div>
                  </div>
                </div>

                <div className="tab-actions">
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => setActiveTab("parameters")}
                  >
                    {t('simulation.btn_back')}
                  </button>
                  <button
                    type="submit"
                    className="btn-primary"
                    disabled={loading}
                  >
                    {loading ? t('simulation.btn_running') : t('simulation.btn_run_simulation')}
                  </button>
                </div>
              </div>
            </div>

            {/* Tab 3: Result */}
            <div className={`tab-content ${activeTab === "result" ? "active" : ""}`}>
              {error && (
                <div className="results-panel error-panel">
                  <h2>{t('simulation.error_title')}</h2>
                  <p>{error}</p>
                </div>
              )}

              {results && (
                <div className="results-panel">
                  {/* Performance Metrics */}
                  <div className="metrics-section">
                    <h2>{t('simulation.section_performance_summary')}</h2>
                    <div className="metrics-grid">
                      <div className="metric-card">
                        <div className="metric-label">{t('simulation.metric_initial_capital')}</div>
                        <div className="metric-value">
                          {formatCurrency(results.portfolio_metrics.initial_capital)}
                        </div>
                      </div>
                      <div className="metric-card">
                        <div className="metric-label">{t('simulation.metric_final_value')}</div>
                        <div className="metric-value">
                          {formatCurrency(results.portfolio_metrics.final_value)}
                        </div>
                      </div>
                      <div className={`metric-card ${results.portfolio_metrics.total_return >= 0 ? 'positive' : 'negative'}`}>
                        <div className="metric-label">{t('simulation.metric_total_return')}</div>
                        <div className="metric-value">
                          {formatCurrency(results.portfolio_metrics.total_return)}
                        </div>
                        <div className="metric-sub">
                          {formatPercent(results.portfolio_metrics.total_return_pct)}
                        </div>
                      </div>
                      <div className="metric-card">
                        <div className="metric-label">{t('simulation.metric_total_trades')}</div>
                        <div className="metric-value">
                          {results.portfolio_metrics.total_trades}
                        </div>
                        <div className="metric-sub">
                          {t('simulation.metric_win_rate', { rate: results.portfolio_metrics.win_rate.toFixed(1) })}
                        </div>
                      </div>
                      <div className="metric-card">
                        <div className="metric-label">{t('simulation.metric_sharpe_ratio')}</div>
                        <div className="metric-value">
                          {results.portfolio_metrics.sharpe_ratio.toFixed(2)}
                        </div>
                      </div>
                      <div className="metric-card">
                        <div className="metric-label">{t('simulation.metric_max_drawdown')}</div>
                        <div className="metric-value negative">
                          {results.portfolio_metrics.max_drawdown.toFixed(2)}%
                        </div>
                      </div>
                      <div className={`metric-card ${results.portfolio_metrics.alpha >= 0 ? 'positive' : 'negative'}`}>
                        <div className="metric-label">{t('simulation.metric_alpha')}</div>
                        <div className="metric-value">
                          {formatPercent(results.portfolio_metrics.alpha)}
                        </div>
                      </div>
                      <div className="metric-card">
                        <div className="metric-label">{t('simulation.metric_prediction_accuracy')}</div>
                        <div className="metric-value">
                          {results.prediction_accuracy.direction_accuracy.toFixed(1)}%
                        </div>
                        <div className="metric-sub">
                          {t('simulation.metric_mape', { value: results.prediction_accuracy.mape.toFixed(2) })}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Price Chart with Predictions */}
                  <ResultChart
                    data={results.time_series}
                    transactions={results.transaction_history}
                  />

                  {/* Transaction History */}
                  <TransactionHistory transactions={results.transaction_history} />
                </div>
              )}

              {!results && !error && (
                <div className="no-results">
                  <div className="no-results-icon">📊</div>
                  <h3>{t('simulation.no_results_title')}</h3>
                  <p>{t('simulation.no_results_message')}</p>
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={() => setActiveTab("parameters")}
                  >
                    {t('simulation.btn_go_to_parameters')}
                  </button>
                </div>
              )}
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

// Custom triangle up shape for buy signals
const BuySignalShape = (props) => {
  const { cx, cy } = props;
  return (
    <text
      x={cx}
      y={cy}
      textAnchor="middle"
      dominantBaseline="middle"
      fill="#2196F3"
      fontSize="20"
      fontWeight="bold"
    >
      ^
    </text>
  );
};

// Custom triangle down shape for sell signals
const SellSignalShape = (props) => {
  const { cx, cy } = props;
  return (
    <text
      x={cx}
      y={cy}
      textAnchor="middle"
      dominantBaseline="middle"
      fill="#f44336"
      fontSize="20"
      fontWeight="bold"
    >
      V
    </text>
  );
};

// Result Chart Component with Buy/Sell signals
const ResultChart = ({ data, transactions }) => {
  const { t, i18n } = useTranslation();
  const dateLocale = i18n.language === 'en' ? 'en-GB' : 'vi-VN';
  const numLocale = 'vi-VN';

  // Prepare chart data with buy/sell markers
  const chartData = data.map((point) => {
    const buyTransaction = transactions.find(t => t.type === "BUY" && t.date === point.date);
    const sellTransaction = transactions.find(t => t.type === "SELL" && t.date === point.date);

    return {
      ...point,
      buySignal: buyTransaction ? point.actual_price : null,
      sellSignal: sellTransaction ? point.actual_price : null
    };
  });

  // Custom tooltip
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const dataPoint = payload[0].payload;
      return (
        <div className="custom-tooltip">
          <p className="tooltip-date">{new Date(label).toLocaleDateString(dateLocale)}</p>
          <p className="tooltip-actual">
            {t('simulation.tooltip_actual_price', { price: dataPoint.actual_price?.toLocaleString(numLocale) })}
          </p>
          <p className="tooltip-predicted">
            {t('simulation.tooltip_predicted_price', { price: dataPoint.predicted_price?.toLocaleString(numLocale) })}
          </p>
          {dataPoint.buySignal && (
            <p className="tooltip-buy">{t('simulation.tooltip_buy_signal')}</p>
          )}
          {dataPoint.sellSignal && (
            <p className="tooltip-sell">{t('simulation.tooltip_sell_signal')}</p>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="chart-section">
      <h2>{t('simulation.section_chart_title')}</h2>
      <ResponsiveContainer width="100%" height={620}>
        <LineChart data={chartData} margin={{ top: 16, right: 36, left: 28, bottom: 28 }}>
          <CartesianGrid
            stroke="#AEB6C2"
            strokeDasharray="3 3"
            horizontal
            vertical
          />
          <XAxis
            dataKey="date"
            tickFormatter={(date) => new Date(date).toLocaleDateString(dateLocale)}
            tick={getRechartsGridProps().tick}
            tickMargin={8}
            minTickGap={40}
            axisLine={{ stroke: "#D1D5DB" }}
            tickLine={{ stroke: "#9CA3AF" }}
            label={{
              value: t('simulation.axis_date', 'Date'),
              position: "insideBottom",
              offset: -16,
              fontSize: 12,
              fill: "#6B7280"
            }}
          />
          <YAxis
            tickFormatter={(value) => (value / 1000).toFixed(0) + 'K'}
            tick={getRechartsGridProps().tick}
            tickMargin={6}
            width={64}
            axisLine={{ stroke: "#D1D5DB" }}
            tickLine={{ stroke: "#9CA3AF" }}
            label={{
              value: t('simulation.axis_price', 'Price (VND)'),
              angle: -90,
              position: "insideLeft",
              style: { textAnchor: "middle" },
              fontSize: 12,
              fill: "#6B7280"
            }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            verticalAlign="top"
            height={32}
            iconType="plainline"
            wrapperStyle={{ fontSize: 13 }}
          />
          <Line
            type="monotone"
            dataKey="actual_price"
            stroke="#2563eb"
            strokeWidth={1.5}
            name={t('simulation.legend_actual_price')}
            dot={false}
            activeDot={{ r: 3 }}
          />
          <Line
            type="monotone"
            dataKey="predicted_price"
            stroke="#dc2626"
            strokeWidth={1.5}
            name={t('simulation.legend_predicted_price')}
            dot={false}
            activeDot={{ r: 3 }}
          />
          <Line
            type="monotone"
            dataKey="buySignal"
            stroke="transparent"
            dot={<BuySignalShape />}
            name="Buy Signal"
            legendType="none"
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="sellSignal"
            stroke="transparent"
            dot={<SellSignalShape />}
            name="Sell Signal"
            legendType="none"
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

// Original Price Chart Component (kept for backward compatibility)
// eslint-disable-next-line no-unused-vars -- legacy chart component preserved for re-enable
const PriceChart = ({ data, transactions }) => {
  return <ResultChart data={data} transactions={transactions} />;
};

// Transaction History Component
const TransactionHistory = ({ transactions }) => {
  const { t, i18n } = useTranslation();
  const dateLocale = i18n.language === 'en' ? 'en-GB' : 'vi-VN';
  const numLocale = 'vi-VN';
  return (
    <div className="transaction-section">
      <h2>{t('simulation.section_transaction_history')}</h2>
      <div className="transaction-table-wrapper">
        <table className="transaction-table">
          <thead>
            <tr>
              <th>{t('simulation.column_date')}</th>
              <th>{t('simulation.column_action')}</th>
              <th>{t('simulation.column_price')}</th>
              <th>{t('simulation.column_shares')}</th>
              <th>{t('simulation.column_total_value')}</th>
              <th>{t('simulation.column_portfolio_value')}</th>
              <th>{t('simulation.column_cash_balance')}</th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((transaction, index) => (
              <tr key={index} className={`transaction-${transaction.type.toLowerCase()}`}>
                <td>{new Date(transaction.date).toLocaleDateString(dateLocale)}</td>
                <td>
                  <span className={`badge badge-${transaction.type.toLowerCase()}`}>
                    {transaction.type}
                  </span>
                </td>
                <td>{transaction.price.toLocaleString(numLocale)}</td>
                <td>{transaction.shares.toLocaleString(numLocale)}</td>
                <td>{transaction.total_value.toLocaleString(numLocale)}</td>
                <td>{transaction.portfolio_value.toLocaleString(numLocale)}</td>
                <td>{transaction.cash_balance.toLocaleString(numLocale)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default SimulationDashboard;
