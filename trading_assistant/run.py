#!/usr/bin/env python3
"""
Trading Assistant Client — Job entry point.

Called by cron. Receives updates from FMP_TRADING_CONTRACT, relays via .EmailService.
Uses PortalVision's email_service (love.heart). No execution. Suggestions only.
"""
import asyncio
import os
import sys
from pathlib import Path

# Ensure PortalVision root is on path (for email_service + FullMetalPacket)
PORTAL_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PORTAL_ROOT))
os.chdir(PORTAL_ROOT)

from dotenv import load_dotenv
load_dotenv(PORTAL_ROOT / ".env")
load_dotenv(PORTAL_ROOT / "2ndOpinionMD-MVP" / ".env")

# FMP tool
FMP_BASE = PORTAL_ROOT / "FullMetalPacket" / "FMP_TRADING_CONTRACT"


def _run_fmp() -> dict:
    """Import and run FMP_TRADING_CONTRACT."""
    sys.path.insert(0, str(PORTAL_ROOT))
    sys.path.insert(0, str(PORTAL_ROOT / "FullMetalPacket"))
    from FMP_TRADING_CONTRACT.run import run
    return run(base_dir=FMP_BASE)


async def _send_digest(body: str, to: list[str], subject: str) -> None:
    """Send via .EmailService (PortalVision)."""
    from email_service import EmailService
    service = EmailService()
    await service.send(to=to, subject=subject, body=body)


def main() -> int:
    result = _run_fmp()
    digest = result.get("digest_body", "No digest.")
    subject = f"Trading Assistant Digest — {result.get('timestamp', '')[:10]}"
    to = os.getenv("TRADING_DIGEST_TO", "nate@2ndopinionmd.ai,dylan@2ndopinionmd.ai").split(",")
    to = [e.strip() for e in to if e.strip()]
    if not to:
        to = ["nate@2ndopinionmd.ai", "dylan@2ndopinionmd.ai"]
    asyncio.run(_send_digest(digest, to, subject))
    print(digest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
