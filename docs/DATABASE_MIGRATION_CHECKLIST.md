# Database Migration Implementation Checklist

This checklist provides a comprehensive testing guide for the database migration from JSON file storage to SQLite/PostgreSQL before merging to main.

## 📋 Pre-Merge Verification Checklist

### 1. Test Suite Verification

- [X] ~~***Run full test suite**: `pytest`*~~ [2025-11-29]
  - Expected: 426+ tests passing
  - Expected: Coverage ≥ 85% (current: 86.46%)
  - Expected: Execution time < 10 seconds
  - [X] ~~*Verify no UNIQUE constraint failures*~~ [2025-11-29]
  - [X] ~~*Verify BackupService tests all pass (42/42)*~~ [2025-11-29]
  - [X] ~~*Verify Repository tests all pass (78/78)*~~ [2025-11-29]
  - [X] ~~*Verify Service tests pass (88/88 target)*~~ [2025-11-29]
  - [X] ~~*Verify Version Control tests all pass (48/48)*~~ [2025-11-29]

- [X] ~~***Check specific test categories**:*~~ [2025-11-29]
  ```bash
  pytest tests/test_db_repositories.py -v
  pytest tests/test_db_services.py -v
  pytest tests/test_version_system.py -v
  pytest tests/test_api_endpoints.py -v
  ```

### 2. Database Functionality Tests

#### SQLite (Development)

- [X] ~~***Fresh database creation***~~ [2025-11-29]
  ```bash
  rm -f data/prompts.db
  python run_web.py
  ```
  - [X] ~~*Database file created at `data/prompts.db`*~~ [2025-11-29]
  - [X] ~~*All tables created (prompts, prompt_versions, categories, tags, users, backups, etc.)*~~ [2025-11-29]
  - [X] ~~*App starts without errors*~~ [2025-11-29]

- [ ] **CRUD Operations**
  - [X] ~~*Create a new prompt via web UI*~~ [2025-11-29]
  - [X] ~~*Update the prompt (verify version created)*~~ [2025-11-29]
  - [X] ~~*Delete the prompt*~~ [2025-11-29]
  - [X] ~~*Create prompt with category and tags*~~ [2025-11-29]
  - [ ] Toggle favorite status #TODO: fix the favorite toggle bug, when it is first clicked, it remains visually as before despite actually being changed.
  - [ ] Search/filter prompts

- [ ] **Version Control**
  - [ ] Create prompt (initial version)
  - [ ] Update prompt 3 times (3 new versions)
  - [ ] View version history (should show 4 versions)
  - [ ] Compare two versions
  - [ ] Revert to previous version
  - [ ] Verify revert creates new version (not destructive)

- [ ] **Categories & Tags**
  - [ ] Create prompts with different categories
  - [ ] Add multiple tags to prompts
  - [ ] Filter by category
  - [ ] Filter by tags
  - [ ] Verify category/tag counters are accurate

- [ ] **Backup System**
  - [ ] Create manual backup
  - [ ] List backups (verify metadata)
  - [ ] Restore from backup
  - [ ] Verify pre-restore safety backup created
  - [ ] Delete backup
  - [ ] Check backup compression (if old backups exist)
  - [ ] Verify backup IDs are unique (no duplicates)

#### PostgreSQL (Production - Optional)

- [ ] **Set up PostgreSQL database**
  ```bash
  export DATABASE_URL="postgresql://user:password@localhost:5432/promptvault"
  python -c "from src.db.session import create_all_tables; create_all_tables()"
  ```

- [ ] **Verify PostgreSQL-specific features**
  - [ ] Database connection successful
  - [ ] All tables created with correct schema
  - [ ] CRUD operations work
  - [ ] Backup system uses pg_dump
  - [ ] Restore from pg_dump backup works

### 3. Data Migration Testing

- [ ] **Migration from JSON to Database**
  - [ ] Start with existing `data/prompts_data.json` file
  - [ ] Run migration script (if available) or manual migration
  - [ ] Verify all prompts migrated
  - [ ] Verify all version history preserved
  - [ ] Verify all categories migrated
  - [ ] Verify all tags migrated
  - [ ] Verify prompt counts match

### 4. Performance Testing

- [ ] **Test with realistic data**
  - [ ] Create 100+ prompts
  - [ ] Each prompt with 5+ versions
  - [ ] Search/filter performance < 1 second
  - [ ] List all prompts performance < 1 second
  - [ ] Backup creation < 5 seconds

- [ ] **Memory usage**
  - [ ] Monitor memory during heavy operations
  - [ ] Check for memory leaks during version operations
  - [ ] Verify database connection pool works correctly

### 5. API Endpoint Testing

- [ ] **Prompt Management APIs**
  - [ ] `GET /api/prompts` - List all prompts
  - [ ] `POST /api/prompts` - Create new prompt
  - [ ] `GET /api/prompts/{id}` - Get specific prompt
  - [ ] `PUT /api/prompts/{id}` - Update prompt
  - [ ] `DELETE /api/prompts/{id}` - Delete prompt
  - [ ] `GET /api/prompts/search` - Search with filters
  - [ ] `PUT /api/prompts/{id}/favorite` - Toggle favorite

- [ ] **Version Control APIs**
  - [ ] `GET /api/prompts/{id}/versions` - Get version history
  - [ ] `GET /api/prompts/{id}/versions/compare` - Compare versions
  - [ ] `GET /api/prompts/{id}/versions/{version_id}` - Get specific version
  - [ ] `POST /api/prompts/{id}/versions/{version_id}/revert` - Revert to version

- [ ] **Backup APIs**
  - [ ] `GET /api/backups` - List all backups
  - [ ] `POST /api/backups` - Create backup
  - [ ] `POST /api/backups/{id}/restore` - Restore backup
  - [ ] `DELETE /api/backups/{id}` - Delete backup
  - [ ] `GET /api/backups/stats` - Backup statistics

- [ ] **Category & Tag APIs**
  - [ ] `GET /api/categories` - List all categories
  - [ ] `GET /api/tags` - List all tags

### 6. Error Handling & Edge Cases

- [ ] **Database connection errors**
  - [ ] Stop database server → verify graceful error handling
  - [ ] Invalid DATABASE_URL → verify clear error message
  - [ ] Database file permissions issue → verify error handling

- [ ] **Data validation**
  - [ ] Try to create prompt with invalid data
  - [ ] Try to update non-existent prompt
  - [ ] Try to delete non-existent prompt
  - [ ] Try to revert to non-existent version
  - [ ] Try to restore non-existent backup

- [ ] **Concurrent operations**
  - [ ] Multiple users creating prompts simultaneously
  - [ ] Multiple users updating same prompt
  - [ ] Backup creation during active usage

### 7. Backwards Compatibility

- [ ] **Legacy code deprecation warnings**
  - [ ] Check for deprecation warnings in logs
  - [ ] Verify legacy JSON services still work (if needed)
  - [ ] Ensure migration path documented

- [ ] **Configuration**
  - [ ] Default to SQLite if no DATABASE_URL set
  - [ ] Environment variables work correctly
  - [ ] Docker compose configuration works

### 8. Documentation Review

- [ ] **Technical Documentation**
  - [ ] `docs/SPECS/SPEC_DATABASE.md` is accurate
  - [ ] `docs/TESTING.md` is complete
  - [ ] `docs/AGENTS.md` reflects database architecture
  - [ ] `CHANGELOG.md` includes database migration details

- [ ] **Code Documentation**
  - [ ] All new classes have docstrings
  - [ ] All new methods have docstrings
  - [ ] Complex database queries are commented
  - [ ] Migration steps are documented

### 9. Security Verification

- [ ] **SQL Injection Protection**
  - [ ] All queries use parameterized statements
  - [ ] No raw SQL string concatenation
  - [ ] ORM usage is consistent

- [ ] **Data Privacy**
  - [ ] Backup files have appropriate permissions
  - [ ] Database credentials not exposed in logs
  - [ ] Sensitive data not in error messages

### 10. Docker & Deployment

- [ ] **Docker Build**
  ```bash
  docker-compose build
  docker-compose up
  ```
  - [ ] Container starts successfully
  - [ ] Database volume mounted correctly
  - [ ] Data persists across container restarts
  - [ ] Backup directory accessible

- [ ] **Data Persistence**
  - [ ] Stop container, restart → data still present
  - [ ] Database file in `./data/prompts.db` on host
  - [ ] Backups in `./data/backups/` on host

### 11. Git & Version Control

- [ ] **Branch Status**
  - [ ] All changes committed
  - [ ] No uncommitted files
  - [ ] Branch up to date with origin

- [ ] **Code Review**
  - [ ] No debug print statements
  - [ ] No commented-out code blocks
  - [ ] No TODO comments for critical issues
  - [ ] Consistent code style

### 12. Final Verification

- [ ] **Clean slate test**
  ```bash
  # Remove all test data
  rm -rf data/prompts.db data/backups/* data/logs/*

  # Run full test suite
  pytest

  # Start fresh app
  python run_web.py
  ```
  - [ ] All tests pass
  - [ ] App starts cleanly
  - [ ] No errors in logs

- [ ] **Stress test**
  - [ ] Create 500 prompts
  - [ ] Create 50 backups
  - [ ] Perform bulk operations
  - [ ] Monitor performance and errors

## 📊 Success Criteria

✅ **Must Have (Blocking Issues)**:
- [ ] Test suite: ≥ 510 tests passing (99%+ pass rate)
- [ ] Coverage: ≥ 85% (current: 86.46%)
- [ ] No UNIQUE constraint errors
- [ ] All CRUD operations work via API
- [ ] Version control fully functional
- [ ] Backup/restore works correctly
- [ ] SQLite works in development
- [ ] No data loss during migrations

⚠️ **Should Have (Important but not blocking)**:
- [ ] PostgreSQL tested and working
- [ ] Performance benchmarks met
- [ ] All documentation updated
- [ ] Docker deployment verified
- [ ] Error handling comprehensive

💡 **Nice to Have (Future improvements)**:
- [ ] Migration script for JSON → Database
- [ ] Database optimization (indexes, etc.)
- [ ] Monitoring/observability improvements
- [ ] Additional backup strategies

## 🚀 Merge Readiness

When all "Must Have" criteria are met, the feature is ready to merge to main.

**Final Sign-off**:
- [ ] All blocking issues resolved
- [ ] Test suite green
- [ ] Documentation complete
- [ ] No known regressions
- [ ] Team review completed (if applicable)

---

## 📝 Testing Notes

Record any issues, observations, or concerns discovered during testing:

```
Date: _______________
Tester: _______________

Issues Found:
1.
2.
3.

Performance Observations:
-
-

Recommendations:
-
-
```

## 🔧 Troubleshooting Guide

### Common Issues

**Issue**: Database file locked
- **Solution**: Close all database connections, restart app

**Issue**: Migration fails
- **Solution**: Check database schema version, verify data integrity

**Issue**: Tests fail intermittently
- **Solution**: Check for test isolation issues, verify database cleanup

**Issue**: Backup IDs collide
- **Solution**: This should be fixed (microsecond precision), but verify backups created within same second have unique IDs

**Issue**: Coverage below 85%
- **Solution**: Check `.coveragerc` excludes legacy services, run full test suite

---

**Last Updated**: 2025-11-29
**Migration Status**: Ready for final verification before merge
**Test Coverage**: 86.46%
**Passing Tests**: 512/514 (99.6%)
