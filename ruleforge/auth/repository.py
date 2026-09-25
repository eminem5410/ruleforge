from typing import Optional, List
from datetime import datetime
from .models import ApiKey, ApiKeyModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

class InMemoryApiKeyRepository:
    def __init__(self):
        self._store = {}

    async def create(self, key_hash: str, name: str, scopes: List[str]) -> ApiKey:
        import uuid
        key_id = str(uuid.uuid4())
        now = datetime.now()
        api_key = ApiKey(id=key_id, key_hash=key_hash, name=name, status="ACTIVE", scopes=scopes, created_at=now)
        self._store[key_hash] = api_key
        return api_key

    async def get_by_hash(self, key_hash: str) -> Optional[ApiKey]:
        return self._store.get(key_hash)

    async def update_last_used(self, key_id: str):
        pass # No-op for in-memory

class PostgresApiKeyRepository:
    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory

    async def create(self, key_hash: str, name: str, scopes: List[str]) -> ApiKey:
        async with self.session_factory() as session:
            db_key = ApiKeyModel(key_hash=key_hash, name=name, scopes=scopes)
            session.add(db_key)
            await session.commit()
            await session.refresh(db_key)
            return ApiKey(**db_key.__dict__)

    async def get_by_hash(self, key_hash: str) -> Optional[ApiKey]:
        async with self.session_factory() as session:
            stmt = select(ApiKeyModel).where(ApiKeyModel.key_hash == key_hash)
            res = await session.execute(stmt)
            model = res.scalar_one_or_none()
            if not model:
                return None
            return ApiKey(**model.__dict__)

    async def update_last_used(self, key_id: str):
        async with self.session_factory() as session:
            stmt = select(ApiKeyModel).where(ApiKeyModel.id == key_id)
            res = await session.execute(stmt)
            model = res.scalar_one_or_none()
            if model:
                model.last_used_at = datetime.now()
                await session.commit()
