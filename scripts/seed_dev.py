"""
DeepTrace — Development Database Seeder
Creates demo organizations, users, and investigations for testing via Swagger UI and Web UI.

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
    await db.execute_raw("SELECT set_config('app.is_auth', 'true', false);")

    # 1. Seed Banking Organizations
    banks = [
        {
            "name": "Meezan Bank Ltd",
            "slug": "meezan-bank",
            "subscriptionTier": "ENTERPRISE",
            "monthlyDocLimit": 50000,
            "domain": "meezanbank.com",
        },
        {
            "name": "Habib Bank Limited",
            "slug": "hbl",
            "subscriptionTier": "ENTERPRISE",
            "monthlyDocLimit": 50000,
            "domain": "hbl.com",
        },
        {
            "name": "United Bank Limited",
            "slug": "ubl",
            "subscriptionTier": "ENTERPRISE",
            "monthlyDocLimit": 50000,
            "domain": "ubl.com.pk",
        },
        {
            "name": "Standard Chartered Bank Pakistan",
            "slug": "scb-pk",
            "subscriptionTier": "ENTERPRISE",
            "monthlyDocLimit": 50000,
            "domain": "sc.com/pk",
        },
        {
            "name": "State Bank of Pakistan",
            "slug": "sbp-regulator",
            "subscriptionTier": "ENTERPRISE",
            "monthlyDocLimit": 100000,
            "domain": "sbp.org.pk",
        },
    ]

    org_map = {}
    for b in banks:
        existing = await db.organization.find_unique(where={"slug": b["slug"]})
        if not existing:
            created = await db.organization.create(data=b)
            print(f"Created Organization: {created.name} (ID: {created.id})")
            org_map[b["slug"]] = created
        else:
            print(f"Organization exists: {existing.name} (ID: {existing.id})")
            org_map[b["slug"]] = existing

    meezan_org = org_map["meezan-bank"]

    # Set tenant context for Meezan to allow user creation under RLS
    await db.execute_raw(f"SELECT set_config('app.current_org_id', '{meezan_org.id}', false);")

    # 2. Platform Admin
    admin_email = "admin@deeptrace.test"
    admin = await db.user.find_unique(where={"email": admin_email})
    if not admin:
        admin = await db.user.create(
            data={
                "organizationId": meezan_org.id,
                "email": admin_email,
                "passwordHash": hash_password("Admin@12345"),
                "firstName": "Platform",
                "lastName": "Administrator",
                "role": "ADMIN",
            }
        )
        print(f"Created Admin: {admin.email} (Password: Admin@12345)")
    else:
        print(f"Admin exists: {admin.email}")

    # 3. Standard Analyst (No MFA)
    analyst_email = "analyst@meezan.pk"
    analyst = await db.user.find_unique(where={"email": analyst_email})
    if not analyst:
        analyst = await db.user.create(
            data={
                "organizationId": meezan_org.id,
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

    # 4. MFA-Enforced Analyst (2FA Enabled)
    mfa_analyst_email = "analyst.mfa@meezan.pk"
    mfa_analyst = await db.user.find_unique(where={"email": mfa_analyst_email})
    if not mfa_analyst:
        mfa_analyst = await db.user.create(
            data={
                "organizationId": meezan_org.id,
                "email": mfa_analyst_email,
                "passwordHash": hash_password("Analyst@12345"),
                "firstName": "Zubair",
                "lastName": "Ahmed",
                "role": "ANALYST",
                "mfaEnabled": True,
                "mfaSecret": "JBSWY3DPEHPK3PXP",  # Standard test base32 secret
            }
        )
        print(f"Created MFA Analyst: {mfa_analyst.email} (Password: Analyst@12345, Secret: JBSWY3DPEHPK3PXP)")
    else:
        # Ensure MFA fields are set
        await db.user.update(
            where={"id": mfa_analyst.id},
            data={"mfaEnabled": True, "mfaSecret": "JBSWY3DPEHPK3PXP"},
        )
        print(f"MFA Analyst updated: {mfa_analyst.email}")

    # 5. Sample Investigation for Meezan Bank
    case_num = "DT-PK-2026-000001"
    inv = await db.investigation.find_unique(where={"caseNumber": case_num})
    if not inv:
        inv = await db.investigation.create(
            data={
                "organizationId": meezan_org.id,
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
    print("\n--- Test Credentials for UI / API ---")
    print("1. Standard Analyst: analyst@meezan.pk        / Analyst@12345")
    print("2. 2FA Analyst:      analyst.mfa@meezan.pk    / Analyst@12345 (Secret: JBSWY3DPEHPK3PXP)")
    print("3. Admin:            admin@deeptrace.test     / Admin@12345")
    print("-------------------------------------")


if __name__ == "__main__":
    asyncio.run(seed())
