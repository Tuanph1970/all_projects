"""
Feature Flag Storage Service
Redis-backed storage for feature flags with caching
"""
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import hashlib

import redis.asyncio as redis

from app.config import settings, DEFAULT_FLAGS, CUTOVER_PHASES
from app.models.flag import (
    FeatureFlag, FlagUpdate, FlagEvaluation, EvaluationContext, AuditLogEntry
)


logger = logging.getLogger(__name__)


class FlagStore:
    """Redis-backed feature flag storage"""

    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.prefix = "ff:"  # Feature flags prefix
        self._local_cache: Dict[str, FeatureFlag] = {}
        self._cache_ttl = 5  # Local cache TTL in seconds

    async def initialize(self):
        """Initialize Redis connection"""
        self.redis = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        logger.info("Feature flag store initialized")

    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()

    async def load_defaults(self):
        """Load default flags if not already set"""
        for flag_name, flag_config in DEFAULT_FLAGS.items():
            exists = await self.redis.exists(f"{self.prefix}flag:{flag_name}")
            if not exists:
                flag = FeatureFlag(name=flag_name, **flag_config)
                await self.set_flag(flag)
                logger.info(f"Loaded default flag: {flag_name}")

    async def get_flag(self, name: str) -> Optional[FeatureFlag]:
        """Get a feature flag by name"""
        data = await self.redis.get(f"{self.prefix}flag:{name}")
        if data:
            return FeatureFlag(**json.loads(data))
        return None

    async def set_flag(self, flag: FeatureFlag) -> None:
        """Set a feature flag"""
        flag.updated_at = datetime.utcnow()
        await self.redis.set(
            f"{self.prefix}flag:{flag.name}",
            json.dumps(flag.model_dump(), default=str)
        )
        self._local_cache[flag.name] = flag

    async def update_flag(
        self,
        name: str,
        update: FlagUpdate,
        actor: str = "system"
    ) -> Optional[FeatureFlag]:
        """Update a feature flag"""
        flag = await self.get_flag(name)
        if not flag:
            return None

        # Store previous value for audit
        previous = flag.model_dump()

        # Apply updates
        if update.enabled is not None:
            flag.enabled = update.enabled
        if update.percentage is not None:
            flag.percentage = update.percentage
        if update.description is not None:
            flag.description = update.description
        if update.user_whitelist is not None:
            flag.user_whitelist = update.user_whitelist
        if update.group_whitelist is not None:
            flag.group_whitelist = update.group_whitelist
        if update.metadata is not None:
            flag.metadata.update(update.metadata)

        await self.set_flag(flag)

        # Create audit log
        await self._log_audit(
            action="update",
            flag_name=name,
            previous_value=previous,
            new_value=flag.model_dump(),
            actor=actor
        )

        return flag

    async def delete_flag(self, name: str, actor: str = "system") -> bool:
        """Delete a feature flag"""
        flag = await self.get_flag(name)
        if not flag:
            return False

        await self.redis.delete(f"{self.prefix}flag:{name}")
        self._local_cache.pop(name, None)

        await self._log_audit(
            action="delete",
            flag_name=name,
            previous_value=flag.model_dump(),
            actor=actor
        )

        return True

    async def get_all_flags(self) -> Dict[str, FeatureFlag]:
        """Get all feature flags"""
        flags = {}
        cursor = 0

        while True:
            cursor, keys = await self.redis.scan(
                cursor=cursor,
                match=f"{self.prefix}flag:*",
                count=100
            )

            for key in keys:
                name = key.replace(f"{self.prefix}flag:", "")
                flag = await self.get_flag(name)
                if flag:
                    flags[name] = flag

            if cursor == 0:
                break

        return flags

    async def evaluate_flag(
        self,
        name: str,
        context: EvaluationContext
    ) -> FlagEvaluation:
        """Evaluate a feature flag for a given context"""
        flag = await self.get_flag(name)

        if not flag:
            return FlagEvaluation(
                flag_name=name,
                enabled=False,
                use_microservice=False,
                reason="Flag not found"
            )

        if not flag.enabled:
            return FlagEvaluation(
                flag_name=name,
                enabled=False,
                use_microservice=False,
                reason="Flag disabled"
            )

        # Check user whitelist
        if context.user_id and context.user_id in flag.user_whitelist:
            return FlagEvaluation(
                flag_name=name,
                enabled=True,
                use_microservice=True,
                reason="User in whitelist"
            )

        # Check group whitelist
        if context.user_groups:
            for group in context.user_groups:
                if group in flag.group_whitelist:
                    return FlagEvaluation(
                        flag_name=name,
                        enabled=True,
                        use_microservice=True,
                        reason=f"User in whitelisted group: {group}"
                    )

        # Percentage-based routing
        if flag.percentage == 100:
            return FlagEvaluation(
                flag_name=name,
                enabled=True,
                use_microservice=True,
                reason="100% traffic to microservice"
            )

        if flag.percentage == 0:
            return FlagEvaluation(
                flag_name=name,
                enabled=True,
                use_microservice=False,
                reason="0% traffic to microservice"
            )

        # Consistent hashing for percentage-based routing
        hash_input = f"{name}:{context.user_id or context.request_id or 'anonymous'}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        bucket = hash_value % 100

        use_microservice = bucket < flag.percentage

        return FlagEvaluation(
            flag_name=name,
            enabled=True,
            use_microservice=use_microservice,
            reason=f"Percentage routing ({flag.percentage}%): bucket={bucket}"
        )

    async def apply_phase(
        self,
        phase_name: str,
        actor: str = "system",
        dry_run: bool = False
    ) -> List[Dict[str, Any]]:
        """Apply a cutover phase to all flags"""
        if phase_name not in CUTOVER_PHASES:
            raise ValueError(f"Unknown phase: {phase_name}")

        phase = CUTOVER_PHASES[phase_name]
        changes = []

        for flag_name, percentage in phase["percentages"].items():
            flag = await self.get_flag(flag_name)
            if not flag:
                continue

            old_percentage = flag.percentage

            if not dry_run:
                await self.update_flag(
                    flag_name,
                    FlagUpdate(percentage=percentage),
                    actor=actor
                )

            changes.append({
                "flag": flag_name,
                "old_percentage": old_percentage,
                "new_percentage": percentage,
                "applied": not dry_run
            })

        # Store current phase
        if not dry_run:
            await self.redis.set(f"{self.prefix}current_phase", phase_name)

        return changes

    async def get_current_phase(self) -> Optional[str]:
        """Get current cutover phase"""
        return await self.redis.get(f"{self.prefix}current_phase")

    async def _log_audit(
        self,
        action: str,
        flag_name: str,
        previous_value: Optional[Dict] = None,
        new_value: Optional[Dict] = None,
        actor: str = "system",
        reason: Optional[str] = None
    ):
        """Log an audit entry"""
        entry = AuditLogEntry(
            action=action,
            flag_name=flag_name,
            previous_value=previous_value,
            new_value=new_value,
            actor=actor,
            reason=reason
        )

        # Store in Redis list (keep last 1000 entries)
        await self.redis.lpush(
            f"{self.prefix}audit_log",
            json.dumps(entry.model_dump(), default=str)
        )
        await self.redis.ltrim(f"{self.prefix}audit_log", 0, 999)

        logger.info(f"Audit: {action} {flag_name} by {actor}")

    async def get_audit_log(self, limit: int = 100) -> List[AuditLogEntry]:
        """Get recent audit log entries"""
        entries = await self.redis.lrange(f"{self.prefix}audit_log", 0, limit - 1)
        return [AuditLogEntry(**json.loads(e)) for e in entries]
