"""Prediction Service - Main Application"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
from sqlalchemy import text
import time
import logging

from app.config import get_settings
from app.api.routes import router
from app.api.dependencies import engine
from app.models.domain import Base

# SQL for WebAPI-compatible tables (model management)
WEBAPI_TABLES_SQL = [
    """
    CREATE TABLE IF NOT EXISTS model_instances (
        id INT AUTO_INCREMENT PRIMARY KEY,
        model_type VARCHAR(100) NOT NULL,
        model_sub_type VARCHAR(100),
        model_name VARCHAR(255) NOT NULL,
        user_id VARCHAR(100) NOT NULL,
        status VARCHAR(50) DEFAULT 'created',
        config_json LONGTEXT,
        file_extension VARCHAR(10),
        file_path VARCHAR(500),
        past_covariate BOOLEAN DEFAULT FALSE,
        future_covariate BOOLEAN DEFAULT FALSE,
        created_by VARCHAR(100),
        last_training_date TIMESTAMP NULL,
        training_metrics_json LONGTEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_user_id (user_id),
        INDEX idx_model_type (model_type),
        INDEX idx_status (status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS tbl_all_models (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) UNIQUE NOT NULL,
        description TEXT,
        has_sub_models BOOLEAN DEFAULT FALSE,
        is_active BOOLEAN DEFAULT TRUE,
        display_order INT DEFAULT 0
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS tbl_model_sub_types (
        id INT AUTO_INCREMENT PRIMARY KEY,
        model_id INT NOT NULL,
        name VARCHAR(100) NOT NULL,
        description TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        display_order INT DEFAULT 0,
        FOREIGN KEY (model_id) REFERENCES tbl_all_models(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS tbl_model_field (
        id INT AUTO_INCREMENT PRIMARY KEY,
        model_type_ VARCHAR(100) NOT NULL,
        field_name VARCHAR(100) NOT NULL,
        field_type VARCHAR(50) DEFAULT 'text',
        description TEXT,
        display_order INT DEFAULT 0
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS tbl_model_defaul_value (
        id INT AUTO_INCREMENT PRIMARY KEY,
        model_type_ VARCHAR(100) NOT NULL,
        field_name VARCHAR(100) NOT NULL,
        default_value VARCHAR(500),
        description TEXT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS tbl_param_option (
        id INT AUTO_INCREMENT PRIMARY KEY,
        param_name VARCHAR(100) NOT NULL,
        option_value VARCHAR(500) NOT NULL,
        description TEXT,
        display_order INT DEFAULT 0,
        INDEX idx_param_name (param_name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
]


# Seed data for model parameter tables (extracted from WebAPI model classes)
SEED_DATA_SQL = [
    # ---- tbl_model_field: defines which fields to show for each model type ----
    # BlockRNN fields
    """INSERT IGNORE INTO tbl_model_field (model_type_, field_name, field_type, description, display_order) VALUES
    ('BlockRNN', 'model_sub_type', 'select', 'Sub model type', 1),
    ('BlockRNN', 'input_chunk_length', 'text', 'Input chunk length', 2),
    ('BlockRNN', 'output_chunk_length', 'text', 'Output chunk length', 3),
    ('BlockRNN', 'hidden_dim', 'text', 'Hidden dimension', 4),
    ('BlockRNN', 'n_rnn_layers', 'text', 'Number of RNN layers', 5),
    ('BlockRNN', 'dropout', 'text', 'Dropout rate', 6),
    ('BlockRNN', 'batch_size', 'text', 'Batch size', 7),
    ('BlockRNN', 'n_epochs', 'text', 'Number of epochs', 8),
    ('BlockRNN', 'learning_rate', 'text', 'Learning rate', 9),
    ('BlockRNN', 'past_covariate', 'checkbox', 'Use past covariates', 10),
    ('BlockRNN', 'future_covariate', 'checkbox', 'Use future covariates', 11)""",
    # RNN fields
    """INSERT IGNORE INTO tbl_model_field (model_type_, field_name, field_type, description, display_order) VALUES
    ('RNN', 'model_sub_type', 'select', 'Sub model type', 1),
    ('RNN', 'input_chunk_length', 'text', 'Input chunk length', 2),
    ('RNN', 'training_length', 'text', 'Training length', 3),
    ('RNN', 'hidden_dim', 'text', 'Hidden dimension', 4),
    ('RNN', 'n_rnn_layers', 'text', 'Number of RNN layers', 5),
    ('RNN', 'dropout', 'text', 'Dropout rate', 6),
    ('RNN', 'batch_size', 'text', 'Batch size', 7),
    ('RNN', 'n_epochs', 'text', 'Number of epochs', 8),
    ('RNN', 'learning_rate', 'text', 'Learning rate', 9),
    ('RNN', 'past_covariate', 'checkbox', 'Use past covariates', 10),
    ('RNN', 'future_covariate', 'checkbox', 'Use future covariates', 11)""",
    # TCN fields
    """INSERT IGNORE INTO tbl_model_field (model_type_, field_name, field_type, description, display_order) VALUES
    ('TCN', 'input_chunk_length', 'text', 'Input chunk length', 1),
    ('TCN', 'output_chunk_length', 'text', 'Output chunk length', 2),
    ('TCN', 'kernel_size', 'text', 'Kernel size', 3),
    ('TCN', 'dilation_base', 'text', 'Dilation base', 4),
    ('TCN', 'weight_norm', 'checkbox', 'Weight normalization', 5),
    ('TCN', 'dropout', 'text', 'Dropout rate', 6),
    ('TCN', 'batch_size', 'text', 'Batch size', 7),
    ('TCN', 'n_epochs', 'text', 'Number of epochs', 8),
    ('TCN', 'past_covariate', 'checkbox', 'Use past covariates', 9),
    ('TCN', 'future_covariate', 'checkbox', 'Use future covariates', 10)""",
    # Transformer fields
    """INSERT IGNORE INTO tbl_model_field (model_type_, field_name, field_type, description, display_order) VALUES
    ('Transformer', 'input_chunk_length', 'text', 'Input chunk length', 1),
    ('Transformer', 'output_chunk_length', 'text', 'Output chunk length', 2),
    ('Transformer', 'd_model', 'text', 'Model dimension', 3),
    ('Transformer', 'nhead', 'text', 'Number of attention heads', 4),
    ('Transformer', 'num_encoder_layers', 'text', 'Encoder layers', 5),
    ('Transformer', 'num_decoder_layers', 'text', 'Decoder layers', 6),
    ('Transformer', 'dim_feedforward', 'text', 'Feedforward dimension', 7),
    ('Transformer', 'dropout', 'text', 'Dropout rate', 8),
    ('Transformer', 'activation', 'select', 'Activation function', 9),
    ('Transformer', 'batch_size', 'text', 'Batch size', 10),
    ('Transformer', 'n_epochs', 'text', 'Number of epochs', 11),
    ('Transformer', 'past_covariate', 'checkbox', 'Use past covariates', 12),
    ('Transformer', 'future_covariate', 'checkbox', 'Use future covariates', 13)""",
    # TFT fields
    """INSERT IGNORE INTO tbl_model_field (model_type_, field_name, field_type, description, display_order) VALUES
    ('TFT', 'input_chunk_length', 'text', 'Input chunk length', 1),
    ('TFT', 'output_chunk_length', 'text', 'Output chunk length', 2),
    ('TFT', 'hidden_size', 'text', 'Hidden size', 3),
    ('TFT', 'lstm_layers', 'text', 'LSTM layers', 4),
    ('TFT', 'num_attention_heads', 'text', 'Attention heads', 5),
    ('TFT', 'dropout', 'text', 'Dropout rate', 6),
    ('TFT', 'batch_size', 'text', 'Batch size', 7),
    ('TFT', 'n_epochs', 'text', 'Number of epochs', 8),
    ('TFT', 'past_covariate', 'checkbox', 'Use past covariates', 9),
    ('TFT', 'future_covariate', 'checkbox', 'Use future covariates', 10)""",
    # NBeats fields
    """INSERT IGNORE INTO tbl_model_field (model_type_, field_name, field_type, description, display_order) VALUES
    ('NBeats', 'input_chunk_length', 'text', 'Input chunk length', 1),
    ('NBeats', 'output_chunk_length', 'text', 'Output chunk length', 2),
    ('NBeats', 'generic_architecture', 'checkbox', 'Generic architecture', 3),
    ('NBeats', 'num_stacks', 'text', 'Number of stacks', 4),
    ('NBeats', 'num_blocks', 'text', 'Number of blocks', 5),
    ('NBeats', 'num_layers', 'text', 'Number of layers', 6),
    ('NBeats', 'layer_widths', 'text', 'Layer widths', 7),
    ('NBeats', 'batch_size', 'text', 'Batch size', 8),
    ('NBeats', 'n_epochs', 'text', 'Number of epochs', 9),
    ('NBeats', 'past_covariate', 'checkbox', 'Use past covariates', 10)""",
    # NHits fields
    """INSERT IGNORE INTO tbl_model_field (model_type_, field_name, field_type, description, display_order) VALUES
    ('NHits', 'input_chunk_length', 'text', 'Input chunk length', 1),
    ('NHits', 'output_chunk_length', 'text', 'Output chunk length', 2),
    ('NHits', 'num_stacks', 'text', 'Number of stacks', 3),
    ('NHits', 'num_blocks', 'text', 'Number of blocks', 4),
    ('NHits', 'num_layers', 'text', 'Number of layers', 5),
    ('NHits', 'layer_widths', 'text', 'Layer widths', 6),
    ('NHits', 'batch_size', 'text', 'Batch size', 7),
    ('NHits', 'n_epochs', 'text', 'Number of epochs', 8),
    ('NHits', 'past_covariate', 'checkbox', 'Use past covariates', 9)""",
    # DLinear fields
    """INSERT IGNORE INTO tbl_model_field (model_type_, field_name, field_type, description, display_order) VALUES
    ('DLinear', 'input_chunk_length', 'text', 'Input chunk length', 1),
    ('DLinear', 'output_chunk_length', 'text', 'Output chunk length', 2),
    ('DLinear', 'shared_weights', 'checkbox', 'Shared weights', 3),
    ('DLinear', 'kernel_size', 'text', 'Kernel size', 4),
    ('DLinear', 'const_init', 'checkbox', 'Constant initialization', 5),
    ('DLinear', 'batch_size', 'text', 'Batch size', 6),
    ('DLinear', 'n_epochs', 'text', 'Number of epochs', 7),
    ('DLinear', 'past_covariate', 'checkbox', 'Use past covariates', 8),
    ('DLinear', 'future_covariate', 'checkbox', 'Use future covariates', 9)""",
    # NLinear fields
    """INSERT IGNORE INTO tbl_model_field (model_type_, field_name, field_type, description, display_order) VALUES
    ('NLinear', 'input_chunk_length', 'text', 'Input chunk length', 1),
    ('NLinear', 'output_chunk_length', 'text', 'Output chunk length', 2),
    ('NLinear', 'shared_weights', 'checkbox', 'Shared weights', 3),
    ('NLinear', 'const_init', 'checkbox', 'Constant initialization', 4),
    ('NLinear', 'batch_size', 'text', 'Batch size', 5),
    ('NLinear', 'n_epochs', 'text', 'Number of epochs', 6),
    ('NLinear', 'past_covariate', 'checkbox', 'Use past covariates', 7),
    ('NLinear', 'future_covariate', 'checkbox', 'Use future covariates', 8)""",
    # XGBoost fields
    """INSERT IGNORE INTO tbl_model_field (model_type_, field_name, field_type, description, display_order) VALUES
    ('XGBoost', 'lag_len', 'text', 'Lag length', 1),
    ('XGBoost', 'lag_past_len', 'text', 'Past lag length', 2),
    ('XGBoost', 'lag_future_len', 'text', 'Future lag length', 3),
    ('XGBoost', 'output_chunk_length', 'text', 'Output chunk length', 4),
    ('XGBoost', 'multi_models', 'checkbox', 'Multi models', 5),
    ('XGBoost', 'past_covariate', 'checkbox', 'Use past covariates', 6),
    ('XGBoost', 'future_covariate', 'checkbox', 'Use future covariates', 7)""",
    # LightGBM fields
    """INSERT IGNORE INTO tbl_model_field (model_type_, field_name, field_type, description, display_order) VALUES
    ('LightGBM', 'lag_len', 'text', 'Lag length', 1),
    ('LightGBM', 'lag_past_len', 'text', 'Past lag length', 2),
    ('LightGBM', 'lag_future_len', 'text', 'Future lag length', 3),
    ('LightGBM', 'output_chunk_length', 'text', 'Output chunk length', 4),
    ('LightGBM', 'multi_models', 'checkbox', 'Multi models', 5),
    ('LightGBM', 'past_covariate', 'checkbox', 'Use past covariates', 6),
    ('LightGBM', 'future_covariate', 'checkbox', 'Use future covariates', 7)""",
    # RandomForest fields
    """INSERT IGNORE INTO tbl_model_field (model_type_, field_name, field_type, description, display_order) VALUES
    ('RandomForest', 'lag_len', 'text', 'Lag length', 1),
    ('RandomForest', 'lag_past_len', 'text', 'Past lag length', 2),
    ('RandomForest', 'lag_future_len', 'text', 'Future lag length', 3),
    ('RandomForest', 'output_chunk_length', 'text', 'Output chunk length', 4),
    ('RandomForest', 'multi_models', 'checkbox', 'Multi models', 5),
    ('RandomForest', 'past_covariate', 'checkbox', 'Use past covariates', 6),
    ('RandomForest', 'future_covariate', 'checkbox', 'Use future covariates', 7)""",
    # CatBoost fields
    """INSERT IGNORE INTO tbl_model_field (model_type_, field_name, field_type, description, display_order) VALUES
    ('CatBoost', 'lag_len', 'text', 'Lag length', 1),
    ('CatBoost', 'lag_past_len', 'text', 'Past lag length', 2),
    ('CatBoost', 'lag_future_len', 'text', 'Future lag length', 3),
    ('CatBoost', 'output_chunk_length', 'text', 'Output chunk length', 4),
    ('CatBoost', 'multi_models', 'checkbox', 'Multi models', 5),
    ('CatBoost', 'past_covariate', 'checkbox', 'Use past covariates', 6),
    ('CatBoost', 'future_covariate', 'checkbox', 'Use future covariates', 7)""",

    # ---- tbl_model_defaul_value: default parameter values per model type ----
    """INSERT IGNORE INTO tbl_model_defaul_value (model_type_, field_name, default_value, description) VALUES
    ('BlockRNN', 'model_sub_type', 'LSTM', 'Default sub model'),
    ('BlockRNN', 'input_chunk_length', '14', 'Default input chunk'),
    ('BlockRNN', 'output_chunk_length', '10', 'Default output chunk'),
    ('BlockRNN', 'hidden_dim', '20', 'Default hidden dim'),
    ('BlockRNN', 'n_rnn_layers', '1', 'Default RNN layers'),
    ('BlockRNN', 'dropout', '0', 'Default dropout'),
    ('BlockRNN', 'batch_size', '16', 'Default batch size'),
    ('BlockRNN', 'n_epochs', '300', 'Default epochs'),
    ('BlockRNN', 'learning_rate', '0.0001', 'Default learning rate')""",
    """INSERT IGNORE INTO tbl_model_defaul_value (model_type_, field_name, default_value, description) VALUES
    ('RNN', 'model_sub_type', 'LSTM', 'Default sub model'),
    ('RNN', 'input_chunk_length', '14', 'Default input chunk'),
    ('RNN', 'training_length', '30', 'Default training length'),
    ('RNN', 'hidden_dim', '20', 'Default hidden dim'),
    ('RNN', 'n_rnn_layers', '1', 'Default RNN layers'),
    ('RNN', 'dropout', '0', 'Default dropout'),
    ('RNN', 'batch_size', '16', 'Default batch size'),
    ('RNN', 'n_epochs', '300', 'Default epochs'),
    ('RNN', 'learning_rate', '0.0001', 'Default learning rate')""",
    """INSERT IGNORE INTO tbl_model_defaul_value (model_type_, field_name, default_value, description) VALUES
    ('TCN', 'input_chunk_length', '14', 'Default input chunk'),
    ('TCN', 'output_chunk_length', '10', 'Default output chunk'),
    ('TCN', 'kernel_size', '3', 'Default kernel size'),
    ('TCN', 'dilation_base', '2', 'Default dilation base'),
    ('TCN', 'dropout', '0.2', 'Default dropout'),
    ('TCN', 'batch_size', '16', 'Default batch size'),
    ('TCN', 'n_epochs', '500', 'Default epochs')""",
    """INSERT IGNORE INTO tbl_model_defaul_value (model_type_, field_name, default_value, description) VALUES
    ('Transformer', 'input_chunk_length', '14', 'Default input chunk'),
    ('Transformer', 'output_chunk_length', '10', 'Default output chunk'),
    ('Transformer', 'd_model', '16', 'Default model dim'),
    ('Transformer', 'nhead', '8', 'Default attention heads'),
    ('Transformer', 'num_encoder_layers', '2', 'Default encoder layers'),
    ('Transformer', 'num_decoder_layers', '2', 'Default decoder layers'),
    ('Transformer', 'dim_feedforward', '128', 'Default feedforward dim'),
    ('Transformer', 'dropout', '0.1', 'Default dropout'),
    ('Transformer', 'activation', 'relu', 'Default activation'),
    ('Transformer', 'batch_size', '16', 'Default batch size'),
    ('Transformer', 'n_epochs', '300', 'Default epochs')""",
    """INSERT IGNORE INTO tbl_model_defaul_value (model_type_, field_name, default_value, description) VALUES
    ('TFT', 'input_chunk_length', '14', 'Default input chunk'),
    ('TFT', 'output_chunk_length', '10', 'Default output chunk'),
    ('TFT', 'hidden_size', '64', 'Default hidden size'),
    ('TFT', 'lstm_layers', '1', 'Default LSTM layers'),
    ('TFT', 'num_attention_heads', '4', 'Default attention heads'),
    ('TFT', 'dropout', '0.1', 'Default dropout'),
    ('TFT', 'batch_size', '16', 'Default batch size'),
    ('TFT', 'n_epochs', '300', 'Default epochs')""",
    """INSERT IGNORE INTO tbl_model_defaul_value (model_type_, field_name, default_value, description) VALUES
    ('NBeats', 'input_chunk_length', '14', 'Default input chunk'),
    ('NBeats', 'output_chunk_length', '10', 'Default output chunk'),
    ('NBeats', 'num_stacks', '10', 'Default stacks'),
    ('NBeats', 'num_blocks', '1', 'Default blocks'),
    ('NBeats', 'num_layers', '4', 'Default layers'),
    ('NBeats', 'layer_widths', '512', 'Default layer widths'),
    ('NBeats', 'batch_size', '16', 'Default batch size'),
    ('NBeats', 'n_epochs', '300', 'Default epochs')""",
    """INSERT IGNORE INTO tbl_model_defaul_value (model_type_, field_name, default_value, description) VALUES
    ('NHits', 'input_chunk_length', '14', 'Default input chunk'),
    ('NHits', 'output_chunk_length', '10', 'Default output chunk'),
    ('NHits', 'num_stacks', '10', 'Default stacks'),
    ('NHits', 'num_blocks', '1', 'Default blocks'),
    ('NHits', 'num_layers', '4', 'Default layers'),
    ('NHits', 'layer_widths', '512', 'Default layer widths'),
    ('NHits', 'batch_size', '16', 'Default batch size'),
    ('NHits', 'n_epochs', '300', 'Default epochs')""",
    """INSERT IGNORE INTO tbl_model_defaul_value (model_type_, field_name, default_value, description) VALUES
    ('DLinear', 'input_chunk_length', '14', 'Default input chunk'),
    ('DLinear', 'output_chunk_length', '10', 'Default output chunk'),
    ('DLinear', 'kernel_size', '25', 'Default kernel size'),
    ('DLinear', 'batch_size', '32', 'Default batch size'),
    ('DLinear', 'n_epochs', '100', 'Default epochs')""",
    """INSERT IGNORE INTO tbl_model_defaul_value (model_type_, field_name, default_value, description) VALUES
    ('NLinear', 'input_chunk_length', '14', 'Default input chunk'),
    ('NLinear', 'output_chunk_length', '10', 'Default output chunk'),
    ('NLinear', 'batch_size', '32', 'Default batch size'),
    ('NLinear', 'n_epochs', '100', 'Default epochs')""",
    """INSERT IGNORE INTO tbl_model_defaul_value (model_type_, field_name, default_value, description) VALUES
    ('XGBoost', 'lag_len', '14', 'Default lag length'),
    ('XGBoost', 'lag_past_len', '14', 'Default past lag'),
    ('XGBoost', 'lag_future_len', '14', 'Default future lag'),
    ('XGBoost', 'output_chunk_length', '1', 'Default output chunk')""",
    """INSERT IGNORE INTO tbl_model_defaul_value (model_type_, field_name, default_value, description) VALUES
    ('LightGBM', 'lag_len', '14', 'Default lag length'),
    ('LightGBM', 'lag_past_len', '14', 'Default past lag'),
    ('LightGBM', 'lag_future_len', '14', 'Default future lag'),
    ('LightGBM', 'output_chunk_length', '10', 'Default output chunk')""",
    """INSERT IGNORE INTO tbl_model_defaul_value (model_type_, field_name, default_value, description) VALUES
    ('RandomForest', 'lag_len', '14', 'Default lag length'),
    ('RandomForest', 'lag_past_len', '14', 'Default past lag'),
    ('RandomForest', 'lag_future_len', '14', 'Default future lag'),
    ('RandomForest', 'output_chunk_length', '1', 'Default output chunk')""",
    """INSERT IGNORE INTO tbl_model_defaul_value (model_type_, field_name, default_value, description) VALUES
    ('CatBoost', 'lag_len', '14', 'Default lag length'),
    ('CatBoost', 'lag_past_len', '14', 'Default past lag'),
    ('CatBoost', 'lag_future_len', '14', 'Default future lag'),
    ('CatBoost', 'output_chunk_length', '1', 'Default output chunk')""",

    # ---- tbl_param_option: dropdown options for select fields ----
    """INSERT IGNORE INTO tbl_param_option (param_name, option_value, description, display_order) VALUES
    ('model_sub_type', 'LSTM', 'Long Short-Term Memory', 1),
    ('model_sub_type', 'GRU', 'Gated Recurrent Unit', 2),
    ('model_sub_type', 'RNN', 'Vanilla RNN', 3),
    ('activation', 'relu', 'ReLU activation', 1),
    ('activation', 'gelu', 'GELU activation', 2)""",
]

settings = get_settings()

# Logging configuration
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    "prediction_service_requests_total",
    "Total requests",
    ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "prediction_service_request_latency_seconds",
    "Request latency",
    ["method", "endpoint"]
)
PREDICTION_COUNT = Counter(
    "prediction_service_predictions_total",
    "Total predictions generated",
    ["symbol", "model_type"]
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info(f"Starting {settings.SERVICE_NAME} v{settings.SERVICE_VERSION}")

    # Create database tables (SQLAlchemy models)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("SQLAlchemy database tables created")

    # Create WebAPI-compatible tables (model management)
    async with engine.begin() as conn:
        for table_sql in WEBAPI_TABLES_SQL:
            try:
                await conn.execute(text(table_sql))
            except Exception as e:
                logger.warning(f"Table creation warning: {e}")
    logger.info("WebAPI-compatible tables ensured")

    # Seed model parameter data (INSERT IGNORE = skip if already exists)
    async with engine.begin() as conn:
        for seed_sql in SEED_DATA_SQL:
            try:
                await conn.execute(text(seed_sql))
            except Exception as e:
                logger.debug(f"Seed data note: {e}")
    logger.info("Model parameter seed data ensured")

    # Create model directory
    import os
    os.makedirs(settings.MODEL_PATH, exist_ok=True)
    logger.info(f"Model directory ready: {settings.MODEL_PATH}")

    yield

    # Cleanup
    await engine.dispose()
    logger.info(f"Shutting down {settings.SERVICE_NAME}")


# Create FastAPI app
app = FastAPI(
    title="Prediction Service",
    description="Microservice for ML-based stock price predictions",
    version=settings.SERVICE_VERSION,
    docs_url=f"/{settings.API_PREFIX}/api/v2/predict/docs",
    redoc_url=f"/{settings.API_PREFIX}/api/v2/predict/redoc",
    openapi_url=f"/{settings.API_PREFIX}/api/v2/predict/openapi.json",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Metrics middleware
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    endpoint = request.url.path
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=endpoint,
        status=response.status_code
    ).inc()
    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=endpoint
    ).observe(duration)

    return response


# Include API routes for /predict path
app.include_router(
    router,
    prefix=f"/{settings.API_PREFIX}/api/v2/predict",
    tags=["Predictions"]
)

# Also include routes for /models path (for model management endpoints)
app.include_router(
    router,
    prefix=f"/{settings.API_PREFIX}/api/v2/models",
    tags=["Models"]
)


# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check"""
    return {"status": "healthy", "service": settings.SERVICE_NAME}


@app.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe"""
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness_check():
    """Kubernetes readiness probe"""
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "not ready", "database": str(e)}
        )


# Prometheus metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# Service info endpoint
@app.get(f"/{settings.API_PREFIX}/api/v2/predict/info")
async def service_info():
    """Service information"""
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "environment": settings.ENVIRONMENT,
        "ml_config": {
            "model_path": settings.MODEL_PATH,
            "default_prediction_days": settings.DEFAULT_PREDICTION_DAYS,
            "max_prediction_days": settings.MAX_PREDICTION_DAYS,
            "lookback_period": settings.LOOKBACK_PERIOD
        },
        "endpoints": {
            "predict": f"/{settings.API_PREFIX}/api/v2/predict/predict",
            "models": f"/{settings.API_PREFIX}/api/v2/predict/models",
            "train": f"/{settings.API_PREFIX}/api/v2/predict/models/train",
            "backtest": f"/{settings.API_PREFIX}/api/v2/predict/backtest",
            "compare": f"/{settings.API_PREFIX}/api/v2/predict/compare"
        }
    }


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
