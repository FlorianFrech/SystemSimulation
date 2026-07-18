from __future__ import annotations

import sys
from pathlib import Path


LOGO_ROOT = Path(__file__).resolve().parents[1]
if str(LOGO_ROOT) not in sys.path:
    sys.path.insert(0, str(LOGO_ROOT))
