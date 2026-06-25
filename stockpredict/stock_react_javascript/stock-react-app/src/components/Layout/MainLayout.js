// src/components/Layout/MainLayout.js
//
// Native react-router-dom routing — replaced the prior RouterContext-based
// switch statement (Backlog #29). Each existing route string now maps to a
// URL path of the same name; dynamic routes (company, solutions edit) use
// useParams via tiny wrapper components so the existing page components
// keep their original prop signatures.
import React, { useState, useEffect, useCallback } from 'react';
import { Route, Routes, useParams } from 'react-router-dom';

import Sidebar from './Sidebar';
import Header from './Header';
import Dashboard from '../Dashboard/Dashboard';
import PriceBoard from '../Pages/PriceBoard';
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
import { Models, Solutions } from '../Pages/Predict';
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
import JournalOverview from '../Pages/Journal/JournalOverview';
import DailyPlanning from '../Pages/Journal/DailyPlanning';
import WeeklyReview from '../Pages/Journal/WeeklyReview';
import KnowledgeQAChat from '../Pages/KnowledgeQAChat';
import Watchlist from '../Pages/Watchlist';
import PositionCalculator from '../Pages/PositionCalculator';
import Backtest from '../Pages/Backtest';
import DecisionConsole from '../Pages/DecisionConsole';
import WatchlistDecisionBoard from '../Pages/WatchlistDecisionBoard';
import BacktestStudio from '../Pages/BacktestStudio';
import DisciplineDashboard from '../Pages/DisciplineDashboard';
import ScheduledRunsLog from '../Pages/ScheduledRunsLog';
import ScannerPage from '../Pages/ScannerPage';
import AnalyticsPage from '../Pages/AnalyticsPage';
import PositionsPage from '../Pages/PositionsPage';
import OutcomesPage from '../Pages/OutcomesPage';
import RiskDashboard from '../Pages/RiskDashboard';
import WatchlistHeatMap from '../Pages/WatchlistHeatMap';
import DecisionHelperOverview from '../Pages/DecisionHelperOverview';
import ChartDecompPage from '../Pages/ChartDecomp';
import VolForecastPage from '../Pages/ChartDecomp/VolForecastPage';
import AlertCenter from '../common/AlertToast';
import { useAlertStream } from '../../hooks/useAlertStream';

// Thin wrapper: <Company> takes `symbol` as a prop, so we extract it from
// the URL via useParams rather than touching the existing component.
const CompanyRoute = () => {
  const { symbol } = useParams();
  return <Company symbol={symbol} />;
};

const MainLayout = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  // Start collapsed by default to maximize chart/content area
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true);
  const { alerts, connected, unread, markAllRead, clearAlerts } = useAlertStream();

  const handleToggleCollapse = useCallback(() => {
    setSidebarCollapsed((prev) => !prev);
  }, []);

  useEffect(() => {
    const handleToggleSidebar = () => setSidebarOpen((s) => !s);
    document.addEventListener('toggleSidebar', handleToggleSidebar);
    return () => document.removeEventListener('toggleSidebar', handleToggleSidebar);
  }, []);

  return (
    <div className={`main-layout ${sidebarCollapsed ? 'sidebar-collapsed' : 'sidebar-expanded'}`}>
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={handleToggleCollapse}
      />

      <div className="main-content">
        <Header
          onToggleSidebar={handleToggleCollapse}
          isSidebarCollapsed={sidebarCollapsed}
          alertSlot={
            <AlertCenter
              alerts={alerts}
              connected={connected}
              unread={unread}
              onMarkAllRead={markAllRead}
              onClear={clearAlerts}
            />
          }
        />

        <main className="page-content">
          <Routes>
            {/* Dashboard is both / and /dashboard so the legacy default-route
                behavior (any unknown path → Dashboard) keeps working. */}
            <Route path="/" element={<Dashboard />} />
            <Route path="/dashboard" element={<Dashboard />} />

            <Route path="/priceboard" element={<PriceBoard />} />

            {/* Stocks */}
            <Route path="/stockscreener" element={<StockScreener />} />
            <Route path="/byindustry" element={<StocksByIndustry />} />
            <Route path="/stocklist" element={<StockList />} />

            {/* Market movers */}
            <Route path="/topgainer" element={<Gainers />} />
            <Route path="/toploser" element={<Losers />} />
            <Route path="/topactive" element={<Actives />} />

            {/* Prediction */}
            <Route path="/indicators" element={<IndicatorsList />} />
            <Route path="/models" element={<Models />} />
            <Route path="/solutions" element={<Solutions />} />
            <Route path="/solutions/add" element={<SolutionAddNew />} />
            {/* Numeric solution id — must come AFTER /solutions/add so it
                doesn't shadow the static path. SolutionEdit reads :id from
                useLocation().pathname. */}
            <Route path="/solutions/:id" element={<div className="chart-dense"><SolutionEdit /></div>} />
            <Route path="/backtest" element={<div className="chart-dense chart-tall"><Backtest /></div>} />

            <Route path="/agents" element={<div className="chart-dense"><Agent /></div>} />
            <Route path="/simulation" element={<div className="chart-dense chart-tall"><SimulationDashboard /></div>} />
            <Route path="/chatbot" element={<ChatbotAgent />} />
            <Route path="/knowledge-qa" element={<KnowledgeQAChat />} />

            {/* Analysis */}
            <Route path="/technical" element={<div className="chart-dense chart-tall"><TechnicalAnalysis /></div>} />
            <Route path="/fundamental" element={<FundamentalAnalysis />} />
            <Route path="/ai-insights" element={<div className="chart-dense"><AIInsights /></div>} />

            {/* Portfolio */}
            <Route path="/holdings" element={<Holdings />} />
            <Route path="/performance" element={<div className="chart-dense"><Performance /></div>} />
            <Route path="/alerts" element={<Alerts />} />

            {/* Journal */}
            <Route path="/journal-overview" element={<JournalOverview />} />
            <Route path="/journal-accounts" element={<JournalAccounts />} />
            <Route path="/journal-dashboard" element={<div className="chart-dense"><JournalDashboard /></div>} />
            <Route path="/trade-log" element={<TradeLog />} />
            <Route path="/trade-diary" element={<div className="chart-dense"><TradeDiary /></div>} />
            <Route path="/daily-planning" element={<DailyPlanning />} />
            <Route path="/weekly-review" element={<WeeklyReview />} />

            {/* Decision Helper — Phase D / F */}
            <Route path="/decision-helper-overview" element={<DecisionHelperOverview />} />
            <Route path="/decision-console" element={<DecisionConsole />} />
            <Route path="/decision-board" element={<WatchlistDecisionBoard />} />
            <Route path="/backtest-studio" element={<div className="chart-dense chart-tall"><BacktestStudio /></div>} />
            <Route path="/discipline" element={<DisciplineDashboard />} />
            <Route path="/scheduled-runs" element={<ScheduledRunsLog />} />
            <Route path="/scanner" element={<ScannerPage />} />
            <Route path="/analytics" element={<div className="chart-dense"><AnalyticsPage /></div>} />
            <Route path="/positions-open" element={<PositionsPage />} />
            <Route path="/outcomes" element={<OutcomesPage />} />
            <Route path="/risk-dashboard" element={<RiskDashboard />} />
            <Route path="/watchlist-heatmap" element={<WatchlistHeatMap />} />
            <Route path="/chart-decomp" element={<div className="chart-dense chart-tall"><ChartDecompPage /></div>} />
            <Route path="/vol-forecast" element={<div className="chart-dense chart-tall"><VolForecastPage /></div>} />

            {/* Tools */}
            <Route path="/screener" element={<StockScreener />} />
            <Route path="/calculator" element={<PositionCalculator />} />
            <Route path="/watchlist" element={<Watchlist />} />

            {/* Company detail with symbol param */}
            <Route path="/company/:symbol" element={<div className="chart-dense chart-tall"><CompanyRoute /></div>} />

            {/* Fallback — preserves the prior switch's default-to-Dashboard. */}
            <Route path="*" element={<Dashboard />} />
          </Routes>
        </main>
      </div>
    </div>
  );
};

export default MainLayout;
