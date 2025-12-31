# Stock Helper Load Testing Suite

Comprehensive load testing suite for Stock Helper microservices using [Locust](https://locust.io/).

## Quick Start

### Prerequisites

```bash
pip install locust httpx
```

### Run a Quick Smoke Test

```bash
./run_load_test.sh smoke
```

### Run with Web UI

```bash
locust -f locustfile.py --host=http://localhost
# Open http://localhost:8089
```

## Test Scenarios

| Scenario | Users | Duration | Purpose |
|----------|-------|----------|---------|
| `smoke` | 5 | 1 min | Quick functionality check |
| `load` | 50 | 5 min | Normal load simulation |
| `stress` | 200-2000 | 12 min | Find breaking points |
| `spike` | 50-500 | 5 min | Sudden traffic surge |
| `soak` | 30 | 30 min | Long-running stability |
| `breakpoint` | 1000 | 15 min | Maximum capacity |

## Running Tests

### Using Shell Scripts

```bash
# Smoke test
./run_load_test.sh smoke

# Load test with custom parameters
./run_load_test.sh load --host http://staging.example.com

# Stress test
./run_load_test.sh stress

# Spike test
./run_load_test.sh spike

# Soak test (30 minutes)
./run_load_test.sh soak

# Custom parameters
./run_load_test.sh custom --users 100 --spawn-rate 10 --run-time 10m
```

### Using Docker Compose

```bash
# Start master + 4 workers
docker-compose -f docker-compose.locust.yml up --scale worker=4

# Run spike test
docker-compose -f docker-compose.locust.yml --profile spike up

# Run stress test
docker-compose -f docker-compose.locust.yml --profile stress up
```

### Distributed Testing

For high-scale tests, use distributed mode:

```bash
# Start distributed test with 8 workers
./run_distributed.sh start --workers 8 --users 500

# Start master only
./run_distributed.sh master

# Start workers (on other machines)
./run_distributed.sh worker --master-host 192.168.1.100

# Check status
./run_distributed.sh status

# Stop all
./run_distributed.sh stop
```

## User Behaviors

The test suite simulates different user types:

| User Type | Weight | Behavior |
|-----------|--------|----------|
| `StockDataUser` | 5 | Browse stocks, search, view history |
| `PortfolioUser` | 3 | Manage portfolio, transactions, alerts |
| `AnalysisUser` | 3 | Technical/fundamental analysis, screener |
| `PredictionUser` | 1 | ML predictions (expensive) |
| `AIUser` | 1 | AI insights, chat (expensive) |
| `MixedUser` | 2 | Mixed behavior across services |
| `HealthCheckUser` | 1 | Service health monitoring |

## Analyzing Results

### Quick Analysis

```bash
python analyze_results.py analyze smoke_20240115_120000
```

### Compare Runs

```bash
python analyze_results.py compare baseline_20240114 current_20240115
```

### Validate Thresholds

```bash
python analyze_results.py validate smoke_20240115_120000 --thresholds thresholds.json
```

### Output Formats

- **HTML**: Interactive charts and tables
- **Markdown**: Git-friendly documentation
- **JSON**: Machine-readable for CI/CD

## Performance Thresholds

Default thresholds (in `thresholds.json`):

| Endpoint Type | P95 Target | P99 Target | Success Rate |
|--------------|------------|------------|--------------|
| Health checks | 100ms | 200ms | 99.9% |
| Auth endpoints | 500ms | 1000ms | 99.5% |
| Stock data | 300ms | 500ms | 99.5% |
| Portfolio | 500ms | 1000ms | 99.0% |
| Analysis | 800ms | 1500ms | 98.0% |
| Predictions | 2000ms | 5000ms | 95.0% |
| AI/Chat | 5000ms | 15000ms | 95.0% |

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Run Load Tests
  run: |
    cd tests/performance/locust
    ./run_load_test.sh smoke --headless
    python analyze_results.py validate smoke_* --thresholds thresholds.json
```

### Threshold Validation

The `validate` command returns exit code 1 if any threshold fails, making it suitable for CI/CD pipelines.

## Project Structure

```
locust/
├── locustfile.py           # Main test file with user behaviors
├── config.py               # Configuration (services, thresholds)
├── thresholds.json         # Performance thresholds
├── run_load_test.sh        # Single-node runner
├── run_distributed.sh      # Distributed runner
├── analyze_results.py      # CLI analysis tool
├── docker-compose.locust.yml
├── scenarios/
│   ├── spike_test.py       # Spike test scenario
│   ├── stress_test.py      # Stress test scenario
│   └── soak_test.py        # Soak test scenario
├── reporting/
│   ├── analyzer.py         # Result parsing and analysis
│   ├── reporter.py         # HTML report generation
│   └── comparator.py       # Cross-run comparison
└── reports/                # Output directory
```

## Customization

### Adding New Endpoints

Edit `locustfile.py` and add tasks to the appropriate user class:

```python
@task(5)
@tag("stock-data", "read")
def my_new_endpoint(self):
    self.client.get("/api/v2/my-endpoint")
```

### Adding New Scenarios

Create a new file in `scenarios/` with a custom `LoadTestShape`:

```python
class MyLoadShape(LoadTestShape):
    stages = [
        {"duration": 60, "users": 10, "spawn_rate": 1},
        {"duration": 120, "users": 50, "spawn_rate": 5},
    ]

    def tick(self):
        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])
        return None
```

## Troubleshooting

### Services Not Responding

```bash
# Check service health
curl http://localhost:8007/health/live  # auth
curl http://localhost:8001/health/live  # stock-data
curl http://localhost:8003/health/live  # portfolio
```

### High Failure Rate

1. Check service logs for errors
2. Verify database connections
3. Check rate limiting configuration
4. Review resource utilization

### Slow Performance

1. Profile slow endpoints
2. Check database query performance
3. Review caching configuration
4. Analyze network latency
