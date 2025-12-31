import functools
import time
from typing import Dict, Any, Callable
from core.exceptions import ValidationException


class CacheManager:
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_expiry: Dict[str, float] = {}
    
    def get(self, key: str) -> Any:
        if key in self._cache:
            if time.time() < self._cache_expiry.get(key, 0):
                return self._cache[key]
            else:
                self.invalidate(key)
        return None
    
    def set(self, key: str, value: Any, ttl: int = 300):
        self._cache[key] = value
        self._cache_expiry[key] = time.time() + ttl
    
    def invalidate(self, key: str):
        self._cache.pop(key, None)
        self._cache_expiry.pop(key, None)
    
    def clear(self):
        self._cache.clear()
        self._cache_expiry.clear()


cache_manager = CacheManager()


def cache_result(ttl: int = 300, key_func: Callable = None):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            return result
        
        wrapper.cache_manager = cache_manager
        return wrapper
    return decorator


def validate_input(**validators):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for param_name, validator in validators.items():
                if param_name in kwargs:
                    value = kwargs[param_name]
                    if not validator(value):
                        raise ValidationException(
                            f"Validation failed for parameter '{param_name}' with value '{value}'",
                            param_name
                        )
            return func(*args, **kwargs)
        return wrapper
    return decorator


def retry(max_attempts: int = 3, delay: float = 1.0, exceptions: tuple = (Exception,)):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(delay * (attempt + 1))
                    continue
            
            raise last_exception
        return wrapper
    return decorator


def log_execution(logger=None):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            if logger:
                logger.info(f"Starting execution of {func.__name__}")
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                if logger:
                    logger.info(f"Completed {func.__name__} in {execution_time:.2f}s")
                
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                
                if logger:
                    logger.error(f"Failed {func.__name__} after {execution_time:.2f}s: {str(e)}")
                
                raise
        return wrapper
    return decorator


def validate_ticker(ticker: str) -> bool:
    return isinstance(ticker, str) and len(ticker) >= 2 and ticker.isalpha()


def validate_positive_int(value: Any) -> bool:
    return isinstance(value, int) and value > 0


def validate_date_string(date_str: Any) -> bool:
    import re
    if not isinstance(date_str, str):
        return False
    pattern = r'^\d{4}-\d{2}-\d{2}$'
    return bool(re.match(pattern, date_str))


def validate_model_type(model_type: Any) -> bool:
    allowed_types = ['RNN', 'XGBoost', 'CatBoost', 'LightGBM', 'RandomForest', 'DLinear', 'NBeats', 'NHits', 'NLinear', 'TCN', 'TFT', 'TiDE', 'Transformer', 'BlockRNN']
    return isinstance(model_type, str) and model_type in allowed_types