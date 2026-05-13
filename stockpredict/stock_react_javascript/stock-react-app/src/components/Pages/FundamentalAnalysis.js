import React, { useState, useEffect } from 'react';
import { analysisAPI, stockAPI } from '../../services/api';
import { TrendingUp, AlertCircle, DollarSign, BarChart2, Activity, Briefcase, Search } from 'lucide-react';

export const FundamentalAnalysis = () => {
  const [selectedSymbol, setSelectedSymbol] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [analysisData, setAnalysisData] = useState(null);

  // Stock search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [showResults, setShowResults] = useState(false);
  const [isSearching, setIsSearching] = useState(false);

  useEffect(() => {
    // Listen for stock selection from header search
    const handleStockSelection = (event) => {
      const { symbol } = event.detail;
      if (symbol) {
        setSelectedSymbol(symbol);
        setSearchQuery(symbol);
        fetchFundamentalAnalysis(symbol);
      }
    };

    document.addEventListener('viewStock', handleStockSelection);
    return () => document.removeEventListener('viewStock', handleStockSelection);
  }, []);

  const fetchFundamentalAnalysis = async (symbol) => {
    setLoading(true);
    setError(null);
    try {
      const data = await analysisAPI.getFundamentalAnalysis(symbol);
      setAnalysisData(data);
    } catch (err) {
      setError('Failed to fetch fundamental analysis data');
      console.error('Error:', err);
    } finally {
      setLoading(false);
    }
  };

  // Stock search functionality
  const handleSearch = async (query) => {
    if (!query.trim()) {
      setSearchResults([]);
      setShowResults(false);
      return;
    }

    setIsSearching(true);
    try {
      const results = await stockAPI.searchStock(query);
      setSearchResults(results);
      setShowResults(true);
    } catch (error) {
      console.error('Search error:', error);
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const handleSearchChange = (e) => {
    const value = e.target.value;
    setSearchQuery(value);

    // Clear existing timeout
    if (window.searchTimeout) {
      clearTimeout(window.searchTimeout);
    }

    // Debounce search
    window.searchTimeout = setTimeout(() => {
      handleSearch(value);
    }, 300);
  };

  const handleStockSelect = (stock) => {
    setSearchQuery(stock.symbol);
    setShowResults(false);
    setSelectedSymbol(stock.symbol);
    fetchFundamentalAnalysis(stock.symbol);
  };

  const handleSearchFocus = () => {
    if (searchQuery) {
      setShowResults(true);
    }
  };

  const handleSearchBlur = () => {
    // Delay hiding results to allow for click events
    setTimeout(() => setShowResults(false), 300);
  };

  const formatCurrency = (value) => {
    if (!value) return 'N/A';
    if (Math.abs(value) >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
    if (Math.abs(value) >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
    if (Math.abs(value) >= 1e3) return `$${(value / 1e3).toFixed(2)}K`;
    return `$${value.toFixed(2)}`;
  };

  const formatPercentage = (value) => {
    if (value === null || value === undefined) return 'N/A';
    return `${value.toFixed(2)}%`;
  };

  const formatNumber = (value) => {
    if (value === null || value === undefined) return 'N/A';
    return value.toFixed(2);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'bullish':
      case 'strong':
      case 'undervalued':
        return 'text-green-600';
      case 'bearish':
      case 'weak':
      case 'overvalued':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const getStatusBgColor = (status) => {
    switch (status) {
      case 'bullish':
      case 'strong':
      case 'undervalued':
        return 'bg-green-50';
      case 'bearish':
      case 'weak':
      case 'overvalued':
        return 'bg-red-50';
      default:
        return 'bg-gray-50';
    }
  };

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-lg font-bold text-gray-900">Phân tích cơ bản</h1>

        {/* Stock Search */}
        <div className="relative">
          <div className="flex items-center bg-white border border-gray-300 rounded-lg px-3 py-2 focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500">
            <Search className="w-5 h-5 text-gray-400 mr-2" />
            <input
              type="text"
              placeholder="Tìm cổ phiếu (VD: TCB, VIC)..."
              value={searchQuery}
              onChange={handleSearchChange}
              onFocus={handleSearchFocus}
              onBlur={handleSearchBlur}
              className="outline-none flex-1 min-w-0 w-64"
            />
          </div>

          {showResults && (
            <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-300 rounded-lg shadow-lg z-50 max-h-60 overflow-y-auto">
              {isSearching ? (
                <div className="p-3 text-center text-gray-500">Đang tìm kiếm...</div>
              ) : searchResults.length > 0 ? (
                searchResults.map((stock) => (
                  <button
                    key={stock.symbol}
                    className="w-full text-left px-3 py-2 hover:bg-gray-50 border-b border-gray-100 last:border-b-0"
                    onMouseDown={(e) => {
                      e.preventDefault();
                      handleStockSelect(stock);
                    }}
                  >
                    <div className="flex justify-between items-center">
                      <div>
                        <div className="font-semibold text-gray-900">{stock.symbol}</div>
                        <div className="text-sm text-gray-600">{stock.name}</div>
                      </div>
                      <div className="text-right">
                        <div className="font-semibold text-blue-600">${stock.price}</div>
                      </div>
                    </div>
                  </button>
                ))
              ) : (
                <div className="p-3 text-center text-gray-500">Không tìm thấy kết quả</div>
              )}
            </div>
          )}
        </div>
      </div>
      
      {!selectedSymbol ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
          <AlertCircle className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-700 mb-2">Chưa chọn cổ phiếu</h2>
          <p className="text-gray-500">
            Vui lòng tìm và chọn một cổ phiếu từ thanh tìm kiếm để xem phân tích cơ bản
          </p>
        </div>
      ) : loading ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Đang tải phân tích cơ bản cho {selectedSymbol}...</p>
        </div>
      ) : error ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-700 mb-2">Lỗi tải dữ liệu</h2>
          <p className="text-gray-500">{error}</p>
          <button
            onClick={() => fetchFundamentalAnalysis(selectedSymbol)}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Thử lại
          </button>
        </div>
      ) : analysisData ? (
        <div className="space-y-4">
          {/* Company Overview - Header Card with 6-Column Table */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-bold text-gray-900">
                {analysisData.company_info?.name || selectedSymbol}
              </h2>
              <span className="text-lg font-bold text-blue-600">{selectedSymbol}</span>
            </div>
            <table className="w-full text-sm">
              <tbody>
                <tr className="border-b border-gray-100">
                  <td className="py-2 text-gray-500 w-1/6">Vốn hóa</td>
                  <td className="py-2 font-semibold text-blue-600 w-1/6">{formatCurrency(analysisData.company_info?.marketCap)}</td>
                  <td className="py-2 text-gray-500 w-1/6">Ngành</td>
                  <td className="py-2 font-semibold w-1/6">{analysisData.company_info?.industry || 'N/A'}</td>
                  <td className="py-2 text-gray-500 w-1/6">Lĩnh vực</td>
                  <td className="py-2 font-semibold w-1/6">{analysisData.company_info?.sector || 'N/A'}</td>
                </tr>
                <tr>
                  <td className="py-2 text-gray-500">Sàn giao dịch</td>
                  <td className="py-2 font-semibold">{analysisData.company_info?.exchange || 'N/A'}</td>
                  <td className="py-2"></td>
                  <td className="py-2"></td>
                  <td className="py-2"></td>
                  <td className="py-2"></td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Valuation Summary - 6-Column Table Layout */}
          {analysisData.valuation_summary && (
            <div className={`rounded-xl shadow-sm border border-gray-200 p-4 ${getStatusBgColor(analysisData.valuation_summary.status)}`}>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-bold text-gray-900">Tóm tắt định giá</h2>
                <div className="flex items-center space-x-2">
                  <span className={`text-lg font-bold ${getStatusColor(analysisData.valuation_summary.status)}`}>
                    {analysisData.valuation_summary.status?.toUpperCase()}
                  </span>
                  <span className="text-xs text-gray-500">
                    (Điểm: {analysisData.valuation_summary.score}/100)
                  </span>
                </div>
              </div>
              <table className="w-full text-sm">
                <tbody>
                  {(() => {
                    const factors = analysisData.valuation_summary.factors || [];
                    const rows = [];
                    for (let i = 0; i < factors.length; i += 3) {
                      rows.push(
                        <tr key={i} className={i < factors.length - 3 ? "border-b border-gray-200" : ""}>
                          {[0, 1, 2].map(offset => {
                            const factor = factors[i + offset];
                            if (!factor) return <React.Fragment key={offset}><td className="py-2 w-1/6"></td><td className="py-2 w-1/6"></td></React.Fragment>;
                            return (
                              <React.Fragment key={offset}>
                                <td className="py-2 text-gray-500 w-1/6">{factor.factor}</td>
                                <td className={`py-2 font-semibold w-1/6 ${getStatusColor(factor.status)}`}>
                                  {factor.value} <span className="text-gray-400 text-xs">({factor.status})</span>
                                </td>
                              </React.Fragment>
                            );
                          })}
                        </tr>
                      );
                    }
                    return rows;
                  })()}
                </tbody>
              </table>
            </div>
          )}

          {/* Financial Ratios - 6-Column Table Layout */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <h3 className="text-sm font-bold text-gray-900 mb-3 flex items-center">
              <BarChart2 className="w-4 h-4 mr-2" />
              Tỷ số tài chính
            </h3>
            <table className="w-full text-sm">
              <tbody>
                <tr className="border-b border-gray-100">
                  <td className="py-2 text-gray-500 w-1/6">P/E</td>
                  <td className="py-2 font-semibold text-blue-600 w-1/6">{formatNumber(analysisData.financial_ratios?.pe)}</td>
                  <td className="py-2 text-gray-500 w-1/6">ROE</td>
                  <td className="py-2 font-semibold text-green-600 w-1/6">{formatPercentage(analysisData.financial_ratios?.roe)}</td>
                  <td className="py-2 text-gray-500 w-1/6">ROA</td>
                  <td className="py-2 font-semibold text-purple-600 w-1/6">{formatPercentage(analysisData.financial_ratios?.roa)}</td>
                </tr>
                <tr className="border-b border-gray-100">
                  <td className="py-2 text-gray-500">Nợ/Vốn CSH</td>
                  <td className="py-2 font-semibold text-yellow-600">{formatNumber(analysisData.financial_ratios?.debtToEquity)}</td>
                  <td className="py-2 text-gray-500">Hệ số thanh toán</td>
                  <td className="py-2 font-semibold text-red-600">{formatNumber(analysisData.financial_ratios?.currentRatio)}</td>
                  <td className="py-2 text-gray-500">Biên lợi nhuận gộp</td>
                  <td className="py-2 font-semibold text-indigo-600">{formatPercentage(analysisData.financial_ratios?.grossMargin)}</td>
                </tr>
                <tr>
                  <td className="py-2 text-gray-500">Biên lợi nhuận ròng</td>
                  <td className="py-2 font-semibold text-pink-600">{formatPercentage(analysisData.financial_ratios?.netMargin)}</td>
                  <td className="py-2 text-gray-500">P/B</td>
                  <td className="py-2 font-semibold text-gray-600">{formatNumber(analysisData.financial_ratios?.pb)}</td>
                  <td className="py-2"></td>
                  <td className="py-2"></td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Growth Metrics - 6-Column Table Layout */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <h3 className="text-sm font-bold text-gray-900 mb-3 flex items-center">
              <TrendingUp className="w-4 h-4 mr-2" />
              Chỉ số tăng trưởng (YoY)
            </h3>
            <table className="w-full text-sm">
              <tbody>
                <tr>
                  <td className="py-2 text-gray-500 w-1/6">Tăng trưởng DT</td>
                  <td className="py-2 font-semibold w-1/6">
                    <span className={analysisData.growth_metrics?.revenueGrowth > 0 ? 'text-green-600' : 'text-red-600'}>
                      {formatPercentage(analysisData.growth_metrics?.revenueGrowth)}
                    </span>
                    <span className="text-xs text-gray-400 ml-1">
                      {analysisData.growth_metrics?.revenueGrowth > 0 ? '↑' : '↓'}
                    </span>
                  </td>
                  <td className="py-2 text-gray-500 w-1/6">Tăng trưởng LN</td>
                  <td className="py-2 font-semibold w-1/6">
                    <span className={analysisData.growth_metrics?.earningsGrowth > 0 ? 'text-green-600' : 'text-red-600'}>
                      {formatPercentage(analysisData.growth_metrics?.earningsGrowth)}
                    </span>
                    <span className="text-xs text-gray-400 ml-1">
                      {analysisData.growth_metrics?.earningsGrowth > 0 ? '↑' : '↓'}
                    </span>
                  </td>
                  <td className="py-2 text-gray-500 w-1/6">Tăng trưởng EPS</td>
                  <td className="py-2 font-semibold w-1/6">
                    <span className={analysisData.growth_metrics?.epsGrowth > 0 ? 'text-green-600' : 'text-red-600'}>
                      {formatPercentage(analysisData.growth_metrics?.epsGrowth)}
                    </span>
                    <span className="text-xs text-gray-400 ml-1">
                      {analysisData.growth_metrics?.epsGrowth > 0 ? '↑' : '↓'}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Financial Statements - 6-Column Table Layout */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <h3 className="text-sm font-bold text-gray-900 mb-3 flex items-center">
              <DollarSign className="w-4 h-4 mr-2" />
              Báo cáo kết quả kinh doanh
            </h3>
            <table className="w-full text-sm">
              <tbody>
                <tr className="border-b border-gray-100">
                  <td className="py-2 text-gray-500 w-1/6">Doanh thu</td>
                  <td className="py-2 font-semibold text-blue-600 w-1/6">{formatCurrency(analysisData.income_statement?.revenue)}</td>
                  <td className="py-2 text-gray-500 w-1/6">Lợi nhuận gộp</td>
                  <td className="py-2 font-semibold text-green-600 w-1/6">{formatCurrency(analysisData.income_statement?.grossProfit)}</td>
                  <td className="py-2 text-gray-500 w-1/6">LN hoạt động</td>
                  <td className="py-2 font-semibold text-purple-600 w-1/6">{formatCurrency(analysisData.income_statement?.operatingIncome)}</td>
                </tr>
                <tr>
                  <td className="py-2 text-gray-500">LN ròng</td>
                  <td className="py-2 font-semibold text-indigo-600">{formatCurrency(analysisData.income_statement?.netIncome)}</td>
                  <td className="py-2 text-gray-500">EPS</td>
                  <td className="py-2 font-semibold text-pink-600">{formatNumber(analysisData.income_statement?.eps)}</td>
                  <td className="py-2"></td>
                  <td className="py-2"></td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Balance Sheet - 6-Column Table Layout */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <h3 className="text-sm font-bold text-gray-900 mb-3 flex items-center">
              <Briefcase className="w-4 h-4 mr-2" />
              Bảng cân đối kế toán
            </h3>
            <table className="w-full text-sm">
              <tbody>
                <tr className="border-b border-gray-100">
                  <td className="py-2 text-gray-500 w-1/6">Tổng tài sản</td>
                  <td className="py-2 font-semibold text-blue-600 w-1/6">{formatCurrency(analysisData.balance_sheet?.totalAssets)}</td>
                  <td className="py-2 text-gray-500 w-1/6">Tổng nợ phải trả</td>
                  <td className="py-2 font-semibold text-red-600 w-1/6">{formatCurrency(analysisData.balance_sheet?.totalLiabilities)}</td>
                  <td className="py-2 text-gray-500 w-1/6">Vốn chủ sở hữu</td>
                  <td className="py-2 font-semibold text-green-600 w-1/6">{formatCurrency(analysisData.balance_sheet?.totalEquity)}</td>
                </tr>
                <tr>
                  <td className="py-2 text-gray-500">Tiền mặt</td>
                  <td className="py-2 font-semibold text-teal-600">{formatCurrency(analysisData.balance_sheet?.cash)}</td>
                  <td className="py-2 text-gray-500">Nợ dài hạn</td>
                  <td className="py-2 font-semibold text-orange-600">{formatCurrency(analysisData.balance_sheet?.longTermDebt)}</td>
                  <td className="py-2"></td>
                  <td className="py-2"></td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Cash Flow - 6-Column Table Layout */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <h3 className="text-sm font-bold text-gray-900 mb-3 flex items-center">
              <Activity className="w-4 h-4 mr-2" />
              Báo cáo lưu chuyển tiền tệ
            </h3>
            <table className="w-full text-sm">
              <tbody>
                <tr className="border-b border-gray-100">
                  <td className="py-2 text-gray-500 w-1/6">LCTT hoạt động</td>
                  <td className="py-2 font-semibold text-blue-600 w-1/6">{formatCurrency(analysisData.cash_flow?.operatingCashFlow)}</td>
                  <td className="py-2 text-gray-500 w-1/6">LCTT đầu tư</td>
                  <td className="py-2 font-semibold text-purple-600 w-1/6">{formatCurrency(analysisData.cash_flow?.investingCashFlow)}</td>
                  <td className="py-2 text-gray-500 w-1/6">LCTT tài chính</td>
                  <td className="py-2 font-semibold text-indigo-600 w-1/6">{formatCurrency(analysisData.cash_flow?.financingCashFlow)}</td>
                </tr>
                <tr>
                  <td className="py-2 text-gray-500">Dòng tiền tự do</td>
                  <td className="py-2 font-semibold text-green-600">{formatCurrency(analysisData.cash_flow?.freeCashFlow)}</td>
                  <td className="py-2 text-gray-500">Dòng tiền ròng</td>
                  <td className="py-2 font-semibold text-teal-600">{formatCurrency(analysisData.cash_flow?.netCashFlow)}</td>
                  <td className="py-2"></td>
                  <td className="py-2"></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </div>
  );
};
