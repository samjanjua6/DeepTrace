"""
Stage 1: Evidence Custody Lock & Integrity Verification — Celery Task & Async Processor
NIST SP 800-86 Compliant Cryptographic Lock Verification.
"""
from datetime import datetime, timezone
import time
from typing import Any

from app.config import get_settings
from app.core.celery_app import celery_app
from app.core.security import compute_sha256
from app.core.storage import storage
from prisma import Json
from app.db.client import db, set_org_context

settings = get_settings()


async def process_custody_lock(
    pipeline_run_id: str,
    pipeline_stage_id: str,
    org_id: str,
    investigation_id: str,
    document_id: str | None = None,
) -> dict[str, Any]:
    """
    Execute Stage 1: Cryptographic Custody Lock & Verification.
    Verifies that the stored document bytes match their acquisition SHA-256 fingerprint,
    ensures immutable storage clone exists, and logs the verification in the chain of custody.
    """
    start_time = time.perf_counter()

    async with set_org_context(org_id) as tx:
        # Mark stage as RUNNING
        await tx.pipelinestage.update(
            where={"id": pipeline_stage_id},
            data={
                "status": "RUNNING",
                "startedAt": datetime.now(timezone.utc),
            },
        )

        try:
            # Query target document(s)
            where_doc: dict[str, Any] = {"investigationId": investigation_id}
            if document_id:
                where_doc["id"] = document_id

            documents = await tx.document.find_many(where=where_doc)
            if not documents:
                raise ValueError(f"No documents found for investigation '{investigation_id}'")

            verified_documents = []

            for doc in documents:
                # 1. Fetch primary storage object
                file_bytes = storage.get_file(settings.s3_bucket_documents, doc.storagePath)
                if not file_bytes:
                    raise FileNotFoundError(
                        f"Document '{doc.id}' missing in storage path '{doc.storagePath}'"
                    )

                # 2. Re-compute SHA-256 and MD5
                current_sha256 = compute_sha256(file_bytes)
                if current_sha256.lower() != doc.sha256Hash.lower():
                    raise ValueError(
                        f"CRITICAL CUSTODY BREACH: Document '{doc.id}' SHA-256 hash mismatch! "
                        f"Expected {doc.sha256Hash}, computed {current_sha256}."
                    )

                # 3. Ensure immutable forensic clone exists
                clone_path = doc.storagePath.replace("/original/", "/immutable_clone/")
                if not storage.file_exists(settings.s3_bucket_artifacts, clone_path):
                    storage.upload_file(
                        settings.s3_bucket_artifacts,
                        clone_path,
                        file_bytes,
                        doc.mimeType,
                    )

                # 4. Acquire RFC 3161 Cryptographic Timestamp Seal (PECA 2016 / ETO 2002)
                tst_storage_path = None
                rfc3161_meta = None
                try:
                    from app.core import rfc3161_service
                    ts_info = rfc3161_service.request_timestamp_token(current_sha256)
                    tst_storage_path = f"custody_seals/{investigation_id}/{doc.id}_rfc3161.tst"
                    storage.upload_file(
                        settings.s3_bucket_artifacts,
                        tst_storage_path,
                        ts_info["token_der"],
                        "application/vnd.etsi.timestamp-token",
                    )
                    rfc3161_meta = {
                        "status": ts_info["status"],
                        "tsa_provider": ts_info["tsa_provider"],
                        "is_pakistan_accredited": ts_info["is_pakistan_accredited"],
                        "gen_time": ts_info["gen_time"],
                        "serial_number": ts_info["serial_number"],
                        "policy_oid": ts_info["policy_oid"],
                        "digest_algorithm": ts_info["digest_algorithm"],
                        "message_imprint": ts_info["message_imprint"],
                        "token_storage_path": tst_storage_path,
                        "token_b64": ts_info["token_b64"],
                        "verified": ts_info["verified"],
                        "legal_framework": ts_info["legal_framework"],
                        "is_offline_local_seal": ts_info.get("is_offline_local_seal", False),
                    }
                except Exception as tsa_err:
                    rfc3161_meta = {
                        "status": "UNAVAILABLE",
                        "error": str(tsa_err),
                    }

                # 5. Append Verification CustodyEvent with RFC 3161 Seal
                custody_desc = (
                    f"Cryptographic integrity verified and RFC 3161 Timestamp Seal registered from '{rfc3161_meta.get('tsa_provider', 'Local TSA')}' (PECA 2016 §33/§34)."
                    if rfc3161_meta and rfc3161_meta.get("status") == "SEALED"
                    else "Cryptographic integrity verified prior to forensic pipeline execution."
                )
                await tx.custodyevent.create(
                    data={
                        "investigation": {"connect": {"id": investigation_id}},
                        "eventType": "CUSTODY_SEAL_RFC3161" if rfc3161_meta and rfc3161_meta.get("status") == "SEALED" else "VERIFICATION",
                        "sha256Hash": current_sha256,
                        "description": custody_desc,
                        "actorType": "system",
                        "actorId": "deeptrace-rfc3161-tsa",
                        "metadata": Json({"rfc3161": rfc3161_meta}) if rfc3161_meta else None,
                    }
                )

                verified_documents.append({
                    "document_id": doc.id,
                    "sha256_hash": current_sha256,
                    "size_bytes": len(file_bytes),
                    "custody_status": "LOCKED_AND_VERIFIED",
                    "rfc3161_seal": rfc3161_meta,
                })

            duration_ms = int((time.perf_counter() - start_time) * 1000)
            output_payload = {
                "verified_documents": verified_documents,
                "total_documents": len(verified_documents),
                "duration_ms": duration_ms,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            await tx.pipelinestage.update(
                where={"id": pipeline_stage_id},
                data={
                    "status": "COMPLETED",
                    "durationMs": duration_ms,
                    "completedAt": datetime.now(timezone.utc),
                    "outputPayload": Json(output_payload),
                },
            )

            return output_payload

        except Exception as exc:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            await tx.pipelinestage.update(
                where={"id": pipeline_stage_id},
                data={
                    "status": "FAILED",
                    "durationMs": duration_ms,
                    "completedAt": datetime.now(timezone.utc),
                    "errorMessage": str(exc),
                    "errorStack": exc.__class__.__name__,
                },
            )
            raise


@celery_app.task(
    name="app.features.pipeline.tasks.stage_1_custody",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def run(
    self,
    pipeline_run_id: str,
    pipeline_stage_id: str,
    org_id: str,
    investigation_id: str,
    document_id: str | None = None,
) -> dict:
    """Celery task entry point for Stage 1."""
    import asyncio
    return asyncio.run(
        process_custody_lock(
            pipeline_run_id, pipeline_stage_id, org_id, investigation_id, document_id
        )
    )
