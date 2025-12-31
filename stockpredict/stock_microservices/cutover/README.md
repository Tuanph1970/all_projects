# Gradual Traffic Cutover System

Tools and configurations for managing the gradual migration of traffic from Django monolith to microservices.

## Overview

This system implements the **Strangler Fig pattern** with gradual traffic shifting:

```
Week 1: Shadow Mode    →  0% to microservices (comparison only)
Week 2: Canary         → 10% to microservices
Week 3: Early Adopter  → 30% to microservices
Week 4: Half           → 50% to microservices
Week 5: Majority       → 80% to microservices
Week 6: Final          → 95% to microservices
Week 7: Complete       → 100% to microservices
```

## Components

### Feature Flag Service

Redis-backed service for managing traffic routing decisions.

**Port:** 8010

```bash
# Start service
docker-compose up feature-flags

# Check status
curl http://localhost:8010/api/flags/status/current
```

### Cutover CLI

Command-line tool for managing cutover phases.

```bash
# Install dependencies
pip install httpx

# Show current status
python cutover.py status

# Preview a phase change
python cutover.py apply canary --dry-run

# Apply a phase (requires confirmation)
python cutover.py apply half --confirm

# Emergency rollback
python cutover.py rollback "High error rate detected"

# Set individual flag
python cutover.py set auth_microservice 75 --confirm
```

### Rollback Scripts

Emergency rollback procedures:

```bash
# Emergency rollback (routes 100% to Django)
./scripts/rollback.sh "Reason for rollback"

# Health check before cutover
./scripts/health_check.sh
```

## API Endpoints

### Feature Flags Service

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/flags/` | GET | List all flags |
| `/api/flags/{name}` | GET | Get specific flag |
| `/api/flags/{name}/evaluate` | POST | Evaluate flag for routing |
| `/api/flags/status/current` | GET | Get current cutover status |
| `/api/admin/phases/apply` | POST | Apply a cutover phase |
| `/api/admin/rollback` | POST | Emergency rollback |
| `/api/admin/flags/{name}/percentage` | POST | Set flag percentage |

### Authentication

Admin endpoints require the `X-Admin-Key` header:

```bash
curl -X POST http://localhost:8010/api/admin/phases/apply \
  -H "X-Admin-Key: your-admin-key" \
  -H "Content-Type: application/json" \
  -d '{"phase": "canary", "dry_run": true}'
```

## Traefik Configuration

The weighted routing configuration is in `traefik/dynamic-weighted.yml`.

Weights are managed by the feature flag service and cutover CLI.

## Monitoring

### Grafana Dashboard

Import `monitoring/grafana/dashboards/cutover-progress.json` for:

- Current cutover phase
- Traffic distribution (Django vs Microservices)
- Error rates and latency comparisons
- Service health status
- Active alerts

### Prometheus Alerts

Alert rules in `monitoring/prometheus/alerts/cutover-alerts.yml`:

| Alert | Severity | Threshold |
|-------|----------|-----------|
| HighMicroserviceErrorRate | Critical | >5% errors |
| ElevatedMicroserviceErrorRate | Warning | >1% errors |
| HighMicroserviceLatency | Critical | P99 >500ms |
| HighResponseMismatchRate | Critical | >10% mismatch |
| MicroserviceDown | Critical | Service unreachable |
| CutoverRollbackTriggered | Critical | Rollback activated |

## Cutover Workflow

### Pre-Cutover Checklist

1. [ ] All microservices healthy (`./scripts/health_check.sh`)
2. [ ] Shadow mode running for 1+ week
3. [ ] Response match rate >95%
4. [ ] Latency difference <100ms
5. [ ] Monitoring dashboards configured
6. [ ] Alert notifications set up
7. [ ] Rollback procedures tested
8. [ ] Team trained on rollback

### During Cutover

1. Apply each phase gradually:
   ```bash
   python cutover.py apply canary --confirm
   ```

2. Monitor for 24-48 hours at each phase

3. Check key metrics:
   - Error rate <1%
   - P99 latency <300ms
   - Success rate >99%

4. If issues arise:
   ```bash
   python cutover.py rollback "Description of issue"
   ```

### Post-Cutover

1. Confirm 100% traffic on microservices for 2 weeks
2. Monitor for any edge cases
3. Begin Django decommissioning

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FEATURE_FLAGS_URL` | http://localhost:8010 | Feature flags service URL |
| `ADMIN_API_KEY` | change-me-in-production | Admin API authentication |
| `REDIS_URL` | redis://redis:6379/6 | Redis connection URL |
| `SHADOW_COMPARATOR_URL` | http://localhost:9000 | Shadow comparator URL |

## Troubleshooting

### Traffic Not Shifting

1. Check feature flag service is running
2. Verify Traefik can reach feature flags
3. Check flag percentage is set correctly

```bash
curl http://localhost:8010/api/flags/auth_microservice
```

### High Error Rate After Cutover

1. Check microservice logs
2. Review shadow comparator mismatches
3. Consider rollback if >5% errors

```bash
python cutover.py rollback "Error rate exceeded 5%"
```

### Rollback Not Working

1. Manually update Traefik config
2. Set all flags to 0% directly in Redis
3. Contact on-call engineer

## File Structure

```
cutover/
├── cutover.py              # Main CLI tool
├── scripts/
│   ├── rollback.sh         # Emergency rollback
│   └── health_check.sh     # Service health check
├── config/
│   └── phases.yml          # Phase definitions
└── README.md

feature-flags/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── models/
│   ├── services/
│   └── routers/
├── Dockerfile
└── requirements.txt

traefik/
├── dynamic-weighted.yml    # Weighted routing config
├── shadow-mode.yml
├── cutover-10-percent.yml
├── cutover-50-percent.yml
└── cutover-100-percent.yml

monitoring/
├── grafana/dashboards/
│   └── cutover-progress.json
└── prometheus/alerts/
    └── cutover-alerts.yml
```
