from __future__ import annotations

from pathlib import Path


_PACKAGE_ROOT = Path(__file__).resolve().parent.parent / "src" / "backend"
__path__ = [str(_PACKAGE_ROOT)]
