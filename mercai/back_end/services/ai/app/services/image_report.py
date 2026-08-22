"""
Deterministic image quality checks.

Phase 1 is Pillow-only on purpose (see design doc section 4). These checks
cannot hallucinate: every finding is a measurement. A vision model for
alt-text and subjective quality is deferred to phase 2.
"""
import logging
import os
from typing import Any, Dict, List, Optional

from PIL import Image, ImageStat

from shared.config import settings

logger = logging.getLogger(__name__)

MIN_LONG_EDGE = 1000
MIN_ASPECT, MAX_ASPECT = 0.6, 1.7   # outside this range ProductCard crops badly
MIN_IMAGE_COUNT = 3
MAX_FILE_MB = 2.0
MIN_BRIGHTNESS, MAX_BRIGHTNESS = 40, 225   # 0-255 mean luminance


def _finding(severity: str, code: str, message: str, image_id: Optional[int] = None) -> Dict[str, Any]:
    return {"severity": severity, "code": code, "message": message, "image_id": image_id}


def _local_path(image_url: str) -> Optional[str]:
    """
    Map a stored image URL onto a path on disk.

    Uploads are served from a local directory by the seller service
    (StaticFiles at /static/uploads), so only that prefix is resolvable here.
    Anything else is skipped rather than fetched -- this service does not make
    outbound requests to arbitrary URLs.
    """
    if not image_url:
        return None
    marker = "/static/uploads/"
    if marker not in image_url:
        return None
    filename = image_url.split(marker, 1)[1].lstrip("/")
    if not filename or ".." in filename:
        return None
    return os.path.join(settings.UPLOAD_DIR, filename)


def build_image_report(images: List[Any]) -> Dict[str, Any]:
    """
    `images` are ProductImage rows. Returns a report the seller can act on.

    Images that cannot be inspected (remote URL, missing file) are counted but
    produce no findings -- silence is better than a warning we cannot support.
    """
    findings: List[Dict[str, Any]] = []

    if not images:
        return {
            "score": "missing",
            "findings": [_finding("warn", "no_images", "This listing has no photos. Buyers rarely order without them.")],
            "inspected": 0,
        }

    if len(images) < MIN_IMAGE_COUNT:
        findings.append(_finding(
            "info", "too_few_images",
            f"Listings with {MIN_IMAGE_COUNT}+ photos convert better. You have {len(images)}.",
        ))

    if not any(getattr(img, "is_primary", False) for img in images):
        findings.append(_finding(
            "info", "no_primary_image",
            "No main photo is set, so the first upload is used by default.",
        ))

    inspected = 0
    for img in images:
        path = _local_path(getattr(img, "image_url", "") or "")
        if not path or not os.path.exists(path):
            continue

        try:
            size_mb = os.path.getsize(path) / (1024 * 1024)
            if size_mb > MAX_FILE_MB:
                findings.append(_finding(
                    "info", "large_file",
                    f"Photo is {size_mb:.1f}MB; compressing it speeds up loading on mobile data.",
                    getattr(img, "id", None),
                ))

            with Image.open(path) as im:
                width, height = im.size
                inspected += 1

                if max(width, height) < MIN_LONG_EDGE:
                    findings.append(_finding(
                        "warn", "low_resolution",
                        f"Photo is {width}x{height}px; aim for at least {MIN_LONG_EDGE}px on the long edge.",
                        getattr(img, "id", None),
                    ))

                aspect = width / height if height else 0
                if aspect and not (MIN_ASPECT <= aspect <= MAX_ASPECT):
                    findings.append(_finding(
                        "info", "unusual_aspect_ratio",
                        "This photo is an unusual shape and will be cropped in product listings.",
                        getattr(img, "id", None),
                    ))

                try:
                    brightness = ImageStat.Stat(im.convert("L")).mean[0]
                    if brightness < MIN_BRIGHTNESS:
                        findings.append(_finding(
                            "warn", "too_dark",
                            "This photo looks very dark. Natural light usually shows glaze better.",
                            getattr(img, "id", None),
                        ))
                    elif brightness > MAX_BRIGHTNESS:
                        findings.append(_finding(
                            "info", "too_bright",
                            "This photo looks overexposed, which can wash out the glaze colour.",
                            getattr(img, "id", None),
                        ))
                except Exception:
                    logger.debug("Brightness check failed", exc_info=True)

        except Exception:
            logger.debug("Could not inspect image at %s", path, exc_info=True)
            continue

    if any(f["severity"] == "warn" for f in findings):
        score = "needs_work"
    elif findings:
        score = "good"
    else:
        score = "excellent"

    return {"score": score, "findings": findings, "inspected": inspected}
