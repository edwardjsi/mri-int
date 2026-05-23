"""
Standardized engine result wrapper.

Every engine in the system returns an EngineResult object with:
  - data: the actual payload (dict, list, float, etc.)
  - status: OK, UNAVAILABLE, ERROR, STALE
  - quality: 0.0-1.0 confidence in the data
  - warnings: list of human-readable warning strings
  - source: the engine name that produced this

This replaces the current pattern where each engine returns ad-hoc dicts,
raw floats, or None, forcing callers to do type-checking.
"""

from __future__ import annotations

from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)

# Sentinel: returned by engines that can't produce data
ENGINE_UNAVAILABLE = -999.0


class EngineResult:
    """Standardized wrapper for all engine outputs."""

    __slots__ = ("data", "status", "quality", "warnings", "source")

    def __init__(
        self,
        data: Any = None,
        status: str = "OK",
        quality: float = 1.0,
        warnings: Optional[list[str]] = None,
        source: str = "unknown",
    ):
        self.data = data
        self.status = status
        self.quality = max(0.0, min(1.0, quality))
        self.warnings = warnings or []
        self.source = source

    # ── Factory constructors ──────────────────────────────────────────────

    @classmethod
    def ok(cls, data: Any, source: str = "unknown", quality: float = 1.0, warnings: Optional[list[str]] = None) -> "EngineResult":
        """Engine ran successfully with data."""
        return cls(data=data, status="OK", quality=quality, warnings=warnings, source=source)

    @classmethod
    def unavailable(cls, source: str = "unknown", reason: str = "") -> "EngineResult":
        """Engine could not produce data (missing inputs, no data source, etc.)."""
        return cls(
            data=ENGINE_UNAVAILABLE,
            status="UNAVAILABLE",
            quality=0.0,
            warnings=[reason] if reason else [],
            source=source,
        )

    @classmethod
    def error(cls, source: str = "unknown", message: str = "") -> "EngineResult":
        """Engine threw an error during execution."""
        return cls(
            data=ENGINE_UNAVAILABLE,
            status="ERROR",
            quality=0.0,
            warnings=[message] if message else [],
            source=source,
        )

    @classmethod
    def stale(cls, data: Any, source: str = "unknown", quality: float = 0.5, age_hours: Optional[float] = None) -> "EngineResult":
        """Engine produced data but it's older than expected freshness threshold."""
        w = [f"Data is {age_hours:.0f}h old" if age_hours else "Data may be stale"]
        return cls(data=data, status="STALE", quality=quality, warnings=w, source=source)

    # ── Convenience helpers ───────────────────────────────────────────────

    @property
    def is_available(self) -> bool:
        return self.status == "OK" and self.data is not None and self.data != ENGINE_UNAVAILABLE

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dict for JSON responses / DB storage."""
        return {
            "status": self.status,
            "quality": self.quality,
            "warnings": self.warnings,
            "source": self.source,
            "data": self.data,
        }

    def __repr__(self) -> str:
        return f"<EngineResult status={self.status} quality={self.quality:.2f} source='{self.source}'>"


# ── Migration helper: wrap any existing engine call ─────────────────────

def wrap_engine_call(func, source: str, *args, **kwargs) -> EngineResult:
    """Call an existing engine function and wrap its return in EngineResult.

    Handles three return patterns found across the codebase:
      1. dict with 'verdict' key → OK with dict as data
      2. float → OK with float as data
      3. None / empty dict → UNAVAILABLE
      4. Exception → ERROR
    """
    try:
        result = func(*args, **kwargs)
    except Exception as e:
        logger.warning(f"Engine {source} raised exception: {e}")
        return EngineResult.error(source=source, message=str(e))

    if result is None:
        return EngineResult.unavailable(source=source, reason="Engine returned None")
    if isinstance(result, dict) and not result:
        return EngineResult.unavailable(source=source, reason="Engine returned empty dict")
    if isinstance(result, dict) and result.get("verdict", "").lower().startswith("insufficient"):
        return EngineResult.unavailable(source=source, reason=result["verdict"])
    if isinstance(result, dict) and result.get("verdict", "").lower().startswith("no "):
        return EngineResult.unavailable(source=source, reason=result["verdict"])

    return EngineResult.ok(data=result, source=source)
