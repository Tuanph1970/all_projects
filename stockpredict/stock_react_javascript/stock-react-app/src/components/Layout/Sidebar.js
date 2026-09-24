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
  BookOpen,
  Crosshair,
  Newspaper,
} from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../context/AuthContext';

const Sidebar = ({ isOpen, onClose, isCollapsed, onToggleCollapse }) => {
  const [expandedMenus, setExpandedMenus] = useState({});
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const { t } = useTranslation();
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
    { key: 'dashboard',   labelKey: 'sidebar.dashboard',  icon: LayoutDashboard, route: 'dashboard' },
    { key: 'priceboard',  labelKey: 'sidebar.priceboard', icon: Table2,          route: 'priceboard' },
    {
      key: 'stocks',
      labelKey: 'sidebar.stocks',
      icon: TrendingUp,
      route: 'stocks',
      submenu: [
        { key: 'stockscreener', labelKey: 'sidebar.stockscreener', route: 'stockscreener' },
        { key: 'byindustry',    labelKey: 'sidebar.byindustry',    route: 'byindustry' },
        { key: 'stocklist',     labelKey: 'sidebar.stocklist',     route: 'stocklist' }
      ]
    },
    {
      key: 'maketmover',
      labelKey: 'sidebar.marketmover',
      icon: Activity,
      submenu: [
        { key: 'topgainer', labelKey: 'sidebar.topgainer', route: 'topgainer' },
        { key: 'toploser',  labelKey: 'sidebar.toploser',  route: 'toploser' },
        { key: 'topactive', labelKey: 'sidebar.topactive', route: 'topactive' }
      ]
    },
    {
      key: 'prediction',
      labelKey: 'sidebar.prediction',
      icon: BrainCircuit,
      submenu: [
        { key: 'models',     labelKey: 'sidebar.models',     route: 'models' },
        { key: 'solutions',  labelKey: 'sidebar.solutions',  route: 'solutions' },
        { key: 'indicators', labelKey: 'sidebar.indicators', route: 'indicators' },
        { key: 'backtest',   labelKey: 'sidebar.backtest',   route: 'backtest' }
      ]
    },
    { key: 'simulation', labelKey: 'sidebar.simulation', icon: PlayCircle, route: 'simulation' },
    {
      key: 'chatbot',
      labelKey: 'sidebar.chatbot',
      icon: MessageCircle,
      submenu: [
        { key: 'chatbot-agent', labelKey: 'sidebar.chatbot_agent', route: 'chatbot' },
        { key: 'knowledge-qa',  labelKey: 'sidebar.knowledge_qa',  route: 'knowledge-qa' }
      ]
    },
    {
      key: 'analysis',
      labelKey: 'sidebar.analysis',
      icon: SearchCode,
      submenu: [
        { key: 'technical',    labelKey: 'sidebar.technical',    route: 'technical' },
        { key: 'fundamental',  labelKey: 'sidebar.fundamental',  route: 'fundamental' },
        { key: 'ai-insights',  labelKey: 'sidebar.ai_insights',  route: 'ai-insights' },
        { key: 'chart-decomp',  labelKey: 'sidebar.chart_decomp',  route: 'chart-decomp' },
        { key: 'vol-forecast',   labelKey: 'sidebar.vol_forecast',   route: 'vol-forecast' },
        { key: 'event-reaction', labelKey: 'sidebar.event_reaction', route: 'event-reaction' }
      ]
    },
    {
      key: 'portfolio',
      labelKey: 'sidebar.portfolio',
      icon: Wallet,
      submenu: [
        { key: 'holdings',    labelKey: 'sidebar.holdings',    route: 'holdings' },
        { key: 'performance', labelKey: 'sidebar.performance', route: 'performance' },
        { key: 'alerts',      labelKey: 'sidebar.alerts',      route: 'alerts' },
        { key: 'watchlist',   labelKey: 'sidebar.watchlist',   route: 'watchlist' }
      ]
    },
    {
      key: 'news',
      labelKey: 'sidebar.news',
      icon: Newspaper,
      submenu: [
        { key: 'tcb-news', labelKey: 'sidebar.tcb_news', route: 'tcb-news' }
      ]
    },
    {
      key: 'journal',
      labelKey: 'sidebar.journal',
      icon: BookOpen,
      submenu: [
        { key: 'journal-overview',  labelKey: 'sidebar.journal_overview',  route: 'journal-overview' },
        { key: 'journal-dashboard', labelKey: 'sidebar.journal_dashboard', route: 'journal-dashboard' },
        { key: 'journal-accounts',  labelKey: 'sidebar.journal_accounts',  route: 'journal-accounts' },
        { key: 'trade-log',         labelKey: 'sidebar.trade_log',         route: 'trade-log' },
        { key: 'trade-diary',       labelKey: 'sidebar.trade_diary',       route: 'trade-diary' },
        { key: 'daily-planning',    labelKey: 'sidebar.daily_planning',    route: 'daily-planning' },
        { key: 'weekly-review',     labelKey: 'sidebar.weekly_review',     route: 'weekly-review' }
      ]
    },
    {
      key: 'decision-helper',
      labelKey: 'sidebar.decision_helper',
      icon: Crosshair,
      submenu: [
        { key: 'decision-helper-overview', labelKey: 'sidebar.decision_helper_overview', route: 'decision-helper-overview' },
        { key: 'decision-console',  labelKey: 'sidebar.decision_console',  route: 'decision-console' },
        { key: 'decision-board',    labelKey: 'sidebar.decision_board',    route: 'decision-board' },
        { key: 'backtest-studio',   labelKey: 'sidebar.backtest_studio',   route: 'backtest-studio' },
        { key: 'discipline',        labelKey: 'sidebar.discipline',        route: 'discipline' },
        { key: 'scheduled-runs',    labelKey: 'sidebar.scheduled_runs',    route: 'scheduled-runs' },
        { key: 'scanner',           labelKey: 'sidebar.scanner',           route: 'scanner' },
        { key: 'watchlist-heatmap', labelKey: 'sidebar.watchlist_heatmap', route: 'watchlist-heatmap' },
        { key: 'analytics',         labelKey: 'sidebar.analytics',         route: 'analytics' },
        { key: 'positions-open',    labelKey: 'sidebar.positions_open',    route: 'positions-open' },
        { key: 'outcomes',          labelKey: 'sidebar.outcomes',          route: 'outcomes' },
        { key: 'risk-dashboard',    labelKey: 'sidebar.risk_dashboard',    route: 'risk-dashboard' }
      ]
    },
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
                title={isCollapsed ? t(item.labelKey) : ''}
              >
                <div className="nav-button-content">
                  <item.icon className="nav-icon" />
                  {!isCollapsed && <span className="nav-button-text">{t(item.labelKey)}</span>}
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
                      {t(subitem.labelKey)}
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
                  {userEmail || t('common.guest')}
                </div>
                <div className="sidebar-user-role">{t('common.personal_account')}</div>
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
            title={isCollapsed ? t('common.expand_menu') : t('common.collapse_menu')}
          >
            {isCollapsed ? <ChevronRight /> : <ChevronLeft />}
            {!isCollapsed && <span>{t('common.collapse_menu')}</span>}
          </button>
        </div>
      </div>
    </>
  );
};

export default Sidebar;
