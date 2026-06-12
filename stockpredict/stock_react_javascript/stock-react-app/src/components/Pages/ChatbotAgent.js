/**
 * ChatbotAgent Component
 * Intelligent stock market chatbot with LLM-based agent routing
 */

import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import chatbotAgentService from '../../services/chatbotAgentService';
import '../../styles/chatbot-agent.css';

const ChatbotAgent = () => {
  const { t } = useTranslation();
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
        content: t('chatbot.welcome_message'),
        category: 'system',
        timestamp: new Date()
      }
    ]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
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
      let errorText = t('chatbot.error_processing');
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
      return response.message || t('chatbot.error_unprocessable');
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

  // Helper: format a signed number with leading +/- (returns "N/A" if missing)
  const fmtSigned = (v) => {
    if (v === null || v === undefined) return 'N/A';
    return (v >= 0 ? '+' : '') + v;
  };
  const fmtSignedFixed = (v, digits = 2) => {
    if (v === null || v === undefined) return 'N/A';
    return (v >= 0 ? '+' : '') + v.toFixed(digits);
  };

  const formatMarketOverview = (data, message) => {
    if (!data) return message;

    if (data.index) {
      let out = t('chatbot.tpl_overview_header', { index: data.index }) + '\n\n';
      out += t('chatbot.tpl_current_level', { level: data.level || data.current_level || 'N/A' }) + '\n';
      out += t('chatbot.tpl_change', {
        change: fmtSigned(data.change),
        percent: fmtSigned(data.change_percent),
      }) + '\n';
      if (data.volume) out += t('chatbot.tpl_volume', { count: formatNumber(data.volume) }) + '\n';
      if (data.gainers) {
        out += t('chatbot.tpl_gainers_losers', {
          gainers: data.gainers,
          losers: data.losers,
          unchanged: data.unchanged,
        }) + '\n';
      }
      return out;
    }
    return message;
  };

  const formatStockPerformance = (data, message) => {
    if (!data) return message;

    if (Array.isArray(data)) {
      // Format list of stocks
      return data.map(stock =>
        `${stock.ticker}: ${stock.price || 'N/A'} (${fmtSigned(stock.change_percent)}%)`
      ).join('\n');
    } else if (data.ticker) {
      let out = `**${data.ticker}**\n\n`;
      out += t('chatbot.tpl_stock_price', { price: data.price || 'N/A' }) + '\n';
      out += t('chatbot.tpl_change', {
        change: fmtSigned(data.change),
        percent: fmtSigned(data.change_percent),
      }) + '\n';
      if (data.volume) out += t('chatbot.tpl_volume', { count: formatNumber(data.volume) }) + '\n';
      if (data.market_cap) out += t('chatbot.tpl_market_cap', { value: formatNumber(data.market_cap) }) + '\n';
      return out;
    }
    return message;
  };

  const formatSectorAnalysis = (data, message) => {
    if (!data) return message;

    if (Array.isArray(data)) {
      return data.map(sector =>
        `${sector.sector}: ${fmtSigned(sector.change_percent)}%`
      ).join('\n');
    } else if (data.sector) {
      let out = t('chatbot.tpl_sector_header', { sector: data.sector }) + '\n\n';
      out += t('chatbot.tpl_sector_performance', { percent: fmtSigned(data.change_percent) }) + '\n';
      if (data.top_stocks) {
        out += t('chatbot.tpl_top_stocks') + '\n';
        out += data.top_stocks.map(s => `  - ${s.ticker}: ${fmtSigned(s.change_percent)}%`).join('\n');
      }
      return out;
    }
    return message;
  };

  const formatMarketTrends = (data, message) => {
    if (!data) return message;

    let formatted = '';
    if (data.trend) {
      formatted += t('chatbot.tpl_market_trend', { trend: data.trend.trend || data.trend }) + '\n\n';
      if (data.trend.strength) formatted += t('chatbot.tpl_trend_strength', { strength: data.trend.strength }) + '\n';
      if (data.trend.support_level) formatted += t('chatbot.tpl_support_level', { level: data.trend.support_level }) + '\n';
      if (data.trend.resistance_level) formatted += t('chatbot.tpl_resistance_level', { level: data.trend.resistance_level }) + '\n';
    }
    if (data.breadth) {
      formatted += '\n' + t('chatbot.tpl_market_breadth') + '\n';
      formatted += t('chatbot.tpl_breadth_gainers_losers', {
        gainers: data.breadth.gainers,
        losers: data.breadth.losers,
      }) + '\n';
      formatted += t('chatbot.tpl_breadth_ratio', { ratio: data.breadth.breadth_ratio }) + '\n';
    }
    if (data.sentiment) {
      formatted += '\n' + t('chatbot.tpl_sentiment', {
        sentiment: data.sentiment.sentiment,
        percent: Math.round(data.sentiment.confidence * 100),
      }) + '\n';
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
      let formatted = t('chatbot.tpl_technical_for', { ticker: data.ticker }) + '\n\n';
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
    let formatted = t('chatbot.tpl_prediction_header', { ticker: data.ticker, emoji: directionEmoji }) + '\n\n';

    // Current status
    formatted += t('chatbot.tpl_current_status') + '\n';
    formatted += t('chatbot.tpl_current_price_line', { price: formatNumber(data.current_price) }) + '\n';
    formatted += t('chatbot.tpl_current_date_line', { date: data.date }) + '\n\n';

    // Forecast
    formatted += t('chatbot.tpl_forecast_header', { horizon: data.horizon }) + '\n';
    formatted += t('chatbot.tpl_predicted_price_line', { price: formatNumber(data.predicted_price) }) + '\n';
    formatted += t('chatbot.tpl_change_line', {
      percent: fmtSignedFixed(data.change_percent),
      amount: fmtSigned(formatNumber(data.change_amount)),
    }) + '\n';
    formatted += t('chatbot.tpl_direction_line', {
      direction: data.direction === 'up' ? t('chatbot.tpl_direction_up') : t('chatbot.tpl_direction_down'),
      percent: Math.round(data.probability * 100),
    }) + '\n';
    formatted += t('chatbot.tpl_confidence_interval', {
      lower: formatNumber(data.confidence_interval.lower),
      upper: formatNumber(data.confidence_interval.upper),
    }) + '\n\n';

    // Technical signals
    if (data.technical_signals && data.technical_signals.length > 0) {
      formatted += t('chatbot.tpl_technical_signals_header') + '\n';
      data.technical_signals.forEach(signal => {
        formatted += `• ${signal}\n`;
      });
      formatted += `\n`;
    }

    // Confidence
    formatted += t('chatbot.tpl_confidence_line', { percent: Math.round((data.confidence || 0.5) * 100) }) + '\n\n';

    // Current indicators
    if (data.current_indicators) {
      const ind = data.current_indicators;
      formatted += t('chatbot.tpl_current_indicators_header') + '\n';
      formatted += t('chatbot.tpl_rsi_line', { value: ind.rsi.toFixed(1) }) + '\n';
      formatted += t('chatbot.tpl_macd_line', { value: ind.macd.toFixed(2) }) + '\n';
      formatted += t('chatbot.tpl_relative_volume_line', { value: ind.relative_volume.toFixed(2) }) + '\n';
      formatted += t('chatbot.tpl_trend_line', {
        label: ind.trend_strength > 0 ? t('chatbot.tpl_trend_up_label') : t('chatbot.tpl_trend_down_label'),
      }) + '\n\n';
    }

    // Disclaimer
    formatted += `⚠️ ${data.disclaimer || t('chatbot.disclaimer_default')}`;

    return formatted;
  };

  const numLocale = 'vi-VN';
  const formatNumber = (num) => {
    if (!num) return 'N/A';
    return num.toLocaleString(numLocale);
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
        <h2>{t('chatbot.header_title')}</h2>
        <p>{t('chatbot.header_subtitle')}</p>
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
          <h4>{t('chatbot.sample_questions_header', { category: selectedCategory.name.replace('_', ' ') })}</h4>
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
                {msg.type === 'user' ? t('chatbot.you') : t('chatbot.ai_assistant')}
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
                <span className="message-category">{t('chatbot.category_label', { category: msg.category })}</span>
                {msg.confidence && (
                  <span className="message-confidence">
                    {t('chatbot.confidence_label', { percent: Math.round(msg.confidence * 100) })}
                  </span>
                )}
                {msg.sources && msg.sources.length > 0 && (
                  <span className="message-sources">
                    {t('chatbot.sources_label', { sources: msg.sources.join(', ') })}
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
          placeholder={t('chatbot.input_placeholder')}
          rows={2}
          disabled={isLoading}
        />
        <button
          onClick={() => handleSendMessage()}
          disabled={isLoading || !inputValue.trim()}
          className="send-btn"
        >
          {isLoading ? t('chatbot.btn_processing') : t('chatbot.btn_send')}
        </button>
      </div>
    </div>
  );
};

export default ChatbotAgent;
