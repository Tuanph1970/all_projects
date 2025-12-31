// src/services/api.js
// API Service for Microservices Architecture

import { API_ENDPOINTS, API_BASE_URLS } from '../constants/api';

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
        throw new Error('Registration failed');
      }

      const data = await response.json();
      return { message: 'Registration successful' };
    } catch (error) {
      throw new Error('Registration failed');
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

      const data = await response.json();
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

      const data = await response.json();
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
      const response = await fetch(`${API_ENDPOINTS.STOCK_SEARCH}?query=${encodeURIComponent(query)}`, {
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
      // Fallback to mock data if API fails
      const mockStocks = [
        { symbol: 'AAPL', name: 'Apple Inc.', price: 175.43 },
        { symbol: 'GOOGL', name: 'Alphabet Inc.', price: 2547.12 },
        { symbol: 'MSFT', name: 'Microsoft Corporation', price: 338.54 },
        { symbol: 'TSLA', name: 'Tesla Inc.', price: 242.68 },
        { symbol: 'AMZN', name: 'Amazon.com Inc.', price: 3367.52 },
        { symbol: 'NVDA', name: 'NVIDIA Corporation', price: 465.89 },
        { symbol: 'META', name: 'Meta Platforms Inc.', price: 326.78 }
      ];

      return mockStocks.filter(stock =>
        stock.symbol.toLowerCase().includes(query.toLowerCase()) ||
        stock.name.toLowerCase().includes(query.toLowerCase())
      );
    }
  },

  getPortfolio: async () => {
    try {
      const response = await fetch(API_ENDPOINTS.PORTFOLIO_DEFAULT, {
        method: 'GET',
        headers: getAuthHeaders()
      });

      if (!response.ok) {
        throw new Error('Failed to fetch portfolio');
      }

      const data = await response.json();
      return data;
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
          company_name: companyName,
          transaction_type: 'buy',
          shares: shares,
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
      const portfolioResponse = await fetch(API_ENDPOINTS.PORTFOLIO_DEFAULT, {
        method: 'GET',
        headers: getAuthHeaders()
      });

      if (!portfolioResponse.ok) {
        throw new Error('Failed to get portfolio');
      }

      const portfolio = await portfolioResponse.json();
      const portfolioId = portfolio.id;

      const response = await fetch(API_ENDPOINTS.PORTFOLIO_HOLDINGS(portfolioId), {
        method: 'GET',
        headers: getAuthHeaders()
      });

      if (!response.ok) {
        throw new Error('Failed to fetch portfolio holdings');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error fetching portfolio holdings:', error);
      return { total_stocks: 0, total_value: 0 };
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

      const response = await fetch(API_ENDPOINTS.PORTFOLIO_SUMMARY(portfolioId), {
        method: 'GET',
        headers: getAuthHeaders()
      });

      if (!response.ok) {
        throw new Error('Failed to fetch portfolio performance');
      }

      const data = await response.json();
      return data;
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

      const response = await fetch(`${API_ENDPOINTS.PORTFOLIO_SUMMARY(portfolioId)}?timeframe=${timeframe}`, {
        method: 'GET',
        headers: getAuthHeaders()
      });

      if (!response.ok) {
        throw new Error('Failed to fetch portfolio metrics');
      }

      const data = await response.json();
      return data;
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

  getRecommendations: async () => {
    try {
      const response = await fetch(API_ENDPOINTS.AI_PORTFOLIO_INSIGHTS, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ type: 'recommendations' })
      });

      if (!response.ok) {
        throw new Error('Failed to fetch recommendations');
      }

      const data = await response.json();
      return data.recommendations || data;
    } catch (error) {
      console.error('Error fetching recommendations:', error);
      // Fallback to mock data if API fails
      return [
        {
          type: 'BUY',
          symbol: 'VIC',
          name: 'Vingroup Joint Stock Company',
          reason: 'Strong technical indicators with RSI showing oversold conditions. Vietnam market leader in real estate.',
          confidence: 87
        },
        {
          type: 'HOLD',
          symbol: 'VNM',
          name: 'Vietnam Dairy Products Joint Stock Company',
          reason: 'Mixed signals from technical analysis. Wait for clearer trend before action.',
          confidence: 64
        },
        {
          type: 'SELL',
          symbol: 'TCB',
          name: 'Techcombank',
          reason: 'Overbought conditions with high P/E ratio. Consider taking profits.',
          confidence: 72
        }
      ];
    }
  },

  getProspectiveStocks: async () => {
    try {
      const response = await fetch(API_ENDPOINTS.ANALYSIS_SCREENER, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ type: 'prospective' })
      });

      if (!response.ok) {
        throw new Error('Failed to fetch prospective stocks');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error fetching prospective stocks:', error);
      // Fallback to mock data based on fundamental analysis criteria
      return [
        {
          symbol: 'FPT',
          name: 'FPT Corporation',
          price: 125.50,
          peRatio: 18.5,
          epsGrowth2Y: 22.4,
          netProfitGrowth2Y: 25.8,
          news: 'Signed major AI partnership with NVIDIA, expanding digital transformation services globally.',
          sector: 'Technology'
        },
        {
          symbol: 'MWG',
          name: 'Mobile World Investment Corporation',
          price: 52.80,
          peRatio: 14.2,
          epsGrowth2Y: 18.6,
          netProfitGrowth2Y: 20.3,
          news: 'Strong retail expansion with new store openings and e-commerce growth accelerating.',
          sector: 'Retail'
        },
        {
          symbol: 'VHM',
          name: 'Vinhomes JSC',
          price: 42.30,
          peRatio: 8.9,
          epsGrowth2Y: 15.2,
          netProfitGrowth2Y: 17.8,
          news: 'New mega-project launch in Ho Chi Minh City with strong pre-sales performance.',
          sector: 'Real Estate'
        },
        {
          symbol: 'HPG',
          name: 'Hoa Phat Group JSC',
          price: 28.45,
          peRatio: 10.3,
          epsGrowth2Y: 28.5,
          netProfitGrowth2Y: 32.1,
          news: 'Steel demand surge from infrastructure projects, export volume increased 40% YoY.',
          sector: 'Steel'
        },
        {
          symbol: 'ACB',
          name: 'Asia Commercial Bank',
          price: 24.80,
          peRatio: 7.8,
          epsGrowth2Y: 19.7,
          netProfitGrowth2Y: 21.4,
          news: 'Digital banking transformation success, NPL ratio at historic low of 0.8%.',
          sector: 'Banking'
        }
      ];
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
 * Routes to Portfolio Service (Alerts) via /api/v2/alerts
 */
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
      return data;
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
        body: JSON.stringify(alertData)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to create alert');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      throw new Error('Failed to create alert: ' + error.message);
    }
  },

  updateAlert: async (alertId, alertData) => {
    try {
      const response = await fetch(API_ENDPOINTS.ALERT_UPDATE(alertId), {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(alertData)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to update alert');
      }

      const data = await response.json();
      return data;
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
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to delete alert');
      }

      const data = await response.json();
      return data;
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
