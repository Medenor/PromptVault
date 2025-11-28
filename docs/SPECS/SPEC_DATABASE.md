# SPEC: Database Migration for PromptVault

**Version:** 1.0
**Status:** Implemented
**Last Updated:** 2025-01-28
**Authors:** medenor

---

## 1. Overview

### 1.1 Purpose

This specification defines the database migration of PromptVault from JSON file-based storage to a relational database backend (SQLite/PostgreSQL), providing improved performance, data integrity, and scalability while maintaining 100% backward compatibility with the existing API.

### 1.2 Goals

- **Performance:** Improve query performance for search and filtering operations
- **Scalability:** Support datasets with 10,000+ prompts efficiently
- **Integrity:** Ensure data consistency through ACID transactions
- **Compatibility:** Maintain existing API contracts and interfaces
- **Flexibility:** Support both SQLite (development) and PostgreSQL (production)
- **Migration:** Provide seamless migration path from JSON to database

### 1.3 Non-Goals

- Changing the API endpoint structure or response formats
- Modifying the web UI or frontend components
- Implementing full-text search (deferred to future phase)
- Adding new features beyond database migration
- Supporting databases other than SQLite and PostgreSQL

---

## 2. Requirements

### 2.1 Functional Requirements

#### FR-1: Data Storage

- **FR-1.1:** System SHALL store all prompt data in a relational database
- **FR-1.2:** System SHALL support both SQLite and PostgreSQL backends
- **FR-1.3:** System SHALL maintain referential integrity between related entities
- **FR-1.4:** System SHALL preserve all existing prompt attributes and metadata
- **FR-1.5:** System SHALL store version history as immutable snapshots

#### FR-2: Data Migration

- **FR-2.1:** System SHALL provide automated migration from JSON to database
- **FR-2.2:** Migration SHALL preserve all prompts, versions, categories, and tags
- **FR-2.3:** Migration SHALL maintain prompt IDs from JSON source
- **FR-2.4:** Migration SHALL be idempotent and safely re-runnable
- **FR-2.5:** Migration SHALL provide dry-run mode for validation

#### FR-3: CRUD Operations

- **FR-3.1:** System SHALL support creating new prompts with auto-generated IDs
- **FR-3.2:** System SHALL support reading prompts by ID or multiple criteria
- **FR-3.3:** System SHALL support updating prompts with automatic versioning
- **FR-3.4:** System SHALL support deleting prompts (soft or hard delete)
- **FR-3.5:** System SHALL support bulk operations for efficiency

#### FR-4: Search and Filtering

- **FR-4.1:** System SHALL support text search in title and content
- **FR-4.2:** System SHALL filter prompts by category
- **FR-4.3:** System SHALL filter prompts by tags (AND/OR logic)
- **FR-4.4:** System SHALL filter by favorite status
- **FR-4.5:** System SHALL support pagination for large result sets

#### FR-5: Version Control

- **FR-5.1:** System SHALL automatically create versions on prompt updates
- **FR-5.2:** System SHALL store complete prompt snapshots in each version
- **FR-5.3:** System SHALL track version metadata (author, timestamp, message)
- **FR-5.4:** System SHALL support retrieving version history
- **FR-5.5:** System SHALL maintain parent-child version relationships

#### FR-6: Categories and Tags

- **FR-6.1:** System SHALL implement get-or-create pattern for categories
- **FR-6.2:** System SHALL implement get-or-create pattern for tags
- **FR-6.3:** System SHALL support renaming categories and tags
- **FR-6.4:** System SHALL support merging duplicate tags
- **FR-6.5:** System SHALL track usage counts for categories and tags

#### FR-7: Backup and Restore

- **FR-7.1:** System SHALL support database backups for SQLite and PostgreSQL
- **FR-7.2:** System SHALL store backup metadata in database
- **FR-7.3:** System SHALL support automated backup before restore operations
- **FR-7.4:** System SHALL implement backup retention policies
- **FR-7.5:** System SHALL provide backup listing and statistics

#### FR-8: Backward Compatibility

- **FR-8.1:** System SHALL maintain identical API response formats
- **FR-8.2:** System SHALL support dict-based interface for legacy code
- **FR-8.3:** System SHALL provide deprecation warnings for obsolete methods
- **FR-8.4:** System SHALL allow gradual migration of calling code
- **FR-8.5:** System SHALL maintain existing prompt ID sequence

### 2.2 Non-Functional Requirements

#### NFR-1: Performance

- **NFR-1.1:** Load all prompts operation SHALL complete in < 1 second for 10,000 prompts
- **NFR-1.2:** Search operations SHALL complete in < 500ms for 10,000 prompts
- **NFR-1.3:** Single prompt CRUD operations SHALL complete in < 100ms
- **NFR-1.4:** Database connection pool SHALL support 20+ concurrent connections

#### NFR-2: Reliability

- **NFR-2.1:** System SHALL use ACID transactions for all data modifications
- **NFR-2.2:** System SHALL handle database connection failures gracefully
- **NFR-2.3:** System SHALL implement automatic retry for transient errors
- **NFR-2.4:** System SHALL validate data integrity on all operations

#### NFR-3: Scalability

- **NFR-3.1:** System SHALL support databases with 100,000+ prompts
- **NFR-3.2:** System SHALL use indexed queries for search operations
- **NFR-3.3:** System SHALL implement efficient pagination
- **NFR-3.4:** System SHALL use connection pooling for PostgreSQL

#### NFR-4: Maintainability

- **NFR-4.1:** Database schema SHALL be version-controlled via Alembic migrations
- **NFR-4.2:** System SHALL use repository pattern for data access abstraction
- **NFR-4.3:** System SHALL provide comprehensive error logging
- **NFR-4.4:** Code SHALL maintain 85%+ test coverage
- **NFR-4.5:** Documentation SHALL be complete and up-to-date

#### NFR-5: Security

- **NFR-5.1:** System SHALL use parameterized queries to prevent SQL injection
- **NFR-5.2:** System SHALL support secure database connections (SSL/TLS)
- **NFR-5.3:** Database credentials SHALL be stored in environment variables
- **NFR-5.4:** System SHALL implement proper access control on database
- **NFR-5.5:** Backup files SHALL have restricted file permissions

#### NFR-6: Portability

- **NFR-6.1:** System SHALL run on Linux, macOS, and Windows
- **NFR-6.2:** System SHALL work with SQLite 3.x and PostgreSQL 12+
- **NFR-6.3:** System SHALL use standard SQL with minimal database-specific features
- **NFR-6.4:** System SHALL provide Docker support for deployment

---

## 3. Technical Design

### 3.1 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Web API Layer                           │
│                  (FastAPI Endpoints)                         │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                  Service Layer                               │
│  ┌─────────────────────────┐  ┌──────────────────────────┐ │
│  │ PromptDataService (DB)  │  │  BackupService (DB)      │ │
│  └─────────────────────────┘  └──────────────────────────┘ │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                Repository Layer                              │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────────────┐  │
│  │PromptRepo    │ │VersionRepo   │ │CategoryRepo/TagRepo│  │
│  └──────────────┘ └──────────────┘ └────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                   ORM Layer                                  │
│               (SQLAlchemy Models)                            │
│  ┌──────┐ ┌─────────┐ ┌──────────┐ ┌────┐ ┌──────┐        │
│  │Prompt│ │Version  │ │Category  │ │Tag │ │Backup│        │
│  └──────┘ └─────────┘ └──────────┘ └────┘ └──────┘        │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                Database Layer                                │
│         SQLite (Development) / PostgreSQL (Production)       │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Database Schema

#### 3.2.1 Tables

**prompts**

```sql
CREATE TABLE prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(500) NOT NULL,
    prompt TEXT NOT NULL,
    category_id INTEGER,
    favorite BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    user_id INTEGER,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

**prompt_versions**

```sql
CREATE TABLE prompt_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id VARCHAR(36) UNIQUE NOT NULL,
    prompt_id INTEGER NOT NULL,
    version_number INTEGER NOT NULL,
    author VARCHAR(255),
    message TEXT,
    created_at TIMESTAMP NOT NULL,
    parent_version_id VARCHAR(36),
    -- Denormalized snapshot
    title VARCHAR(500),
    prompt TEXT,
    category_id INTEGER,
    favorite BOOLEAN,
    FOREIGN KEY (prompt_id) REFERENCES prompts(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_version_id) REFERENCES prompt_versions(version_id),
    UNIQUE(prompt_id, version_number)
);
```

**categories**

```sql
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**tags**

```sql
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**prompt_tags** (Many-to-Many)

```sql
CREATE TABLE prompt_tags (
    prompt_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (prompt_id, tag_id),
    FOREIGN KEY (prompt_id) REFERENCES prompts(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);
```

**users**

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**backups**

```sql
CREATE TABLE backups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    backup_id VARCHAR(36) UNIQUE NOT NULL,
    backup_type VARCHAR(50) NOT NULL,
    filename VARCHAR(500) NOT NULL,
    size_bytes INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON
);
```

#### 3.2.2 Indexes

```sql
CREATE INDEX idx_prompts_title ON prompts(title);
CREATE INDEX idx_prompts_category ON prompts(category_id);
CREATE INDEX idx_prompts_favorite ON prompts(favorite);
CREATE INDEX idx_prompts_created_at ON prompts(created_at);
CREATE INDEX idx_prompts_updated_at ON prompts(updated_at);

CREATE INDEX idx_versions_prompt ON prompt_versions(prompt_id);
CREATE INDEX idx_versions_version_id ON prompt_versions(version_id);
CREATE INDEX idx_versions_created_at ON prompt_versions(created_at);

CREATE INDEX idx_categories_name ON categories(name);
CREATE INDEX idx_tags_name ON tags(name);

CREATE INDEX idx_prompt_tags_tag ON prompt_tags(tag_id);
```

### 3.3 Data Models

#### 3.3.1 SQLAlchemy Models

**Prompt Model:**

```python
class Prompt(Base):
    __tablename__ = "prompts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    prompt = Column(Text, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"))
    favorite = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))

    # Relationships
    category = relationship("Category", back_populates="prompts")
    tags = relationship("Tag", secondary="prompt_tags", back_populates="prompts")
    versions = relationship("PromptVersion", back_populates="prompt", cascade="all, delete-orphan")
    user = relationship("User", back_populates="prompts")
```

**PromptVersion Model:**

```python
class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version_id = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    prompt_id = Column(Integer, ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    author = Column(String(255))
    message = Column(Text)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    parent_version_id = Column(String(36), ForeignKey("prompt_versions.version_id"))

    # Denormalized snapshot
    title = Column(String(500))
    prompt = Column(Text)
    category_id = Column(Integer)
    favorite = Column(Boolean)

    # Relationships
    prompt = relationship("Prompt", back_populates="versions")
    parent = relationship("PromptVersion", remote_side=[version_id], backref="children")
```

### 3.4 Repository Pattern

**Base Repository:**

```python
class BaseRepository(Generic[T]):
    def __init__(self, session: Session, model: Type[T]):
        self.session = session
        self.model = model

    def get_by_id(self, id: int) -> Optional[T]:
        return self.session.query(self.model).filter(self.model.id == id).first()

    def get_all(self) -> List[T]:
        return self.session.query(self.model).all()

    def create(self, **kwargs) -> T:
        instance = self.model(**kwargs)
        self.session.add(instance)
        self.session.commit()
        self.session.refresh(instance)
        return instance

    def update(self, id: int, **kwargs) -> Optional[T]:
        instance = self.get_by_id(id)
        if instance:
            for key, value in kwargs.items():
                setattr(instance, key, value)
            self.session.commit()
            self.session.refresh(instance)
        return instance

    def delete(self, id: int) -> bool:
        instance = self.get_by_id(id)
        if instance:
            self.session.delete(instance)
            self.session.commit()
            return True
        return False
```

### 3.5 Session Management

**Database Session Context Manager:**

```python
@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Provides a transactional scope for database operations.

    Automatically commits on success, rolls back on error.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        session.close()
```

**Usage:**

```python
def create_prompt(title: str, content: str) -> int:
    with get_db_session() as session:
        repo = PromptRepository(session)
        prompt = repo.create(title=title, prompt=content)
        return prompt.id
```

---

## 4. Interfaces

### 4.1 Service Layer Interface

**PromptDataService (Database-backed):**

```python
class PromptDataService:
    """Database-backed prompt data service with backward compatibility."""

    # Core CRUD Operations
    def add_new_prompt(self, prompt_data: Dict) -> int:
        """Create a new prompt, returns ID."""

    def get_prompt_data(self, prompt_id: int) -> Optional[Dict]:
        """Get prompt by ID, returns dict format."""

    def update_prompt(self, prompt_id: int, prompt_data: Dict, message: str = "") -> bool:
        """Update prompt, creates new version."""

    def delete_prompt(self, prompt_id: int) -> bool:
        """Delete prompt by ID."""

    def delete_prompts_bulk(self, prompt_ids: List[int]) -> Dict:
        """Bulk delete, returns statistics."""

    # Loading and Listing
    def load_prompts(self) -> Dict[int, Dict]:
        """Load all prompts in dict format."""

    # Search and Filtering
    def search_prompts(self, query: str = "", category: str = "",
                       tags: List[str] = None, favorite: bool = None) -> List[Dict]:
        """Search prompts with filters."""

    # Categories and Tags
    def get_categories(self) -> List[str]:
        """Get all category names."""

    def get_tags(self) -> List[str]:
        """Get all tag names."""

    def get_tags_with_counts(self) -> List[Dict]:
        """Get tags with usage counts."""

    # Version History
    def get_prompt_versions(self, prompt_id: int) -> List[Dict]:
        """Get version history for prompt."""

    # Backward Compatibility
    @property
    def prompts(self) -> Dict:
        """Dict-style interface for backward compatibility."""

    @property
    def next_id(self) -> int:
        """Next available prompt ID."""

    def save_prompts(self) -> bool:
        """No-op with deprecation warning."""
```

### 4.2 Repository Interfaces

**PromptRepository:**

```python
class PromptRepository(BaseRepository[Prompt]):
    def search(self, query: str = "", category: str = None,
               tags: List[str] = None, favorite: bool = None,
               offset: int = 0, limit: int = None) -> List[Prompt]:
        """Search prompts with multiple criteria."""

    def get_favorites(self) -> List[Prompt]:
        """Get all favorite prompts."""

    def get_statistics(self) -> Dict:
        """Get prompt statistics."""
```

**VersionRepository:**

```python
class VersionRepository:
    def create_version(self, prompt: Prompt, author: str, message: str,
                       parent_version_id: str = None) -> PromptVersion:
        """Create new version snapshot."""

    def get_versions_for_prompt(self, prompt_id: int) -> List[PromptVersion]:
        """Get all versions for a prompt, ordered newest first."""

    def get_latest_version(self, prompt_id: int) -> Optional[PromptVersion]:
        """Get most recent version."""

    def get_version_count(self, prompt_id: int) -> int:
        """Count versions for a prompt."""
```

---

## 5. Data Flow

### 5.1 Create Prompt Flow

```
1. API Endpoint receives POST request with prompt data
2. PromptDataService.add_new_prompt() called
3. Service opens database session
4. CategoryRepository.get_or_create() for category
5. TagRepository.get_or_create_many() for tags
6. PromptRepository.create() creates prompt
7. VersionRepository.create_version() creates initial version
8. Session commits transaction
9. Return prompt ID to client
```

### 5.2 Update Prompt Flow

```
1. API Endpoint receives PUT request with updated data
2. PromptDataService.update_prompt() called
3. Service opens database session
4. PromptRepository.get_by_id() retrieves existing prompt
5. Get latest version for parent_version_id
6. PromptRepository.update() modifies prompt
7. VersionRepository.create_version() creates new version snapshot
8. Session commits transaction
9. Return success to client
```

### 5.3 Search Flow

```
1. API Endpoint receives GET request with query parameters
2. PromptDataService.search_prompts() called
3. Service opens database session
4. PromptRepository.search() builds query:
   - Text search: WHERE title LIKE '%query%' OR prompt LIKE '%query%'
   - Category filter: JOIN categories WHERE category.name = ?
   - Tag filter: JOIN prompt_tags JOIN tags WHERE tag.name IN (...)
   - Favorite filter: WHERE favorite = TRUE
5. Apply pagination (OFFSET/LIMIT)
6. Execute query with indexes
7. Convert ORM objects to dict format
8. Return results to client
```

---

## 6. Migration Strategy

### 6.1 Migration Script

**Purpose:** Migrate existing JSON data to database

**Input:** `data/prompts.json`

**Output:** Populated database tables

**Process:**

```
1. Load JSON file
2. Create database session
3. For each prompt:
   a. Get or create category
   b. Get or create tags
   c. Create prompt with original ID
   d. Create versions from version history
4. Commit transaction
5. Report statistics
```

**Error Handling:**

- Validation errors: Log and skip invalid entries
- Duplicate IDs: Skip with warning
- Database errors: Rollback transaction, exit with error

### 6.2 Rollback Strategy

**Option 1:** Keep JSON file as backup for 30 days

**Option 2:** Export database to JSON format

**Option 3:** Database migrations can be rolled back via Alembic

```bash
# Rollback last migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade <revision>

# Rollback all
alembic downgrade base
```

---

## 7. Testing Strategy

### 7.1 Unit Tests

**Repository Tests:**

- Test each CRUD operation
- Test search with various filter combinations
- Test edge cases (empty results, invalid IDs)
- Test transaction rollback on errors

**Service Tests:**

- Test backward compatibility interface
- Test version creation on updates
- Test bulk operations
- Test category/tag management

### 7.2 Integration Tests

**Database Integration:**

- Test with in-memory SQLite
- Test complete workflows (create → update → delete)
- Test concurrent operations
- Test backup/restore operations

### 7.3 Performance Tests

**Load Tests:**

- Test with 10,000+ prompts
- Measure query performance
- Test pagination efficiency
- Test connection pool behavior

### 7.4 Migration Tests

**Migration Script Tests:**

- Test with sample JSON data
- Test with large datasets
- Test error conditions
- Verify data integrity post-migration

---

## 8. Deployment

### 8.1 Prerequisites

**System Requirements:**

- Python 3.11+
- PostgreSQL 15+ (production) or SQLite 3.x (development)
- 1GB RAM minimum
- 1GB disk space

**Python Dependencies:**

- SQLAlchemy >= 2.0
- Alembic >= 1.12
- psycopg2-binary >= 2.9 (for PostgreSQL)
- pydantic-settings >= 2.0

### 8.2 Deployment Steps

**Step 1: Install Dependencies**

```bash
pip install -e .
```

**Step 2: Configure Environment**

```bash
cp .env.example .env
# Edit .env with DATABASE_URL
```

**Step 3: Run Migrations**

```bash
alembic upgrade head
```

**Step 4: Migrate Data** (if needed)

```bash
python scripts/migrate_json_to_db.py
```

**Step 5: Verify**

```bash
python scripts/test_db_operations.py
```

### 8.3 Docker Deployment

**Docker Compose:**

```bash
docker-compose up -d
docker-compose exec web alembic upgrade head
```

---

## 9. Monitoring and Maintenance

### 9.1 Monitoring

**Key Metrics:**

- Database connection pool utilization
- Query execution times
- Error rates
- Backup success/failure rates

**Logging:**

- All database errors logged at ERROR level
- Query logging available via DB_ECHO=true
- Audit logging for version control operations

### 9.2 Maintenance

**Daily:**

- Monitor error logs
- Check backup completion

**Weekly:**

- Review slow query logs
- Check database size growth
- Verify backup integrity

**Monthly:**

- Vacuum/analyze database (PostgreSQL)
- Review and optimize indexes
- Test restore procedures

---

## 10. Security Considerations

### 10.1 SQL Injection Prevention

- **Requirement:** ALL database queries MUST use parameterized statements
- **Implementation:** SQLAlchemy ORM provides automatic parameterization
- **Validation:** Never construct SQL with string concatenation

### 10.2 Database Access Control

- **Requirement:** Database credentials stored in environment variables
- **Implementation:** Use .env files, never commit credentials
- **Production:** Use secrets management (e.g., AWS Secrets Manager)

### 10.3 Backup Security

- **Requirement:** Backup files have restricted permissions (600)
- **Implementation:** Set permissions immediately after creation
- **Encryption:** Consider encrypting backups for sensitive data

### 10.4 Connection Security

- **Requirement:** Use SSL/TLS for database connections in production
- **Implementation:** Configure DATABASE_URL with sslmode parameter
- **Example:** `postgresql://user:pass@host:5432/db?sslmode=require`

---

## 11. Performance Optimization

### 11.1 Database Indexes

All frequently queried columns have indexes:

- prompts.title, category_id, favorite, created_at, updated_at
- prompt_versions.prompt_id, version_id, created_at
- categories.name, tags.name

### 11.2 Query Optimization

- Use eager loading (joinedload) to prevent N+1 queries
- Implement pagination for large result sets
- Use database-level sorting instead of Python sorting

### 11.3 Connection Pooling

- PostgreSQL uses connection pool (default 20 connections)
- Pool timeout: 30 seconds
- Connection recycling: 3600 seconds

---

## 12. Constraints and Limitations

### 12.1 Technical Constraints

- **Database Support:** Only SQLite and PostgreSQL are supported
- **Python Version:** Requires Python 3.11+ for modern type hints
- **ID Preservation:** Migrated prompts retain original IDs, but this limits maximum ID value
- **Full-Text Search:** Not implemented in Phase 1-9, uses LIKE-based search

### 12.2 Operational Constraints

- **Migration Downtime:** Application should be stopped during migration
- **Database Size:** SQLite has 140TB theoretical limit, practical limit ~1TB
- **Concurrent Writes:** SQLite supports one writer at a time
- **Backup Size:** Database backups can be large for datasets with many versions

---

## 13. Dependencies

### 13.1 Internal Dependencies

- **src/db/models/**: SQLAlchemy ORM models
- **src/db/repositories/**: Repository implementations
- **src/db/session.py**: Database session management
- **src/db/config.py**: Database configuration
- **src/services/**: Service layer implementations

### 13.2 External Dependencies

**Required:**

- SQLAlchemy 2.0+
- Alembic 1.12+
- pydantic 2.0+
- pydantic-settings 2.0+

**Optional:**

- psycopg2-binary 2.9+ (PostgreSQL support)
- pytest 7.0+ (testing)
- pytest-cov (coverage)

---

## 14. API Compatibility

### 14.1 Maintained Endpoints

All existing API endpoints maintain identical:

- Request parameters
- Response formats
- Status codes
- Error messages

**Example:**

```python
# GET /api/prompts/{id}
# Before (JSON):
{
  "id": 1,
  "title": "Example",
  "prompt": "Content",
  "category": "General",
  "tags": ["tag1", "tag2"],
  "favorite": false,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-02T00:00:00"
}

# After (Database):
{
  "id": 1,
  "title": "Example",
  "prompt": "Content",
  "category": "General",
  "tags": ["tag1", "tag2"],
  "favorite": false,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-02T00:00:00"
}
# Identical!
```

### 14.2 Deprecated Methods

**PromptDataService.save_prompts():**

- Status: Deprecated
- Behavior: No-op, returns True
- Warning: DeprecationWarning emitted
- Removal: Planned for next major version

---

## 15. Acceptance Criteria

### 15.1 Functional Acceptance

- [ ] All prompts can be migrated from JSON to database without data loss
- [ ] CRUD operations work correctly for prompts
- [ ] Search and filtering return correct results
- [ ] Version history is preserved and queryable
- [ ] Categories and tags are managed correctly
- [ ] Backup and restore operations succeed
- [ ] All existing API endpoints return correct responses

### 15.2 Performance Acceptance

- [ ] Load 10,000 prompts in < 1 second
- [ ] Search across 10,000 prompts in < 500ms
- [ ] Single CRUD operation completes in < 100ms
- [ ] Test suite runs in < 30 seconds

### 15.3 Reliability Acceptance

- [ ] All tests pass (42+ tests)
- [ ] Test coverage >= 85%
- [ ] No data corruption under normal operations
- [ ] Transaction rollback works on errors
- [ ] Backup/restore maintains data integrity

### 15.4 Deployment Acceptance

- [ ] Docker Compose deployment works without errors
- [ ] Health checks pass
- [ ] Alembic migrations apply successfully
- [ ] Documentation is complete and accurate

---

## 16. Future Enhancements

### 16.1 Phase 12: Full-Text Search

- Implement PostgreSQL FTS for better search
- Add search ranking and relevance scoring
- Support advanced query syntax

### 16.2 Phase 13: Multi-User Support

- Implement user authentication
- Add user-specific prompt collections
- Implement sharing and permissions

### 16.3 Phase 14: Real-Time Sync

- WebSocket support for live updates
- Multi-client synchronization
- Conflict resolution

### 16.4 Phase 15: Analytics

- Track prompt usage statistics
- Generate usage reports
- Implement recommendation system

---

## 17. References

### 17.1 Internal Documentation

- [Phase 7: Service Layer Refactoring](../phase7_service_layer_migration.md)
- [Phase 8: Backup System Integration](../phase8_backup_system_integration.md)
- [Phase 9: Test Infrastructure](../phase9_test_infrastructure.md)
- [Deployment Guide](../DEPLOYMENT.md)
- [Migration Guide](../MIGRATION_GUIDE.md)

### 17.2 External References

- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)

---

## 18. Glossary

- **ACID:** Atomicity, Consistency, Isolation, Durability - database transaction properties
- **FTS:** Full-Text Search - advanced text search capabilities
- **ORM:** Object-Relational Mapping - technique for converting between database rows and Python objects
- **Repository Pattern:** Design pattern that mediates between domain and data access layers
- **Migration:** Process of moving data from one storage system to another
- **Denormalization:** Storing redundant data to improve read performance
- **Connection Pool:** Cache of database connections for reuse
- **Eager Loading:** Loading related objects in a single query to avoid N+1 problem
- **N+1 Problem:** Performance issue where N queries follow 1 initial query

---

**Document Control:**

- Version 1.0 - Initial specification
- Last updated: 2025-01-28
- Status: Implemented (Phases 1-9 complete)
- Next review: After Phase 12 implementation
