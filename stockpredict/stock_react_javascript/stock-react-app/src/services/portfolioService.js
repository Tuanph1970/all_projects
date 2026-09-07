// Portfolio Service - API calls for portfolio management
import { stockAPI } from './api';
import { formatVND } from '../utils/currencyFormatter';

class PortfolioService {
  
  // Get portfolio holdings
  async getPortfolio() {
    try {
      const data = await stockAPI.getPortfolio();
      return { success: true, data };
    } catch (error) {
      console.error('Failed to fetch portfolio:', error);
      return { success: false, error: error.message };
    }
  }

  // Get portfolio summary
  async getPortfolioSummary() {
    try {
      const data = await stockAPI.getPortfolioSummary();
      return { success: true, data };
    } catch (error) {
      console.error('Failed to fetch portfolio summary:', error);
      return { success: false, error: error.message };
    }
  }

  // Add stock to portfolio (buy)
  async addStock(symbol, companyName, shares, price) {
    try {
      const result = await stockAPI.buyStock(symbol, companyName, shares, price);
      return { success: true, data: result };
    } catch (error) {
      console.error('Failed to add stock:', error);
      return { success: false, error: error.message };
    }
  }

  // Sell shares from portfolio
  async sellStock(symbol, shares, price) {
    try {
      const result = await stockAPI.sellStock(symbol, shares, price);
      return { success: true, data: result };
    } catch (error) {
      console.error('Failed to sell stock:', error);
      return { success: false, error: error.message };
    }
  }

  // Remove stock from portfolio completely
  async removeStock(symbol) {
    try {
      const result = await stockAPI.removeStock(symbol);
      return { success: true, data: result };
    } catch (error) {
      console.error('Failed to remove stock:', error);
      return { success: false, error: error.message };
    }
  }

  // Get available stock options for selection
  async getStockOptions() {
    try {
      const data = await stockAPI.getPortfolioStockOption();
      return { success: true, data };
    } catch (error) {
      console.error('Failed to fetch stock options:', error);
      return { 
        success: false, 
        error: error.message,
        data: [] // Return empty array as fallback
      };
    }
  }

  // Calculate total cost for stock purchase
  calculateTotalCost(shares, price) {
    return (parseFloat(shares) * parseFloat(price) || 0).toFixed(2);
  }

  // Validate stock transaction data
  validateStockData(symbol, shares, price) {
    const errors = [];
    
    if (!symbol || symbol.trim() === '') {
      errors.push('Stock symbol is required');
    }
    
    if (!shares || isNaN(shares) || parseInt(shares) <= 0) {
      errors.push('Valid number of shares is required');
    }
    
    if (!price || isNaN(price) || parseFloat(price) <= 0) {
      errors.push('Valid stock price is required');
    }
    
    return {
      isValid: errors.length === 0,
      errors
    };
  }

  // Format portfolio data for display
  formatPortfolioData(portfolio) {
    if (!Array.isArray(portfolio)) return [];
    
    return portfolio.map(stock => ({
      ...stock,
      total_value: (stock.shares || 0) * (stock.price || 0),
      formattedPrice: formatVND(stock.price || 0),
      formattedTotalValue: formatVND((stock.shares || 0) * (stock.price || 0))
    }));
  }
}

const portfolioServiceInstance = new PortfolioService();
export default portfolioServiceInstance;