"""
Stage 8: Forensic Dossier Generation — Celery Task & Async Processor
NIST SP 800-86 Compliant Final Dossier Compilation.
"""
from datetime import datetime, timezone
import time
from typing import Any

from app.core.celery_app import celery_app
from prisma import Json
from app.db.client import db, set_org_context


async def process_report_generation(
    pipeline_run_id: str,
    pipeline_stage_id: str,
    org_id: str,
    investigation_id: str,
    document_id: str | None = None,
) -> dict[str, Any]:
    """
    Execute Stage 8: Forensic Dossier Generation.
    Compiles final summary dossier and marks pipeline completion.
    """
    start_time = time.perf_counter()

    async with set_org_context(org_id) as tx:
        await tx.pipelinestage.update(
            where={"id": pipeline_stage_id},
            data={"status": "RUNNING", "startedAt": datetime.now(timezone.utc)},
        )

        try:
            assessment = await tx.riskassessment.find_unique(
                where={"investigationId": investigation_id}
            )

            # Generate and archive court-admissible PDF dossier
            from app.features.reports.service import generate_report
            report_resp = await generate_report(tx, investigation_id)

            dossier_summary = {
                "investigation_id": investigation_id,
                "overall_score": assessment.overallScore if assessment else 0,
                "risk_tier": assessment.riskTier if assessment else "LOW",
                "action_directive": assessment.actionDirective if assessment else "STRAIGHT_THROUGH_APPROVAL",
                "compiled_at": datetime.now(timezone.utc).isoformat(),
                "status": "DOSSIER_READY",
                "download_url": report_resp.download_url,
                "sha256_hash": report_resp.sha256_hash,
                "file_size_bytes": report_resp.file_size_bytes,
            }

            duration_ms = int((time.perf_counter() - start_time) * 1000)

            await tx.pipelinestage.update(
                where={"id": pipeline_stage_id},
                data={
                    "status": "COMPLETED",
                    "durationMs": duration_ms,
                    "completedAt": datetime.now(timezone.utc),
                    "outputPayload": Json(dossier_summary),
                },
            )
            return dossier_summary

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
    name="app.features.pipeline.tasks.stage_8_report",
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
    """Celery task entry point for Stage 8."""
    import asyncio
    return asyncio.run(
        process_report_generation(
            pipeline_run_id, pipeline_stage_id, org_id, investigation_id, document_id
        )
    )
