"""
Recovery Procedures

Provides disaster recovery procedures and execution utilities.
"""
import os
import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class RecoveryType(Enum):
    """Types of recovery operations"""
    FULL_RESTORE = "full_restore"           # Complete system restore
    DATABASE_RESTORE = "database_restore"    # Database only
    CACHE_RESTORE = "cache_restore"          # Cache only
    FILES_RESTORE = "files_restore"          # Files only
    POINT_IN_TIME = "point_in_time"          # PITR
    FAILOVER = "failover"                    # Failover to secondary
    ROLLBACK = "rollback"                    # Rollback to previous state


class RecoveryStatus(Enum):
    """Recovery operation status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class RecoverySeverity(Enum):
    """Recovery severity levels"""
    LOW = "low"         # Non-critical, scheduled recovery
    MEDIUM = "medium"   # Important, same-day recovery
    HIGH = "high"       # Critical, immediate recovery needed
    CRITICAL = "critical"  # System down, emergency recovery


@dataclass
class RecoveryStep:
    """Individual recovery step"""
    name: str
    description: str
    command: Optional[str] = None
    script: Optional[str] = None
    timeout_seconds: int = 300
    retryable: bool = True
    max_retries: int = 3
    rollback_command: Optional[str] = None
    validation_command: Optional[str] = None
    order: int = 0


@dataclass
class RecoveryProcedure:
    """Recovery procedure definition"""
    name: str
    recovery_type: RecoveryType
    description: str
    severity: RecoverySeverity
    steps: List[RecoveryStep] = field(default_factory=list)
    estimated_duration_minutes: int = 30
    requires_approval: bool = True
    notify_on_start: bool = True
    notify_on_complete: bool = True
    pre_checks: List[str] = field(default_factory=list)
    post_checks: List[str] = field(default_factory=list)


@dataclass
class RecoveryPlan:
    """Complete recovery plan"""
    plan_id: str
    name: str
    description: str
    procedures: List[RecoveryProcedure] = field(default_factory=list)
    target_rto_minutes: int = 60  # Recovery Time Objective
    target_rpo_minutes: int = 15  # Recovery Point Objective
    last_tested: Optional[datetime] = None
    version: str = "1.0"


@dataclass
class RecoveryExecution:
    """Recovery execution record"""
    execution_id: str
    procedure_name: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: RecoveryStatus = RecoveryStatus.PENDING
    current_step: int = 0
    total_steps: int = 0
    step_results: List[Dict[str, Any]] = field(default_factory=list)
    error_message: Optional[str] = None
    initiated_by: str = "system"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "procedure_name": self.procedure_name,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status.value,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "step_results": self.step_results,
            "error_message": self.error_message,
            "initiated_by": self.initiated_by,
        }


# Predefined recovery procedures
DATABASE_RESTORE_PROCEDURE = RecoveryProcedure(
    name="database_restore",
    recovery_type=RecoveryType.DATABASE_RESTORE,
    description="Restore PostgreSQL database from backup",
    severity=RecoverySeverity.HIGH,
    estimated_duration_minutes=45,
    pre_checks=[
        "check_backup_exists",
        "check_target_database_accessible",
        "check_sufficient_disk_space",
    ],
    steps=[
        RecoveryStep(
            name="stop_application",
            description="Stop all application services to prevent writes",
            command="docker-compose stop auth stock-data portfolio prediction analysis ai-insights chatbot",
            order=1,
            timeout_seconds=120,
        ),
        RecoveryStep(
            name="terminate_connections",
            description="Terminate existing database connections",
            command="psql -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'stockhelper' AND pid <> pg_backend_pid();\"",
            order=2,
            timeout_seconds=30,
        ),
        RecoveryStep(
            name="drop_database",
            description="Drop existing database",
            command="dropdb --if-exists stockhelper",
            order=3,
            timeout_seconds=60,
            rollback_command="echo 'Cannot rollback database drop'",
        ),
        RecoveryStep(
            name="create_database",
            description="Create empty database",
            command="createdb stockhelper",
            order=4,
            timeout_seconds=30,
        ),
        RecoveryStep(
            name="restore_database",
            description="Restore database from backup",
            command="pg_restore --dbname=stockhelper --jobs=4 --verbose /backups/latest.dump",
            order=5,
            timeout_seconds=1800,  # 30 minutes
        ),
        RecoveryStep(
            name="verify_restore",
            description="Verify database restore",
            validation_command="psql -c \"SELECT COUNT(*) FROM users;\"",
            order=6,
            timeout_seconds=60,
        ),
        RecoveryStep(
            name="run_migrations",
            description="Run any pending migrations",
            command="alembic upgrade head",
            order=7,
            timeout_seconds=300,
        ),
        RecoveryStep(
            name="start_application",
            description="Start application services",
            command="docker-compose up -d auth stock-data portfolio prediction analysis ai-insights chatbot",
            order=8,
            timeout_seconds=180,
        ),
        RecoveryStep(
            name="verify_health",
            description="Verify all services are healthy",
            validation_command="./scripts/check_health.sh",
            order=9,
            timeout_seconds=300,
        ),
    ],
    post_checks=[
        "verify_data_integrity",
        "verify_api_responses",
        "verify_user_authentication",
    ],
)

FAILOVER_PROCEDURE = RecoveryProcedure(
    name="failover_to_secondary",
    recovery_type=RecoveryType.FAILOVER,
    description="Failover to secondary datacenter/region",
    severity=RecoverySeverity.CRITICAL,
    estimated_duration_minutes=15,
    pre_checks=[
        "check_secondary_health",
        "check_replication_lag",
        "check_dns_ready",
    ],
    steps=[
        RecoveryStep(
            name="notify_stakeholders",
            description="Send failover notification",
            command="./scripts/notify.sh failover_started",
            order=1,
            timeout_seconds=30,
        ),
        RecoveryStep(
            name="stop_primary_traffic",
            description="Stop routing traffic to primary",
            command="./scripts/traffic_control.sh stop_primary",
            order=2,
            timeout_seconds=60,
        ),
        RecoveryStep(
            name="promote_secondary_db",
            description="Promote secondary database to primary",
            command="pg_ctl promote -D /var/lib/postgresql/data",
            order=3,
            timeout_seconds=60,
        ),
        RecoveryStep(
            name="update_dns",
            description="Update DNS to point to secondary",
            command="./scripts/update_dns.sh secondary",
            order=4,
            timeout_seconds=120,
        ),
        RecoveryStep(
            name="start_secondary_traffic",
            description="Start routing traffic to secondary",
            command="./scripts/traffic_control.sh start_secondary",
            order=5,
            timeout_seconds=60,
        ),
        RecoveryStep(
            name="verify_failover",
            description="Verify failover success",
            validation_command="./scripts/verify_failover.sh",
            order=6,
            timeout_seconds=300,
        ),
    ],
    post_checks=[
        "verify_all_services_responding",
        "verify_data_consistency",
        "monitor_error_rates",
    ],
)

POINT_IN_TIME_RECOVERY_PROCEDURE = RecoveryProcedure(
    name="point_in_time_recovery",
    recovery_type=RecoveryType.POINT_IN_TIME,
    description="Recover database to specific point in time",
    severity=RecoverySeverity.HIGH,
    estimated_duration_minutes=60,
    pre_checks=[
        "check_wal_archive_available",
        "check_base_backup_available",
        "check_target_time_valid",
    ],
    steps=[
        RecoveryStep(
            name="stop_application",
            description="Stop all application services",
            command="docker-compose stop",
            order=1,
            timeout_seconds=120,
        ),
        RecoveryStep(
            name="stop_postgres",
            description="Stop PostgreSQL",
            command="pg_ctl stop -D /var/lib/postgresql/data",
            order=2,
            timeout_seconds=60,
        ),
        RecoveryStep(
            name="backup_current_data",
            description="Backup current data directory",
            command="mv /var/lib/postgresql/data /var/lib/postgresql/data.backup",
            order=3,
            timeout_seconds=300,
        ),
        RecoveryStep(
            name="restore_base_backup",
            description="Restore base backup",
            command="pg_basebackup -D /var/lib/postgresql/data -Fp",
            order=4,
            timeout_seconds=900,
        ),
        RecoveryStep(
            name="configure_recovery",
            description="Configure recovery target",
            script="""
cat > /var/lib/postgresql/data/recovery.signal << EOF
# Recovery configuration
EOF
cat >> /var/lib/postgresql/data/postgresql.auto.conf << EOF
restore_command = 'cp /var/lib/postgresql/archive/%f %p'
recovery_target_time = '${RECOVERY_TARGET_TIME}'
recovery_target_action = 'promote'
EOF
            """,
            order=5,
            timeout_seconds=60,
        ),
        RecoveryStep(
            name="start_postgres",
            description="Start PostgreSQL in recovery mode",
            command="pg_ctl start -D /var/lib/postgresql/data",
            order=6,
            timeout_seconds=1800,  # Recovery can take time
        ),
        RecoveryStep(
            name="wait_recovery",
            description="Wait for recovery to complete",
            command="while [ -f /var/lib/postgresql/data/recovery.signal ]; do sleep 5; done",
            order=7,
            timeout_seconds=1800,
        ),
        RecoveryStep(
            name="verify_recovery",
            description="Verify recovery completed successfully",
            validation_command="psql -c 'SELECT pg_is_in_recovery();'",
            order=8,
            timeout_seconds=60,
        ),
        RecoveryStep(
            name="start_application",
            description="Start application services",
            command="docker-compose up -d",
            order=9,
            timeout_seconds=180,
        ),
    ],
    post_checks=[
        "verify_data_integrity",
        "verify_recovered_data",
    ],
)


# Recovery execution engine
class RecoveryExecutor:
    """Executes recovery procedures"""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.executions: Dict[str, RecoveryExecution] = {}

    async def execute_step(
        self,
        step: RecoveryStep,
        execution: RecoveryExecution
    ) -> Dict[str, Any]:
        """Execute a single recovery step"""
        result = {
            "step_name": step.name,
            "started_at": datetime.now().isoformat(),
            "success": False,
            "output": "",
            "error": None,
        }

        logger.info(f"Executing step: {step.name}")

        try:
            if self.dry_run:
                result["output"] = f"DRY RUN: Would execute - {step.command or step.script}"
                result["success"] = True
            else:
                if step.command:
                    result = await self._run_command(step.command, step.timeout_seconds)
                elif step.script:
                    result = await self._run_script(step.script, step.timeout_seconds)

                # Run validation if provided
                if result["success"] and step.validation_command:
                    validation = await self._run_command(
                        step.validation_command,
                        step.timeout_seconds
                    )
                    if not validation["success"]:
                        result["success"] = False
                        result["error"] = f"Validation failed: {validation.get('error')}"

        except Exception as e:
            result["error"] = str(e)
            result["success"] = False

        result["completed_at"] = datetime.now().isoformat()
        return result

    async def _run_command(self, command: str, timeout: int) -> Dict[str, Any]:
        """Run a shell command"""
        import subprocess

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            return {
                "success": process.returncode == 0,
                "output": stdout.decode(),
                "error": stderr.decode() if process.returncode != 0 else None,
            }

        except asyncio.TimeoutError:
            return {
                "success": False,
                "output": "",
                "error": f"Command timed out after {timeout} seconds",
            }

    async def _run_script(self, script: str, timeout: int) -> Dict[str, Any]:
        """Run a script"""
        import tempfile
        import os

        # Write script to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write("#!/bin/bash\nset -e\n" + script)
            script_path = f.name

        try:
            os.chmod(script_path, 0o755)
            result = await self._run_command(script_path, timeout)
        finally:
            os.unlink(script_path)

        return result

    async def execute_procedure(
        self,
        procedure: RecoveryProcedure,
        initiated_by: str = "system"
    ) -> RecoveryExecution:
        """Execute a complete recovery procedure"""
        import uuid

        execution = RecoveryExecution(
            execution_id=str(uuid.uuid4()),
            procedure_name=procedure.name,
            started_at=datetime.now(),
            status=RecoveryStatus.RUNNING,
            total_steps=len(procedure.steps),
            initiated_by=initiated_by,
        )

        self.executions[execution.execution_id] = execution
        logger.info(f"Starting recovery: {procedure.name}")

        # Sort steps by order
        sorted_steps = sorted(procedure.steps, key=lambda s: s.order)

        for i, step in enumerate(sorted_steps):
            execution.current_step = i + 1

            result = await self.execute_step(step, execution)
            execution.step_results.append(result)

            if not result["success"]:
                # Attempt retry if retryable
                if step.retryable:
                    for retry in range(step.max_retries):
                        logger.warning(f"Retrying step {step.name}, attempt {retry + 2}")
                        result = await self.execute_step(step, execution)
                        if result["success"]:
                            break

                if not result["success"]:
                    execution.status = RecoveryStatus.FAILED
                    execution.error_message = result.get("error")
                    execution.completed_at = datetime.now()
                    logger.error(f"Recovery failed at step: {step.name}")
                    return execution

        execution.status = RecoveryStatus.COMPLETED
        execution.completed_at = datetime.now()
        logger.info(f"Recovery completed: {procedure.name}")

        return execution


async def execute_recovery(
    procedure: RecoveryProcedure,
    dry_run: bool = True,
    initiated_by: str = "system"
) -> RecoveryExecution:
    """
    Execute a recovery procedure

    Args:
        procedure: Recovery procedure to execute
        dry_run: If True, simulate without making changes
        initiated_by: Who initiated the recovery

    Returns:
        RecoveryExecution result
    """
    executor = RecoveryExecutor(dry_run=dry_run)
    return await executor.execute_procedure(procedure, initiated_by)


# Predefined recovery plan
def get_default_recovery_plan() -> RecoveryPlan:
    """Get the default disaster recovery plan"""
    return RecoveryPlan(
        plan_id="dr-plan-001",
        name="StockHelper Disaster Recovery Plan",
        description="Comprehensive disaster recovery plan for StockHelper microservices",
        procedures=[
            DATABASE_RESTORE_PROCEDURE,
            FAILOVER_PROCEDURE,
            POINT_IN_TIME_RECOVERY_PROCEDURE,
        ],
        target_rto_minutes=60,
        target_rpo_minutes=15,
        version="1.0",
    )
