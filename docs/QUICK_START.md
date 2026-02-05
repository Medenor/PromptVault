# ⚠️ DEPRECATED - Quick Start Guide

**This document has been deprecated and replaced by the new Turnkey Deployment System.**

👉 **Please use the new deployment guide instead:**
- [Turnkey Deployment Guide](DEPLOYMENT.md)
- [Deployment Orchestration](scripts/setup/DEPLOY_README.md)

## Migration to New System

The quick start guide has been replaced with a comprehensive deployment orchestration system that provides:

✅ **Automated five-phase deployment**
✅ **Pre-flight validation checks**
✅ **Automatic rollback on failure**
✅ **Dry-run mode for safe testing**
✅ **CI/CD integration**

## New Deployment Command

```bash
# Use the new deployment script instead
python scripts/setup/deploy.py --dry-run  # Test first
python scripts/setup/deploy.py           # Actual deployment
```

For more information, see the [complete deployment documentation](DEPLOYMENT.md).
