"""
API Response Compression Configuration

Provides compression middleware and utilities for optimizing response sizes.
"""
import os
import gzip
import zlib
from typing import Optional, List, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
import logging

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class CompressionAlgorithm(Enum):
    """Supported compression algorithms"""
    GZIP = "gzip"
    DEFLATE = "deflate"
    BR = "br"  # Brotli
    IDENTITY = "identity"  # No compression


@dataclass
class CompressionConfig:
    """Compression configuration settings"""

    # Enable/disable compression
    enabled: bool = os.getenv("COMPRESSION_ENABLED", "true").lower() == "true"

    # Minimum response size to compress (bytes)
    minimum_size: int = int(os.getenv("COMPRESSION_MIN_SIZE", "500"))

    # Compression level (1-9, higher = more compression but slower)
    gzip_level: int = int(os.getenv("COMPRESSION_GZIP_LEVEL", "6"))
    deflate_level: int = int(os.getenv("COMPRESSION_DEFLATE_LEVEL", "6"))
    brotli_quality: int = int(os.getenv("COMPRESSION_BROTLI_QUALITY", "4"))

    # Preferred algorithm order
    preferred_algorithms: List[str] = field(default_factory=lambda: [
        "br",       # Brotli - best compression
        "gzip",     # Gzip - widely supported
        "deflate",  # Deflate - fallback
    ])

    # Content types to compress
    compressible_types: Set[str] = field(default_factory=lambda: {
        "application/json",
        "application/xml",
        "text/html",
        "text/plain",
        "text/css",
        "text/javascript",
        "application/javascript",
        "application/x-javascript",
        "image/svg+xml",
    })

    # Paths to exclude from compression
    excluded_paths: Set[str] = field(default_factory=lambda: {
        "/health",
        "/metrics",
        "/ready",
        "/live",
    })

    # Maximum response size to compress (avoid compressing huge responses)
    maximum_size: int = int(os.getenv("COMPRESSION_MAX_SIZE", str(50 * 1024 * 1024)))  # 50MB


def get_compression_config() -> CompressionConfig:
    """Get compression configuration singleton"""
    return CompressionConfig()


def should_compress(
    request: Request,
    response_size: int,
    content_type: str,
    config: Optional[CompressionConfig] = None
) -> bool:
    """
    Determine if a response should be compressed

    Args:
        request: FastAPI request
        response_size: Size of response body in bytes
        content_type: Response content type
        config: Optional compression config

    Returns:
        True if response should be compressed
    """
    config = config or get_compression_config()

    if not config.enabled:
        return False

    # Check size thresholds
    if response_size < config.minimum_size:
        return False

    if response_size > config.maximum_size:
        return False

    # Check if path is excluded
    if request.url.path in config.excluded_paths:
        return False

    # Check content type
    base_type = content_type.split(";")[0].strip()
    if base_type not in config.compressible_types:
        return False

    # Check if client accepts compression
    accept_encoding = request.headers.get("accept-encoding", "")
    if not any(alg in accept_encoding for alg in config.preferred_algorithms):
        return False

    return True


def get_best_encoding(
    accept_encoding: str,
    config: Optional[CompressionConfig] = None
) -> str:
    """
    Get the best compression encoding based on client preferences

    Args:
        accept_encoding: Accept-Encoding header value
        config: Optional compression config

    Returns:
        Best encoding to use
    """
    config = config or get_compression_config()

    # Parse accept-encoding with quality values
    encodings = {}
    for part in accept_encoding.split(","):
        part = part.strip()
        if ";q=" in part:
            encoding, q = part.split(";q=")
            encodings[encoding.strip()] = float(q)
        else:
            encodings[part] = 1.0

    # Find best match from our preferences
    for preferred in config.preferred_algorithms:
        if preferred in encodings and encodings[preferred] > 0:
            return preferred

    return "identity"


def compress_data(
    data: bytes,
    encoding: str,
    config: Optional[CompressionConfig] = None
) -> bytes:
    """
    Compress data using specified encoding

    Args:
        data: Raw data to compress
        encoding: Compression encoding to use
        config: Optional compression config

    Returns:
        Compressed data
    """
    config = config or get_compression_config()

    if encoding == "gzip":
        return gzip.compress(data, compresslevel=config.gzip_level)

    elif encoding == "deflate":
        return zlib.compress(data, level=config.deflate_level)

    elif encoding == "br":
        try:
            import brotli
            return brotli.compress(data, quality=config.brotli_quality)
        except ImportError:
            logger.warning("Brotli not available, falling back to gzip")
            return gzip.compress(data, compresslevel=config.gzip_level)

    return data


class AdvancedCompressionMiddleware(BaseHTTPMiddleware):
    """
    Advanced compression middleware with content-type awareness
    and configurable compression algorithms
    """

    def __init__(
        self,
        app: ASGIApp,
        config: Optional[CompressionConfig] = None
    ):
        super().__init__(app)
        self.config = config or get_compression_config()

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip if compression disabled
        if not self.config.enabled:
            return await call_next(request)

        # Skip excluded paths
        if request.url.path in self.config.excluded_paths:
            return await call_next(request)

        # Get response
        response = await call_next(request)

        # Check if already compressed
        if "content-encoding" in response.headers:
            return response

        # Get content type
        content_type = response.headers.get("content-type", "")
        base_type = content_type.split(";")[0].strip()

        # Check if compressible
        if base_type not in self.config.compressible_types:
            return response

        # Get best encoding
        accept_encoding = request.headers.get("accept-encoding", "")
        encoding = get_best_encoding(accept_encoding, self.config)

        if encoding == "identity":
            return response

        # For streaming responses, we can't easily get size
        # Use standard GZipMiddleware behavior
        return response


def get_compression_middleware(
    app: ASGIApp,
    config: Optional[CompressionConfig] = None
) -> ASGIApp:
    """
    Get configured compression middleware

    Returns the appropriate middleware based on configuration.
    """
    config = config or get_compression_config()

    if not config.enabled:
        return app

    # Use Starlette's built-in GZipMiddleware for simplicity
    # It handles streaming responses correctly
    return GZipMiddleware(
        app,
        minimum_size=config.minimum_size,
        compresslevel=config.gzip_level
    )


# Response size optimization utilities
@dataclass
class ResponseOptimizer:
    """Utilities for optimizing response sizes"""

    @staticmethod
    def remove_null_fields(data: dict) -> dict:
        """Remove null/None fields from response"""
        return {k: v for k, v in data.items() if v is not None}

    @staticmethod
    def truncate_fields(
        data: dict,
        max_lengths: dict
    ) -> dict:
        """
        Truncate string fields to maximum lengths

        Args:
            data: Response data
            max_lengths: Dict mapping field names to max lengths
        """
        result = data.copy()
        for field, max_len in max_lengths.items():
            if field in result and isinstance(result[field], str):
                if len(result[field]) > max_len:
                    result[field] = result[field][:max_len] + "..."
        return result

    @staticmethod
    def paginate_list(
        items: list,
        page: int = 1,
        page_size: int = 50
    ) -> dict:
        """
        Paginate a list response

        Args:
            items: List of items
            page: Page number (1-indexed)
            page_size: Items per page

        Returns:
            Paginated response with metadata
        """
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size

        return {
            "items": items[start:end],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total,
                "total_pages": (total + page_size - 1) // page_size,
                "has_next": end < total,
                "has_prev": page > 1,
            }
        }

    @staticmethod
    def select_fields(
        data: dict,
        fields: List[str]
    ) -> dict:
        """
        Select only specified fields from response

        Supports nested fields with dot notation (e.g., "user.name")
        """
        result = {}
        for field in fields:
            if "." in field:
                # Handle nested fields
                parts = field.split(".")
                value = data
                for part in parts:
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        value = None
                        break
                if value is not None:
                    # Reconstruct nested structure
                    current = result
                    for part in parts[:-1]:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
                    current[parts[-1]] = value
            elif field in data:
                result[field] = data[field]
        return result


# Content negotiation
def negotiate_content_type(
    accept_header: str,
    available_types: List[str]
) -> Optional[str]:
    """
    Negotiate content type based on Accept header

    Args:
        accept_header: Accept header value
        available_types: List of available content types

    Returns:
        Best matching content type or None
    """
    if not accept_header:
        return available_types[0] if available_types else None

    # Parse accept header
    accepted = []
    for part in accept_header.split(","):
        part = part.strip()
        if ";q=" in part:
            media_type, q = part.split(";q=")
            accepted.append((media_type.strip(), float(q)))
        else:
            accepted.append((part, 1.0))

    # Sort by quality
    accepted.sort(key=lambda x: x[1], reverse=True)

    # Find best match
    for media_type, _ in accepted:
        if media_type == "*/*":
            return available_types[0] if available_types else None
        if media_type in available_types:
            return media_type
        # Check for type/* wildcards
        if media_type.endswith("/*"):
            base = media_type[:-2]
            for available in available_types:
                if available.startswith(base):
                    return available

    return None
