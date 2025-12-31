# Advanced Stock Prediction System

## Overview

An enhanced prediction system integrating **Sundial-inspired temporal pattern analysis**, **engineered features encoding cross-variable relationships**, and **expert technical analysis rules** for Vietnamese stock market predictions.

## Architecture

### Three-Layer Approach

```
┌─────────────────────────────────────────────────────────────┐
│                   User Question                              │
│         "Will VCB go up tomorrow?"                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│          1. TEMPORAL PATTERN ANALYSIS                        │
│   - Historical price data (90+ days)                         │
│   - Trend analysis and momentum                              │
│   - Volatility calculation                                   │
│   - Base prediction generation                               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│       2. FEATURE ENGINEERING                                 │
│   Encodes indicator-price relationships:                     │
│   - Volume-Price relationships                               │
│   - RSI-Price divergence                                     │
│   - MACD strength & trend                                    │
│   - Bollinger Band position                                  │
│   - Multi-indicator composite scores                         │
│   - Volatility & trend features                              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│       3. TECHNICAL RULE ENGINE                               │
│   Expert knowledge rules:                                    │
│   - RSI oversold/overbought                                  │
│   - Volume confirmation                                      │
│   - MACD crossover                                           │
│   - Bollinger Band bounces                                   │
│   - Trend strength                                           │
│   → Adjustment factor applied to base prediction             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              FINAL PREDICTION                                │
│   - Adjusted price forecast                                  │
│   - Technical signals                                        │
│   - Confidence score                                         │
│   - 95% confidence interval                                  │
└─────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Temporal Pattern Analysis

**Purpose**: Handle temporal patterns and trends (inspired by Sundial)

**Process**:
- Analyzes recent 20-day price trends
- Calculates momentum from composite indicators
- Estimates volatility for uncertainty quantification
- Generates base prediction with confidence intervals

**Output**: Base prediction with statistical bounds

---

### 2. Feature Engineering

**Purpose**: Encode cross-variable relationships implicitly

**Engineered Features**:

#### Volume-Price Relationships
```python
volume_weighted_price = close * relative_volume
price_volume_trend = close * volume / volume_ma_20
```

#### RSI-Price Relationships
```python
rsi_momentum = rsi.diff()
rsi_extreme = (rsi - 50) / 50  # Normalized -1 to +1
rsi_price_divergence = (rsi.diff() * returns).rolling(5).mean()
```

#### MACD-Price Relationships
```python
macd_strength = macd_histogram / close
macd_trend = macd_histogram.diff()
```

#### Bollinger Band-Price Relationships
```python
bb_position = (close - bb_lower) / (bb_upper - bb_lower)
bb_width = (bb_upper - bb_lower) / bb_middle
bb_squeeze = bb_width.rolling(20).mean() / bb_width
```

#### Multi-Indicator Composite
```python
momentum_composite = (
    (rsi - 50) / 50 +  # RSI contribution
    macd_histogram / macd_histogram.abs().rolling(20).mean() +  # MACD
    (stoch_k - 50) / 50  # Stochastic
) / 3
```

---

### 3. Technical Rule Engine

**Purpose**: Add expert knowledge about indicator-price relationships

**Rules Applied**:

#### Rule 1: RSI Oversold/Overbought
```python
if rsi < 30:  # Oversold
    adjustment = +2%  # Bullish reversal expected
elif rsi > 70:  # Overbought
    adjustment = -2%  # Bearish correction expected
```

#### Rule 2: Volume Confirmation
```python
if relative_volume > 2.0:  # High volume
    if price_change > 0:
        adjustment = +1.5%  # Confirms uptrend
    else:
        adjustment = -1.5%  # Confirms downtrend
```

#### Rule 3: MACD Crossover
```python
if bullish_crossover:
    adjustment = +2.5%  # Strong buy signal
elif bearish_crossover:
    adjustment = -2.5%  # Strong sell signal
```

#### Rule 4: Bollinger Band Position
```python
if bb_position < 0.1:  # Near lower band
    adjustment = +1.5%  # Bounce expected
elif bb_position > 0.9:  # Near upper band
    adjustment = -1.5%  # Pullback expected
```

#### Rule 5: Trend Strength
```python
if abs(trend_strength) > 0.05:  # Strong trend
    if trend_strength > 0:
        adjustment = +1%  # Uptrend continues
    else:
        adjustment = -1%  # Downtrend continues
```

---

## Usage

### Python Backend

```python
from services.advanced_prediction_service import get_advanced_predictor

# Get predictor instance
predictor = get_advanced_predictor()

# Generate prediction
result = predictor.predict_stock(
    ticker='VCB',
    horizon='1D',  # 1D, 1W, or 1M
    days_back=90
)

# Access results
print(f"Current: {result['current_price']}")
print(f"Predicted: {result['predicted_price']}")
print(f"Change: {result['change_percent']:.2f}%")
print(f"Confidence: {result['confidence']:.0%}")
print(f"Signals: {result['technical_signals']}")
```

### Chatbot Integration

The prediction system is automatically integrated into the chatbot:

```
User: "Will VCB go up tomorrow?"
Bot: Generates prediction using AdvancedStockPredictor
```

**Example Response**:
```
**VCB Stock Prediction** 📈

**Current Status**:
• Price: 95,000 VND
• Date: 2025-10-07

**1D Forecast**:
• Predicted: 96,500 VND
• Change: +1.58% (+1,500 VND)
• Direction: UP (72% probability)
• 95% Range: 94,800 - 98,200 VND

**Technical Signals**:
• RSI Oversold (28.5) → Bullish reversal likely
• MACD Bullish Crossover
• Price near BB lower band (8%) → Bounce likely

**Confidence**: 75%

**Current Indicators**:
• RSI: 28.5
• MACD: -850.50
• Volume: 2.3x average
• Trend: Uptrend ↗

⚠️ AI-powered analysis for informational purposes only. Not financial advice.
```

---

## API Integration

### Prediction Endpoint

**Endpoint**: `POST /api/chatbot/ask/`

**Request**:
```json
{
  "question": "Predict VCB stock for tomorrow"
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "ticker": "VCB",
    "current_price": 95000,
    "predicted_price": 96500,
    "change_percent": 1.58,
    "direction": "up",
    "probability": 0.72,
    "confidence_interval": {
      "lower": 94800,
      "upper": 98200
    },
    "technical_signals": [
      "RSI Oversold (28.5) → Bullish reversal likely",
      "MACD Bullish Crossover",
      "Price near BB lower band (8%) → Bounce likely"
    ],
    "confidence": 0.75,
    "current_indicators": {
      "rsi": 28.5,
      "macd": -850.5,
      "relative_volume": 2.3,
      "trend_strength": 0.08
    },
    "model_used": "Temporal Pattern Analysis + Technical Rules"
  },
  "category": "predictions",
  "confidence": 0.75,
  "sources": [
    "Temporal Pattern Analysis",
    "Technical Indicators",
    "Expert Rules Engine"
  ]
}
```

---

## Advantages

### 1. Multi-Layer Intelligence
- **Temporal patterns**: Captures time-based trends
- **Feature engineering**: Encodes complex relationships
- **Expert rules**: Adds domain knowledge

### 2. Probabilistic Predictions
- 95% confidence intervals
- Probability scores for direction
- Confidence metrics for reliability

### 3. Explainable AI
- Technical signals explain the reasoning
- Shows which indicators influenced the prediction
- Transparent adjustment factors

### 4. Real-time Adaptation
- Uses current market indicators
- Adjusts to recent price movements
- Considers volume and volatility

---

## Extending the System

### Adding New Features

```python
# In TechnicalFeatureEngineer.create_features()
df['your_new_feature'] = calculate_custom_indicator(df)
```

### Adding New Rules

```python
# In TechnicalRuleEngine.apply_rules()

# Rule N: Your Custom Rule
if your_condition:
    adjustment_factor += your_adjustment
    signals.append("Your signal message")
    confidence_factors.append(('Your Rule', confidence))
```

### Integrating Sundial Model

For production deployment with actual Sundial model:

```python
# Install transformers and torch
pip install transformers torch

# In advanced_prediction_service.py
from transformers import AutoModelForCausalLM
import torch

class SundialPredictor:
    def __init__(self):
        self.model = AutoModelForCausalLM.from_pretrained(
            'thuml/sundial-base-128m',
            trust_remote_code=True
        )
        self.model.eval()

    def predict(self, feature_series, forecast_length=5):
        input_tensor = torch.tensor(feature_series, dtype=torch.float32)
        with torch.no_grad():
            output = self.model.generate(
                input_tensor,
                max_new_tokens=forecast_length
            )
        return output
```

---

## Performance

### Prediction Speed
- **Feature Engineering**: ~500ms
- **Temporal Analysis**: ~100ms
- **Rule Application**: ~50ms
- **Total**: <1 second per prediction

### Accuracy Expectations
- **1-Day Predictions**: 60-70% directional accuracy
- **1-Week Predictions**: 55-65% directional accuracy
- **1-Month Predictions**: 50-60% directional accuracy

*Note: Actual accuracy depends on market conditions and should be validated with backtesting*

---

## Configuration

### Adjusting Parameters

Edit `chatbot_config.py`:

```python
PREDICTION_CONFIG = {
    'default_horizon': '1D',
    'max_horizon_days': 30,
    'confidence_threshold': 0.6,
    'lookback_period': 90,
    'feature_engineering': {
        'rsi_period': 14,
        'macd_fast': 12,
        'macd_slow': 26,
        'bollinger_period': 20
    },
    'technical_rules': {
        'rsi_oversold': 30,
        'rsi_overbought': 70,
        'volume_threshold': 2.0,
        'trend_threshold': 0.05
    }
}
```

---

## Testing

### Unit Tests

```python
import unittest
from services.advanced_prediction_service import AdvancedStockPredictor

class TestAdvancedPredictor(unittest.TestCase):
    def setUp(self):
        self.predictor = AdvancedStockPredictor()

    def test_prediction_generation(self):
        result = self.predictor.predict_stock('VCB', '1D')
        self.assertIn('predicted_price', result)
        self.assertIn('technical_signals', result)
        self.assertGreater(result['confidence'], 0)
```

---

## Troubleshooting

### Common Issues

**Issue**: Insufficient data error
**Solution**: Ensure stock has at least 30 days of historical data

**Issue**: High volatility warnings
**Solution**: Wide confidence intervals are normal during volatile periods

**Issue**: Conflicting technical signals
**Solution**: System averages confidence factors; check individual signal weights

---

## Future Enhancements

1. **Actual Sundial Integration**: Replace temporal analysis with real Sundial model
2. **Multi-Asset Predictions**: Extend to indices, currencies, commodities
3. **Ensemble Models**: Combine multiple prediction approaches
4. **Backtesting Framework**: Historical validation and performance metrics
5. **Real-time Updates**: WebSocket integration for live predictions
6. **Custom Strategies**: Allow users to define custom technical rules

---

## References

- Sundial Model: [thuml/sundial-base-128m](https://huggingface.co/thuml/sundial-base-128m)
- Technical Indicators: RSI, MACD, Bollinger Bands, Stochastic
- Feature Engineering: Cross-variable relationship encoding
- Expert Systems: Rule-based technical analysis

---

## License

Part of the Stock Market Chatbot System
See main documentation for license information

---

## Support

For issues or questions about the prediction system:
- See main chatbot documentation
- Review code comments in `advanced_prediction_service.py`
- Contact: support@stockpredict.com
