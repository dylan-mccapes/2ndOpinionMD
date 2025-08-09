# Production API Routing and HTTPS

Frontend expects the API base to be available at `${window.location.origin}/api` by default, or via the environment variable `REACT_APP_API_BASE_URL`.

Example production configuration:

1) Frontend environment
- File: frontend/react/.env.production (not committed)
  REACT_APP_API_BASE_URL=https://your-public-domain.example.com/api

2) Reverse proxy (nginx example)
- Ensure /api is forwarded to FastAPI on localhost:8000:
  location /api/ {
    proxy_pass http://127.0.0.1:8000/api/;
    proxy_set_header Host $host;
    proxy_http_version 1.1;
  }

3) HTTPS and Mixed Content
- Serve both the site and the API over HTTPS to avoid mixed-content blocking in the browser.
- If the API is on a different domain, configure CORS on the backend to allow the site origin.

4) Verification steps (external)
- Open DevTools → Network on the public site and attempt login. Requests should go to:
  https://your-public-domain.example.com/api/...
- No mixed-content or CORS errors.
- Backend logs should show /api/auth/token requests.

5) Curl checks
- Replace with your public domain:
  ORIGIN="https://your-public-domain.example.com"
  curl -i "$ORIGIN/api/auth/health"
  curl -i -X POST "$ORIGIN/api/auth/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data "username=fake@example.com&password=bad" | head -n 20
