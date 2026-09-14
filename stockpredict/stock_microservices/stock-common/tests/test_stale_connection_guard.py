"""Stale pooled-connection guard (stock_common.database.connection).

Regression for the "first request after an idle gap returns HTTP 500 and the
UI shows N/A" bug: asyncmy under uvloop raises a bare RuntimeError on a
server-closed socket, which SQLAlchemy's pool_pre_ping does not treat as a
disconnect.
"""
from unittest.mock import MagicMock

import pytest
from sqlalchemy import exc
from sqlalchemy.ext.asyncio import create_async_engine

from stock_common.database.connection import (
    install_stale_connection_guard,
    ping_or_discard,
)


def test_healthy_connection_passes_through():
    conn = MagicMock()
    ping_or_discard(conn)
    conn.ping.assert_called_once_with(False)


def test_uvloop_runtime_error_becomes_disconnection_error():
    conn = MagicMock()
    conn.ping.side_effect = RuntimeError(
        "unable to perform operation on <TCPTransport closed=True>; the handler is closed"
    )
    with pytest.raises(exc.DisconnectionError):
        ping_or_discard(conn)


def test_dbapi_operational_error_becomes_disconnection_error():
    conn = MagicMock()
    conn.ping.side_effect = Exception("(2013, 'Lost connection to MySQL server during query')")
    with pytest.raises(exc.DisconnectionError):
        ping_or_discard(conn)


def test_guard_registers_checkout_listener():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        assert len(list(engine.sync_engine.pool.dispatch.checkout)) == 0
        install_stale_connection_guard(engine)
        assert len(list(engine.sync_engine.pool.dispatch.checkout)) == 1
    finally:
        engine.sync_engine.dispose()
