# Disaster Recovery & High Availability Runbook

**Phase 3.5 §3.5.3 (HA) + §3.5.4 (DR).** This is the operational runbook for
keeping the Stock Helper platform available and recovering it after failure.

| Objective | Target |
|---|---|
| **RPO** (Recovery Point Objective — max data loss) | **1 hour** (MySQL), 5 min (Redis cache) |
| **RTO** (Recovery Time Objective — max downtime) | **4 hours** (full region), < 2 min (single service) |
| **Availability target** | 99.9% (≤ 43.8 min downtime/month) |

---

## 1. High-Availability Architecture

The platform is stateless at the service tier and stateful only at the data
tier (MySQL, Redis, RabbitMQ). HA is achieved by running multiple replicas of
each stateless service behind Traefik, spread across nodes.

### 1.1 Replica topology

| Service | Replicas | Anti-affinity | Rationale |
|---|---|---|---|
| traefik (gateway) | 2 | one per node | entry point must never be a SPOF |
| auth-service | 2 | one per node | every request needs token validation |
| stock-data-service | 3 | ≤ 2 per node | highest read traffic |
| portfolio-service | 3 | one per node | core write path |
| analysis-service | 2 | one per node | CPU-heavy, benefits from spread |
| prediction-service | 2 | one per node | ML inference |
| redis / rabbitmq | 1* | pinned to manager | *see §1.3 for true clustering |

### 1.2 Deploying HA

**Docker Swarm** (honours `deploy:`, ignores `container_name`):
```bash
docker swarm init
docker stack deploy -c docker-compose.yml -c docker-compose.ha.yml stock
docker stack services stock         # confirm replica counts
docker service scale stock_stock-data-service=5   # scale on demand
```

**Kubernetes** (full manifests with PDB + HPA):
```bash
kubectl apply -f production/kubernetes/deployment-ha.yaml -n stock
kubectl get deploy,hpa,pdb -n stock
kubectl rollout status deploy/stock-data-service -n stock
```

Both configs use **`maxUnavailable: 0` / `order: start-first`** so rolling
deploys never drop below the desired replica count — zero-downtime releases.

### 1.3 Stateful-tier HA (production hardening)

Redis and RabbitMQ run single-replica in the base config. For production:

- **MySQL**: primary + ≥1 read replica with async replication; promote replica
  on primary failure (see `production/ha/replication.py`, `failover.py`).
- **Redis**: Redis Sentinel (3 sentinels) or managed Redis with automatic
  failover. `appendonly yes` is already enabled for durability.
- **RabbitMQ**: quorum queues across a 3-node cluster.

---

## 2. Backup Strategy (RPO)

Driven by `scripts/backup.sh`.

| Data store | Method | Frequency | Retention | Location |
|---|---|---|---|---|
| MySQL | `mysqldump --single-transaction` → gzip | hourly | 30 days | local + `s3://backups/mysql/` |
| Redis | `SAVE` + RDB copy | every 5 min | 30 days | local + `s3://backups/redis/` |
| Config | git | on change | ∞ | this repo |

### 2.1 Cron schedule

```cron
0   * * * *  /opt/stock/scripts/backup.sh mysql >> /var/log/stock-backup.log 2>&1
*/5 * * * *  /opt/stock/scripts/backup.sh redis >> /var/log/stock-backup.log 2>&1
```

To enable S3 offsite copies, export `BACKUP_S3_BUCKET=s3://your-bucket/` and
ensure the `aws` CLI is configured on the backup host.

### 2.2 Verify a backup

```bash
./scripts/backup.sh mysql
ls -lh backups/mysql/                       # newest *.sql.gz non-empty
gunzip -t backups/mysql/<file>.sql.gz       # gzip integrity
```

---

## 3. Recovery Procedures

### 3.1 Single service failure (RTO < 2 min)

Docker `restart: unless-stopped` (compose) and the Deployment controller (K8s)
restart a crashed task automatically; Traefik drops the dead endpoint and
routes to healthy replicas. **No manual action required.** Verify:

```bash
docker ps --filter name=stock_                 # service back to Up (healthy)
curl -sf http://localhost:8004/health/live
# K8s:
kubectl get pods -n stock
```

### 3.2 Database failure (RTO < 1 h)

1. **Failover to replica** (if configured): promote the read replica to primary
   and repoint `DATABASE_HOST`. See `production/ha/failover.py`.
2. **Restore from backup** (no replica):
   ```bash
   gunzip < backups/mysql/<latest>.sql.gz | \
     mysql --host="$DATABASE_HOST" --user="$MYSQL_USER" -p"$MYSQL_PASSWORD" "$DATABASE_NAME"
   ```
3. Restart services so connection pools reconnect:
   ```bash
   docker compose restart auth-service stock-data-service portfolio-service \
     prediction-service analysis-service journal-service decision-helper-service
   ```

### 3.3 Redis failure (RTO < 5 min)

Redis restarts automatically; `appendonly` + RDB snapshot restore state. If the
volume is lost, the cache simply repopulates on demand (cold-cache latency
spike only — no permanent data loss, since Redis is a cache here).

### 3.4 Complete outage / region loss (RTO < 4 h)

1. Provision infrastructure in the DR region (IaC).
2. Deploy the stack: `docker stack deploy` / `kubectl apply` (§1.2).
3. Restore MySQL from the latest offsite backup (§3.2).
4. Update DNS / load balancer to point at the DR region.
5. Run the post-recovery verification (§4).

---

## 4. Post-Recovery Verification

```bash
# 1. All services healthy
./scripts/deploy.sh --health

# 2. Public endpoints respond
./scripts/deploy.sh --test

# 3. Performance within SLA (p99 ≤ 300ms core APIs)
python tests/performance/benchmark.py --samples 50

# 4. A representative read/write round-trips (login → create → read)
```

---

## 5. DR Drill

Run the automated drill regularly (quarterly minimum, and after any infra
change) to prove the procedures above actually work.

```bash
./scripts/dr-drill.sh all          # service + redis + gateway + backup
./scripts/dr-drill.sh service      # single scenario
RTO_BUDGET_SECONDS=60 ./scripts/dr-drill.sh service   # tighter budget
```

The drill kills real containers and measures recovery time (RTO) against
`RTO_BUDGET_SECONDS`. It never deletes volumes, so it is safe to run against a
staging stack. A run is **PASS** only if every exercised scenario recovers
within budget.

### 5.1 Drill log

Record each drill in the table below (date, scenarios, measured RTO, result,
follow-ups).

| Date | Scenarios | Max RTO | Result | Follow-ups |
|---|---|---|---|---|
| 2026-05-31 | service, redis, gateway, backup | _record on first staging run_ | _pending_ | initial drill tooling landed |

---

## 6. Escalation

| Severity | Condition | Action |
|---|---|---|
| SEV-1 | Full outage / data loss risk | Page on-call; start §3.4; notify stakeholders |
| SEV-2 | One service down, replicas absorbing | Auto-recovery; monitor; investigate root cause |
| SEV-3 | Degraded latency (p99 > SLA) | Scale replicas (§1.2); check DB slow log |

---

## 7. References

- `docker-compose.ha.yml` — Swarm HA overlay (replicas, anti-affinity, rolling).
- `production/kubernetes/deployment-ha.yaml` — K8s Deployments + PDB + HPA.
- `production/ha/` — failover, replication, load-balancer, health-check helpers.
- `production/disaster-recovery/` — backup config, recovery procedures, DR test framework.
- `scripts/backup.sh` — MySQL + Redis backup automation.
- `scripts/dr-drill.sh` — automated DR drill.
- `PHASE3_IMPLEMENTATION_PLAN.md` §3.5.3–§3.5.4 — source requirements.
