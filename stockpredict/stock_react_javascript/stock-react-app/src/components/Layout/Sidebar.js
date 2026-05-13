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
  BookOpen
} from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';

const Sidebar = ({ isOpen, onClose, isCollapsed, onToggleCollapse }) => {
  const [expandedMenus, setExpandedMenus] = useState({});
  const navigate = useNavigate();
  const location = useLocation();
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
      iconColor: '#3b82f6', // Blue - overview/home
      route: 'dashboard'
    },
    {
      key: 'priceboard',
      label: 'Bảng giá',
      icon: Table2,
      iconColor: '#06b6d4', // Cyan - data tables
      route: 'priceboard'
    },
    {
      key: 'stocks',
      label: 'Cổ phiếu',
      icon: TrendingUp,
      iconColor: '#10b981', // Green - stocks/growth
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
      iconColor: '#f59e0b', // Amber - activity/movement
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
      iconColor: '#8b5cf6', // Purple - AI/intelligence
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
      iconColor: '#ec4899', // Pink - play/simulation
      route: "simulation"
    },
    {
      key: 'chatbot',
      label: 'Trợ lý AI',
      icon: MessageCircle,
      iconColor: '#14b8a6', // Teal - communication
      submenu: [
        { key: 'chatbot-agent', label: 'Trò chuyện AI', route: 'chatbot' },
        { key: 'knowledge-qa', label: 'Knowledge QA', route: 'knowledge-qa' }
      ]
    },
    {
      key: 'analysis',
      label: 'Phân tích',
      icon: SearchCode,
      iconColor: '#6366f1', // Indigo - analysis/research
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
      iconColor: '#22c55e', // Emerald - money/wallet
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
      iconColor: '#f97316', // Orange - journaling/reflection
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
      key: 'tools',
      label: 'Công cụ',
      icon: Wrench,
      iconColor: '#64748b', // Slate - utilities/tools
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

  return (
    <>
      {isOpen && <div className="sidebar-overlay" onClick={onClose} />}

      <div className={`sidebar ${isOpen ? 'open' : ''} ${isCollapsed ? 'collapsed' : 'expanded'}`}>
        <div className="sidebar-header">
          <div className="sidebar-logo">
            <TrendingUp className="sidebar-logo-icon" />
            {!isCollapsed && <span className="sidebar-logo-text">StockAI</span>}
          </div>
          <button onClick={onClose} className="sidebar-close mobile-only">
            <X />
          </button>
        </div>

        {/* Toggle button for desktop - visible at bottom of sidebar */}
        <button
          onClick={onToggleCollapse}
          className="sidebar-toggle-btn desktop-only"
          title={isCollapsed ? 'Mở rộng menu' : 'Thu gọn menu'}
        >
          {isCollapsed ? <ChevronRight /> : <ChevronLeft />}
        </button>

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
                  <item.icon className="nav-icon" style={{ color: item.iconColor }} />
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
      </div>
    </>
  );
};

export default Sidebar;