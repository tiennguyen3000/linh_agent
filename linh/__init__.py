"""Linh — Personal AI Engineering Agent.

Owner: Linh Nguyen. Built on the Hermes core architecture (Nous Research).
The `linh` command dispatches Linh-native subcommands and passes everything else
through to the core CLI, so the full capability surface (gateway, cron, tools,
delegation, desktop/TUI) is preserved.
"""

import os
from pathlib import Path

LINH_NAME = "Linh"
LINH_EXPANSION = ""  # no expansion for this distribution
LINH_OWNER = "Linh Nguyen"
LINH_VERSION = "1.0.0"

ROOT = Path(__file__).resolve().parent.parent
CORE = ROOT / "core"
IDENTITY = ROOT / "identity"
VENV_BIN = ROOT / "venv" / "bin"


def linh_home() -> Path:
    """Linh data home (~/.linh unless LINH_HOME says otherwise)."""
    return Path(os.environ.get("LINH_HOME") or (Path.home() / ".linh")).expanduser()


def core_entry() -> Path:
    """The core CLI entry the passthrough execs (Linh's own venv copy)."""
    return VENV_BIN / "hermes"
