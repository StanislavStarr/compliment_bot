---
name: database-migrations
description: Database migration best practices for schema changes, data migrations, rollbacks, and zero-downtime deployments. Covers Alembic and raw SQL (project uses Alembic; migrations in app/infrastructure/db/migrations).
origin: ECC
---

# Database Migration Patterns

Safe, reversible database schema changes for production systems.

## When to Activate

- Creating or altering database tables
- Adding/removing columns or indexes
- Running data migrations (backfill, transform)
- Planning zero-downtime schema changes

## Core Principles

1. **Every change is a migration** -- never alter production databases manually
2. **Migrations are forward-only in production** -- rollbacks use new forward migrations
3. **Schema and data migrations are separate** -- never mix DDL and DML
4. **Test against production-sized data** -- a migration that works on 100 rows may lock on 10M
5. **Migrations are immutable once deployed** -- never edit a deployed migration

## Migration Safety Checklist

- [ ] Migration has both UP and DOWN (or is marked irreversible)
- [ ] No full table locks on large tables (use concurrent operations)
- [ ] New columns have defaults or are nullable
- [ ] Indexes created concurrently
- [ ] Data backfill is separate from schema change
- [ ] Tested against production-sized data
- [ ] Rollback plan documented

## PostgreSQL Safe Patterns

```sql
-- Adding a column safely
ALTER TABLE users ADD COLUMN avatar_url TEXT;

-- Index without downtime
CREATE INDEX CONCURRENTLY idx_users_email ON users (email);

-- Batch update for large data migrations
DO $$
DECLARE batch_size INT := 10000; rows_updated INT;
BEGIN
  LOOP
    UPDATE users SET normalized_email = LOWER(email)
    WHERE id IN (
      SELECT id FROM users WHERE normalized_email IS NULL LIMIT batch_size FOR UPDATE SKIP LOCKED
    );
    GET DIAGNOSTICS rows_updated = ROW_COUNT;
    EXIT WHEN rows_updated = 0;
    COMMIT;
  END LOOP;
END $$;
```

## Alembic (SQLAlchemy)

```bash
alembic revision --autogenerate -m "add user avatar"  # Generate
alembic upgrade head                 # Apply
alembic downgrade -1                 # Rollback one step
alembic history                      # Show history
```

```python
# app/infrastructure/db/migrations/versions/<rev>_add_user_avatar.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('users', sa.Column('avatar_url', sa.Text(), nullable=True))
    op.create_index('idx_users_avatar', 'users', ['avatar_url'], unique=False)

def downgrade():
    op.drop_index('idx_users_avatar', table_name='users')
    op.drop_column('users', 'avatar_url')
```

## Zero-Downtime Strategy (Expand-Contract)

```
Phase 1: EXPAND   -- Add new column (nullable), deploy app writing to BOTH
Phase 2: MIGRATE  -- Backfill data, app reads from NEW
Phase 3: CONTRACT -- Drop old column in separate migration
```
