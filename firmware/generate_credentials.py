Import("env")

import subprocess
import sys
from pathlib import Path

project_dir = Path(env.subst("$PROJECT_DIR"))
subprocess.run(
    [sys.executable, str(project_dir / "configure_wifi.py")],
    cwd=project_dir,
    check=True,
)
