import React from "react";
import { useState, useEffect } from "react";
import { Tab, Tabs, TabList, TabPanel } from 'react-tabs';
import { StockGeneral } from "./stocks/StockGeneral";
import { StockPerformance } from "./stocks/StockPerformance";
import { StockAnalysis } from "./stocks/StockAnalysis";
import { StockDividend } from "./stocks/StockDividend";
import { StockFinancial } from "./stocks/StockFinancial";
import './stocks/StockComponents.css';
import { useNavigate } from "react-router-dom";
import httpClient from "../../services/httpClient";
import { API_ENDPOINTS } from "../../constants/api";



export const Stocks = () => {
  
    const [data, setTableRowsData] = useState([])
    const [isLoading, setIsLoading] = useState([]);
  
    useEffect(() => {
      (async () => {
        try {
          setIsLoading(true);
          const result = await httpClient.get(API_ENDPOINTS.COMPANIES_ALL);
          if (result.success && result.data) {
            setTableRowsData(result.data);
            console.log(result.data);
          }
        } catch (error) {
          console.error('Error fetching companies:', error);
        } finally {
          setIsLoading(false);
        }
      })();
    }, []); 
    if (isLoading) {
      return <p>Đang tải dữ liệu...</p>;
    }
    else {

  
  
  return (    
    <div className="services">
          <Tabs>
            <TabList>
              <Tab >Tổng quan</Tab>
              <Tab >Hiệu suất</Tab>
              <Tab >Nhà phân tích</Tab>
              <Tab>Cổ tức</Tab>
              <Tab>Tài chính</Tab>
            </TabList>
            <TabPanel>
                <StockGeneral data={data} />
            </TabPanel>
            <TabPanel>
              <StockPerformance data={data}/>
            </TabPanel>
            <TabPanel>
              <StockAnalysis data={data}/>
            </TabPanel>
            <TabPanel>
              <StockDividend data={data}/>
            </TabPanel>
            <TabPanel>
              <StockFinancial data={data}/>
            </TabPanel>
        </Tabs>
      </div>    
   );
 };
}

export const StockScreener = () => {
  const [screenedStocks, setScreenedStocks] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [criteria, setCriteria] = useState({
    exchange: 'ALL',
    min_price: '',
    max_price: '',
    min_volume: '',
    limit: 50
  });
  // eslint-disable-next-line no-unused-vars -- criteria are loaded once and consulted via setter callbacks in dependent paths
  const [availableCriteria, setAvailableCriteria] = useState(null);

  useEffect(() => {
    fetchAvailableCriteria();
    fetchDefaultScreenedStocks();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchAvailableCriteria = async () => {
    try {
      const result = await httpClient.get(API_ENDPOINTS.ANALYSIS_SCREENER_CONFIGS);
      if (result.success && result.data) {
        setAvailableCriteria(result.data.criteria);
        setError(null);
      }
    } catch (error) {
      console.error('Error fetching screening criteria:', error);
      setError('Failed to load screening criteria. Please try again later.');
    }
  };

  const fetchDefaultScreenedStocks = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await httpClient.get(API_ENDPOINTS.ANALYSIS_SCREENER);

      if (result.success) {
        // Parse response if it's a string
        let parsedData = result.data;
        if (typeof result.data === 'string') {
          parsedData = JSON.parse(result.data);
        }

        // Validate and clean the data - API returns 'stocks' array
        const data = parsedData.stocks || parsedData.data || parsedData || [];

        const cleanedData = data.map(stock => ({
          ...stock,
          symbol: stock.symbol || stock.ticker,
          name: stock.name || stock.companyName || stock.company,
          price: validateNumber(stock.price || stock.close || stock.price_near_realtime),
          volume: validateNumber(stock.volume || stock.total_trading_value),
          marketCap: validateNumber(stock.marketCap || stock.market_cap),
          change: validateNumber(stock.change || stock.change_percent || stock.prev_1d_growth_pct)
        }));

        setScreenedStocks(cleanedData);
        setError(null);
      } else {
        throw new Error(result.error?.message || 'Failed to fetch data');
      }
    } catch (error) {
      console.error('Error fetching default screened stocks:', error);
      setScreenedStocks([]);
      setError('Failed to fetch stock data. The server encountered an error processing the data.');
    } finally {
      setIsLoading(false);
    }
  };

  // Helper function to validate and clean numeric values
  const validateNumber = (value) => {
    if (value === null || value === undefined || value === '') {
      return null;
    }
    const num = parseFloat(value);
    if (isNaN(num) || !isFinite(num)) {
      return null;
    }
    return num;
  };

  const handleCriteriaChange = (field, value) => {
    setCriteria(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleScreenStocks = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // Build filters array in the format expected by backend ScreenerRequest
      const filters = [];

      // Exchange filter
      if (criteria.exchange && criteria.exchange !== 'ALL') {
        filters.push({
          field: 'exchange',
          operator: 'eq',
          value: criteria.exchange
        });
      }

      // Min price filter
      if (criteria.min_price && criteria.min_price !== '') {
        filters.push({
          field: 'price',
          operator: 'gte',
          value: parseFloat(criteria.min_price)
        });
      }

      // Max price filter
      if (criteria.max_price && criteria.max_price !== '') {
        filters.push({
          field: 'price',
          operator: 'lte',
          value: parseFloat(criteria.max_price)
        });
      }

      // Min volume filter
      if (criteria.min_volume && criteria.min_volume !== '') {
        filters.push({
          field: 'volume',
          operator: 'gte',
          value: parseInt(criteria.min_volume)
        });
      }

      const payload = {
        filters: filters,
        sort_by: 'symbol',
        sort_order: 'asc',
        limit: parseInt(criteria.limit) || 50,
        offset: 0
      };

      const result = await httpClient.post(API_ENDPOINTS.ANALYSIS_SCREENER, payload);

      if (result.success) {
        // Parse response if it's a string
        let parsedData = result.data;
        if (typeof result.data === 'string') {
          parsedData = JSON.parse(result.data);
        }

        // Validate and clean the data - API returns 'stocks' array
        const data = parsedData.stocks || parsedData.data || parsedData || [];

        const cleanedData = data.map(stock => ({
          ...stock,
          symbol: stock.symbol || stock.ticker,
          name: stock.name || stock.companyName || stock.company,
          price: validateNumber(stock.price || stock.close || stock.price_near_realtime),
          volume: validateNumber(stock.volume || stock.total_trading_value),
          marketCap: validateNumber(stock.marketCap || stock.market_cap),
          change: validateNumber(stock.change || stock.change_percent || stock.prev_1d_growth_pct)
        }));

        setScreenedStocks(cleanedData);
        setError(null);
      } else {
        throw new Error(result.error?.message || 'Failed to screen stocks');
      }
    } catch (error) {
      console.error('Error screening stocks:', error);
      setScreenedStocks([]);
      const errorMessage = error.message || 'Failed to screen stocks. The server encountered an error processing the data.';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return <div className="loading">Đang tải cổ phiếu được lọc...</div>;
  }

  return (
    <div className="stock-screener">
      <h2>Lọc cổ phiếu</h2>

      {/* Error Display */}
      {error && (
        <div className="error-message" style={{
          backgroundColor: '#fee',
          color: '#c00',
          padding: '10px',
          marginBottom: '20px',
          borderRadius: '5px',
          border: '1px solid #fcc'
        }}>
          {error}
        </div>
      )}

      {/* Screening Criteria Form */}
      <div className="screening-form screener-form-professional">
        <div className="criteria-row criteria-single-row">
          <div className="criteria-item">
            <label>Sàn giao dịch</label>
            <select
              value={criteria.exchange}
              onChange={(e) => handleCriteriaChange('exchange', e.target.value)}
            >
              <option value="ALL">Tất cả</option>
              <option value="HOSE">HOSE</option>
              <option value="HNX">HNX</option>
              <option value="UPCOM">UPCOM</option>
            </select>
          </div>

          <div className="criteria-item">
            <label>Giá tối thiểu</label>
            <input
              type="number"
              value={criteria.min_price}
              onChange={(e) => handleCriteriaChange('min_price', e.target.value)}
              placeholder="0"
            />
          </div>

          <div className="criteria-item">
            <label>Giá tối đa</label>
            <input
              type="number"
              value={criteria.max_price}
              onChange={(e) => handleCriteriaChange('max_price', e.target.value)}
              placeholder="∞"
            />
          </div>

          <div className="criteria-item">
            <label>KL tối thiểu</label>
            <input
              type="number"
              value={criteria.min_volume}
              onChange={(e) => handleCriteriaChange('min_volume', e.target.value)}
              placeholder="0"
            />
          </div>

          <div className="criteria-item">
            <label>Giới hạn</label>
            <input
              type="number"
              value={criteria.limit}
              onChange={(e) => handleCriteriaChange('limit', e.target.value)}
              placeholder="50"
            />
          </div>

          <div className="criteria-item criteria-button-item">
            <button onClick={handleScreenStocks} className="screen-button">
              🔍 Lọc
            </button>
          </div>
        </div>
      </div>

      {/* Results Table */}
      {screenedStocks.length > 0 ? (
        <div className="screened-results">
          <div className="results-header">
            <h3>📊 Kết quả lọc</h3>
            <span className="results-count">{screenedStocks.length} cổ phiếu được tìm thấy</span>
          </div>
          <table className="stocks-table screener-table">
            <thead>
              <tr>
                <th className="th-symbol">Mã CP</th>
                <th className="th-name">Tên</th>
                <th className="th-exchange">Sàn</th>
                <th className="th-price">Giá</th>
                <th className="th-volume">Khối lượng</th>
                <th className="th-change">Thay đổi %</th>
              </tr>
            </thead>
            <tbody>
              {screenedStocks.map((stock, index) => (
                <tr key={index} className={index % 2 === 0 ? 'row-even' : 'row-odd'}>
                  <td className="td-symbol">{stock.symbol || 'N/A'}</td>
                  <td className="td-name">{stock.name || stock.companyName || 'N/A'}</td>
                  <td className="td-exchange">
                    <span className={`exchange-badge exchange-${(stock.exchange || '').toLowerCase()}`}>
                      {stock.exchange || 'N/A'}
                    </span>
                  </td>
                  <td className="td-price">{stock.price !== null && stock.price !== undefined ? stock.price.toLocaleString() : 'N/A'}</td>
                  <td className="td-volume">{stock.volume !== null && stock.volume !== undefined ? stock.volume.toLocaleString() : 'N/A'}</td>
                  <td className={`td-change ${stock.change !== null && stock.change >= 0 ? 'positive' : stock.change !== null && stock.change < 0 ? 'negative' : ''}`}>
                    {stock.change !== null && stock.change !== undefined
                      ? <span className="change-value">{stock.change >= 0 ? '▲' : '▼'} {Math.abs(stock.change).toFixed(2)}%</span>
                      : 'N/A'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="no-results">
          <p>Không tìm thấy cổ phiếu phù hợp với tiêu chí.</p>
        </div>
      )}
    </div>
  );
};

export const StocksByIndustry = () => {
  const navigate = useNavigate();
  const [industries, setIndustries] = useState([]);
  const [selectedIndustry, setSelectedIndustry] = useState('');
  const [stocksByIndustry, setStocksByIndustry] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);

  useEffect(() => {
    fetchIndustries();
  }, []);

  const fetchIndustries = async () => {
    try {
      const result = await httpClient.get(API_ENDPOINTS.INDUSTRIES_LIST);

      if (result.success) {
        // Parse response if it's a string
        let parsedData = result.data;
        if (typeof result.data === 'string') {
          parsedData = JSON.parse(result.data);
        }

        setIndustries(parsedData.data || parsedData || []);
      }
    } catch (error) {
      console.error('Error fetching industries:', error);
      setIndustries([]);
    }
  };

  const fetchStocksByIndustry = async (industryCode, page = 1) => {
    if (!industryCode) return;

    setIsLoading(true);
    try {
      const result = await httpClient.get(
        `${API_ENDPOINTS.INDUSTRY_COMPANIES(industryCode)}?page=${page}&page_size=20`
      );

      if (result.success) {
        // Parse response if it's a string
        let parsedData = result.data;
        if (typeof result.data === 'string') {
          parsedData = JSON.parse(result.data);
        }

        // Map field names similar to StockScreener
        const data = parsedData.items || parsedData.data || parsedData || [];

        // Helper function to validate and clean numeric values
        const validateNumber = (value) => {
          if (value === null || value === undefined || value === '') {
            return null;
          }
          const num = parseFloat(value);
          if (isNaN(num) || !isFinite(num)) {
            return null;
          }
          return num;
        };

        const cleanedData = data.map(stock => ({
          ...stock,
          symbol: stock.symbol || stock.Symbol || stock.ticker,
          name: stock.name || stock.organ_name || stock.Company || stock.companyName,
          price: validateNumber(stock.price || stock.Price || stock.close || stock.price_near_realtime),
          marketCap: validateNumber(stock.marketCap || stock.MarketCap || stock.market_cap),
          change: validateNumber(stock.change || stock['Change%'] || stock.change_percent || stock.prev_1d_growth_pct),
          pe: validateNumber(stock.pe || stock['P/E']),
          volume: validateNumber(stock.volume || stock.total_trading_value)
        }));

        setStocksByIndustry(cleanedData);
        setTotalPages(parsedData.total_pages || 0);
        setCurrentPage(page);
      }
    } catch (error) {
      console.error('Error fetching stocks by industry:', error);
      setStocksByIndustry([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleIndustryChange = (industryCode) => {
    setSelectedIndustry(industryCode);
    setCurrentPage(1);
    fetchStocksByIndustry(industryCode, 1);
  };

  const handlePageChange = (page) => {
    fetchStocksByIndustry(selectedIndustry, page);
  };

  if (isLoading) {
    return <div className="loading">Đang tải cổ phiếu theo ngành...</div>;
  }

  return (
    <div className="stocks-by-industry stocks-by-industry-professional">
      <h2>🏭 Cổ phiếu theo ngành</h2>

      {/* Industry Selection */}
      <div className="industry-selection industry-selection-professional">
        <div className="industry-selector-wrapper">
          <label>Chọn ngành</label>
          <select
            value={selectedIndustry}
            onChange={(e) => handleIndustryChange(e.target.value)}
            className="industry-select"
          >
            <option value="">Chọn một ngành...</option>
            {industries.map((industry, index) => (
              <option key={index} value={industry.code || industry.icb_code || index}>
                {industry.name_en || industry.en_icb_name || industry.name || industry.icb_name || `Industry ${index + 1}`}
              </option>
            ))}
          </select>
        </div>
        {selectedIndustry && (
          <div className="industry-stats">
            <span className="stat-badge stat-badge-primary">
              📊 {stocksByIndustry.length} cổ phiếu
            </span>
          </div>
        )}
      </div>

      {/* Stocks List */}
      {selectedIndustry && stocksByIndustry.length > 0 ? (
        <div className="stocks-list">
          <div className="results-header">
            <h3>📋 Cổ phiếu ngành</h3>
            <span className="results-count">{stocksByIndustry.length} công ty</span>
          </div>
          <table className="stocks-table industry-table">
            <thead>
              <tr>
                <th className="th-industry-symbol">Mã CP</th>
                <th className="th-industry-name">Tên công ty</th>
                <th className="th-industry-l2">Cấp 2</th>
                <th className="th-industry-l3">Cấp 3</th>
                <th className="th-industry-l4">Cấp 4</th>
                <th className="th-industry-type">Loại</th>
              </tr>
            </thead>
            <tbody>
              {stocksByIndustry.map((stock, index) => (
                <tr key={index} className={index % 2 === 0 ? 'row-even' : 'row-odd'}>
                  <td className="td-symbol">
                    <span
                      className="symbol-link"
                      onClick={() => navigate('/company/' + stock.symbol)}
                    >
                      {stock.symbol || 'N/A'}
                    </span>
                  </td>
                  <td className="td-company-name">{stock.name || stock.organ_name || 'N/A'}</td>
                  <td className="td-industry-level">
                    <span className="industry-tag industry-l2">{stock.icb_name2 || 'N/A'}</span>
                  </td>
                  <td className="td-industry-level">
                    <span className="industry-tag industry-l3">{stock.icb_name3 || 'N/A'}</span>
                  </td>
                  <td className="td-industry-level">
                    <span className="industry-tag industry-l4">{stock.icb_name4 || 'N/A'}</span>
                  </td>
                  <td className="td-type">
                    <span className={`type-badge type-${(stock.com_type_code || '').toLowerCase()}`}>
                      {stock.com_type_code || 'N/A'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="pagination pagination-professional">
              <button
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
                className="page-button"
              >
                ← Trước
              </button>

              <span className="page-info">
                Trang <strong>{currentPage}</strong> / <strong>{totalPages}</strong>
              </span>

              <button
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
                className="page-button"
              >
                Tiếp →
              </button>
            </div>
          )}
        </div>
      ) : selectedIndustry ? (
        <div className="no-results no-results-styled">
          <span className="no-results-icon">🔍</span>
          <p>Không tìm thấy cổ phiếu trong ngành được chọn.</p>
        </div>
      ) : (
        <div className="select-industry select-industry-styled">
          <span className="select-icon">🏢</span>
          <p>Vui lòng chọn một ngành để xem cổ phiếu.</p>
        </div>
      )}
    </div>
  );
};

export const StockList = () => {
  const navigate = useNavigate();
  const [stocks, setStocks] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [filters, setFilters] = useState({
    exchange: '',
    search: '',
    sort_by: 'symbol',
    sort_order: 'asc'
  });
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [totalStocks, setTotalStocks] = useState(0);
  const [selectedStock, setSelectedStock] = useState(null);
  const [showDetails, setShowDetails] = useState(false);

  // Helper function to validate and clean numeric values
  const validateNumber = (value) => {
    if (value === null || value === undefined || value === '') {
      return null;
    }
    const num = parseFloat(value);
    if (isNaN(num) || !isFinite(num)) {
      return null;
    }
    return num;
  };

  useEffect(() => {
    fetchStocks(1);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchStocks = async (page = 1) => {
    setIsLoading(true);
    try {
      // Build query params
      let queryParams = `?page=${page}&page_size=25`;
      if (filters.exchange) queryParams += `&exchange=${filters.exchange}`;
      if (filters.search) queryParams += `&search=${filters.search}`;
      if (filters.sort_by) queryParams += `&sort_by=${filters.sort_by}`;
      if (filters.sort_order) queryParams += `&sort_order=${filters.sort_order}`;

      const result = await httpClient.get(`${API_ENDPOINTS.COMPANIES_LIST}${queryParams}`);

      if (result.success) {
        // Parse and clean the data
        const responseData = result.data;
        const data = responseData.items || responseData.data || responseData || [];

        // Debug: Log the first item to see actual structure
        if (data.length > 0) {
          console.log('Sample stock data:', data[0]);
        }

        const cleanedData = data.map(stock => ({
          ...stock,
          symbol: stock.symbol || stock.ticker,
          name: stock.name || stock.organ_name || stock.organ_short_name || stock.shortName || stock.companyName || stock.company,
          exchange: stock.exchange || stock.exchange_name || stock.Exchange,
          close: validateNumber(stock.price || stock.close || stock.price_near_realtime),
          volume: validateNumber(stock.volume || stock.total_trading_value)
        }));

        setStocks(cleanedData);
        setTotalPages(responseData.total_pages || 0);
        setTotalStocks(responseData.total || 0);
        setCurrentPage(page);
      }
    } catch (error) {
      console.error('Error fetching stocks:', error);
      setStocks([]);
    } finally {
      setIsLoading(false);
    }
  };

  // eslint-disable-next-line no-unused-vars -- preserved for upcoming detail-modal wiring
  const fetchStockDetails = async (symbol) => {
    try {
      const result = await httpClient.get(API_ENDPOINTS.STOCK_DETAIL(symbol));
      if (result.success && result.data) {
        setSelectedStock(result.data);
        setShowDetails(true);
      }
    } catch (error) {
      console.error('Error fetching stock details:', error);
      setSelectedStock(null);
    }
  };

  const handleFilterChange = (field, value) => {
    setFilters(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleSearch = () => {
    setCurrentPage(1);
    fetchStocks(1);
  };

  const handlePageChange = (page) => {
    fetchStocks(page);
  };

  const handleSort = (sortBy) => {
    const newSortOrder = filters.sort_by === sortBy && filters.sort_order === 'asc' ? 'desc' : 'asc';
    setFilters(prev => ({
      ...prev,
      sort_by: sortBy,
      sort_order: newSortOrder
    }));
    setCurrentPage(1);
    setTimeout(() => fetchStocks(1), 100);
  };

  const getSortIcon = (column) => {
    if (filters.sort_by !== column) return '↕️';
    return filters.sort_order === 'asc' ? '↑' : '↓';
  };

  if (isLoading) {
    return <div className="loading">Đang tải danh sách cổ phiếu...</div>;
  }

  return (
    <div className="stock-list stock-list-professional">
      <h2>📋 Danh sách cổ phiếu</h2>

      {/* Filters and Search */}
      <div className="filters-section filters-section-professional">
        <div className="filter-row filter-row-single">
          <div className="filter-item">
            <label>Sàn giao dịch</label>
            <select
              value={filters.exchange}
              onChange={(e) => handleFilterChange('exchange', e.target.value)}
            >
              <option value="">Tất cả</option>
              <option value="HOSE">HOSE</option>
              <option value="HNX">HNX</option>
              <option value="UPCOM">UPCOM</option>
            </select>
          </div>

          <div className="filter-item filter-item-search">
            <label>Tìm kiếm</label>
            <input
              type="text"
              value={filters.search}
              onChange={(e) => handleFilterChange('search', e.target.value)}
              placeholder="🔍 Tìm theo mã hoặc tên..."
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            />
          </div>

          <div className="filter-item filter-button-item">
            <button onClick={handleSearch} className="search-button">
              🔍 Tìm kiếm
            </button>
          </div>
        </div>
      </div>

      {/* Results Summary */}
      <div className="results-summary results-summary-professional">
        <div className="summary-left">
          <span className="summary-icon">📊</span>
          <span className="summary-text">Tìm thấy <strong>{totalStocks}</strong> cổ phiếu</span>
        </div>
        <div className="summary-right">
          <span className="page-indicator">Trang {currentPage} / {totalPages}</span>
        </div>
      </div>

      {/* Stock Details Modal */}
      {showDetails && selectedStock && (
        <div className="stock-details-modal">
          <div className="modal-content">
            <div className="modal-header">
              <h3>{selectedStock.symbol} - Chi tiết cổ phiếu</h3>
              <button
                onClick={() => setShowDetails(false)}
                className="close-button"
              >
                ×
              </button>
            </div>
            <div className="modal-body">
              {selectedStock.overview && (
                <div className="details-section">
                  <h4>Tổng quan công ty</h4>
                  <p><strong>Tên:</strong> {selectedStock.overview.companyName || 'N/A'}</p>
                  <p><strong>Ngành:</strong> {selectedStock.overview.industry || 'N/A'}</p>
                  <p><strong>Sàn:</strong> {selectedStock.overview.exchange || 'N/A'}</p>
                </div>
              )}

              {selectedStock.latest_price && (
                <div className="details-section">
                  <h4>Giá mới nhất</h4>
                  <p><strong>Giá hiện tại:</strong> {selectedStock.latest_price.current_price || 'N/A'}</p>
                  <p><strong>Mở cửa:</strong> {selectedStock.latest_price.open_price || 'N/A'}</p>
                  <p><strong>Cao nhất:</strong> {selectedStock.latest_price.high_price || 'N/A'}</p>
                  <p><strong>Thấp nhất:</strong> {selectedStock.latest_price.low_price || 'N/A'}</p>
                  <p><strong>Khối lượng:</strong> {selectedStock.latest_price.volume?.toLocaleString() || 'N/A'}</p>
                </div>
              )}

              {selectedStock.technical_indicators && (
                <div className="details-section">
                  <h4>Chỉ báo kỹ thuật</h4>
                  <p><strong>RSI:</strong> {selectedStock.technical_indicators.rsi?.toFixed(2) || 'N/A'}</p>
                  <p><strong>SMA 20:</strong> {selectedStock.technical_indicators.sma_20?.toFixed(2) || 'N/A'}</p>
                  <p><strong>SMA 50:</strong> {selectedStock.technical_indicators.sma_50?.toFixed(2) || 'N/A'}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Stocks Table */}
      {stocks.length > 0 ? (
        <div className="stocks-table-container">
          <table className="stocks-table stocklist-table">
            <thead>
              <tr>
                <th className="th-list-symbol sortable" onClick={() => handleSort('symbol')}>
                  Mã CP {getSortIcon('symbol')}
                </th>
                <th className="th-list-name sortable" onClick={() => handleSort('name')}>
                  Tên {getSortIcon('name')}
                </th>
                <th className="th-list-exchange sortable" onClick={() => handleSort('exchange')}>
                  Sàn {getSortIcon('exchange')}
                </th>
                <th className="th-list-price sortable" onClick={() => handleSort('close')}>
                  Giá {getSortIcon('close')}
                </th>
                <th className="th-list-volume sortable" onClick={() => handleSort('volume')}>
                  Khối lượng {getSortIcon('volume')}
                </th>
              </tr>
            </thead>
            <tbody>
              {stocks.map((stock, index) => (
                <tr key={index} className={index % 2 === 0 ? 'row-even' : 'row-odd'}>
                  <td className="td-symbol">
                    <span
                      className="symbol-link"
                      onClick={() => navigate('/company/' + stock.symbol)}
                    >
                      {stock.symbol || 'N/A'}
                    </span>
                  </td>
                  <td className="td-company-name">{stock.name || 'N/A'}</td>
                  <td className="td-exchange">
                    <span className={`exchange-badge exchange-${(stock.exchange || '').toLowerCase()}`}>
                      {stock.exchange || 'N/A'}
                    </span>
                  </td>
                  <td className="td-price">{stock.close !== null && stock.close !== undefined ? stock.close.toLocaleString() : 'N/A'}</td>
                  <td className="td-volume">{stock.volume !== null && stock.volume !== undefined ? stock.volume.toLocaleString() : 'N/A'}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="pagination pagination-professional">
              <button
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
                className="page-button"
              >
                ← Trước
              </button>

              <span className="page-info">
                Trang <strong>{currentPage}</strong> / <strong>{totalPages}</strong>
              </span>

              <button
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
                className="page-button"
              >
                Tiếp →
              </button>
            </div>
          )}
        </div>
      ) : (
        <div className="no-results no-results-styled">
          <span className="no-results-icon">🔍</span>
          <p>Không tìm thấy cổ phiếu với bộ lọc hiện tại.</p>
        </div>
      )}
    </div>
  );
};
