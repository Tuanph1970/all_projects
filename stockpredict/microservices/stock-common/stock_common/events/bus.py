"""
Event bus implementation using RabbitMQ.

Provides async event publishing and consuming with:
- Topic-based routing
- Automatic reconnection
- Dead letter queues
- Message acknowledgment
"""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional

import aio_pika
from aio_pika import ExchangeType, Message
from aio_pika.abc import AbstractChannel, AbstractConnection, AbstractExchange, AbstractQueue

from stock_common.config import RabbitMQConfig
from stock_common.events.models import Event

logger = logging.getLogger(__name__)


class EventBus:
    """
    Async event bus for RabbitMQ-based event-driven communication.

    Supports:
    - Topic-based routing with wildcards
    - Automatic reconnection on connection loss
    - Dead letter queues for failed messages
    - Message acknowledgment and rejection
    """

    def __init__(
        self,
        config: RabbitMQConfig,
        service_name: str = "unknown-service",
    ):
        self.config = config
        self.service_name = service_name
        self._connection: Optional[AbstractConnection] = None
        self._channel: Optional[AbstractChannel] = None
        self._exchange: Optional[AbstractExchange] = None
        self._consumers: Dict[str, AbstractQueue] = {}
        self._handlers: Dict[str, List[Callable]] = {}
        self._is_connected = False

    async def connect(self) -> None:
        """Establish connection to RabbitMQ."""
        if self._is_connected:
            return

        try:
            self._connection = await aio_pika.connect_robust(
                self.config.url,
                client_properties={"connection_name": self.service_name},
            )
            self._channel = await self._connection.channel()
            await self._channel.set_qos(prefetch_count=self.config.prefetch_count)

            # Declare the main topic exchange
            self._exchange = await self._channel.declare_exchange(
                self.config.exchange,
                ExchangeType.TOPIC,
                durable=True,
            )

            # Declare dead letter exchange
            self._dlx = await self._channel.declare_exchange(
                f"{self.config.exchange}.dlx",
                ExchangeType.TOPIC,
                durable=True,
            )

            self._is_connected = True
            logger.info(f"Connected to RabbitMQ at {self.config.host}:{self.config.port}")

        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def disconnect(self) -> None:
        """Close connection to RabbitMQ."""
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
            self._is_connected = False
            logger.info("Disconnected from RabbitMQ")

    async def publish(
        self,
        event: Event,
        routing_key: Optional[str] = None,
    ) -> None:
        """
        Publish an event to the message broker.

        Args:
            event: The event to publish
            routing_key: Optional routing key (defaults to event_type)
        """
        if not self._is_connected:
            await self.connect()

        routing_key = routing_key or event.event_type
        event.metadata.source_service = self.service_name

        message = Message(
            body=event.model_dump_json().encode(),
            content_type="application/json",
            message_id=event.metadata.event_id,
            correlation_id=event.metadata.correlation_id,
            timestamp=event.metadata.timestamp,
            headers={
                "event_type": event.event_type,
                "source_service": self.service_name,
                "version": event.metadata.version,
            },
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )

        await self._exchange.publish(message, routing_key=routing_key)
        logger.debug(f"Published event {event.event_type} with ID {event.metadata.event_id}")

    async def subscribe(
        self,
        event_pattern: str,
        handler: Callable[[Event], Any],
        queue_name: Optional[str] = None,
        durable: bool = True,
    ) -> None:
        """
        Subscribe to events matching a pattern.

        Args:
            event_pattern: Routing key pattern (e.g., 'stock.*', 'prediction.training.*')
            handler: Async function to handle incoming events
            queue_name: Optional queue name (auto-generated if not provided)
            durable: Whether the queue should survive broker restarts
        """
        if not self._is_connected:
            await self.connect()

        queue_name = queue_name or f"{self.service_name}.{event_pattern.replace('*', 'all').replace('#', 'wildcard')}"

        # Declare queue with dead letter exchange
        queue = await self._channel.declare_queue(
            queue_name,
            durable=durable,
            arguments={
                "x-dead-letter-exchange": f"{self.config.exchange}.dlx",
                "x-dead-letter-routing-key": f"dead.{event_pattern}",
            },
        )

        # Bind queue to exchange with pattern
        await queue.bind(self._exchange, routing_key=event_pattern)

        # Store handler
        if event_pattern not in self._handlers:
            self._handlers[event_pattern] = []
        self._handlers[event_pattern].append(handler)

        # Start consuming
        async def process_message(message: aio_pika.IncomingMessage) -> None:
            async with message.process():
                try:
                    event_data = json.loads(message.body.decode())
                    event = Event(**event_data)

                    for h in self._handlers.get(event_pattern, []):
                        await h(event)

                    logger.debug(f"Processed event {event.event_type}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    # Message will be nacked and sent to DLQ
                    raise

        await queue.consume(process_message)
        self._consumers[event_pattern] = queue
        logger.info(f"Subscribed to events matching '{event_pattern}' on queue '{queue_name}'")

    async def unsubscribe(self, event_pattern: str) -> None:
        """Unsubscribe from an event pattern."""
        if event_pattern in self._consumers:
            await self._consumers[event_pattern].cancel()
            del self._consumers[event_pattern]
            if event_pattern in self._handlers:
                del self._handlers[event_pattern]
            logger.info(f"Unsubscribed from events matching '{event_pattern}'")

    @property
    def is_connected(self) -> bool:
        """Check if connected to RabbitMQ."""
        return self._is_connected and self._connection and not self._connection.is_closed

    async def __aenter__(self) -> "EventBus":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.disconnect()


# Global event bus instance (lazy initialization)
_event_bus: Optional[EventBus] = None


def get_event_bus(config: RabbitMQConfig, service_name: str) -> EventBus:
    """Get or create the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus(config, service_name)
    return _event_bus
