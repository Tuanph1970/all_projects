# Stock Backend API - Restructured Architecture

## Overview
This document outlines the restructured architecture of the stock backend API, implementing clean architecture principles with proper separation of concerns, design patterns, and maintainable code structure.

## Architecture Layers

### 1. Core Layer (`/core/`)
The foundation layer containing essential infrastructure components:

- **`database.py`**: Singleton pattern for database connection management
- **`interfaces.py`**: Abstract base classes and contracts
- **`exceptions.py`**: Custom exception hierarchy
- **`factories.py`**: Factory patterns for model and data source creation
- **`strategies.py`**: Strategy pattern for different data sources (VCI, TCBS)
- **`observers.py`**: Observer pattern for model event notifications
- **`commands.py`**: Command pattern for model operations with undo/redo
- **`decorators.py`**: Caching, validation, retry, and logging decorators
- **`config.py`**: Configuration management with environment variable support

### 2. Repository Layer (`/repositories/`)
Data access layer implementing Repository pattern:

- **`base_repository.py`**: Abstract base repository with common database operations
- **`stock_repository.py`**: Stock data, company, and market index repositories
- **`model_repository.py`**: Model and model parameter repositories

### 3. Service Layer (`/services/`)
Business logic layer:

- **`stock_market_service.py`**: Market data operations with caching and validation
- **`model_service.py`**: Model lifecycle management with event publishing
- **`technical_analysis_service.py`**: Technical indicator calculations

### 4. Legacy Integration (`/Service/`, `/Repository/`)
Maintains compatibility with existing code while integrating new patterns.

## Design Patterns Implemented

### 1. Singleton Pattern
- **Database Connection**: Ensures single database connection instance
- **Configuration Manager**: Global configuration access

### 2. Factory Pattern
- **Model Factory**: Creates different ML model types (RNN, XGBoost, etc.)
- **Data Source Factory**: Creates appropriate data source handlers

### 3. Strategy Pattern
- **Data Source Strategy**: Pluggable data sources (VCI, TCBS, SSI)
- **Different implementations for market, company, and financial data**

### 4. Observer Pattern
- **Model Event Publisher**: Notifies observers of model lifecycle events
- **Logging Observer**: Logs model events to file
- **Notification Observer**: Console notifications

### 5. Command Pattern
- **Model Commands**: Create, Update, Delete operations with undo/redo
- **Command Invoker**: History management and operation rollback

### 6. Repository Pattern
- **Data Access Abstraction**: Clean separation between business logic and data access
- **Generic base repository with common operations**

### 7. Decorator Pattern
- **Caching**: Method-level result caching with TTL
- **Validation**: Input parameter validation
- **Retry**: Automatic retry on failures
- **Logging**: Execution time and error logging

## Key Improvements

### 1. Separation of Concerns
- **Views**: Only handle HTTP requests/responses
- **Services**: Contain business logic
- **Repositories**: Handle data access
- **Core**: Infrastructure and cross-cutting concerns

### 2. Configuration Management
```python
# Environment-based configuration
database:
  host: ${DB_HOST}
  user: ${DB_USER}
  password: ${DB_PASSWORD}

cache:
  default_ttl: ${CACHE_DEFAULT_TTL}
  enabled: ${CACHE_ENABLED}
```

### 3. Error Handling
- **Structured exception hierarchy**
- **Service-specific exceptions**
- **Proper error propagation**

### 4. Caching Strategy
```python
@cache_result(ttl=300)
def get_companies_by_group(self, group: str):
    # Cached for 5 minutes
```

### 5. Input Validation
```python
@validate_input(symbol=validate_ticker, start=validate_date_string)
def get_price_history(self, symbol: str, start: str, end: str):
    # Validates ticker format and date strings
```

### 6. Event-Driven Architecture
```python
# Model creation triggers events
self.event_publisher.model_created(model_id, model_type, model_name)
```

## Usage Examples

### 1. Creating a Model with Events
```python
service = ModelService()
model = service.create_model(
    model_name="My RNN Model",
    model_type="RNN",
    parameters={"epochs": 100, "learning_rate": 0.001}
)
# Automatically triggers model_created event
```

### 2. Using Strategy Pattern for Data Sources
```python
context = DataSourceStrategyFactory.create_context("VCI")
market_data = context.get_market_data("VN30F1M")

# Switch to different source
context.set_strategy(DataSourceStrategyFactory.get_strategy("TCBS"))
```

### 3. Command Pattern for Operations
```python
invoker = ModelCommandInvoker()
create_cmd = CreateModelCommand(service, "Test Model", "RNN")
result = invoker.execute_command(create_cmd)

# Undo the operation
invoker.undo()
```

## Database Connection Improvements

### Before (Hardcoded)
```python
conn = pymysql.connect(
    host='stock-tuanph1970db.h.aivencloud.com',
    user='avnadmin',
    password="AVNS_mp2xuWCFM081Ac1WdBD",
    db='defaultdb',
    port=25021
)
```

### After (Configurable & Singleton)
```python
connection = get_database_connection()  # Uses configuration and connection pooling
```

## Testing Strategy
- **Unit tests**: Mock repositories and external services
- **Integration tests**: Test service layer with real repositories
- **E2E tests**: Full API testing with test database

## Migration Path
1. **Phase 1**: New endpoints use new architecture (✅ Completed)
2. **Phase 2**: Gradually migrate existing endpoints
3. **Phase 3**: Remove legacy code once migration is complete

## Benefits Achieved

1. **Maintainability**: Clear separation of concerns and consistent patterns
2. **Testability**: Easy to mock dependencies and test individual components
3. **Scalability**: Factory and strategy patterns allow easy extension
4. **Reliability**: Error handling, retry logic, and validation
5. **Performance**: Caching and connection pooling
6. **Observability**: Event-driven notifications and logging
7. **Configuration**: Environment-based configuration management

## Next Steps

1. **Add comprehensive logging**: Structured logging with correlation IDs
2. **Implement authentication/authorization**: JWT tokens with role-based access
3. **Add API rate limiting**: Prevent abuse and ensure fair usage
4. **Database migrations**: Version-controlled schema changes
5. **Monitoring**: Health checks and metrics collection
6. **Documentation**: Auto-generated API documentation