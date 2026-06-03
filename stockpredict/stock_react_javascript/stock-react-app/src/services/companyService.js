// Company Service - API calls for company information
// Routes to Stock Data Service via /api/v2/companies
import axios from 'axios';
import { API_ENDPOINTS } from '../constants/api';

class CompanyService {
  // Get company profile data
  async getCompanyProfile(symbol) {
    try {
      const { data } = await axios.get(API_ENDPOINTS.COMPANY_PROFILE(symbol));
      return { success: true, data: this.formatProfileData(data) };
    } catch (error) {
      console.error('Failed to fetch company profile:', error);
      return {
        success: false,
        error: error.response?.data?.message || error.message || 'Failed to fetch company profile'
      };
    }
  }

  // Format profile data to ensure consistency
  // Backend returns camelCase keys: companyProfile, history, industry, industryL2, industryL3
  formatProfileData(data) {
    if (!Array.isArray(data) || data.length === 0) {
      return null;
    }

    const profile = data[0];
    return {
      ticker: profile.ticker || '',
      companyProfile: profile.companyProfile || '',
      history: profile.history || '',
      industry: profile.industry || '',
      industryL2: profile.industryL2 || '',
      industryL3: profile.industryL3 || '',
      charterCapital: profile.charterCapital,
      issueShare: profile.issueShare,
    };
  }

  // Get company financial data
  async getCompanyFinancials(symbol) {
    try {
      const { data } = await axios.get(API_ENDPOINTS.COMPANY_FINANCIALS(symbol));
      return { success: true, data };
    } catch (error) {
      console.error('Failed to fetch company financials:', error);
      return {
        success: false,
        error: error.response?.data?.message || error.message || 'Failed to fetch financials'
      };
    }
  }

  // Translate a UI timeframe (e.g. '2Y', '5Y') into a calendar-day lookback.
  // The stock-data-service /stocks/{symbol}/history endpoint honours
  // start_date/end_date but ignores ?timeframe=, so a fixed timeframe always
  // returned ~1 trading year (~264 points). We compute the date window here.
  static timeframeToDays(timeframe = '1Y') {
    const tf = String(timeframe).trim().toUpperCase();
    const map = { '1Y': 365, '2Y': 730, '3Y': 1095, '5Y': 1825 };
    if (map[tf]) return map[tf];
    const m = tf.match(/^(\d+)\s*Y$/);   // tolerate other "<n>Y" values
    if (m) return parseInt(m[1], 10) * 365;
    return 365;
  }

  // Get company charts data (stock history)
  async getCompanyCharts(symbol, timeframe = '1Y') {
    try {
      const end = new Date();
      const start = new Date();
      start.setDate(start.getDate() - CompanyService.timeframeToDays(timeframe));
      const fmt = (d) => d.toISOString().slice(0, 10); // YYYY-MM-DD
      const url = `${API_ENDPOINTS.COMPANY_CHARTS(symbol)}`
        + `?start_date=${fmt(start)}&end_date=${fmt(end)}`;
      const { data } = await axios.get(url);
      return { success: true, data };
    } catch (error) {
      console.error('Failed to fetch company charts:', error);
      return {
        success: false,
        error: error.response?.data?.message || error.message || 'Failed to fetch charts'
      };
    }
  }

  // Get company dividends
  async getCompanyDividends(symbol) {
    try {
      const { data } = await axios.get(API_ENDPOINTS.COMPANY_DIVIDENDS(symbol));
      return { success: true, data };
    } catch (error) {
      console.error('Failed to fetch company dividends:', error);
      return {
        success: false,
        error: error.response?.data?.message || error.message || 'Failed to fetch dividends'
      };
    }
  }

  // Get company events
  async getCompanyEvents(symbol) {
    try {
      const { data } = await axios.get(API_ENDPOINTS.COMPANY_EVENTS(symbol));
      return { success: true, data };
    } catch (error) {
      console.error('Failed to fetch company events:', error);
      return {
        success: false,
        error: error.response?.data?.message || error.message || 'Failed to fetch events'
      };
    }
  }

  // Get company news
  async getCompanyNews(symbol, limit = 10) {
    try {
      const { data } = await axios.get(`${API_ENDPOINTS.COMPANY_NEWS(symbol)}?limit=${limit}`);
      return { success: true, data };
    } catch (error) {
      console.error('Failed to fetch company news:', error);
      return {
        success: false,
        error: error.response?.data?.message || error.message || 'Failed to fetch news'
      };
    }
  }

  // Validate symbol
  isValidSymbol(symbol) {
    return symbol && typeof symbol === 'string' && symbol.trim().length > 0;
  }
}

const companyServiceInstance = new CompanyService();
export default companyServiceInstance;