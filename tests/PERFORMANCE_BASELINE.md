# Performance Baseline Report

Generated: 2026-07-03T17:57:12.626632+00:00
Platform: darwin

## Summary

This report documents the performance characteristics of `list_all_with_counts()` operations for tags and categories.

## Category Performance

| Dataset | Categories | Prompts | Time (s) | Queries | Memory (MB) |
|---------|-----------|---------|----------|---------|-------------|
| Small | 10 | 100 | 0.0016 | 1 | 0.04 |
| Medium | 100 | 1000 | 0.0026 | 1 | 0.13 |
| Large | 1000 | 5000 | 0.0208 | 1 | 1.49 |

## Tag Performance

| Dataset | Tags | Prompts | Time (s) | Queries | Memory (MB) |
|---------|------|---------|----------|---------|-------------|
| Small | 100 | 500 | 0.0117 | 1 | 0.32 |
| Medium | 500 | 2000 | 0.0216 | 1 | 0.88 |
| Large | 1000 | 10000 | 0.0556 | 1 | 2.46 |

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

