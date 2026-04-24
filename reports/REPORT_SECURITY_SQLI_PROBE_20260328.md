# Security Report: Automated SQL Injection Probe
**Date**: 2026-03-28  
**Severity**: Informational (no breach, no exposure)  
**Outcome**: Attack failed at the first layer — endpoint does not exist  
**Audience**: Founders (non-technical summary + technical detail)

---

## TL;DR for Founders

An automated bot hit our server with one of the most sophisticated SQL injection payloads you can throw at a web application. It got a 404. The endpoint it was targeting doesn't exist. Patient data was never in the path. We are safe. This report explains exactly what the bot was trying to do and why it failed.

---

## 1. What the Bot Was

This was **not a human**. This was `sqlmap` — the industry-standard automated SQL injection tool, widely used by both security researchers and attackers. It runs scripted probes in sequence, trying dozens of injection techniques at high speed. The tab-character obfuscation (`%09`) in the payload is a `sqlmap` signature technique to slip past web application firewalls (WAFs) that block the word "UNION" or "SELECT" when surrounded by spaces.

**Source IP**: `93.123.109.205` — Romanian IP space, consistent with a VPS used for automated scanning. This is not a targeted attack. This bot probes thousands of hosts per day looking for vulnerable endpoints.

---

## 2. What It Was Targeting

The endpoint it hit: `/api/v1/repos/search`

This is the **Gitea** repository search API — Gitea is a self-hosted GitHub alternative. The bot assumed our server was running Gitea (or something similar) and tried to exploit a known vulnerable `q=` parameter pattern. It wasn't looking for patient data. It was looking for database credentials and the ability to run arbitrary SQL.

This tells us: the bot is running a generic internet-wide scan, not a targeted attack on 2ndOpinionMD. It found our server's IP, saw a web server responding, and threw its entire Gitea exploit playbook at it. We don't run Gitea.

---

## 3. The Attack Decoded

The URL-encoded payload, decoded into readable SQL:

```sql
q=') 
UNION SELECT * FROM
  (SELECT null) AS a1
  JOIN (SELECT 1) as u
  JOIN (SELECT user()) AS b1    ← database username leak
  JOIN (SELECT user()) AS b2    ← database username leak (2nd column)
  JOIN (SELECT null) as a3
  ... (nulls to fill columns a4 through a22)
  WHERE ('%'='
```

### What each piece does

**`')`** — Closes the assumed SQL string and parenthesis. If the code does something like `WHERE name = '$input'`, injecting `')` breaks out of that string and lets the attacker append their own SQL.

**`UNION SELECT`** — Piggybacks a second query onto the first. The attacker's query runs alongside the real query and its results appear in the response.

**`user()`** — A MySQL/MariaDB built-in function that returns the current database user (e.g., `app_user@localhost`). Knowing the DB user tells the attacker what privileges they have.

**The 22 JOIN (SELECT null)** — This is column count enumeration. A UNION query must return the exact same number of columns as the original query. The attacker doesn't know how many columns `/api/v1/repos/search` returns, so they stuff 22 null columns to try to match whatever the real query returns. This is brute-force column alignment — if the real query returns 22 columns, this payload would succeed.

**Tab characters (`%09`) instead of spaces** — WAFs block `UNION SELECT` with spaces. Tabs are functionally identical to SQL parsers but invisible to many pattern-matching filters. This is `sqlmap`'s `--tamper=charunicodeescape` technique.

**`WHERE ('%'='`** — Closes the injected WHERE clause. The `%` always equals `%` (tautology), so the condition is always true, returning all rows.

### What a successful attack would have done

If this endpoint existed AND the code was vulnerable to SQL injection AND the database was MySQL/MariaDB:

1. The response would have included the database username in the results
2. The attacker would then escalate: dump table names, then data, then attempt `LOAD_FILE()` or `INTO OUTFILE` for remote file access
3. In the worst case: full read access to whatever database the application user could reach

**None of this happened.**

---

## 4. Why We Were Safe

### Layer 1: The endpoint doesn't exist
**HTTP 404 Not Found.** The server responded before any application code ran. There is no `/api/v1/repos/search` endpoint. The attack died here.

### Layer 2: We don't run Gitea
The bot's entire playbook assumed Gitea's database schema. Even if an endpoint with a similar name existed, it wouldn't have the column structure the bot expected.

### Layer 3: Request middleware
The middleware stack intercepts and logs all requests before they reach route handlers. Malformed or suspicious queries are logged and can be rate-limited or blocked. This request was logged (which is how we're seeing it).

### Layer 4: No MySQL in the patient data path
The patient data (PatientTimelineVision graphs) is stored as JSON files and in PostgreSQL. MySQL's `user()` function does not exist in PostgreSQL — the injection would have failed even if it reached a query parser, because it targets the wrong database engine.

### Layer 5: Parameterized queries
Any legitimate search endpoints use parameterized queries (prepared statements), not string interpolation. Even a perfectly crafted injection payload cannot break out of a parameterized query — the input is always treated as data, never as SQL.

---

## 5. What This Tells Us About Our Exposure Profile

The fact that this bot found us at all means our server IP is publicly reachable and responding to HTTP requests. That is expected and intentional for a web service. The bot learned nothing from this probe — a 404 reveals no information about our stack, database, or data model.

However, the existence of this scan in our logs is a useful signal: **our server is in automated scanning rotation**. This will happen again, from different IPs, with different payloads (path traversal, SSRF, XXE, authentication bypass, etc.). This is normal for any public-facing web server. The correct response is defense-in-depth, which we have.

---

## 6. No Action Required (But Optional Hardening)

**No immediate action required.** The attack failed completely.

If we want to reduce log noise and add a layer of proactive defense, three options:

| Option | Effort | Effect |
|---|---|---|
| Block the IP `93.123.109.205` at firewall/nginx | 2 minutes | Blocks this specific scanner (will rotate IPs anyway) |
| Add rate limiting on unknown routes | 1 hour | Slows automated scans that hit many endpoints quickly |
| Add a 400-level honeypot response + alert on `UNION` / `SELECT` in query params | 2 hours | Alerts us in real-time when SQL injection is attempted |

None of these are urgent. They are improvements to our detection posture, not responses to an active threat.

---

## 7. One-Line Summary for Investors or Partners

*"An automated scanner probed a non-existent endpoint with a SQL injection attack. It received a 404. No data, no credentials, and no application logic was exposed. This is routine internet background noise at the level of sophistication we expect and are designed to handle."*

---

*Report generated: 2026-03-28*  
*Classification: Internal / Non-confidential*
