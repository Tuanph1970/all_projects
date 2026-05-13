/**
 * ChatbotAgent Component
 * Intelligent stock market chatbot with LLM-based agent routing
 */

import React, { useState, useEffect, useRef } from 'react';
import chatbotAgentService from '../../services/chatbotAgentService';
import '../../styles/chatbot-agent.css';

const ChatbotAgent = () => {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const messagesEndRef = useRef(null);

  // Sample questions for each category — preserved for the in-progress
  // suggested-prompts panel.
  // eslint-disable-next-line no-unused-vars
  const sampleQuestions = {
    'market_overview': [
      'What is the current VN-Index level?',
      'How did the VN-Index perform today?',
      "What's the trading volume on HOSE today?",
      'Is the Vietnamese stock market volatile?'
    ],
    'stock_performance': [
      "What's the current price of VCB stock?",
      'Which stocks are gaining the most today?',
      'Show me the top 10 stocks by trading volume',
      'What stocks hit ceiling price today?'
    ],
    'sector_analysis': [
      'Which sectors are leading the market today?',
      'How is the banking sector performing?',
      "What's happening with real estate stocks?",
      'Are tech stocks rising or falling?'
    ],
    'market_trends': [
      'Is the market in an uptrend or downtrend?',
      "What's the market breadth today?",
      'Are foreign investors buying or selling?',
      'Is there a bullish or bearish sentiment?'
    ],
    'technical_indicators': [
      'What is the RSI for VCB?',
      'Show me the MACD for VNINDEX',
      'Calculate 20-day moving average for HPG',
      'What are the technical indicators for VHM?'
    ],
    'predictions': [
      'Will the market go up or down tomorrow?',
      "What's the outlook for VN-Index this week?",
      'Predict the price of VCB for next month',
      'Is now a good time to invest?'
    ]
  };

  useEffect(() => {
    // Load categories on mount
    loadCategories();
    // Add welcome message
    setMessages([
      {
        id: Date.now(),
        type: 'bot',
        content: 'Xin chào! Tôi là trợ lý thị trường chứng khoán thông minh của bạn. Hãy hỏi tôi bất cứ điều gì về thị trường chứng khoán Việt Nam, cổ phiếu riêng lẻ, ngành, xu hướng hoặc dự đoán!',
        category: 'system',
        timestamp: new Date()
      }
    ]);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadCategories = async () => {
    try {
      const data = await chatbotAgentService.getQuestionCategories();
      setCategories(data.categories || []);
    } catch (error) {
      console.error('Error loading categories:', error);
    }
  };

  const handleSendMessage = async (questionText = null) => {
    const question = questionText || inputValue.trim();

    if (!question) return;

    // Add user message
    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: question,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);
    setShowSuggestions(false);

    try {
      // Send question to agent backend
      const response = await chatbotAgentService.askQuestion(question);

      // Add bot response
      const botMessage = {
        id: Date.now() + 1,
        type: 'bot',
        content: formatResponse(response),
        rawData: response.data,
        category: response.category,
        confidence: response.confidence,
        sources: response.sources,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      console.error('ChatbotAgent error:', error);

      // Extract error message
      let errorText = 'Xin lỗi, đã xảy ra lỗi khi xử lý câu hỏi của bạn. Vui lòng thử lại.';
      if (error?.message) {
        errorText = `Error: ${error.message}`;
      } else if (typeof error === 'string') {
        errorText = `Error: ${error}`;
      }

      // Add error message
      const errorMessage = {
        id: Date.now() + 1,
        type: 'bot',
        content: errorText,
        error: true,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const formatResponse = (response) => {
    if (!response.success) {
      return response.message || 'Không thể xử lý câu hỏi của bạn.';
    }

    const { data, message, category } = response;

    // Format response based on category
    switch (category) {
      case 'market_overview':
        return formatMarketOverview(data, message);
      case 'stock_performance':
        return formatStockPerformance(data, message);
      case 'sector_analysis':
        return formatSectorAnalysis(data, message);
      case 'market_trends':
        return formatMarketTrends(data, message);
      case 'technical_indicators':
        return formatTechnicalIndicators(data, message);
      case 'predictions':
        return formatPredictions(data, message);
      default:
        return message || JSON.stringify(data, null, 2);
    }
  };

  const formatMarketOverview = (data, message) => {
    if (!data) return message;

    if (data.index) {
      return `**Tổng quan ${data.index}**\n\n` +
        `Mức hiện tại: ${data.level || data.current_level || 'N/A'}\n` +
        `Thay đổi: ${data.change >= 0 ? '+' : ''}${data.change || 'N/A'} (${data.change_percent >= 0 ? '+' : ''}${data.change_percent || 'N/A'}%)\n` +
        (data.volume ? `Khối lượng: ${formatNumber(data.volume)} cổ phiếu\n` : '') +
        (data.gainers ? `Tăng: ${data.gainers} | Giảm: ${data.losers} | Không đổi: ${data.unchanged}\n` : '');
    }
    return message;
  };

  const formatStockPerformance = (data, message) => {
    if (!data) return message;

    if (Array.isArray(data)) {
      // Format list of stocks
      return data.map(stock =>
        `${stock.ticker}: ${stock.price || 'N/A'} (${stock.change_percent >= 0 ? '+' : ''}${stock.change_percent || 'N/A'}%)`
      ).join('\n');
    } else if (data.ticker) {
      // Format single stock
      return `**${data.ticker}**\n\n` +
        `Giá: ${data.price || 'N/A'} VND\n` +
        `Thay đổi: ${data.change >= 0 ? '+' : ''}${data.change || 'N/A'} (${data.change_percent >= 0 ? '+' : ''}${data.change_percent || 'N/A'}%)\n` +
        (data.volume ? `Khối lượng: ${formatNumber(data.volume)} cổ phiếu\n` : '') +
        (data.market_cap ? `Vốn hóa: ${formatNumber(data.market_cap)} VND\n` : '');
    }
    return message;
  };

  const formatSectorAnalysis = (data, message) => {
    if (!data) return message;

    if (Array.isArray(data)) {
      return data.map(sector =>
        `${sector.sector}: ${sector.change_percent >= 0 ? '+' : ''}${sector.change_percent}%`
      ).join('\n');
    } else if (data.sector) {
      return `**Ngành ${data.sector}**\n\n` +
        `Hiệu suất: ${data.change_percent >= 0 ? '+' : ''}${data.change_percent}%\n` +
        (data.top_stocks ? `Cổ phiếu hàng đầu:\n${data.top_stocks.map(s => `  - ${s.ticker}: ${s.change_percent >= 0 ? '+' : ''}${s.change_percent}%`).join('\n')}` : '');
    }
    return message;
  };

  const formatMarketTrends = (data, message) => {
    if (!data) return message;

    let formatted = '';
    if (data.trend) {
      formatted += `**Xu hướng thị trường: ${data.trend.trend || data.trend}**\n\n`;
      if (data.trend.strength) formatted += `Độ mạnh: ${data.trend.strength}\n`;
      if (data.trend.support_level) formatted += `Hỗ trợ: ${data.trend.support_level}\n`;
      if (data.trend.resistance_level) formatted += `Kháng cự: ${data.trend.resistance_level}\n`;
    }
    if (data.breadth) {
      formatted += `\nĐộ rộng thị trường:\n`;
      formatted += `Tăng: ${data.breadth.gainers} | Giảm: ${data.breadth.losers}\n`;
      formatted += `Tỷ lệ độ rộng: ${data.breadth.breadth_ratio}\n`;
    }
    if (data.sentiment) {
      formatted += `\nTâm lý: ${data.sentiment.sentiment} (độ tin cậy ${Math.round(data.sentiment.confidence * 100)}%)\n`;
    }
    return formatted || message;
  };

  const formatTechnicalIndicators = (data, message) => {
    if (!data) return message;

    if (Array.isArray(data)) {
      // Last value from time series
      const latest = data[data.length - 1];
      return JSON.stringify(latest, null, 2);
    } else if (data.ticker) {
      let formatted = `**Chỉ báo kỹ thuật cho ${data.ticker}**\n\n`;
      if (data.rsi) formatted += `RSI: ${JSON.stringify(data.rsi)}\n`;
      if (data.macd) formatted += `MACD: ${JSON.stringify(data.macd)}\n`;
      if (data.sma_20) formatted += `SMA(20): ${JSON.stringify(data.sma_20)}\n`;
      return formatted;
    }
    return message;
  };

  const formatPredictions = (data, message) => {
    if (!data) return message;

    const directionEmoji = data.direction === 'up' ? '📈' : '📉';
    let formatted = `**Dự đoán cổ phiếu ${data.ticker}** ${directionEmoji}\n\n`;

    // Current status
    formatted += `**Trạng thái hiện tại**:\n`;
    formatted += `• Giá: ${formatNumber(data.current_price)} VND\n`;
    formatted += `• Ngày: ${data.date}\n\n`;

    // Forecast
    formatted += `**Dự báo ${data.horizon}**:\n`;
    formatted += `• Dự đoán: ${formatNumber(data.predicted_price)} VND\n`;
    formatted += `• Thay đổi: ${data.change_percent >= 0 ? '+' : ''}${data.change_percent.toFixed(2)}% `;
    formatted += `(${data.change_amount >= 0 ? '+' : ''}${formatNumber(data.change_amount)} VND)\n`;
    formatted += `• Hướng: ${data.direction === 'up' ? 'TĂNG' : 'GIẢM'} (xác suất ${Math.round(data.probability * 100)}%)\n`;
    formatted += `• Phạm vi 95%: ${formatNumber(data.confidence_interval.lower)} - ${formatNumber(data.confidence_interval.upper)} VND\n\n`;

    // Technical signals
    if (data.technical_signals && data.technical_signals.length > 0) {
      formatted += `**Tín hiệu kỹ thuật**:\n`;
      data.technical_signals.forEach(signal => {
        formatted += `• ${signal}\n`;
      });
      formatted += `\n`;
    }

    // Confidence
    formatted += `**Độ tin cậy**: ${Math.round((data.confidence || 0.5) * 100)}%\n\n`;

    // Current indicators
    if (data.current_indicators) {
      const ind = data.current_indicators;
      formatted += `**Chỉ báo hiện tại**:\n`;
      formatted += `• RSI: ${ind.rsi.toFixed(1)}\n`;
      formatted += `• MACD: ${ind.macd.toFixed(2)}\n`;
      formatted += `• Khối lượng: ${ind.relative_volume.toFixed(2)}x trung bình\n`;
      formatted += `• Xu hướng: ${ind.trend_strength > 0 ? 'Tăng ↗' : 'Giảm ↘'}\n\n`;
    }

    // Disclaimer
    formatted += `⚠️ ${data.disclaimer || 'Phân tích AI chỉ mang tính chất tham khảo. Không phải lời khuyên đầu tư.'}`;

    return formatted;
  };

  const formatNumber = (num) => {
    if (!num) return 'N/A';
    return num.toLocaleString('vi-VN');
  };

  const handleSuggestionClick = (question) => {
    setInputValue(question);
    handleSendMessage(question);
  };

  const handleCategorySelect = (category) => {
    setSelectedCategory(category);
    setShowSuggestions(true);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="chatbot-agent-container">
      <div className="chatbot-header">
        <h2>🤖 Trợ lý AI Thị trường Chứng khoán</h2>
        <p>Được hỗ trợ bởi hệ thống AI</p>
      </div>

      {/* Category Pills */}
      <div className="category-pills">
        {categories.map((cat, idx) => (
          <button
            key={idx}
            className={`category-pill ${selectedCategory?.name === cat.name ? 'active' : ''}`}
            onClick={() => handleCategorySelect(cat)}
            title={cat.description}
          >
            {cat.name.replace('_', ' ').toUpperCase()}
          </button>
        ))}
      </div>

      {/* Sample Questions */}
      {showSuggestions && selectedCategory && (
        <div className="suggestions-panel">
          <h4>Câu hỏi mẫu cho {selectedCategory.name.replace('_', ' ')}:</h4>
          <div className="suggestions-list">
            {(selectedCategory.examples || []).map((question, idx) => (
              <button
                key={idx}
                className="suggestion-btn"
                onClick={() => handleSuggestionClick(question)}
              >
                {question}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="messages-container">
        {messages.map((msg) => (
          <div key={msg.id} className={`message ${msg.type}-message ${msg.error ? 'error' : ''}`}>
            <div className="message-header">
              <span className="message-sender">
                {msg.type === 'user' ? '👤 Bạn' : '🤖 Trợ lý AI'}
              </span>
              <span className="message-time">
                {msg.timestamp.toLocaleTimeString()}
              </span>
            </div>
            <div className="message-content">
              {msg.content.split('\n').map((line, idx) => (
                <p key={idx}>
                  {line.startsWith('**') && line.endsWith('**') ? (
                    <strong>{line.slice(2, -2)}</strong>
                  ) : (
                    line
                  )}
                </p>
              ))}
            </div>
            {msg.category && msg.category !== 'system' && (
              <div className="message-meta">
                <span className="message-category">Danh mục: {msg.category}</span>
                {msg.confidence && (
                  <span className="message-confidence">
                    Độ tin cậy: {Math.round(msg.confidence * 100)}%
                  </span>
                )}
                {msg.sources && msg.sources.length > 0 && (
                  <span className="message-sources">
                    Nguồn: {msg.sources.join(', ')}
                  </span>
                )}
              </div>
            )}
          </div>
        ))}
        {isLoading && (
          <div className="message bot-message loading">
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="input-container">
        <textarea
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Hỏi bất cứ điều gì về thị trường chứng khoán..."
          rows={2}
          disabled={isLoading}
        />
        <button
          onClick={() => handleSendMessage()}
          disabled={isLoading || !inputValue.trim()}
          className="send-btn"
        >
          {isLoading ? 'Đang xử lý...' : 'Gửi'}
        </button>
      </div>
    </div>
  );
};

export default ChatbotAgent;
