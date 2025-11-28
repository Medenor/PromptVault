# PromptVault Database Migration Implementation Plan

## Overview

This plan details the migration of PromptVault from JSON file storage to SQLAlchemy ORM with dual database support (SQLite for development/testing, PostgreSQL for production).

**Goal:** Replace `data/prompts_data.json` with a relational database while maintaining 100% API backward compatibility and zero data loss.

---

## Current State Analysis

### Existing Architecture
- **Storage:** JSON file (`data/prompts_data.json`) with nested structure
- **Services:** PromptDataService (load/save), PromptVersioningService, BackupService
- **Data Model:** Denormalized prompts with inline version history
- **Dependencies:** FastAPI, Uvicorn, Pytest (no database packages)
- **Tests:** 24 test files, 85% coverage requirement

### Key Challenges
1. Complex nested JSON structure (prompts → versions → branches)
2. No existing database infrastructure
3. Backup system uses file copy (needs pg_dump integration)
4. Transaction boundaries currently implicit (save_prompts() atomicity)
5. In-memory dictionary access pattern (`prompts[id]`)

---

## Database Schema Design

### Core Tables

#### 1. users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(200),
    email VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### 2. categories
```sql
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### 3. tags
```sql
CREATE TABLE tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### 4. prompts
```sql
CREATE TABLE prompts (
    id INTEGER PRIMARY KEY,  -- Preserve existing integer IDs
    title VARCHAR(200) NOT NULL,
    prompt TEXT NOT NULL,
    category_id INTEGER REFERENCES categories(id),
    note TEXT,
    favorite BOOLEAN DEFAULT FALSE,
    user_id UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indices for performance
CREATE INDEX idx_prompts_title ON prompts(title);
CREATE INDEX idx_prompts_category ON prompts(category_id);
CREATE INDEX idx_prompts_user ON prompts(user_id);
CREATE INDEX idx_prompts_created ON prompts(created_at);
CREATE INDEX idx_prompts_favorite ON prompts(favorite);
```

#### 5. prompt_versions
```sql
CREATE TABLE prompt_versions (
    id SERIAL PRIMARY KEY,
    prompt_id INTEGER REFERENCES prompts(id) ON DELETE CASCADE,
    version_id UUID UNIQUE NOT NULL,
    version_number INTEGER NOT NULL,
    title VARCHAR(200),
    prompt TEXT,
    category_id INTEGER REFERENCES categories(id),
    note TEXT,
    tags JSONB,  -- Store tags array for historical accuracy
    favorite BOOLEAN,
    author VARCHAR(100),
    message VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    parent_version_id UUID REFERENCES prompt_versions(version_id),

    UNIQUE(prompt_id, version_number)
);

CREATE INDEX idx_versions_prompt ON prompt_versions(prompt_id);
CREATE INDEX idx_versions_created ON prompt_versions(created_at);
CREATE INDEX idx_versions_parent ON prompt_versions(parent_version_id);
```

#### 6. prompt_tags (join table)
```sql
CREATE TABLE prompt_tags (
    prompt_id INTEGER REFERENCES prompts(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (prompt_id, tag_id)
);

CREATE INDEX idx_prompt_tags_tag ON prompt_tags(tag_id);
```

#### 7. prompt_branches
```sql
CREATE TABLE prompt_branches (
    id SERIAL PRIMARY KEY,
    prompt_id INTEGER REFERENCES prompts(id) ON DELETE CASCADE,
    branch_name VARCHAR(50) NOT NULL DEFAULT 'main',
    current_version_id UUID REFERENCES prompt_versions(version_id),

    UNIQUE(prompt_id, branch_name)
);
```

#### 8. backups
```sql
CREATE TABLE backups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    backup_type VARCHAR(50) NOT NULL,  -- 'pg_dump', 'sqlite_copy', 'json_export'
    filename VARCHAR(255) NOT NULL,
    storage_path TEXT NOT NULL,
    size_bytes BIGINT,
    prompt_count INTEGER,
    created_by VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    succeeded BOOLEAN DEFAULT TRUE,
    metadata JSONB
);
```

### Full-Text Search Setup

**PostgreSQL:**
```sql
-- Add tsvector column for full-text search
ALTER TABLE prompts ADD COLUMN search_vector tsvector;

-- Update function
CREATE OR REPLACE FUNCTION prompts_search_vector_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.prompt, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.note, '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger
CREATE TRIGGER prompts_search_vector_trigger
BEFORE INSERT OR UPDATE ON prompts
FOR EACH ROW EXECUTE FUNCTION prompts_search_vector_update();

-- GIN index
CREATE INDEX idx_prompts_search ON prompts USING GIN(search_vector);
```

**SQLite:**
```sql
-- FTS5 virtual table
CREATE VIRTUAL TABLE prompts_fts USING fts5(
    prompt_id UNINDEXED,
    title,
    prompt,
    note
);

-- Triggers to keep in sync
CREATE TRIGGER prompts_fts_insert AFTER INSERT ON prompts
BEGIN
    INSERT INTO prompts_fts(prompt_id, title, prompt, note)
    VALUES (NEW.id, NEW.title, NEW.prompt, NEW.note);
END;
```

---

## Implementation Phases

### Phase 1: Dependencies & Project Structure (Day 1)

**1.1 Update pyproject.toml**
```toml
[project]
dependencies = [
    "fastapi==0.104.1",
    "uvicorn[standard]==0.24.0",
    # ... existing deps ...
    "sqlalchemy>=2.0.25",
    "alembic>=1.13.1",
    "psycopg[binary]>=3.1.16",
    "greenlet>=3.0.3",  # For SQLAlchemy async
]
```

**1.2 Create new directory structure**
```
src/
├── db/
│   ├── __init__.py
│   ├── config.py          # Database configuration
│   ├── session.py         # Session management
│   ├── base.py            # SQLAlchemy Base
│   └── models/
│       ├── __init__.py
│       ├── user.py
│       ├── prompt.py
│       ├── prompt_version.py
│       ├── category.py
│       ├── tag.py
│       ├── backup.py
│       └── associations.py  # Join tables
```

**1.3 Initialize Alembic**
```bash
alembic init alembic
```

**Deliverables:**
- ✅ Dependencies installed
- ✅ Directory structure created
- ✅ Alembic initialized

---

### Phase 2: SQLAlchemy Models (Days 2-3)

**2.1 Create Base Configuration**

**File:** `src/db/base.py`
```python
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData

# Naming convention for constraints
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)

class Base(DeclarativeBase):
    metadata = metadata
```

**2.2 Create ORM Models**

**Key Models:**
- `User` - User accounts
- `Category` - Prompt categories
- `Tag` - Reusable tags
- `Prompt` - Main prompt entity
- `PromptVersion` - Version history
- `PromptBranch` - Branch tracking
- `PromptTag` - Many-to-many association
- `Backup` - Backup metadata

**Example:** `src/db/models/prompt.py`
```python
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.db.base import Base

class Prompt(Base):
    __tablename__ = "prompts"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    prompt = Column(Text, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"))
    note = Column(Text)
    favorite = Column(Boolean, default=False)
    user_id = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    category = relationship("Category", back_populates="prompts")
    tags = relationship("Tag", secondary="prompt_tags", back_populates="prompts")
    versions = relationship("PromptVersion", back_populates="prompt", cascade="all, delete-orphan")
    branches = relationship("PromptBranch", back_populates="prompt", cascade="all, delete-orphan")
    user = relationship("User", back_populates="prompts")
```

**Deliverables:**
- ✅ 8 ORM models created
- ✅ Relationships defined
- ✅ Constraints and indices

---

### Phase 3: Database Configuration & Session Management (Day 3)

**3.1 Database Config**

**File:** `src/db/config.py`
```python
import os
from typing import Optional
from pydantic_settings import BaseSettings

class DatabaseSettings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./data/promptvault.db"
    DB_POOL_SIZE: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600
    DB_ECHO: bool = False

    class Config:
        env_file = ".env"

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def is_postgresql(self) -> bool:
        return self.DATABASE_URL.startswith("postgresql")

db_settings = DatabaseSettings()
```

**3.2 Session Management**

**File:** `src/db/session.py`
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
from src.db.config import db_settings

# Create engine
engine = create_engine(
    db_settings.DATABASE_URL,
    echo=db_settings.DB_ECHO,
    pool_size=db_settings.DB_POOL_SIZE if not db_settings.is_sqlite else 0,
    pool_pre_ping=True,
    pool_recycle=db_settings.DB_POOL_RECYCLE
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager for database sessions"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**3.3 Health Check**

**File:** `src/db/health.py`
```python
from sqlalchemy import text
from src.db.session import engine

def check_database_health() -> bool:
    """Check if database is accessible"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Database health check failed: {e}")
        return False
```

**Deliverables:**
- ✅ Database configuration
- ✅ Connection pooling
- ✅ Session management
- ✅ Health check function

---

### Phase 4: Alembic Migrations (Day 4)

**4.1 Configure Alembic**

**File:** `alembic/env.py`
```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from src.db.base import Base
from src.db.config import db_settings

# Import all models
from src.db.models.user import User
from src.db.models.category import Category
from src.db.models.tag import Tag
from src.db.models.prompt import Prompt
from src.db.models.prompt_version import PromptVersion
from src.db.models.backup import Backup

config = context.config
config.set_main_option("sqlalchemy.url", db_settings.DATABASE_URL)
target_metadata = Base.metadata

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
```

**4.2 Create Initial Migration**

```bash
alembic revision --autogenerate -m "Initial schema"
```

**4.3 Add PostgreSQL-specific Features**

Create migration file: `alembic/versions/002_add_fts.py`
```python
def upgrade():
    # Check if PostgreSQL
    if op.get_bind().dialect.name == 'postgresql':
        # Add search vector column
        op.add_column('prompts', sa.Column('search_vector', TSVECTOR))
        # Create trigger function
        op.execute("""
            CREATE FUNCTION prompts_search_vector_update() RETURNS trigger AS $$
            BEGIN
                NEW.search_vector :=
                    setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
                    setweight(to_tsvector('english', COALESCE(NEW.prompt, '')), 'B');
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        # Create trigger
        op.execute("""
            CREATE TRIGGER prompts_search_vector_trigger
            BEFORE INSERT OR UPDATE ON prompts
            FOR EACH ROW EXECUTE FUNCTION prompts_search_vector_update();
        """)
        # Create index
        op.execute("CREATE INDEX idx_prompts_search ON prompts USING GIN(search_vector);")
```

**Deliverables:**
- ✅ Alembic configured
- ✅ Initial schema migration
- ✅ FTS migrations (PostgreSQL/SQLite)

---

### Phase 5: Data Migration Script (Days 4-5)

**Critical File:** `scripts/migrate_json_to_db.py`

```python
#!/usr/bin/env python3
"""
Migrate data from JSON file to database.

Usage:
    python scripts/migrate_json_to_db.py --source data/prompts_data.json --dry-run
    python scripts/migrate_json_to_db.py --source data/prompts_data.json
"""

import json
import argparse
from pathlib import Path
from sqlalchemy.orm import Session
from src.db.session import engine, SessionLocal
from src.db.base import Base
from src.db.models import Prompt, PromptVersion, Category, Tag, User

def load_json_data(json_path: str) -> dict:
    """Load and parse JSON file"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def migrate_data(json_data: dict, session: Session, dry_run: bool = False):
    """Migrate JSON data to database"""

    stats = {
        "prompts": 0,
        "versions": 0,
        "categories": 0,
        "tags": 0,
        "errors": []
    }

    # 1. Create default user
    default_user = session.query(User).filter_by(username="system").first()
    if not default_user:
        default_user = User(username="system", display_name="System User")
        if not dry_run:
            session.add(default_user)
            session.flush()

    # 2. Migrate categories
    category_map = {}
    for cat_name in json_data.get("categories", []):
        cat = session.query(Category).filter_by(name=cat_name).first()
        if not cat:
            cat = Category(name=cat_name)
            if not dry_run:
                session.add(cat)
                session.flush()
            stats["categories"] += 1
        category_map[cat_name] = cat

    # 3. Migrate tags
    tag_map = {}
    for tag_name in json_data.get("global_tags", []):
        tag = session.query(Tag).filter_by(name=tag_name).first()
        if not tag:
            tag = Tag(name=tag_name)
            if not dry_run:
                session.add(tag)
                session.flush()
            stats["tags"] += 1
        tag_map[tag_name] = tag

    # 4. Migrate prompts and versions
    for prompt_id_str, prompt_data in json_data.get("prompts", {}).items():
        try:
            prompt_id = int(prompt_id_str)
            data = prompt_data["data"]

            # Get category
            category = category_map.get(data.get("category"))

            # Create prompt
            prompt = Prompt(
                id=prompt_id,
                title=data["title"],
                prompt=data["prompt"],
                category=category,
                note=data.get("note", ""),
                favorite=data.get("favorite", False),
                user=default_user
            )

            if not dry_run:
                session.add(prompt)
                session.flush()

            stats["prompts"] += 1

            # Add tags
            for tag_name in data.get("tags", []):
                if tag_name in tag_map:
                    prompt.tags.append(tag_map[tag_name])

            # Migrate versions
            for idx, version_data in enumerate(prompt_data.get("versions", [])):
                version = PromptVersion(
                    prompt_id=prompt_id,
                    version_id=version_data["version_id"],
                    version_number=idx + 1,
                    title=version_data["data"]["title"],
                    prompt=version_data["data"]["prompt"],
                    tags=json.dumps(version_data["data"].get("tags", [])),
                    author=version_data["author"],
                    message=version_data["message"],
                    created_at=version_data["timestamp"]
                )

                if not dry_run:
                    session.add(version)

                stats["versions"] += 1

        except Exception as e:
            stats["errors"].append(f"Prompt {prompt_id_str}: {str(e)}")

    if not dry_run:
        session.commit()

    return stats

def main():
    parser = argparse.ArgumentParser(description="Migrate JSON data to database")
    parser.add_argument("--source", required=True, help="Path to JSON file")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    # Load JSON
    json_data = load_json_data(args.source)

    # Create tables
    Base.metadata.create_all(bind=engine)

    # Migrate
    session = SessionLocal()
    try:
        stats = migrate_data(json_data, session, dry_run=args.dry_run)

        print("\n=== Migration Complete ===")
        print(f"Prompts: {stats['prompts']}")
        print(f"Versions: {stats['versions']}")
        print(f"Categories: {stats['categories']}")
        print(f"Tags: {stats['tags']}")
        if stats['errors']:
            print(f"\nErrors: {len(stats['errors'])}")
            for error in stats['errors']:
                print(f"  - {error}")
    finally:
        session.close()

if __name__ == "__main__":
    main()
```

**Deliverables:**
- ✅ Complete migration script
- ✅ Dry-run mode for preview
- ✅ Error handling and reporting
- ✅ Data validation

---

### Phase 6: Repository Pattern (Days 5-6)

**File:** `src/db/repositories/prompt_repository.py`

```python
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from src.db.models import Prompt, PromptVersion, Tag, Category

class PromptRepository:
    """Data access layer for prompts"""

    def __init__(self, session: Session):
        self.session = session

    def get_all(self) -> List[Prompt]:
        """Get all prompts"""
        return self.session.query(Prompt).all()

    def get_by_id(self, prompt_id: int) -> Optional[Prompt]:
        """Get prompt by ID"""
        return self.session.query(Prompt).filter(Prompt.id == prompt_id).first()

    def create(self, prompt_data: Dict[str, Any]) -> Prompt:
        """Create new prompt"""
        prompt = Prompt(**prompt_data)
        self.session.add(prompt)
        self.session.flush()
        return prompt

    def update(self, prompt_id: int, updates: Dict[str, Any]) -> Optional[Prompt]:
        """Update existing prompt"""
        prompt = self.get_by_id(prompt_id)
        if prompt:
            for key, value in updates.items():
                setattr(prompt, key, value)
            self.session.flush()
        return prompt

    def delete(self, prompt_id: int) -> bool:
        """Delete prompt"""
        prompt = self.get_by_id(prompt_id)
        if prompt:
            self.session.delete(prompt)
            self.session.flush()
            return True
        return False

    def search(self, query: str, category: Optional[str] = None,
               tags: Optional[List[str]] = None) -> List[Prompt]:
        """Search prompts"""
        q = self.session.query(Prompt)

        if query:
            q = q.filter(
                or_(
                    Prompt.title.ilike(f"%{query}%"),
                    Prompt.prompt.ilike(f"%{query}%")
                )
            )

        if category:
            q = q.join(Category).filter(Category.name == category)

        if tags:
            q = q.join(Prompt.tags).filter(Tag.name.in_(tags))

        return q.all()
```

**Deliverables:**
- ✅ PromptRepository
- ✅ VersionRepository
- ✅ CategoryRepository
- ✅ TagRepository

---

### Phase 7: Service Layer Refactoring (Days 6-8)

**7.1 Update PromptDataService**

**File:** `src/services/prompt_data_service.py`

**Strategy:** Create compatibility layer that maintains existing interface while using database backend.

```python
from typing import Dict, List, Optional, Any
from src.db.session import get_db_session
from src.db.repositories.prompt_repository import PromptRepository
from src.db.models import Prompt, PromptVersion

class PromptDataService:
    """Data service with database backend (backward compatible)"""

    def __init__(self, data_file_path: Optional[str] = None):
        # Keep for backward compatibility but not used
        self.data_file_path = data_file_path
        self._prompts_cache = None

    def load_prompts(self) -> Dict[int, Dict[str, Any]]:
        """Load prompts from database (returns dict for compatibility)"""
        with get_db_session() as session:
            repo = PromptRepository(session)
            prompts = repo.get_all()

            # Convert to old format for backward compatibility
            return self._convert_to_dict_format(prompts)

    def save_prompts(self) -> bool:
        """No-op for backward compatibility (DB auto-commits)"""
        return True

    def add_new_prompt(self, prompt_data: Dict[str, Any]) -> int:
        """Create new prompt"""
        with get_db_session() as session:
            repo = PromptRepository(session)

            # Handle tags
            tags = self._process_tags(session, prompt_data.pop("tags", []))

            # Create prompt
            prompt = repo.create(prompt_data)
            prompt.tags.extend(tags)

            # Create initial version
            self._create_initial_version(session, prompt, prompt_data)

            return prompt.id

    def update_prompt(self, prompt_id: int, updates: Dict[str, Any],
                     commit_message: str) -> bool:
        """Update prompt with version tracking"""
        with get_db_session() as session:
            repo = PromptRepository(session)
            prompt = repo.update(prompt_id, updates)

            if prompt:
                # Create new version
                self._create_version(session, prompt, commit_message)
                return True
            return False

    def delete_prompt(self, prompt_id: int) -> bool:
        """Delete prompt (cascade deletes versions)"""
        with get_db_session() as session:
            repo = PromptRepository(session)
            return repo.delete(prompt_id)

    def _convert_to_dict_format(self, prompts: List[Prompt]) -> Dict[int, Dict]:
        """Convert ORM objects to old dict format"""
        result = {}
        for prompt in prompts:
            result[prompt.id] = {
                "data": {
                    "title": prompt.title,
                    "prompt": prompt.prompt,
                    "category": prompt.category.name if prompt.category else "",
                    "tags": [tag.name for tag in prompt.tags],
                    "note": prompt.note or "",
                    "favorite": prompt.favorite
                },
                "versions": [
                    self._version_to_dict(v) for v in prompt.versions
                ],
                "branches": {
                    b.branch_name: b.current_version_id
                    for b in prompt.branches
                }
            }
        return result
```

**7.2 Backward Compatibility Layer**

Key principle: All existing API endpoints continue to work without changes.

- `load_prompts()` returns dict format (converts ORM → dict)
- `save_prompts()` becomes no-op (DB auto-commits)
- All CRUD methods maintain same signatures
- Internal implementation uses repositories

**Deliverables:**
- ✅ Refactored PromptDataService
- ✅ Backward compatibility maintained
- ✅ Repository integration
- ✅ Transaction management

---

### Phase 8: Backup System Integration (Days 8-9)

**8.1 Update BackupService**

**File:** `src/services/backup_service.py`

```python
import subprocess
import gzip
from pathlib import Path
from src.db.config import db_settings

class BackupService:
    """Backup service with database support"""

    def create_backup(self, custom_name: Optional[str] = None) -> str:
        """Create database backup"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_id = custom_name or f"backup_{timestamp}"

        if db_settings.is_postgresql:
            return self._create_pg_backup(backup_id)
        elif db_settings.is_sqlite:
            return self._create_sqlite_backup(backup_id)
        else:
            raise BackupError("Unsupported database type")

    def _create_pg_backup(self, backup_id: str) -> str:
        """Create PostgreSQL backup using pg_dump"""
        backup_file = self.backups_dir / f"{backup_id}.sql"

        # Parse DATABASE_URL
        db_url = db_settings.DATABASE_URL
        # postgresql://user:pass@host:port/dbname

        cmd = [
            "pg_dump",
            "--file", str(backup_file),
            "--format=plain",
            "--clean",
            "--if-exists",
            db_url
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)

            # Create metadata
            metadata = {
                "backup_id": backup_id,
                "backup_type": "pg_dump",
                "filename": backup_file.name,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "size_bytes": backup_file.stat().st_size
            }

            self._save_metadata(backup_id, metadata)
            return backup_id

        except subprocess.CalledProcessError as e:
            raise BackupError(f"pg_dump failed: {e.stderr.decode()}")

    def _create_sqlite_backup(self, backup_id: str) -> str:
        """Create SQLite backup using file copy"""
        db_path = db_settings.DATABASE_URL.replace("sqlite:///", "")
        backup_file = self.backups_dir / f"{backup_id}.db"

        shutil.copy2(db_path, backup_file)

        metadata = {
            "backup_id": backup_id,
            "backup_type": "sqlite_copy",
            "filename": backup_file.name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "size_bytes": backup_file.stat().st_size
        }

        self._save_metadata(backup_id, metadata)
        return backup_id

    def restore_backup(self, backup_id: str) -> bool:
        """Restore from backup"""
        # Create pre-restore backup
        pre_restore_id = self.create_backup("pre_restore")

        metadata = self._load_metadata(backup_id)

        if metadata["backup_type"] == "pg_dump":
            return self._restore_pg_backup(backup_id)
        elif metadata["backup_type"] == "sqlite_copy":
            return self._restore_sqlite_backup(backup_id)
```

**Deliverables:**
- ✅ PostgreSQL pg_dump integration
- ✅ SQLite file copy backup
- ✅ Restore functionality
- ✅ Pre-restore backups

---

### Phase 9: Test Infrastructure (Days 9-10)

**9.1 Update conftest.py**

**File:** `tests/conftest.py`

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.db.base import Base
from src.db.models import *

@pytest.fixture(scope="function")
def test_db_engine():
    """Create in-memory SQLite engine for tests"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()

@pytest.fixture(scope="function")
def test_db_session(test_db_engine):
    """Create test database session"""
    SessionLocal = sessionmaker(bind=test_db_engine)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()

@pytest.fixture
def populated_db_service(test_db_session, sample_prompt_data):
    """Create service with populated test database"""
    # Create test prompts
    for i in range(5):
        prompt_data = sample_prompt_data(title=f"Test Prompt {i+1}")
        # ... create via repository

    service = PromptDataService()
    service._session = test_db_session  # Inject test session
    return service
```

**9.2 Update Existing Tests**

Example: `tests/test_prompt_data_service.py`

```python
def test_add_prompt(populated_db_service, sample_prompt_data):
    """Test adding a new prompt (now uses database)"""
    initial_count = len(populated_db_service.load_prompts())
    new_prompt = sample_prompt_data(title="New Test Prompt")

    prompt_id = populated_db_service.add_new_prompt(new_prompt)

    assert prompt_id is not None
    prompts = populated_db_service.load_prompts()
    assert len(prompts) == initial_count + 1
    assert prompts[prompt_id]['data']['title'] == "New Test Prompt"
```

**Deliverables:**
- ✅ In-memory SQLite test fixtures
- ✅ Test database session management
- ✅ All existing tests adapted
- ✅ 85%+ coverage maintained

---

### Phase 10: Docker & Deployment (Days 10-11)

**10.1 Update docker-compose.yml**

```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: promptvault
      POSTGRES_PASSWORD: promptvault
      POSTGRES_DB: promptvault
    volumes:
      - promptvault_db:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U promptvault"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - promptvault_network

  web:
    build: .
    ports:
      - "8001:8000"
    environment:
      - DATABASE_URL=postgresql://promptvault:promptvault@db:5432/promptvault
      - PYTHONPATH=/app
    volumes:
      - ./data:/app/data:rw
      - ./src:/app/src:ro
    depends_on:
      db:
        condition: service_healthy
    networks:
      - promptvault_network

volumes:
  promptvault_db:

networks:
  promptvault_network:
```

**10.2 Update Dockerfile**

```dockerfile
FROM python:3.11-slim

# Install PostgreSQL client for pg_dump
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY . .

# Run migrations on startup
CMD alembic upgrade head && uvicorn src.web.app:app --host 0.0.0.0 --port 8000 --reload
```

**10.3 Environment Variables**

**File:** `.env.example`
```bash
# Database Configuration
DATABASE_URL=postgresql://promptvault:promptvault@localhost:5432/promptvault
# For SQLite: DATABASE_URL=sqlite:///./data/promptvault.db

# Database Connection Pool
DB_POOL_SIZE=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600

# Application
ENVIRONMENT=production
LOG_LEVEL=INFO
AUDIT_LOG_LEVEL=INFO
```

**Deliverables:**
- ✅ PostgreSQL service in Docker Compose
- ✅ Environment variable configuration
- ✅ Migration on startup
- ✅ Health checks

---

### Phase 11: Documentation & Migration Guide (Days 11-12)

**11.1 Create Migration Guide**

**File:** `docs/DATABASE_MIGRATION_GUIDE.md`

```markdown
# Database Migration Guide

## Overview

This guide helps you migrate from JSON file storage to database storage.

## Prerequisites

- Backup your `data/prompts_data.json` file
- Install Docker (for PostgreSQL) or use SQLite

## Migration Steps

### Option 1: PostgreSQL (Recommended for Production)

1. **Start PostgreSQL**
   ```bash
   docker-compose up -d db
   ```

2. **Run Migrations**
   ```bash
   alembic upgrade head
   ```

3. **Migrate Data**
   ```bash
   python scripts/migrate_json_to_db.py \
       --source data/prompts_data.json \
       --dry-run  # Preview first

   python scripts/migrate_json_to_db.py \
       --source data/prompts_data.json  # Actual migration
   ```

4. **Verify**
   ```bash
   # Check prompt count
   psql postgresql://promptvault:promptvault@localhost:5432/promptvault \
       -c "SELECT COUNT(*) FROM prompts;"
   ```

5. **Start Application**
   ```bash
   docker-compose up web
   ```

### Option 2: SQLite (Development/Testing)

1. **Set Environment**
   ```bash
   export DATABASE_URL=sqlite:///./data/promptvault.db
   ```

2. **Run Migrations**
   ```bash
   alembic upgrade head
   ```

3. **Migrate Data**
   ```bash
   python scripts/migrate_json_to_db.py --source data/prompts_data.json
   ```

## Rollback Plan

If you need to rollback:

1. Stop the application
2. Restore your JSON backup
3. Update docker-compose.yml to use old version
4. Restart application

## Verification Checklist

- [ ] All prompts migrated (check count)
- [ ] Version history preserved
- [ ] Tags and categories intact
- [ ] Favorites marked correctly
- [ ] API endpoints respond correctly
- [ ] Search functionality works
```

**Deliverables:**
- ✅ Migration guide
- ✅ Troubleshooting section
- ✅ Rollback instructions
- ✅ API documentation updates

---

## Critical Files Summary

### New Files to Create
1. `src/db/config.py` - Database configuration
2. `src/db/session.py` - Session management
3. `src/db/base.py` - SQLAlchemy base
4. `src/db/models/*.py` - 8 ORM model files
5. `src/db/repositories/*.py` - Repository pattern
6. `scripts/migrate_json_to_db.py` - Data migration
7. `alembic/versions/001_initial_schema.py` - Schema migration
8. `docs/DATABASE_MIGRATION_GUIDE.md` - User guide

### Files to Modify
1. `pyproject.toml` - Add database dependencies
2. `src/services/prompt_data_service.py` - Use repositories
3. `src/services/backup_service.py` - Add pg_dump support
4. `src/web/app.py` - Database health check on startup
5. `tests/conftest.py` - Database test fixtures
6. `docker-compose.yml` - Add PostgreSQL service
7. `Dockerfile` - Install PostgreSQL client

### Files to Keep Unchanged
- `src/web/models/requests.py` - Pydantic models (unchanged)
- API endpoint signatures (backward compatible)
- Frontend JavaScript (no changes needed)

---

## Risk Mitigation

### Data Loss Prevention
- ✅ Automatic backup before migration
- ✅ Dry-run mode for preview
- ✅ Transaction rollback on errors
- ✅ Data verification (count checks)

### Backward Compatibility
- ✅ PromptDataService maintains same interface
- ✅ API responses unchanged
- ✅ Existing tests adapted (not rewritten)

### Performance
- ✅ Database indices on frequent queries
- ✅ Connection pooling
- ✅ Query optimization with SQLAlchemy

---

## Success Criteria

- [ ] All 13 specification requirements met (REQ-001 through REQ-013)
- [ ] Zero data loss during migration
- [ ] 85%+ test coverage maintained
- [ ] All existing API tests pass
- [ ] Query performance < 200ms for 10k prompts
- [ ] PostgreSQL and SQLite both supported
- [ ] Full-text search functional
- [ ] Backup/restore with pg_dump working
- [ ] Migration guide complete

---

## Timeline Estimate

**Total: 15-20 working days**

- Phase 1-4: Foundation (Days 1-4) - 4 days
- Phase 5-7: Service Refactoring (Days 5-8) - 4 days
- Phase 8-9: Backup & Testing (Days 9-10) - 2 days
- Phase 10-11: Docker & Docs (Days 11-12) - 2 days
- Buffer: Testing & refinement - 3-8 days

---

## Implementation Decisions

Based on user feedback, the following decisions have been made:

1. **User Management**: ✅ Option C - Add user table structure but defer authentication to future phase (related to separate ticket)
   - Create `users` table in schema
   - Create default "system" user for migration
   - Authentication/authorization deferred to future implementation

2. **Database Priority**: ✅ Option C - Both PostgreSQL and SQLite equally supported
   - PostgreSQL recommended for production
   - SQLite for development and testing
   - Abstraction layer handles differences

3. **Migration Approach**: ✅ Option C - Database-only with one-time migration script
   - Users run migration script once
   - No dual JSON/DB mode
   - Comprehensive migration guide with verification

4. **Backward Compatibility**: ✅ Option A - Maintain dict interface permanently
   - PromptDataService keeps dict-based API
   - Internal implementation uses ORM
   - Zero breaking changes for existing code

5. **Full-Text Search**: ✅ Option B - Start with LIKE queries (FTS deferred to future ticket)
   - Simple ILIKE/LIKE pattern matching initially
   - PostgreSQL tsvector and SQLite FTS5 in future phase
   - Keeps migration focused and testable

---

## Quick Start Implementation Guide

### Step 1: Dependencies (Day 1)
```bash
# Update pyproject.toml
pip install sqlalchemy>=2.0.25 alembic>=1.13.1 psycopg[binary]>=3.1.16

# Initialize Alembic
alembic init alembic
```

### Step 2: Create Database Layer (Days 2-3)
Create directory structure:
- `src/db/config.py` - Database settings
- `src/db/session.py` - Session management
- `src/db/base.py` - SQLAlchemy Base
- `src/db/models/` - All ORM models (User, Prompt, PromptVersion, Category, Tag, etc.)

### Step 3: Run Migrations (Day 4)
```bash
# Configure Alembic to use your models
# Create initial migration
alembic revision --autogenerate -m "Initial schema"

# Apply migration
alembic upgrade head
```

### Step 4: Data Migration (Days 4-5)
```bash
# Preview migration
python scripts/migrate_json_to_db.py --source data/prompts_data.json --dry-run

# Execute migration
python scripts/migrate_json_to_db.py --source data/prompts_data.json
```

### Step 5: Refactor Services (Days 6-8)
Update `src/services/prompt_data_service.py`:
- Replace JSON load/save with database queries
- Use Repository pattern
- Maintain dict-based interface for backward compatibility

### Step 6: Testing (Days 9-10)
Update `tests/conftest.py`:
- Create in-memory SQLite fixtures
- Adapt all existing tests
- Verify 85%+ coverage maintained

### Step 7: Docker & Deployment (Days 10-12)
- Update `docker-compose.yml` with PostgreSQL service
- Add environment variable configuration
- Create migration guide for users

---

## Final Implementation Checklist

**Phase 1: Foundation**
- [ ] Add SQLAlchemy, Alembic, psycopg dependencies to pyproject.toml
- [ ] Create `src/db/` directory structure
- [ ] Initialize Alembic configuration

**Phase 2: Database Schema**
- [ ] Create SQLAlchemy Base and naming conventions
- [ ] Define User model (with default system user)
- [ ] Define Category model
- [ ] Define Tag model
- [ ] Define Prompt model (preserve integer IDs)
- [ ] Define PromptVersion model (denormalized snapshots)
- [ ] Define PromptBranch model
- [ ] Define PromptTag association table
- [ ] Define Backup model

**Phase 3: Configuration & Sessions**
- [ ] Implement DatabaseSettings in config.py
- [ ] Create session factory with connection pooling
- [ ] Add database health check function
- [ ] Support both PostgreSQL and SQLite URLs

**Phase 4: Migrations**
- [ ] Configure Alembic env.py with all models
- [ ] Create initial schema migration
- [ ] Add indices for performance (title, category, user_id, created_at)
- [ ] Test migration on empty database

**Phase 5: Data Migration Script**
- [ ] Create migrate_json_to_db.py script
- [ ] Implement dry-run mode
- [ ] Handle categories migration
- [ ] Handle tags migration
- [ ] Handle prompts migration (preserve IDs)
- [ ] Handle version history migration
- [ ] Add data verification (counts, checksums)
- [ ] Error handling and rollback

**Phase 6: Repository Pattern**
- [ ] Create PromptRepository
- [ ] Create VersionRepository
- [ ] Create CategoryRepository
- [ ] Create TagRepository
- [ ] Implement search with LIKE queries (not FTS yet)

**Phase 7: Service Refactoring**
- [ ] Refactor PromptDataService to use repositories
- [ ] Maintain dict-based interface (backward compatibility)
- [ ] Replace load_prompts() with DB query + dict conversion
- [ ] Make save_prompts() a no-op (DB auto-commits)
- [ ] Update add_new_prompt() to use repository
- [ ] Update update_prompt() with version creation
- [ ] Update delete_prompt() with cascade
- [ ] Add transaction management

**Phase 8: Backup Integration**
- [ ] Update BackupService.create_backup() for PostgreSQL (pg_dump)
- [ ] Update BackupService.create_backup() for SQLite (file copy)
- [ ] Update BackupService.restore_backup() for both databases
- [ ] Test backup/restore workflows

**Phase 9: Test Infrastructure**
- [ ] Create test_db_engine fixture (in-memory SQLite)
- [ ] Create test_db_session fixture
- [ ] Update sample_prompt_data to work with DB
- [ ] Adapt all existing tests to use DB fixtures
- [ ] Verify 85%+ coverage maintained
- [ ] Test migration script with sample data

**Phase 10: Docker & Deployment**
- [ ] Add PostgreSQL service to docker-compose.yml
- [ ] Update Dockerfile to install postgresql-client
- [ ] Add DATABASE_URL environment variable
- [ ] Configure health checks for database
- [ ] Add migration run on startup (alembic upgrade head)
- [ ] Test Docker Compose setup

**Phase 11: Documentation**
- [ ] Create DATABASE_MIGRATION_GUIDE.md
- [ ] Document PostgreSQL migration steps
- [ ] Document SQLite migration steps
- [ ] Add verification checklist
- [ ] Document rollback procedure
- [ ] Update README.md with database information
- [ ] Create .env.example with database configuration

---

## Key Implementation Notes

1. **Preserve Integer IDs**: Use existing prompt IDs from JSON (not auto-increment from 1)
2. **Denormalized Versions**: Store complete prompt snapshot in each version for historical accuracy
3. **Default User**: Create "system" user during migration for all existing prompts
4. **Transaction Safety**: Wrap all multi-step operations in database transactions
5. **Dict Interface**: Maintain PromptDataService dict-based API for zero breaking changes
6. **Search**: Use LIKE/ILIKE queries initially (defer tsvector/FTS5 to future ticket)
7. **Dual Database**: Support both PostgreSQL and SQLite through abstraction
8. **No Authentication**: User table exists but authentication deferred to separate ticket
