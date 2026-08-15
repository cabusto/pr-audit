from __future__ import annotations

from pathlib import Path
from pkgutil import extend_path

__version__ = "0.1.0"

__path__ = extend_path(__path__, __name__)
_src_package = Path(__file__).resolve().parent.parent / "src" / "pr_audit"
if _src_package.is_dir():
    __path__.append(str(_src_package))
