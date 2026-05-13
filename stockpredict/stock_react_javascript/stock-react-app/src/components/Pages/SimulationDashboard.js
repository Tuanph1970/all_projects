import React, { useState, useEffect } from "react";
import httpClient from "../../services/httpClient";
import { API_ENDPOINTS } from "../../constants/api";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from "recharts";
import { Settings, TrendingUp, BarChart3 } from "lucide-react";
import { getRechartsGridProps } from "../../constants/chartTheme";
import "./SimulationDashboard.css";

const SimulationDashboard = () => {
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

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('vi-VN', {
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
        <h1>Mô phỏng Giao dịch với AI</h1>
        <p>Huấn luyện mô hình ML để dự đoán giá cổ phiếu và mô phỏng chiến lược giao dịch</p>
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
              <span>Tham số</span>
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
              <span>Chiến lược giao dịch</span>
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
              <span>Kết quả</span>
            </button>
          </div>

          <form onSubmit={handleSubmit}>
            {/* Tab 1: Parameters */}
            <div className={`tab-content ${activeTab === "parameters" ? "active" : ""}`}>
              <div className="configuration-panel">
                {/* Stock Selection */}
                <div className="form-section">
                  <h3>Cổ phiếu & Thời gian</h3>
                  {tickers.length === 0 ? (
                    <div className="empty-portfolio-warning" style={{
                      backgroundColor: '#fff3cd',
                      border: '1px solid #ffc107',
                      borderRadius: '8px',
                      padding: '16px',
                      marginBottom: '16px'
                    }}>
                      <h4 style={{ color: '#856404', marginBottom: '8px' }}>Chưa có cổ phiếu trong danh mục</h4>
                      <p style={{ color: '#856404', marginBottom: '8px' }}>
                        Bạn cần thêm cổ phiếu vào danh mục trước khi chạy mô phỏng.
                      </p>
                      <a href="/portfolio" style={{ color: '#0d6efd' }}>Đi đến Danh mục →</a>
                    </div>
                  ) : (
                  <div className="form-row">
                    <div className="form-group">
                      <label>Mã cổ phiếu</label>
                      <select
                        name="ticker"
                        value={formData.ticker}
                        onChange={handleInputChange}
                        required
                      >
                        <option value="">Chọn cổ phiếu...</option>
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
                      <label>Ngày bắt đầu</label>
                      <input
                        type="date"
                        name="startDate"
                        value={formData.startDate}
                        onChange={handleInputChange}
                        required
                      />
                    </div>
                    <div className="form-group">
                      <label>Ngày kết thúc</label>
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
                  <h3>Mô hình ML</h3>

                  <div className="form-group checkbox-group">
                    <label>
                      <input
                        type="checkbox"
                        name="usePretrainedModel"
                        checked={formData.usePretrainedModel}
                        onChange={handleInputChange}
                      />
                      Sử dụng mô hình đã huấn luyện (Bỏ qua huấn luyện)
                    </label>
                  </div>

                  {formData.usePretrainedModel ? (
                    <div className="form-group">
                      <label>Chọn giải pháp đã huấn luyện</label>
                      <select
                        name="pretrainedSolutionId"
                        value={formData.pretrainedSolutionId}
                        onChange={handleInputChange}
                        required
                      >
                        <option value="">Chọn giải pháp...</option>
                        {trainedSolutions.map((solution) => (
                          <option key={solution.solution_id} value={solution.solution_id}>
                            {solution.solution_name} - {solution.model_name} ({solution.ticker}) - {solution.training_period}
                          </option>
                        ))}
                      </select>
                      <small>Sử dụng mô hình đã huấn luyện sẽ bỏ qua giai đoạn huấn luyện</small>
                    </div>
                  ) : (
                    <div className="form-group">
                      <label>Mô hình dự đoán (Huấn luyện mới)</label>
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
                      <small>Điều này sẽ huấn luyện mô hình mới từ đầu</small>
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
                      Sử dụng chỉ báo kỹ thuật (SMA, RSI, MACD)
                    </label>
                  </div>
                </div>

                <div className="tab-actions">
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={() => setActiveTab("trading")}
                  >
                    Tiếp: Chiến lược giao dịch →
                  </button>
                </div>
              </div>
            </div>

            {/* Tab 2: Trading Strategy */}
            <div className={`tab-content ${activeTab === "trading" ? "active" : ""}`}>
              <div className="configuration-panel">
                <div className="form-section">
                  <h3>Vốn & Vị thế</h3>
                  <div className="form-group">
                    <label>Vốn ban đầu (VND)</label>
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
                    <label>Kích thước vị thế (%)</label>
                    <input
                      type="number"
                      name="positionSize"
                      value={formData.positionSize}
                      onChange={handleInputChange}
                      min="1"
                      max="100"
                      step="1"
                    />
                    <small>Phần trăm vốn sử dụng cho mỗi giao dịch</small>
                  </div>
                </div>

                <div className="form-section">
                  <h3>Ngưỡng Mua/Bán</h3>
                  <div className="form-row">
                    <div className="form-group">
                      <label>Ngưỡng Mua (%)</label>
                      <input
                        type="number"
                        name="thresholdBuy"
                        value={formData.thresholdBuy}
                        onChange={handleInputChange}
                        step="0.1"
                        min="0"
                      />
                      <small>Mua khi lợi nhuận dự đoán vượt % này</small>
                    </div>
                    <div className="form-group">
                      <label>Ngưỡng Bán (%)</label>
                      <input
                        type="number"
                        name="thresholdSell"
                        value={formData.thresholdSell}
                        onChange={handleInputChange}
                        step="0.1"
                        max="0"
                      />
                      <small>Bán khi lợi nhuận dự đoán dưới % này</small>
                    </div>
                  </div>
                </div>

                <div className="tab-actions">
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => setActiveTab("parameters")}
                  >
                    ← Quay lại
                  </button>
                  <button
                    type="submit"
                    className="btn-primary"
                    disabled={loading}
                  >
                    {loading ? "Đang chạy mô phỏng..." : "Chạy mô phỏng"}
                  </button>
                </div>
              </div>
            </div>

            {/* Tab 3: Result */}
            <div className={`tab-content ${activeTab === "result" ? "active" : ""}`}>
              {error && (
                <div className="results-panel error-panel">
                  <h2>Lỗi</h2>
                  <p>{error}</p>
                </div>
              )}

              {results && (
                <div className="results-panel">
                  {/* Performance Metrics */}
                  <div className="metrics-section">
                    <h2>Tóm tắt Hiệu suất</h2>
                    <div className="metrics-grid">
                      <div className="metric-card">
                        <div className="metric-label">Vốn ban đầu</div>
                        <div className="metric-value">
                          {formatCurrency(results.portfolio_metrics.initial_capital)}
                        </div>
                      </div>
                      <div className="metric-card">
                        <div className="metric-label">Giá trị cuối</div>
                        <div className="metric-value">
                          {formatCurrency(results.portfolio_metrics.final_value)}
                        </div>
                      </div>
                      <div className={`metric-card ${results.portfolio_metrics.total_return >= 0 ? 'positive' : 'negative'}`}>
                        <div className="metric-label">Tổng lợi nhuận</div>
                        <div className="metric-value">
                          {formatCurrency(results.portfolio_metrics.total_return)}
                        </div>
                        <div className="metric-sub">
                          {formatPercent(results.portfolio_metrics.total_return_pct)}
                        </div>
                      </div>
                      <div className="metric-card">
                        <div className="metric-label">Tổng giao dịch</div>
                        <div className="metric-value">
                          {results.portfolio_metrics.total_trades}
                        </div>
                        <div className="metric-sub">
                          Tỷ lệ thắng: {results.portfolio_metrics.win_rate.toFixed(1)}%
                        </div>
                      </div>
                      <div className="metric-card">
                        <div className="metric-label">Tỷ lệ Sharpe</div>
                        <div className="metric-value">
                          {results.portfolio_metrics.sharpe_ratio.toFixed(2)}
                        </div>
                      </div>
                      <div className="metric-card">
                        <div className="metric-label">Sụt giảm tối đa</div>
                        <div className="metric-value negative">
                          {results.portfolio_metrics.max_drawdown.toFixed(2)}%
                        </div>
                      </div>
                      <div className={`metric-card ${results.portfolio_metrics.alpha >= 0 ? 'positive' : 'negative'}`}>
                        <div className="metric-label">Alpha (so với Mua & Giữ)</div>
                        <div className="metric-value">
                          {formatPercent(results.portfolio_metrics.alpha)}
                        </div>
                      </div>
                      <div className="metric-card">
                        <div className="metric-label">Độ chính xác dự đoán</div>
                        <div className="metric-value">
                          {results.prediction_accuracy.direction_accuracy.toFixed(1)}%
                        </div>
                        <div className="metric-sub">
                          MAPE: {results.prediction_accuracy.mape.toFixed(2)}%
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
                  <h3>Chưa có Kết quả</h3>
                  <p>Cấu hình tham số và chạy mô phỏng để xem kết quả tại đây.</p>
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={() => setActiveTab("parameters")}
                  >
                    Đi đến Tham số
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
          <p className="tooltip-date">{new Date(label).toLocaleDateString('vi-VN')}</p>
          <p className="tooltip-actual">
            Giá thực: {dataPoint.actual_price?.toLocaleString('vi-VN')} VND
          </p>
          <p className="tooltip-predicted">
            Dự đoán: {dataPoint.predicted_price?.toLocaleString('vi-VN')} VND
          </p>
          {dataPoint.buySignal && (
            <p className="tooltip-buy">Tín hiệu MUA</p>
          )}
          {dataPoint.sellSignal && (
            <p className="tooltip-sell">Tín hiệu BÁN</p>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="chart-section">
      <h2>Dự đoán Giá & Tín hiệu Giao dịch</h2>
      <div className="chart-legend-custom">
        <span className="legend-item">
          <span className="legend-line actual"></span> Giá thực tế
        </span>
        <span className="legend-item">
          <span className="legend-line predicted"></span> Giá dự đoán
        </span>
        <span className="legend-item buy-signal">
          <span className="signal-marker">^</span> Tín hiệu Mua
        </span>
        <span className="legend-item sell-signal">
          <span className="signal-marker">V</span> Tín hiệu Bán
        </span>
      </div>
      <ResponsiveContainer width="100%" height={450}>
        <LineChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid {...getRechartsGridProps().grid} />
          <XAxis
            dataKey="date"
            tickFormatter={(date) => new Date(date).toLocaleDateString('vi-VN')}
            tick={getRechartsGridProps().tick}
          />
          <YAxis
            tickFormatter={(value) => (value / 1000).toFixed(0) + 'K'}
            tick={getRechartsGridProps().tick}
          />
          <Tooltip content={<CustomTooltip />} />
          <Line
            type="monotone"
            dataKey="actual_price"
            stroke="#8884d8"
            strokeWidth={2}
            name="Actual Price"
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="predicted_price"
            stroke="#82ca9d"
            strokeWidth={2}
            name="Predicted Price"
            strokeDasharray="5 5"
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="buySignal"
            stroke="transparent"
            dot={<BuySignalShape />}
            name="Buy Signal"
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="sellSignal"
            stroke="transparent"
            dot={<SellSignalShape />}
            name="Sell Signal"
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
  return (
    <div className="transaction-section">
      <h2>Lịch sử Giao dịch</h2>
      <div className="transaction-table-wrapper">
        <table className="transaction-table">
          <thead>
            <tr>
              <th>Ngày</th>
              <th>Hành động</th>
              <th>Giá</th>
              <th>Số CP</th>
              <th>Tổng giá trị</th>
              <th>Giá trị DM</th>
              <th>Số dư TM</th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((transaction, index) => (
              <tr key={index} className={`transaction-${transaction.type.toLowerCase()}`}>
                <td>{new Date(transaction.date).toLocaleDateString('vi-VN')}</td>
                <td>
                  <span className={`badge badge-${transaction.type.toLowerCase()}`}>
                    {transaction.type}
                  </span>
                </td>
                <td>{transaction.price.toLocaleString('vi-VN')}</td>
                <td>{transaction.shares.toLocaleString()}</td>
                <td>{transaction.total_value.toLocaleString('vi-VN')}</td>
                <td>{transaction.portfolio_value.toLocaleString('vi-VN')}</td>
                <td>{transaction.cash_balance.toLocaleString('vi-VN')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default SimulationDashboard;
