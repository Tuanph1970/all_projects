"""HA + DR configuration validation tests (Phase 3.5 §3.5.3 / §3.5.4).

These are static validation tests — they assert that the HA/DR artifacts exist
and encode the required properties (replicas, anti-affinity, zero-downtime
rolling updates, resource limits, health probes, backup/drill tooling, runbook
coverage). They do NOT require a running stack, so they run in unit-test CI.

The live failover behaviour is exercised separately by scripts/dr-drill.sh
against a deployed stack.
"""
from __future__ import annotations

import os
import re
import stat
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

REPO = Path(__file__).resolve().parents[2]   # stock_microservices/
HA_COMPOSE = REPO / "docker-compose.ha.yml"
K8S_HA = REPO / "production" / "kubernetes" / "deployment-ha.yaml"
BACKUP_SH = REPO / "scripts" / "backup.sh"
DRILL_SH = REPO / "scripts" / "dr-drill.sh"
RUNBOOK = REPO / "production" / "docs" / "DR_RUNBOOK.md"

# Core stateless services that must be highly available.
HA_SERVICES = ["auth-service", "stock-data-service", "portfolio-service"]


# ── docker-compose.ha.yml ─────────────────────────────────────────────────────

class TestHAComposeOverlay:
    def test_file_exists(self):
        assert HA_COMPOSE.is_file(), "docker-compose.ha.yml missing"

    @pytest.fixture
    def compose(self):
        with open(HA_COMPOSE) as f:
            return yaml.safe_load(f)

    def test_core_services_have_multiple_replicas(self, compose):
        services = compose["services"]
        for name in HA_SERVICES:
            assert name in services, f"{name} missing from HA overlay"
            replicas = services[name]["deploy"]["replicas"]
            assert replicas >= 2, f"{name} must have >= 2 replicas, got {replicas}"

    def test_stock_data_has_three_replicas(self, compose):
        # Highest-traffic read service per the runbook topology.
        assert compose["services"]["stock-data-service"]["deploy"]["replicas"] == 3

    def test_zero_downtime_rolling_update(self, compose):
        # start-first ensures a new task is up before the old one stops
        # (the Swarm equivalent of K8s maxUnavailable=0).
        for name in HA_SERVICES:
            update = compose["services"][name]["deploy"]["update_config"]
            assert update["order"] == "start-first", (
                f"{name} update_config.order must be start-first for zero downtime"
            )
            assert update.get("failure_action") == "rollback"

    def test_anti_affinity_present(self, compose):
        # max_replicas_per_node spreads replicas across nodes.
        for name in HA_SERVICES:
            placement = compose["services"][name]["deploy"]["placement"]
            assert "max_replicas_per_node" in placement, (
                f"{name} must define anti-affinity via max_replicas_per_node"
            )

    def test_resource_limits_present(self, compose):
        for name in HA_SERVICES:
            resources = compose["services"][name]["deploy"]["resources"]
            assert "limits" in resources and "reservations" in resources
            assert "memory" in resources["limits"]
            assert "cpus" in resources["limits"]

    def test_restart_policy_present(self, compose):
        for name in HA_SERVICES:
            rp = compose["services"][name]["deploy"]["restart_policy"]
            assert rp["condition"] in ("any", "on-failure")


# ── Kubernetes manifests ──────────────────────────────────────────────────────

class TestKubernetesHA:
    def test_file_exists(self):
        assert K8S_HA.is_file(), "production/kubernetes/deployment-ha.yaml missing"

    @pytest.fixture
    def docs(self):
        with open(K8S_HA) as f:
            return [d for d in yaml.safe_load_all(f) if d]

    def test_deployments_present(self, docs):
        deployments = {d["metadata"]["name"]: d
                       for d in docs if d.get("kind") == "Deployment"}
        for name in HA_SERVICES:
            assert name in deployments, f"Deployment {name} missing"
            assert deployments[name]["spec"]["replicas"] >= 2

    def test_zero_downtime_strategy(self, docs):
        for d in docs:
            if d.get("kind") != "Deployment":
                continue
            ru = d["spec"]["strategy"]["rollingUpdate"]
            assert ru["maxUnavailable"] == 0, (
                f"{d['metadata']['name']} must set maxUnavailable=0"
            )

    def test_pod_anti_affinity(self, docs):
        for d in docs:
            if d.get("kind") != "Deployment":
                continue
            affinity = d["spec"]["template"]["spec"]["affinity"]
            assert "podAntiAffinity" in affinity, (
                f"{d['metadata']['name']} must define podAntiAffinity"
            )

    def test_liveness_and_readiness_probes(self, docs):
        for d in docs:
            if d.get("kind") != "Deployment":
                continue
            container = d["spec"]["template"]["spec"]["containers"][0]
            assert "livenessProbe" in container
            assert "readinessProbe" in container
            assert container["livenessProbe"]["httpGet"]["path"] == "/health/live"
            assert container["readinessProbe"]["httpGet"]["path"] == "/health/ready"

    def test_resource_requests_and_limits(self, docs):
        for d in docs:
            if d.get("kind") != "Deployment":
                continue
            res = d["spec"]["template"]["spec"]["containers"][0]["resources"]
            assert "requests" in res and "limits" in res

    def test_pod_disruption_budgets(self, docs):
        pdbs = [d for d in docs if d.get("kind") == "PodDisruptionBudget"]
        assert len(pdbs) >= len(HA_SERVICES), "expected a PDB per HA service"
        for pdb in pdbs:
            assert "minAvailable" in pdb["spec"]


# ── Backup + drill scripts ────────────────────────────────────────────────────

class TestBackupScript:
    def test_exists_and_executable(self):
        assert BACKUP_SH.is_file(), "scripts/backup.sh missing"
        mode = BACKUP_SH.stat().st_mode
        assert mode & stat.S_IXUSR, "backup.sh must be executable"

    def test_covers_mysql_and_redis(self):
        text = BACKUP_SH.read_text()
        assert "backup_mysql" in text
        assert "backup_redis" in text
        assert "mysqldump" in text
        assert "RETENTION_DAYS" in text

    def test_has_strict_mode(self):
        assert "set -euo pipefail" in BACKUP_SH.read_text()


class TestDrillScript:
    def test_exists_and_executable(self):
        assert DRILL_SH.is_file(), "scripts/dr-drill.sh missing"
        assert DRILL_SH.stat().st_mode & stat.S_IXUSR, "dr-drill.sh must be executable"

    def test_covers_all_scenarios(self):
        text = DRILL_SH.read_text()
        for fn in ("drill_service", "drill_redis", "drill_gateway", "drill_backup"):
            assert fn in text, f"dr-drill.sh missing {fn}"

    def test_measures_rto_against_budget(self):
        text = DRILL_SH.read_text()
        assert "RTO_BUDGET_SECONDS" in text
        assert "print_summary" in text

    def test_does_not_delete_volumes(self):
        # Safety: the drill must never run `docker ... down -v` or volume rm.
        text = DRILL_SH.read_text()
        assert "down -v" not in text
        assert "volume rm" not in text
        assert not re.search(r"docker\s+volume\s+rm", text)


# ── Runbook ───────────────────────────────────────────────────────────────────

class TestDRRunbook:
    def test_exists(self):
        assert RUNBOOK.is_file(), "production/docs/DR_RUNBOOK.md missing"

    def test_defines_rpo_and_rto(self):
        text = RUNBOOK.read_text()
        assert "RPO" in text and "RTO" in text
        assert re.search(r"1\s*hour", text), "RPO target (1 hour) must be stated"
        assert re.search(r"4\s*hours", text), "RTO target (4 hours) must be stated"

    def test_covers_required_sections(self):
        text = RUNBOOK.read_text()
        for section in [
            "High-Availability Architecture",
            "Backup Strategy",
            "Recovery Procedures",
            "Post-Recovery Verification",
            "DR Drill",
            "Escalation",
        ]:
            assert section in text, f"runbook missing section: {section}"

    def test_documents_recovery_for_each_failure_mode(self):
        text = RUNBOOK.read_text().lower()
        for mode in ["service failure", "database failure", "redis failure", "complete outage"]:
            assert mode in text, f"runbook missing recovery for: {mode}"
