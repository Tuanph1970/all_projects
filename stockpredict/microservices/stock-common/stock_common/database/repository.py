"""
Base repository class for data access.

Provides:
- Common CRUD operations
- Query building utilities
- Transaction support
"""

import logging
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Generic type for models
T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    Base repository with common CRUD operations.

    Example:
        class UserRepository(BaseRepository[User]):
            def __init__(self, session: AsyncSession):
                super().__init__(session, User)

            async def find_by_email(self, email: str) -> Optional[User]:
                return await self.find_one(email=email)
    """

    def __init__(self, session: AsyncSession, model: Type[T]):
        self.session = session
        self.model = model

    async def create(self, **kwargs) -> T:
        """Create a new entity."""
        entity = self.model(**kwargs)
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        logger.debug(f"Created {self.model.__name__}: {entity}")
        return entity

    async def create_many(self, entities: List[Dict[str, Any]]) -> List[T]:
        """Create multiple entities."""
        objects = [self.model(**data) for data in entities]
        self.session.add_all(objects)
        await self.session.flush()
        for obj in objects:
            await self.session.refresh(obj)
        logger.debug(f"Created {len(objects)} {self.model.__name__} entities")
        return objects

    async def get_by_id(self, id: Any) -> Optional[T]:
        """Get entity by ID."""
        return await self.session.get(self.model, id)

    async def find_one(self, **filters) -> Optional[T]:
        """Find one entity matching filters."""
        query = select(self.model).filter_by(**filters)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def find_all(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None,
        **filters,
    ) -> List[T]:
        """Find all entities matching filters with pagination."""
        query = select(self.model).filter_by(**filters)

        if order_by:
            if order_by.startswith("-"):
                query = query.order_by(getattr(self.model, order_by[1:]).desc())
            else:
                query = query.order_by(getattr(self.model, order_by))

        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(self, **filters) -> int:
        """Count entities matching filters."""
        query = select(func.count()).select_from(self.model).filter_by(**filters)
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def exists(self, **filters) -> bool:
        """Check if entity exists."""
        return await self.count(**filters) > 0

    async def update(self, id: Any, **kwargs) -> Optional[T]:
        """Update entity by ID."""
        entity = await self.get_by_id(id)
        if entity:
            for key, value in kwargs.items():
                setattr(entity, key, value)
            await self.session.flush()
            await self.session.refresh(entity)
            logger.debug(f"Updated {self.model.__name__} {id}")
        return entity

    async def update_many(self, filters: Dict[str, Any], **updates) -> int:
        """Update multiple entities matching filters."""
        query = (
            update(self.model)
            .filter_by(**filters)
            .values(**updates)
        )
        result = await self.session.execute(query)
        await self.session.flush()
        logger.debug(f"Updated {result.rowcount} {self.model.__name__} entities")
        return result.rowcount

    async def delete(self, id: Any) -> bool:
        """Delete entity by ID."""
        entity = await self.get_by_id(id)
        if entity:
            await self.session.delete(entity)
            await self.session.flush()
            logger.debug(f"Deleted {self.model.__name__} {id}")
            return True
        return False

    async def delete_many(self, **filters) -> int:
        """Delete multiple entities matching filters."""
        query = delete(self.model).filter_by(**filters)
        result = await self.session.execute(query)
        await self.session.flush()
        logger.debug(f"Deleted {result.rowcount} {self.model.__name__} entities")
        return result.rowcount

    async def upsert(self, id_field: str, id_value: Any, **kwargs) -> T:
        """Update if exists, create otherwise."""
        entity = await self.find_one(**{id_field: id_value})
        if entity:
            for key, value in kwargs.items():
                setattr(entity, key, value)
            await self.session.flush()
            await self.session.refresh(entity)
        else:
            kwargs[id_field] = id_value
            entity = await self.create(**kwargs)
        return entity
