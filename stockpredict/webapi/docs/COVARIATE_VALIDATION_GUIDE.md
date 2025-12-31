# Covariate Type Validation Guide

## Overview

This guide explains the **covariate type validation system** that ensures indicators are only configured with covariate types supported by the solution's selected model.

**Key Constraint**: Each model has capabilities flags (`past_covariate`, `future_covariate`), and indicators must be configured with compatible `covariate_type` values.

---

## Model Covariate Capabilities

### Model Support Matrix

| Model | past_covariate | future_covariate | Supported covariate_type |
|-------|----------------|------------------|-------------------------|
| LSTM Basic | 1 | 0 | 'past' only |
| LSTM Advanced | 1 | 1 | 'past', 'future', 'both' |
| RNN Simple | 1 | 0 | 'past' only |
| XGBoost | 1 | 0 | 'past' only |

### Covariate Type Options

- **`past`**: Historical data features (e.g., past MACD values)
- **`future`**: Known future events (e.g., scheduled earnings dates, holidays)
- **`both`**: Feature available in both historical and future contexts

---

## Validation Layers

### 1. Application Layer (Service)

**Location**: `services/indicator_service.py`

**Method**: `_validate_covariate_compatibility()`

**When**: Before adding/updating solution indicators

**Example**:
```python
# This will RAISE ValidationException if incompatible
indicator_service.add_solution_indicator({
    'solution_id': 1,
    'indicator_id': 2,
    'indicator_category': 'momentum',
    'covariate_type': 'future',  # ← Validated against model
    'parameters': {'period': 10}
})
```

**Error Message**:
```
ValidationException: Model 'LSTM Basic' does not support future covariates. Cannot set covariate_type='future'.
```

---

### 2. Database Layer (Triggers)

**Location**: `migrations/002_add_covariate_validation.sql`

**Triggers**:
- `trg_solution_indicators_before_insert`
- `trg_solution_indicators_before_update`

**When**: Before INSERT/UPDATE on `solution_indicators` table

**Example**:
```sql
-- This will FAIL with SQL error
INSERT INTO solution_indicators (solution_id, indicator_id, indicator_category, covariate_type)
VALUES (1, 2, 'momentum', 'future');

-- Error 1644: Covariate type "future" is incompatible with model "LSTM Basic".
-- Check model past_covariate and future_covariate capabilities.
```

---

## API Usage

### Check Model Compatibility

**Before** setting indicators, check what covariate types are supported:

```http
GET /api/predict/solution/1/covariate-compatibility/

Response:
{
    "solution_id": 1,
    "solution_name": "TCB LSTM Prediction",
    "model_id": 1,
    "model_name": "LSTM Basic",
    "model_capabilities": {
        "supports_past_covariates": true,
        "supports_future_covariates": false
    },
    "compatible_covariate_types": ["past"],
    "recommendations": {
        "past": "Use for historical data features",
        "future": "Not supported by this model",
        "both": "Not supported by this model"
    }
}
```

---

### Add Indicator with Validation

```http
POST /api/predict/solution/1/indicators/add/
Content-Type: application/json

{
    "indicator_id": 2,
    "indicator_category": "momentum",
    "covariate_type": "past",  # ← Must be compatible with model
    "parameters": {"period": 10}
}
```

**Success Response** (200 OK):
```json
{
    "id": 10
}
```

**Error Response** (400 Bad Request):
```json
{
    "error": "Model 'LSTM Basic' does not support future covariates. Cannot set covariate_type='future'."
}
```

---

### Set All Indicators

```http
POST /api/predict/solution/1/indicators/set/
Content-Type: application/json

{
    "trend_indicator": {
        "id": 1,
        "covariate_type": "past",  # ← Validated
        "parameters": {"fast_period": 10}
    },
    "momentum_indicator": {
        "id": 2,
        "covariate_type": "past",  # ← Validated
        "parameters": {"period": 10}
    },
    "volatility_indicator": {
        "id": 3,
        "covariate_type": "past",  # ← Validated
        "parameters": null
    },
    "volume_indicator": {
        "id": 4,
        "covariate_type": "past",  # ← Validated
        "parameters": null
    }
}
```

---

## Validation Rules

### Validation Logic

```python
def validate_covariate_type(model, covariate_type):
    """
    Returns True if covariate_type is compatible with model
    """
    supports_past = model['past_covariate'] == 1
    supports_future = model['future_covariate'] == 1

    if covariate_type == 'past':
        return supports_past

    elif covariate_type == 'future':
        return supports_future

    elif covariate_type == 'both':
        return supports_past and supports_future

    else:
        return False  # Invalid covariate_type
```

### Validation Matrix

| Model Capabilities | Valid covariate_type |
|-------------------|---------------------|
| past=0, future=0 | ❌ None (model unusable) |
| past=1, future=0 | ✅ 'past' only |
| past=0, future=1 | ✅ 'future' only |
| past=1, future=1 | ✅ 'past', 'future', 'both' |

---

## Database Validation Functions

### Function: `validate_covariate_compatibility()`

```sql
SELECT validate_covariate_compatibility(1, 'past') AS is_valid;
-- Returns: 1 (TRUE) if compatible, 0 (FALSE) if not

SELECT validate_covariate_compatibility(1, 'future') AS is_valid;
-- Returns: 0 (FALSE) if model doesn't support future covariates
```

### Stored Procedure: `sp_check_solution_covariate_compatibility()`

Check all indicators for a solution:

```sql
CALL sp_check_solution_covariate_compatibility(1);
```

**Output**:
```
+-----+--------+----------+--------------+-------------------+
| id  | name   | category | covariate    | compatibility     |
+-----+--------+----------+--------------+-------------------+
| 10  | MACD   | trend    | past         | VALID             |
| 11  | RSI    | momentum | past         | VALID             |
| 12  | ATR    | volatility| past        | VALID             |
| 13  | OBV    | volume   | past         | VALID             |
+-----+--------+----------+--------------+-------------------+
```

### View: `v_covariate_compatibility_audit`

Query for all solutions with incompatible configurations:

```sql
SELECT *
FROM v_covariate_compatibility_audit
WHERE compatibility_status = 'INVALID';
```

---

## Common Scenarios

### Scenario 1: Model Only Supports Past Covariates

**Model**: LSTM Basic (past=1, future=0)

**Valid Configuration**:
```json
{
    "trend_indicator": {"id": 1, "covariate_type": "past"},
    "momentum_indicator": {"id": 2, "covariate_type": "past"},
    "volatility_indicator": {"id": 3, "covariate_type": "past"},
    "volume_indicator": {"id": 4, "covariate_type": "past"}
}
```

**Invalid Configuration**:
```json
{
    "trend_indicator": {"id": 1, "covariate_type": "future"},  // ❌ WILL FAIL
    ...
}
```

**Error**:
```
Model 'LSTM Basic' does not support future covariates. Cannot set covariate_type='future'.
```

---

### Scenario 2: Model Supports Both Types

**Model**: LSTM Advanced (past=1, future=1)

**Valid Configurations**:
```json
// Option 1: All past
{
    "trend_indicator": {"id": 1, "covariate_type": "past"},
    "momentum_indicator": {"id": 2, "covariate_type": "past"},
    "volatility_indicator": {"id": 3, "covariate_type": "past"},
    "volume_indicator": {"id": 4, "covariate_type": "past"}
}

// Option 2: Mixed
{
    "trend_indicator": {"id": 1, "covariate_type": "past"},
    "momentum_indicator": {"id": 2, "covariate_type": "future"},
    "volatility_indicator": {"id": 3, "covariate_type": "both"},
    "volume_indicator": {"id": 4, "covariate_type": "past"}
}

// Option 3: All both
{
    "trend_indicator": {"id": 1, "covariate_type": "both"},
    "momentum_indicator": {"id": 2, "covariate_type": "both"},
    "volatility_indicator": {"id": 3, "covariate_type": "both"},
    "volume_indicator": {"id": 4, "covariate_type": "both"}
}
```

---

### Scenario 3: Changing Model

When changing a solution's model, existing indicator configurations may become invalid:

**Before**:
- Model: LSTM Advanced (past=1, future=1)
- Indicators: All configured with `covariate_type='both'`

**After changing to LSTM Basic (past=1, future=0)**:

**Problem**: Existing indicators with `covariate_type='both'` are now invalid!

**Solution**:
1. Check compatibility first:
   ```http
   GET /api/predict/solution/1/covariate-compatibility/
   ```

2. Update indicators to compatible types:
   ```http
   POST /api/predict/solution/1/indicators/set/
   {
       "trend_indicator": {"id": 1, "covariate_type": "past"},  // Changed from "both"
       ...
   }
   ```

---

## Troubleshooting

### Issue: ValidationException when adding indicator

**Error**:
```
Model 'LSTM Basic' does not support future covariates. Cannot set covariate_type='future'.
```

**Solution**:
1. Check model capabilities:
   ```http
   GET /api/predict/solution/1/covariate-compatibility/
   ```

2. Use compatible covariate_type:
   - If model only supports past: Use `covariate_type='past'`
   - If model supports both: Use `'past'`, `'future'`, or `'both'`

---

### Issue: SQL Error 1644 when inserting

**Error**:
```
Error 1644: Covariate type "future" is incompatible with model "LSTM Basic"
```

**Solution**: Database trigger caught the incompatibility. Fix the covariate_type in your INSERT/UPDATE statement.

---

### Issue: Want to use future covariates but model doesn't support

**Problem**: Need future covariate support for better predictions.

**Solutions**:
1. **Change Model**: Switch to a model that supports future covariates
   ```http
   PUT /api/predict/solution
   {
       "id": 1,
       "model_id": 2,  // LSTM Advanced with future support
       ...
   }
   ```

2. **Use Different Indicator**: Some indicators naturally work better as past covariates

3. **Model Configuration**: Check if model can be configured to support future covariates

---

## Best Practices

### 1. Check Compatibility First

Always check model capabilities before configuring indicators:

```python
# 1. Get compatibility info
response = requests.get(f'/api/predict/solution/{solution_id}/covariate-compatibility/')
compatible_types = response.json()['compatible_covariate_types']

# 2. Configure indicators with compatible types
if 'both' in compatible_types:
    covariate_type = 'both'  # Best option
elif 'past' in compatible_types:
    covariate_type = 'past'  # Safest fallback
else:
    covariate_type = 'future'
```

---

### 2. Use 'past' as Default

When in doubt, use `covariate_type='past'`:
- Most models support past covariates
- Historical data is always available
- Simpler to implement and test

---

### 3. Document Model Requirements

When creating models, clearly document covariate support:

```python
# Example model documentation
"""
LSTM Basic Model
- Supports: past_covariate=1
- Does NOT support: future_covariate=0
- Recommended for: Time series with only historical features
- Use cases: Standard stock price prediction
"""
```

---

### 4. Validate Before Training

Before training, verify all indicators are compatible:

```http
GET /api/predict/solution/1/indicators/validate

Response:
{
    "is_valid": true,
    "missing_types": [],
    "configured_types": ["trend", "momentum", "volatility", "volume"]
}
```

Then check covariate compatibility:

```sql
CALL sp_check_solution_covariate_compatibility(1);
```

---

## Migration Guide

### Running the Validation Migration

```bash
# 1. Backup database first
mysqldump -h stock-tuanph1970db.h.aivencloud.com \
          -u avnadmin -p -P 25021 defaultdb > backup.sql

# 2. Run migration
mysql -h stock-tuanph1970db.h.aivencloud.com \
      -u avnadmin -p -P 25021 \
      defaultdb < migrations/002_add_covariate_validation.sql

# 3. Verify
mysql -h stock-tuanph1970db.h.aivencloud.com \
      -u avnadmin -p -P 25021 \
      -e "SELECT * FROM v_covariate_compatibility_audit WHERE compatibility_status='INVALID';" \
      defaultdb
```

---

### Fixing Existing Invalid Configurations

If you have existing solutions with invalid covariate configurations:

```sql
-- Find invalid configurations
SELECT *
FROM v_covariate_compatibility_audit
WHERE compatibility_status = 'INVALID';

-- Fix by updating to 'past' (most compatible)
UPDATE solution_indicators si
INNER JOIN tbl_solution s ON si.solution_id = s.id
INNER JOIN tbl_model m ON s.model_id = m.id
SET si.covariate_type = 'past'
WHERE si.covariate_type = 'future' AND m.future_covariate = 0;

UPDATE solution_indicators si
INNER JOIN tbl_solution s ON si.solution_id = s.id
INNER JOIN tbl_model m ON s.model_id = m.id
SET si.covariate_type = 'past'
WHERE si.covariate_type = 'both' AND (m.past_covariate = 0 OR m.future_covariate = 0);
```

---

## Summary

✅ **What Was Implemented**:
1. Application-level validation in `indicator_service.py`
2. Database-level triggers preventing invalid inserts/updates
3. Helper functions and stored procedures for validation
4. Audit view for monitoring compatibility
5. New API endpoint for checking model capabilities

✅ **Benefits**:
- Prevents runtime errors during training
- Clear error messages for debugging
- Database integrity enforced at multiple layers
- Easy auditing and monitoring
- Better user experience with compatibility checks

✅ **Usage**:
- Always check `/covariate-compatibility/` before configuring indicators
- Use `covariate_type='past'` as safe default
- Validate configuration before training
- Monitor compatibility with audit view

---

## See Also

- [Database Schema Redesign Documentation](DATABASE_SCHEMA_REDESIGN.md)
- [API Reference](API_REFERENCE.md)
- [Model Configuration Guide](MODEL_CONFIGURATION.md)
