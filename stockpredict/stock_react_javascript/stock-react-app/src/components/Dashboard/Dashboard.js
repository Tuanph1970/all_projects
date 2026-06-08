// src/components/Dashboard/Dashboard.js
import React, { useState, useEffect } from 'react';
import { Inbox, Sparkles, Star } from 'lucide-react';
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

const Dashboard = () => {
  const [portfolio, setPortfolio] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [prospectiveStocks, setProspectiveStocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const { t } = useTranslation();

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
          <div
            className={`dashboard-stat-value ${totalGainLoss < 0 ? 'neg' : ''}`}
          >
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
      </div>

      {/* Portfolio card */}
      <section className="dashboard-card">
        <div className="dashboard-card-header">
          <div>
            <div className="dashboard-card-eyebrow">{t('dashboard.portfolio_eyebrow')}</div>
            <div className="dashboard-card-title">
              {(() => {
                const phrase = t('dashboard.portfolio_count', { count: portfolio.length });
                // Italicize everything after the leading count so layout
                // matches the serif/italic emphasis used elsewhere.
                const head = String(portfolio.length);
                const tail = phrase.startsWith(head) ? phrase.slice(head.length).trimStart() : phrase;
                return (
                  <>
                    {head} <em>{tail}</em>
                  </>
                );
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
              <div className="dashboard-empty-icon">
                <Inbox />
              </div>
              <div className="dashboard-empty-title">
                {t('dashboard.portfolio_empty_title')}
              </div>
              <div className="dashboard-empty-sub">
                {t('dashboard.portfolio_empty_sub')}
              </div>
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
                    <div className={`col col-num ${changeClass}`}>
                      {stock.change}
                    </div>
                    <div className="col col-num">
                      {(stock.shares * (stock.currentPrice || 0)).toLocaleString(
                        'vi-VN',
                        { maximumFractionDigits: 0 }
                      )} ₫
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
              {t('dashboard.ai_eyebrow', { count: recommendations.length })}
            </span>
          </div>
          <button
            type="button"
            className="dashboard-link-btn"
            onClick={() => navigate('/ai-insights')}
          >
            {t('common.see_all')} ›
          </button>
        </div>

        <div className="dashboard-rec-list">
          {recommendations.length === 0 ? (
            <div className="dashboard-empty">
              <div className="dashboard-empty-icon">
                <Sparkles />
              </div>
              <div className="dashboard-empty-title">{t('dashboard.ai_empty_title')}</div>
              <div className="dashboard-empty-sub">
                {t('dashboard.ai_empty_sub')}
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
                    <div className="rec-confidence-label">{t('dashboard.ai_confidence_label')}</div>
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
            <span>{t('dashboard.prospect_eyebrow')}</span>
          </div>
          <div className="dashboard-card-subtitle">
            {t('dashboard.prospect_subtitle')}
          </div>
        </div>

        <div className="dashboard-rec-list">
          {prospectiveStocks.length === 0 ? (
            <div className="dashboard-empty">
              <div className="dashboard-empty-icon">
                <Star />
              </div>
              <div className="dashboard-empty-title">
                {t('dashboard.prospect_empty_title')}
              </div>
              <div className="dashboard-empty-sub">
                {t('dashboard.prospect_empty_sub')}
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
                    <span className="metric-k">{t('dashboard.prospect_metric_price')}</span>
                    <span className="metric-v">
                      ${Number(stock.price || 0).toFixed(2)}
                    </span>
                  </div>
                  <div className="metric">
                    <span className="metric-k">{t('dashboard.prospect_metric_pe')}</span>
                    <span className="metric-v">
                      {Number(stock.peRatio || 0).toFixed(1)}
                    </span>
                  </div>
                  <div className="metric">
                    <span className="metric-k">{t('dashboard.prospect_metric_eps')}</span>
                    <span className="metric-v pos">
                      +{Number(stock.epsGrowth2Y || 0).toFixed(1)}%
                    </span>
                  </div>
                  <div className="metric">
                    <span className="metric-k">{t('dashboard.prospect_metric_profit')}</span>
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
