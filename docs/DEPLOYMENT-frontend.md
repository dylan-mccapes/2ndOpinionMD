2ndOpinionMD Frontend Deployment (CRA)

Prereqs
- Node.js 18 (nvm use 18)
- Yarn
- Reverse proxy routing /api → FastAPI on 127.0.0.1:8000
- Domain: https://2ndopinionmd.ai

1) Set production API base URL at build time
CRA reads env only at build time.

Option A: .env.production (recommended)
- In frontend/react, create .env.production with:
REACT_APP_API_BASE_URL=https://2ndopinionmd.ai/api

Option B: export in the same shell for the build
export REACT_APP_API_BASE_URL=https://2ndopinionmd.ai/api

2) Install and build
cd frontend/react
nvm use 18
yarn install --frozen-lockfile
# If using Option B, ensure the export is in this shell
yarn build

Result: frontend/react/build contains the production bundle with the correct API base.

3) Deploy the build
- Copy/sync frontend/react/build to your web root or serve it directly.
- Example (static server):
  yarn global add serve
  serve -s build

- If using nginx or Caddy, point the site root to the build directory and reload the server.

4) Reverse proxy sanity (nginx example)
location /api/ {
  proxy_pass http://127.0.0.1:8000/api/;
  proxy_set_header Host $host;
  proxy_http_version 1.1;
}

5) Clear cache / service worker (if applicable)
- In the browser: DevTools → Application → Service Workers → Unregister
- Hard refresh the site

6) Verify on production (same-origin)
- Open https://2ndopinionmd.ai/login
- DevTools → Network:
  - POST https://2ndopinionmd.ai/api/auth/token
    - Content-Type: application/x-www-form-urlencoded
    - 200 with access_token for valid creds; 401 for invalid creds
  - GET https://2ndopinionmd.ai/api/auth/users/me
    - Authorization: Bearer <token>
    - 200 and JSON user info
- UI should route to the dashboard and persist session on reload (token in localStorage)

7) Quick curl checks (optional)
curl -I https://2ndopinionmd.ai/api/health
curl -i -X POST https://2ndopinionmd.ai/api/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "username=fake@example.com&password=wrong" | head -n 20

Notes
- If you need a staging/preview domain to call prod API cross-origin, add that origin to the backend CORS allowlist; otherwise keep same-origin for production.
- The frontend defaults to same-origin /api when REACT_APP_API_BASE_URL is not set and will throw if a production build is configured to point at localhost or RFC1918 ranges.
