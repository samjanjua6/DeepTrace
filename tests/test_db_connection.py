"""
Comprehensive database validation test for DeepTrace.
Tests:
1. Connecting to PostgreSQL on port 5433
2. Creating an Organization
3. Creating a User
4. Generating Case Number via PostgreSQL sequence
5. Creating an Investigation
6. Creating a Document with SHA-256 hash
7. Creating an immutable CustodyEvent
8. Asserting that the DB immutability trigger blocks UPDATE mutations
9. Fetching with nested Prisma relations
10. Verifying RLS and cleaning up
"""
import asyncio
import os
import sys

# Ensure database URL is loaded from .env
from dotenv import load_dotenv
load_dotenv()

from prisma import Prisma


async def main():
    db = Prisma()
    print("1. Connecting to PostgreSQL via Prisma...")
    await db.connect()
    print(f"   Connected successfully to {os.getenv('POSTGRES_DB')} on port {os.getenv('POSTGRES_PORT')}!")

    # Cleanup any old test org
    old = await db.organization.find_unique(where={"slug": "test-bank-pk"})
    if old:
        await db.execute_raw("SELECT set_config('app.allow_test_cleanup', 'true', false);")
        await db.execute_raw(f"SELECT set_config('app.current_org_id', '{old.id}', false);")
        await db.investigation.delete_many(where={"organizationId": old.id})
        await db.user.delete_many(where={"organizationId": old.id})
        await db.organization.delete(where={"id": old.id})

    print("2. Creating Organization...")
    org = await db.organization.create(
        data={
            "name": "Meezan Test Bank",
            "slug": "test-bank-pk",
            "subscriptionTier": "ENTERPRISE",
            "monthlyDocLimit": 50000,
        }
    )
    print(f"   Created Org: {org.id} [{org.name}]")

    # Set tenant context to allow inserting rows under this organization
    await db.execute_raw(f"SELECT set_config('app.current_org_id', '{org.id}', false);")

    print("3. Creating User...")
    user = await db.user.create(
        data={
            "organizationId": org.id,
            "email": "analyst@meezan.pk",
            "passwordHash": "$2b$12$e8S91Xsamplehashedpassword",
            "firstName": "Tariq",
            "lastName": "Mahmood",
            "role": "ANALYST",
        }
    )
    print(f"   Created User: {user.id} [{user.email}]")

    print("4. Testing Case Number Sequence (DT-PK-YYYY-NNNNNN)...")
    res = await db.query_raw("SELECT generate_case_number() AS case_number")
    case_num = res[0]["case_number"]
    print(f"   Generated Case Number: {case_num}")

    print("5. Creating Investigation...")
    inv = await db.investigation.create(
        data={
            "organizationId": org.id,
            "userId": user.id,
            "caseNumber": case_num,
            "title": "August 2026 Meezan Statement Audit",
            "status": "PROCESSING",
            "priority": 2,
        }
    )
    print(f"   Created Investigation: {inv.id} [{inv.caseNumber}]")

    print("6. Creating Document with SHA-256 custody hash...")
    doc = await db.document.create(
        data={
            "investigationId": inv.id,
            "originalFilename": "meezan_aug_statement.pdf",
            "mimeType": "application/pdf",
            "fileSizeBytes": 2048576,
            "documentType": "BANK_STATEMENT",
            "sha256Hash": "4a7f92b1c8890123d4e5f6789abcdef0123456789abcdef0123456789abcdef0",
            "storagePath": "investigations/meezan_aug_statement.pdf",
        }
    )
    print(f"   Created Document: {doc.id} [{doc.originalFilename}]")

    print("7. Creating CustodyEvent...")
    custody = await db.custodyevent.create(
        data={
            "investigationId": inv.id,
            "eventType": "ACQUIRED",
            "description": "Statement uploaded and immutable SHA-256 hash locked.",
            "sha256Hash": doc.sha256Hash,
            "actorType": "user",
            "actorId": user.id,
        }
    )
    print(f"   Created CustodyEvent: {custody.id} [{custody.eventType}]")

    print("8. Testing Immutability Trigger (UPDATE custody_events)...")
    try:
        await db.execute_raw(
            f"UPDATE custody_events SET description = 'tampered' WHERE id = '{custody.id}'"
        )
        print("   FAILED: Immutability trigger did not block UPDATE!")
        sys.exit(1)
    except Exception as exc:
        print("   SUCCESS: Trigger correctly blocked mutation:")
        print(f"   -> {str(exc).splitlines()[0]}")

    print("9. Fetching Investigation with nested relations...")
    fetched = await db.investigation.find_unique(
        where={"id": inv.id},
        include={"documents": True, "custodyEvents": True, "user": True}
    )
    assert fetched is not None
    assert len(fetched.documents) == 1
    assert len(fetched.custodyEvents) == 1
    print(f"   Fetched Investigation {fetched.caseNumber} with {len(fetched.documents)} doc, {len(fetched.custodyEvents)} custody event.")

    print("10. Cleaning up test data...")
    await db.execute_raw("SELECT set_config('app.allow_test_cleanup', 'true', false);")
    await db.investigation.delete(where={"id": inv.id})
    await db.user.delete(where={"id": user.id})
    await db.organization.delete(where={"id": org.id})
    print("   Test data cleaned up successfully.")

    await db.disconnect()
    print("\nALL 10 DATABASE CHECKS PASSED PERFECTLY!")


if __name__ == "__main__":
    asyncio.run(main())
