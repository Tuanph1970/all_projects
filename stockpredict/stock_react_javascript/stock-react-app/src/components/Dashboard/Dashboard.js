// src/components/Dashboard/Dashboard.js
import React, { useState, useEffect } from 'react';
import { TrendingUp, BarChart3, PieChart, Star, Newspaper } from 'lucide-react';
import { stockAPI } from '../../services/api';
import { useRouter } from '../../context/RouterContext';
import Contact from '../Contact/Contact';

const Dashboard = () => {
  const [portfolio, setPortfolio] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [prospectiveStocks, setProspectiveStocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const { navigate } = useRouter();

  const handleSymbolClick = (symbol) => {
    navigate(`company/${symbol}`);
  };

  useEffect(() => {
    const loadDashboardData = async () => {
      try {
        setLoading(true);
        const [portfolioData, recommendationsData, prospectiveData] = await Promise.all([
          stockAPI.getPortfolio(),
          stockAPI.getRecommendations(),
          stockAPI.getProspectiveStocks()
        ]);
        setPortfolio(portfolioData);
        setRecommendations(recommendationsData);
        setProspectiveStocks(prospectiveData);
        console.log('Recommendations data:', recommendationsData);
        console.log('Prospective stocks data:', prospectiveData);
      } catch (error) {
        console.error('Error loading dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    loadDashboardData();
  }, []);

  const totalValue = portfolio.reduce((sum, stock) => sum + (stock.shares * stock.currentPrice), 0);
  const totalGainLoss = portfolio.reduce((sum, stock) => 
    sum + (stock.shares * (stock.currentPrice - stock.avgPrice)), 0
  );

  const getRecommendationStyle = (recommendation) => {
    if (!recommendation) return 'bg-gray-50 border-gray-200';
    switch (recommendation.toLowerCase()) {
      case 'buy':
        return 'bg-green-50 border-green-200';
      case 'sell':
        return 'bg-red-50 border-red-200';
      case 'hold':
        return 'bg-yellow-50 border-yellow-200';
      default:
        return 'bg-gray-50 border-gray-200';
    }
  };

  const getBadgeStyle = (recommendation) => {
    if (!recommendation) return 'bg-gray-50 border-gray-200';
    switch (recommendation.toLowerCase()) {
      case 'buy':
        return 'bg-green-600 text-white';
      case 'sell':
        return 'bg-red-600 text-white';
      case 'hold':
        return 'bg-yellow-600 text-white';
      default:
        return 'bg-gray-600 text-white';
    }
  };

  const getConfidenceStyle = (recommendation) => {
    if (!recommendation) return 'bg-gray-50 border-gray-200';
    switch (recommendation.toLowerCase()) {
      case 'buy':
        return 'text-green-600';
      case 'sell':
        return 'text-red-600';
      case 'hold':
        return 'text-yellow-600';
      default:
        return 'text-gray-600';
    }
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-gray-200 rounded w-48"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-32 bg-gray-200 rounded-xl"></div>
            ))}
          </div>
          <div className="h-64 bg-gray-200 rounded-xl"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Bảng điều khiển</h1>
        <div className="text-sm text-gray-500">
          Cập nhật lúc: {new Date().toLocaleString('vi-VN')}
        </div>
      </div>

      {/* Portfolio Overview - Single Horizontal Row */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-600">Tổng giá trị</p>
              <p className="text-xl font-bold text-gray-900">
                ${totalValue.toLocaleString(undefined, { maximumFractionDigits: 2 })}
              </p>
            </div>
            <div className="bg-green-100 p-2 rounded-full">
              <TrendingUp className="w-5 h-5 text-green-600" />
            </div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-600">Lãi/Lỗ</p>
              <p className={`text-xl font-bold ${totalGainLoss >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {totalGainLoss >= 0 ? '+' : ''}${totalGainLoss.toLocaleString(undefined, { maximumFractionDigits: 2 })}
              </p>
            </div>
            <div className="bg-blue-100 p-2 rounded-full">
              <BarChart3 className="w-5 h-5 text-blue-600" />
            </div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-600">Cổ phiếu nắm giữ</p>
              <p className="text-xl font-bold text-gray-900">{portfolio.length}</p>
            </div>
            <div className="bg-purple-100 p-2 rounded-full">
              <PieChart className="w-5 h-5 text-purple-600" />
            </div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-600">Thay đổi trong ngày</p>
              <p className="text-xl font-bold text-green-600">+2.34%</p>
            </div>
            <div className="bg-orange-100 p-2 rounded-full">
              <TrendingUp className="w-5 h-5 text-orange-600" />
            </div>
          </div>
        </div>
      </div>

      {/* Portfolio Holdings - Professional Enhanced Table */}
      <div className="bg-white rounded-2xl shadow-lg border-0 overflow-hidden">
        {/* Header with gradient accent */}
        <div className="relative p-6 border-b border-gray-100">
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500"></div>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg">
              <PieChart className="w-5 h-5 text-white" />
            </div>
            <h2 className="text-xl font-bold text-gray-900">Danh mục đầu tư</h2>
          </div>
        </div>

        <div className="p-6">
          {/* Table Header with Gradient */}
          <div className="flex text-left text-sm font-semibold mb-2 rounded-xl overflow-hidden"
               style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
            <div className="flex-1 px-4 py-3 text-white">Mã CP</div>
            <div className="flex-[2] px-4 py-3 text-white">Công ty</div>
            <div className="flex-1 px-4 py-3 text-white text-right">Số lượng</div>
            <div className="flex-1 px-4 py-3 text-white text-right">Giá TB</div>
            <div className="flex-1 px-4 py-3 text-white text-right">Giá hiện tại</div>
            <div className="flex-1 px-4 py-3 text-white text-right">Thay đổi</div>
            <div className="flex-1 px-4 py-3 text-white text-right">Giá trị</div>
          </div>

          {/* Table Body */}
          <div className="space-y-1">
            {portfolio.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <PieChart className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                <p className="font-medium">Chưa có cổ phiếu</p>
                <p className="text-sm mt-1">Bắt đầu xây dựng danh mục của bạn</p>
              </div>
            ) : (
              portfolio.map((stock, index) => (
                <div
                  key={stock.symbol}
                  className={`flex items-center py-4 px-2 rounded-xl transition-all duration-300 hover:shadow-md hover:scale-[1.01] cursor-pointer ${
                    index % 2 === 0 ? 'bg-gradient-to-r from-gray-50 to-white' : 'bg-white'
                  }`}
                  style={{ borderLeft: '3px solid transparent' }}
                  onMouseEnter={(e) => e.currentTarget.style.borderLeftColor = '#667eea'}
                  onMouseLeave={(e) => e.currentTarget.style.borderLeftColor = 'transparent'}
                >
                  {/* Symbol Badge */}
                  <div className="flex-1 px-2">
                    <span
                      className="inline-flex items-center px-3 py-1.5 rounded-lg font-bold text-sm text-white cursor-pointer transition-all duration-200 hover:scale-105"
                      style={{ background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)', boxShadow: '0 2px 4px rgba(59, 130, 246, 0.3)' }}
                      onClick={() => handleSymbolClick(stock.symbol)}
                    >
                      {stock.symbol}
                    </span>
                  </div>

                  {/* Company Name */}
                  <div className="flex-[2] px-2">
                    <span className="text-gray-700 font-medium truncate block">{stock.name}</span>
                  </div>

                  {/* Shares Badge */}
                  <div className="flex-1 px-2 text-right">
                    <span className="inline-flex items-center justify-center px-3 py-1 rounded-full text-sm font-semibold text-white"
                          style={{ background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)', minWidth: '50px' }}>
                      {stock.shares}
                    </span>
                  </div>

                  {/* Avg Price */}
                  <div className="flex-1 px-2 text-right">
                    <span className="inline-flex items-center px-2.5 py-1 rounded-md text-sm font-medium text-teal-700"
                          style={{ background: 'linear-gradient(135deg, #f0fdfa 0%, #ccfbf1 100%)', border: '1px solid #99f6e4' }}>
                      ${stock.avgPrice?.toFixed(2) || '0.00'}
                    </span>
                  </div>

                  {/* Current Price */}
                  <div className="flex-1 px-2 text-right">
                    <span className="inline-flex items-center px-2.5 py-1 rounded-md text-sm font-medium text-indigo-700"
                          style={{ background: 'linear-gradient(135deg, #eef2ff 0%, #e0e7ff 100%)', border: '1px solid #c7d2fe' }}>
                      ${stock.currentPrice?.toFixed(2) || '0.00'}
                    </span>
                  </div>

                  {/* Change Badge */}
                  <div className="flex-1 px-2 text-right">
                    <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-sm font-bold ${
                      parseFloat(stock.change) >= 0
                        ? 'text-green-700'
                        : 'text-red-700'
                    }`}
                    style={{
                      background: parseFloat(stock.change) >= 0
                        ? 'linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)'
                        : 'linear-gradient(135deg, #fee2e2 0%, #fecaca 100%)',
                      border: parseFloat(stock.change) >= 0 ? '1px solid #86efac' : '1px solid #fca5a5'
                    }}>
                      {stock.change}
                    </span>
                  </div>

                  {/* Total Value Badge */}
                  <div className="flex-1 px-2 text-right">
                    <span className="inline-flex items-center px-3 py-1.5 rounded-lg text-sm font-bold text-amber-800"
                          style={{ background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)', border: '1px solid #fcd34d', boxShadow: '0 2px 4px rgba(251, 191, 36, 0.2)' }}>
                      ${(stock.shares * (stock.currentPrice || 0)).toLocaleString()}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* AI Recommendations */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Khuyến nghị AI</h2>
        </div>
        <div className="p-6">
          <div className="space-y-4">
            {recommendations.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <p>Chưa có khuyến nghị AI.</p>
                <p className="text-sm mt-2">Vui lòng quay lại sau để xem khuyến nghị mới.</p>
              </div>
            ) : (
              recommendations.map((rec, index) => (
              <div
                key={index}
                className={`flex items-start space-x-4 p-4 rounded-lg border ${getRecommendationStyle(rec.type || rec.recommendation)}`}
              >
                <div className={`px-2 py-1 rounded text-xs font-medium ${getBadgeStyle(rec.type || rec.recommendation)}`}>
                  {rec.type || rec.recommendation}
                </div>
                <div className="flex-1">
                  <div className="font-medium text-gray-900">
                    <span
                      className="cursor-pointer hover:text-blue-600 hover:underline"
                      onClick={() => handleSymbolClick(rec.symbol)}
                    >
                      {rec.symbol}
                    </span>
                    {' - '}{rec.name}
                  </div>
                  <div className="text-sm text-gray-600 mt-1">
                    {rec.reason}
                  </div>
                  <div className={`text-xs mt-2 font-medium ${getConfidenceStyle(rec.type || rec.recommendation)}`}>
                    Độ tin cậy: {rec.confidence}%
                  </div>
                </div>
              </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Prospective Stocks - Fundamental Analysis */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <Star className="w-5 h-5 text-yellow-500" />
            <h2 className="text-lg font-semibold text-gray-900">Cổ phiếu tiềm năng</h2>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            Dựa trên phân tích cơ bản: tin tức tích cực, tỷ số P/E hấp dẫn và tăng trưởng lợi nhuận 2 năm
          </p>
        </div>
        <div className="p-6">
          {prospectiveStocks.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <p>Chưa có cổ phiếu tiềm năng.</p>
              <p className="text-sm mt-2">Vui lòng quay lại sau để xem phân tích mới.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {prospectiveStocks.map((stock, index) => (
                <div
                  key={index}
                  className="p-4 rounded-lg border border-blue-100 bg-gradient-to-r from-blue-50 to-indigo-50 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3">
                        <span
                          className="text-lg font-bold text-blue-700 cursor-pointer hover:text-blue-900 hover:underline"
                          onClick={() => handleSymbolClick(stock.symbol)}
                        >
                          {stock.symbol}
                        </span>
                        <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full">
                          {stock.sector}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 mt-1">{stock.name}</p>

                      {/* Fundamental Metrics */}
                      <div className="flex flex-wrap gap-4 mt-3">
                        <div className="flex items-center gap-1">
                          <span className="text-xs text-gray-500">Giá:</span>
                          <span className="text-sm font-medium text-gray-900">
                            ${stock.price?.toFixed(2) || 'N/A'}
                          </span>
                        </div>
                        <div className="flex items-center gap-1">
                          <span className="text-xs text-gray-500">P/E:</span>
                          <span className="text-sm font-medium text-indigo-600">
                            {stock.peRatio?.toFixed(1) || 'N/A'}
                          </span>
                        </div>
                        <div className="flex items-center gap-1">
                          <span className="text-xs text-gray-500">Tăng trưởng EPS (2 năm):</span>
                          <span className="text-sm font-medium text-green-600">
                            +{stock.epsGrowth2Y?.toFixed(1) || 'N/A'}%
                          </span>
                        </div>
                        <div className="flex items-center gap-1">
                          <span className="text-xs text-gray-500">Tăng trưởng lợi nhuận (2 năm):</span>
                          <span className="text-sm font-medium text-green-600">
                            +{stock.netProfitGrowth2Y?.toFixed(1) || 'N/A'}%
                          </span>
                        </div>
                      </div>

                      {/* News Highlight */}
                      <div className="mt-3 flex items-start gap-2">
                        <Newspaper className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
                        <p className="text-sm text-gray-600 italic">
                          {stock.news}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Contact Section */}
      <Contact />
    </div>
  );
};

export default Dashboard;