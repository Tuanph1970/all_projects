// src/components/Layout/MainLayout.js
import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from '../../context/RouterContext';
import Sidebar from './Sidebar';
import Header from './Header';
import Dashboard from '../Dashboard/Dashboard';
import PriceBoardWrapper from '../Pages/PriceBoardWrapper';
import { TechnicalAnalysis } from '../Pages/TechnicalAnalysis';
import { FundamentalAnalysis } from '../Pages/FundamentalAnalysis';
import { StocksByIndustry } from '../Pages/Stocks';
import { AIInsights } from '../Pages/AIInsights';
import { Company } from '../Pages/company';

import { StockScreener } from '../Pages/Stocks';
import { StockList } from '../Pages/Stocks';
import Gainers from '../Pages/MarketMovers/Gainer';
import Losers from '../Pages/MarketMovers/Losers';
import Actives from '../Pages/MarketMovers/Actives';
import { TimeSeries,Models,Solutions } from '../Pages/Predict';
import SolutionAddNew from '../Pages/Solutions/SolutionAddNew';
import SolutionEdit from '../Pages/Solutions/SolutionEdit';
import { Agent } from '../Pages/Agent';
import ChatbotAgent from '../Pages/ChatbotAgent';
import Holdings from '../Pages/Portfolio/Holdings';
import Performance from '../Pages/Portfolio/Performance';
import Alerts from '../Pages/Portfolio/Alerts';
import IndicatorsList from '../Pages/Indicators/IndicatorsList';
import SimulationDashboard from '../Pages/SimulationDashboard';
import JournalAccounts from '../Pages/Journal/JournalAccounts';
import TradeLog from '../Pages/Journal/TradeLog';
import TradeDiary from '../Pages/Journal/TradeDiary';
import JournalDashboard from '../Pages/Journal/JournalDashboard';
import DailyPlanning from '../Pages/Journal/DailyPlanning';
import WeeklyReview from '../Pages/Journal/WeeklyReview';

const MainLayout = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  // Start collapsed by default to maximize chart/content area
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true);
  const { currentRoute } = useRouter();

  // Toggle sidebar collapse state
  const handleToggleCollapse = useCallback(() => {
    setSidebarCollapsed(prev => !prev);
  }, []);

  useEffect(() => {
    const handleToggleSidebar = () => setSidebarOpen(!sidebarOpen);
    document.addEventListener('toggleSidebar', handleToggleSidebar);
    return () => document.removeEventListener('toggleSidebar', handleToggleSidebar);
  }, [sidebarOpen]);

  const renderCurrentPage = () => {
    // Handle company routes with symbol parameter
    if (currentRoute.startsWith('company/')) {
      const symbol = currentRoute.split('/')[1];
      return <Company symbol={symbol} />;
    }

    // Handle solutions routes
    if (currentRoute.startsWith('solutions/')) {
      const path = currentRoute.split('/')[1];
      if (path === 'add') {
        return <SolutionAddNew />;
      } else if (!isNaN(path)) {
        // If path is a number, it's an ID for editing
        return <SolutionEdit />;
      }
    }

    switch (currentRoute) {
      case 'dashboard':
        return <Dashboard />;
      case 'priceboard':
        return <PriceBoardWrapper/>      
      case 'stockscreener':
        return <StockScreener/>
      case 'byindustry':
        return <StocksByIndustry/>
      case 'stocklist':
        return <StockList/>
      case 'topgainer':
        return <Gainers/>
      case 'toploser':
        return <Losers/>
      case 'topactive':
        return <Actives/>
      case "timeseries":
        return <TimeSeries/>
      case "indicators":
        return <IndicatorsList/>
      case "models":
        return <Models/>;
      case "solutions":
        return <Solutions/>;
      case "agents":
        return <Agent/>
      case "simulation":
        return <SimulationDashboard/>
      case "chatbot":
        return <ChatbotAgent/>
      case 'technical':
        return <TechnicalAnalysis />;
      case 'fundamental':
        return <FundamentalAnalysis />;
      case 'ai-insights':
        return <AIInsights />;
      case 'holdings':
        return <Holdings />;
      case 'performance':
        return <Performance />;
      case 'alerts':
        return <Alerts />;
      // Journal routes
      case 'journal-dashboard':
        return <JournalDashboard />;
      case 'trade-log':
        return <TradeLog />;
      case 'trade-diary':
        return <TradeDiary />;
      case 'daily-planning':
        return <DailyPlanning />;
      case 'weekly-review':
        return <WeeklyReview />;
      case 'screener':
        return <Dashboard />; // Could be separate component
      case 'calculator':
        return <Dashboard />; // Could be separate component
      case 'watchlist':
        return <Dashboard />; // Could be separate component
      default:
        return <Dashboard />;
    }
  };

  return (
    <div className={`main-layout ${sidebarCollapsed ? 'sidebar-collapsed' : 'sidebar-expanded'}`}>
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={handleToggleCollapse}
      />

      <div className="main-content">
        <Header onToggleSidebar={handleToggleCollapse} isSidebarCollapsed={sidebarCollapsed} />

        <main className="page-content">
          {renderCurrentPage()}
        </main>
      </div>
    </div>
  );
};

export default MainLayout;