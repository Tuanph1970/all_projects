// src/components/Dashboard/Dashboard.js
import React, { useState, useEffect } from 'react';
import { Inbox, Sparkles, Star } from 'lucide-react';
import { stockAPI } from '../../services/api';
import { useNavigate } from 'react-router-dom';
import Contact from '../Contact/Contact';
import '../../styles/dashboard.css';

const formatUSD = (n) =>
  `$${Number(n || 0).toLocaleString('en-US', { maximumFractionDigits: 2 })}`;

const formatSigned = (n) => {
  const v = Number(n || 0);
  const sign = v > 0 ? '+' : v < 0 ? '−' : '+';
  return `${sign}$${Math.abs(v).toLocaleString('en-US', { maximumFractionDigits: 2 })}`;
};

const Dashboard = () => {
  const [portfolio, setPortfolio] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [prospectiveStocks, setProspectiveStocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const handleSymbolClick = (symbol) => {
    navigate(`/company/${symbol}`);
  };

  useEffect(() => {
    const loadDashboardData = async () => {
      try {
        setLoading(true);
        const [portfolioData, recommendationsData, prospectiveData] = await Promise.all([
          stockAPI.getPortfolio(),
          stockAPI.getRecommendations(),
          stockAPI.getProspectiveStocks()
        ]);
        setPortfolio(portfolioData);
        setRecommendations(recommendationsData);
        setProspectiveStocks(prospectiveData);
      } catch (error) {
        console.error('Error loading dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    loadDashboardData();
  }, []);

  const totalValue = portfolio.reduce(
    (sum, stock) => sum + (stock.shares * stock.currentPrice), 0
  );
  const totalGainLoss = portfolio.reduce(
    (sum, stock) => sum + (stock.shares * (stock.currentPrice - stock.avgPrice)), 0
  );

  const recommendationTone = (recommendation) => {
    switch ((recommendation || '').toLowerCase()) {
      case 'buy':  return 'buy';
      case 'sell': return 'sell';
      case 'hold': return 'hold';
      default:     return 'hold';
    }
  };

  const confidenceTone = (pct) => {
    const v = Number(pct) || 0;
    if (v >= 80) return 'pos';
    if (v >= 60) return 'amber';
    return 'neg';
  };

  if (loading) {
    return (
      <div className="dashboard">
        <div className="dashboard-stat-grid">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="dashboard-stat skeleton" />
          ))}
        </div>
        <div className="dashboard-card skeleton-tall" />
        <div className="dashboard-card skeleton-tall" />
      </div>
    );
  }

  return (
    <div className="dashboard">
      {/* Stat cards */}
      <div className="dashboard-stat-grid">
        <div className="dashboard-stat">
          <div className="dashboard-stat-label">Tổng giá trị</div>
          <div className="dashboard-stat-value">{formatUSD(totalValue)}</div>
          <div className="dashboard-stat-meta">
            {portfolio.length === 0 ? 'Chưa có khoản đầu tư' : 'Tổng hiện tại'}
          </div>
        </div>

        <div className="dashboard-stat">
          <div className="dashboard-stat-label">Lãi / Lỗ</div>
          <div
            className={`dashboard-stat-value ${totalGainLoss < 0 ? 'neg' : ''}`}
          >
            {formatSigned(totalGainLoss)}
          </div>
          <div className="dashboard-stat-meta">Hôm nay</div>
        </div>

        <div className="dashboard-stat">
          <div className="dashboard-stat-label">Cổ phiếu nắm giữ</div>
          <div className="dashboard-stat-value">{portfolio.length}</div>
          <div className="dashboard-stat-meta">
            {portfolio.length} mã đang nắm
          </div>
        </div>

        <div className="dashboard-stat">
          <div className="dashboard-stat-label">Thay đổi trong ngày</div>
          <div className="dashboard-stat-value pos">+2.34%</div>
          <div className="dashboard-stat-meta">VN-Index +0.42%</div>
        </div>
      </div>

      {/* Portfolio card */}
      <section className="dashboard-card">
        <div className="dashboard-card-header">
          <div>
            <div className="dashboard-card-eyebrow">Danh mục đầu tư</div>
            <div className="dashboard-card-title">
              {portfolio.length} <em>mã đang nắm giữ</em>
            </div>
          </div>
          <button
            type="button"
            className="dashboard-primary-btn"
            onClick={() => navigate('/holdings')}
          >
            + Thêm cổ phiếu
          </button>
        </div>

        <div className="dashboard-table">
          <div className="dashboard-table-head">
            <div className="col col-sym">Mã CP</div>
            <div className="col col-name">Công ty</div>
            <div className="col col-num">Số lượng</div>
            <div className="col col-num">Giá TB</div>
            <div className="col col-num">Giá hiện tại</div>
            <div className="col col-num">Thay đổi</div>
            <div className="col col-num">Giá trị</div>
          </div>

          {portfolio.length === 0 ? (
            <div className="dashboard-empty">
              <div className="dashboard-empty-icon">
                <Inbox />
              </div>
              <div className="dashboard-empty-title">
                Danh mục của bạn đang trống
              </div>
              <div className="dashboard-empty-sub">
                Bắt đầu thêm cổ phiếu để theo dõi hiệu suất danh mục của bạn theo
                thời gian thực
              </div>
              <button
                type="button"
                className="dashboard-secondary-btn"
                onClick={() => navigate('/stockscreener')}
              >
                Khám phá mã được khuyến nghị →
              </button>
            </div>
          ) : (
            <div className="dashboard-table-body">
              {portfolio.map((stock) => {
                const change = parseFloat(stock.change);
                const changeClass = change >= 0 ? 'pos' : 'neg';
                return (
                  <div className="dashboard-table-row" key={stock.symbol}>
                    <div
                      className="col col-sym sym"
                      onClick={() => handleSymbolClick(stock.symbol)}
                    >
                      {stock.symbol}
                    </div>
                    <div className="col col-name">{stock.name}</div>
                    <div className="col col-num">{stock.shares}</div>
                    <div className="col col-num">
                      ${Number(stock.avgPrice || 0).toFixed(2)}
                    </div>
                    <div className="col col-num">
                      ${Number(stock.currentPrice || 0).toFixed(2)}
                    </div>
                    <div className={`col col-num ${changeClass}`}>
                      {stock.change}
                    </div>
                    <div className="col col-num">
                      ${(stock.shares * (stock.currentPrice || 0)).toLocaleString(
                        'en-US',
                        { maximumFractionDigits: 2 }
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </section>

      {/* AI Recommendations */}
      <section className="dashboard-card">
        <div className="dashboard-card-header">
          <div className="dashboard-card-eyebrow with-icon">
            <Sparkles className="eyebrow-icon" />
            <span>
              Khuyến nghị AI · {recommendations.length} mã
            </span>
          </div>
          <button
            type="button"
            className="dashboard-link-btn"
            onClick={() => navigate('/ai-insights')}
          >
            Xem tất cả ›
          </button>
        </div>

        <div className="dashboard-rec-list">
          {recommendations.length === 0 ? (
            <div className="dashboard-empty">
              <div className="dashboard-empty-icon">
                <Sparkles />
              </div>
              <div className="dashboard-empty-title">Chưa có khuyến nghị AI</div>
              <div className="dashboard-empty-sub">
                Vui lòng quay lại sau để xem khuyến nghị mới.
              </div>
            </div>
          ) : (
            recommendations.map((rec, idx) => {
              const tone = recommendationTone(rec.type || rec.recommendation);
              const conf = Number(rec.confidence) || 0;
              const confTone = confidenceTone(conf);
              return (
                <div className="dashboard-rec-row" key={idx}>
                  <div className={`rec-badge tone-${tone}`}>
                    {(rec.type || rec.recommendation || '').toUpperCase()}
                  </div>
                  <div className="rec-body">
                    <div className="rec-headline">
                      <span
                        className="rec-symbol"
                        onClick={() => handleSymbolClick(rec.symbol)}
                      >
                        {rec.symbol}
                      </span>
                      <span className="rec-sep">·</span>
                      <span className="rec-name">{rec.name}</span>
                    </div>
                    <div className="rec-reason">{rec.reason}</div>
                  </div>
                  <div className="rec-confidence">
                    <div className="rec-confidence-label">ĐỘ TIN CẬY</div>
                    <div className="rec-confidence-value">{conf}%</div>
                    <div className="rec-confidence-bar">
                      <div
                        className={`rec-confidence-bar-fill tone-${confTone}`}
                        style={{ width: `${Math.max(0, Math.min(100, conf))}%` }}
                      />
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </section>

      {/* Prospective stocks */}
      <section className="dashboard-card">
        <div className="dashboard-card-header column">
          <div className="dashboard-card-eyebrow with-icon">
            <Star className="eyebrow-icon" />
            <span>Cổ phiếu tiềm năng</span>
          </div>
          <div className="dashboard-card-subtitle">
            Dựa trên phân tích cơ bản: tin tức tích cực, tỷ số P/E hấp dẫn và tăng
            trưởng lợi nhuận 2 năm
          </div>
        </div>

        <div className="dashboard-rec-list">
          {prospectiveStocks.length === 0 ? (
            <div className="dashboard-empty">
              <div className="dashboard-empty-icon">
                <Star />
              </div>
              <div className="dashboard-empty-title">
                Chưa có cổ phiếu tiềm năng
              </div>
              <div className="dashboard-empty-sub">
                Hệ thống đang phân tích thị trường. Vui lòng quay lại sau để xem
                các mã được đề xuất.
              </div>
            </div>
          ) : (
            prospectiveStocks.map((stock, idx) => (
              <div className="dashboard-prospect-row" key={idx}>
                <div className="prospect-head">
                  <span
                    className="prospect-symbol"
                    onClick={() => handleSymbolClick(stock.symbol)}
                  >
                    {stock.symbol}
                  </span>
                  <span className="prospect-sector">{stock.sector}</span>
                </div>
                <div className="prospect-name">{stock.name}</div>
                <div className="prospect-metrics">
                  <div className="metric">
                    <span className="metric-k">GIÁ</span>
                    <span className="metric-v">
                      ${Number(stock.price || 0).toFixed(2)}
                    </span>
                  </div>
                  <div className="metric">
                    <span className="metric-k">P/E</span>
                    <span className="metric-v">
                      {Number(stock.peRatio || 0).toFixed(1)}
                    </span>
                  </div>
                  <div className="metric">
                    <span className="metric-k">EPS 2Y</span>
                    <span className="metric-v pos">
                      +{Number(stock.epsGrowth2Y || 0).toFixed(1)}%
                    </span>
                  </div>
                  <div className="metric">
                    <span className="metric-k">LNST 2Y</span>
                    <span className="metric-v pos">
                      +{Number(stock.netProfitGrowth2Y || 0).toFixed(1)}%
                    </span>
                  </div>
                </div>
                {stock.news && (
                  <div className="prospect-news">{stock.news}</div>
                )}
              </div>
            ))
          )}
        </div>
      </section>

      <Contact />
    </div>
  );
};

export default Dashboard;
