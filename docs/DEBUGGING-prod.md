Prod Debugging Quickstart

Goals
- Verify the SPA is served statically by nginx (not via a dev proxy)
- Confirm the frontend resolves the correct API base in production
- Validate login calls hit the backend
- Use built-in diagnostics to speed up troubleshooting

1) Check static hosting
- Stop any dev server (serve -s build etc.). The site root must still load.
- If you see 502 when dev server stops, nginx is proxying "/" to :3000; update nginx to serve root from:
  /opt/homebrew/var/www/2ndopinionmd
  and proxy only "/api" to 127.0.0.1:8000.

2) Runtime diagnostics
- Visit https://2ndopinionmd.ai/?debug=1
  - Open the console; you should see:
    [Diagnostics] API_BASE: https://2ndopinionmd.ai/api
    [Diagnostics] /api/health 200 { ... }
- Visit https://2ndopinionmd.ai/diagnostics
  - Click buttons to call /api/health and /api/meta/ping
  - Both should succeed (200) with JSON responses

3) Login flow checks
- In DevTools → Network on https://2ndopinionmd.ai/login:
  - POST https://2ndopinionmd.ai/api/auth/token (Content-Type: application/x-www-form-urlencoded)
  - GET https://2ndopinionmd.ai/api/auth/users/me (Authorization: Bearer <token>)
- Both should return 200 for valid credentials; invalid creds return 401 on token.

4) Curl probes
curl -i https://2ndopinionmd.ai/api/health
curl -i https://2ndopinionmd.ai/api/meta/ping
curl -i -X POST https://2ndopinionmd.ai/api/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "username=fake@example.com&password=wrong"

5) Nginx logs (Homebrew macOS)
tail -f /opt/homebrew/var/log/nginx/access.log /opt/homebrew/var/log/nginx/error.log

6) Build-time env reminders (CRA)
- Prefer same-origin fallback; optionally set:
  REACT_APP_API_BASE_URL=https://2ndopinionmd.ai/api
- Rebuild with Yarn on Node 18:
  cd frontend/react && nvm use 18 && yarn build
- Deploy build/ to /opt/homebrew/var/www/2ndopinionmd
- Clear service worker/cache and hard refresh
