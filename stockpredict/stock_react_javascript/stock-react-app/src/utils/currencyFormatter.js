/**
 * Currency formatting utilities for Vietnamese Dong (VND)
 */

/**
 * Format number as Vietnamese Dong currency
 * @param {number} amount - The amount to format
 * @param {Object} options - Formatting options
 * @returns {string} Formatted currency string
 */
export const formatVND = (amount, options = {}) => {
  const {
    showSymbol = true,
    showDecimals = false,
    locale = 'vi-VN'
  } = options;

  if (amount === null || amount === undefined || isNaN(amount)) {
    return showSymbol ? '0 ₫' : '0';
  }

  const numericAmount = parseFloat(amount);

  try {
    if (showSymbol) {
      const numberPart = numericAmount.toLocaleString(locale, {
        minimumFractionDigits: showDecimals ? 2 : 0,
        maximumFractionDigits: showDecimals ? 2 : 0
      });
      return `${numberPart} ₫`;
    } else {
      return numericAmount.toLocaleString(locale, {
        minimumFractionDigits: showDecimals ? 2 : 0,
        maximumFractionDigits: showDecimals ? 2 : 0
      });
    }
  } catch (error) {
    // Fallback formatting
    const numberPart = numericAmount.toFixed(showDecimals ? 2 : 0).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    return showSymbol ? `${numberPart} ₫` : numberPart;
  }
};

/**
 * Format stock price specifically (multiplies by 1000 for Vietnamese stocks)
 * @param {number} price - Raw price from API
 * @param {Object} options - Formatting options
 * @returns {string} Formatted price string
 */
export const formatStockPrice = (price, options = {}) => {
  if (price === null || price === undefined || isNaN(price)) {
    return formatVND(0, options);
  }

  // Vietnamese stock prices are typically shown in thousands
  const adjustedPrice = parseFloat(price) * 1000;
  return formatVND(adjustedPrice, options);
};

/**
 * Format percentage change
 * @param {number} value - The percentage value
 * @param {number} decimals - Number of decimal places (default: 2)
 * @returns {string} Formatted percentage string with color indicator
 */
export const formatPercentageChange = (value, decimals = 2) => {
  if (value === null || value === undefined || isNaN(value)) {
    return '0.00%';
  }

  const numericValue = parseFloat(value);
  const formatted = numericValue.toFixed(decimals);
  const sign = numericValue > 0 ? '+' : '';

  return `${sign}${formatted}%`;
};

/**
 * Get color class for percentage change
 * @param {number} value - The percentage value
 * @returns {string} CSS class name for styling
 */
export const getChangeColorClass = (value) => {
  if (value === null || value === undefined || isNaN(value)) {
    return 'text-neutral';
  }

  const numericValue = parseFloat(value);
  if (numericValue > 0) return 'text-success';
  if (numericValue < 0) return 'text-danger';
  return 'text-warning';
};

/**
 * Format market cap value
 * @param {number} value - Market cap value
 * @returns {string} Formatted market cap string
 */
export const formatMarketCap = (value) => {
  if (value === null || value === undefined || isNaN(value)) {
    return formatVND(0);
  }

  const numericValue = parseFloat(value);

  if (numericValue >= 1e12) {
    return formatVND(numericValue / 1e12, { showDecimals: true }) + ' nghìn tỷ';
  } else if (numericValue >= 1e9) {
    return formatVND(numericValue / 1e9, { showDecimals: true }) + ' tỷ';
  } else if (numericValue >= 1e6) {
    return formatVND(numericValue / 1e6, { showDecimals: true }) + ' triệu';
  }

  return formatVND(numericValue);
};

/**
 * Format volume with appropriate units
 * @param {number} value - Volume value
 * @returns {string} Formatted volume string
 */
export const formatVolume = (value) => {
  if (value === null || value === undefined || isNaN(value)) {
    return '0';
  }

  const numericValue = parseFloat(value);

  if (numericValue >= 1e9) {
    return `${(numericValue / 1e9).toFixed(1)}B`;
  } else if (numericValue >= 1e6) {
    return `${(numericValue / 1e6).toFixed(1)}M`;
  } else if (numericValue >= 1e3) {
    return `${(numericValue / 1e3).toFixed(1)}K`;
  }

  return numericValue.toLocaleString('vi-VN');
};

/**
 * Parse VND formatted string back to number
 * @param {string} vndString - VND formatted string
 * @returns {number} Parsed numeric value
 */
export const parseVND = (vndString) => {
  if (!vndString || typeof vndString !== 'string') {
    return 0;
  }

  // Remove currency symbol and spaces
  const cleanString = vndString.replace(/[₫\s]/g, '');
  // Remove thousand separators (commas or dots)
  const numberString = cleanString.replace(/[,.]/g, '');

  return parseFloat(numberString) || 0;
};

// Export all utilities as default
const currencyFormatter = {
  formatVND,
  formatStockPrice,
  formatPercentageChange,
  getChangeColorClass,
  formatMarketCap,
  formatVolume,
  parseVND
};

export default currencyFormatter;