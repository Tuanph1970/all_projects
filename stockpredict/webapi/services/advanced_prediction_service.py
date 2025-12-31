"""
Advanced Stock Prediction Service
Integrates Sundial temporal patterns with technical analysis rules
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging

from services.stock_market_service import CompanyService
from services.technical_analysis_service import TechnicalAnalysisService
from core.exceptions import ValidationException, ExternalServiceException

logger = logging.getLogger(__name__)


class TechnicalFeatureEngineer:
    """
    Engineer features encoding cross-variable relationships
    Sundial handles temporal patterns, features encode indicator relationships
    """

    def __init__(self):
        self.technical_service = TechnicalAnalysisService()

    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create comprehensive feature set for prediction
        Encodes indicator-price relationships implicitly
        """
        df = df.copy()

        # === Basic Price Features ===
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))

        # === Volume Features ===
        df['volume_ma_20'] = df['volume'].rolling(20).mean()
        df['relative_volume'] = df['volume'] / (df['volume_ma_20'] + 1e-10)

        # === Technical Indicators ===
        df['rsi'] = self._calculate_rsi(df['close'])
        macd, signal, histogram = self._calculate_macd(df['close'])
        df['macd'] = macd
        df['macd_signal'] = signal
        df['macd_histogram'] = histogram

        bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(df['close'])
        df['bb_upper'] = bb_upper
        df['bb_middle'] = bb_middle
        df['bb_lower'] = bb_lower

        stoch_k, stoch_d = self._calculate_stochastic(df['high'], df['low'], df['close'])
        df['stoch_k'] = stoch_k
        df['stoch_d'] = stoch_d

        # === Engineered Relationship Features ===
        # These encode cross-variable relationships

        # 1. Volume-Price Relationships
        df['volume_weighted_price'] = df['close'] * df['relative_volume']
        df['price_volume_trend'] = df['close'] * df['volume'] / (df['volume'].rolling(20).mean() + 1e-10)

        # 2. RSI-Price Relationships
        df['rsi_momentum'] = df['rsi'].diff()
        df['rsi_extreme'] = (df['rsi'] - 50) / 50  # Normalized: -1 to +1
        df['rsi_price_divergence'] = (df['rsi'].diff() * df['close'].pct_change()).rolling(5).mean()

        # 3. MACD-Price Relationships
        df['macd_strength'] = df['macd_histogram'] / (df['close'] + 1e-10)
        df['macd_trend'] = df['macd_histogram'].diff()

        # 4. Bollinger Band-Price Relationships
        bb_range = df['bb_upper'] - df['bb_lower']
        df['bb_position'] = (df['close'] - df['bb_lower']) / (bb_range + 1e-10)
        df['bb_width'] = bb_range / (df['bb_middle'] + 1e-10)
        df['bb_squeeze'] = df['bb_width'].rolling(20).mean() / (df['bb_width'] + 1e-10)

        # 5. Multi-Indicator Composite Scores
        rsi_norm = (df['rsi'] - 50) / 50
        macd_norm = df['macd_histogram'] / (df['macd_histogram'].abs().rolling(20).mean() + 1e-10)
        stoch_norm = (df['stoch_k'] - 50) / 50
        df['momentum_composite'] = (rsi_norm + macd_norm + stoch_norm) / 3

        # 6. Volatility Features
        df['volatility'] = df['returns'].rolling(20).std()
        df['atr'] = (df['high'] - df['low']).rolling(14).mean()

        # 7. Trend Features
        df['ma_5'] = df['close'].rolling(5).mean()
        df['ma_10'] = df['close'].rolling(10).mean()
        df['ma_20'] = df['close'].rolling(20).mean()
        df['ma_50'] = df['close'].rolling(50).mean()
        df['trend_strength'] = (df['ma_5'] - df['ma_20']) / (df['ma_20'] + 1e-10)

        # Fill NaN values
        df = df.fillna(method='bfill').fillna(method='ffill').fillna(0)

        return df

    @staticmethod
    def _calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / (loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def _calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
        """Calculate MACD"""
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        histogram = macd - signal_line
        return macd, signal_line, histogram

    @staticmethod
    def _calculate_bollinger_bands(prices: pd.Series, period: int = 20, std: float = 2):
        """Calculate Bollinger Bands"""
        middle = prices.rolling(window=period).mean()
        std_dev = prices.rolling(window=period).std()
        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)
        return upper, middle, lower

    @staticmethod
    def _calculate_stochastic(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14):
        """Calculate Stochastic Oscillator"""
        lowest_low = low.rolling(window=period).min()
        highest_high = high.rolling(window=period).max()
        k = 100 * ((close - lowest_low) / (highest_high - lowest_low + 1e-10))
        d = k.rolling(window=3).mean()
        return k, d


class TechnicalRuleEngine:
    """
    Apply expert technical analysis rules to enhance predictions
    Rules add domain knowledge about indicator-price relationships
    """

    def apply_rules(
        self,
        base_prediction: float,
        current_state: Dict,
        features_df: pd.DataFrame
    ) -> Dict:
        """
        Apply technical rules to adjust base prediction

        Args:
            base_prediction: Base model prediction
            current_state: Current technical indicators
            features_df: Historical features for context

        Returns:
            Adjusted prediction with signals
        """
        adjustment_factor = 1.0
        signals = []
        confidence_factors = []

        # Rule 1: RSI Oversold/Overbought
        rsi = current_state.get('rsi', 50)
        if rsi < 30:  # Oversold - bullish reversal
            adjustment = 0.02
            adjustment_factor += adjustment
            signals.append(f"RSI Oversold ({rsi:.1f}) → Bullish reversal likely")
            confidence_factors.append(('RSI Oversold', 0.75))
        elif rsi > 70:  # Overbought - bearish correction
            adjustment = -0.02
            adjustment_factor += adjustment
            signals.append(f"RSI Overbought ({rsi:.1f}) → Bearish correction likely")
            confidence_factors.append(('RSI Overbought', 0.75))

        # Rule 2: Volume Confirmation
        relative_volume = current_state.get('relative_volume', 1.0)
        price_change = current_state.get('returns', 0)

        if relative_volume > 2.0:  # High volume
            if price_change > 0:
                adjustment_factor += 0.015
                signals.append(f"High Volume ({relative_volume:.1f}x) confirms uptrend")
                confidence_factors.append(('Volume Confirmation', 0.8))
            else:
                adjustment_factor -= 0.015
                signals.append(f"High Volume ({relative_volume:.1f}x) confirms downtrend")
                confidence_factors.append(('Volume Confirmation', 0.8))

        # Rule 3: MACD Crossover
        macd = current_state.get('macd', 0)
        macd_signal = current_state.get('macd_signal', 0)

        if len(features_df) >= 2:
            macd_prev = features_df['macd'].iloc[-2]
            signal_prev = features_df['macd_signal'].iloc[-2]

            if macd > macd_signal and macd_prev <= signal_prev:  # Bullish
                adjustment_factor += 0.025
                signals.append("MACD Bullish Crossover")
                confidence_factors.append(('MACD Bullish', 0.8))
            elif macd < macd_signal and macd_prev >= signal_prev:  # Bearish
                adjustment_factor -= 0.025
                signals.append("MACD Bearish Crossover")
                confidence_factors.append(('MACD Bearish', 0.8))

        # Rule 4: Bollinger Band Position
        bb_position = current_state.get('bb_position', 0.5)
        if bb_position < 0.1:  # Near lower band
            adjustment_factor += 0.015
            signals.append(f"Price near BB lower band ({bb_position:.1%}) → Bounce likely")
            confidence_factors.append(('BB Lower', 0.65))
        elif bb_position > 0.9:  # Near upper band
            adjustment_factor -= 0.015
            signals.append(f"Price near BB upper band ({bb_position:.1%}) → Pullback likely")
            confidence_factors.append(('BB Upper', 0.65))

        # Rule 5: Trend Strength
        trend_strength = current_state.get('trend_strength', 0)
        if abs(trend_strength) > 0.05:  # Strong trend
            if trend_strength > 0:
                adjustment_factor += 0.01
                signals.append(f"Strong uptrend (MA spread: {trend_strength:.2%})")
                confidence_factors.append(('Trend Up', 0.7))
            else:
                adjustment_factor -= 0.01
                signals.append(f"Strong downtrend (MA spread: {trend_strength:.2%})")
                confidence_factors.append(('Trend Down', 0.7))

        # Calculate confidence
        avg_confidence = np.mean([cf[1] for cf in confidence_factors]) if confidence_factors else 0.5

        # Apply adjustment
        adjusted_prediction = base_prediction * adjustment_factor

        return {
            'base_prediction': base_prediction,
            'adjusted_prediction': adjusted_prediction,
            'adjustment_factor': adjustment_factor,
            'adjustment_percent': (adjustment_factor - 1.0) * 100,
            'technical_signals': signals,
            'confidence': avg_confidence,
            'signal_count': len(signals)
        }


class AdvancedStockPredictor:
    """
    Advanced prediction system combining:
    1. Sundial-style temporal pattern analysis
    2. Engineered features for cross-variable relationships
    3. Technical rule engine for expert knowledge
    """

    def __init__(self):
        self.company_service = CompanyService()
        self.feature_engineer = TechnicalFeatureEngineer()
        self.rule_engine = TechnicalRuleEngine()
        logger.info("AdvancedStockPredictor initialized")

    def predict_stock(
        self,
        ticker: str,
        horizon: str = '1D',
        days_back: int = 90
    ) -> Dict:
        """
        Generate comprehensive stock prediction

        Args:
            ticker: Stock symbol
            horizon: Prediction horizon (1D, 1W, 1M)
            days_back: Historical data period

        Returns:
            Prediction results with technical analysis
        """
        try:
            logger.info(f"Generating prediction for {ticker}, horizon: {horizon}")

            # Step 1: Fetch historical data
            to_date = datetime.now().strftime('%Y-%m-%d')
            from_date = (datetime.now() - timedelta(days=days_back + 100)).strftime('%Y-%m-%d')

            df = self.company_service.get_price_history_df(
                ticker, "VCI", start=from_date, end=to_date
            )

            if df is None or len(df) < 30:
                raise ValidationException(f"Insufficient data for {ticker}")

            logger.info(f"Fetched {len(df)} days of data for {ticker}")

            # Step 2: Engineer features
            features_df = self.feature_engineer.create_features(df)
            logger.info(f"Created {len(features_df.columns)} features")

            # Step 3: Generate base prediction using temporal patterns
            # In production, this would use Sundial or similar time series model
            # For now, use statistical prediction with temporal patterns
            base_prediction = self._generate_temporal_prediction(features_df, horizon)

            # Step 4: Get current technical state
            current_state = {
                'rsi': features_df['rsi'].iloc[-1],
                'macd': features_df['macd'].iloc[-1],
                'macd_signal': features_df['macd_signal'].iloc[-1],
                'relative_volume': features_df['relative_volume'].iloc[-1],
                'bb_position': features_df['bb_position'].iloc[-1],
                'trend_strength': features_df['trend_strength'].iloc[-1],
                'returns': features_df['returns'].iloc[-1],
                'volatility': features_df['volatility'].iloc[-1],
                'momentum_composite': features_df['momentum_composite'].iloc[-1]
            }

            # Step 5: Apply technical rules
            rule_results = self.rule_engine.apply_rules(
                base_prediction['mean'],
                current_state,
                features_df
            )

            # Step 6: Compile results
            current_price = df['close'].iloc[-1]
            predicted_price = rule_results['adjusted_prediction']
            change_percent = ((predicted_price - current_price) / current_price) * 100

            result = {
                'ticker': ticker,
                'current_price': current_price,
                'date': df['date'].iloc[-1].strftime('%Y-%m-%d') if hasattr(df['date'].iloc[-1], 'strftime') else str(df['date'].iloc[-1]),

                # Predictions
                'predicted_price': predicted_price,
                'change_percent': change_percent,
                'change_amount': predicted_price - current_price,
                'direction': 'up' if change_percent > 0 else 'down',
                'probability': min(0.5 + abs(change_percent) / 20, 0.95),  # Heuristic

                # Confidence intervals
                'confidence_interval': {
                    'lower': base_prediction['lower'],
                    'upper': base_prediction['upper']
                },

                # Technical analysis
                'technical_signals': rule_results['technical_signals'],
                'confidence': rule_results['confidence'],
                'adjustment_percent': rule_results['adjustment_percent'],

                # Current indicators
                'current_indicators': current_state,

                # Metadata
                'horizon': horizon,
                'model_used': 'Temporal Pattern Analysis + Technical Rules',
                'disclaimer': 'AI-powered analysis for informational purposes only. Not financial advice.'
            }

            logger.info(f"Prediction complete for {ticker}: {predicted_price:.2f}")
            return result

        except ValidationException as e:
            logger.warning(f"Validation error in prediction: {e}")
            raise
        except Exception as e:
            logger.error(f"Error generating prediction for {ticker}: {e}", exc_info=True)
            raise ExternalServiceException("PredictionService", str(e))

    def _generate_temporal_prediction(self, features_df: pd.DataFrame, horizon: str) -> Dict:
        """
        Generate base prediction using temporal patterns
        In production, integrate Sundial or similar time series foundation model
        """
        # Get recent price history
        prices = features_df['close'].values

        # Simple temporal pattern analysis
        # Calculate trends and momentum
        recent_trend = np.mean(np.diff(prices[-20:]))  # 20-day trend
        momentum = features_df['momentum_composite'].iloc[-1]
        volatility = features_df['volatility'].iloc[-1]

        # Horizon mapping
        horizon_map = {'1D': 1, '1W': 7, '1M': 30}
        days = horizon_map.get(horizon, 1)

        # Base prediction using trend + momentum
        current_price = prices[-1]
        trend_component = recent_trend * days
        momentum_component = current_price * momentum * 0.01 * days

        # Combine components
        predicted_price = current_price + trend_component + momentum_component

        # Calculate confidence interval using volatility
        std_dev = volatility * current_price * np.sqrt(days)

        return {
            'mean': predicted_price,
            'lower': predicted_price - 1.96 * std_dev,  # 95% CI
            'upper': predicted_price + 1.96 * std_dev,
            'std': std_dev
        }

    def format_prediction_response(self, result: Dict) -> str:
        """Format prediction for chatbot display"""

        if 'error' in result:
            return f"❌ {result['error']}"

        current = result['current_price']
        predicted = result['predicted_price']
        change = result['change_percent']
        direction_emoji = "📈" if change > 0 else "📉"

        response = f"""**{result['ticker']} Stock Prediction** {direction_emoji}

**Current Status**:
• Price: {current:,.0f} VND
• Date: {result['date']}

**{result['horizon']} Forecast**:
• Predicted: {predicted:,.0f} VND
• Change: {change:+.2f}% ({result['change_amount']:+,.0f} VND)
• Direction: {result['direction'].upper()} ({int(result['probability']*100)}% probability)
• 95% Range: {result['confidence_interval']['lower']:,.0f} - {result['confidence_interval']['upper']:,.0f} VND

**Technical Signals**:
"""

        if result['technical_signals']:
            for signal in result['technical_signals']:
                response += f"• {signal}\n"
        else:
            response += "• No significant technical signals\n"

        response += f"\n**Confidence**: {int(result['confidence']*100)}%"

        response += f"""

**Current Indicators**:
• RSI: {result['current_indicators']['rsi']:.1f}
• MACD: {result['current_indicators']['macd']:.2f}
• Volume: {result['current_indicators']['relative_volume']:.2f}x average
• Trend: {'Uptrend ↗' if result['current_indicators']['trend_strength'] > 0 else 'Downtrend ↘'}

⚠️ {result['disclaimer']}
"""

        return response.strip()


# Global instance for reuse
_predictor_instance = None

def get_advanced_predictor() -> AdvancedStockPredictor:
    """Get singleton instance of predictor"""
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = AdvancedStockPredictor()
    return _predictor_instance
