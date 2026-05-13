// src/services/api.js
// API Service for Microservices Architecture

import { API_ENDPOINTS } from '../constants/api';

/**
 * Helper function to get auth headers
 */
const getAuthHeaders = () => {
  const token = localStorage.getItem('token');
  return {
    'Content-Type': 'application/json',
    ...(token && { 'Authorization': `Bearer ${token}` })
  };
};

/**
 * Authentication API
 * Routes to Auth Service via /api/v2/auth
 */
export const authAPI = {
  login: async (username, password) => {
    try {
      const response = await fetch(API_ENDPOINTS.AUTH_LOGIN, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: username,
          password: password
        })
      });

      if (!response.ok) {
        throw new Error('Invalid credentials');
      }

      const data = await response.json();

      // Store token and user info in localStorage for authentication
      if (data.access_token || data.token) {
        localStorage.setItem('token', data.access_token || data.token);
        localStorage.setItem('email', username);
        localStorage.setItem('userId', data.user_id || data.userId);
        if (data.refresh_token) {
          localStorage.setItem('refreshToken', data.refresh_token);
        }
      }

      return {
        token: data.access_token || data.token,
        user: {
          id: data.user_id || data.userId,
          username: username,
          email: username
        }
      };
    } catch (error) {
      throw new Error('Invalid credentials');
    }
  },

  register: async (username, email, password) => {
    try {
      const response = await fetch(API_ENDPOINTS.AUTH_REGISTER, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: username,
          email: email,
          password: password
        })
      });

      if (!response.ok) {
        // Try to get error message from response
        try {
          const errorData = await response.json();
          throw new Error(errorData.message || errorData.detail || 'Đăng ký thất bại');
        } catch {
          throw new Error('Đăng ký thất bại');
        }
      }

      // Registration successful
      return { message: 'Đăng ký thành công! Vui lòng đăng nhập.' };
    } catch (error) {
      // Re-throw with meaningful message
      throw new Error(error.message || 'Đăng ký thất bại');
    }
  },

  resetPassword: async (email) => {
    try {
      const response = await fetch(API_ENDPOINTS.AUTH_RESET_PASSWORD, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: email
        })
      });

      if (!response.ok) {
        throw new Error('Password reset failed');
      }

      await response.json();
      return { message: 'Password reset email sent' };
    } catch (error) {
      throw new Error('Password reset failed');
    }
  },

  changePassword: async (currentPassword, newPassword) => {
    try {
      const response = await fetch(API_ENDPOINTS.AUTH_CHANGE_PASSWORD, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword
        })
      });

      if (!response.ok) {
        throw new Error('Failed to change password');
      }

      await response.json();
      return { message: 'Password changed successfully' };
    } catch (error) {
      throw new Error('Failed to change password');
    }
  },

  logout: async () => {
    try {
      // Call logout endpoint to invalidate token on server
      const token = localStorage.getItem('token');
      if (token) {
        await fetch(API_ENDPOINTS.AUTH_LOGOUT, {
          method: 'POST',
          headers: getAuthHeaders()
        }).catch(() => {}); // Ignore errors on logout
      }

      // Clear all authentication data from localStorage
      localStorage.removeItem('token');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('email');
      localStorage.removeItem('userId');

      return { message: 'Logged out successfully' };
    } catch (error) {
      throw new Error('Failed to logout');
    }
  },

  validateToken: async () => {
    try {
      const token = localStorage.getItem('token');
      const email = localStorage.getItem('email');

      if (!token || !email) {
        return { valid: false, user: null };
      }

      // Use verify endpoint to validate token
      const response = await fetch(API_ENDPOINTS.AUTH_VERIFY, {
        method: 'POST',
        headers: getAuthHeaders()
      });

      if (!response.ok) {
        // Token is invalid or expired
        localStorage.removeItem('token');
        localStorage.removeItem('refreshToken');
        localStorage.removeItem('email');
        localStorage.removeItem('userId');
        return { valid: false, user: null };
      }

      // Token is valid, return user info
      return {
        valid: true,
        user: {
          username: email,
          email: email,
          id: localStorage.getItem('userId')
        }
      };
    } catch (error) {
      // Network error or server unavailable
      localStorage.removeItem('token');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('email');
      localStorage.removeItem('userId');
      return { valid: false, user: null };
    }
  },

  refreshToken: async () => {
    try {
      const refreshToken = localStorage.getItem('refreshToken');
      if (!refreshToken) {
        throw new Error('No refresh token available');
      }

      const response = await fetch(API_ENDPOINTS.AUTH_REFRESH, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          refresh_token: refreshToken
        })
      });

      if (!response.ok) {
        throw new Error('Token refresh failed');
      }

      const data = await response.json();
      if (data.access_token) {
        localStorage.setItem('token', data.access_token);
      }

      return data;
    } catch (error) {
      throw new Error('Token refresh failed');
    }
  }
};

/**
 * Stock API
 * Routes to Stock Data Service (/api/v2/stocks) and Portfolio Service (/api/v2/portfolio)
 */
export const stockAPI = {
  searchStock: async (query) => {
    try {
      // Backend expects parameter 'q' not 'query'
      const response = await fetch(`${API_ENDPOINTS.STOCK_SEARCH}?q=${encodeURIComponent(query)}`, {
        method: 'GET',
        headers: getAuthHeaders()
      });

      if (!response.ok) {
        throw new Error('Failed to search stocks');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error searching stocks:', error);
      // No fake fallback — return empty so the UI shows "no results" rather
      // than tricking users with a hardcoded VN30 sample. Backlog #9.
      return [];
    }
  },

  getPortfolio: async () => {
    try {
      // First get the default portfolio
      const portfolioResponse = await fetch(API_ENDPOINTS.PORTFOLIO_DEFAULT, {
        method: 'GET',
        headers: getAuthHeaders()
      });

      if (!portfolioResponse.ok) {
        throw new Error('Failed to fetch portfolio');
      }

      const portfolio = await portfolioResponse.json();
      const portfolioId = portfolio.id;

      // Then fetch the holdings for that portfolio
      const holdingsResponse = await fetch(API_ENDPOINTS.PORTFOLIO_HOLDINGS(portfolioId), {
        method: 'GET',
        headers: getAuthHeaders()
      });

      if (!holdingsResponse.ok) {
        throw new Error('Failed to fetch portfolio holdings');
      }

      const holdings = await holdingsResponse.json();
      // Transform holdings to match Dashboard expected format
      return (holdings || []).map(h => ({
        symbol: h.symbol,
        name: h.company_name || h.symbol,
        shares: h.quantity || 0,
        avgPrice: h.average_price || 0,
        currentPrice: h.current_price || h.average_price || 0,
        change: h.gain_loss_percent ? `${h.gain_loss_percent >= 0 ? '+' : ''}${h.gain_loss_percent.toFixed(2)}%` : '0.00%'
      }));
    } catch (error) {
      console.error('Error fetching portfolio:', error);
      return [];
    }
  },

  buyStock: async (symbol, companyName, shares, price) => {
    try {
      // First get or create default portfolio
      const portfolioResponse = await fetch(API_ENDPOINTS.PORTFOLIO_DEFAULT, {
        method: 'GET',
        headers: getAuthHeaders()
      });

      if (!portfolioResponse.ok) {
        throw new Error('Failed to get portfolio');
      }

      const portfolio = await portfolioResponse.json();
      const portfolioId = portfolio.id;

      // Add transaction
      const response = await fetch(API_ENDPOINTS.PORTFOLIO_TRANSACTIONS(portfolioId), {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          symbol: symbol,
          type: 'buy',
          quantity: shares,
          price: price
        })
      });

      if (!response.ok) {
        throw new Error('Failed to buy stock');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      throw new Error('Failed to buy stock: ' + error.message);
    }
  },

  sellStock: async (symbol, shares) => {
    try {
      // First get default portfolio
      const portfolioResponse = await fetch(API_ENDPOINTS.PORTFOLIO_DEFAULT, {
        method: 'GET',
        headers: getAuthHeaders()
      });

      if (!portfolioResponse.ok) {
        throw new Error('Failed to get portfolio');
      }

      const portfolio = await portfolioResponse.json();
      const portfolioId = portfolio.id;

      // Add sell transaction
      const response = await fetch(API_ENDPOINTS.PORTFOLIO_TRANSACTIONS(portfolioId), {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          symbol: symbol,
          transaction_type: 'sell',
          shares: shares
        })
      });

      if (!response.ok) {
        throw new Error('Failed to sell stock');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      throw new Error('Failed to sell stock: ' + error.message);
    }
  },

  addStock: async (symbol, companyName, shares, price) => {
    try {
      // First get or create default portfolio
      const portfolioResponse = await fetch(API_ENDPOINTS.PORTFOLIO_DEFAULT, {
        method: 'GET',
        headers: getAuthHeaders()
      });

      if (!portfolioResponse.ok) {
        throw new Error('Failed to get portfolio');
      }

      const portfolio = await portfolioResponse.json();
      const portfolioId = portfolio.id;

      // Add holding
      const response = await fetch(API_ENDPOINTS.PORTFOLIO_HOLDINGS(portfolioId), {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          symbol: symbol,
          company_name: companyName,
          shares: shares,
          average_price: price
        })
      });

      if (!response.ok) {
        throw new Error('Failed to add stock');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      throw new Error('Failed to add stock: ' + error.message);
    }
  },

  removeStock: async (symbol) => {
    try {
      // First get default portfolio
      const portfolioResponse = await fetch(API_ENDPOINTS.PORTFOLIO_DEFAULT, {
        method: 'GET',
        headers: getAuthHeaders()
      });

      if (!portfolioResponse.ok) {
        throw new Error('Failed to get portfolio');
      }

      const portfolio = await portfolioResponse.json();
      const portfolioId = portfolio.id;

      // Remove holding
      const response = await fetch(API_ENDPOINTS.PORTFOLIO_HOLDING(portfolioId, symbol), {
        method: 'DELETE',
        headers: getAuthHeaders()
      });

      if (!response.ok) {
        throw new Error('Failed to remove stock');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      throw new Error('Failed to remove stock: ' + error.message);
    }
  },

  getPortfolioSummary: async () => {
    try {
      const portfolioResponse = await fetch(API_ENDPOINTS.PORTFOLIO_DEFAULT, {
        method: 'GET',
        headers: getAuthHeaders()
      });

      if (!portfolioResponse.ok) {
        throw new Error('Failed to get portfolio');
      }

      const portfolio = await portfolioResponse.json();
      const portfolioId = portfolio.id;

      const response = await fetch(API_ENDPOINTS.PORTFOLIO_SUMMARY(portfolioId), {
        method: 'GET',
        headers: getAuthHeaders()
      });

      if (!response.ok) {
        throw new Error('Failed to fetch portfolio summary');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error fetching portfolio summary:', error);
      return { total_stocks: 0, total_value: 0 };
    }
  },

  getPortfolioStockOption: async () => {
    try {
      // Fetch available stocks from priceboards API (VN30 stocks with real-time prices)
      const response = await fetch(`${API_ENDPOINTS.PRICEBOARDS}?group=VN30`, {
        method: 'GET',
        headers: getAuthHeaders()
      });

      if (!response.ok) {
        throw new Error('Failed to fetch stock options');
      }

      const data = await response.json();

      // Transform priceboard data to stock options format
      if (Array.isArray(data)) {
        return data.map(stock => ({
          symbol: stock.symbol,
          name: stock.name || stock.symbol,
          price: stock.matchPrice || stock.close || 0,
          change: stock.change || 0,
          changePercent: stock.changePercent || 0
        })).filter(stock => stock.symbol && stock.price > 0);
      }

      return [];
    } catch (error) {
      console.error('Error fetching stock options:', error);
      return [];
    }
  },

  getPortfolioPerformance: async () => {
    try {
      const portfolioResponse = await fetch(API_ENDPOINTS.PORTFOLIO_DEFAULT, {
        method: 'GET',
        headers: getAuthHeaders()
      });

      if (!portfolioResponse.ok) {
        throw new Error('Failed to get portfolio');
      }

      const portfolio = await portfolioResponse.json();
      const portfolioId = portfolio.id;

      // Fetch holdings list instead of summary
      const response = await fetch(API_ENDPOINTS.PORTFOLIO_HOLDINGS(portfolioId), {
        method: 'GET',
        headers: getAuthHeaders()
      });

      if (!response.ok) {
        throw new Error('Failed to fetch portfolio holdings');
      }

      const holdings = await response.json();
      // Transform holdings to expected format
      return Array.isArray(holdings) ? holdings.map(h => ({
        symbol: h.symbol,
        company_name: h.company_name || h.symbol,
        shares: h.quantity,
        average_price: h.average_price,
        current_price: h.current_price,
        current_value: h.current_value || (h.quantity * (h.current_price || h.average_price || 0)),
        gain_loss: h.profit_loss || 0,
        gain_loss_percent: h.profit_loss_percent || 0
      })) : [];
    } catch (error) {
      console.error('Error fetching portfolio performance:', error);
      return [];
    }
  },

  getPortfolioMetrics: async (timeframe = '1M') => {
    try {
      const portfolioResponse = await fetch(API_ENDPOINTS.PORTFOLIO_DEFAULT, {
        method: 'GET',
        headers: getAuthHeaders()
      });

      if (!portfolioResponse.ok) {
        throw new Error('Failed to get portfolio');
      }

      const portfolio = await portfolioResponse.json();
      const portfolioId = portfolio.id;

      // Fetch both summary and holdings for complete metrics
      const [summaryResponse, holdingsResponse] = await Promise.all([
        fetch(`${API_ENDPOINTS.PORTFOLIO_SUMMARY(portfolioId)}?timeframe=${timeframe}`, {
          method: 'GET',
          headers: getAuthHeaders()
        }),
        fetch(API_ENDPOINTS.PORTFOLIO_HOLDINGS(portfolioId), {
          method: 'GET',
          headers: getAuthHeaders()
        })
      ]);

      if (!summaryResponse.ok) {
        throw new Error('Failed to fetch portfolio metrics');
      }

      const summary = await summaryResponse.json();
      const holdings = holdingsResponse.ok ? await holdingsResponse.json() : [];

      // Calculate portfolio distribution
      const totalValue = summary.current_value || 0;
      const distribution = Array.isArray(holdings) ? holdings.map(h => ({
        symbol: h.symbol,
        value: h.current_value || 0,
        allocation: totalValue > 0 ? ((h.current_value || 0) / totalValue) * 100 : 0
      })) : [];

      // Transform top/worst performers
      const topPerformer = summary.top_performers && summary.top_performers.length > 0
        ? {
            symbol: summary.top_performers[0].symbol,
            company_name: summary.top_performers[0].company_name || summary.top_performers[0].symbol,
            value: summary.top_performers[0].current_value || 0,
            gain_loss_percent: summary.top_performers[0].profit_loss_percent || 0
          }
        : null;

      const worstPerformer = summary.worst_performers && summary.worst_performers.length > 0
        ? {
            symbol: summary.worst_performers[0].symbol,
            company_name: summary.worst_performers[0].company_name || summary.worst_performers[0].symbol,
            value: summary.worst_performers[0].current_value || 0,
            gain_loss_percent: summary.worst_performers[0].profit_loss_percent || 0
          }
        : null;

      return {
        total_value: summary.current_value || 0,
        total_cost: summary.total_invested || 0,
        total_gain_loss: summary.total_profit_loss || 0,
        total_gain_loss_percent: summary.total_profit_loss_percent || 0,
        total_stocks: summary.total_holdings || 0,
        top_performer: topPerformer,
        worst_performer: worstPerformer,
        portfolio_distribution: distribution
      };
    } catch (error) {
      console.error('Error fetching portfolio metrics:', error);
      return {
        total_value: 0,
        total_cost: 0,
        total_gain_loss: 0,
        total_gain_loss_percent: 0,
        total_stocks: 0,
        top_performer: null,
        worst_performer: null,
        portfolio_distribution: []
      };
    }
  },

  refreshPriceBoard: async (group = 'VN30') => {
    try {
      const response = await fetch(`${API_ENDPOINTS.PRICEBOARDS}/refresh?group=${encodeURIComponent(group)}`, {
        method: 'POST',
        headers: getAuthHeaders()
      });
      if (!response.ok) {
        throw new Error('Failed to refresh price board');
      }
      return await response.json();
    } catch (error) {
      console.error('Error refreshing price board:', error);
      throw error;
    }
  },

  getRecommendations: async () => {
    try {
      // Call the new real recommendations endpoint
      const response = await fetch(API_ENDPOINTS.AI_RECOMMENDATIONS, {
        method: 'GET',
        headers: getAuthHeaders()
      });

      if (!response.ok) {
        throw new Error('Failed to fetch recommendations');
      }

      const data = await response.json();
      return data.recommendations || data;
    } catch (error) {
      console.error('Error fetching recommendations:', error);
      // No mock fallback — empty list lets the dashboard render its own
      // empty-state UI rather than a fake "Loading..." pseudo-recommendation
      // that lingers after the network actually fails. Backlog #10.
      return [];
    }
  },

  getProspectiveStocks: async () => {
    try {
      // Screener requires filters array - use filters for prospective stocks criteria
      const response = await fetch(API_ENDPOINTS.ANALYSIS_SCREENER, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          filters: [
            { field: 'pe_ratio', operator: 'lt', value: 20 },
            { field: 'change_percent', operator: 'gt', value: 0 }
          ],
          sort_by: 'change_percent',
          sort_order: 'desc',
          limit: 10
        })
      });

      if (!response.ok) {
        throw new Error('Failed to fetch prospective stocks');
      }

      const data = await response.json();
      // Transform screener response to expected format
      if (data && data.stocks && Array.isArray(data.stocks)) {
        return data.stocks.map(s => ({
          symbol: s.symbol,
          name: s.name || s.symbol,
          price: s.price || 0,
          peRatio: s.pe_ratio || 0,
          epsGrowth2Y: 0,
          netProfitGrowth2Y: 0,
          news: 'Based on technical screening criteria',
          sector: s.sector || 'Unknown'
        }));
      }
      return [];
    } catch (error) {
      console.error('Error fetching prospective stocks:', error);
      // Empty list rather than five fake hand-curated picks. The dashboard
      // empty-state already handles this case. Backlog #10.
      return [];
    }
  }
};

/**
 * Analysis API
 * Routes to Analysis Service via /api/v2/analysis
 */
export const analysisAPI = {
  getFundamentalAnalysis: async (symbol) => {
    try {
      const response = await fetch(API_ENDPOINTS.ANALYSIS_FUNDAMENTAL(symbol), {
        method: 'GET',
        headers: getAuthHeaders()
      });

      if (!response.ok) {
        throw new Error('Failed to fetch fundamental analysis');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error fetching fundamental analysis:', error);
      throw error;
    }
  },

  getFinancialStatements: async (symbol, period = 'year') => {
    try {
      const response = await fetch(`${API_ENDPOINTS.ANALYSIS_FUNDAMENTAL_STATEMENTS(symbol)}?period=${period}`, {
        method: 'GET',
        headers: getAuthHeaders()
      });

      if (!response.ok) {
        throw new Error('Failed to fetch financial statements');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error fetching financial statements:', error);
      throw error;
    }
  },

  compareFundamentalRatios: async (symbols) => {
    try {
      const symbolsParam = symbols.join(',');
      const response = await fetch(`${API_ENDPOINTS.ANALYSIS_COMPARE}?symbols=${symbolsParam}`, {
        method: 'GET',
        headers: getAuthHeaders()
      });

      if (!response.ok) {
        throw new Error('Failed to compare fundamental ratios');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error comparing fundamental ratios:', error);
      throw error;
    }
  },

  getTechnicalAnalysis: async (symbol, period = 100) => {
    console.log('=== API CALL DEBUG ===');
    console.log('getTechnicalAnalysis called with:', { symbol, period });

    const url = `${API_ENDPOINTS.ANALYSIS_TECHNICAL(symbol)}?period=${period}`;
    const token = localStorage.getItem('token');

    console.log('API URL:', url);
    console.log('Token:', token ? 'Token exists' : 'No token found');

    try {
      console.log('Making fetch request...');
      const response = await fetch(url, {
        method: 'GET',
        headers: getAuthHeaders()
      });

      console.log('Response received:', response.status, response.statusText);

      if (!response.ok) {
        console.log('Response not OK, throwing error');
        throw new Error('Failed to fetch technical analysis');
      }

      console.log('Parsing JSON response...');
      const data = await response.json();
      console.log('API response data:', data);
      console.log('=== END API CALL DEBUG ===');
      return data;
    } catch (error) {
      console.error('=== API CALL ERROR ===');
      console.error('Error fetching technical analysis:', error);
      console.error('=== END API CALL ERROR ===');
      throw error;
    }
  },

  getTechnicalIndicators: async (symbol, indicators = 'rsi,macd,sma', period = 30) => {
    try {
      const response = await fetch(`${API_ENDPOINTS.ANALYSIS_TECHNICAL_INDICATORS(symbol)}?indicators=${indicators}&period=${period}`, {
        method: 'GET',
        headers: getAuthHeaders()
      });

      if (!response.ok) {
        throw new Error('Failed to fetch technical indicators');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error fetching technical indicators:', error);
      throw error;
    }
  },

  getIntradayAnalysis: async (symbol) => {
    try {
      const response = await fetch(API_ENDPOINTS.ANALYSIS_TECHNICAL_INTRADAY(symbol), {
        method: 'GET',
        headers: getAuthHeaders()
      });

      if (!response.ok) {
        throw new Error('Failed to fetch intraday analysis');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error fetching intraday analysis:', error);
      throw error;
    }
  }
};

/**
 * Alerts API
 * Routes to Portfolio Service (Alerts) via /api/v2/portfolio/alerts
 */

// Helper to transform alert from backend (snake_case) to frontend (camelCase)
const transformAlertResponse = (alert) => ({
  id: alert.id,
  userId: alert.user_id,
  symbol: alert.symbol,
  companyName: alert.company_name || alert.symbol,
  alertType: alert.alert_type === 'above' ? 'price_above' : alert.alert_type === 'below' ? 'price_below' : alert.alert_type,
  targetPrice: alert.target_price,
  targetPercent: alert.target_percent,
  currentPrice: alert.current_price || 0,
  isActive: alert.is_active,
  triggered: alert.is_triggered,
  triggeredAt: alert.triggered_at,
  notes: alert.notes,
  createdAt: alert.created_at ? new Date(alert.created_at).toLocaleDateString('vi-VN') : null,
  updatedAt: alert.updated_at
});

// Helper to transform alert CREATE request from frontend (camelCase) to backend (snake_case)
const transformAlertCreateRequest = (alertData) => ({
  symbol: alertData.symbol,
  alert_type: alertData.alertType === 'price_above' ? 'above' : alertData.alertType === 'price_below' ? 'below' : alertData.alertType,
  target_price: parseFloat(alertData.targetPrice) || null,
  is_active: alertData.isActive !== false,
  notes: alertData.notes || null
});

// Helper to transform alert UPDATE request (only allowed fields)
const transformAlertUpdateRequest = (alertData) => ({
  target_price: parseFloat(alertData.targetPrice) || null,
  is_active: alertData.isActive !== false,
  notes: alertData.notes || null
});

export const alertsAPI = {
  getAlerts: async () => {
    try {
      const response = await fetch(API_ENDPOINTS.ALERTS_LIST, {
        method: 'GET',
        headers: getAuthHeaders()
      });

      if (!response.ok) {
        throw new Error('Failed to fetch alerts');
      }

      const data = await response.json();
      // Transform each alert from snake_case to camelCase
      return Array.isArray(data) ? data.map(transformAlertResponse) : [];
    } catch (error) {
      console.error('Error fetching alerts:', error);
      return [];
    }
  },

  createAlert: async (alertData) => {
    try {
      const response = await fetch(API_ENDPOINTS.ALERT_CREATE, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(transformAlertCreateRequest(alertData))
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || errorData.error || 'Failed to create alert');
      }

      const data = await response.json();
      return transformAlertResponse(data);
    } catch (error) {
      throw new Error('Failed to create alert: ' + error.message);
    }
  },

  updateAlert: async (alertId, alertData) => {
    try {
      const response = await fetch(API_ENDPOINTS.ALERT_UPDATE(alertId), {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(transformAlertUpdateRequest(alertData))
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || errorData.error || 'Failed to update alert');
      }

      const data = await response.json();
      return transformAlertResponse(data);
    } catch (error) {
      throw new Error('Failed to update alert: ' + error.message);
    }
  },

  deleteAlert: async (alertId) => {
    try {
      const response = await fetch(API_ENDPOINTS.ALERT_DELETE(alertId), {
        method: 'DELETE',
        headers: getAuthHeaders()
      });

      if (!response.ok) {
        const errorText = await response.text();
        const errorData = errorText ? JSON.parse(errorText) : {};
        throw new Error(errorData.detail || errorData.error || 'Failed to delete alert');
      }

      // DELETE returns 204 No Content - no body to parse
      return { success: true };
    } catch (error) {
      throw new Error('Failed to delete alert: ' + error.message);
    }
  },

  toggleAlert: async (alertId) => {
    try {
      const response = await fetch(API_ENDPOINTS.ALERT_TOGGLE(alertId), {
        method: 'POST',
        headers: getAuthHeaders()
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to toggle alert');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      throw new Error('Failed to toggle alert: ' + error.message);
    }
  }
};
