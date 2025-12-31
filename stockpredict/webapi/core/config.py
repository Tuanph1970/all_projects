import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import json


@dataclass
class DatabaseConfig:
    host: str = field(default_factory=lambda: os.getenv('DB_HOST', '127.0.0.1'))
    user: str = field(default_factory=lambda: os.getenv('DB_USER', 'root'))
    password: str = field(default_factory=lambda: os.getenv('DB_PASSWORD', 'Mysql_2025'))
    database: str = field(default_factory=lambda: os.getenv('DB_NAME', 'defaultdb'))
    port: int = field(default_factory=lambda: int(os.getenv('DB_PORT', '3306')))
    pool_size: int = field(default_factory=lambda: int(os.getenv('DB_POOL_SIZE', '10')))
    timeout: int = field(default_factory=lambda: int(os.getenv('DB_TIMEOUT', '30')))


@dataclass
class SSHConfig:
    enabled: bool = field(default_factory=lambda: os.getenv('SSH_ENABLED', 'false').lower() == 'true')
    host: str = field(default_factory=lambda: os.getenv('SSH_HOST', '112.213.91.103'))
    port: int = field(default_factory=lambda: int(os.getenv('SSH_PORT', '22')))
    user: str = field(default_factory=lambda: os.getenv('SSH_USER', 'root'))
    password: str = field(default_factory=lambda: os.getenv('SSH_PASSWORD', ''))


@dataclass
class CacheConfig:
    default_ttl: int = field(default_factory=lambda: int(os.getenv('CACHE_DEFAULT_TTL', '300')))
    max_size: int = field(default_factory=lambda: int(os.getenv('CACHE_MAX_SIZE', '1000')))
    enabled: bool = field(default_factory=lambda: os.getenv('CACHE_ENABLED', 'true').lower() == 'true')


@dataclass
class ApiConfig:
    rate_limit_per_minute: int = field(default_factory=lambda: int(os.getenv('API_RATE_LIMIT', '60')))
    max_request_size: int = field(default_factory=lambda: int(os.getenv('API_MAX_REQUEST_SIZE', '10485760')))  # 10MB
    timeout: int = field(default_factory=lambda: int(os.getenv('API_TIMEOUT', '30')))


@dataclass
class ModelConfig:
    default_epochs: int = field(default_factory=lambda: int(os.getenv('MODEL_DEFAULT_EPOCHS', '100')))
    max_models: int = field(default_factory=lambda: int(os.getenv('MODEL_MAX_COUNT', '50')))
    auto_save: bool = field(default_factory=lambda: os.getenv('MODEL_AUTO_SAVE', 'true').lower() == 'true')
    model_storage_path: str = field(default_factory=lambda: os.getenv('MODEL_STORAGE_PATH', './models'))


@dataclass
class LoggingConfig:
    level: str = field(default_factory=lambda: os.getenv('LOG_LEVEL', 'INFO'))
    file_path: str = field(default_factory=lambda: os.getenv('LOG_FILE_PATH', './logs/app.log'))
    max_file_size: str = field(default_factory=lambda: os.getenv('LOG_MAX_FILE_SIZE', '10MB'))
    backup_count: int = field(default_factory=lambda: int(os.getenv('LOG_BACKUP_COUNT', '5')))


@dataclass
class StockDataConfig:
    default_source: str = field(default_factory=lambda: os.getenv('STOCK_DEFAULT_SOURCE', 'VCI'))
    supported_sources: list = field(default_factory=lambda: ['VCI', 'TCBS', 'SSI'])
    request_delay: float = field(default_factory=lambda: float(os.getenv('STOCK_REQUEST_DELAY', '1.0')))
    max_retries: int = field(default_factory=lambda: int(os.getenv('STOCK_MAX_RETRIES', '3')))


@dataclass
class AppConfig:
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    ssh: SSHConfig = field(default_factory=SSHConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    api: ApiConfig = field(default_factory=ApiConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    stock_data: StockDataConfig = field(default_factory=StockDataConfig)

    debug: bool = field(default_factory=lambda: os.getenv('DEBUG', 'false').lower() == 'true')
    environment: str = field(default_factory=lambda: os.getenv('ENVIRONMENT', 'development'))


class ConfigManager:
    _instance: Optional['ConfigManager'] = None
    _config: Optional[AppConfig] = None
    
    def __new__(cls) -> 'ConfigManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self._load_config()
            self.initialized = True
    
    def _load_config(self):
        config_file = os.getenv('CONFIG_FILE', 'config.json')
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                self._config = self._create_config_from_dict(config_data)
            except Exception as e:
                print(f"Failed to load config file {config_file}: {e}")
                self._config = AppConfig()
        else:
            self._config = AppConfig()
    
    def _create_config_from_dict(self, config_data: Dict[str, Any]) -> AppConfig:
        database_config = DatabaseConfig(**config_data.get('database', {}))
        ssh_config = SSHConfig(**config_data.get('ssh', {}))
        cache_config = CacheConfig(**config_data.get('cache', {}))
        api_config = ApiConfig(**config_data.get('api', {}))
        model_config = ModelConfig(**config_data.get('model', {}))
        logging_config = LoggingConfig(**config_data.get('logging', {}))
        stock_data_config = StockDataConfig(**config_data.get('stock_data', {}))

        return AppConfig(
            database=database_config,
            ssh=ssh_config,
            cache=cache_config,
            api=api_config,
            model=model_config,
            logging=logging_config,
            stock_data=stock_data_config,
            debug=config_data.get('debug', False),
            environment=config_data.get('environment', 'development')
        )
    
    @property
    def config(self) -> AppConfig:
        return self._config
    
    def get_database_config(self) -> DatabaseConfig:
        return self._config.database

    def get_ssh_config(self) -> SSHConfig:
        return self._config.ssh

    def get_cache_config(self) -> CacheConfig:
        return self._config.cache
    
    def get_api_config(self) -> ApiConfig:
        return self._config.api
    
    def get_model_config(self) -> ModelConfig:
        return self._config.model
    
    def get_logging_config(self) -> LoggingConfig:
        return self._config.logging
    
    def get_stock_data_config(self) -> StockDataConfig:
        return self._config.stock_data
    
    def is_debug(self) -> bool:
        return self._config.debug
    
    def is_production(self) -> bool:
        return self._config.environment.lower() == 'production'
    
    def reload_config(self):
        self._load_config()


def get_config() -> AppConfig:
    return ConfigManager().config