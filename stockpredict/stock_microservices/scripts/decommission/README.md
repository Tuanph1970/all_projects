# Django Decommissioning Scripts

This directory contains scripts for safely decommissioning the Django monolith after successful migration to microservices.

## Overview

The decommissioning process follows a structured approach:

```
1. verify_readiness.py  →  Check all prerequisites
         ↓
2. archive_django.sh    →  Create backups and archives
         ↓
3. decommission_django.sh → Shut down Django services
         ↓
4. post_migration_checklist.py → Complete follow-up tasks
```

## Prerequisites

Before running any decommission scripts:

1. **All microservices at 100% traffic** for minimum 2 weeks
2. **No active critical alerts**
3. **Shadow comparator showing >99% match rate**
4. **All data migration verified**
5. **Stakeholder approval obtained**

## Scripts

### 1. verify_readiness.py

Comprehensive verification that all prerequisites for decommissioning are met.

```bash
# Run verification
python verify_readiness.py

# Output includes:
# - Traffic routing check (must be 100% microservices)
# - Microservices health check
# - Error rate check (<1%)
# - Latency check (P99 <500ms)
# - Data consistency check (>99%)
# - Feature flags check
# - Minimum runtime check (>14 days at 100%)
# - Active alerts check
```

**Exit codes:**
- `0` - Ready for decommissioning
- `1` - Not ready (critical failures)

### 2. archive_django.sh

Creates comprehensive archives of Django code, database, logs, and configuration.

```bash
# Preview what will be archived
./archive_django.sh --dry-run

# Create archive
./archive_django.sh

# Skip specific components
./archive_django.sh --skip-db --skip-logs
```

**Archives created:**
- `django_code_<timestamp>.tar.gz` - Complete codebase
- `django_repo_<timestamp>.bundle` - Git bundle
- `django_db_<timestamp>.sql.gz` - Database dump
- `django_schema_<timestamp>.sql` - Schema export
- `logs_<dir>_<timestamp>.tar.gz` - Application logs
- `MANIFEST.json` - Archive metadata

**Storage:**
- Uploaded to S3 with STANDARD_IA storage class
- Default retention: 90 days
- Tagged for lifecycle management

### 3. decommission_django.sh

Performs the actual decommissioning of Django services.

```bash
# Preview decommissioning steps
./decommission_django.sh --dry-run

# Execute decommissioning (requires typing 'DECOMMISSION' to confirm)
./decommission_django.sh

# Skip confirmation prompts (use with caution)
./decommission_django.sh --force

# Keep database for reference
./decommission_django.sh --keep-db
```

**Actions performed:**
1. Remove Django routes from Traefik
2. Stop Django containers
3. Update docker-compose.yml
4. Remove Django containers and images
5. Update feature flags
6. Send notifications
7. Create decommission record

### 4. post_migration_checklist.py

Interactive checklist tool for completing all follow-up tasks.

```bash
# View checklist
python post_migration_checklist.py

# Interactive mode
python post_migration_checklist.py --interactive

# Mark task as completed
python post_migration_checklist.py --complete infra-001

# Generate completion report
python post_migration_checklist.py --report

# Reset checklist
python post_migration_checklist.py --reset
```

**Task Categories:**
- Infrastructure (CI/CD, DNS, load balancer)
- Documentation (architecture, API docs, runbooks)
- Communication (stakeholders, status page)
- Security (secrets, IAM, scans)
- Monitoring (dashboards, alerts)
- Database (archival, cleanup)
- Training (support team, guides)
- Cleanup (repos, artifacts)

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FEATURE_FLAGS_URL` | Feature flags service URL | `http://localhost:8010` |
| `PROMETHEUS_URL` | Prometheus URL | `http://localhost:9090` |
| `TRAEFIK_API_URL` | Traefik API URL | `http://localhost:8080` |
| `ARCHIVE_BUCKET` | S3 bucket for archives | `stockhelper-archives` |
| `DJANGO_DIR` | Django project directory | `/app/django` |
| `DB_HOST` | Database host | `localhost` |
| `DB_NAME` | Database name | `defaultdb` |
| `SLACK_WEBHOOK` | Slack webhook URL | (optional) |
| `EMAIL_RECIPIENTS` | Notification emails | (optional) |

## Recommended Workflow

### Day 1: Verification & Archive

```bash
# 1. Run verification
python verify_readiness.py

# 2. Review report and address any failures

# 3. Create archives (when ready)
./archive_django.sh

# 4. Verify archives were uploaded to S3
aws s3 ls s3://stockhelper-archives/django-decommission/
```

### Day 2: Decommissioning

```bash
# 1. Schedule maintenance window

# 2. Run decommissioning
./decommission_django.sh

# 3. Verify microservices still functioning
curl http://localhost/api/v2/health

# 4. Monitor for any issues
```

### Week 1-2: Follow-up Tasks

```bash
# 1. Start interactive checklist
python post_migration_checklist.py --interactive

# 2. Complete all tasks by category/priority

# 3. Generate completion report
python post_migration_checklist.py --report
```

## Rollback

If issues are discovered after decommissioning:

1. **Restore Traefik config** from backup:
   ```bash
   cp traefik/dynamic.yml.backup.<timestamp> traefik/dynamic.yml
   ```

2. **Restore docker-compose.yml** from backup:
   ```bash
   cp docker-compose.yml.backup.<timestamp> docker-compose.yml
   ```

3. **Restore database** from archive:
   ```bash
   aws s3 cp s3://stockhelper-archives/django-decommission/<timestamp>/django_complete_archive.tar.gz .
   tar -xzf django_complete_archive.tar.gz
   gunzip -c django_db_<timestamp>.sql.gz | mysql -h $DB_HOST -u $DB_USER $DB_NAME
   ```

4. **Restart Django**:
   ```bash
   docker-compose up -d django
   ```

5. **Update feature flags** to route traffic back to Django

## Troubleshooting

### Verification failures

- **Traffic not at 100%**: Use cutover CLI to set all services to 100%
- **Services unhealthy**: Check individual service logs
- **High error rate**: Investigate recent changes, consider rollback
- **Data inconsistency**: Review shadow comparator results

### Archive failures

- **S3 upload failed**: Check AWS credentials and bucket permissions
- **Database dump failed**: Verify database connectivity and permissions
- **Disk space**: Ensure /tmp has sufficient space for archives

### Decommissioning failures

- **Container stop failed**: Check for dependent services
- **Traefik update failed**: Manually edit configuration
- **Feature flag update failed**: Use feature flags UI to update

## Support

For issues with the decommissioning process:

1. Check logs in `/var/log/decommission/`
2. Review backup files in `/tmp/`
3. Contact Platform team on Slack #platform-support

---

*Last updated: December 2024*
