import os
import hashlib
from fastapi import Security, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Annotated
from .repository import InMemoryApiKeyRepository, PostgresApiKeyRepository
from .models import ApiKey

# Usar InMemory por defecto, Postgres si hay DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    engine = create_async_engine(DATABASE_URL)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    _repo_instance = PostgresApiKeyRepository(SessionLocal)
else:
    _repo_instance = InMemoryApiKeyRepository()

security = HTTPBearer(auto_error=False)

async def get_api_key(creds: Annotated[HTTPAuthorizationCredentials, Security(security)]) -> ApiKey:
    if not creds or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = creds.credentials
    key_hash = hashlib.sha256(token.encode()).hexdigest()
    
    api_key = await _repo_instance.get_by_hash(key_hash)
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")
    
    if api_key.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Revoked API Key")
        
    if api_key.expires_at and api_key.expires_at < datetime.now():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Expired API Key")
        
    await _repo_instance.update_last_used(api_key.id)
    return api_key

def require_scope(required_scope: str):
    async def scope_checker(api_key: Annotated[ApiKey, Security(get_api_key)]):
        if required_scope not in api_key.scopes and "rules:admin" not in api_key.scopes:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing scope: {required_scope}")
        return api_key
    return scope_checker

# Función para inyectar en los tests (bypass)
async def get_api_key_test():
    # Retorna una API Key mock con todos los scopes para no romper los tests existentes
    return ApiKey(id="test", key_hash="test", name="test", status="ACTIVE", scopes=["rules:read", "rules:write", "rules:activate", "rules:evaluate", "rules:admin"], created_at=datetime.now())
