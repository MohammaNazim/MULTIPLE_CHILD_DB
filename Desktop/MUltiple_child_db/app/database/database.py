# app/database/database.py

from pydantic_settings import BaseSettings
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    DATABASE_URL: str = Field(..., env="DATABASE_URL")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()

# 🔹 ASYNC ENGINE (FastAPI runtime)
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
    pool_pre_ping=True
)

AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# 🔹 BASE
Base = declarative_base()

# 🔹 SYNC ENGINE (Alembic only)
sync_engine = create_engine(
    settings.DATABASE_URL.replace("+asyncpg", ""),
    echo=True,
    pool_pre_ping=True
)


# 🔹 Dependency
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
