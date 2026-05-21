// src/components/Layout/Header.js
import React, { useEffect, useState } from 'react';
import { LogOut, Menu, Search } from 'lucide-react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import NotificationBell from './NotificationBell';

// Map the current path segment to a Vietnamese page title shown as the
// H1 in the header. Falls back to a generic label for unknown routes so
// the header is never empty.
const PAGE_TITLES = {
  '': { title: 'Bảng điều khiển', emphasis: 'khiển' },
  dashboard: { title: 'Bảng điều khiển', emphasis: 'khiển' },
  priceboard: { title: 'Bảng giá', emphasis: 'giá' },
  stockscreener: { title: 'Lọc cổ phiếu', emphasis: 'phiếu' },
  byindustry: { title: 'Theo ngành', emphasis: 'ngành' },
  stocklist: { title: 'Danh sách cổ phiếu', emphasis: 'phiếu' },
  topgainer: { title: 'Tăng mạnh nhất', emphasis: 'nhất' },
  toploser: { title: 'Giảm mạnh nhất', emphasis: 'nhất' },
  topactive: { title: 'Giao dịch nhiều nhất', emphasis: 'nhất' },
  timeseries: { title: 'Chuỗi thời gian', emphasis: 'thời gian' },
  models: { title: 'Mô hình', emphasis: 'hình' },
  solutions: { title: 'Giải pháp', emphasis: 'pháp' },
  indicators: { title: 'Chỉ báo', emphasis: 'báo' },
  backtest: { title: 'Backtest', emphasis: '' },
  simulation: { title: 'Mô phỏng giao dịch', emphasis: 'giao dịch' },
  chatbot: { title: 'Trợ lý AI', emphasis: 'AI' },
  'knowledge-qa': { title: 'Knowledge QA', emphasis: 'QA' },
  technical: { title: 'Phân tích kỹ thuật', emphasis: 'thuật' },
  fundamental: { title: 'Phân tích cơ bản', emphasis: 'bản' },
  'ai-insights': { title: 'Phân tích AI', emphasis: 'AI' },
  holdings: { title: 'Cổ phiếu nắm giữ', emphasis: 'giữ' },
  performance: { title: 'Hiệu suất', emphasis: 'suất' },
  alerts: { title: 'Cảnh báo giá', emphasis: 'giá' },
  'journal-dashboard': { title: 'Tổng quan nhật ký', emphasis: 'nhật ký' },
  'journal-accounts': { title: 'Tài khoản', emphasis: 'khoản' },
  'trade-log': { title: 'Sổ giao dịch', emphasis: 'giao dịch' },
  'trade-diary': { title: 'Nhật ký giao dịch', emphasis: 'giao dịch' },
  'daily-planning': { title: 'Kế hoạch hàng ngày', emphasis: 'ngày' },
  'weekly-review': { title: 'Tổng kết tuần', emphasis: 'tuần' },
  'decision-console': { title: 'Decision Console', emphasis: 'Console' },
  'decision-board': { title: 'Watchlist Board', emphasis: 'Board' },
  'backtest-studio': { title: 'Backtest Studio', emphasis: 'Studio' },
  discipline: { title: 'Discipline', emphasis: '' },
  'scheduled-runs': { title: 'Scheduled Runs', emphasis: 'Runs' },
  scanner: { title: 'Scanner', emphasis: '' },
  analytics: { title: 'Analytics', emphasis: '' },
  'positions-open': { title: 'Open Positions', emphasis: 'Positions' },
  outcomes: { title: 'Trade Outcomes', emphasis: 'Outcomes' },
  'risk-dashboard': { title: 'Risk Dashboard', emphasis: 'Dashboard' },
  'watchlist-heatmap': { title: 'Watchlist Heat Map', emphasis: 'Heat Map' },
  calculator: { title: 'Máy tính đầu tư', emphasis: 'đầu tư' },
  watchlist: { title: 'Danh sách theo dõi', emphasis: 'theo dõi' },
  company: { title: 'Chi tiết cổ phiếu', emphasis: 'cổ phiếu' },
};

const formatTime = (d) =>
  d.toLocaleTimeString('vi-VN', { hour12: false });
const formatDate = (d) =>
  d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' });

const renderTitle = ({ title, emphasis }) => {
  if (!emphasis || !title.endsWith(emphasis)) {
    return <span>{title}</span>;
  }
  const head = title.slice(0, title.length - emphasis.length).trimEnd();
  return (
    <>
      {head}
      {head && ' '}
      <em>{emphasis}</em>
    </>
  );
};

const Header = ({ alertSlot }) => {
  const { logout } = useAuth();
  const location = useLocation();
  const segments = location.pathname.split('/').filter(Boolean);
  const key = segments.length === 0 ? '' : segments[0];
  const pageTitle = PAGE_TITLES[key] || { title: 'Bảng điều khiển', emphasis: 'khiển' };

  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <header className="header">
      <div className="header-content">
        <div className="header-left">
          {/* Mobile menu toggle */}
          <button
            onClick={() => document.dispatchEvent(new CustomEvent('toggleSidebar'))}
            className="menu-toggle mobile-only"
            title="Mở menu di động"
          >
            <Menu />
          </button>

          <div className="header-title-block">
            <div className="header-meta">
              <span className="header-meta-dot" />
              <span className="header-meta-text">
                CẬP NHẬT {formatTime(now)} · {formatDate(now)} · THỊ TRƯỜNG MỞ
              </span>
            </div>
            <h1 className="header-title">{renderTitle(pageTitle)}</h1>
          </div>
        </div>

        <div className="header-right">
          <div className="header-search">
            <Search className="header-search-icon" />
            <input
              type="text"
              placeholder="Tìm mã cổ phiếu..."
              className="header-search-input"
              aria-label="Tìm kiếm"
            />
            <span className="header-search-kbd">⌘K</span>
          </div>

          <NotificationBell />
          {alertSlot}

          <button onClick={logout} className="logout-button" title="Đăng xuất">
            <LogOut />
            <span className="logout-text">Đăng xuất</span>
          </button>
        </div>
      </div>
    </header>
  );
};

export default Header;
