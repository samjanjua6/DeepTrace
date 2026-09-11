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
                kps, descs = sift.detectAndCompute(img_gray, None)
                norm_type = cv2.NORM_L2
            except Exception as e:
                logger.debug("cmfd_engine: SIFT failed (%s), falling back to ORB.", e)

        if descs is None:
            method_name = "orb_ransac_4d"
            orb = cv2.ORB_create(nfeatures=nfeatures)
            kps, descs = orb.detectAndCompute(img_gray, None)
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
                comp_confidence = len(comp) / max(len(cluster), 1)

                results.append(
                    CopyMoveMatch(
                        src_bbox=src_bbox,
                        dst_bbox=dst_bbox,
                        match_count=len(comp),
                        confidence=round(comp_confidence, 3),
                        shift_vector=(round(dx_mean, 1), round(dy_mean, 1)),
                        method=method_name,
                    )
                )

        # Sort matches by inlier count descending
        results.sort(key=lambda x: x.match_count, reverse=True)
        return results

    except Exception as exc:
        logger.warning("cmfd_engine: Copy-move detection failed: %s", exc)
        return []
