---
name: sqlalchemy-patterns
description: SQLAlchemy 2.0 patterns — ORM models, async sessions, relationships, queries, Alembic migrations, repository pattern, and performance optimization.
origin: custom
---

# SQLAlchemy 2.0 Patterns

Modern SQLAlchemy patterns for building robust data access layers.

## When to Activate

- Designing database models with SQLAlchemy
- Writing database queries (sync or async)
- Setting up Alembic migrations
- Implementing repository pattern
- Optimizing query performance

## Database Setup (Async)

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

## Model Patterns

### Base Model with Common Fields

```python
from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    name: Mapped[str]
    hashed_password: Mapped[str]
    is_active: Mapped[bool] = mapped_column(default=True)

    # Relationships
    posts: Mapped[list["Post"]] = relationship(back_populates="author", lazy="selectin")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"
```

### Relationships

```python
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

class Post(TimestampMixin, Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    content: Mapped[str]
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # Many-to-one
    author: Mapped["User"] = relationship(back_populates="posts")

    # Many-to-many
    tags: Mapped[list["Tag"]] = relationship(secondary="post_tags", back_populates="posts")

# Association table for many-to-many
from sqlalchemy import Table, Column, Integer, ForeignKey

post_tags = Table(
    "post_tags",
    Base.metadata,
    Column("post_id", Integer, ForeignKey("posts.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)

class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)

    posts: Mapped[list["Post"]] = relationship(secondary="post_tags", back_populates="tags")
```

### Enum and JSON Fields

```python
import enum
from sqlalchemy import Enum, JSON
from sqlalchemy.dialects.postgresql import JSONB

class UserRole(enum.Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
```

## Query Patterns (2.0 Style)

### Basic Queries

```python
from sqlalchemy import select, func

# Get by ID
stmt = select(User).where(User.id == user_id)
result = await session.execute(stmt)
user = result.scalar_one_or_none()

# Filter with multiple conditions
stmt = select(User).where(User.is_active == True, User.role == UserRole.ADMIN)
result = await session.execute(stmt)
admins = result.scalars().all()

# Search with LIKE
stmt = select(User).where(User.name.ilike(f"%{query}%"))

# Order and limit
stmt = select(User).order_by(User.created_at.desc()).limit(20)

# Count
stmt = select(func.count()).select_from(User).where(User.is_active == True)
result = await session.execute(stmt)
count = result.scalar()
```

### Eager Loading (Avoid N+1)

```python
from sqlalchemy.orm import selectinload, joinedload

# selectinload: separate SELECT IN query (best for collections)
stmt = select(User).options(selectinload(User.posts)).where(User.id == user_id)

# joinedload: LEFT JOIN (best for single related objects)
stmt = select(Post).options(joinedload(Post.author)).where(Post.id == post_id)

# Nested eager loading
stmt = select(User).options(
    selectinload(User.posts).selectinload(Post.tags)
)
```

### Aggregations

```python
from sqlalchemy import func, case

# Group by with aggregation
stmt = (
    select(
        User.role,
        func.count(User.id).label("count"),
        func.avg(func.extract("epoch", User.created_at)).label("avg_created"),
    )
    .group_by(User.role)
)

# Conditional aggregation
stmt = select(
    func.count(case((User.is_active == True, 1))).label("active_count"),
    func.count(case((User.is_active == False, 1))).label("inactive_count"),
)
```

### Subqueries and CTEs

```python
# Subquery
subq = select(func.count(Post.id)).where(Post.author_id == User.id).correlate(User).scalar_subquery()
stmt = select(User, subq.label("post_count")).order_by(subq.desc())

# CTE (Common Table Expression)
active_users = (
    select(User.id, User.name)
    .where(User.is_active == True)
    .cte("active_users")
)
stmt = select(active_users.c.name, func.count(Post.id)).join(
    Post, Post.author_id == active_users.c.id
).group_by(active_users.c.name)
```

## Repository Pattern (project style)

One concrete repository class per aggregate in `app/infrastructure/db/repositories/`.
It takes an `AsyncSession`, exposes intent-named methods (`get_open_for_author`),
and never commits. No generic `BaseRepository[T]`; do not add one (YAGNI).

```python
class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, order_id: uuid.UUID) -> Order | None:
        return await self._session.get(Order, order_id)
```

## Performance Tips

1. **Always use eager loading** for relationships you'll access
2. **Use `select()` instead of `session.query()`** (2.0 style)
3. **Avoid N+1**: use `selectinload` for collections, `joinedload` for single objects
4. **Use `expire_on_commit=False`** in async sessions
5. **Batch inserts**: use `session.add_all()` or `insert().values()`
6. **Connection pooling**: configure `pool_size` and `max_overflow`
7. **Use indexes**: add `index=True` to frequently filtered columns

## Quick Reference

| Pattern | Usage |
|---------|-------|
| `select(Model)` | Build SELECT query |
| `session.execute(stmt)` | Execute query |
| `result.scalars().all()` | Get list of objects |
| `result.scalar_one_or_none()` | Get single object or None |
| `selectinload(Model.rel)` | Eager load collection |
| `joinedload(Model.rel)` | Eager load single object |
| `session.add(obj)` | Insert new object |
| `session.flush()` | Write to DB without commit |
| `session.commit()` | Commit transaction |

**Remember**: SQLAlchemy 2.0 uses `select()` statements instead of legacy `Query` API. Always prefer the new style for clarity and better type support.
