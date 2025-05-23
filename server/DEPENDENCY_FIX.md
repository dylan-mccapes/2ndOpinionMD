# Dependency Compatibility Fix

## Overview
This document provides instructions for fixing the dependency compatibility issues between pydantic, pydantic-settings, and fastapi-mail in the 2ndOpinionMD-MVP server.

## The Issue
The server has a dependency conflict:
- fastapi-mail 1.4.1 requires pydantic<2.0
- pydantic-settings requires pydantic>=2.0.1
- This creates an impossible dependency resolution

## Solution
We've implemented a compatibility layer that allows the server to work with any version of pydantic and fastapi-mail. The solution involves:

1. A custom compatibility layer for fastapi-mail in `utils/email/fastapi_mail_compat.py`
2. Updated imports in `utils/email/config.py` to use our compatibility layer
3. This approach works with the encrypted logging implementation that was already merged

## Installation Instructions

### Option 1: Use the compatibility layer (recommended)
This approach uses our compatibility layer and doesn't require specific package versions:

```bash
cd /Users/2ndopinionmd/Sites/2ndOpinionMD-MVP
git fetch
git checkout devin/fix-pydantic-compatibility
```

### Option 2: Install specific compatible versions
If you prefer to use specific package versions instead of the compatibility layer:

```bash
cd /Users/2ndopinionmd/Sites/2ndOpinionMD-MVP/server
pip install "pydantic==1.10.8" "fastapi-mail==1.2.5" "pydantic-settings==1.0.0" --force-reinstall
```

## Verification
After applying either solution, you can verify it works by running:

```bash
cd /Users/2ndopinionmd/Sites/2ndOpinionMD-MVP/server
python -m uvicorn api.app:app --host 0.0.0.0 --port 8000
```

The server should start without any dependency errors, and encrypted logs will be stored in the configured directory.
