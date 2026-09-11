"""
Stage 4: Computer Vision Forgery Detection — Celery Task & Async Processor
NIST SP 800-86 Compliant Forensics. Combines three complementary detectors:

  1. TruFor (CVPR 2023) neural manipulation detection — primary when PyTorch available.
     Produces pixel-level anomaly map via Noiseprint++ noise residual fusion.
     Falls back to JPEG ELA when torch/weights unavailable.

  2. JPEG Error Level Analysis (ELA) — double-compression difference heatmap at Q=95.
     Gibbs suppression via Canny edge masking + morphological connected components.
     Acts as fallback / supplement to TruFor.

  3. Copy-Move Forgery Detection (CMFD) — ORB keypoint matching + BFMatcher Hamming
     distance + RANSAC homography. Detects pasted stamps, cloned rows, duplicate sigs.
     Requires no additional dependencies beyond core opencv-python.
"""
from datetime import datetime, timezone
import io
import time
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageEnhance
from prisma import Json

from app.config import get_settings
from app.core.celery_app import celery_app
from app.core.storage import storage
from app.db.client import db, set_org_context

settings = get_settings()


async def process_vision_ela(
    pipeline_run_id: str,
    pipeline_stage_id: str,
    org_id: str,
    investigation_id: str,
    document_id: str | None = None,
) -> dict[str, Any]:
    """
    Execute Stage 4: Computer Vision Error Level Analysis (ELA).
    Generates JPEG re-compression difference heatmaps at Q=95, detects localized compression
    noise spikes indicative of cut-and-paste tampering, and extracts bounding boxes.
    """
    start_time = time.perf_counter()

    async with set_org_context(org_id) as tx:
        await tx.pipelinestage.update(
            where={"id": pipeline_stage_id},
            data={"status": "RUNNING", "startedAt": datetime.now(timezone.utc)},
        )

        try:
            where_doc: dict[str, Any] = {"investigationId": investigation_id}
            if document_id:
                where_doc["id"] = document_id

            documents = await tx.document.find_many(
                where=where_doc,
                include={"pages": True},
            )
            if not documents:
                raise ValueError(f"No documents found for investigation '{investigation_id}'")

            stage_findings = []

            for doc in documents:
                for page in (doc.pages or []):
                    # Fetch rendered page image from storage
                    if not page.renderedImagePath:
                        continue
                    img_bytes = storage.get_file(settings.s3_bucket_documents, page.renderedImagePath)
                    if not img_bytes:
                        continue

                    try:
                        orig_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                        width, height = orig_img.size

                        # 1. Resave at quality Q=95 in memory
                        buf = io.BytesIO()
                        orig_img.save(buf, format="JPEG", quality=95)
                        buf.seek(0)
                        resaved_img = Image.open(buf)

                        # 2. Compute absolute difference and amplify
                        diff = ImageChops.difference(orig_img, resaved_img)

                        # Scale differences by 15x to bring out low-amplitude compression artifacts
                        extrema = diff.getextrema()
                        max_diff = max([ex[1] for ex in extrema])
                        scale = 255.0 / max(1, max_diff) if max_diff > 0 else 1.0
                        scale = min(15.0, scale)

                        diff_amplified = ImageEnhance.Brightness(diff).enhance(scale)

                        # Save ELA Heatmap PNG to storage artifacts
                        ela_buf = io.BytesIO()
                        diff_amplified.save(ela_buf, format="PNG")
                        ela_bytes = ela_buf.getvalue()

                        artifact_storage_path = (
                            f"artifacts/{investigation_id}/{doc.id}/ela/page_{page.pageNumber}_ela.png"
                        )
                        storage.upload_file(
                            settings.s3_bucket_artifacts,
                            artifact_storage_path,
                            ela_bytes,
                            "image/png",
                        )

                        # 3. Suppress Gibbs Phenomenon along sharp vector/text edges & table grid lines
                        gray_orig = cv2.cvtColor(np.array(orig_img), cv2.COLOR_RGB2GRAY)
                        edges = cv2.Canny(gray_orig, 100, 200)
                        dilated_edges = cv2.dilate(edges, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)), iterations=1)

                        # Morphological table grid line suppression:
                        # Suppresses horizontal/vertical ruling lines which otherwise connect disparate anomalies
                        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 1))
                        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 30))
                        h_lines = cv2.morphologyEx(dilated_edges, cv2.MORPH_OPEN, h_kernel)
                        v_lines = cv2.morphologyEx(dilated_edges, cv2.MORPH_OPEN, v_kernel)
                        grid_lines = cv2.dilate(cv2.bitwise_or(h_lines, v_lines), cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)), iterations=1)
                        non_edge_mask = (dilated_edges == 0) & (grid_lines == 0)

                        # 4. Analyze Error Variance on non-edge ambient surface (for ELA fallback)
                        diff_gray = np.array(diff.convert("L"), dtype=np.float32)
                        non_edge_diff = diff_gray[non_edge_mask]
                        mean_err = float(np.mean(non_edge_diff)) if len(non_edge_diff) > 0 else float(np.mean(diff_gray))
                        std_err = float(np.std(non_edge_diff)) if len(non_edge_diff) > 0 else float(np.std(diff_gray))

                        # Adaptive threshold: ambient mean + 3.5 sigma, at least 4.0
                        threshold = max(4.0, mean_err + (3.5 * std_err))

                        # ── TruFor Neural Manipulation Detection (primary) ────────────
                        # When PyTorch + weights or ONNX are available, TruFor's anomaly_map replaces
                        # the JPEG difference hotspot mask. Falls back to ELA if unavailable.
                        trufor_result = None
                        trufor_artifact_path = None
                        ela_evidence_method = "ela"
                        ela_severity_override = None
                        anomaly_bytes = b""
                        try:
                            from app.features.pipeline.tasks.trufor_engine import TruForEngine
                            trufor_engine = TruForEngine.get_instance()
                            if trufor_engine.is_available():
                                orig_rgb_arr = np.array(orig_img)
                                trufor_result = trufor_engine.predict(orig_rgb_arr)
                                ela_evidence_method = trufor_result.method

                                # Save TruFor anomaly map as additional artifact
                                if trufor_result.anomaly_map is not None and trufor_result.anomaly_map.max() > 0:
                                    anomaly_vis = (trufor_result.anomaly_map * 255).clip(0, 255).astype(np.uint8)
                                    anomaly_pil = Image.fromarray(anomaly_vis, mode="L")
                                    anomaly_buf = io.BytesIO()
                                    anomaly_pil.save(anomaly_buf, format="PNG")
                                    anomaly_bytes = anomaly_buf.getvalue()
                                    trufor_artifact_path = (
                                        f"artifacts/{investigation_id}/{doc.id}/trufor/page_{page.pageNumber}_anomaly.png"
                                    )
                                    storage.upload_file(
                                        settings.s3_bucket_artifacts,
                                        trufor_artifact_path,
                                        anomaly_bytes,
                                        "image/png",
                                    )

                                # Low global score → strong evidence of manipulation
                                if trufor_result.score < 0.2:
                                    ela_severity_override = "CRITICAL"
                        except Exception as trufor_err:
                            import logging as _logging
                            _logging.getLogger(__name__).debug("TruFor unavailable: %s", trufor_err)

                        # Build hotspot mask from TruFor anomaly map (primary) or ELA (fallback)
                        is_trufor_active = False
                        if trufor_result is not None and trufor_result.anomaly_map is not None and trufor_result.detection == "manipulated":
                            # Resize anomaly map to match image dimensions if needed
                            am = trufor_result.anomaly_map
                            if am.shape != (height, width):
                                am = cv2.resize(am, (width, height), interpolation=cv2.INTER_LINEAR)
                            hotspots = (am > 0.45) & non_edge_mask
                            is_trufor_active = True
                        else:
                            # Fallback: classic JPEG ELA hotspot mask
                            hotspots = (diff_gray > threshold) & non_edge_mask

                        # 5. Morphological filtering & Connected Components via cv2.findContours
                        hotspot_mask = (hotspots.astype(np.uint8)) * 255

                        # Suppress lingering thin horizontal/vertical line artifacts (table borders & ruling lines)
                        vert_thick = cv2.dilate(cv2.erode(hotspot_mask, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 5))), cv2.getStructuringElement(cv2.MORPH_RECT, (1, 5)))
                        horiz_thick = cv2.dilate(cv2.erode(hotspot_mask, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 1))), cv2.getStructuringElement(cv2.MORPH_RECT, (5, 1)))
                        thick_blocks = cv2.bitwise_or(vert_thick, horiz_thick)
                        thin_elements = cv2.bitwise_and(hotspot_mask, cv2.bitwise_not(thick_blocks))

                        h_stripes = cv2.morphologyEx(thin_elements, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (35, 1)))
                        v_stripes = cv2.morphologyEx(thin_elements, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 35)))
                        hotspot_mask = cv2.bitwise_and(hotspot_mask, cv2.bitwise_not(cv2.bitwise_or(h_stripes, v_stripes)))

                        kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
                        opened = cv2.morphologyEx(hotspot_mask, cv2.MORPH_OPEN, kernel_open)
                        kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
                        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel_close)

                        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                        # Filter candidate components
                        candidate_components = []
                        for c in contours:
                            carea = cv2.contourArea(c)
                            cx, cy, cw, ch = cv2.boundingRect(c)
                            if cw <= 0 or ch <= 0:
                                continue
                            density = carea / (cw * ch)
                            aspect_ratio = cw / ch if ch > 0 else 0

                            # Ensure component is dense, localized, and not whole-page runaway noise
                            if (
                                carea >= 40
                                and density >= 0.12
                                and 0.08 <= aspect_ratio <= 12.0
                                and cw < (0.40 * width)
                                and ch < (0.35 * height)
                                and (cw * ch) < (0.12 * width * height)
                            ):
                                candidate_components.append((cx, cy, cw, ch, int(carea)))

                        # Horizontal line-aware baseline agglomeration:
                        # Merge adjacent components on the same text row or in tight 2D proximity
                        merged_boxes = []
                        for comp in candidate_components:
                            cx, cy, cw, ch, carea = comp
                            merged = False
                            for idx, (bx, by, bw, bh, barea) in enumerate(merged_boxes):
                                b_cy = by + bh / 2.0
                                c_cy = cy + ch / 2.0
                                y_overlap = max(0, min(by + bh, cy + ch) - max(by, cy))
                                min_h = min(bh, ch)
                                same_row = (abs(b_cy - c_cy) <= 10) or (min_h > 0 and (y_overlap / min_h) >= 0.50)
                                x_gap = max(0, max(bx, cx) - min(bx + bw, cx + cw))
                                y_gap = max(0, max(by, cy) - min(by + bh, cy + ch))

                                if (x_gap <= 6 and y_gap <= 6) or (same_row and x_gap <= 20):
                                    nx = min(cx, bx)
                                    ny = min(cy, by)
                                    nw = max(cx + cw, bx + bw) - nx
                                    nh = max(cy + ch, by + bh) - ny
                                    if nw < (0.45 * width) and nh < (0.25 * height):
                                        merged_boxes[idx] = (nx, ny, nw, nh, barea + carea)
                                        merged = True
                                        break
                            if not merged:
                                merged_boxes.append((cx, cy, cw, ch, carea))

                        # OCR Token Snapping:
                        # Snap bounding boxes to exact overlapping OCR word boundaries if present
                        scale_to_pts = (page.widthPts / page.widthPx) if page.widthPx else (72.0 / 150.0)
                        pts_to_px = (1.0 / scale_to_pts) if scale_to_pts > 0 else (150.0 / 72.0)
                        ocr_words = []
                        if page.ocrDataJson and isinstance(page.ocrDataJson, dict):
                            raw_w = page.ocrDataJson.get("words", [])
                            if isinstance(raw_w, list):
                                ocr_words = raw_w

                        snapped_boxes = []
                        for (bx, by, bw, bh, barea) in merged_boxes:
                            intersecting_words = []
                            for w_entry in ocr_words:
                                if len(w_entry) >= 4:
                                    wx0 = float(w_entry[0]) * pts_to_px
                                    wy0 = float(w_entry[1]) * pts_to_px
                                    wx1 = float(w_entry[2]) * pts_to_px
                                    wy1 = float(w_entry[3]) * pts_to_px
                                    ix0 = max(bx, wx0)
                                    iy0 = max(by, wy0)
                                    ix1 = min(bx + bw, wx1)
                                    iy1 = min(by + bh, wy1)
                                    if ix1 > ix0 and iy1 > iy0:
                                        inter_a = (ix1 - ix0) * (iy1 - iy0)
                                        w_a = (wx1 - wx0) * (wy1 - wy0)
                                        if w_a > 0 and (inter_a / w_a) >= 0.25:
                                            intersecting_words.append((wx0, wy0, wx1, wy1))

                            if intersecting_words:
                                min_wx = min(w[0] for w in intersecting_words)
                                min_wy = min(w[1] for w in intersecting_words)
                                max_wx = max(w[2] for w in intersecting_words)
                                max_wy = max(w[3] for w in intersecting_words)
                                snapped_x = max(0, int(min_wx - 3))
                                snapped_y = max(0, int(min_wy - 3))
                                snapped_w = min(width - snapped_x, int(max_wx - min_wx + 6))
                                snapped_h = min(height - snapped_y, int(max_wy - min_wy + 6))
                                snapped_boxes.append((snapped_x, snapped_y, snapped_w, snapped_h, barea))
                            else:
                                snapped_boxes.append((bx, by, bw, bh, barea))

                        for b_idx, (x_min, y_min, bbox_w, bbox_h, patch_pixel_count) in enumerate(snapped_boxes[:5]):
                            patch_slice = diff_gray[y_min : y_min + bbox_h, x_min : x_min + bbox_w]
                            patch_peak = float(np.max(patch_slice)) if patch_slice.size > 0 else float(threshold)

                            if is_trufor_active:
                                rule_id = "RULE_CV_TRUFOR_MANIPULATION"
                                finding_severity = ela_severity_override or "HIGH"
                                finding_points = 30 if finding_severity == "CRITICAL" else 25
                                finding_title = f"Neural Manipulation Detection: Localized Tampering on Page {page.pageNumber}"
                                finding_desc = (
                                    f"TruFor neural model ({trufor_result.method}) detected localized visual tampering on Page {page.pageNumber} "
                                    f"(authenticity score: {trufor_result.score:.3f}, detection: {trufor_result.detection}). "
                                    f"Multi-band noise residual and RGB fusion isolated an anomalous region with peak residual {patch_peak:.1f} "
                                    f"(ambient baseline: {mean_err:.1f} ± {std_err:.1f})."
                                )
                                finding_label = "Neural Manipulation Anomaly"
                                finding_color = "#dc2626" if finding_severity == "CRITICAL" else "#ea580c"
                                finding_conf = 0.92
                            else:
                                rule_id = "RULE_CV_ELA_ANOMALY"
                                finding_severity = "HIGH"
                                finding_points = 20
                                finding_title = f"ELA Compression Discontinuity (Page {page.pageNumber})"
                                finding_desc = (
                                    f"Error Level Analysis identified an anomalous compression noise cluster on Page {page.pageNumber} "
                                    f"(local patch peak: {patch_peak:.1f}, ambient noise: {mean_err:.1f} ± {std_err:.1f}). "
                                    "This indicates visual elements (stamps, numbers, or logo) spliced from an external source "
                                    "with a different JPEG compression history."
                                )
                                finding_label = "ELA Compression Anomaly"
                                finding_color = "#f97316"
                                finding_conf = 0.85

                            finding = await tx.evidenceitem.create(
                                data={
                                    "document": {"connect": {"id": doc.id}},
                                    "pipelineStage": {"connect": {"id": pipeline_stage_id}},
                                    "category": "IMAGE_ELA_MANIPULATION",
                                    "severity": finding_severity,
                                    "ruleId": rule_id,
                                    "riskPoints": finding_points,
                                    "title": finding_title,
                                    "description": finding_desc,
                                    "isDeterministic": False,
                                    "confidence": finding_conf,
                                    "pageNumber": page.pageNumber,
                                    "expectedValue": f"Uniform ambient error noise (mean ~ {mean_err:.1f})",
                                    "actualValue": f"Local noise hotspot (patch peak ~ {patch_peak:.1f})",
                                    "discrepancy": "Anomalous compression / noise residual rate",
                                    "technicalDetails": Json({
                                        "detection_method": ela_evidence_method,
                                        "rule_id": rule_id,
                                        "trufor_score": round(trufor_result.score, 4) if trufor_result else None,
                                        "trufor_detection": trufor_result.detection if trufor_result else None,
                                        "mean_ambient_error": round(mean_err, 2),
                                        "std_ambient_error": round(std_err, 2),
                                        "threshold": round(threshold, 2),
                                        "patch_pixel_count": int(patch_pixel_count),
                                        "patch_bounds_px": [int(x_min), int(y_min), int(bbox_w), int(bbox_h)],
                                        "trufor_artifact_path": trufor_artifact_path,
                                        "ela_artifact_path": artifact_storage_path,
                                    }),
                                }
                            )

                            # Attach BoundingBox
                            await tx.boundingbox.create(
                                data={
                                    "evidenceItem": {"connect": {"id": finding.id}},
                                    "pageNumber": page.pageNumber,
                                    "x": float(x_min),
                                    "y": float(y_min),
                                    "width": float(bbox_w),
                                    "height": float(bbox_h),
                                    "xPts": float(x_min * scale_to_pts),
                                    "yPts": float(y_min * scale_to_pts),
                                    "widthPts": float(bbox_w * scale_to_pts),
                                    "heightPts": float(bbox_h * scale_to_pts),
                                    "label": finding_label,
                                    "color": finding_color,
                                }
                            )

                            # Attach EvidenceArtifact for the first finding
                            if b_idx == 0:
                                if is_trufor_active and trufor_artifact_path:
                                    await tx.evidenceartifact.create(
                                        data={
                                            "evidenceItem": {"connect": {"id": finding.id}},
                                            "artifactType": "trufor_anomaly",
                                            "storagePath": trufor_artifact_path,
                                            "mimeType": "image/png",
                                            "fileSizeBytes": len(anomaly_bytes),
                                            "caption": f"TruFor Neural Anomaly Map — Page {page.pageNumber}",
                                            "metadata": Json({
                                                "score": round(trufor_result.score, 4) if trufor_result else None,
                                                "detection": trufor_result.detection if trufor_result else None,
                                            }),
                                        }
                                    )
                                else:
                                    await tx.evidenceartifact.create(
                                        data={
                                            "evidenceItem": {"connect": {"id": finding.id}},
                                            "artifactType": "ela_heatmap",
                                            "storagePath": artifact_storage_path,
                                            "mimeType": "image/png",
                                            "fileSizeBytes": len(ela_bytes),
                                            "caption": f"Error Level Analysis (Q=95) Heatmap — Page {page.pageNumber}",
                                            "metadata": Json({
                                                "quality": 95,
                                                "scale_factor": scale,
                                                "mean_error": round(mean_err, 2),
                                            }),
                                        }
                                    )

                            stage_findings.append({
                                "id": finding.id,
                                "rule_id": rule_id,
                                "severity": finding.severity,
                                "page": page.pageNumber,
                                "title": finding.title,
                            })

                    except Exception as err:
                        # Non-fatal image processing error (ELA/TruFor)
                        import logging as _l
                        _l.getLogger(__name__).debug("ELA/TruFor non-fatal error on page %d: %s", page.pageNumber, err)

                    # ── Copy-Move Forgery Detection (CMFD) — non-fatal pass ───────────
                    # Runs independently of TruFor/ELA. Detects cloned/pasted regions.
                    try:
                        img_bytes_cmfd = storage.get_file(settings.s3_bucket_documents, page.renderedImagePath)
                        if img_bytes_cmfd:
                            from app.features.pipeline.tasks.cmfd_engine import detect_copy_move
                            orig_cmfd = Image.open(io.BytesIO(img_bytes_cmfd)).convert("RGB")
                            gray_cmfd = cv2.cvtColor(np.array(orig_cmfd), cv2.COLOR_RGB2GRAY)
                            scale_to_pts_cmfd = (page.widthPts / page.widthPx) if (page.widthPx and page.widthPts) else (72.0 / 150.0)

                            cmfd_matches = detect_copy_move(gray_cmfd, min_match_count=16, min_confidence=0.25)
                            for match in cmfd_matches:
                                cmfd_finding = await tx.evidenceitem.create(
                                    data={
                                        "document": {"connect": {"id": doc.id}},
                                        "pipelineStage": {"connect": {"id": pipeline_stage_id}},
                                        "category": "IMAGE_ELA_MANIPULATION",
                                        "severity": "CRITICAL",
                                        "ruleId": "RULE_CV_COPY_MOVE_FORGERY",
                                        "riskPoints": 30,
                                        "title": f"Copy-Move Forgery: Duplicated Region on Page {page.pageNumber}",
                                        "description": (
                                            f"ORB keypoint analysis (RANSAC verified, {match.match_count} inliers, "
                                            f"confidence {match.confidence:.1%}) identified a geometrically consistent "
                                            f"copy-move forgery on Page {page.pageNumber}. A region at "
                                            f"({match.src_bbox[0]}, {match.src_bbox[1]}) was duplicated to "
                                            f"({match.dst_bbox[0]}, {match.dst_bbox[1]}). "
                                            "This is consistent with cloned transaction rows, pasted stamps, or duplicated signatures."
                                        ),
                                        "isDeterministic": False,
                                        "confidence": round(match.confidence, 3),
                                        "pageNumber": page.pageNumber,
                                        "expectedValue": "Unique, non-duplicated visual content across all regions",
                                        "actualValue": f"Geometrically matching cloned region ({match.match_count} keypoint inliers)",
                                        "discrepancy": "Copy-move duplication detected",
                                        "technicalDetails": Json({
                                            "detection_method": "orb_bfmatcher_ransac",
                                            "inlier_count": match.match_count,
                                            "confidence": match.confidence,
                                            "src_bbox_px": list(match.src_bbox),
                                            "dst_bbox_px": list(match.dst_bbox),
                                        }),
                                    }
                                )
                                # Source bounding box
                                sx0, sy0, sw, sh = match.src_bbox
                                await tx.boundingbox.create(
                                    data={
                                        "evidenceItem": {"connect": {"id": cmfd_finding.id}},
                                        "pageNumber": page.pageNumber,
                                        "x": float(sx0), "y": float(sy0),
                                        "width": float(sw), "height": float(sh),
                                        "xPts": float(sx0 * scale_to_pts_cmfd),
                                        "yPts": float(sy0 * scale_to_pts_cmfd),
                                        "widthPts": float(sw * scale_to_pts_cmfd),
                                        "heightPts": float(sh * scale_to_pts_cmfd),
                                        "label": "Copy-Move Source",
                                        "color": "#7c3aed",
                                    }
                                )
                                # Destination bounding box
                                dx0, dy0, dw, dh = match.dst_bbox
                                await tx.boundingbox.create(
                                    data={
                                        "evidenceItem": {"connect": {"id": cmfd_finding.id}},
                                        "pageNumber": page.pageNumber,
                                        "x": float(dx0), "y": float(dy0),
                                        "width": float(dw), "height": float(dh),
                                        "xPts": float(dx0 * scale_to_pts_cmfd),
                                        "yPts": float(dy0 * scale_to_pts_cmfd),
                                        "widthPts": float(dw * scale_to_pts_cmfd),
                                        "heightPts": float(dh * scale_to_pts_cmfd),
                                        "label": "Copy-Move Destination",
                                        "color": "#dc2626",
                                    }
                                )
                                stage_findings.append({
                                    "id": cmfd_finding.id,
                                    "rule_id": "RULE_CV_COPY_MOVE_FORGERY",
                                    "severity": cmfd_finding.severity,
                                    "page": page.pageNumber,
                                    "title": cmfd_finding.title,
                                })
                    except Exception as cmfd_err:
                        import logging as _lc
                        _lc.getLogger(__name__).debug("CMFD non-fatal error on page %d: %s", page.pageNumber, cmfd_err)

            duration_ms = int((time.perf_counter() - start_time) * 1000)
            output_payload = {
                "findings_count": len(stage_findings),
                "findings": stage_findings,
                "duration_ms": duration_ms,
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
            try:
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
            except Exception:
                pass
            raise


@celery_app.task(
    name="app.features.pipeline.tasks.stage_4_vision_ela",
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
    """Celery task entry point for Stage 4."""
    import asyncio
    return asyncio.run(
        process_vision_ela(
            pipeline_run_id, pipeline_stage_id, org_id, investigation_id, document_id
        )
    )
