#!/usr/bin/env python3
"""Standalone training + prediction test script.

Runs OUTSIDE Docker, connects directly to MySQL on port 3309.
Trains a model for solution 1 (FPT, BlockRNN->XGBoost), saves joblib,
then tests the prediction flow.

Usage:
    cd stock_microservices/services/prediction-service
    python scripts/test_training.py
"""
import json
import os
import sys
import time

import joblib
import numpy as np
import pandas as pd
import pymysql
import ta
import xgboost as xgb
import lightgbm as lgb
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

# ── Configuration ──────────────────────────────────────────────
DB_HOST = "127.0.0.1"
DB_PORT = 3309
DB_USER = "root"
DB_PASSWORD = "Mysql_2025"
DB_NAME = "defaultdb"

SOLUTION_ID = 1
MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models")

# ── DARTS -> ML mapping (same as solution_routes.py) ──────────
DARTS_TO_ML_MAP = {
    'BlockRNN': 'xgboost', 'RNNModel': 'lightgbm', 'TCNModel': 'xgboost',
    'TransformerModel': 'lightgbm', 'NBEATSModel': 'random_forest',
    'TFTModel': 'lightgbm', 'NBeats': 'random_forest', 'NHits': 'xgboost',
    'DLinear': 'lightgbm', 'NLinear': 'lightgbm', 'TiDE': 'xgboost',
    'XGBoost': 'xgboost', 'LightGBM': 'lightgbm', 'RandomForest': 'random_forest',
    'CatBoost': 'xgboost', 'LinearRegression': 'linear_regression',
}

INDICATOR_NAME_MAP = {
    'SMA': 'SMA', 'Simple Moving Average': 'SMA',
    'EMA': 'EMA', 'Exponential Moving Average': 'EMA',
    'WMA': 'WMA', 'Weighted Moving Average': 'WMA',
    'MACD': 'MACD', 'RSI': 'RSI', 'Relative Strength Index': 'RSI',
    'STOCH': 'STOCH', 'CCI': 'CCI', 'WILLIAMS_R': 'WILLIAMS_R',
    'ROC': 'ROC', 'BB': 'BB', 'Bollinger Bands': 'BB',
    'ATR': 'ATR', 'Average True Range': 'ATR',
    'KELTNER': 'KELTNER', 'DONCHIAN': 'DONCHIAN',
    'OBV': 'OBV', 'On Balance Volume': 'OBV',
    'MFI': 'MFI', 'Money Flow Index': 'MFI',
    'CMF': 'CMF', 'VOLUME': 'VOLUME', 'VWAP': 'VWAP',
    'STDDEV': 'STDDEV', 'HV': 'HV', 'MOM': 'MOM', 'Momentum Indicator': 'MOM',
    'AD': 'AD', 'ADX': 'ADX', 'Average Directional Index': 'ADX',
    'PSAR': 'PSAR', 'Parabolic SAR': 'PSAR',
}


# ── DB helper ──────────────────────────────────────────────────
def get_connection():
    return pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER,
        password=DB_PASSWORD, database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
    )


def query(sql, params=None):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()
    finally:
        conn.close()


def execute(sql, params=None):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
        conn.commit()
    finally:
        conn.close()


# ── Indicator calculation (same as solution_routes.py) ─────────
def _safe_val(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    if pd.isna(v):
        return None
    return float(v)


def _calculate_indicator(df, code, params):
    result = []
    dates = df.index
    try:
        if code == 'SMA':
            values = ta.trend.SMAIndicator(df['close'], window=params.get('period', 20)).sma_indicator()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'sma': _safe_val(values.iloc[i])})
        elif code == 'EMA':
            values = ta.trend.EMAIndicator(df['close'], window=params.get('period', 20)).ema_indicator()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'ema': _safe_val(values.iloc[i])})
        elif code == 'MACD':
            m = ta.trend.MACD(df['close'], window_fast=params.get('fast_period', 12),
                              window_slow=params.get('slow_period', 26), window_sign=params.get('signal_period', 9))
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(),
                               'macd': _safe_val(m.macd().iloc[i]),
                               'signal': _safe_val(m.macd_signal().iloc[i]),
                               'histogram': _safe_val(m.macd_diff().iloc[i])})
        elif code == 'ADX':
            adx = ta.trend.ADXIndicator(df['high'], df['low'], df['close'], window=params.get('period', 14))
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'adx': _safe_val(adx.adx().iloc[i])})
        elif code == 'RSI':
            values = ta.momentum.RSIIndicator(df['close'], window=params.get('period', 14)).rsi()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'rsi': _safe_val(values.iloc[i])})
        elif code == 'STOCH':
            s = ta.momentum.StochasticOscillator(df['high'], df['low'], df['close'],
                                                  window=params.get('k_period', 14), smooth_window=params.get('d_period', 3))
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(),
                               'stoch_k': _safe_val(s.stoch().iloc[i]),
                               'stoch_d': _safe_val(s.stoch_signal().iloc[i])})
        elif code == 'BB':
            std_val = params.get('std_dev', params.get('std', 2))
            bb = ta.volatility.BollingerBands(df['close'], window=params.get('period', 20), window_dev=std_val)
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(),
                               'bb_upper': _safe_val(bb.bollinger_hband().iloc[i]),
                               'bb_middle': _safe_val(bb.bollinger_mavg().iloc[i]),
                               'bb_lower': _safe_val(bb.bollinger_lband().iloc[i])})
        elif code == 'ATR':
            values = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'],
                                                     window=params.get('period', 14)).average_true_range()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'atr': _safe_val(values.iloc[i])})
        elif code == 'OBV':
            values = ta.volume.OnBalanceVolumeIndicator(df['close'], df['volume']).on_balance_volume()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'obv': _safe_val(values.iloc[i])})
        elif code == 'MFI':
            values = ta.volume.MFIIndicator(df['high'], df['low'], df['close'], df['volume'],
                                             window=params.get('period', 14)).money_flow_index()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'mfi': _safe_val(values.iloc[i])})
        elif code == 'CMF':
            values = ta.volume.ChaikinMoneyFlowIndicator(df['high'], df['low'], df['close'], df['volume'],
                                                          window=params.get('period', 20)).chaikin_money_flow()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'cmf': _safe_val(values.iloc[i])})
        elif code == 'VWAP':
            values = ta.volume.VolumeWeightedAveragePrice(df['high'], df['low'], df['close'], df['volume']).volume_weighted_average_price()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'vwap': _safe_val(values.iloc[i])})
        elif code == 'MOM':
            values = df['close'] - df['close'].shift(params.get('period', 10))
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'mom': _safe_val(values.iloc[i])})
        elif code == 'AD':
            values = ta.volume.AccDistIndexIndicator(df['high'], df['low'], df['close'], df['volume']).acc_dist_index()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'ad': _safe_val(values.iloc[i])})
        elif code == 'VOLUME':
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'volume': float(df['volume'].iloc[i])})
        elif code == 'STDDEV':
            values = df['close'].rolling(window=params.get('period', 20)).std()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'stddev': _safe_val(values.iloc[i])})
        elif code == 'HV':
            log_returns = np.log(df['close'] / df['close'].shift(1))
            values = log_returns.rolling(window=params.get('period', 20)).std() * np.sqrt(252)
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'hv': _safe_val(values.iloc[i])})
        else:
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'value': float(df['close'].iloc[i])})
    except Exception as e:
        print(f"  WARNING: Failed to calculate {code}: {e}")
        for i, d in enumerate(dates):
            result.append({'date': d.isoformat(), 'value': float(df['close'].iloc[i])})
    return result


def _prepare_indicator_features(df, indicator_rows):
    feature_df = pd.DataFrame(index=df.index)
    for row in indicator_rows:
        name = row.get('name', '')
        code = INDICATOR_NAME_MAP.get(name, name)
        params = row.get('parameters')
        if params and isinstance(params, str):
            try:
                params = json.loads(params)
            except (json.JSONDecodeError, TypeError):
                params = {}
        if not params:
            default_params = row.get('default_parameters')
            if default_params and isinstance(default_params, str):
                try:
                    params = json.loads(default_params)
                except (json.JSONDecodeError, TypeError):
                    params = {}
            elif isinstance(default_params, dict):
                params = default_params
            else:
                params = {}

        indicator_data = _calculate_indicator(df, code, params)
        if not indicator_data:
            continue

        ind_df = pd.DataFrame(indicator_data)
        if 'date' in ind_df.columns:
            ind_df['date'] = pd.to_datetime(ind_df['date'])
            ind_df = ind_df.set_index('date')

        for col in ind_df.columns:
            if col != 'date':
                try:
                    feature_df[col] = pd.to_numeric(ind_df[col], errors='coerce')
                except Exception:
                    pass

    return feature_df


def _build_feature_df(df, indicator_feature_df):
    """Build feature DataFrame — same logic as solution_routes.py::_build_feature_df."""
    feature_df = pd.DataFrame(index=df.index)
    feature_df['close'] = df['close']

    feature_df['returns'] = df['close'].pct_change()
    feature_df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
    feature_df['high_low_ratio'] = df['high'] / df['low']
    feature_df['close_open_ratio'] = df['close'] / df['open']

    for lag in [1, 2, 3, 5, 10]:
        feature_df[f'close_lag_{lag}'] = df['close'].shift(lag)
        feature_df[f'returns_lag_{lag}'] = feature_df['returns'].shift(lag)

    feature_df['volatility_5'] = feature_df['returns'].rolling(5).std()
    feature_df['volatility_20'] = feature_df['returns'].rolling(20).std()

    if 'volume' in df.columns:
        feature_df['volume_sma_20'] = df['volume'].rolling(20).mean()
        feature_df['volume_ratio'] = df['volume'] / feature_df['volume_sma_20']

    for col in indicator_feature_df.columns:
        feature_df[col] = indicator_feature_df[col]

    return feature_df


def _create_ml_model(model_type, config_json=None):
    """Create ML model with per-model-type hyperparameters (mirrors solution_routes.py)."""
    ml_type = DARTS_TO_ML_MAP.get(model_type, 'xgboost')

    MODEL_DEFAULTS = {
        # ── XGBoost variants ──
        'XGBoost':          {'n_estimators': 200, 'max_depth': 6,  'learning_rate': 0.10, 'subsample': 0.8, 'colsample_bytree': 0.8},
        'BlockRNN':         {'n_estimators': 300, 'max_depth': 8,  'learning_rate': 0.05, 'subsample': 0.85, 'colsample_bytree': 0.7},
        'TCNModel':         {'n_estimators': 150, 'max_depth': 10, 'learning_rate': 0.08, 'subsample': 0.75, 'colsample_bytree': 0.9},
        'NHits':            {'n_estimators': 500, 'max_depth': 5,  'learning_rate': 0.03, 'subsample': 0.9, 'colsample_bytree': 0.6},
        'TiDE':             {'n_estimators': 100, 'max_depth': 4,  'learning_rate': 0.15, 'subsample': 0.7, 'colsample_bytree': 0.85},
        'CatBoost':         {'n_estimators': 400, 'max_depth': 7,  'learning_rate': 0.04, 'subsample': 0.8, 'colsample_bytree': 0.75},
        # ── LightGBM variants ──
        'LightGBM':         {'n_estimators': 200, 'max_depth': 6,  'learning_rate': 0.10, 'subsample': 0.8, 'colsample_bytree': 0.8, 'num_leaves': 31},
        'RNNModel':         {'n_estimators': 300, 'max_depth': 8,  'learning_rate': 0.05, 'subsample': 0.85, 'colsample_bytree': 0.7, 'num_leaves': 63},
        'TransformerModel': {'n_estimators': 400, 'max_depth': 5,  'learning_rate': 0.03, 'subsample': 0.9, 'colsample_bytree': 0.6, 'num_leaves': 127},
        'TFTModel':         {'n_estimators': 350, 'max_depth': 9,  'learning_rate': 0.04, 'subsample': 0.8, 'colsample_bytree': 0.75, 'num_leaves': 80},
        'DLinear':          {'n_estimators': 100, 'max_depth': 3,  'learning_rate': 0.15, 'subsample': 0.7, 'colsample_bytree': 0.9, 'num_leaves': 15},
        'NLinear':          {'n_estimators': 80,  'max_depth': 2,  'learning_rate': 0.20, 'subsample': 0.7, 'colsample_bytree': 0.95, 'num_leaves': 10},
        # ── RandomForest variants ──
        'RandomForest':     {'n_estimators': 200, 'max_depth': 10, 'min_samples_split': 5,  'min_samples_leaf': 2},
        'NBEATSModel':      {'n_estimators': 400, 'max_depth': 15, 'min_samples_split': 3,  'min_samples_leaf': 1},
        'NBeats':           {'n_estimators': 300, 'max_depth': 12, 'min_samples_split': 4,  'min_samples_leaf': 2},
    }

    defaults = MODEL_DEFAULTS.get(model_type, {})
    user_config = {}
    if config_json:
        try:
            user_config = json.loads(config_json) if isinstance(config_json, str) else config_json
        except (json.JSONDecodeError, TypeError):
            user_config = {}
    cfg = {**defaults, **user_config}

    if ml_type == 'xgboost':
        return xgb.XGBRegressor(
            n_estimators=cfg.get('n_estimators', 200), max_depth=cfg.get('max_depth', 6),
            learning_rate=cfg.get('learning_rate', 0.1), subsample=cfg.get('subsample', 0.8),
            colsample_bytree=cfg.get('colsample_bytree', 0.8), random_state=42, verbosity=0)
    elif ml_type == 'lightgbm':
        return lgb.LGBMRegressor(
            n_estimators=cfg.get('n_estimators', 200), max_depth=cfg.get('max_depth', 6),
            learning_rate=cfg.get('learning_rate', 0.1), num_leaves=cfg.get('num_leaves', 31),
            subsample=cfg.get('subsample', 0.8), colsample_bytree=cfg.get('colsample_bytree', 0.8),
            random_state=42, verbose=-1)
    elif ml_type == 'random_forest':
        return RandomForestRegressor(
            n_estimators=cfg.get('n_estimators', 200), max_depth=cfg.get('max_depth', 10),
            min_samples_split=cfg.get('min_samples_split', 5), min_samples_leaf=cfg.get('min_samples_leaf', 2),
            random_state=42, n_jobs=-1)
    else:
        return LinearRegression()


# ── Main ───────────────────────────────────────────────────────
def main():
    print("=" * 70)
    print("  STANDALONE TRAINING + PREDICTION TEST")
    print("=" * 70)

    # 1. Load solution
    print("\n[1] Loading solution data...")
    solutions = query("SELECT * FROM tbl_solution WHERE id = %s", (SOLUTION_ID,))
    if not solutions:
        print(f"ERROR: Solution {SOLUTION_ID} not found")
        sys.exit(1)
    sol = solutions[0]
    ticker = sol['ticker']
    model_id = sol['model_id']
    print(f"  Solution: {sol['solution_name']}, ticker={ticker}, model_id={model_id}")

    # 2. Load model instance
    print("\n[2] Loading model instance...")
    models = query("SELECT * FROM model_instances WHERE id = %s", (model_id,))
    if not models:
        print(f"ERROR: Model instance {model_id} not found")
        sys.exit(1)
    mi = models[0]
    model_type = mi['model_type']
    ml_type = DARTS_TO_ML_MAP.get(model_type, 'xgboost')
    print(f"  Model: {mi['model_name']}, type={model_type} -> ML={ml_type}")

    # 3. Load indicators
    print("\n[3] Loading solution indicators...")
    indicator_rows = query("""
        SELECT si.indicator_id, si.indicator_category, si.covariate_type, si.parameters,
               ti.name, ti.type, ti.default_parameters, ti.calculation_function
        FROM solution_indicators si
        LEFT JOIN technical_indicators ti ON si.indicator_id = ti.id
        WHERE si.solution_id = %s
    """, (SOLUTION_ID,))
    print(f"  Found {len(indicator_rows)} indicators:")
    for r in indicator_rows:
        print(f"    - {r['name']} ({r['indicator_category']})")

    # 4. Fetch stock prices directly from MySQL
    print(f"\n[4] Fetching price data for {ticker}...")
    prices = query("""
        SELECT sp.date, sp.open, sp.high, sp.low, sp.close, sp.volume
        FROM stock_prices sp
        JOIN companies c ON sp.company_id = c.id
        WHERE c.symbol = %s
        ORDER BY sp.date ASC
    """, (ticker,))
    if not prices:
        print(f"ERROR: No price data for {ticker}")
        sys.exit(1)
    print(f"  Loaded {len(prices)} price records")

    df = pd.DataFrame(prices)
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date').sort_index()
    df = df[['open', 'high', 'low', 'close', 'volume']].copy()
    df = df.apply(pd.to_numeric, errors='coerce')
    df = df.dropna()
    print(f"  Date range: {df.index[0].date()} to {df.index[-1].date()}")
    print(f"  Rows after cleaning: {len(df)}")

    # 5. Calculate indicator features
    print("\n[5] Calculating technical indicators...")
    indicator_feature_df = _prepare_indicator_features(df, indicator_rows)
    print(f"  Indicator columns: {list(indicator_feature_df.columns)}")

    # 6. Build features
    print("\n[6] Building feature DataFrame...")
    feature_df = _build_feature_df(df, indicator_feature_df)
    feature_df['target'] = feature_df['close'].shift(-1)
    feature_df = feature_df.dropna()
    print(f"  Feature columns: {len(feature_df.columns) - 2}")  # minus close, target
    print(f"  Usable rows: {len(feature_df)}")

    if len(feature_df) < 30:
        print(f"ERROR: Not enough data ({len(feature_df)} < 30)")
        sys.exit(1)

    # 7. Train/val split
    train_ratio = float(sol.get('train_validation_ratio') or 0.8)
    feature_cols = [col for col in feature_df.columns if col not in ['close', 'target']]
    X = feature_df[feature_cols].values
    y = feature_df['target'].values

    split_idx = int(len(X) * train_ratio)
    X_train, X_val = X[:split_idx], X[split_idx:]
    y_train, y_val = y[:split_idx], y[split_idx:]
    print(f"\n[7] Split: {len(X_train)} train, {len(X_val)} val, ratio={train_ratio}")

    # 8. Train model
    print(f"\n[8] Training {ml_type} model...")
    t0 = time.time()
    ml_model = _create_ml_model(model_type, mi.get('config_json'))
    ml_model.fit(X_train, y_train)
    elapsed = time.time() - t0
    print(f"  Training took {elapsed:.2f}s")

    # 9. Evaluate
    print("\n[9] Evaluating model...")
    y_pred_val = ml_model.predict(X_val)
    rmse = float(np.sqrt(mean_squared_error(y_val, y_pred_val)))
    mae = float(mean_absolute_error(y_val, y_pred_val))
    r2 = float(r2_score(y_val, y_pred_val))

    actual_dir = np.sign(y_val[1:] - y_val[:-1])
    pred_dir = np.sign(y_pred_val[1:] - y_pred_val[:-1])
    direction_accuracy = float(np.mean(actual_dir == pred_dir) * 100)

    print(f"  RMSE:     {rmse:.4f}")
    print(f"  MAE:      {mae:.4f}")
    print(f"  R2:       {r2:.4f}")
    print(f"  Dir Acc:  {direction_accuracy:.1f}%")

    # 10. Save model
    os.makedirs(MODEL_DIR, exist_ok=True)
    model_file = os.path.join(MODEL_DIR, f"solution_{SOLUTION_ID}_model.joblib")
    print(f"\n[10] Saving model to {model_file}...")
    from datetime import datetime
    joblib.dump({
        'model': ml_model,
        'feature_cols': feature_cols,
        'model_type': model_type,
        'ml_type': ml_type,
        'ticker': ticker,
        'trained_at': datetime.now().isoformat(),
    }, model_file)
    file_size = os.path.getsize(model_file)
    print(f"  Saved ({file_size / 1024:.1f} KB)")

    # 11. Update DB
    print("\n[11] Updating database...")
    metrics_json = json.dumps({
        'rmse': rmse, 'mae': mae, 'r2': r2,
        'direction_accuracy': direction_accuracy,
        'training_samples': int(len(X_train)),
        'validation_samples': int(len(X_val)),
        'features_used': len(feature_cols),
    })
    execute("""
        UPDATE model_instances
        SET status='trained', file_path=%s,
            training_metrics_json=%s, last_training_date=NOW()
        WHERE id = %s
    """, (model_file, metrics_json, model_id))
    execute("""
        UPDATE tbl_solution
        SET train_status='trained', solution_status=1
        WHERE id = %s
    """, (SOLUTION_ID,))
    print("  DB updated.")

    # 12. Verify: reload model and predict
    print("\n[12] Verification: reload model and predict on validation data...")
    saved = joblib.load(model_file)
    loaded_model = saved['model']
    loaded_feature_cols = saved['feature_cols']
    assert loaded_feature_cols == feature_cols, "Feature columns mismatch!"

    y_verify = loaded_model.predict(X_val)
    verify_rmse = float(np.sqrt(mean_squared_error(y_val, y_verify)))
    print(f"  Reloaded model RMSE: {verify_rmse:.4f} (should match {rmse:.4f})")
    assert abs(verify_rmse - rmse) < 1e-6, "Reloaded model produces different results!"
    print("  PASS: Model loads and predicts correctly.")

    # 13. Test prediction flow on recent data
    print("\n[13] Testing future prediction flow...")
    last_close = float(df['close'].iloc[-1])
    future_df = df.copy()
    future_preds = []

    for day_i in range(5):
        next_date = future_df.index[-1] + pd.Timedelta(days=1)
        while next_date.weekday() >= 5:
            next_date += pd.Timedelta(days=1)

        new_row = pd.DataFrame({
            'open': [last_close], 'high': [last_close * 1.005],
            'low': [last_close * 0.995], 'close': [last_close],
            'volume': [float(future_df['volume'].tail(5).mean())],
        }, index=[next_date])
        future_df = pd.concat([future_df, new_row])

        ind_feat = _prepare_indicator_features(future_df, indicator_rows)
        feat = _build_feature_df(future_df, ind_feat)
        feat = feat.dropna()

        if next_date not in feat.index:
            print(f"  Day {day_i+1}: skipped (NaN features)")
            continue

        for c in feature_cols:
            if c not in feat.columns:
                feat[c] = 0.0

        x_next = feat.loc[[next_date], feature_cols].values
        pred_price = float(loaded_model.predict(x_next)[0])

        future_df.loc[next_date, 'close'] = pred_price
        future_df.loc[next_date, 'open'] = pred_price
        future_df.loc[next_date, 'high'] = pred_price * 1.005
        future_df.loc[next_date, 'low'] = pred_price * 0.995

        future_preds.append((next_date.strftime('%Y-%m-%d'), pred_price))
        last_close = pred_price

    print(f"\n  Last actual close: {float(df['close'].iloc[-1]):.2f} on {df.index[-1].date()}")
    print("  Future predictions:")
    for date_str, price in future_preds:
        print(f"    {date_str}: {price:.2f}")

    print("\n" + "=" * 70)
    print("  ALL TESTS PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()
