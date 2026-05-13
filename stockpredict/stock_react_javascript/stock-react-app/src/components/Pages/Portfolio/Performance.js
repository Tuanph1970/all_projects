import React, { useState, useEffect } from 'react';
import { stockAPI } from '../../../services/api';
import { LoadingSpinner, ErrorMessage } from '../../ui';
import { TrendingUp, TrendingDown, DollarSign, Percent, BarChart3, PieChart } from 'lucide-react';

const Performance = () => {
  const [portfolio, setPortfolio] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [timeframe, setTimeframe] = useState('1M');

  useEffect(() => {
    fetchPortfolioData();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeframe]);

  const fetchPortfolioData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Fetch both performance data and metrics in parallel
      const [performanceData, metricsData] = await Promise.all([
        stockAPI.getPortfolioPerformance(),
        stockAPI.getPortfolioMetrics(timeframe)
      ]);
      
      setPortfolio(performanceData);
      setMetrics(metricsData);
    } catch (err) {
      setError('Failed to fetch portfolio data. Please try again later.');
      console.error('Error fetching portfolio data:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  };

  const formatPercent = (value) => {
    const formatted = Math.abs(value).toFixed(2);
    return value >= 0 ? `+${formatted}%` : `-${formatted}%`;
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="performance-page">
      <div className="page-header">
        <h1>Hiệu suất danh mục</h1>
        <div className="timeframe-selector">
          {['1D', '1W', '1M', '3M', '6M', '1Y', 'ALL'].map(period => (
            <button
              key={period}
              onClick={() => setTimeframe(period)}
              className={`timeframe-btn ${timeframe === period ? 'active' : ''}`}
            >
              {period}
            </button>
          ))}
        </div>
      </div>

      {error && <ErrorMessage message={error} onClose={() => setError(null)} />}

      {metrics && (
        <>
          <div className="performance-overview">
            <div className="metric-card">
              <div className="metric-header">
                <DollarSign className="metric-icon" />
                <span>Tổng giá trị</span>
              </div>
              <div className="metric-value">{formatCurrency(metrics.total_value)}</div>
              <div className={`metric-change ${metrics.total_gain_loss >= 0 ? 'positive' : 'negative'}`}>
                {metrics.total_gain_loss >= 0 ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                {formatCurrency(Math.abs(metrics.total_gain_loss))} ({formatPercent(metrics.total_gain_loss_percent)})
              </div>
            </div>

            <div className="metric-card">
              <div className="metric-header">
                <Percent className="metric-icon" />
                <span>Lợi suất toàn bộ</span>
              </div>
              <div className={`metric-value ${metrics.total_gain_loss >= 0 ? 'positive' : 'negative'}`}>
                {formatPercent(metrics.total_gain_loss_percent)}
              </div>
              <div className="metric-subtitle">
                {formatCurrency(metrics.total_gain_loss)} lãi/lỗ
              </div>
            </div>

            <div className="metric-card">
              <div className="metric-header">
                <BarChart3 className="metric-icon" />
                <span>Tổng cổ phiếu</span>
              </div>
              <div className="metric-value">{metrics.total_stocks}</div>
              <div className="metric-subtitle">
                Vị thế đang mở
              </div>
            </div>

            <div className="metric-card">
              <div className="metric-header">
                <PieChart className="metric-icon" />
                <span>Đa dạng hóa</span>
              </div>
              <div className="metric-value">
                {metrics.total_stocks > 0 ? (100 / metrics.total_stocks).toFixed(1) : 0}%
              </div>
              <div className="metric-subtitle">
                Phân bổ TB mỗi cổ phiếu
              </div>
            </div>
          </div>

          <div className="performance-details">
            {metrics.top_performer && (
              <div className="performance-section">
                <h2>Hiệu suất cao nhất</h2>
                <div className="performer-card positive">
                  <div className="performer-info">
                    <h3>{metrics.top_performer.symbol}</h3>
                    <p>{metrics.top_performer.company_name}</p>
                  </div>
                  <div className="performer-metrics">
                    <span className="performer-value">
                      {formatCurrency(metrics.top_performer.value)}
                    </span>
                    <span className="performer-change">
                      {formatPercent(metrics.top_performer.gain_loss_percent)}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {metrics.worst_performer && metrics.worst_performer.symbol !== metrics.top_performer?.symbol && (
              <div className="performance-section">
                <h2>Hiệu suất thấp nhất</h2>
                <div className="performer-card negative">
                  <div className="performer-info">
                    <h3>{metrics.worst_performer.symbol}</h3>
                    <p>{metrics.worst_performer.company_name}</p>
                  </div>
                  <div className="performer-metrics">
                    <span className="performer-value">
                      {formatCurrency(metrics.worst_performer.value)}
                    </span>
                    <span className="performer-change">
                      {formatPercent(metrics.worst_performer.gain_loss_percent)}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="holdings-breakdown">
            <h2>Chi tiết nắm giữ</h2>
            <div className="holdings-list">
              {portfolio.map(stock => {
                const allocation = metrics.portfolio_distribution?.find(
                  d => d.symbol === stock.symbol
                )?.allocation || 0;

                return (
                  <div key={stock.symbol} className="holding-item">
                    <div className="holding-info">
                      <h3>{stock.symbol}</h3>
                      <p>{stock.company_name}</p>
                      <span className="holding-shares">{stock.shares} cổ phiếu</span>
                    </div>
                    <div className="holding-metrics">
                      <div className="holding-value">
                        {formatCurrency(stock.current_value)}
                      </div>
                      <div className="holding-allocation">
                        {allocation.toFixed(1)}%
                      </div>
                      <div className={`holding-change ${stock.gain_loss >= 0 ? 'positive' : 'negative'}`}>
                        {formatPercent(stock.gain_loss_percent)}
                      </div>
                    </div>
                    <div className="allocation-bar">
                      <div
                        className="allocation-fill"
                        style={{
                          width: `${allocation}%`,
                          backgroundColor: stock.gain_loss >= 0 ? '#10b981' : '#ef4444'
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {metrics.portfolio_distribution && metrics.portfolio_distribution.length > 0 && (
            <div className="portfolio-distribution">
              <h2>Phân bổ danh mục</h2>
              <div className="distribution-grid">
                {metrics.portfolio_distribution.map(item => (
                  <div key={item.symbol} className="distribution-item">
                    <div className="distribution-header">
                      <span className="distribution-symbol">{item.symbol}</span>
                      <span className="distribution-allocation">
                        {item.allocation.toFixed(1)}%
                      </span>
                    </div>
                    <div className="distribution-bar">
                      <div
                        className="distribution-fill"
                        style={{ width: `${item.allocation}%` }}
                      />
                    </div>
                    <div className="distribution-value">
                      {formatCurrency(item.value)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {(!portfolio || portfolio.length === 0) && !loading && (
        <div className="empty-state">
          <PieChart size={64} className="empty-icon" />
          <h2>Không có dữ liệu danh mục</h2>
          <p>Thêm cổ phiếu vào danh mục để xem các chỉ số hiệu suất.</p>
        </div>
      )}
    </div>
  );
};

export default Performance;