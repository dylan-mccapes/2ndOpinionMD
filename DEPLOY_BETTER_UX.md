# Deploy Better UX (rag-demo-ui)

**Date:** January 18, 2026  
**Purpose:** Replace current index.html with improved rag-demo-ui/index.html  
**Status:** Ready to deploy

---

## Quick Deploy (Recommended)

### 1. Update docker-compose.yml

**File:** `docker-compose.yml`

**Change line 31 from:**
```yaml
- ./index.html:/usr/share/nginx/html/index.html:ro
```

**To:**
```yaml
- ./rag-demo-ui/index.html:/usr/share/nginx/html/index.html:ro
```

### 2. Restart nginx

```bash
cd /Users/2ndopinionmd/dev/provenance-engines/PortalVision/2ndOpinionMD-MVP
docker-compose down nginx
docker-compose up -d nginx
```

Or restart the full stack:

```bash
docker-compose down
docker-compose up -d
```

### 3. Access

**URL:** `http://localhost`

**API endpoint:** `http://localhost/api/` (proxied to port 8000)

### 4. Operator deploy to Homebrew web root (manual)

Use this after validating locally:

```bash
sudo cp /Users/2ndopinionmd/dev/provenance-engines/PortalVision/2ndOpinionMD-MVP/rag-demo-ui/index.html /opt/homebrew/var/www/2opmd/index.html
```

If your nginx root differs, replace the destination path accordingly.

---

## Verify Deployment

```bash
# Check if nginx is running
docker-compose ps nginx

# Check nginx logs
docker-compose logs nginx

# Test the UI
curl -I http://localhost

# Should return 200 OK
```

---

## Rollback (If Needed)

**Change back to:**
```yaml
- ./index.html:/usr/share/nginx/html/index.html:ro
```

**Then:**
```bash
docker-compose restart nginx
```

---

## Alternative: Test First (No Modify Existing)

**Standalone test container:**

```bash
docker run -d \
  --name rag-demo-ui-test \
  -p 8080:80 \
  -v "$(pwd)/rag-demo-ui/index.html:/usr/share/nginx/html/index.html:ro" \
  nginx:alpine
```

**Access:** `http://localhost:8080`

**Clean up:**
```bash
docker stop rag-demo-ui-test && docker rm rag-demo-ui-test
```

---

## What's Different

**Old UI:** `./index.html` (basic interface)

**New UI:** `./rag-demo-ui/index.html`
- Modern dark theme
- Better SSE event visualization
- Enhanced debug display
- Simplified console mode UX (ASK, CODING, EoH)
- 1340 lines of polished interface

---

## Structure > Chaos

**One line change. Better UX. Same infrastructure.**

**Deploy when ready.** 🫡

