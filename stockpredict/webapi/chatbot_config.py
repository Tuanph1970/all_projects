"""
Chatbot Agent Configuration
Centralized configuration for easy customization
"""

# Agent Configuration
AGENT_CONFIG = {
    'cache_enabled': True,
    'cache_timeout': 300,  # 5 minutes
    'max_retries': 3,
    'timeout': 30,  # seconds
    'default_confidence_threshold': 0.7,
}

# Category Weights for Router
# Higher weights = more likely to match this category
CATEGORY_WEIGHTS = {
    'market_overview': 1.0,
    'stock_performance': 1.2,  # Prioritize stock questions
    'sector_analysis': 0.9,
    'market_trends': 1.0,
    'technical_indicators': 1.1,
    'predictions': 0.8,  # Lower priority for predictions
    'comparative_analysis': 0.9,
    'news_events': 0.9,
    'user_actions': 1.0,
}

# Data Source Configuration
DATA_SOURCES = {
    'primary': 'VCI',
    'fallback': 'TCBS',
    'timeout': 10,  # seconds
}

# Response Formatting
RESPONSE_CONFIG = {
    'include_sources': True,
    'include_confidence': True,
    'include_metadata': True,
    'max_response_length': 2000,  # characters
    'decimal_places': 2,
}

# Technical Indicator Defaults
TECHNICAL_DEFAULTS = {
    'rsi_period': 14,
    'macd_fast': 12,
    'macd_slow': 26,
    'macd_signal': 9,
    'sma_period': 20,
    'ema_period': 20,
    'lookback_days': 90,
}

# Prediction Configuration
PREDICTION_CONFIG = {
    'default_horizon': '1D',  # 1 day
    'max_horizon_days': 30,
    'confidence_threshold': 0.6,
    'ensemble_models': ['RNN', 'XGBoost', 'LightGBM'],
    'use_ensemble': True,
}

# Market Data Configuration
MARKET_CONFIG = {
    'indices': ['VNINDEX', 'VN30', 'HNXINDEX'],
    'exchanges': ['HOSE', 'HNX', 'UPCOM'],
    'update_frequency': 60,  # seconds
}

# Logging Configuration
LOGGING_CONFIG = {
    'enabled': True,
    'level': 'INFO',  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    'log_queries': True,
    'log_responses': True,
    'log_errors': True,
    'log_file': 'chatbot_agent.log',
}

# Performance Monitoring
MONITORING_CONFIG = {
    'track_response_time': True,
    'track_agent_usage': True,
    'track_category_distribution': True,
    'alert_slow_queries': True,
    'slow_query_threshold': 5.0,  # seconds
}

# Feature Flags
FEATURES = {
    'enable_predictions': True,
    'enable_technical_analysis': True,
    'enable_sentiment_analysis': False,  # Future feature
    'enable_multi_language': False,  # Future feature
    'enable_voice_input': False,  # Future feature
}

# Rate Limiting
RATE_LIMIT = {
    'enabled': True,
    'requests_per_minute': 60,
    'requests_per_hour': 500,
}

# Error Messages
ERROR_MESSAGES = {
    'no_data': "I couldn't find data for your question. Please try rephrasing.",
    'service_unavailable': "The data service is currently unavailable. Please try again later.",
    'invalid_ticker': "I couldn't recognize that stock ticker. Please check and try again.",
    'rate_limit': "You've made too many requests. Please wait a moment and try again.",
    'timeout': "The request took too long. Please try again with a simpler question.",
}

# Sample Questions (for UI suggestions)
SAMPLE_QUESTIONS = {
    'market_overview': [
        "What is the current VN-Index level?",
        "How did the VN-Index perform today?",
        "What's the VN30 Index movement this week?",
        "What's the trading volume on HOSE today?",
    ],
    'stock_performance': [
        "What's the current price of VCB stock?",
        "Which stocks are gaining the most today?",
        "Show me the top 10 stocks by trading volume",
        "What stocks hit ceiling price today?",
    ],
    'sector_analysis': [
        "Which sectors are leading the market today?",
        "How is the banking sector performing?",
        "What's happening with real estate stocks?",
    ],
    'market_trends': [
        "Is the market in an uptrend or downtrend?",
        "What's the market breadth today?",
        "Are foreign investors buying or selling?",
    ],
    'technical_indicators': [
        "What's the RSI for VCB?",
        "Show me the MACD for VNINDEX",
        "Calculate 20-day moving average for HPG",
    ],
    'predictions': [
        "Will the market go up or down tomorrow?",
        "What's the outlook for VN-Index this week?",
        "Predict the price of VCB for next month",
    ],
}

# Notification Settings
NOTIFICATION_CONFIG = {
    'send_email_on_error': False,
    'send_slack_notification': False,
    'admin_email': 'admin@stockpredict.com',
    'slack_webhook': None,
}


def get_config(key: str, default=None):
    """
    Get configuration value by key

    Args:
        key: Configuration key (e.g., 'AGENT_CONFIG.cache_timeout')
        default: Default value if key not found

    Returns:
        Configuration value or default
    """
    parts = key.split('.')
    config = globals()

    for part in parts:
        if isinstance(config, dict):
            config = config.get(part)
        else:
            config = getattr(config, part, None)

        if config is None:
            return default

    return config


def update_config(key: str, value):
    """
    Update configuration value

    Args:
        key: Configuration key (e.g., 'AGENT_CONFIG.cache_timeout')
        value: New value
    """
    parts = key.split('.')
    config = globals()

    for i, part in enumerate(parts[:-1]):
        if isinstance(config, dict):
            config = config[part]
        else:
            config = getattr(config, part)

    if isinstance(config, dict):
        config[parts[-1]] = value
    else:
        setattr(config, parts[-1], value)
