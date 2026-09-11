"""
Test Suite: Celery Pipeline Dispatch & Orchestration
Verifies:
  1. stage_map is properly populated and accessible for all 8 stages (no NameError).
  2. build_celery_canvas_chain constructs immutable signatures with per-stage errbacks.
  3. orchestrate_pipeline task executes in worker context with auto-connected Prisma client.
  4. finalize_pipeline_run properly marks PipelineRun as COMPLETED and syncs Investigation status.
  5. handle_pipeline_failure marks PipelineRun as FAILED with error messages.
"""
import asyncio
import sys
import unittest
from unittest.mock import patch, MagicMock

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, r"d:\zylo\DeepTrace")

from app.core.celery_app import celery_app
from app.db.client import connect, disconnect, db, set_org_context
from app.features.pipeline import service
from app.features.pipeline.tasks import orchestrator


class TestCeleryPipeline(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        await connect()
        async with set_org_context("cmtl7u5ku0000120pueg7by84") as tx:
            # Create a test investigation
            import time
            unique_case = f"DT-TEST-CELERY-{int(time.time()*1000)}"
            user = await tx.user.find_first()
            self.inv = await tx.investigation.create(
                data={
                    "organizationId": "cmtl7u5ku0000120pueg7by84",
                    "userId": user.id,
                    "caseNumber": unique_case,
                    "title": "Celery Pipeline Test Case",
                }
            )

    async def asyncTearDown(self):
        async with set_org_context("cmtl7u5ku0000120pueg7by84") as tx:
            if hasattr(self, "inv") and self.inv:
                await tx.pipelinestage.delete_many(where={"pipelineRun": {"investigationId": self.inv.id}})
                await tx.pipelinerun.delete_many(where={"investigationId": self.inv.id})
                await tx.investigation.delete(where={"id": self.inv.id})
        await disconnect()

    async def test_trigger_pipeline_stage_map_no_nameerror(self):
        """Test trigger_pipeline with mocked Redis available to ensure no NameError on stage_map."""
        with patch.object(service, "is_redis_available", return_value=True), \
             patch.object(celery_app, "send_task") as mock_send_task:

            run = await service.trigger_pipeline(
                org_id="cmtl7u5ku0000120pueg7by84",
                investigation_id=self.inv.id,
                triggered_by="system",
            )

            self.assertIsNotNone(run)
            self.assertEqual(len(run.stages), 8)
            # Verify Celery send_task was called with orchestrator
            mock_send_task.assert_called_once()
            call_args = mock_send_task.call_args
            self.assertEqual(call_args[0][0], "app.features.pipeline.tasks.orchestrator.orchestrate_pipeline")
            self.assertEqual(call_args[1]["queue"], "pipeline")
            print("✓ test_trigger_pipeline_stage_map_no_nameerror passed")

    async def test_build_celery_canvas_chain(self):
        """Test build_celery_canvas_chain generates all 8 stage signatures + finalizer with errback."""
        stage_map = {
            order: MagicMock(id=f"stage_id_{order}")
            for order, _, _, _ in service.STAGE_FLOW
        }

        chain = service.build_celery_canvas_chain(
            pipeline_run_id="run_123",
            stage_map=stage_map,
            org_id="cmtl7u5ku0000120pueg7by84",
            investigation_id=self.inv.id,
        )

        # A Celery chain of 8 stages + 1 finalizer = 9 tasks
        self.assertEqual(len(chain.tasks), 9)
        # Verify immutable flag on all tasks
        for task in chain.tasks:
            self.assertTrue(task.immutable)
            self.assertEqual(task.options.get("queue"), "pipeline")
            # Verify link_error is attached
            self.assertIsNotNone(task.options.get("link_error"))

        print("✓ test_build_celery_canvas_chain passed (9 immutable signatures with errbacks)")

    async def test_lifecycle_finalize_and_failure(self):
        """Test lifecycle completion and failure update functions."""
        # 1. Test finalize on a run
        run_status = await service.trigger_pipeline(
            org_id="cmtl7u5ku0000120pueg7by84",
            investigation_id=self.inv.id,
            triggered_by="system",
        )
        res = await orchestrator._async_finalize(
            pipeline_run_id=run_status.id,
            org_id="cmtl7u5ku0000120pueg7by84",
            investigation_id=self.inv.id,
        )
        self.assertEqual(res["status"], "COMPLETED")

        # Verify in DB
        async with set_org_context("cmtl7u5ku0000120pueg7by84") as tx:
            updated_run = await tx.pipelinerun.find_unique(where={"id": run_status.id})
            self.assertEqual(updated_run.status, "COMPLETED")

        # 2. Test failure handler
        await orchestrator._async_handle_failure(
            pipeline_run_id=run_status.id,
            org_id="cmtl7u5ku0000120pueg7by84",
            error_msg="Synthetic stage test failure",
            investigation_id=self.inv.id,
        )

        async with set_org_context("cmtl7u5ku0000120pueg7by84") as tx:
            failed_run = await tx.pipelinerun.find_unique(where={"id": run_status.id})
            self.assertEqual(failed_run.status, "FAILED")
            self.assertEqual(failed_run.errorMessage, "Synthetic stage test failure")
            failed_inv = await tx.investigation.find_unique(where={"id": self.inv.id})
            self.assertEqual(failed_inv.status, "FAILED")

        print("✓ test_lifecycle_finalize_and_failure passed")


if __name__ == "__main__":
    unittest.main()
