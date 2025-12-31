# Database Schema Redesign Documentation

## Overview

This document describes the redesigned database schema for the stock prediction system. The new schema simplifies and clarifies the relationship between solutions, models, and technical indicators.

**Date**: 2025-10-09
**Migration Script**: `migrations/001_improve_prediction_schema.sql`

---

## Problems with Old Schema

1. **Confusing Abstraction**: `tbl_time_series` + `time_series_solution` created unnecessary complexity
2. **Mixed Approaches**: Solutions could use EITHER time_series OR indicators (dual-path logic)
3. **Unclear Relationships**: Direct data fields (High, Open, Low, Volume) mixed with indicators
4. **Missing Features**:
   - No covariate type specification (past/future)
   - No train/validation ratio configuration
   - No indicator category enforcement

---

## New Schema Design

### Core Principles

1. **One Solution = One Model + One Ticker + Four Indicators**
2. **Clear Categories**: Each solution must have exactly one indicator from each category (trend, momentum, volatility, volume)
3. **Flexible Parameters**: Custom parameters per solution without affecting templates
4. **Explicit Covariate Types**: Each indicator specifies if it's past, future, or both
5. **Training Configuration**: Store train/validation ratio with solution

---

## Database Tables

### 1. `technical_indicators` (Template Library)

Template library of available technical indicators.

```sql
CREATE TABLE technical_indicators (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL,
    type ENUM('trend', 'momentum', 'volatility', 'volume') NOT NULL,
    description TEXT,
    calculation_function VARCHAR(100),
    default_parameters JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

**Fields**:
- `id`: Primary key
- `name`: Indicator name (e.g., 'MACD', 'RSI', 'ATR', 'OBV')
- `type`: Category - one of 'trend', 'momentum', 'volatility', 'volume'
- `description`: Human-readable description
- `calculation_function`: Function name for calculation
- `default_parameters`: JSON with default parameter values
- `created_at`, `updated_at`: Timestamps

**Examples**:
```sql
INSERT INTO technical_indicators (name, type, description, default_parameters) VALUES
('MACD', 'trend', 'Moving Average Convergence Divergence', '{"fast_period": 12, "slow_period": 26, "signal_period": 9}'),
('RSI', 'momentum', 'Relative Strength Index', '{"period": 14}'),
('ATR', 'volatility', 'Average True Range', '{"period": 14}'),
('OBV', 'volume', 'On Balance Volume', '{}');
```

---

### 2. `tbl_model` (Models)

Machine learning models with covariate support flags.

```sql
CREATE TABLE tbl_model (
    id INT PRIMARY KEY AUTO_INCREMENT,
    model_name VARCHAR(100) NOT NULL,
    model_type ENUM('RNN', 'LSTM', 'XGBoost') NOT NULL,
    past_covariate TINYINT(1) DEFAULT 0 COMMENT 'Model supports past covariates',
    future_covariate TINYINT(1) DEFAULT 0 COMMENT 'Model supports future covariates',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

**Fields**:
- `id`: Primary key
- `model_name`: Descriptive model name
- `model_type`: One of 'RNN', 'LSTM', 'XGBoost'
- `past_covariate`: 1 if model supports past covariates, 0 otherwise
- `future_covariate`: 1 if model supports future covariates, 0 otherwise

**Examples**:
```sql
INSERT INTO tbl_model (model_name, model_type, past_covariate, future_covariate) VALUES
('LSTM Basic', 'LSTM', 1, 0),
('LSTM Advanced', 'LSTM', 1, 1),
('XGBoost', 'XGBoost', 1, 0);
```

---

### 3. `tbl_solution` (Solutions)

Prediction solutions combining model, ticker, and indicators.

```sql
CREATE TABLE tbl_solution (
    id INT PRIMARY KEY AUTO_INCREMENT,
    solution_name VARCHAR(200) NOT NULL,
    model_id INT NOT NULL,
    ticker VARCHAR(20) NOT NULL COMMENT 'Stock symbol (e.g., TCB, FPT, ICT)',
    status TINYINT DEFAULT 1,
    solution_status INT DEFAULT 0 COMMENT '0=not trained, 1=training, 2=trained, 3=error',
    start_training_date DATE COMMENT 'Training period start',
    end_training_date DATE COMMENT 'Training period end',
    train_validation_ratio DECIMAL(3,2) DEFAULT 0.80 COMMENT 'Train/validation split (e.g., 0.80 = 80% train)',
    created_date DATETIME,
    created_by VARCHAR(100),
    updated_date DATETIME,
    updated_by VARCHAR(100),
    FOREIGN KEY (model_id) REFERENCES tbl_model(id)
);
```

**Fields**:
- `id`: Primary key
- `solution_name`: Descriptive solution name
- `model_id`: Foreign key to tbl_model
- `ticker`: Stock symbol (e.g., 'TCB', 'FPT', 'ICT')
- `status`: Active/inactive flag
- `solution_status`: Training status (0=not trained, 1=training, 2=trained, 3=error)
- `start_training_date`: Training period start
- `end_training_date`: Training period end
- `train_validation_ratio`: Split ratio (default 0.80 = 80% train, 20% validation)
- `created_date`, `created_by`, `updated_date`, `updated_by`: Audit fields

**Example**:
```sql
INSERT INTO tbl_solution
(solution_name, model_id, ticker, start_training_date, end_training_date, train_validation_ratio, created_date, created_by)
VALUES
('TCB LSTM Prediction', 2, 'TCB', '2024-01-01', '2024-12-31', 0.80, NOW(), 'admin');
```

---

### 4. `solution_indicators` (Solution-Indicator Mapping)

Links solutions to indicators with custom parameters and covariate types.

```sql
CREATE TABLE solution_indicators (
    id INT PRIMARY KEY AUTO_INCREMENT,
    solution_id INT NOT NULL,
    indicator_id INT NOT NULL,
    indicator_category ENUM('trend', 'momentum', 'volatility', 'volume') NOT NULL COMMENT 'One per category required',
    covariate_type ENUM('past', 'future', 'both') DEFAULT 'past' COMMENT 'Past covariate, future covariate, or both',
    parameters JSON COMMENT 'Custom parameters (overrides template defaults)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (solution_id) REFERENCES tbl_solution(id) ON DELETE CASCADE,
    FOREIGN KEY (indicator_id) REFERENCES technical_indicators(id),
    UNIQUE KEY unique_solution_indicator_category (solution_id, indicator_category)
);
```

**Fields**:
- `id`: Primary key
- `solution_id`: Foreign key to tbl_solution
- `indicator_id`: Foreign key to technical_indicators
- `indicator_category`: One of 'trend', 'momentum', 'volatility', 'volume'
- `covariate_type`: 'past', 'future', or 'both'
- `parameters`: JSON with custom parameters (overrides template defaults)
- `created_at`, `updated_at`: Timestamps

**Constraints**:
- `UNIQUE (solution_id, indicator_category)`: Ensures exactly one indicator per category per solution
- `FOREIGN KEY CASCADE`: Deletes indicators when solution is deleted

**Example**:
```sql
-- Solution 1 with 4 indicators
INSERT INTO solution_indicators (solution_id, indicator_id, indicator_category, covariate_type, parameters) VALUES
(1, 1, 'trend', 'past', '{"fast_period": 10, "slow_period": 20, "signal_period": 7}'),  -- MACD
(1, 2, 'momentum', 'past', '{"period": 10}'),  -- RSI
(1, 3, 'volatility', 'past', NULL),  -- ATR with default params
(1, 4, 'volume', 'past', NULL);  -- OBV with default params
```

---

## Deprecated Tables

These tables are deprecated and will be removed in a future version:

### `tbl_time_series` (DEPRECATED)
- **Status**: Deprecated
- **Replacement**: Use `solution_indicators` instead
- **Migration Path**: Existing solutions should be migrated to use indicators

### `time_series_solution` (DEPRECATED)
- **Status**: Deprecated
- **Replacement**: Use `solution_indicators` with `covariate_type` field
- **Migration Path**: Convert time_series references to indicator references

---

## Database Views

### `v_solution_complete`

Complete solution details with all indicators in a single row.

```sql
SELECT * FROM v_solution_complete WHERE solution_id = 1;
```

**Returns**:
- Solution details (id, name, ticker, status, dates, ratio)
- Model details (id, name, type, supports_past, supports_future)
- All 4 indicators with names, covariate types, and parameters

### `v_solution_validation`

Solution configuration status validation.

```sql
SELECT * FROM v_solution_validation WHERE configuration_status != 'COMPLETE';
```

**Returns**:
- `solution_id`, `solution_name`, `ticker`
- `configured_indicators`: Count of configured indicators (should be 4)
- `has_trend`, `has_momentum`, `has_volatility`, `has_volume`: Boolean flags
- `configuration_status`: 'COMPLETE', 'INCOMPLETE', or 'NOT_CONFIGURED'

---

## API Changes

### Solution APIs

#### Create Solution
```http
POST /api/solutions
Content-Type: application/json

{
    "solution_name": "TCB LSTM Prediction",
    "model_id": 2,
    "ticker": "TCB",
    "start_training_date": "2024-01-01",
    "end_training_date": "2024-12-31",
    "train_validation_ratio": 0.80,
    "created_date": "2025-01-09T10:00:00",
    "created_by": "admin"
}
```

**Response**: `{ "id": 1 }`

**Note**: Indicators are added separately (see below)

---

#### Update Solution
```http
PUT /api/solutions
Content-Type: application/json

{
    "id": 1,
    "solution_name": "TCB LSTM Prediction v2",
    "model_id": 2,
    "ticker": "TCB",
    "start_training_date": "2024-01-01",
    "end_training_date": "2024-12-31",
    "train_validation_ratio": 0.85,
    "updated_date": "2025-01-09T11:00:00",
    "updated_by": "admin"
}
```

---

### Indicator APIs

#### Get All Indicators (Grouped by Category)
```http
GET /api/indicators

Response:
{
    "trend": [
        {"id": 1, "name": "MACD", "type": "trend", "description": "...", "default_parameters": {...}},
        {"id": 5, "name": "EMA", "type": "trend", "description": "...", "default_parameters": {...}}
    ],
    "momentum": [...],
    "volatility": [...],
    "volume": [...]
}
```

---

#### Get Indicators by Type
```http
GET /api/indicators/type/trend

Response:
[
    {"id": 1, "name": "MACD", "type": "trend", "description": "...", "default_parameters": {...}},
    {"id": 5, "name": "EMA", "type": "trend", "description": "...", "default_parameters": {...}}
]
```

---

#### Get Solution Indicators
```http
GET /api/solutions/1/indicators

Response:
{
    "trend": {
        "id": 1,
        "name": "MACD",
        "description": "...",
        "covariate_type": "past",
        "parameters": {"fast_period": 10, "slow_period": 20, "signal_period": 7}
    },
    "momentum": {
        "id": 2,
        "name": "RSI",
        "description": "...",
        "covariate_type": "past",
        "parameters": {"period": 10}
    },
    "volatility": {...},
    "volume": {...}
}
```

---

#### Add Single Indicator to Solution
```http
POST /api/solutions/1/indicators
Content-Type: application/json

{
    "indicator_id": 1,
    "indicator_category": "trend",
    "covariate_type": "past",
    "parameters": {
        "fast_period": 10,
        "slow_period": 20,
        "signal_period": 7
    }
}
```

**Response**: `{ "id": 10 }`

---

#### Set All Indicators at Once
```http
POST /api/solutions/1/indicators/set
Content-Type: application/json

{
    "trend_indicator": {
        "id": 1,
        "covariate_type": "past",
        "parameters": {"fast_period": 10, "slow_period": 20, "signal_period": 7}
    },
    "momentum_indicator": {
        "id": 2,
        "covariate_type": "past",
        "parameters": {"period": 10}
    },
    "volatility_indicator": {
        "id": 3,
        "covariate_type": "past",
        "parameters": null
    },
    "volume_indicator": {
        "id": 4,
        "covariate_type": "past",
        "parameters": null
    }
}
```

**Notes**:
- Clears existing indicators and replaces with new configuration
- `covariate_type` options: 'past', 'future', 'both'
- `parameters`: null uses template defaults, custom object overrides

---

#### Validate Solution Indicators
```http
GET /api/solutions/1/indicators/validate

Response:
{
    "is_valid": true,
    "missing_types": [],
    "configured_types": ["trend", "momentum", "volatility", "volume"]
}
```

---

## Migration Steps

### 1. Run SQL Migration

```bash
mysql -h stock-tuanph1970db.h.aivencloud.com \
      -u avnadmin \
      -p \
      -P 25021 \
      defaultdb < migrations/001_improve_prediction_schema.sql
```

### 2. Verify Migration

```sql
-- Check solution_indicators structure
DESCRIBE solution_indicators;

-- Check for incomplete solutions
SELECT * FROM v_solution_validation WHERE configuration_status != 'COMPLETE';

-- Validate a solution
CALL sp_validate_solution_indicators(1);
```

### 3. Update Application Code

All code updates are already included in the repository:
- ✅ Repository layer updated
- ✅ Service layer updated
- ✅ API endpoints updated
- ✅ Backward compatibility maintained

### 4. Test APIs

```bash
# Test getting indicators
curl http://localhost:8000/api/indicators

# Test creating solution
curl -X POST http://localhost:8000/api/solutions \
  -H "Content-Type: application/json" \
  -d '{"solution_name": "Test Solution", "model_id": 1, "ticker": "TCB", ...}'

# Test setting indicators
curl -X POST http://localhost:8000/api/solutions/1/indicators/set \
  -H "Content-Type: application/json" \
  -d '{"trend_indicator": {...}, "momentum_indicator": {...}, ...}'
```

---

## Key Benefits

### 1. **Simplified Architecture**
- Removed confusing time_series abstraction
- Clear one-to-one-to-four relationship (Solution → Model → 4 Indicators)
- No more dual-path logic (always uses indicators now)

### 2. **Better Data Integrity**
- UNIQUE constraint ensures exactly one indicator per category
- CHECK constraint validates indicator category matches template type
- CASCADE delete prevents orphaned records

### 3. **Enhanced Flexibility**
- Custom parameters per solution without affecting templates
- Explicit covariate type configuration (past/future/both)
- Configurable train/validation ratio

### 4. **Improved Maintainability**
- Separation of concerns (repositories, services, views)
- Clear API contracts with proper documentation
- Database views for easy querying

### 5. **Backward Compatibility**
- Old time_series tables kept temporarily
- API accepts both old and new field names
- Gradual migration path

---

## Example Workflow

### Complete Solution Setup

```python
# 1. Create solution
solution_data = {
    "solution_name": "TCB LSTM Prediction",
    "model_id": 2,
    "ticker": "TCB",
    "start_training_date": "2024-01-01",
    "end_training_date": "2024-12-31",
    "train_validation_ratio": 0.80,
    "created_date": "2025-01-09T10:00:00",
    "created_by": "admin"
}
response = requests.post("http://api/solutions", json=solution_data)
solution_id = response.json()["id"]

# 2. Set all indicators
indicators_data = {
    "trend_indicator": {
        "id": 1,  # MACD
        "covariate_type": "past",
        "parameters": {"fast_period": 10, "slow_period": 20, "signal_period": 7}
    },
    "momentum_indicator": {
        "id": 2,  # RSI
        "covariate_type": "past",
        "parameters": {"period": 10}
    },
    "volatility_indicator": {
        "id": 3,  # ATR
        "covariate_type": "past",
        "parameters": None  # Use defaults
    },
    "volume_indicator": {
        "id": 4,  # OBV
        "covariate_type": "past",
        "parameters": None  # Use defaults
    }
}
response = requests.post(f"http://api/solutions/{solution_id}/indicators/set", json=indicators_data)

# 3. Validate configuration
response = requests.get(f"http://api/solutions/{solution_id}/indicators/validate")
validation = response.json()
assert validation["is_valid"] == True

# 4. Train solution
train_data = {
    "id": solution_id,
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "validation": True,
    "train_ratio": 0.80
}
response = requests.post("http://api/solutions/train", json=train_data)

# 5. Make predictions
predict_data = {
    "id": solution_id,
    "start_date": "2025-01-01",
    "end_date": "2025-01-31"
}
response = requests.post("http://api/solutions/predict", json=predict_data)
predictions = response.json()
```

---

## Troubleshooting

### Issue: UNIQUE constraint violation

**Problem**: Trying to add multiple indicators of the same category to a solution.

**Solution**: Each solution can have only ONE indicator per category. Update the existing indicator instead:

```http
PUT /api/solutions/1/indicators/2
{"parameters": {"period": 15}}
```

Or clear all indicators and set new ones:

```http
POST /api/solutions/1/indicators/set
{...}
```

---

### Issue: Solution validation fails

**Problem**: `is_valid: false` when validating solution indicators.

**Solution**: Check which categories are missing:

```http
GET /api/solutions/1/indicators/validate

Response:
{
    "is_valid": false,
    "missing_types": ["volume"],
    "configured_types": ["trend", "momentum", "volatility"]
}
```

Add the missing indicator:

```http
POST /api/solutions/1/indicators
{
    "indicator_id": 4,
    "indicator_category": "volume",
    "covariate_type": "past"
}
```

---

### Issue: Model doesn't support covariate type

**Problem**: Setting `covariate_type: 'future'` but model doesn't support future covariates.

**Solution**: Check model capabilities first:

```http
GET /api/solutions/models

Response:
[
    {"id": 1, "model_name": "LSTM Basic", "past_covariate": 1, "future_covariate": 0},
    {"id": 2, "model_name": "LSTM Advanced", "past_covariate": 1, "future_covariate": 1}
]
```

Choose a model that supports the required covariate types.

---

## Future Enhancements

1. **Auto-suggest Indicators**: ML-based indicator recommendations
2. **Parameter Optimization**: Auto-tune indicator parameters
3. **Multi-target Prediction**: Predict multiple targets (High, Low, Close)
4. **Ensemble Models**: Combine multiple solutions
5. **Real-time Updates**: Live indicator calculations
6. **Backtesting Framework**: Historical performance evaluation

---

## Support

For questions or issues:
- Check this documentation first
- Review migration script: `migrations/001_improve_prediction_schema.sql`
- Review API examples in this document
- Contact: admin@yourcompany.com
