#!/usr/bin/env python3
"""Linh home seeder — builds ~/.linh so Linh starts capable, not empty.

Two situations:

  * A Hermes home exists (~/.hermes) — the capability surface (config, credentials,
    skills, memories, plugins) is inherited, then the Linh identity layer is
    installed on top.
  * No Hermes home (fresh machine) — nothing to inherit; the identity layer and
    empty runtime dirs are still installed, plus a default config.yaml written by
    the core itself (so `linh` boots instead of failing on a missing config).
    Credentials still have to be added: `linh setup`, or edit ~/.linh/.env.

Deliberately NOT copied: state.db, session transcripts, kanban board, history and
caches — Linh starts with its own clean session history. The source home is only
ever read.

Re-runnable: identity files are overwritten (they are generated from the repo),
config/credentials/skills are only copied when absent unless --force.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IDENTITY = ROOT / "identity"
SRC_HOME = Path.home() / ".hermes"
DST_HOME = Path(os.environ.get("LINH_HOME") or (Path.home() / ".linh"))
VENV_PY = ROOT / "venv" / "bin" / "python3"

# Files the user chose to inherit: without these Linh cannot run at all.
INHERIT_FILES = ("config.yaml", ".env", "auth.json", "google_token.json", "google_client_secret.json")
INHERIT_DIRS = ("skills", "memories", "plugins")
# Fresh empty dirs so first-run logging/session writes never race a missing parent.
FRESH_DIRS = ("logs", "sessions", "cron", "cache", "pastes", "plans", "sandboxes", "workspace")

# Identity artefacts: (destination relative to home, source)
IDENTITY_FILES = (
    ("SOUL.md", IDENTITY / "SOUL.md"),
    ("AGENTS.md", IDENTITY / "AGENTS.md"),
)

# Runs on the Linh venv python: the core owns the config schema, so let the core
# write its own defaults instead of hand-rolling YAML that could drift.
DEFAULT_CONFIG_SNIPPET = (
    "import copy;"
    "from hermes_cli.config import DEFAULT_CONFIG, get_config_path, save_config;"
    "cfg = copy.deepcopy(DEFAULT_CONFIG);"
    "cfg.setdefault('display', {});"
    "cfg['display']['skin'] = 'linh';"
    "save_config(cfg);"
    "print(get_config_path())"
)


def step(msg: str) -> None:
    print(f"== {msg}")


def copy_file(src: Path, dst: Path, force: bool) -> str:
    if not src.is_file():
        return f"skip (source missing): {src}"
    if dst.exists() and not force:
        return f"keep existing: {dst}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return f"copied: {dst}"


def seed_default_config() -> None:
    """Write a core-owned default config.yaml when there is nothing to inherit."""
    cfg_path = DST_HOME / "config.yaml"
    if cfg_path.exists():
        print(f"    keep existing: {cfg_path}")
        return
    if not VENV_PY.is_file():
        print("    skip: venv not built yet — run scripts/setup_venv.py, then re-run seeding")
        return
    env = {**os.environ, "LINH_HOME": str(DST_HOME), "HERMES_HOME": str(DST_HOME)}
    env.pop("PYTHONPATH", None)
    try:
        out = subprocess.run(
            [str(VENV_PY), "-c", DEFAULT_CONFIG_SNIPPET],
            cwd=str(ROOT / "core"), env=env, capture_output=True, text=True, check=True,
        )
        print(f"    wrote default config: {out.stdout.strip()}")
        print("    add credentials next:  linh setup   (or edit ~/.linh/.env)")
    except subprocess.CalledProcessError as exc:
        print(f"    FAILED to write default config: {(exc.stderr or '').strip()[-300:]}")


def ensure_skin() -> None:
    """Force display.skin=linh.

    A home seeded from Hermes inherits `display.skin: default`, which makes
    `linh selfcheck`'s skin check fail and drops the Linh skin. Use the core's own
    config command so the write goes through the normal validated path.
    """
    cfg_path = DST_HOME / "config.yaml"
    if not cfg_path.is_file():
        return
    launcher = ROOT / "venv" / "bin" / "linh"
    if not launcher.is_file():
        print("    skip skin: venv/bin/linh not built yet — run scripts/setup_venv.py, then re-run seeding")
        return
    env = {**os.environ, "LINH_HOME": str(DST_HOME), "HERMES_HOME": str(DST_HOME)}
    env.pop("PYTHONPATH", None)
    try:
        out = subprocess.run(
            [str(launcher), "config", "set", "display.skin", "linh"],
            env=env, capture_output=True, text=True, check=True,
        )
        print(f"    {(out.stdout or '').strip().splitlines()[-1] if out.stdout.strip() else 'display.skin = linh'}")
    except subprocess.CalledProcessError as exc:
        print(f"    WARN could not set display.skin: {((exc.stderr or exc.stdout) or '').strip()[-200:]}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="overwrite inherited config/skills in the home")
    args = ap.parse_args()

    inherit = SRC_HOME.is_dir()
    if not inherit:
        print(f"== no Hermes home at {SRC_HOME} — fresh install, nothing to inherit")

    step(f"seeding Linh home: {DST_HOME}")
    DST_HOME.mkdir(parents=True, exist_ok=True)
    DST_HOME.chmod(0o700)

    for name in FRESH_DIRS:
        (DST_HOME / name).mkdir(parents=True, exist_ok=True)
    step(f"fresh dirs: {', '.join(FRESH_DIRS)}")

    if inherit:
        for name in INHERIT_FILES:
            print("   ", copy_file(SRC_HOME / name, DST_HOME / name, args.force))

        for name in INHERIT_DIRS:
            src, dst = SRC_HOME / name, DST_HOME / name
            if not src.is_dir():
                print(f"    skip (source missing): {src}")
                continue
            if dst.exists() and not args.force:
                print(f"    keep existing: {dst}")
                continue
            shutil.copytree(src, dst, dirs_exist_ok=True)
            print(f"    copied tree: {dst}")

    step("installing Linh identity layer")
    for rel, src in IDENTITY_FILES:
        print("   ", copy_file(src, DST_HOME / rel, True))  # identity is generated: always refresh
    for rel_dir, src_dir in (("agents", IDENTITY / "agents"), ("skins", IDENTITY / "skins")):
        shutil.copytree(src_dir, DST_HOME / rel_dir, dirs_exist_ok=True)
        print(f"    installed: {DST_HOME / rel_dir}  ({len(list(src_dir.glob('*')))} files)")

    skill_src = IDENTITY / "skills" / "linh"
    if skill_src.is_dir():
        shutil.copytree(skill_src, DST_HOME / "skills" / "linh", dirs_exist_ok=True)
        print(f"    installed: {DST_HOME / 'skills/linh'}")

    step("config.yaml")
    seed_default_config()
    ensure_skin()

    # A Linh home must never be a Hermes home.
    assert DST_HOME.resolve() != SRC_HOME.resolve(), "refusing to seed onto the Hermes home"
    step("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
