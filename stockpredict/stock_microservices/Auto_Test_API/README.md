# Auto_Test_API - Stock Helper API Testing Suite

Standalone automated testing application for Stock Helper Microservices APIs.

## Overview

This testing suite covers all 7 microservices:

| Service | Description | Endpoints Tested |
|---------|-------------|------------------|
| Auth Service | User authentication & authorization | 20 tests |
| Stock Data Service | Companies, prices, market data | 17 tests |
| Portfolio Service | Portfolios, holdings, transactions | 21 tests |
| Analysis Service | Technical & fundamental analysis | 14 tests |
| Prediction Service | ML-based price predictions | 13 tests |
| AI Insights Service | LLM-powered market insights | 11 tests |
| Chatbot Service | Conversational AI | 13 tests |

## Installation

```bash
cd Auto_Test_API
pip install -r requirements.txt
```

## Configuration

Edit `config.py` or create a `.env` file:

```env
# Base URL (via Traefik gateway)
BASE_URL=http://localhost:8004/stock_helper/api/v2

# Test Stock Symbol
TEST_STOCK_SYMBOL=VNM

# Timeouts
REQUEST_TIMEOUT=30
LONG_REQUEST_TIMEOUT=120
```

## Usage

### Run All Tests
```bash
python test_stock_api.py
```

### Run Specific Service Tests
```bash
# Authentication tests
python test_stock_api.py --service auth

# Stock data tests
python test_stock_api.py --service stock

# Portfolio tests
python test_stock_api.py --service portfolio

# Analysis tests
python test_stock_api.py --service analysis

# Prediction tests
python test_stock_api.py --service prediction

# AI Insights tests
python test_stock_api.py --service ai

# Chatbot tests
python test_stock_api.py --service chatbot
```

### Run Individual Test Files
```bash
# Auth tests only
python -m tests.test_auth_api

# Stock data tests only
python -m tests.test_stock_data_api

# Portfolio tests only
python -m tests.test_portfolio_api
```

### Options
```bash
python test_stock_api.py --help

Options:
  --base-url URL    API base URL (default: http://localhost:8004/stock_helper/api/v2)
  --service NAME    Run tests for specific service only
  --quiet, -q       Reduce output verbosity
  --list-services   List available services
```

## Test Categories

### 1. Auth Service Tests (`test_auth_api.py`)
- User Registration (valid/invalid data)
- User Login (valid/invalid credentials)
- Token Verification
- Token Refresh
- Password Change
- Password Reset Request
- Logout (single device/all devices)
- Protected Endpoint Access

### 2. Stock Data Service Tests (`test_stock_data_api.py`)
- List Companies (paginated, all, by exchange)
- Get Stock Details
- Get Historical Data (with/without date params)
- Search Companies (by name, by symbol)
- Top Movers (gainers, losers, actives)
- Industries List & Companies by Industry
- Market Indices
- Price Board

### 3. Portfolio Service Tests (`test_portfolio_api.py`)
- Portfolio CRUD (create, read, update, delete)
- Holdings Management (add, update, delete)
- Transaction Recording
- Price Alerts (create, update, delete)
- Watchlist Operations
- Unauthenticated Access Protection

### 4. Analysis Service Tests (`test_analysis_api.py`)
- Technical Analysis (with period)
- Fundamental Analysis
- Stock Screener (filters, config save/load)
- Stock Comparison
- Industry Analysis
- Combined Analysis
- Trading Signals
- Quick Summary

### 5. Prediction Service Tests (`test_prediction_api.py`)
- Generate Predictions (POST/GET)
- Bulk Predictions
- Model Management (list, details, features)
- Training Logs
- Model Training (requires auth)
- Backtesting
- Model Comparison
- Health Status

### 6. AI Insights Service Tests (`test_ai_insights_api.py`)
- AI Capabilities
- Generate Insights (POST/GET)
- Stock Comparison
- News Analysis
- Ask Question
- Market Overview
- Batch Insights
- Trending Topics
- Portfolio Insights
- Sector Insights

### 7. Chatbot Service Tests (`test_chatbot_api.py`)
- Supported Intents
- Quick Suggestions
- Send Messages (initial, follow-up, stock queries)
- Conversation History
- Export History (JSON, Markdown)
- Feedback Submission
- Usage Statistics
- Session Management

## Project Structure

```
Auto_Test_API/
├── config.py                    # Configuration settings
├── requirements.txt             # Python dependencies
├── test_stock_api.py           # Main test runner
├── README.md                    # This file
├── utils/
│   ├── __init__.py
│   └── http_client.py          # HTTP client utilities
└── tests/
    ├── __init__.py
    ├── test_auth_api.py        # Auth service tests
    ├── test_stock_data_api.py  # Stock data tests
    ├── test_portfolio_api.py   # Portfolio tests
    ├── test_analysis_api.py    # Analysis tests
    ├── test_prediction_api.py  # Prediction tests
    ├── test_ai_insights_api.py # AI insights tests
    └── test_chatbot_api.py     # Chatbot tests
```

## API Endpoints Reference

### Auth Service (`/auth`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /register | Register new user |
| POST | /login | User login |
| POST | /refresh | Refresh token |
| POST | /verify | Verify token |
| GET | /me | Get current user |
| POST | /change-password | Change password |
| POST | /logout | Logout single device |
| POST | /logout-all | Logout all devices |
| POST | /reset-password | Request password reset |

### Stock Data Service (`/companies`, `/stocks`, `/market`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /companies | List companies (paginated) |
| GET | /companies/all | All companies |
| GET | /stocks/{symbol} | Company details |
| GET | /stocks/{symbol}/history | Historical data |
| GET | /stocks/search | Search companies |
| GET | /companies/top-gainers | Top gainers |
| GET | /companies/top-losers | Top losers |
| GET | /companies/top-actives | Most active |
| GET | /industries | All industries |
| GET | /market/indices | Market indices |
| GET | /priceboards | Price board |

### Portfolio Service (`/portfolio`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /portfolios | Create portfolio |
| GET | /portfolios | List portfolios |
| GET | /portfolios/default | Default portfolio |
| GET | /portfolios/{id} | Portfolio details |
| PUT | /portfolios/{id} | Update portfolio |
| DELETE | /portfolios/{id} | Delete portfolio |
| POST | /portfolios/{id}/holdings | Add holding |
| POST | /portfolios/{id}/transactions | Record transaction |
| POST | /alerts | Create price alert |
| POST | /watchlist | Add to watchlist |

### Analysis Service (`/analysis`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /technical/{symbol} | Technical analysis |
| GET | /fundamental/{symbol} | Fundamental analysis |
| POST | /screener | Run screener |
| POST | /compare | Compare stocks |
| GET | /signals | Trading signals |
| GET | /summary/{symbol} | Quick summary |

### Prediction Service (`/predictions`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /predict | Generate prediction |
| GET | /predict/{symbol} | Get prediction |
| POST | /predict/bulk | Bulk predictions |
| GET | /models | List models |
| POST | /models/train | Train model |
| POST | /backtest | Run backtest |

### AI Insights Service (`/insights`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /insight | Generate insight |
| POST | /compare | Compare stocks |
| POST | /ask | Ask question |
| GET | /market-overview | Market overview |
| GET | /trending | Trending topics |

### Chatbot Service (`/chat`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /chat | Send message |
| GET | /history/{session_id} | Get history |
| DELETE | /session/{session_id} | Clear session |
| GET | /suggestions | Get suggestions |
| POST | /feedback | Submit feedback |

## Notes

- AI Insights and Chatbot tests may fail if AI API keys (OpenAI/Anthropic) are not configured
- Prediction model training tests may take longer due to ML processing
- Tests create temporary users for authentication testing
- All tests are independent and can be run in any order
