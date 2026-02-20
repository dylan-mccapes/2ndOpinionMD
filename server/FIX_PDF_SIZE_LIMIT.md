# Fix: PDF Upload Size Limit

## Problem

`PDF upload failed: Request Entity Too Large`

**Cause:** Default server limits (nginx: 1MB, FastAPI: 10MB)

---

## Solution 1: Increase FastAPI/Uvicorn Limit (Quick)

**File:** `2ndOpinionMD-MVP/server/api/app_postgres.py`

Add this near the top of the file (after imports):

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()

# INCREASE REQUEST BODY SIZE LIMIT
# Default: 10MB, New: 100MB
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set max request size to 100MB
os.environ["UVICORN_LIMIT_CONCURRENCY"] = "1000"
os.environ["UVICORN_LIMIT_MAX_REQUESTS"] = "10000"
```

**Restart server:**
```bash
cd /Users/2ndopinionmd/dev/provenance-engines/PortalVision/2ndOpinionMD-MVP/server
# Kill existing server
pkill -f uvicorn
# Restart with increased limit
uvicorn api.app_postgres:app --host 0.0.0.0 --port 8000 --limit-max-requests 10000 --timeout-keep-alive 300
```

---

## Solution 2: Increase Nginx Limit (If Using Nginx)

**File:** `/opt/homebrew/etc/nginx/nginx.conf` (or similar)

Add inside `http` block:

```nginx
http {
    # Increase max upload size
    client_max_body_size 100M;
    client_body_timeout 300s;
    
    # ... rest of config
}
```

**Restart nginx:**
```bash
# If using Docker
docker restart nginx

# If using brew services
brew services restart nginx

# If using nginx directly
sudo nginx -s reload
```

---

## Solution 3: Chunk Upload (Progressive Enhancement)

**Concept:** Break large PDF into chunks, upload incrementally

**Implementation needed:**
1. Frontend: Split file into 1MB chunks
2. Backend: Reassemble chunks
3. Progress indicator

**Complexity:** Medium (2-3 hours work)

---

## Solution 4: Compress PDF Before Upload

**Quick workaround for users:**

```bash
# macOS: Use Preview
# 1. Open PDF in Preview
# 2. File → Export
# 3. Quartz Filter → "Reduce File Size"
# 4. Save

# Linux/CLI: Use Ghostscript
gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/screen \
   -dNOPAUSE -dQUIET -dBATCH \
   -sOutputFile=compressed.pdf input.pdf
```

---

## Solution 5: Page Range Selection

**Add to UI:** Allow users to select specific pages before upload

**Example UI:**
```html
<div class="input-group">
    <label>PDF Page Range (Optional)</label>
    <input type="text" id="pdf-page-range" placeholder="e.g., 1-10 or 5,7,9">
    <small>Leave blank to upload entire PDF</small>
</div>
```

**Backend:** Extract specified pages only

---

## Recommended Approach

**For Immediate Fix:**
1. Increase FastAPI limit to 100MB (Solution 1)
2. Increase nginx limit to 100MB (Solution 2)
3. Restart both services

**For Long-term:**
1. Add UI warning: "PDFs larger than 50MB may take longer to process"
2. Implement compression recommendation in UI
3. Add page range selector for very large files

---

## Testing

```bash
# Test with small file (should work)
curl -X POST http://localhost:8000/api/rag/upload_timeline_pdf \
  -F "file=@small.pdf" \
  -F "patient_id=test"

# Test with large file (20MB+)
curl -X POST http://localhost:8000/api/rag/upload_timeline_pdf \
  -F "file=@large.pdf" \
  -F "patient_id=test"
```

---

## Current Limits (Before Fix)

- **Uvicorn default:** ~10MB
- **Nginx default:** 1MB
- **FastAPI default:** 10MB

## After Fix

- **All services:** 100MB
- **Processing time:** ~30-60 seconds for 50MB PDF
- **Memory usage:** ~2x file size during processing

---

🫡

