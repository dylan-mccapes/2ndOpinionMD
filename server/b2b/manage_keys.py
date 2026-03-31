#!/usr/bin/env python3
"""
CLI for B2B API key management.

Usage (from 2ndOpinionMD-MVP, venv active):

    # Create a tenant
    python -m server.b2b.manage_keys create-tenant \
        --name "Acme Health" --email "api@acme.health"

    # Create an API key for that tenant
    python -m server.b2b.manage_keys create-key \
        --tenant-id <uuid> --scopes mkg:read,mkg:evidence --name "Acme prod"

    # List keys for a tenant
    python -m server.b2b.manage_keys list-keys --tenant-id <uuid>

    # Revoke a key
    python -m server.b2b.manage_keys revoke-key --key-id <uuid>

    # List all tenants
    python -m server.b2b.manage_keys list-tenants
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Ensure project is importable
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env", override=False)

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from server.b2b.api_keys import (
    generate_raw_key, hash_key, key_prefix, key_last4,
    validate_scopes, ALL_SCOPES,
)
from server.b2b.key_store import create_key_record, create_tenant, revoke_key


def _get_db_url() -> str:
    raw = os.getenv("DATABASE_URL") or os.getenv("SYNC_DATABASE_URL")
    if not raw:
        print("ERROR: Set DATABASE_URL or SYNC_DATABASE_URL", file=sys.stderr)
        sys.exit(1)
    if raw.startswith("postgresql://") and "+asyncpg" not in raw:
        raw = raw.replace("postgresql://", "postgresql+asyncpg://", 1)
    return raw


async def _session() -> AsyncSession:
    engine = create_async_engine(_get_db_url())
    maker = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    return maker()


async def cmd_create_tenant(args):
    async with await _session() as session:
        tid = await create_tenant(
            session, name=args.name, contact_email=args.email, plan=args.plan,
        )
    print(f"Tenant created:  {tid}")
    print(f"  name:          {args.name}")
    print(f"  email:         {args.email}")
    print(f"  plan:          {args.plan}")


async def cmd_list_tenants(args):
    async with await _session() as session:
        rows = (await session.execute(
            text("SELECT id, name, contact_email, plan, is_active, created_at FROM b2b.tenants ORDER BY created_at")
        )).mappings().all()
    if not rows:
        print("No tenants.")
        return
    for r in rows:
        active = "active" if r["is_active"] else "INACTIVE"
        print(f"  {r['id']}  {r['name']:<30s}  {r['plan']:<10s}  {active}  {r['contact_email']}")


async def cmd_create_key(args):
    scopes = validate_scopes(args.scopes.split(","))
    raw = generate_raw_key(env=args.env)

    async with await _session() as session:
        key_id = await create_key_record(
            session,
            tenant_id=args.tenant_id,
            key_hash_val=hash_key(raw),
            prefix=key_prefix(raw),
            last4=key_last4(raw),
            name=args.name,
            scopes=scopes,
            rate_limit_rpm=args.rpm,
            rate_limit_rpd=args.rpd,
        )

    print()
    print("=" * 70)
    print("  API KEY CREATED — COPY THIS NOW, IT WILL NOT BE SHOWN AGAIN")
    print("=" * 70)
    print(f"  Key:        {raw}")
    print(f"  Key ID:     {key_id}")
    print(f"  Tenant:     {args.tenant_id}")
    print(f"  Scopes:     {scopes}")
    print(f"  Rate limit: {args.rpm} rpm / {args.rpd} rpd")
    if args.name:
        print(f"  Label:      {args.name}")
    print("=" * 70)
    print()


async def cmd_list_keys(args):
    async with await _session() as session:
        rows = (await session.execute(
            text("""
                SELECT id, key_prefix, key_last4, name, scopes,
                       rate_limit_rpm, rate_limit_rpd, is_active,
                       created_at, last_used_at
                FROM b2b.api_keys
                WHERE tenant_id = :tid
                ORDER BY created_at
            """),
            {"tid": args.tenant_id},
        )).mappings().all()

    if not rows:
        print("No keys for this tenant.")
        return

    for r in rows:
        active = "active" if r["is_active"] else "REVOKED"
        used = str(r["last_used_at"])[:19] if r["last_used_at"] else "never"
        print(f"  {r['id']}  {r['key_prefix']}...{r['key_last4']}  "
              f"{active:<8s}  scopes={r['scopes']}  "
              f"rpm={r['rate_limit_rpm']}  last_used={used}  "
              f"name={r['name'] or '-'}")


async def cmd_revoke_key(args):
    async with await _session() as session:
        ok = await revoke_key(session, args.key_id)
    if ok:
        print(f"Key {args.key_id} revoked.")
    else:
        print(f"Key {args.key_id} not found.")


def main():
    parser = argparse.ArgumentParser(description="B2B API key management")
    sub = parser.add_subparsers(dest="command", required=True)

    # create-tenant
    ct = sub.add_parser("create-tenant")
    ct.add_argument("--name", required=True)
    ct.add_argument("--email", required=True)
    ct.add_argument("--plan", default="free", choices=["free", "starter", "pro", "enterprise"])

    # list-tenants
    sub.add_parser("list-tenants")

    # create-key
    ck = sub.add_parser("create-key")
    ck.add_argument("--tenant-id", required=True)
    ck.add_argument("--scopes", required=True, help=f"Comma-separated.  Valid: {','.join(sorted(ALL_SCOPES))}")
    ck.add_argument("--name", default=None, help="Human label for this key")
    ck.add_argument("--env", default="live", choices=["live", "test"])
    ck.add_argument("--rpm", type=int, default=60, help="Requests per minute")
    ck.add_argument("--rpd", type=int, default=10000, help="Requests per day")

    # list-keys
    lk = sub.add_parser("list-keys")
    lk.add_argument("--tenant-id", required=True)

    # revoke-key
    rk = sub.add_parser("revoke-key")
    rk.add_argument("--key-id", required=True)

    args = parser.parse_args()
    dispatch = {
        "create-tenant": cmd_create_tenant,
        "list-tenants": cmd_list_tenants,
        "create-key": cmd_create_key,
        "list-keys": cmd_list_keys,
        "revoke-key": cmd_revoke_key,
    }
    asyncio.run(dispatch[args.command](args))


if __name__ == "__main__":
    main()
