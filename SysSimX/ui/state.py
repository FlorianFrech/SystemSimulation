# Framework/ui/state.py
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Set
from SysSimX.system.system import System
from SysSimX.core.fmu_comp import FMUComponent

@dataclass
class AppState:
    system: System = field(default_factory=lambda: System("MySystem"))
    selected_models: Set[Path] = field(default_factory=set)         # .mo files
    export_base: Path = Path.cwd()                                  # base dir
    export_subfolder: str = "exported_fmus"
    create_missing_dirs: bool = True

    current_fmu_path: Optional[Path] = None
    registry: Dict[str, FMUComponent] = field(default_factory=dict) # name -> comp

    def export_dir(self) -> Path:
        d = self.export_base / self.export_subfolder if self.export_subfolder else self.export_base
        return d.resolve()
