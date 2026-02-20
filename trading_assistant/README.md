# Trading Assistant Client

Job runner for FMP_TRADING_CONTRACT. Receives result, relays via .EmailService.

## Cron

```bash
# Daily digest (example: 6 PM UTC)
0 18 * * * cd /path/to/PortalVision && ./.BeatingHeart/bin/python 2ndOpinionMD-MVP/trading_assistant/run.py
```

Or use systemd timer, launchd, etc. Discrete runs. Each run is a receipt.

## Env

- `TRADING_DIGEST_TO` — comma-separated emails for digest (default: nate@2ndopinionmd.ai,dylan@2ndopinionmd.ai)
- `KILL_SWITCH=true` — disables suggestions (report-only)
- `MAIL_*` — from 2ndOpinionMD-MVP/.env for .EmailService
