"""
DeepTrace — Celery Application Instance
Import `celery_app` in task files to register tasks.
"""

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "deeptrace",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.features.pipeline.tasks.stage_1_custody",
        "app.features.pipeline.tasks.stage_2_pdf_structure",
        "app.features.pipeline.tasks.stage_3_font_glyph",
        "app.features.pipeline.tasks.stage_4_vision_ela",
        "app.features.pipeline.tasks.stage_5_ocr",
        "app.features.pipeline.tasks.stage_6_financial",
        "app.features.pipeline.tasks.stage_7_fusion",
        "app.features.pipeline.tasks.stage_8_report",
        "app.features.pipeline.tasks.orchestrator",
        "app.features.webhooks.tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=False,
    broker_connection_timeout=1.0,
    broker_connection_max_retries=1,
    # Route forensic pipeline tasks to a dedicated queue for prioritization
    task_routes={
        "app.features.pipeline.tasks.*": {"queue": "pipeline"},
        "app.features.webhooks.tasks.*": {"queue": "webhooks"},
    },
    task_annotations={
        "app.features.webhooks.tasks.*": {"ignore_result": True},
    },
)
