"""
AI Insights Service
Comprehensive AI-driven stock analysis including pattern recognition,
sentiment analysis, risk assessment, and price prediction.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import pickle
import json
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import xgboost as xgb
from scipy import stats
from textblob import TextBlob
import yfinance as yf
import requests
from bs4 import BeautifulSoup

from services.advanced_technical_indicators import AdvancedTechnicalIndicators, IndicatorCategory
from services.stock_entities import StockService
from core.exceptions import ExternalServiceException

class PatternType(Enum):
    BULLISH_REVERSAL = "bullish_reversal"
    BEARISH_REVERSAL = "bearish_reversal"
    CONTINUATION = "continuation"
    CONSOLIDATION = "consolidation"
    BREAKOUT = "breakout"

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class SentimentType(Enum):
    VERY_NEGATIVE = "very_negative"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    VERY_POSITIVE = "very_positive"

@dataclass
class PatternDetection:
    pattern_type: PatternType
    confidence: float
    description: str
    start_date: str
    end_date: str
    signal_strength: float

@dataclass
class SentimentAnalysis:
    sentiment_type: SentimentType
    score: float
    confidence: float
    news_count: int
    summary: str

@dataclass
class RiskAssessment:
    risk_level: RiskLevel
    risk_score: float
    volatility: float
    beta: float
    var_95: float
    factors: List[str]

@dataclass
class PricePrediction:
    model_type: str
    predicted_price: float
    confidence_interval: Tuple[float, float]
    accuracy_score: float
    feature_importance: Dict[str, float]
    prediction_date: str

class AIInsightsService:
    def __init__(self):
        self.technical_indicators = AdvancedTechnicalIndicators()
        self.stock_service = StockService()
        self.scaler = StandardScaler()
        self.rf_model = None
        self.xgb_model = None

    def get_comprehensive_insights(self, symbol: str, start_date: str, end_date: str,
                                 selected_indicators: Dict[str, str]) -> Dict[str, Any]:
        """
        Get comprehensive AI insights for a stock including all analysis types.

        Args:
            symbol: Stock symbol
            start_date: Analysis start date
            end_date: Analysis end date
            selected_indicators: Dict with category as key and indicator name as value
                                Example: {'trend': 'MACD', 'momentum': 'RSI', 'volatility': 'BB', 'volume': 'OBV'}
        """
        try:
            results = {}

            # Get stock data
            stock_data = self.technical_indicators.get_price_data(symbol, start_date, end_date)

            # Calculate selected technical indicators
            indicator_names = list(selected_indicators.values())
            indicators_data = self.technical_indicators.calculate_multiple_indicators(
                symbol, indicator_names, start_date, end_date
            )

            # Pattern Recognition
            patterns = self.detect_patterns(stock_data, indicators_data)
            results['pattern_recognition'] = {
                'patterns': [self._serialize_pattern(pattern) for pattern in patterns],
                'summary': self._summarize_patterns(patterns)
            }

            # Sentiment Analysis
            sentiment = self.analyze_sentiment(symbol)
            results['sentiment_analysis'] = self._serialize_sentiment(sentiment)

            # Risk Assessment
            risk = self.assess_risk(stock_data, symbol)
            results['risk_assessment'] = self._serialize_risk(risk)

            # Price Prediction
            predictions = self.predict_prices(stock_data, indicators_data, selected_indicators)
            results['price_prediction'] = {
                'random_forest': predictions['rf'].__dict__ if predictions['rf'] else None,
                'xgboost': predictions['xgb'].__dict__ if predictions['xgb'] else None,
                'model_comparison': predictions['comparison']
            }

            # Overall AI Score
            results['ai_score'] = self._calculate_ai_score(patterns, sentiment, risk, predictions)

            return results

        except Exception as e:
            raise ExternalServiceException("AIInsightsService", f"Failed to generate insights: {str(e)}")

    def detect_patterns(self, stock_data: pd.DataFrame, indicators_data: Dict) -> List[PatternDetection]:
        """Detect chart patterns and technical analysis patterns"""
        patterns = []

        try:
            # Candlestick Pattern Detection
            patterns.extend(self._detect_candlestick_patterns(stock_data))

            # Technical Indicator Patterns
            patterns.extend(self._detect_indicator_patterns(indicators_data))

            # Price Action Patterns
            patterns.extend(self._detect_price_action_patterns(stock_data))

            # Support and Resistance Patterns
            patterns.extend(self._detect_support_resistance_patterns(stock_data))

            return patterns

        except Exception as e:
            raise ExternalServiceException("PatternRecognition", f"Pattern detection failed: {str(e)}")

    def _detect_candlestick_patterns(self, df: pd.DataFrame) -> List[PatternDetection]:
        """Detect common candlestick patterns"""
        patterns = []

        try:
            # Doji pattern
            for i in range(1, len(df)):
                body_size = abs(df['close'].iloc[i] - df['open'].iloc[i])
                range_size = df['high'].iloc[i] - df['low'].iloc[i]

                if body_size / range_size < 0.1 and range_size > 0:  # Doji
                    patterns.append(PatternDetection(
                        pattern_type=PatternType.CONSOLIDATION,
                        confidence=0.7,
                        description="Doji candlestick pattern detected - market indecision",
                        start_date=df.index[i].isoformat(),
                        end_date=df.index[i].isoformat(),
                        signal_strength=0.6
                    ))

            # Hammer pattern
            for i in range(1, len(df)):
                open_price = df['open'].iloc[i]
                close_price = df['close'].iloc[i]
                high_price = df['high'].iloc[i]
                low_price = df['low'].iloc[i]

                body_size = abs(close_price - open_price)
                lower_shadow = min(open_price, close_price) - low_price
                upper_shadow = high_price - max(open_price, close_price)

                if (lower_shadow > 2 * body_size and
                    upper_shadow < body_size and
                    body_size > 0):  # Hammer
                    patterns.append(PatternDetection(
                        pattern_type=PatternType.BULLISH_REVERSAL,
                        confidence=0.75,
                        description="Hammer pattern detected - potential bullish reversal",
                        start_date=df.index[i].isoformat(),
                        end_date=df.index[i].isoformat(),
                        signal_strength=0.8
                    ))

            return patterns

        except Exception:
            return []

    def _detect_indicator_patterns(self, indicators_data: Dict) -> List[PatternDetection]:
        """Detect patterns in technical indicators"""
        patterns = []

        try:
            # MACD Signal Line Crossover
            if 'MACD' in indicators_data:
                macd_data = indicators_data['MACD']['data']
                for i in range(1, len(macd_data)):
                    current = macd_data[i]
                    previous = macd_data[i-1]

                    if (current.get('macd') and current.get('signal') and
                        previous.get('macd') and previous.get('signal')):

                        if (previous['macd'] < previous['signal'] and
                            current['macd'] > current['signal']):  # Bullish crossover
                            patterns.append(PatternDetection(
                                pattern_type=PatternType.BULLISH_REVERSAL,
                                confidence=0.8,
                                description="MACD bullish crossover detected",
                                start_date=previous['date'],
                                end_date=current['date'],
                                signal_strength=0.85
                            ))

                        elif (previous['macd'] > previous['signal'] and
                              current['macd'] < current['signal']):  # Bearish crossover
                            patterns.append(PatternDetection(
                                pattern_type=PatternType.BEARISH_REVERSAL,
                                confidence=0.8,
                                description="MACD bearish crossover detected",
                                start_date=previous['date'],
                                end_date=current['date'],
                                signal_strength=0.85
                            ))

            # RSI Overbought/Oversold
            if 'RSI' in indicators_data:
                rsi_data = indicators_data['RSI']['data']
                for i in range(len(rsi_data)):
                    rsi_value = rsi_data[i].get('rsi')
                    if rsi_value:
                        if rsi_value > 80:  # Overbought
                            patterns.append(PatternDetection(
                                pattern_type=PatternType.BEARISH_REVERSAL,
                                confidence=0.7,
                                description=f"RSI overbought condition ({rsi_value:.1f})",
                                start_date=rsi_data[i]['date'],
                                end_date=rsi_data[i]['date'],
                                signal_strength=0.75
                            ))
                        elif rsi_value < 20:  # Oversold
                            patterns.append(PatternDetection(
                                pattern_type=PatternType.BULLISH_REVERSAL,
                                confidence=0.7,
                                description=f"RSI oversold condition ({rsi_value:.1f})",
                                start_date=rsi_data[i]['date'],
                                end_date=rsi_data[i]['date'],
                                signal_strength=0.75
                            ))

            return patterns

        except Exception:
            return []

    def _detect_price_action_patterns(self, df: pd.DataFrame) -> List[PatternDetection]:
        """Detect price action patterns like trends and reversals"""
        patterns = []

        try:
            # Calculate moving averages for trend detection
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()

            # Trend Analysis
            recent_data = df.tail(20)
            if len(recent_data) >= 20:
                slope_20, _, r_value_20, _, _ = stats.linregress(
                    range(len(recent_data)), recent_data['close']
                )

                if abs(r_value_20) > 0.7:  # Strong correlation
                    if slope_20 > 0:
                        patterns.append(PatternDetection(
                            pattern_type=PatternType.CONTINUATION,
                            confidence=abs(r_value_20),
                            description="Strong uptrend detected",
                            start_date=recent_data.index[0].isoformat(),
                            end_date=recent_data.index[-1].isoformat(),
                            signal_strength=0.8
                        ))
                    else:
                        patterns.append(PatternDetection(
                            pattern_type=PatternType.CONTINUATION,
                            confidence=abs(r_value_20),
                            description="Strong downtrend detected",
                            start_date=recent_data.index[0].isoformat(),
                            end_date=recent_data.index[-1].isoformat(),
                            signal_strength=0.8
                        ))

            return patterns

        except Exception:
            return []

    def _detect_support_resistance_patterns(self, df: pd.DataFrame) -> List[PatternDetection]:
        """Detect support and resistance levels"""
        patterns = []

        try:
            # Find local maxima and minima
            window = 5
            local_maxima = []
            local_minima = []

            for i in range(window, len(df) - window):
                if all(df['high'].iloc[i] >= df['high'].iloc[i-j] for j in range(1, window+1)) and \
                   all(df['high'].iloc[i] >= df['high'].iloc[i+j] for j in range(1, window+1)):
                    local_maxima.append((i, df['high'].iloc[i]))

                if all(df['low'].iloc[i] <= df['low'].iloc[i-j] for j in range(1, window+1)) and \
                   all(df['low'].iloc[i] <= df['low'].iloc[i+j] for j in range(1, window+1)):
                    local_minima.append((i, df['low'].iloc[i]))

            # Check for breakouts
            current_price = df['close'].iloc[-1]
            recent_high = max([price for _, price in local_maxima[-3:]]) if len(local_maxima) >= 3 else None
            recent_low = min([price for _, price in local_minima[-3:]]) if len(local_minima) >= 3 else None

            if recent_high and current_price > recent_high * 1.02:  # 2% breakout
                patterns.append(PatternDetection(
                    pattern_type=PatternType.BREAKOUT,
                    confidence=0.8,
                    description=f"Resistance breakout above {recent_high:.2f}",
                    start_date=df.index[-5].isoformat(),
                    end_date=df.index[-1].isoformat(),
                    signal_strength=0.9
                ))

            if recent_low and current_price < recent_low * 0.98:  # 2% breakdown
                patterns.append(PatternDetection(
                    pattern_type=PatternType.BREAKOUT,
                    confidence=0.8,
                    description=f"Support breakdown below {recent_low:.2f}",
                    start_date=df.index[-5].isoformat(),
                    end_date=df.index[-1].isoformat(),
                    signal_strength=0.9
                ))

            return patterns

        except Exception:
            return []

    def analyze_sentiment(self, symbol: str) -> SentimentAnalysis:
        """Analyze market sentiment from news and social media"""
        try:
            # Get news headlines (simulated - in production, use news APIs)
            headlines = self._get_news_headlines(symbol)

            if not headlines:
                return SentimentAnalysis(
                    sentiment_type=SentimentType.NEUTRAL,
                    score=0.0,
                    confidence=0.5,
                    news_count=0,
                    summary="No recent news available for sentiment analysis"
                )

            # Analyze sentiment using TextBlob
            total_polarity = 0
            total_subjectivity = 0
            news_count = len(headlines)

            for headline in headlines:
                blob = TextBlob(headline)
                total_polarity += blob.sentiment.polarity
                total_subjectivity += blob.sentiment.subjectivity

            avg_polarity = total_polarity / news_count
            avg_subjectivity = total_subjectivity / news_count

            # Determine sentiment type
            if avg_polarity >= 0.3:
                sentiment_type = SentimentType.VERY_POSITIVE
            elif avg_polarity >= 0.1:
                sentiment_type = SentimentType.POSITIVE
            elif avg_polarity <= -0.3:
                sentiment_type = SentimentType.VERY_NEGATIVE
            elif avg_polarity <= -0.1:
                sentiment_type = SentimentType.NEGATIVE
            else:
                sentiment_type = SentimentType.NEUTRAL

            confidence = min(abs(avg_polarity) + avg_subjectivity, 1.0)

            summary = f"Analysis of {news_count} news items shows {sentiment_type.value} sentiment"

            return SentimentAnalysis(
                sentiment_type=sentiment_type,
                score=avg_polarity,
                confidence=confidence,
                news_count=news_count,
                summary=summary
            )

        except Exception as e:
            return SentimentAnalysis(
                sentiment_type=SentimentType.NEUTRAL,
                score=0.0,
                confidence=0.0,
                news_count=0,
                summary=f"Sentiment analysis failed: {str(e)}"
            )

    def _get_news_headlines(self, symbol: str) -> List[str]:
        """Get news headlines for sentiment analysis (simulated)"""
        # In production, integrate with news APIs like Alpha Vantage, NewsAPI, etc.
        # For demo, return sample headlines
        sample_headlines = [
            f"{symbol} reports strong quarterly earnings",
            f"Analysts upgrade {symbol} price target",
            f"{symbol} announces new strategic partnership",
            f"Market volatility affects {symbol} trading",
            f"{symbol} faces regulatory challenges"
        ]
        return sample_headlines

    def assess_risk(self, stock_data: pd.DataFrame, symbol: str) -> RiskAssessment:
        """Comprehensive risk assessment"""
        try:
            # Calculate returns
            returns = stock_data['close'].pct_change().dropna()

            # Volatility (annualized standard deviation)
            volatility = returns.std() * np.sqrt(252)

            # Value at Risk (95% confidence)
            var_95 = np.percentile(returns, 5)

            # Beta calculation (using market proxy - VN-Index for Vietnamese stocks)
            beta = self._calculate_beta(symbol, returns)

            # Risk factors
            risk_factors = []

            # Volatility risk
            if volatility > 0.4:
                risk_factors.append("High volatility")
            elif volatility > 0.25:
                risk_factors.append("Moderate volatility")

            # Beta risk
            if beta > 1.5:
                risk_factors.append("High market sensitivity")
            elif beta > 1.2:
                risk_factors.append("Above-average market sensitivity")

            # VaR risk
            if var_95 < -0.05:
                risk_factors.append("High downside risk")
            elif var_95 < -0.03:
                risk_factors.append("Moderate downside risk")

            # Calculate overall risk score
            risk_score = (volatility * 0.4 + abs(beta - 1) * 0.3 + abs(var_95) * 10 * 0.3)

            # Determine risk level
            if risk_score > 0.8:
                risk_level = RiskLevel.CRITICAL
            elif risk_score > 0.6:
                risk_level = RiskLevel.HIGH
            elif risk_score > 0.3:
                risk_level = RiskLevel.MEDIUM
            else:
                risk_level = RiskLevel.LOW

            return RiskAssessment(
                risk_level=risk_level,
                risk_score=risk_score,
                volatility=volatility,
                beta=beta,
                var_95=var_95,
                factors=risk_factors
            )

        except Exception as e:
            return RiskAssessment(
                risk_level=RiskLevel.MEDIUM,
                risk_score=0.5,
                volatility=0.0,
                beta=1.0,
                var_95=0.0,
                factors=[f"Risk assessment failed: {str(e)}"]
            )

    def _calculate_beta(self, symbol: str, stock_returns: pd.Series) -> float:
        """Calculate beta coefficient"""
        try:
            # For demo purposes, return a random beta between 0.5 and 2.0
            # In production, calculate against market index
            np.random.seed(hash(symbol) % 1000)
            return np.random.uniform(0.5, 2.0)
        except:
            return 1.0

    def predict_prices(self, stock_data: pd.DataFrame, indicators_data: Dict,
                      selected_indicators: Dict[str, str]) -> Dict[str, Any]:
        """Predict future prices using Random Forest and XGBoost"""
        try:
            # Prepare features from technical indicators
            features_df = self._prepare_features(stock_data, indicators_data, selected_indicators)

            if features_df.empty or len(features_df) < 30:
                return {
                    'rf': None,
                    'xgb': None,
                    'comparison': "Insufficient data for prediction"
                }

            # Prepare target variable (next day's close price)
            target = stock_data['close'].shift(-1).dropna()

            # Align features and target
            min_length = min(len(features_df), len(target))
            features_df = features_df.iloc[:min_length]
            target = target.iloc[:min_length]

            if len(features_df) < 10:
                return {
                    'rf': None,
                    'xgb': None,
                    'comparison': "Insufficient data after alignment"
                }

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                features_df, target, test_size=0.2, shuffle=False
            )

            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)

            # Train Random Forest
            rf_prediction = self._train_random_forest(
                X_train_scaled, X_test_scaled, y_train, y_test, features_df.columns
            )

            # Train XGBoost
            xgb_prediction = self._train_xgboost(
                X_train_scaled, X_test_scaled, y_train, y_test, features_df.columns
            )

            # Model comparison
            comparison = self._compare_models(rf_prediction, xgb_prediction)

            return {
                'rf': rf_prediction,
                'xgb': xgb_prediction,
                'comparison': comparison
            }

        except Exception as e:
            return {
                'rf': None,
                'xgb': None,
                'comparison': f"Prediction failed: {str(e)}"
            }

    def _prepare_features(self, stock_data: pd.DataFrame, indicators_data: Dict,
                         selected_indicators: Dict[str, str]) -> pd.DataFrame:
        """Prepare feature matrix from technical indicators"""
        features = pd.DataFrame(index=stock_data.index)

        # Price-based features
        features['price'] = stock_data['close']
        features['volume'] = stock_data['volume']
        features['high_low_ratio'] = stock_data['high'] / stock_data['low']
        features['price_change'] = stock_data['close'].pct_change()

        # Add selected technical indicators
        for category, indicator_name in selected_indicators.items():
            if indicator_name in indicators_data:
                indicator_data = indicators_data[indicator_name]['data']

                # Convert to DataFrame for easier handling
                indicator_df = pd.DataFrame(indicator_data)
                if 'date' in indicator_df.columns:
                    indicator_df['date'] = pd.to_datetime(indicator_df['date'])
                    indicator_df = indicator_df.set_index('date')

                    # Add all numeric columns from the indicator
                    for col in indicator_df.columns:
                        if indicator_df[col].dtype in ['float64', 'int64']:
                            features[f"{indicator_name}_{col}"] = indicator_df[col]

        # Remove rows with NaN values
        features = features.dropna()

        return features

    def _train_random_forest(self, X_train, X_test, y_train, y_test, feature_names) -> Optional[PricePrediction]:
        """Train Random Forest model"""
        try:
            self.rf_model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )

            self.rf_model.fit(X_train, y_train)
            predictions = self.rf_model.predict(X_test)

            # Calculate metrics
            mse = mean_squared_error(y_test, predictions)
            r2 = r2_score(y_test, predictions)

            # Feature importance
            feature_importance = dict(zip(
                feature_names,
                self.rf_model.feature_importances_
            ))

            # Predict next price
            last_features = X_test[-1].reshape(1, -1)
            next_price = self.rf_model.predict(last_features)[0]

            # Calculate confidence interval (simplified)
            std_error = np.sqrt(mse)
            confidence_interval = (
                next_price - 1.96 * std_error,
                next_price + 1.96 * std_error
            )

            return PricePrediction(
                model_type="Random Forest",
                predicted_price=next_price,
                confidence_interval=confidence_interval,
                accuracy_score=r2,
                feature_importance=feature_importance,
                prediction_date=(datetime.now() + timedelta(days=1)).isoformat()
            )

        except Exception:
            return None

    def _train_xgboost(self, X_train, X_test, y_train, y_test, feature_names) -> Optional[PricePrediction]:
        """Train XGBoost model"""
        try:
            self.xgb_model = xgb.XGBRegressor(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42
            )

            self.xgb_model.fit(X_train, y_train)
            predictions = self.xgb_model.predict(X_test)

            # Calculate metrics
            mse = mean_squared_error(y_test, predictions)
            r2 = r2_score(y_test, predictions)

            # Feature importance
            feature_importance = dict(zip(
                feature_names,
                self.xgb_model.feature_importances_
            ))

            # Predict next price
            last_features = X_test[-1].reshape(1, -1)
            next_price = self.xgb_model.predict(last_features)[0]

            # Calculate confidence interval (simplified)
            std_error = np.sqrt(mse)
            confidence_interval = (
                next_price - 1.96 * std_error,
                next_price + 1.96 * std_error
            )

            return PricePrediction(
                model_type="XGBoost",
                predicted_price=next_price,
                confidence_interval=confidence_interval,
                accuracy_score=r2,
                feature_importance=feature_importance,
                prediction_date=(datetime.now() + timedelta(days=1)).isoformat()
            )

        except Exception:
            return None

    def _compare_models(self, rf_prediction: Optional[PricePrediction],
                       xgb_prediction: Optional[PricePrediction]) -> str:
        """Compare model performances"""
        if not rf_prediction and not xgb_prediction:
            return "Both models failed to generate predictions"
        elif not rf_prediction:
            return "Only XGBoost model succeeded"
        elif not xgb_prediction:
            return "Only Random Forest model succeeded"
        else:
            rf_r2 = rf_prediction.accuracy_score
            xgb_r2 = xgb_prediction.accuracy_score

            if rf_r2 > xgb_r2:
                return f"Random Forest performs better (R²: {rf_r2:.3f} vs {xgb_r2:.3f})"
            elif xgb_r2 > rf_r2:
                return f"XGBoost performs better (R²: {xgb_r2:.3f} vs {rf_r2:.3f})"
            else:
                return f"Both models perform similarly (R²: ~{rf_r2:.3f})"

    def _serialize_pattern(self, pattern: PatternDetection) -> Dict[str, Any]:
        """Serialize PatternDetection object to JSON-compatible dictionary"""
        return {
            'pattern_type': pattern.pattern_type.value,  # Convert enum to string
            'confidence': pattern.confidence,
            'description': pattern.description,
            'start_date': pattern.start_date,
            'end_date': pattern.end_date,
            'signal_strength': pattern.signal_strength
        }

    def _serialize_sentiment(self, sentiment: 'SentimentAnalysis') -> Dict[str, Any]:
        """Serialize SentimentAnalysis object to JSON-compatible dictionary"""
        return {
            'sentiment_type': sentiment.sentiment_type.value,  # Convert enum to string
            'score': sentiment.score,
            'confidence': sentiment.confidence,
            'news_count': sentiment.news_count,
            'summary': sentiment.summary
        }

    def _serialize_risk(self, risk: 'RiskAssessment') -> Dict[str, Any]:
        """Serialize RiskAssessment object to JSON-compatible dictionary"""
        return {
            'risk_level': risk.risk_level.value,  # Convert enum to string
            'risk_score': risk.risk_score,
            'volatility': risk.volatility,
            'beta': risk.beta,
            'var_95': risk.var_95,
            'factors': risk.factors
        }

    def _summarize_patterns(self, patterns: List[PatternDetection]) -> str:
        """Summarize detected patterns"""
        if not patterns:
            return "No significant patterns detected"

        pattern_types = {}
        for pattern in patterns:
            pattern_type = pattern.pattern_type.value
            if pattern_type not in pattern_types:
                pattern_types[pattern_type] = 0
            pattern_types[pattern_type] += 1

        summary_parts = []
        for pattern_type, count in pattern_types.items():
            summary_parts.append(f"{count} {pattern_type.replace('_', ' ')} pattern(s)")

        return f"Detected: {', '.join(summary_parts)}"

    def _calculate_ai_score(self, patterns: List[PatternDetection],
                          sentiment: SentimentAnalysis,
                          risk: RiskAssessment,
                          predictions: Dict) -> Dict[str, Any]:
        """Calculate overall AI confidence score"""
        try:
            # Pattern score (0-100)
            pattern_score = 0
            if patterns:
                bullish_patterns = sum(1 for p in patterns if 'bullish' in p.pattern_type.value)
                bearish_patterns = sum(1 for p in patterns if 'bearish' in p.pattern_type.value)
                avg_confidence = np.mean([p.confidence for p in patterns])

                pattern_score = min(avg_confidence * 100, 100)

            # Sentiment score (0-100)
            sentiment_score = (sentiment.score + 1) * 50  # Convert from -1,1 to 0,100

            # Risk score (inverse - lower risk = higher score)
            risk_score = max(0, 100 - risk.risk_score * 100)

            # Prediction accuracy score
            prediction_score = 0
            if predictions.get('rf') and predictions.get('xgb'):
                rf_score = max(0, predictions['rf'].accuracy_score * 100)
                xgb_score = max(0, predictions['xgb'].accuracy_score * 100)
                prediction_score = (rf_score + xgb_score) / 2
            elif predictions.get('rf'):
                prediction_score = max(0, predictions['rf'].accuracy_score * 100)
            elif predictions.get('xgb'):
                prediction_score = max(0, predictions['xgb'].accuracy_score * 100)

            # Overall weighted score
            overall_score = (
                pattern_score * 0.3 +
                sentiment_score * 0.2 +
                risk_score * 0.2 +
                prediction_score * 0.3
            )

            return {
                'overall_score': round(overall_score, 1),
                'pattern_score': round(pattern_score, 1),
                'sentiment_score': round(sentiment_score, 1),
                'risk_score': round(risk_score, 1),
                'prediction_score': round(prediction_score, 1),
                'confidence_level': 'High' if overall_score > 70 else 'Medium' if overall_score > 40 else 'Low'
            }

        except Exception:
            return {
                'overall_score': 50.0,
                'pattern_score': 50.0,
                'sentiment_score': 50.0,
                'risk_score': 50.0,
                'prediction_score': 50.0,
                'confidence_level': 'Medium'
            }

    def get_available_indicators_by_category(self) -> Dict[str, List[Dict]]:
        """Get available indicators grouped by category for frontend selection"""
        return self.technical_indicators.get_available_indicators()