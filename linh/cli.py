"""Linh CLI — Linh-native subcommands + faithful passthrough to the core CLI.

  linh                     interactive session (core CLI)
  linh <anything else>     passed through to the core, argv[0] = "linh"
  linh version             Linh + core version
  linh identity            identity card, home, team roster
  linh agents [role]       list the engineering agents / show one charter
  linh team <role> <task>  delegate a task to one engineering agent
  linh selfcheck           verify the Linh installation end to end
  linh home                print the Linh data home
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from . import CORE, IDENTITY, LINH_NAME, LINH_VERSION, ROOT, core_entry, linh_home
from . import brain


def _print_version() -> int:
    from linh_branding import version_label

    print(f"{LINH_NAME} v{LINH_VERSION} — Personal AI Engineering Agent")
    print(f"core: {version_label(brain._core_version(), brain._core_release())}")
    print(f"home: {linh_home()}")
    print(f"core source: {CORE}")
    return 0


def _print_agents(argv: list[str]) -> int:
    if not argv:
        print(f"{LINH_NAME} engineering agents ({brain.agents_dir()}):\n")
        for role in brain.list_roles():
            print(f"  {role['name']:9s} {role['title']}")
            print(f"            {role['mission']}")
            print(f"            output: {role['output']}")
        print(f"\nGọi: linh team <role> \"<task>\"")
        return 0
    role = brain.load_role(argv[0])
    if not role:
        print(f"unknown role: {argv[0]!r}. available: {', '.join(r['name'] for r in brain.list_roles())}")
        return 2
    print(role["body"].strip())
    print(f"\n(source: {role['path']})")
    return 0


def _team(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print('usage: linh team <role> "<task>"   |   linh team <role> --show')
        print(f"roles: {', '.join(r['name'] for r in brain.list_roles())}")
        return 0 if argv else 2
    role = brain.load_role(argv[0])
    if not role:
        print(f"unknown role: {argv[0]!r}. available: {', '.join(r['name'] for r in brain.list_roles())}")
        return 2
    rest = argv[1:]
    if not rest or rest[0] in ("--show", "--dry-run"):
        print(brain.build_team_prompt(role, "[task chưa gán]"))
        return 0

    prompt = brain.build_team_prompt(role, " ".join(rest))
    if os.environ.get("LINH_TEAM_DRY_RUN") == "1":
        print(prompt)
        return 0

    print(f"── {LINH_NAME} · {role['title']} ─────────────────────────────")
    # A delegated agent runs in its own process: separate session, full toolset,
    # and it cannot corrupt the calling shell's state.
    proc = subprocess.run([str(core_entry()), "chat", "-q", prompt])
    return proc.returncode


def _selfcheck() -> int:
    """Verify the installation the way a user would feel a failure."""
    ok = True
    checks: list[tuple[str, bool, str]] = []

    home = linh_home()
    checks.append(("Linh home exists", home.is_dir(), str(home)))
    checks.append(("SOUL.md (persona)", (home / "SOUL.md").is_file(), str(home / "SOUL.md")))
    checks.append(("config.yaml", (home / "config.yaml").is_file(), str(home / "config.yaml")))
    checks.append(("roles (6 agents)", len(brain.list_roles()) == 6,
                   f"{len(brain.list_roles())} found in {brain.agents_dir()}"))
    checks.append(("core source", (CORE / "hermes_cli").is_dir(), str(CORE)))
    checks.append(("venv", (ROOT / "venv/bin/python3").is_file(), str(ROOT / "venv")))
    checks.append(("core entry", core_entry().is_file(), str(core_entry())))

    def _skin_ok() -> tuple[bool, str]:
        """Resolve the skin the way the core does at startup: config → init → load.

        Checking get_active_skin() alone is misleading — the module-level default is
        "default" until init_skin_from_config() runs, so it would pass while the
        configured skin was never actually loaded.
        """
        try:
            sys.path.insert(0, str(CORE))
            from hermes_cli.config import load_config
            from hermes_cli.skin_engine import get_active_skin, init_skin_from_config
            cfg = load_config()
            init_skin_from_config(cfg)
            skin = get_active_skin()
            configured = (cfg.get("display") or {}).get("skin", "default")
            ok = configured == "linh" and skin.name == "linh" and skin.get_branding("agent_name", "") == LINH_NAME
            return ok, (f"configured={configured!r} loaded={skin.name!r} "
                        f"agent_name={skin.get_branding('agent_name', '')!r}")
        except Exception as exc:  # noqa: BLE001
            return False, f"skin load failed: {exc}"

    def _identity_ok() -> tuple[bool, str]:
        try:
            sys.path.insert(0, str(CORE))
            from agent.prompt_builder import DEFAULT_AGENT_IDENTITY
            return "You are Linh" in DEFAULT_AGENT_IDENTITY, "system-prompt identity"
        except Exception as exc:  # noqa: BLE001
            return False, f"identity import failed: {exc}"

    def _isolation_ok() -> tuple[bool, str]:
        # A Linh run must never resolve its home to ~/.hermes.
        resolved = str(home.resolve())
        return "hermes-agent" not in resolved and resolved != str(Path.home() / ".hermes"), resolved

    for fn in (_skin_ok, _identity_ok, _isolation_ok):
        try:
            passed, detail = fn()
        except Exception as exc:  # noqa: BLE001
            passed, detail = False, str(exc)
        checks.append((fn.__name__.strip("_").replace("_", " "), passed, detail))

    print(f"{LINH_NAME} selfcheck")
    for name, passed, detail in checks:
        ok &= passed
        print(f"  {'✓' if passed else '✗'} {name:24s} {detail}")
    print("\nRESULT:", "ALL GOOD" if ok else "FAILURES ABOVE")
    return 0 if ok else 1


# ── Linh-native dispatch (everything else goes to the core) ───────────────────
_TABLE = {
    "version": lambda argv: _print_version(),
    "--version": lambda argv: _print_version(),
    "-V": lambda argv: _print_version(),
    "identity": lambda argv: (print(brain.identity_card()), 0)[1],
    "agents": _print_agents,
    "roles": _print_agents,
    "team": _team,
    "selfcheck": lambda argv: _selfcheck(),
    "home": lambda argv: (print(linh_home()), 0)[1],
}


def passthrough(argv: list[str]) -> int:
    """Exec the core CLI with argv[0]='linh' — full fidelity, same process image."""
    entry = core_entry()
    if entry.is_file():
        os.execv(str(entry), ["linh", *argv])  # replaces this process
    # Fallback: no venv entry (e.g. source tree without setup_venv.py run).
    sys.path.insert(0, str(CORE))
    from hermes_cli.main import main as core_main

    sys.argv = ["linh", *argv]
    sys.exit(core_main())


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in _TABLE:
        return int(_TABLE[argv[0]](argv[1:]) or 0)
    return passthrough(argv)


if __name__ == "__main__":
    raise SystemExit(main())
