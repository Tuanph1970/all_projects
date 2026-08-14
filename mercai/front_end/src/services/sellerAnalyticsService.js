import { apiClient } from './apiClient.js';
import { API_CONFIG } from '../constants/config.js';

// Analytics interfaces
class SellerAnalyticsService {
  // Get comprehensive dashboard analytics
  async getDashboardAnalytics(days = 30) {
    return await apiClient.get(`${API_CONFIG.ENDPOINTS.SELLER_ANALYTICS}/analytics/dashboard`, {
      params: { days }
    });
  }

  // Get revenue trends over time
  async getRevenueTrends(
    days = 90,
    granularity = 'day'
  ) {
    return await apiClient.get(`${API_CONFIG.ENDPOINTS.SELLER_ANALYTICS}/analytics/revenue-trends`, {
      params: { days, granularity }
    });
  }

  // Get category performance analytics
  async getCategoryPerformance(days = 90) {
    return await apiClient.get(`${API_CONFIG.ENDPOINTS.SELLER_ANALYTICS}/analytics/category-performance`, {
      params: { days }
    });
  }

  // Get customer demographics and behavior
  async getCustomerDemographics(days = 90) {
    return await apiClient.get(`${API_CONFIG.ENDPOINTS.SELLER_ANALYTICS}/analytics/customer-demographics`, {
      params: { days }
    });
  }

  // Get detailed performance metrics
  async getPerformanceMetrics(days = 30) {
    return await apiClient.get(`${API_CONFIG.ENDPOINTS.SELLER_ANALYTICS}/analytics/performance-metrics`, {
      params: { days }
    });
  }

  // Get top performing products
  async getTopProducts(
    days = 30,
    metric = 'revenue',
    limit = 10
  ) {
    return await apiClient.get(`${API_CONFIG.ENDPOINTS.SELLER_ANALYTICS}/analytics/top-products`, {
      params: { days, metric, limit }
    });
  }

  // Compare performance between two periods
  async getComparisonAnalytics(
    period1Days = 30,
    period2Days = 30
  ) {
    return await apiClient.get(`${API_CONFIG.ENDPOINTS.SELLER_ANALYTICS}/analytics/comparison`, {
      params: {
        period1_days: period1Days,
        period2_days: period2Days
      }
    });
  }

  // Helper methods for data formatting and analysis
  formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount);
  }

  formatNumber(num) {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
  }

  formatPercentage(value, decimals = 1) {
    return `${value.toFixed(decimals)}%`;
  }

  formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  }

  formatTrendPeriod(period, granularity) {
    if (granularity === 'day') {
      return new Date(period).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric'
      });
    } else if (granularity === 'week') {
      // Format week periods (e.g., "2024-W12")
      const [year, week] = period.split('-W');
      return `Week ${week}`;
    } else {
      // Format month periods (e.g., "2024-03")
      const [year, month] = period.split('-');
      return new Date(parseInt(year), parseInt(month) - 1).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long'
      });
    }
  }

  getGrowthColor(value) {
    if (value > 0) return '#10B981'; // green
    if (value < 0) return '#EF4444'; // red
    return '#6B7280'; // gray
  }

  getGrowthIcon(value) {
    if (value > 0) return '📈';
    if (value < 0) return '📉';
    return '➖';
  }

  getPerformanceGrade(value, thresholds) {
    if (value >= thresholds.excellent) {
      return { grade: 'A+', color: '#10B981', description: 'Excellent' };
    } else if (value >= thresholds.good) {
      return { grade: 'B+', color: '#3B82F6', description: 'Good' };
    } else if (value >= thresholds.fair) {
      return { grade: 'C', color: '#F59E0B', description: 'Fair' };
    } else {
      return { grade: 'D', color: '#EF4444', description: 'Needs Improvement' };
    }
  }

  generateInsights(metrics) {
    const insights = [];
    
    // Revenue growth insights
    if (metrics.growth_rates && metrics.growth_rates.revenue_growth > 20) {
      insights.push('🚀 Revenue is growing strongly! Keep up the great work.');
    } else if (metrics.growth_rates && metrics.growth_rates.revenue_growth < -10) {
      insights.push('⚠️ Revenue is declining. Review pricing and marketing strategies.');
    }

    // Customer growth insights  
    if (metrics.growth_rates && metrics.growth_rates.customer_growth > 15) {
      insights.push('👥 Customer base is expanding rapidly! Focus on retention strategies.');
    } else if (metrics.growth_rates && metrics.growth_rates.customer_growth < 0) {
      insights.push('⚠️ Customer acquisition is declining. Consider improving marketing efforts.');
    }

    // Efficiency insights
    if (metrics.efficiency_metrics && metrics.efficiency_metrics.conversion_rate < 2) {
      insights.push('📈 Low conversion rate. Consider improving product presentations.');
    }

    if (metrics.efficiency_metrics && metrics.efficiency_metrics.refund_rate > 5) {
      insights.push('🔄 High refund rate. Review product quality and customer expectations.');
    }

    if (metrics.current_period && metrics.current_period.avg_fulfillment_days > 3) {
      insights.push('⏱️ Fulfillment time is high. Consider streamlining your shipping process.');
    }

    return insights.length > 0 ? insights : ['📊 Your analytics look stable. Keep monitoring for trends.'];
  }

  generateRecommendations(dashboard, performance) {
    const recommendations = [];

    // Stock management
    if (dashboard && dashboard.products && dashboard.products.stock_ratio < 80) {
      recommendations.push('📦 Restock low inventory items to avoid lost sales.');
    }

    // Revenue optimization
    if (performance && performance.current_period && performance.current_period.avg_order_value < 50) {
      recommendations.push('💰 Consider bundling products or upselling to increase average order value.');
    }

    // Customer retention
    if (performance && performance.efficiency_metrics && performance.efficiency_metrics.customer_lifetime_value < 100) {
      recommendations.push('🤝 Implement customer retention strategies like loyalty programs.');
    }

    // Performance improvement
    if (performance && performance.efficiency_metrics && performance.efficiency_metrics.conversion_rate < 3) {
      recommendations.push('🎨 Improve product photos and descriptions to boost conversion rates.');
    }

    // Review engagement
    if (dashboard && dashboard.reviews && dashboard.reviews.total_reviews < 10) {
      recommendations.push('⭐ Encourage customers to leave reviews to build trust.');
    }

    return recommendations.length > 0 ? recommendations : ['✨ Your performance metrics look good! Keep up the excellent work.'];
  }

  // TODO: Backend endpoint not implemented - /analytics/export does not exist
  // Generate export URL for analytics data
  generateExportUrl(
    type = 'comprehensive',
    period = 30
  ) {
    // In a real implementation, this would generate and return a download URL
    // For now, return a mock URL
    return `/api/v1/seller/analytics/analytics/export?type=${type}&period=${period}`;
  }

  // TODO: Backend endpoint not implemented - /analytics/schedule-report does not exist
  // Schedule analytics reports
  async scheduleReport(
    frequency,
    email,
    reportTypes
  ) {
    return await apiClient.post(`${API_CONFIG.ENDPOINTS.SELLER_ANALYTICS}/analytics/schedule-report`, {
      frequency,
      email,
      report_types: reportTypes
    });
  }
}

export default new SellerAnalyticsService();