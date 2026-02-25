"""Singleton Neo4j async driver manager."""
import logging
from neo4j import AsyncGraphDatabase, AsyncDriver

logger = logging.getLogger(__name__)

_driver: AsyncDriver | None = None


async def get_neo4j_driver(uri: str, user: str = "", password: str = "") -> AsyncDriver:
    """Get or create a singleton Neo4j async driver."""
    global _driver
    if _driver is None:
        auth = (user, password) if user and password else None
        _driver = AsyncGraphDatabase.driver(uri, auth=auth)
        logger.info(f"Neo4j driver created for {uri}")
    return _driver


async def close_neo4j_driver() -> None:
    """Close the Neo4j driver."""
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None
        logger.info("Neo4j driver closed")
