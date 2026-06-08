// src/components/Dashboard/Dashboard.js
import React, { useState, useEffect } from 'react';
import { Inbox, TrendingUp, BarChart2 } from 'lucide-react';
import { stockAPI } from '../../services/api';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import Contact from '../Contact/Contact';
import '../../styles/dashboard.css';

const formatVND = (n) =>
  `${Number(n || 0).toLocaleString('vi-VN', { maximumFractionDigits: 0 })} ₫`;

const formatSigned = (n) => {
  const v = Number(n || 0);
  const sign = v > 0 ? '+' : v < 0 ? '−' : '+';
  return `${sign}${Math.abs(v).toLocaleString('vi-VN', { maximumFractionDigits: 0 })} ₫`;
};

// Hourglass spinner shown while a section is loading
const SectionSpinner = ({ label }) => (
  <div className="dashboard-section-spinner">
    <span className="dashboard-hourglass">⏳</span>
    <span className="dashboard-spinner-label">{label}</span>
  </div>
);

const Dashboard = () => {
  const [portfolio, setPortfolio] = useState([]);
  const [portfolioLoading, setPortfolioLoading] = useState(true);

  const [longtermRecs, setLongtermRecs] = useState([]);
  const [longtermLoading, setLongtermLoading] = useState(true);

  const [shorttermRecs, setShorttermRecs] = useState([]);
  const [shorttermLoading, setShorttermLoading] = useState(true);

  const navigate = useNavigate();
  const { t } = useTranslation();

  const handleSymbolClick = (symbol) => {
    navigate(`/company/${symbol}`);
  };

  // Portfolio loads first (fast)
  useEffect(() => {
    stockAPI.getPortfolio()
      .then(setPortfolio)
      .catch(() => setPortfolio([]))
      .finally(() => setPortfolioLoading(false));
  }, []);

  // Long-term recs — independent, may take a while
  useEffect(() => {
    stockAPI.getLongtermRecommendations()
      .then(setLongtermRecs)
      .catch(() => setLongtermRecs([]))
      .finally(() => setLongtermLoading(false));
  }, []);

  // Short-term recs — independent
  useEffect(() => {
    stockAPI.getShorttermRecommendations()
      .then(setShorttermRecs)
      .catch(() => setShorttermRecs([]))
      .finally(() => setShorttermLoading(false));
  }, []);

  const totalValue = portfolio.reduce(
    (sum, stock) => sum + (stock.shares * stock.currentPrice), 0
  );
  const totalGainLoss = portfolio.reduce(
    (sum, stock) => sum + (stock.shares * (stock.currentPrice - stock.avgPrice)), 0
  );

  return (
    <div className="dashboard">
      {/* Stat cards */}
      <div className="dashboard-stat-grid">
        {portfolioLoading ? (
          [...Array(4)].map((_, i) => (
            <div key={i} className="dashboard-stat skeleton" />
          ))
        ) : (
          <>
            <div className="dashboard-stat">
              <div className="dashboard-stat-label">{t('dashboard.stat_total_value')}</div>
              <div className="dashboard-stat-value">{formatVND(totalValue)}</div>
              <div className="dashboard-stat-meta">
                {portfolio.length === 0
                  ? t('dashboard.stat_no_investments')
                  : t('dashboard.stat_total_current')}
              </div>
            </div>

            <div className="dashboard-stat">
              <div className="dashboard-stat-label">{t('dashboard.stat_pnl')}</div>
              <div className={`dashboard-stat-value ${totalGainLoss < 0 ? 'neg' : ''}`}>
                {formatSigned(totalGainLoss)}
              </div>
              <div className="dashboard-stat-meta">{t('dashboard.stat_today')}</div>
            </div>

            <div className="dashboard-stat">
              <div className="dashboard-stat-label">{t('dashboard.stat_holdings')}</div>
              <div className="dashboard-stat-value">{portfolio.length}</div>
              <div className="dashboard-stat-meta">
                {t('dashboard.stat_holdings_count', { count: portfolio.length })}
              </div>
            </div>

            <div className="dashboard-stat">
              <div className="dashboard-stat-label">{t('dashboard.stat_day_change')}</div>
              <div className="dashboard-stat-value pos">+2.34%</div>
              <div className="dashboard-stat-meta">{t('dashboard.stat_index_change')}</div>
            </div>
          </>
        )}
      </div>

      {/* Portfolio card */}
      <section className="dashboard-card">
        <div className="dashboard-card-header">
          <div>
            <div className="dashboard-card-eyebrow">{t('dashboard.portfolio_eyebrow')}</div>
            <div className="dashboard-card-title">
              {portfolioLoading ? '…' : (() => {
                const phrase = t('dashboard.portfolio_count', { count: portfolio.length });
                const head = String(portfolio.length);
                const tail = phrase.startsWith(head) ? phrase.slice(head.length).trimStart() : phrase;
                return <>{head} <em>{tail}</em></>;
              })()}
            </div>
          </div>
          <button
            type="button"
            className="dashboard-primary-btn"
            onClick={() => navigate('/holdings')}
          >
            {t('dashboard.portfolio_add')}
          </button>
        </div>

        {portfolioLoading ? (
          <div className="dashboard-card skeleton-tall" />
        ) : (
          <div className="dashboard-table">
            <div className="dashboard-table-head">
              <div className="col col-sym">{t('dashboard.col_symbol')}</div>
              <div className="col col-name">{t('dashboard.col_company')}</div>
              <div className="col col-num">{t('dashboard.col_shares')}</div>
              <div className="col col-num">{t('dashboard.col_avg_price')}</div>
              <div className="col col-num">{t('dashboard.col_current_price')}</div>
              <div className="col col-num">{t('dashboard.col_change')}</div>
              <div className="col col-num">{t('dashboard.col_value')}</div>
            </div>

            {portfolio.length === 0 ? (
              <div className="dashboard-empty">
                <div className="dashboard-empty-icon"><Inbox /></div>
                <div className="dashboard-empty-title">{t('dashboard.portfolio_empty_title')}</div>
                <div className="dashboard-empty-sub">{t('dashboard.portfolio_empty_sub')}</div>
                <button
                  type="button"
                  className="dashboard-secondary-btn"
                  onClick={() => navigate('/stockscreener')}
                >
                  {t('dashboard.portfolio_empty_cta')}
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
                        {Number(stock.avgPrice || 0).toLocaleString('vi-VN', { maximumFractionDigits: 0 })} ₫
                      </div>
                      <div className="col col-num">
                        {Number(stock.currentPrice || 0).toLocaleString('vi-VN', { maximumFractionDigits: 0 })} ₫
                      </div>
                      <div className={`col col-num ${changeClass}`}>{stock.change}</div>
                      <div className="col col-num">
                        {(stock.shares * (stock.currentPrice || 0)).toLocaleString(
                          'vi-VN', { maximumFractionDigits: 0 }
                        )} ₫
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </section>

      {/* Long-term recommendations */}
      <section className="dashboard-card">
        <div className="dashboard-card-header">
          <div className="dashboard-card-eyebrow with-icon">
            <BarChart2 className="eyebrow-icon" />
            <span>Khuyến nghị dài hạn</span>
          </div>
          <span className="dashboard-card-subtitle-inline">
            Top 3 VN30 · P/E &amp; lợi nhuận nhiều năm
          </span>
        </div>

        {longtermLoading ? (
          <SectionSpinner label="Đang phân tích cơ bản VN30…" />
        ) : longtermRecs.length === 0 ? (
          <div className="dashboard-empty">
            <div className="dashboard-empty-icon"><BarChart2 /></div>
            <div className="dashboard-empty-title">Chưa có khuyến nghị</div>
            <div className="dashboard-empty-sub">
              Không tìm thấy cổ phiếu đạt tiêu chí cơ bản dài hạn trong VN30.
            </div>
          </div>
        ) : (
          <div className="dashboard-rec-list">
            {longtermRecs.map((rec, idx) => (
              <div className="dashboard-rec-row" key={idx}>
                <div className="rec-badge tone-buy">DÀI HẠN</div>
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
                  <div className="rec-metrics">
                    {rec.pe != null && (
                      <span className="rec-metric">P/E: {rec.pe}x</span>
                    )}
                    {rec.roe != null && (
                      <span className="rec-metric">ROE: {rec.roe}%</span>
                    )}
                    {rec.profit_growth_years > 0 && (
                      <span className="rec-metric">
                        Lợi nhuận tăng {rec.profit_growth_years} năm
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Short-term recommendations */}
      <section className="dashboard-card">
        <div className="dashboard-card-header">
          <div className="dashboard-card-eyebrow with-icon">
            <TrendingUp className="eyebrow-icon" />
            <span>Khuyến nghị ngắn hạn</span>
          </div>
          <span className="dashboard-card-subtitle-inline">
            Top 3 VN30 · xu hướng tăng 1 năm
          </span>
        </div>

        {shorttermLoading ? (
          <SectionSpinner label="Đang phân tích xu hướng VN30…" />
        ) : shorttermRecs.length === 0 ? (
          <div className="dashboard-empty">
            <div className="dashboard-empty-icon"><TrendingUp /></div>
            <div className="dashboard-empty-title">Chưa có khuyến nghị</div>
            <div className="dashboard-empty-sub">
              Không tìm thấy cổ phiếu có xu hướng tăng đủ mạnh trong VN30.
            </div>
          </div>
        ) : (
          <div className="dashboard-rec-list">
            {shorttermRecs.map((rec, idx) => (
              <div className="dashboard-rec-row" key={idx}>
                <div className="rec-badge tone-buy">NGẮN HẠN</div>
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
                  <div className="rec-metrics">
                    <span className="rec-metric">
                      Giá: {Number(rec.current_price || 0).toLocaleString('vi-VN', { maximumFractionDigits: 0 })} ₫
                    </span>
                    <span className={`rec-metric ${rec.return_1y >= 0 ? 'pos' : 'neg'}`}>
                      1Y: {rec.return_1y >= 0 ? '+' : ''}{rec.return_1y}%
                    </span>
                    <span className={`rec-metric ${rec.return_20d >= 0 ? 'pos' : 'neg'}`}>
                      20D: {rec.return_20d >= 0 ? '+' : ''}{rec.return_20d}%
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <Contact />
    </div>
  );
};

export default Dashboard;
