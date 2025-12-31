#!/usr/bin/env python3
"""
Continuous Sync Service
Real-time synchronization between Django and microservices during migration

This service listens for changes in Django and replicates them to microservices,
ensuring data consistency during the shadow mode period.

Usage:
    python sync_service.py --tables users,portfolios
    python sync_service.py --all
"""
import asyncio
import argparse
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from enum import Enum
import signal

import aio_pika
from sqlalchemy import create_engine, text, event
from sqlalchemy.ext.asyncio import create_async_engine

import sys
sys.path.append('..')
from config.settings import (
    DJANGO_DB, AUTH_DB, STOCK_DATA_DB, PORTFOLIO_DB,
    RABBITMQ_URL, REDIS_URL
)


class ChangeType(Enum):
    """Type of database change"""
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"


@dataclass
class ChangeEvent:
    """Represents a database change event"""
    table: str
    change_type: ChangeType
    record_id: int
    data: Dict[str, Any]
    timestamp: datetime
    source: str = "django"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "table": self.table,
            "change_type": self.change_type.value,
            "record_id": self.record_id,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChangeEvent":
        return cls(
            table=data["table"],
            change_type=ChangeType(data["change_type"]),
            record_id=data["record_id"],
            data=data["data"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            source=data.get("source", "django"),
        )


class SyncHandler:
    """Base class for table-specific sync handlers"""

    def __init__(self, target_db_config, logger: logging.Logger):
        self.target_db = target_db_config
        self.logger = logger
        self._engine = None

    @property
    def engine(self):
        if self._engine is None:
            self._engine = create_engine(self.target_db.connection_string)
        return self._engine

    async def handle_insert(self, event: ChangeEvent) -> bool:
        """Handle INSERT event"""
        raise NotImplementedError

    async def handle_update(self, event: ChangeEvent) -> bool:
        """Handle UPDATE event"""
        raise NotImplementedError

    async def handle_delete(self, event: ChangeEvent) -> bool:
        """Handle DELETE event"""
        raise NotImplementedError

    async def process(self, event: ChangeEvent) -> bool:
        """Process a change event"""
        try:
            if event.change_type == ChangeType.INSERT:
                return await self.handle_insert(event)
            elif event.change_type == ChangeType.UPDATE:
                return await self.handle_update(event)
            elif event.change_type == ChangeType.DELETE:
                return await self.handle_delete(event)
        except Exception as e:
            self.logger.error(f"Error processing {event.change_type.value} for {event.table}: {e}")
            return False

    def close(self):
        if self._engine:
            self._engine.dispose()


class UserSyncHandler(SyncHandler):
    """Sync handler for user changes"""

    def __init__(self, logger: logging.Logger):
        super().__init__(AUTH_DB, logger)

    async def handle_insert(self, event: ChangeEvent) -> bool:
        data = event.data
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO users (
                    legacy_id, username, email, password_hash,
                    first_name, last_name, is_active,
                    created_at, updated_at
                ) VALUES (
                    :id, :username, :email, :password,
                    :first_name, :last_name, :is_active,
                    :date_joined, NOW()
                )
                ON DUPLICATE KEY UPDATE
                    updated_at = NOW()
            """), data)
            conn.commit()
        self.logger.info(f"Synced user INSERT: {data.get('username')}")
        return True

    async def handle_update(self, event: ChangeEvent) -> bool:
        data = event.data
        with self.engine.connect() as conn:
            conn.execute(text("""
                UPDATE users SET
                    email = :email,
                    first_name = :first_name,
                    last_name = :last_name,
                    is_active = :is_active,
                    last_login_at = :last_login,
                    updated_at = NOW()
                WHERE legacy_id = :id
            """), data)
            conn.commit()
        self.logger.info(f"Synced user UPDATE: {data.get('username')}")
        return True

    async def handle_delete(self, event: ChangeEvent) -> bool:
        with self.engine.connect() as conn:
            conn.execute(text("""
                UPDATE users SET is_active = FALSE, updated_at = NOW()
                WHERE legacy_id = :id
            """), {"id": event.record_id})
            conn.commit()
        self.logger.info(f"Synced user DELETE (soft): {event.record_id}")
        return True


class PortfolioSyncHandler(SyncHandler):
    """Sync handler for portfolio changes"""

    def __init__(self, logger: logging.Logger):
        super().__init__(PORTFOLIO_DB, logger)

    async def handle_insert(self, event: ChangeEvent) -> bool:
        data = event.data
        with self.engine.connect() as conn:
            # Get mapped user_id
            user_result = conn.execute(text(
                "SELECT id FROM portfolios.users_view WHERE legacy_id = :user_id"
            ), {"user_id": data.get("user_id")}).fetchone()

            if user_result:
                data["mapped_user_id"] = user_result.id
            else:
                self.logger.warning(f"User mapping not found for user_id {data.get('user_id')}")
                data["mapped_user_id"] = None

            conn.execute(text("""
                INSERT INTO portfolios (
                    legacy_id, user_id, name, description,
                    is_default, currency, created_at, updated_at
                ) VALUES (
                    :id, :mapped_user_id, :name, :description,
                    :is_default, :currency, :created, NOW()
                )
                ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    updated_at = NOW()
            """), data)
            conn.commit()
        self.logger.info(f"Synced portfolio INSERT: {data.get('name')}")
        return True

    async def handle_update(self, event: ChangeEvent) -> bool:
        data = event.data
        with self.engine.connect() as conn:
            conn.execute(text("""
                UPDATE portfolios SET
                    name = :name,
                    description = :description,
                    updated_at = NOW()
                WHERE legacy_id = :id
            """), data)
            conn.commit()
        self.logger.info(f"Synced portfolio UPDATE: {data.get('name')}")
        return True

    async def handle_delete(self, event: ChangeEvent) -> bool:
        with self.engine.connect() as conn:
            # Soft delete
            conn.execute(text("""
                UPDATE portfolios SET is_active = FALSE, updated_at = NOW()
                WHERE legacy_id = :id
            """), {"id": event.record_id})
            conn.commit()
        self.logger.info(f"Synced portfolio DELETE (soft): {event.record_id}")
        return True


class HoldingSyncHandler(SyncHandler):
    """Sync handler for holding changes"""

    def __init__(self, logger: logging.Logger):
        super().__init__(PORTFOLIO_DB, logger)

    async def handle_insert(self, event: ChangeEvent) -> bool:
        data = event.data
        with self.engine.connect() as conn:
            # Get mapped portfolio_id
            portfolio_result = conn.execute(text(
                "SELECT id FROM portfolios WHERE legacy_id = :portfolio_id"
            ), {"portfolio_id": data.get("portfolio_id")}).fetchone()

            data["mapped_portfolio_id"] = portfolio_result.id if portfolio_result else None

            conn.execute(text("""
                INSERT INTO holdings (
                    legacy_id, portfolio_id, symbol, quantity,
                    average_cost, created_at, updated_at
                ) VALUES (
                    :id, :mapped_portfolio_id, :symbol, :quantity,
                    :average_cost, NOW(), NOW()
                )
                ON DUPLICATE KEY UPDATE
                    quantity = VALUES(quantity),
                    updated_at = NOW()
            """), data)
            conn.commit()
        self.logger.info(f"Synced holding INSERT: {data.get('symbol')}")
        return True

    async def handle_update(self, event: ChangeEvent) -> bool:
        data = event.data
        with self.engine.connect() as conn:
            conn.execute(text("""
                UPDATE holdings SET
                    quantity = :quantity,
                    average_cost = :average_cost,
                    updated_at = NOW()
                WHERE legacy_id = :id
            """), data)
            conn.commit()
        self.logger.info(f"Synced holding UPDATE: {data.get('symbol')}")
        return True

    async def handle_delete(self, event: ChangeEvent) -> bool:
        with self.engine.connect() as conn:
            conn.execute(text("""
                DELETE FROM holdings WHERE legacy_id = :id
            """), {"id": event.record_id})
            conn.commit()
        self.logger.info(f"Synced holding DELETE: {event.record_id}")
        return True


class ContinuousSyncService:
    """Main sync service that coordinates all sync handlers"""

    def __init__(self, tables: List[str] = None):
        self.logger = logging.getLogger("sync.service")
        self.running = False
        self.connection = None
        self.channel = None

        # Initialize handlers for specified tables
        all_handlers = {
            "users": UserSyncHandler(self.logger),
            "portfolios": PortfolioSyncHandler(self.logger),
            "holdings": HoldingSyncHandler(self.logger),
        }

        if tables:
            self.handlers = {t: h for t, h in all_handlers.items() if t in tables}
        else:
            self.handlers = all_handlers

        # Stats
        self.stats = {
            "events_received": 0,
            "events_processed": 0,
            "events_failed": 0,
            "started_at": None,
        }

    async def connect(self):
        """Connect to RabbitMQ"""
        self.connection = await aio_pika.connect_robust(RABBITMQ_URL)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=10)
        self.logger.info("Connected to RabbitMQ")

    async def process_message(self, message: aio_pika.IncomingMessage):
        """Process a single change message"""
        async with message.process():
            try:
                self.stats["events_received"] += 1
                data = json.loads(message.body.decode())
                event = ChangeEvent.from_dict(data)

                # Find appropriate handler
                handler = self.handlers.get(event.table)
                if handler:
                    success = await handler.process(event)
                    if success:
                        self.stats["events_processed"] += 1
                    else:
                        self.stats["events_failed"] += 1
                else:
                    self.logger.debug(f"No handler for table: {event.table}")

            except Exception as e:
                self.stats["events_failed"] += 1
                self.logger.error(f"Error processing message: {e}")

    async def start(self):
        """Start the sync service"""
        self.running = True
        self.stats["started_at"] = datetime.utcnow().isoformat()

        await self.connect()

        # Declare queues for each table
        for table_name in self.handlers.keys():
            queue_name = f"django.{table_name}.changes"
            queue = await self.channel.declare_queue(queue_name, durable=True)
            await queue.consume(self.process_message)
            self.logger.info(f"Listening on queue: {queue_name}")

        self.logger.info(f"Sync service started for tables: {list(self.handlers.keys())}")

        # Keep running
        while self.running:
            await asyncio.sleep(1)

    async def stop(self):
        """Stop the sync service"""
        self.running = False

        for handler in self.handlers.values():
            handler.close()

        if self.channel:
            await self.channel.close()
        if self.connection:
            await self.connection.close()

        self.logger.info("Sync service stopped")
        self.logger.info(f"Stats: {self.stats}")

    def get_stats(self) -> Dict[str, Any]:
        """Get current service statistics"""
        return {
            **self.stats,
            "handlers_active": list(self.handlers.keys()),
            "is_running": self.running,
        }


async def main():
    parser = argparse.ArgumentParser(description="Continuous sync service")
    parser.add_argument(
        "--tables",
        help="Comma-separated list of tables to sync"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Sync all supported tables"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    tables = None
    if args.tables:
        tables = [t.strip() for t in args.tables.split(",")]

    service = ContinuousSyncService(tables=tables)

    # Handle shutdown signals
    loop = asyncio.get_event_loop()

    def signal_handler():
        asyncio.create_task(service.stop())

    loop.add_signal_handler(signal.SIGINT, signal_handler)
    loop.add_signal_handler(signal.SIGTERM, signal_handler)

    print("\n=== Continuous Sync Service ===")
    print(f"Tables: {tables or 'all'}")
    print("Press Ctrl+C to stop\n")

    try:
        await service.start()
    except KeyboardInterrupt:
        pass
    finally:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())
