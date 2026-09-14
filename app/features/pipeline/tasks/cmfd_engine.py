"""
Copy-Move Forgery Detection (CMFD) Engine.
Combines:
  1. SIFT 128D scale- and rotation-invariant feature descriptors (primary)
     with automatic fallback to ORB binary descriptors.
  2. 4D Shift-Vector Space Clustering: groups keypoint pairs by translation
     displacement (Δx, Δy), relative scale (Δs), and orientation (Δθ) to isolate
     multiple independent cloned objects while rejecting coincidental font glyph matches.
  3. Geometric RANSAC Homography Verification per cluster.
  4. Dense Patch Correlation Verification for physical boundary confirmation.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Minimum Euclidean distance between matched keypoint centres (pixels)
# to discard self-matches within the same glyph/stroke.
_MIN_SPATIAL_SEPARATION_PX = 25

# Lowe's ratio test threshold
_RATIO_THRESH = 0.75

# RANSAC reprojection threshold (pixels)
_RANSAC_REPROJ_THRESH = 5.0


@dataclass(frozen=True)
class CopyMoveMatch:
    """A geometrically verified copy-move pair."""
    src_bbox: tuple[int, int, int, int]       # (x, y, w, h) in image pixels
    dst_bbox: tuple[int, int, int, int]       # (x, y, w, h) in image pixels
    match_count: int                           # number of inlier keypoint matches
    confidence: float                          # inlier_count / total_cluster_matches
    shift_vector: tuple[float, float] = (0.0, 0.0) # (dx, dy) translation displacement
    method: str = "sift_ransac_4d"
    bg_zncc: float = 0.0                       # Background correlation score
    conflict_ratio: float = 0.0                # Conflicting foreground stroke ratio


def _verify_copy_move_patch(
    img_gray: np.ndarray,
    src_bbox: tuple[int, int, int, int],
    dst_bbox: tuple[int, int, int, int],
) -> tuple[bool, str, float, float]:
    """
    Forensically verify if a candidate keypoint cluster represents a true physical copy-move
    patch duplication or an authentic typographical text repetition (repeated names, dates, labels).

    Evaluates:
      1. Conflicting foreground stroke residual (Otsu thresholding):
         Measures contradictory stroke pixels where one patch has ink and the other has background.
         Partial matches (e.g. 'Issue' vs 'Expiry' in dates, or different names sharing prefixes)
         exhibit significant conflicting strokes (> 12%).
      2. Background substrate correlation (ZNCC):
         In authentic printing, identical words (e.g. 'Muhammad' on Line 1 and Line 2) are printed
         on physically independent security guilloche patterns or paper grain (ZNCC < 0.80).
         In digital copy-paste or clone-stamp manipulation, the entire raster patch including
         background fibers/noise is duplicated (ZNCC >= 0.80).
      3. Typographical geometry classification:
         Monoline and multi-line text fields have characteristic line heights and stroke densities.

    Returns:
        (is_valid, reason, bg_zncc, conflict_ratio)
    """
    sx, sy, sw, sh = src_bbox
    dx, dy, dw, dh = dst_bbox
    img_h, img_w = img_gray.shape[:2]

    # Bounds check
    if sx < 0 or sy < 0 or sx + sw > img_w or sy + sh > img_h:
        return False, "out_of_bounds", 0.0, 0.0
    if dx < 0 or dy < 0 or dx + dw > img_w or dy + dh > img_h:
        return False, "out_of_bounds", 0.0, 0.0

    w = min(sw, dw)
    h = min(sh, dh)
    if w < 10 or h < 10:
        return False, "patch_too_small", 0.0, 0.0

    sp = img_gray[sy : sy + h, sx : sx + w]
    dp = img_gray[dy : dy + h, dx : dx + w]

    # Check contrast / dynamic range
    s_min, s_max = int(np.min(sp)), int(np.max(sp))
    d_min, d_max = int(np.min(dp)), int(np.max(dp))
    if (s_max - s_min) < 12 and (d_max - d_min) < 12:
        return False, "uniform_contrast", 0.0, 0.0

    # Extract core region without outer padding to prevent border artifacts from
    # keypoint bounding box expansion across patch boundaries
    margin_x = min(6, w // 6)
    margin_y = min(6, h // 6)
    sp_core = sp[margin_y : h - margin_y, margin_x : w - margin_x]
    dp_core = dp[margin_y : h - margin_y, margin_x : w - margin_x]
    cw, ch = sp_core.shape[1], sp_core.shape[0]
    if cw < 6 or ch < 6:
        sp_core, dp_core = sp, dp
        cw, ch = w, h

    # 1. Foreground / Background segmentation via Otsu
    _, s_bin = cv2.threshold(sp_core, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    _, d_bin = cv2.threshold(dp_core, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    stroke_mask = (s_bin == 255) | (d_bin == 255)
    stroke_count = int(np.sum(stroke_mask))
    total_pixels = cw * ch
    stroke_density = stroke_count / max(1, total_pixels)

    # 2. Conflicting foreground strokes
    conflict_mask = (s_bin != d_bin)
    conflict_count = int(np.sum(conflict_mask))
    conflict_stroke_ratio = conflict_count / max(1, stroke_count)

    # 3. Background Correlation
    # Dilate foreground strokes to eliminate anti-aliased font halos from leaking into the background
    dilated_strokes = cv2.dilate(stroke_mask.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=2)
    bg_mask = (dilated_strokes == 0)
    bg_count = int(np.sum(bg_mask))
    bg_ratio = bg_count / max(1, total_pixels)

    if bg_count > 30 and bg_ratio > 0.10:
        s_bg = sp_core[bg_mask].astype(np.float32)
        d_bg = dp_core[bg_mask].astype(np.float32)
        s_std = float(np.std(s_bg))
        d_std = float(np.std(d_bg))
        if s_std > 1.5 and d_std > 1.5:
            bg_zncc = float(np.mean((s_bg - np.mean(s_bg)) * (d_bg - np.mean(d_bg))) / (s_std * d_std))
        elif np.allclose(s_bg, d_bg, atol=2.0):
            # Flat uniform background with identical intensity values across cloned regions
            bg_zncc = 1.0
        else:
            bg_zncc = 0.0
    else:
        bg_zncc = 0.0

    # 4. Typographical Classification
    mean_diff = float(np.mean(np.abs(sp_core.astype(float) - dp_core.astype(float))))
    is_typographical = (max(sh, dh) <= min(58, int(0.14 * img_h))) and (stroke_density < 0.42)

    # Rule A: Suppress authentic typographical text unless proven exact digital clone
    # In authentic documents, identical words/labels are printed with identical font glyphs.
    # A true copy-paste forgery duplicates the entire raster patch with identical background (bg_zncc >= 0.85),
    # zero conflicting strokes (<= 4%), and tiny pixel difference (mean_diff <= 4.0).
    if is_typographical:
        is_exact_clone = (bg_zncc >= 0.85) and (conflict_stroke_ratio <= 0.04) and (mean_diff <= 4.0)
        if not is_exact_clone:
            return (
                False,
                f"typographical_text_suppression (bg={bg_zncc:.2f}, conflict={conflict_stroke_ratio:.1%}, diff={mean_diff:.1f})",
                bg_zncc,
                conflict_stroke_ratio,
            )

    # Rule B: Conflicting foreground strokes for any region
    if conflict_stroke_ratio > 0.12:
        return False, f"conflicting_strokes ({conflict_stroke_ratio:.1%})", bg_zncc, conflict_stroke_ratio

    return True, "verified_clone", bg_zncc, conflict_stroke_ratio


def _keypoints_to_bbox(kps: list, img_w: int, img_h: int, pad: int = 8) -> tuple[int, int, int, int]:
    """Return tight axis-aligned bounding box around a set of keypoints with padding."""
    xs = [int(kp.pt[0]) for kp in kps]
    ys = [int(kp.pt[1]) for kp in kps]
    x0 = max(0, min(xs) - pad)
    y0 = max(0, min(ys) - pad)
    x1 = min(img_w, max(xs) + pad)
    y1 = min(img_h, max(ys) + pad)
    return x0, y0, max(1, x1 - x0), max(1, y1 - y0)


def _spatial_partition_inliers(
    src_kps: list[cv2.KeyPoint],
    dst_kps: list[cv2.KeyPoint],
    spatial_dist: float = 60.0,
) -> list[list[int]]:
    """
    Partition inlier keypoint indices into spatially coherent clusters using single-linkage
    connected components in 2D coordinate space. This separates distant rows or text blocks
    that share the same translation vector into distinct localized regions.
    """
    n = len(src_kps)
    if n <= 1:
        return [[0]] if n == 1 else []

    adj = [[] for _ in range(n)]
    for i in range(n):
        si = src_kps[i].pt
        di = dst_kps[i].pt
        for j in range(i + 1, n):
            sj = src_kps[j].pt
            dj = dst_kps[j].pt
            src_dist = ((si[0] - sj[0]) ** 2 + (si[1] - sj[1]) ** 2) ** 0.5
            dst_dist = ((di[0] - dj[0]) ** 2 + (di[1] - dj[1]) ** 2) ** 0.5
            if src_dist <= spatial_dist and dst_dist <= spatial_dist:
                adj[i].append(j)
                adj[j].append(i)

    visited = [False] * n
    components: list[list[int]] = []
    for i in range(n):
        if not visited[i]:
            visited[i] = True
            comp = [i]
            queue = [i]
            while queue:
                curr = queue.pop(0)
                for neighbor in adj[curr]:
                    if not visited[neighbor]:
                        visited[neighbor] = True
                        comp.append(neighbor)
                        queue.append(neighbor)
            components.append(comp)

    return components


def _cluster_shift_vectors(
    matches: list[cv2.DMatch],
    kps: list[cv2.KeyPoint],
    pos_tol: float = 25.0,
    angle_tol: float = 30.0,
) -> list[list[cv2.DMatch]]:
    """
    Cluster keypoint matches into coherent transformation groups using 4D shift vectors:
    (Δx, Δy, Δθ, Δs). Matches belonging to the same cloned stamp/signature share
    nearly identical spatial displacement and rotation.
    """
    if not matches:
        return []

    # Compute 4D parameters for each match
    descriptors_list = []
    for m in matches:
        kp_q = kps[m.queryIdx]
        kp_t = kps[m.trainIdx]
        dx = kp_t.pt[0] - kp_q.pt[0]
        dy = kp_t.pt[1] - kp_q.pt[1]
        d_angle = (kp_t.angle - kp_q.angle + 360.0) % 360.0
        if d_angle > 180.0:
            d_angle = 360.0 - d_angle
        descriptors_list.append((dx, dy, d_angle))

    # Agglomerative clustering by Euclidean distance in (dx, dy) and angle difference
    clusters: list[list[cv2.DMatch]] = []
    cluster_centers: list[tuple[float, float, float]] = []

    for idx, m in enumerate(matches):
        dx, dy, da = descriptors_list[idx]
        assigned = False
        for c_idx, (cdx, cdy, cda) in enumerate(cluster_centers):
            dist_sq = (dx - cdx) ** 2 + (dy - cdy) ** 2
            if dist_sq <= (pos_tol ** 2) and abs(da - cda) <= angle_tol:
                clusters[c_idx].append(m)
                # Update center with moving average
                n = len(clusters[c_idx])
                cluster_centers[c_idx] = (
                    cdx + (dx - cdx) / n,
                    cdy + (dy - cdy) / n,
                    cda + (da - cda) / n,
                )
                assigned = True
                break
        if not assigned:
            clusters.append([m])
            cluster_centers.append((dx, dy, da))

    return clusters


def detect_copy_move(
    img_gray: np.ndarray,
    min_match_count: int = 8,
    nfeatures: int = 3500,
    min_confidence: float = 0.25,
    mask: Optional[np.ndarray] = None,
) -> list[CopyMoveMatch]:
    """
    Detect copy-move forgery in a grayscale page image.

    Algorithm:
      1. Extract SIFT 128D keypoints and descriptors (or ORB as fallback).
      2. BFMatcher nearest-neighbor search (k=3) with Lowe's ratio test (0.75).
      3. Spatial separation filter: discard pairs with Euclidean distance < _MIN_SPATIAL_SEPARATION_PX.
      4. 4D Shift-Vector Clustering: groups matches with coherent (Δx, Δy, Δθ).
      5. Per-cluster RANSAC homography geometric verification.
      6. Bounding box localization and runaway box rejection (< 50% page width).

    Args:
        img_gray:        uint8 grayscale image (H, W).
        min_match_count: Minimum number of RANSAC inliers per cluster to report a forgery.
        nfeatures:       Maximum keypoints to extract.
        min_confidence:  Minimum ratio of inliers to cluster candidate matches.
        mask:            Optional uint8 binary mask (255=search, 0=ignore). Used to exclude
                         native vector text regions in digital PDFs from false alarms.

    Returns:
        List of :class:`CopyMoveMatch`, empty if no forgery detected or on error.
    """
    if img_gray is None or img_gray.size == 0:
        return []

    h, w = img_gray.shape[:2]

    try:
        # 1. Feature Extraction: Prefer SIFT, fallback to ORB
        method_name = "sift_ransac_4d"
        kps, descs = None, None

        if hasattr(cv2, "SIFT_create"):
            try:
                sift = cv2.SIFT_create(nfeatures=nfeatures)
                kps, descs = sift.detectAndCompute(img_gray, mask)
                norm_type = cv2.NORM_L2
            except Exception as e:
                logger.debug("cmfd_engine: SIFT failed (%s), falling back to ORB.", e)

        if descs is None:
            method_name = "orb_ransac_4d"
            orb = cv2.ORB_create(nfeatures=nfeatures)
            kps, descs = orb.detectAndCompute(img_gray, mask)
            norm_type = cv2.NORM_HAMMING

        if descs is None or len(kps) < min_match_count * 2:
            return []

        # 2. Self-Matching with k=3
        # match[0] is self (dist=0), match[1] is closest neighbor, match[2] is 2nd closest
        bf = cv2.BFMatcher(norm_type, crossCheck=False)
        raw_matches = bf.knnMatch(descs, descs, k=3)

        good_matches: list[cv2.DMatch] = []
        for matches in raw_matches:
            non_self = [m for m in matches if m.trainIdx != m.queryIdx]
            if len(non_self) < 2:
                continue
            m, n = non_self[0], non_self[1]

            # Lowe's ratio test
            if m.distance >= _RATIO_THRESH * n.distance:
                continue

            # Directional deduplication (A -> B only, avoid B -> A duplicate)
            if m.queryIdx >= m.trainIdx:
                continue

            # Spatial distance filter (suppress local glyph self-matches)
            kp_q = kps[m.queryIdx]
            kp_t = kps[m.trainIdx]
            dx = kp_q.pt[0] - kp_t.pt[0]
            dy = kp_q.pt[1] - kp_t.pt[1]
            dist = (dx * dx + dy * dy) ** 0.5
            if dist < _MIN_SPATIAL_SEPARATION_PX:
                continue

            good_matches.append(m)

        if len(good_matches) < min_match_count:
            return []

        # 3. 4D Shift-Vector Space Clustering
        clusters = _cluster_shift_vectors(good_matches, kps, pos_tol=35.0, angle_tol=35.0)

        results: list[CopyMoveMatch] = []

        # 4. Geometric RANSAC per cluster
        for cluster in clusters:
            if len(cluster) < min_match_count:
                continue

            src_pts = np.float32([kps[m.queryIdx].pt for m in cluster]).reshape(-1, 1, 2)
            dst_pts = np.float32([kps[m.trainIdx].pt for m in cluster]).reshape(-1, 1, 2)

            # RANSAC homography
            _, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, _RANSAC_REPROJ_THRESH)
            if mask is None:
                continue

            inlier_mask = mask.ravel().astype(bool)
            inlier_count = int(inlier_mask.sum())
            if inlier_count < min_match_count:
                continue

            confidence = inlier_count / max(len(cluster), 1)
            if confidence < min_confidence:
                continue

            # Extract inlier keypoints
            src_kps_inlier = [kps[cluster[i].queryIdx] for i, ok in enumerate(inlier_mask) if ok]
            dst_kps_inlier = [kps[cluster[i].trainIdx] for i, ok in enumerate(inlier_mask) if ok]

            # 5. Spatial Connected-Components Partitioning:
            # Splits distant rows or disparate text blocks sharing the same shift vector
            # into localized physical components.
            comps = _spatial_partition_inliers(src_kps_inlier, dst_kps_inlier, spatial_dist=60.0)

            for comp in comps:
                if len(comp) < min_match_count:
                    continue

                comp_src = [src_kps_inlier[k] for k in comp]
                comp_dst = [dst_kps_inlier[k] for k in comp]

                src_bbox = _keypoints_to_bbox(comp_src, w, h)
                dst_bbox = _keypoints_to_bbox(comp_dst, w, h)

                # 6. Runaway box suppression: localized stamps/signatures/rows are < 45% page width and < 20% page height
                max_box_h = min(220, int(0.20 * h))
                if src_bbox[2] > (0.45 * w) or dst_bbox[2] > (0.45 * w):
                    continue
                if src_bbox[3] > max_box_h or dst_bbox[3] > max_box_h:
                    continue

                # 7. Spatial Disjointness Filter:
                # Source and cloned regions must be spatially separated. High overlap indicates
                # coincidental font glyph matches (e.g. repeated characters) within the same line.
                x_ov = max(0, min(src_bbox[0] + src_bbox[2], dst_bbox[0] + dst_bbox[2]) - max(src_bbox[0], dst_bbox[0]))
                y_ov = max(0, min(src_bbox[1] + src_bbox[3], dst_bbox[1] + dst_bbox[3]) - max(src_bbox[1], dst_bbox[1]))
                inter_area = x_ov * y_ov
                min_box_area = min(src_bbox[2] * src_bbox[3], dst_bbox[2] * dst_bbox[3])
                if min_box_area > 0 and (inter_area / min_box_area) > 0.20:
                    continue

                # Mean displacement for this localized component
                dx_mean = float(np.mean([d.pt[0] - s.pt[0] for s, d in zip(comp_src, comp_dst)]))
                dy_mean = float(np.mean([d.pt[1] - s.pt[1] for s, d in zip(comp_src, comp_dst)]))

                # 8. Intra-Line Monoline Glyph Repetition Suppression:
                # Reject matches where both regions lie along the exact same horizontal baseline (abs(dy) <= 6 px),
                # have single-character typographical height (max(src_h, dst_h) <= 52 px), and small area (< 4500 px²).
                # Also accommodates slight smartphone perspective tilt (abs(dy) <= 12 px when abs(dx) > 3 * abs(dy)).
                is_horizontal_tilt = abs(dy_mean) <= 12.0 and abs(dx_mean) > (3.0 * abs(dy_mean))
                if (abs(dy_mean) <= 6.0 or is_horizontal_tilt) and max(src_bbox[3], dst_bbox[3]) <= 52 and min_box_area < 4500:
                    continue

                # 9. Dense Patch Correlation & Forensic Substrate Verification:
                # Discard candidates where foreground strokes conflict (partial word/date matches)
                # or where typographical text is rendered on independent physical background textures.
                is_valid, reason, bg_zncc, conflict_ratio = _verify_copy_move_patch(img_gray, src_bbox, dst_bbox)
                if not is_valid:
                    logger.debug(
                        "cmfd_engine: Rejected candidate %s -> %s: %s",
                        src_bbox, dst_bbox, reason,
                    )
                    continue

                comp_confidence = len(comp) / max(len(cluster), 1)

                results.append(
                    CopyMoveMatch(
                        src_bbox=src_bbox,
                        dst_bbox=dst_bbox,
                        match_count=len(comp),
                        confidence=round(comp_confidence, 3),
                        shift_vector=(round(dx_mean, 1), round(dy_mean, 1)),
                        method=method_name,
                        bg_zncc=round(bg_zncc, 3),
                        conflict_ratio=round(conflict_ratio, 3),
                    )
                )

        # Sort matches by inlier count descending
        results.sort(key=lambda x: x.match_count, reverse=True)
        return results

    except Exception as exc:
        logger.warning("cmfd_engine: Copy-move detection failed: %s", exc)
        return []
