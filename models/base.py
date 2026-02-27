"""
BlogEngine - Configuración de base de datos SQLAlchemy async.
"""
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, func

from config import get_settings


class Base(DeclarativeBase):
    """Clase base para todos los modelos."""
    pass


class TimestampMixin:
    """Mixin para agregar campos de timestamp a los modelos."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


# Motor y sesión async
settings = get_settings()
engine = create_async_engine(
    settings.database_url,
    echo=settings.app_debug,
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    """Dependencia de FastAPI para obtener sesión de BD."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Crear todas las tablas."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
