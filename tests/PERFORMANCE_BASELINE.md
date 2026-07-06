# Performance Baseline Report

Generated: 2026-07-03T18:18:43.919038+00:00
Platform: darwin

## Summary

This report documents the performance characteristics of `list_all_with_counts()` operations for tags and categories.

## Category Performance

| Dataset | Categories | Prompts | Time (s) | Queries | Memory (MB) |
|---------|-----------|---------|----------|---------|-------------|
| Small | 10 | 100 | 0.0021 | 1 | 0.04 |
| Medium | 100 | 1000 | 0.0034 | 1 | 0.14 |
| Large | 1000 | 5000 | 0.0258 | 1 | 1.50 |

## Tag Performance

| Dataset | Tags | Prompts | Time (s) | Queries | Memory (MB) |
|---------|------|---------|----------|---------|-------------|
| Small | 100 | 500 | 0.0137 | 1 | 0.32 |
| Medium | 500 | 2000 | 0.0252 | 1 | 1.04 |
| Large | 1000 | 10000 | 0.0596 | 1 | 2.43 |

## Analysis

### Query Optimization

- Both operations use efficient JOIN queries
- Query count remains constant regardless of dataset size
- No N+1 query problems detected

### Performance Characteristics

- Response time scales linearly with dataset size
- Memory usage is proportional to result set size
- Operations complete in under 5 seconds for datasets up to 1000 items

## Recommendations

1. **Pagination**: For datasets exceeding 1000 items, consider implementing pagination
2. **Caching**: Consider caching results for frequently accessed lists
3. **Indexing**: Ensure proper database indexes are maintained
4. **Monitoring**: Set up alerts if response time exceeds baseline by >10%

