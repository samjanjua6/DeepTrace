"""
DeepTrace — Development Database Seeder
Creates demo organizations, users, and investigations for testing via Swagger UI.

Usage:
    python scripts/seed_dev.py
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv(".env")
sys.path.insert(0, ".")

from prisma import Prisma
from app.core.security import hash_password


async def seed():
    db = Prisma()
    await db.connect()
    print("Connected to PostgreSQL for seeding...")

    # Enable test cleanup in case re-seeding
    await db.execute_raw("SELECT set_config('app.allow_test_cleanup', 'true', false);")

    # 1. Organization: Meezan Bank Ltd
    org_slug = "meezan-bank"
    org = await db.organization.find_unique(where={"slug": org_slug})
    if not org:
        org = await db.organization.create(
            data={
                "name": "Meezan Bank Ltd",
                "slug": org_slug,
                "subscriptionTier": "ENTERPRISE",
                "monthlyDocLimit": 50000,
                "domain": "meezanbank.com",
            }
        )
        print(f"Created Organization: {org.name} (ID: {org.id})")
    else:
        print(f"Organization exists: {org.name} (ID: {org.id})")

    # Set tenant context to allow creating users for this org under RLS
    await db.execute_raw(f"SELECT set_config('app.current_org_id', '{org.id}', false);")

    # 2. Admin User
    admin_email = "admin@deeptrace.test"
    admin = await db.user.find_unique(where={"email": admin_email})
    if not admin:
        admin = await db.user.create(
            data={
                "organizationId": org.id,
                "email": admin_email,
                "passwordHash": hash_password("Admin@12345"),
                "firstName": "Super",
                "lastName": "Admin",
                "role": "ADMIN",
            }
        )
        print(f"Created Admin: {admin.email} (Password: Admin@12345)")
    else:
        print(f"Admin exists: {admin.email}")

    # 3. Analyst User
    analyst_email = "analyst@meezan.pk"
    analyst = await db.user.find_unique(where={"email": analyst_email})
    if not analyst:
        analyst = await db.user.create(
            data={
                "organizationId": org.id,
                "email": analyst_email,
                "passwordHash": hash_password("Analyst@12345"),
                "firstName": "Tariq",
                "lastName": "Mahmood",
                "role": "ANALYST",
            }
        )
        print(f"Created Analyst: {analyst.email} (Password: Analyst@12345)")
    else:
        print(f"Analyst exists: {analyst.email}")

    # 4. Sample Investigation
    case_num = "DT-PK-2026-000001"
    inv = await db.investigation.find_unique(where={"caseNumber": case_num})
    if not inv:
        inv = await db.investigation.create(
            data={
                "organizationId": org.id,
                "userId": analyst.id,
                "caseNumber": case_num,
                "title": "August 2026 Meezan Account Statement Audit",
                "description": "High-risk statement audit with balance discrepancy and font anomaly.",
                "status": "PROCESSING",
                "priority": 2,
                "source": "WEB_UPLOAD",
                "clientReference": "LOAN-PK-88412",
            }
        )
        print(f"Created Sample Investigation: {inv.caseNumber}")
    else:
        print(f"Investigation exists: {inv.caseNumber}")

    await db.disconnect()
    print("\nDATABASE SEEDING COMPLETE!")
    print("\n--- Test Credentials for Swagger UI ---")
    print("Email:    analyst@meezan.pk")
    print("Password: Analyst@12345")
    print("---------------------------------------")


if __name__ == "__main__":
    asyncio.run(seed())
