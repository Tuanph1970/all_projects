import React, { useState, useEffect, useCallback } from 'react';
import {
  BarChart3, TrendingUp, TrendingDown, Target, Activity,
  DollarSign, Percent, Clock, Award, AlertTriangle,
  Shield, ChevronDown, RefreshCw, ArrowUpRight, ArrowDownRight,
  PieChart, Calendar, Zap
} from 'lucide-react';
import {
  LineChart, Line, BarChart, Bar, PieChart as RechartsPie, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Area, AreaChart, Legend
} from 'recharts';
import journalService from '../../../services/journalService';
import '../../../styles/journal.css';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];

const JournalDashboard = () => {
  const [accounts, setAccounts] = useState([]);
  const [selectedAccountId, setSelectedAccountId] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load accounts
  useEffect(() => {
    const loadAccounts = async () => {
      try {
        const res = await journalService.getAccounts();
        const data = res.data || res;
        setAccounts(Array.isArray(data) ? data : []);
        if (data.length > 0) {
          setSelectedAccountId(data[0].id);
        }
      } catch (err) {
        setError('Không thể tải danh sách tài khoản');
      } finally {
        setLoading(false);
      }
    };
    loadAccounts();
  }, []);

  // Load dashboard data when account changes
  const loadDashboard = useCallback(async () => {
    if (!selectedAccountId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await journalService.getDashboard(selectedAccountId);
      setDashboard(res.data || res);
    } catch (err) {
      setError('Không thể tải dữ liệu dashboard');
    } finally {
      setLoading(false);
    }
  }, [selectedAccountId]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const fmt = (v, currency) => journalService.formatCurrency(v, currency);
  const fmtPct = (v) => journalService.formatPercent(v);

  if (loading && !dashboard) {
    return (
      <div className="journal-accounts">
        <div className="journal-empty">
          <RefreshCw size={40} className="spin" />
          <p>Đang tải dashboard...</p>
        </div>
      </div>
    );
  }

  if (accounts.length === 0) {
    return (
      <div className="journal-accounts">
        <div className="journal-empty">
          <BarChart3 size={48} />
          <h3>Chưa có tài khoản journal</h3>
          <p>Tạo tài khoản trong mục "Tài khoản" để bắt đầu theo dõi giao dịch.</p>
        </div>
      </div>
    );
  }

  const account = dashboard?.account;
  const stats = dashboard?.stats;
  const cumRisk = dashboard?.cumulative_risk;
  const equityCurve = dashboard?.equity_curve || [];
  const byTicker = dashboard?.by_ticker || [];
  const byDirection = dashboard?.by_direction || [];
  const byMonth = dashboard?.by_month || [];
  const currency = account?.currency || 'VND';

  // Risk level color
  const getRiskColor = (pct) => {
    if (pct >= 100) return '#ef4444';
    if (pct >= 70) return '#f59e0b';
    return '#10b981';
  };

  const riskPct = cumRisk?.risk_used_pct || 0;

  return (
    <div className="jdash">
      {/* Header */}
      <div className="jdash-header">
        <div className="jdash-title">
          <BarChart3 size={22} />
          <h2>Dashboard Giao Dịch</h2>
        </div>
        <div className="jdash-controls">
          <select
            value={selectedAccountId || ''}
            onChange={(e) => setSelectedAccountId(Number(e.target.value))}
            className="jdash-account-select"
          >
            {accounts.map(a => (
              <option key={a.id} value={a.id}>{a.account_name}</option>
            ))}
          </select>
          <button onClick={loadDashboard} className="btn-icon" title="Làm mới">
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      {error && <div className="jdash-error">{error}</div>}

      {dashboard && (
        <>
          {/* Account Summary Bar */}
          <div className="jdash-summary-bar">
            <div className="jdash-summary-item">
              <span className="jdash-summary-label">Vốn ban đầu</span>
              <span className="jdash-summary-value">{fmt(account?.starting_equity, currency)}</span>
            </div>
            <div className="jdash-summary-item">
              <span className="jdash-summary-label">Vốn hiện tại</span>
              <span className="jdash-summary-value">{fmt(account?.current_equity, currency)}</span>
            </div>
            <div className="jdash-summary-item">
              <span className="jdash-summary-label">Tổng P/L</span>
              <span className={`jdash-summary-value ${stats?.total_pnl > 0 ? 'positive' : stats?.total_pnl < 0 ? 'negative' : ''}`}>
                {fmt(stats?.total_pnl, currency)}
              </span>
            </div>
            <div className="jdash-summary-item">
              <span className="jdash-summary-label">Lợi nhuận %</span>
              <span className={`jdash-summary-value ${stats?.total_return_pct > 0 ? 'positive' : stats?.total_return_pct < 0 ? 'negative' : ''}`}>
                {fmtPct(stats?.total_return_pct)}
              </span>
            </div>
          </div>

          {/* Stat Cards Grid */}
          <div className="jdash-cards">
            <StatCard
              icon={<Activity size={18} />}
              label="Tổng lệnh đã đóng"
              value={stats?.total_closed || 0}
              sub={`${stats?.total_open || 0} lệnh đang mở`}
              color="#3b82f6"
            />
            <StatCard
              icon={<Target size={18} />}
              label="Win Rate"
              value={`${stats?.win_rate || 0}%`}
              sub={`${stats?.win_count || 0}W / ${stats?.loss_count || 0}L`}
              color={stats?.win_rate >= 50 ? '#10b981' : '#f59e0b'}
            />
            <StatCard
              icon={<Zap size={18} />}
              label="Profit Factor"
              value={stats?.profit_factor || 0}
              sub={stats?.profit_factor >= 1.5 ? 'Tốt' : stats?.profit_factor >= 1 ? 'Trung bình' : 'Kém'}
              color={stats?.profit_factor >= 1.5 ? '#10b981' : stats?.profit_factor >= 1 ? '#f59e0b' : '#ef4444'}
            />
            <StatCard
              icon={<TrendingUp size={18} />}
              label="Avg R-Multiple"
              value={`${stats?.avg_r_multiple || 0}R`}
              sub={stats?.avg_r_multiple >= 1 ? 'Tích cực' : 'Cần cải thiện'}
              color={stats?.avg_r_multiple >= 1 ? '#10b981' : '#f59e0b'}
            />
            <StatCard
              icon={<DollarSign size={18} />}
              label="Expectancy"
              value={fmt(stats?.expectancy, currency)}
              sub="TB mỗi lệnh"
              color={stats?.expectancy > 0 ? '#10b981' : '#ef4444'}
            />
            <StatCard
              icon={<Award size={18} />}
              label="Streak"
              value={`${stats?.max_consecutive_wins || 0}W / ${stats?.max_consecutive_losses || 0}L`}
              sub="Max chuỗi thắng/thua"
              color="#8b5cf6"
            />
            <StatCard
              icon={<Clock size={18} />}
              label="TB thời gian"
              value={`${stats?.avg_duration_days || 0} ngày`}
              sub="mỗi giao dịch"
              color="#06b6d4"
            />
            <StatCard
              icon={<DollarSign size={18} />}
              label="TB Win / Loss"
              value={fmt(stats?.avg_win, currency)}
              sub={`Loss: ${fmt(stats?.avg_loss, currency)}`}
              color="#10b981"
            />
          </div>

          {/* Risk Monitor */}
          <div className="jdash-section">
            <div className="jdash-section-header">
              <Shield size={18} />
              <h3>Giám Sát Rủi Ro</h3>
            </div>
            <div className="jdash-risk-monitor">
              <div className="jdash-risk-bar-container">
                <div className="jdash-risk-labels">
                  <span>Rủi ro tích lũy</span>
                  <span style={{ color: getRiskColor(riskPct) }}>
                    {riskPct.toFixed(1)}% / {account?.max_cumulative_risk}%
                  </span>
                </div>
                <div className="jdash-risk-bar-track">
                  <div
                    className="jdash-risk-bar-fill"
                    style={{
                      width: `${Math.min(riskPct / (account?.max_cumulative_risk || 100) * 100, 100)}%`,
                      background: getRiskColor(riskPct)
                    }}
                  />
                  {/* Threshold markers */}
                  <div className="jdash-risk-marker" style={{ left: '70%' }} title="Cảnh báo (70%)" />
                  <div className="jdash-risk-marker jdash-risk-marker-danger" style={{ left: '100%' }} title="Giới hạn (100%)" />
                </div>
              </div>
              <div className="jdash-risk-details">
                <div className="jdash-risk-detail">
                  <span>Lệnh mở</span>
                  <strong>{cumRisk?.open_trades || 0}</strong>
                </div>
                <div className="jdash-risk-detail">
                  <span>Rủi ro đang dùng</span>
                  <strong style={{ color: getRiskColor(riskPct) }}>
                    {fmt(cumRisk?.total_risk_amount, currency)}
                  </strong>
                </div>
                <div className="jdash-risk-detail">
                  <span>Max / lệnh</span>
                  <strong>{account?.max_risk_per_trade}%</strong>
                </div>
                <div className="jdash-risk-detail">
                  <span>Còn có thể rủi ro</span>
                  <strong style={{ color: '#10b981' }}>
                    {fmt(cumRisk?.remaining_risk, currency)}
                  </strong>
                </div>
              </div>
              {riskPct >= 70 && (
                <div className={`jdash-risk-warning ${riskPct >= 100 ? 'danger' : 'caution'}`}>
                  <AlertTriangle size={16} />
                  {riskPct >= 100
                    ? 'Đã vượt giới hạn rủi ro tích lũy! Không nên mở thêm lệnh.'
                    : 'Rủi ro tích lũy đang ở mức cao. Cân nhắc giảm vị thế.'
                  }
                </div>
              )}
            </div>
          </div>

          {/* Equity Curve Chart */}
          <div className="jdash-section">
            <div className="jdash-section-header">
              <TrendingUp size={18} />
              <h3>Đường Vốn (Equity Curve)</h3>
            </div>
            <div className="jdash-chart-container">
              {equityCurve.length > 1 ? (
                <ResponsiveContainer width="100%" height={320}>
                  <AreaChart data={equityCurve} margin={{ top: 10, right: 30, left: 10, bottom: 0 }}>
                    <defs>
                      <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis
                      dataKey="date"
                      tick={{ fill: '#94a3b8', fontSize: 11 }}
                      tickFormatter={(v) => v ? v.substring(5) : ''}
                      stroke="rgba(255,255,255,0.1)"
                    />
                    <YAxis
                      tick={{ fill: '#94a3b8', fontSize: 11 }}
                      tickFormatter={(v) => v >= 1e6 ? `${(v/1e6).toFixed(1)}M` : v >= 1e3 ? `${(v/1e3).toFixed(0)}K` : v}
                      stroke="rgba(255,255,255,0.1)"
                    />
                    <Tooltip content={<EquityTooltip currency={currency} fmt={fmt} />} />
                    <Area
                      type="monotone"
                      dataKey="equity"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      fill="url(#equityGrad)"
                      dot={false}
                      activeDot={{ r: 5, fill: '#3b82f6' }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="jdash-chart-empty">
                  <p>Chưa có dữ liệu equity curve. Đóng ít nhất 1 giao dịch để xem biểu đồ.</p>
                </div>
              )}
            </div>
          </div>

          {/* Two-column: Monthly P/L Chart + By Direction */}
          <div className="jdash-grid-2">
            {/* Monthly P/L */}
            <div className="jdash-section">
              <div className="jdash-section-header">
                <Calendar size={18} />
                <h3>P/L Theo Tháng</h3>
              </div>
              <div className="jdash-chart-container">
                {byMonth.length > 0 ? (
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={byMonth} margin={{ top: 10, right: 20, left: 10, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                      <XAxis
                        dataKey="month"
                        tick={{ fill: '#94a3b8', fontSize: 11 }}
                        stroke="rgba(255,255,255,0.1)"
                      />
                      <YAxis
                        tick={{ fill: '#94a3b8', fontSize: 11 }}
                        tickFormatter={(v) => v >= 1e6 ? `${(v/1e6).toFixed(1)}M` : v >= 1e3 ? `${(v/1e3).toFixed(0)}K` : v}
                        stroke="rgba(255,255,255,0.1)"
                      />
                      <Tooltip content={<MonthlyTooltip currency={currency} fmt={fmt} />} />
                      <Bar dataKey="total_pnl" radius={[4, 4, 0, 0]}>
                        {byMonth.map((entry, i) => (
                          <Cell key={i} fill={entry.total_pnl >= 0 ? '#10b981' : '#ef4444'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="jdash-chart-empty"><p>Chưa có dữ liệu.</p></div>
                )}
              </div>
            </div>

            {/* By Direction */}
            <div className="jdash-section">
              <div className="jdash-section-header">
                <PieChart size={18} />
                <h3>Phân Tích Long/Short</h3>
              </div>
              <div className="jdash-direction-cards">
                {byDirection.length > 0 ? byDirection.map((d, i) => (
                  <div key={d.direction} className="jdash-direction-card">
                    <div className="jdash-dir-header">
                      {d.direction === 'Long' ? (
                        <ArrowUpRight size={18} className="jdash-dir-icon long" />
                      ) : (
                        <ArrowDownRight size={18} className="jdash-dir-icon short" />
                      )}
                      <span className="jdash-dir-label">{d.direction}</span>
                      <span className="jdash-dir-count">{d.trade_count} lệnh</span>
                    </div>
                    <div className="jdash-dir-stats">
                      <div className="jdash-dir-stat">
                        <span>P/L</span>
                        <strong className={d.total_pnl >= 0 ? 'positive' : 'negative'}>
                          {fmt(d.total_pnl, currency)}
                        </strong>
                      </div>
                      <div className="jdash-dir-stat">
                        <span>Win Rate</span>
                        <strong>{d.win_rate}%</strong>
                      </div>
                      <div className="jdash-dir-stat">
                        <span>Avg R</span>
                        <strong>{d.avg_r}R</strong>
                      </div>
                    </div>
                  </div>
                )) : (
                  <div className="jdash-chart-empty"><p>Chưa có dữ liệu.</p></div>
                )}
              </div>
            </div>
          </div>

          {/* By Ticker Analysis */}
          <div className="jdash-section">
            <div className="jdash-section-header">
              <BarChart3 size={18} />
              <h3>Phân Tích Theo Mã</h3>
            </div>
            {byTicker.length > 0 ? (
              <div className="jdash-ticker-table-wrap">
                <table className="jdash-ticker-table">
                  <thead>
                    <tr>
                      <th>Mã CK</th>
                      <th>Số lệnh</th>
                      <th>Tổng P/L</th>
                      <th>Win</th>
                      <th>Win Rate</th>
                      <th>TB P/L</th>
                    </tr>
                  </thead>
                  <tbody>
                    {byTicker.map((t, i) => (
                      <tr key={t.ticker}>
                        <td className="jdash-ticker-name">
                          <span className="jdash-ticker-rank" style={{ background: COLORS[i % COLORS.length] }}>
                            {i + 1}
                          </span>
                          {t.ticker}
                        </td>
                        <td>{t.trade_count}</td>
                        <td className={t.total_pnl >= 0 ? 'positive' : 'negative'}>
                          {fmt(t.total_pnl, currency)}
                        </td>
                        <td>{t.win_count}</td>
                        <td>
                          <span className={`jdash-wr-badge ${t.win_rate >= 50 ? 'good' : 'poor'}`}>
                            {t.win_rate}%
                          </span>
                        </td>
                        <td className={t.avg_pnl >= 0 ? 'positive' : 'negative'}>
                          {fmt(t.avg_pnl, currency)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="jdash-chart-empty"><p>Chưa có dữ liệu giao dịch theo mã.</p></div>
            )}
          </div>

          {/* Best / Worst Trade */}
          <div className="jdash-grid-2">
            <div className="jdash-highlight-card best">
              <TrendingUp size={20} />
              <div>
                <span className="jdash-hl-label">Lệnh tốt nhất</span>
                <span className="jdash-hl-value positive">{fmt(stats?.best_trade_pnl, currency)}</span>
              </div>
            </div>
            <div className="jdash-highlight-card worst">
              <TrendingDown size={20} />
              <div>
                <span className="jdash-hl-label">Lệnh tệ nhất</span>
                <span className="jdash-hl-value negative">{fmt(stats?.worst_trade_pnl, currency)}</span>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

// =============================================================================
// Sub-components
// =============================================================================

const StatCard = ({ icon, label, value, sub, color }) => (
  <div className="jdash-stat-card">
    <div className="jdash-stat-icon" style={{ color }}>
      {icon}
    </div>
    <div className="jdash-stat-body">
      <span className="jdash-stat-label">{label}</span>
      <span className="jdash-stat-value">{value}</span>
      {sub && <span className="jdash-stat-sub">{sub}</span>}
    </div>
  </div>
);

const EquityTooltip = ({ active, payload, currency, fmt }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="jdash-tooltip">
      <div className="jdash-tooltip-date">{d.date}</div>
      <div className="jdash-tooltip-row">
        <span>Equity:</span>
        <strong>{fmt(d.equity, currency)}</strong>
      </div>
      {d.trade && (
        <div className="jdash-tooltip-row">
          <span>{d.trade}</span>
          <strong className={d.pnl >= 0 ? 'positive' : 'negative'}>
            {fmt(d.pnl, currency)}
          </strong>
        </div>
      )}
    </div>
  );
};

const MonthlyTooltip = ({ active, payload, currency, fmt }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="jdash-tooltip">
      <div className="jdash-tooltip-date">{d.month}</div>
      <div className="jdash-tooltip-row">
        <span>P/L:</span>
        <strong className={d.total_pnl >= 0 ? 'positive' : 'negative'}>
          {fmt(d.total_pnl, currency)}
        </strong>
      </div>
      <div className="jdash-tooltip-row">
        <span>Lệnh:</span>
        <strong>{d.trade_count} ({d.win_count}W)</strong>
      </div>
      <div className="jdash-tooltip-row">
        <span>Win Rate:</span>
        <strong>{d.win_rate}%</strong>
      </div>
    </div>
  );
};

export default JournalDashboard;
