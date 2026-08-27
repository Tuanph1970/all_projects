"""
Per-host adapter registry, and the allowlist derived from it.

An adapter is DATA -- one YAML file per host under app/adapters/. Adding a
source is a diff someone can review, not a Python release. That is the concrete
answer to the objection that started this redesign.

The registry doubles as the fetch allowlist (section 6 rule 2), which is both
the SSRF backstop and the legal posture: we fetch from hosts we chose
deliberately, never from anything a seller happens to paste.
"""
import logging
import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, List, Optional

from shared.config import settings

logger = logging.getLogger(__name__)

ADAPTER_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "adapters")


@dataclass
class Adapter:
    host: str
    currency: str = "VND"
    tiers: List[str] = field(default_factory=list)
    state_paths: List[str] = field(default_factory=list)
    price_selector: Optional[str] = None
    title_selector: Optional[str] = None
    unavailable_selector: Optional[str] = None
    notes: Optional[str] = None


def _from_dict(raw: Dict) -> Optional[Adapter]:
    host = (raw.get("host") or "").strip().lower()
    if not host:
        return None
    sel = raw.get("selectors") or {}
    return Adapter(
        host=host,
        currency=(raw.get("currency") or "VND").upper(),
        tiers=list(raw.get("tiers") or []),
        state_paths=list(raw.get("state_paths") or []),
        price_selector=sel.get("price"),
        title_selector=sel.get("title"),
        unavailable_selector=sel.get("unavailable"),
        notes=raw.get("notes"),
    )


@lru_cache(maxsize=1)
def registry() -> Dict[str, Adapter]:
    """Every adapter on disk, keyed by host. Cached -- these are static files."""
    try:
        import yaml
    except ImportError:  # pragma: no cover - dependency is declared
        logger.warning("PyYAML missing; no adapters loaded")
        return {}

    found: Dict[str, Adapter] = {}
    if not os.path.isdir(ADAPTER_DIR):
        return found

    for name in sorted(os.listdir(ADAPTER_DIR)):
        if not name.endswith((".yml", ".yaml")) or name.startswith("_"):
            continue
        path = os.path.join(ADAPTER_DIR, name)
        try:
            with open(path, encoding="utf-8") as handle:
                adapter = _from_dict(yaml.safe_load(handle) or {})
        except Exception:
            logger.warning("Could not load adapter %s", name, exc_info=True)
            continue
        if adapter:
            found[adapter.host] = adapter
    return found


def _extra_hosts() -> List[str]:
    raw = getattr(settings, "INTEL_ALLOWED_HOSTS", "") or ""
    return [h.strip().lower() for h in raw.split(",") if h.strip()]


def allowed_hosts() -> List[str]:
    return sorted(set(registry()) | set(_extra_hosts()))


def normalise_host(host: str) -> str:
    host = (host or "").strip().lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host


def is_allowed(host: str) -> bool:
    """
    Allowlist check, matching the registrable host and its subdomains.

    `www.` is stripped rather than listed twice, and a subdomain of an allowed
    host is allowed -- `m.tiki.vn` is the same operator as `tiki.vn`. Anything
    else is refused at add-time with a message naming what we do support.
    """
    host = normalise_host(host)
    if not host:
        return False
    for allowed in allowed_hosts():
        if host == allowed or host.endswith("." + allowed):
            return True
    return False


def for_host(host: str) -> Optional[Adapter]:
    host = normalise_host(host)
    table = registry()
    if host in table:
        return table[host]
    for allowed, adapter in table.items():
        if host.endswith("." + allowed):
            return adapter
    return None
