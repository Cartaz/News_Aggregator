"""Low-level process memory controls for supported native runtimes.

The application is cross-platform, so these helpers are deliberately best-effort:
Linux/glibc-specific controls are used when available and become no-ops elsewhere.
"""

from __future__ import annotations

import os
import sys
from typing import Any

DEFAULT_GLIBC_ARENA_MAX = 2

_malloc_trim_library: Any | None = None
_malloc_trim_function: Any | None = None
_malloc_trim_resolved = False


def bootstrap_allocator(arena_max: int = DEFAULT_GLIBC_ARENA_MAX) -> None:
    """Restart once with a bounded glibc arena count before heavy imports.

    ``MALLOC_ARENA_MAX`` is intentionally applied through ``execve`` rather than
    changed in-process: the replacement interpreter then starts with the allocator
    policy active from its first allocation. An explicit user-provided value is
    always respected.
    """
    if not sys.platform.startswith("linux"):
        return
    if os.environ.get("MALLOC_ARENA_MAX", "").strip():
        return

    value = max(1, int(arena_max))
    environment = os.environ.copy()
    environment["MALLOC_ARENA_MAX"] = str(value)
    os.execve(
        sys.executable,
        [sys.executable, *sys.argv],
        environment,
    )


def _resolve_malloc_trim() -> Any | None:
    global _malloc_trim_library, _malloc_trim_function, _malloc_trim_resolved

    if _malloc_trim_resolved:
        return _malloc_trim_function
    _malloc_trim_resolved = True

    if not sys.platform.startswith("linux"):
        return None

    try:
        import ctypes

        library = ctypes.CDLL(None)
        function = getattr(library, "malloc_trim")
        function.argtypes = [ctypes.c_size_t]
        function.restype = ctypes.c_int
    except (AttributeError, OSError):
        return None

    _malloc_trim_library = library
    _malloc_trim_function = function
    return function


def trim_process_memory() -> bool:
    """Ask glibc to return currently free heap pages to the operating system."""
    function = _resolve_malloc_trim()
    if function is None:
        return False
    try:
        return bool(function(0))
    except (OSError, ValueError):
        return False


__all__ = [
    "DEFAULT_GLIBC_ARENA_MAX",
    "bootstrap_allocator",
    "trim_process_memory",
]
