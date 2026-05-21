// src/components/Layout/Sidebar.js
import React, { useState, useEffect, useCallback } from 'react';
import {
  X,
  ChevronDown,
  ChevronRight,
  ChevronLeft,
  TrendingUp,
  LayoutDashboard,
  Table2,
  Activity,
  BrainCircuit,
  PlayCircle,
  MessageCircle,
  SearchCode,
  Wallet,
  Wrench,
  BookOpen,
  Crosshair,
} from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

const Sidebar = ({ isOpen, onClose, isCollapsed, onToggleCollapse }) => {
  const [expandedMenus, setExpandedMenus] = useState({});
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  // The menu items below use `route: 'foo'` as a string id (matching the
  // legacy RouterContext convention). Derive the equivalent string from
  // the URL pathname so the existing isRouteActive logic keeps working
  // — '/' → 'dashboard', everything else → segments[0].
  const segments = location.pathname.split('/').filter(Boolean);
  const currentRoute = segments.length === 0 ? 'dashboard' : segments[0];

  const toggleMenu = (menuKey) => {
    // If sidebar is collapsed, expand it first when clicking on a menu with submenu
    if (isCollapsed) {
      onToggleCollapse();
    }
    setExpandedMenus(prev => ({
      ...prev,
      [menuKey]: !prev[menuKey]
    }));
  };

  // Collapse sidebar when route changes (after menu selection)
  const handleNavigation = useCallback((route) => {
    // Menu items still use the legacy string convention ('foo'); convert
    // to a URL path. Dashboard maps to '/' rather than '/dashboard' so
    // home is the canonical location.
    const path = route === 'dashboard' ? '/' : `/${route}`;
    navigate(path);
    // Auto-collapse sidebar after navigation (with small delay for visual feedback)
    setTimeout(() => {
      if (!isCollapsed && window.innerWidth >= 1024) {
        onToggleCollapse();
      }
    }, 150);
    // Close mobile sidebar
    if (window.innerWidth < 1024) {
      onClose();
    }
  }, [navigate, isCollapsed, onToggleCollapse, onClose]);

  const menuItems = [
    {
      key: 'dashboard',
      label: 'Bảng điều khiển',
      icon: LayoutDashboard,
      route: 'dashboard'
    },
    {
      key: 'priceboard',
      label: 'Bảng giá',
      icon: Table2,
      route: 'priceboard'
    },
    {
      key: 'stocks',
      label: 'Cổ phiếu',
      icon: TrendingUp,
      route: 'stocks',
      submenu:[
         { key: 'stockscreener', label: 'Lọc cổ phiếu', route: 'stockscreener' },
         { key: 'byindustry', label: 'Theo ngành', route: 'byindustry' },
         { key: 'stocklist', label: 'Danh sách CP', route: 'stocklist' }
      ]
    },
    {
      key: 'maketmover',
      label: 'Biến động thị trường',
      icon: Activity,
      submenu: [
        { key: 'topgainer', label: 'Tăng mạnh nhất', route: 'topgainer' },
        { key: 'toploser', label: 'Giảm mạnh nhất', route: 'toploser' },
        { key: 'topactive', label: 'Giao dịch nhiều nhất', route: 'topactive' }
      ]
    },
    {
      key: 'prediction',
      label: 'Dự đoán',
      icon: BrainCircuit,
      submenu: [
        { key: 'timeseries', label: 'Chuỗi thời gian', route: 'timeseries' },
        { key: 'models', label: 'Mô hình', route: 'models' },
        { key: 'solutions', label: 'Giải pháp', route: 'solutions' },
        { key: 'indicators', label: 'Chỉ báo', route: 'indicators' },
        { key: 'backtest', label: 'Backtest', route: 'backtest' }
      ]
    },
    {
      key: 'simulation',
      label: 'Mô phỏng giao dịch với AI',
      icon: PlayCircle,
      route: "simulation"
    },
    {
      key: 'chatbot',
      label: 'Trợ lý AI',
      icon: MessageCircle,
      submenu: [
        { key: 'chatbot-agent', label: 'Trò chuyện AI', route: 'chatbot' },
        { key: 'knowledge-qa', label: 'Knowledge QA', route: 'knowledge-qa' }
      ]
    },
    {
      key: 'analysis',
      label: 'Phân tích',
      icon: SearchCode,
      submenu: [
        { key: 'technical', label: 'Phân tích kỹ thuật', route: 'technical' },
        { key: 'fundamental', label: 'Phân tích cơ bản', route: 'fundamental' },
        { key: 'ai-insights', label: 'Phân tích AI', route: 'ai-insights' }
      ]
    },
    {
      key: 'portfolio',
      label: 'Danh mục',
      icon: Wallet,
      submenu: [
        { key: 'holdings', label: 'Cổ phiếu nắm giữ', route: 'holdings' },
        { key: 'performance', label: 'Hiệu suất', route: 'performance' },
        { key: 'alerts', label: 'Cảnh báo giá', route: 'alerts' }
      ]
    },
    {
      key: 'journal',
      label: 'Nhật ký giao dịch',
      icon: BookOpen,
      submenu: [
        { key: 'journal-dashboard', label: 'Tổng quan', route: 'journal-dashboard' },
        { key: 'journal-accounts', label: 'Tài khoản', route: 'journal-accounts' },
        { key: 'trade-log', label: 'Sổ giao dịch', route: 'trade-log' },
        { key: 'trade-diary', label: 'Nhật ký', route: 'trade-diary' },
        { key: 'daily-planning', label: 'Kế hoạch hàng ngày', route: 'daily-planning' },
        { key: 'weekly-review', label: 'Tổng kết tuần', route: 'weekly-review' }
      ]
    },
    {
      key: 'decision-helper',
      label: 'Decision Helper',
      icon: Crosshair,
      submenu: [
        { key: 'decision-console', label: 'Decision Console', route: 'decision-console' },
        { key: 'decision-board', label: 'Watchlist Board', route: 'decision-board' },
        { key: 'backtest-studio', label: 'Backtest Studio', route: 'backtest-studio' },
        { key: 'discipline', label: 'Discipline', route: 'discipline' },
        { key: 'scheduled-runs', label: 'Scheduled Runs', route: 'scheduled-runs' },
        { key: 'scanner', label: 'Scanner', route: 'scanner' },
        { key: 'watchlist-heatmap', label: 'Heat Map', route: 'watchlist-heatmap' },
        { key: 'analytics', label: 'Analytics', route: 'analytics' },
        { key: 'positions-open', label: 'Open Positions', route: 'positions-open' },
        { key: 'outcomes', label: 'Trade Outcomes', route: 'outcomes' },
        { key: 'risk-dashboard', label: 'Risk Dashboard', route: 'risk-dashboard' },
      ]
    },
    {
      key: 'tools',
      label: 'Công cụ',
      icon: Wrench,
      submenu: [
        { key: 'calculator', label: 'Máy tính đầu tư', route: 'calculator' },
        { key: 'watchlist', label: 'Danh sách theo dõi', route: 'watchlist' }
      ]
    }
  ];

  const isRouteActive = (route) => {
    return currentRoute === route;
  };

  const isParentActive = (submenu) => {
    return submenu && submenu.some(item => item.route === currentRoute);
  };

  // Close expanded menus when sidebar collapses
  useEffect(() => {
    if (isCollapsed) {
      setExpandedMenus({});
    }
  }, [isCollapsed]);

  const userEmail = user?.email || user?.username || '';
  const userInitials = (userEmail || 'U').slice(0, 2).toUpperCase();

  return (
    <>
      {isOpen && <div className="sidebar-overlay" onClick={onClose} />}

      <div className={`sidebar ${isOpen ? 'open' : ''} ${isCollapsed ? 'collapsed' : 'expanded'}`}>
        <div className="sidebar-header">
          <div className="sidebar-logo">
            <TrendingUp className="sidebar-logo-icon" />
            {!isCollapsed && (
              <span className="sidebar-logo-text">
                Stock<em>AI</em>
              </span>
            )}
          </div>
          <button onClick={onClose} className="sidebar-close mobile-only">
            <X />
          </button>
        </div>

        <nav className="sidebar-nav">
          {menuItems.map((item) => (
            <div key={item.key} className="nav-item">
              <button
                onClick={() => {
                  if (item.submenu) {
                    toggleMenu(item.key);
                  } else {
                    handleNavigation(item.route);
                  }
                }}
                className={`nav-button ${isRouteActive(item.route) || isParentActive(item.submenu) ? 'active' : ''}`}
                title={isCollapsed ? item.label : ''}
              >
                <div className="nav-button-content">
                  <item.icon className="nav-icon" />
                  {!isCollapsed && <span className="nav-button-text">{item.label}</span>}
                </div>
                {!isCollapsed && item.submenu && (
                  expandedMenus[item.key] ?
                    <ChevronDown className="nav-chevron" /> :
                    <ChevronRight className="nav-chevron" />
                )}
              </button>

              {!isCollapsed && item.submenu && expandedMenus[item.key] && (
                <div className="nav-submenu">
                  {item.submenu.map((subitem) => (
                    <button
                      key={subitem.key}
                      onClick={() => handleNavigation(subitem.route)}
                      className={`nav-submenu-item ${isRouteActive(subitem.route) ? 'active' : ''}`}
                    >
                      {subitem.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
        </nav>

        <div className="sidebar-footer">
          {!isCollapsed && (
            <div className="sidebar-user">
              <div className="sidebar-user-avatar">{userInitials}</div>
              <div className="sidebar-user-info">
                <div className="sidebar-user-email" title={userEmail}>
                  {userEmail || 'Khách'}
                </div>
                <div className="sidebar-user-role">Tài khoản cá nhân</div>
              </div>
            </div>
          )}
          {isCollapsed && (
            <div className="sidebar-user collapsed" title={userEmail}>
              <div className="sidebar-user-avatar">{userInitials}</div>
            </div>
          )}

          <button
            onClick={onToggleCollapse}
            className="sidebar-toggle-btn desktop-only"
            title={isCollapsed ? 'Mở rộng menu' : 'Thu gọn menu'}
          >
            {isCollapsed ? <ChevronRight /> : <ChevronLeft />}
            {!isCollapsed && <span>Thu gọn menu</span>}
          </button>
        </div>
      </div>
    </>
  );
};

export default Sidebar;
