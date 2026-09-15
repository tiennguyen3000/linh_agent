#!/usr/bin/env python3
"""Linh rebrand patcher — surgical, idempotent, manifest-driven.

Applies the Linh identity layer to the forked core at ~/Linh/core.

Design rules (why this file exists instead of a global sed):
  * Only IDENTITY / USER-FACING surfaces are rewritten. Internal module names
    (hermes_cli, hermes_state, ...) and HERMES_* env vars are left intact: they
    are the runtime API that 4k+ files, the plugin compat layer and the test
    suite depend on. Renaming them buys cosmetics and costs the ability to merge
    upstream fixes. See Linh/docs/REBRAND.md for the full rationale.
  * Every edit is an explicit (file, old, new) pair. If an anchor is missing or
    ambiguous the run FAILS LOUDLY — no silent partial rebrand.
  * Idempotent: re-running after an upstream merge re-applies only what is gone.
  * Writes an auditable diff to patches/rebrand.patch and a JSON manifest.
"""

from __future__ import annotations

import difflib
import json
import subprocess
import sys
from pathlib import Path

LINH_ROOT = Path(__file__).resolve().parent.parent
CORE = LINH_ROOT / "core"
PATCH_DIR = LINH_ROOT / "patches"
# Canonical copy of the branding module. It does not exist upstream (~/.hermes/hermes-agent
# has no linh_branding.py), so a rebuild from the pristine Hermes tree must materialise it —
# otherwise every display import added by this manifest fails at the branding gate below.
BRANDING_SRC = PATCH_DIR / "linh_branding.py"

# ── Identity text ─────────────────────────────────────────────────────────────
# The behaviour spec after the identity clause is preserved verbatim on purpose:
# Linh inherits Hermes' reply-sizing / no-filler contract, only the identity changes.
_ORIG_ID = (
    '    "You are Hermes Agent, built by Nous Research. Be direct: match the length of your reply to the weight of the ask "'
)
_NEW_ID = (
    '    "You are Linh — the personal AI engineering agent of Linh Nguyen, running on the '
    'Hermes core architecture by Nous Research. You are an engineering partner, not a chatbot: read the real code '
    'before claiming anything, verify with real tool output, never fabricate a result. Be direct: match the length '
    'of your reply to the weight of the ask "'
)

_ORIG_GUIDANCE = (
    '    "You run on Hermes Agent (by Nous Research). When the user needs help with Hermes itself — configuring, "\n'
    '    "setting up, using, extending, or troubleshooting it — or when you need to understand your own features, "\n'
    '    "tools, or capabilities, the documentation at https://hermes-agent.nousresearch.com/docs is your "\n'
    '    "authoritative reference and always holds the latest, most up-to-date information. The `hermes-agent` "\n'
    '    "skill has the actual commands and proven workflows — load it with skill_view(name=\'hermes-agent\') "\n'
    '    "before configuring, modifying, or troubleshooting Hermes so you don\'t guess or invent workarounds."'
)
_NEW_GUIDANCE = (
    '    "You run on Linh, a personal AI engineering agent built on the Hermes core by Nous "\n'
    '    "Research. When the user needs help with Linh itself — configuring, setting up, using, extending, or "\n'
    '    "troubleshooting it — or when you need to understand your own features, tools, or capabilities, the `linh` "\n'
    '    "skill holds the Linh-specific commands and conventions: load it with skill_view(name=\'linh\') first. For "\n'
    '    "the underlying core (tools, providers, gateway, cron), the authoritative reference that always holds the "\n'
    '    "latest information is https://hermes-agent.nousresearch.com/docs — check it rather than guessing."'
)

_ORIG_GUIDANCE_NS = (
    '    "You run on Hermes Agent (by Nous Research). When the user needs help with Hermes itself — configuring, "\n'
    '    "setting up, using, extending, or troubleshooting it — or when you need to understand your own features, "\n'
    '    "tools, or capabilities, the documentation at https://hermes-agent.nousresearch.com/docs is the "\n'
    '    "authoritative reference and always holds the latest, most up-to-date information. Point the user there "\n'
    '    "(or read it yourself if you have a way to fetch web content)."'
)
_NEW_GUIDANCE_NS = (
    '    "You run on Linh, a personal AI engineering agent built on the Hermes core by Nous "\n'
    '    "Research. When the user needs help with Linh itself — configuring, setting up, using, extending, or "\n'
    '    "troubleshooting it — or when you need to understand your own features, tools, or capabilities, answer from "\n'
    '    "the installed skills and config. For the underlying core, the authoritative and always-current reference "\n'
    '    "is https://hermes-agent.nousresearch.com/docs — point the user there."'
)

_SOUL_ORIG_COMMENT = (
    "# Kept identical to agent/prompt_builder.py's DEFAULT_AGENT_IDENTITY: _ensure_default_soul_md()"
)
_SOUL_NEW_COMMENT = (
    "# Linh: kept identical to agent/prompt_builder.py's DEFAULT_AGENT_IDENTITY (Linh variant): _ensure_default_soul_md()"
)

_SOUL_ORIG = (
    '    "You are Hermes Agent, built by Nous Research. Be direct: match the length of your reply to the weight of "\n'
    '    "the ask — a one-line question gets a one-line answer, and finished work gets a short report of what "\n'
    '    "changed, what\'s verified, and what\'s left, never a replay of the process. No filler (\\"Great question,\\" "\n'
    '    "\\"I\'d be happy to\\"), no restating the request back, no re-summarizing what you already said, no narrating "\n'
    '    "tool calls the user can see. Plain claims over adjectives; when unsure, say so plainly. Agree because it\'s "\n'
    '    "right, not because the user said it. Depth is earned — give it when the user asks for detail, teaches, or "\n'
    '    "the stakes demand it, not by default."'
)
_SOUL_NEW = (
    '    "You are Linh — the personal AI engineering agent of Linh Nguyen, running on the "\n'
    '    "Hermes core architecture by Nous Research. You are an engineering partner: read the real code, verify with "\n'
    '    "real tool output, never fabricate a result. Be direct: match the length of your reply to the weight of "\n'
    '    "the ask — a one-line question gets a one-line answer, and finished work gets a short report of what "\n'
    '    "changed, what\'s verified, and what\'s left, never a replay of the process. No filler (\\"Great question,\\" "\n'
    '    "\\"I\'d be happy to\\"), no restating the request back, no re-summarizing what you already said, no narrating "\n'
    '    "tool calls the user can see. Plain claims over adjectives; when unsure, say so plainly. Agree because it\'s "\n'
    '    "right, not because the user said it. Depth is earned — give it when the user asks for detail, teaches, or "\n'
    '    "the stakes demand it, not by default."'
)

_SCAFFOLD_ORIG = (
    '    "# Hermes Agent Persona\\n\\n<!--\\nThis file defines the agent\'s personality and tone.\\n"\n'
    '    "The agent will embody whatever you write here.\\nEdit this to customize how Hermes communicates with you.\\n\\n"'
)
_SCAFFOLD_NEW = (
    '    "# Linh Persona\\n\\n<!--\\nThis file defines the agent\'s personality and tone.\\n"\n'
    '    "The agent will embody whatever you write here.\\nEdit this to customize how Linh communicates with you.\\n\\n"'
)

# ── The manifest ──────────────────────────────────────────────────────────────
REPLACEMENTS = [
    # 1. Core identity line in the system prompt (stable tier).
    {"file": "agent/prompt_builder.py", "old": _ORIG_ID, "new": _NEW_ID, "why": "system-prompt identity"},
    # 2. Self-help guidance (with + without the skills toolset).
    {"file": "agent/prompt_builder.py", "old": _ORIG_GUIDANCE, "new": _NEW_GUIDANCE, "why": "self-knowledge pointer"},
    {"file": "agent/prompt_builder.py", "old": _ORIG_GUIDANCE_NS, "new": _NEW_GUIDANCE_NS, "why": "self-knowledge pointer (no skills)"},
    # 3. Let Linh's own skill drive the rich guidance variant.
    {
        "file": "agent/system_prompt.py",
        "old": '    if "skill_view" in (agent.valid_tool_names or set()) and "- hermes-agent:" in skills_prompt:',
        "new": '    if "skill_view" in (agent.valid_tool_names or set()) and (\n'
               '            "- linh:" in skills_prompt or "- hermes-agent:" in skills_prompt\n'
               '    ):',
        "why": "Linh skill drives guidance variant",
    },
    # 4. Auto-seeded persona (users with no SOUL.md).
    {"file": "hermes_cli/default_soul.py", "old": _SOUL_ORIG_COMMENT, "new": _SOUL_NEW_COMMENT, "why": "seed comment truth"},
    {"file": "hermes_cli/default_soul.py", "old": _SOUL_ORIG, "new": _SOUL_NEW, "why": "seeded SOUL.md text"},
    {"file": "hermes_cli/default_soul.py", "old": _SCAFFOLD_ORIG, "new": _SCAFFOLD_NEW, "why": "seeded SOUL.md scaffold"},
    # 5. Banner: Linh wordmark + hero art + version label.
    {
        "file": "hermes_cli/banner.py",
        "old": "from hermes_cli import __version__ as VERSION, __release_date__ as RELEASE_DATE",
        "new": ("from hermes_cli import __version__ as VERSION, __release_date__ as RELEASE_DATE\n"
                "from linh_branding import LINH_HERO, LINH_LOGO, version_label as _linh_version_label"),
        "why": "import Linh branding",
    },
    {
        "file": "hermes_cli/banner.py",
        "old": '    left_lines = ["", getattr(_bskin, "banner_hero", None) or HERMES_CADUCEUS, ""]',
        "new": '    left_lines = ["", getattr(_bskin, "banner_hero", None) or LINH_HERO, ""]',
        "why": "banner hero art",
    },
    {
        "file": "hermes_cli/banner.py",
        "old": '        console.print(getattr(_bskin, "banner_logo", None) or HERMES_AGENT_LOGO)',
        "new": '        console.print(getattr(_bskin, "banner_logo", None) or LINH_LOGO)',
        "why": "banner wordmark logo",
    },
    {"file": "hermes_cli/banner.py", "old": '    base = f"Hermes Agent v{VERSION} ({RELEASE_DATE})"',
     "new": '    base = _linh_version_label(VERSION, RELEASE_DATE)', "why": "banner version label"},
    # 6. Fallback branding for the built-in default skin.
    {
        "file": "hermes_cli/skin_engine.py",
        "old": "from hermes_constants import get_hermes_home",
        "new": ("from hermes_constants import get_hermes_home\nfrom linh_branding import LINH_BRANDING, LINH_SPINNER"),
        "why": "import Linh branding",
    },
    {
        "file": "hermes_cli/skin_engine.py",
        "old": '_HERMES_BRANDING: Dict[str, str] = _branding(\n    "Hermes", "⚕", "Goodbye! ⚕", prompt="❯", help_header="(^_^)? Available Commands")',
        "new": '_HERMES_BRANDING: Dict[str, str] = dict(LINH_BRANDING)  # Linh identity (see linh_branding)',
        "why": "default-skin branding",
    },
    # 7. LINH_HOME as a first-class home override (identity at the runtime level).
    {
        "file": "hermes_constants.py",
        "old": ('    override = get_hermes_home_override()\n'
                '    if override:\n'
                '        return Path(override)\n'
                '    if not os.environ.get("HERMES_HOME", "").strip():'),
        "new": ('    override = get_hermes_home_override()\n'
                '    if override:\n'
                '        return Path(override)\n'
                '    # Linh layer: LINH_HOME is the canonical home for the Linh distribution and wins\n'
                '    # over HERMES_HOME (the core mechanism it is implemented on top of).\n'
                '    _linh_home = os.environ.get("LINH_HOME", "").strip()\n'
                '    if _linh_home:\n'
                '        return Path(_linh_home)\n'
                '    if not os.environ.get("HERMES_HOME", "").strip():'),
        "why": "LINH_HOME override",
    },
    # 8. CLI user-facing strings.
    {"file": "cli.py", "old": '        tiny_line = "⚕ NOUS HERMES"', "new": '        tiny_line = "⚡ Linh"', "why": "banner tiny line"},
    {
        "file": "cli.py",
        "old": ('        tiny_line = _skin.get_branding("agent_name", "Hermes Agent") if _skin else "Hermes Agent"'),
        "new": '        tiny_line = _skin.get_branding("agent_name", "Linh") if _skin else "Linh"',
        "why": "banner tiny line (fallback)",
    },
    {"file": "cli.py", "old": '        version_line = f"Hermes Agent v{_version} ({_release_date})"',
     "new": '        version_line = _linh_version_label(_version, _release_date)',
     "why": "fast-startup banner version"},
    {"file": "cli.py", "old": '        _welcome_text = "Welcome to Hermes Agent! Type your message or /help for commands."',
     "new": '        _welcome_text = "Linh ready — Personal AI Engineering Agent. Type your message or /help for commands."',
     "why": "welcome fallback"},
    {"file": "cli.py", "old": '"""Hermes Agent CLI — interactive terminal interface (``python cli.py --help`` for usage)."""',
     "new": '"""Linh CLI — interactive terminal interface for the Linh personal AI engineering agent."""',
     "why": "module docstring"},
    {"file": "cli.py", "old": '    """Interactive REPL for the Hermes Agent."""',
     "new": '    """Interactive REPL for Linh."""', "why": "class docstring"},
    {"file": "cli.py", "old": "    Hermes Agent CLI - Interactive AI Assistant",
     "new": "    Linh — Personal AI Engineering Agent (CLI)", "why": "help text"},
    # 9. Pin Linh's own skill as essential (like hermes-agent): the system prompt's
    #    guidance slot depends on it being installed, so it must not be disable-able.
    {
        "file": "agent/skill_utils.py",
        "old": 'ESSENTIAL_SKILLS: frozenset = frozenset({"hermes-agent"})',
        "new": 'ESSENTIAL_SKILLS: frozenset = frozenset({"hermes-agent", "linh"})  # "linh": pinned by the Linh layer',
        "why": "Linh skill is essential",
    },
]

# ── Test-expectation alignment (identity strings ONLY) ────────────────────────
# These upstream tests assert the Hermes identity TEXT, not behaviour. A fork that
# changes the identity must move them, or its own suite is knowingly red. Rule for
# this list: only string expectations about the agent's name/identity may be edited —
# never an assertion about behaviour, and never a weakened assertion.
TEST_ALIGNMENT = [
    {"file": "tests/hermes_cli/test_banner.py",
     "old": '    assert "Hermes Agent v" in raw, "Version label missing from title"',
     "new": '    assert "Linh v" in raw, "Version label missing from title"',
     "why": "test alignment: banner title identity"},
    {"file": "tests/hermes_cli/test_skin_engine.py",
     "old": '        assert skin.get_branding("agent_name") == "Hermes Agent"',
     "new": '        assert skin.get_branding("agent_name") == "Linh"',
     "why": "test alignment: default-skin agent name"},
    {"file": "tests/hermes_cli/test_startup_fast_guards.py",
     "old": '    for field in ("Hermes Agent v", "Install directory:", "Python:", "OpenAI SDK:"):',
     "new": '    for field in ("Linh v", "Install directory:", "Python:", "OpenAI SDK:"):',
     "why": "test alignment: fast --version identity"},
    {"file": "tests/hermes_cli/test_startup_fast_guards.py",
     "old": '    assert "Hermes Agent v" in result.stdout',
     "new": '    assert "Linh v" in result.stdout',
     "why": "test alignment: fast --version identity (termux path)"},
    {"file": "tests/agent/test_prompt_builder.py",
     "old": '        assert "Project Context" in result\n        assert "Hermes Agent" in result',
     "new": '        assert "Project Context" in result\n        assert "Linh" in result',
     "why": "test alignment: seeded default persona"},
    {"file": "tests/agent/test_phantom_tool_references.py",
     "old": '        assert "skill_view(name=\'hermes-agent\')" in HERMES_AGENT_HELP_GUIDANCE',
     "new": '        assert "skill_view(name=\'linh\')" in HERMES_AGENT_HELP_GUIDANCE',
     "why": "test alignment: guidance points at the Linh skill"},
]

# cli.py needs the version-label import next to the other hermes_cli imports.
CLI_IMPORT_OLD = "from hermes_cli.banner import format_banner_version_label"
CLI_IMPORT_NEW = ("from hermes_cli.banner import format_banner_version_label\n"
                  "from linh_branding import version_label as _linh_version_label")


def write_audit(applied: list[dict], touched: dict) -> None:
    """Write the authoritative manifest + a full patch against the pristine upstream.

    The patch must be CUMULATIVE: regenerating it from only this run's edits would
    silently drop every previously applied edit from the audit trail (the second run
    diffed 5 edits and lost the first 20).
    """
    PATCH_DIR.mkdir(parents=True, exist_ok=True)
    pristine_root = Path.home() / ".hermes" / "hermes-agent"
    all_specs = REPLACEMENTS + TEST_ALIGNMENT
    files = sorted({s["file"] for s in all_specs} | {str(p.relative_to(CORE)) for p in touched})

    diffs: list[str] = []
    for rel in files:
        cur_path = CORE / rel
        if not cur_path.is_file():
            continue
        cur = cur_path.read_text(encoding="utf-8").splitlines(keepends=True)
        base_path = pristine_root / rel
        if base_path.is_file():
            base = base_path.read_text(encoding="utf-8").splitlines(keepends=True)
        else:  # new file added by the Linh layer
            base = []
        diff = "".join(difflib.unified_diff(base, cur, fromfile=f"a/{rel}", tofile=f"b/{rel}"))
        if diff:
            diffs.append(diff)

    header = (
        "# Linh rebrand patch — the complete Linh-vs-upstream diff for the core.\n"
        "# Generated by scripts/rebrand_core.py (cumulative, diffed against the pristine\n"
        "# upstream checkout at ~/.hermes/hermes-agent). Regenerate after any core edit:\n"
        "#   python3 scripts/rebrand_core.py\n\n"
    )
    (PATCH_DIR / "rebrand.patch").write_text(header + "".join(diffs), encoding="utf-8")
    (PATCH_DIR / "rebrand-manifest.json").write_text(
        json.dumps({
            "linh_version": "1.0.0",
            "pristine_base": str(pristine_root),
            "edits": [{"file": s["file"], "why": s["why"]} for s in all_specs],
            "applied_this_run": applied,
            "files_in_patch": files,
        }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"audit written: patches/rebrand.patch ({len(diffs)} files), patches/rebrand-manifest.json")


def main() -> int:
    problems: list[str] = []
    applied: list[dict] = []
    touched: dict[Path, str] = {}

    # 0. Materialise the branding module first: the manifest's edits import it.
    if BRANDING_SRC.is_file():
        branding_path = CORE / "linh_branding.py"
        want = BRANDING_SRC.read_text(encoding="utf-8")
        have = branding_path.read_text(encoding="utf-8") if branding_path.is_file() else None
        if have != want:
            touched[branding_path] = want
            applied.append({
                "file": "linh_branding.py",
                "why": "branding module (created/refreshed from patches/linh_branding.py)",
            })
    else:
        problems.append(f"missing canonical branding module: {BRANDING_SRC}")

    # cli.py must be able to resolve _linh_version_label before any string edit lands.
    cli_path = CORE / "cli.py"
    cli_text = cli_path.read_text(encoding="utf-8")
    if CLI_IMPORT_NEW not in cli_text:
        if CLI_IMPORT_OLD not in cli_text:
            problems.append("cli.py: version-label import anchor not found")
        else:
            cli_text = cli_text.replace(CLI_IMPORT_OLD, CLI_IMPORT_NEW, 1)
            touched[cli_path] = cli_text
            applied.append({"file": "cli.py", "why": "import Linh version label"})

    for spec in REPLACEMENTS + TEST_ALIGNMENT:
        path = CORE / spec["file"]
        if not path.is_file():
            problems.append(f"{spec['file']}: missing")
            continue
        text = touched.get(path) or path.read_text(encoding="utf-8")
        if spec["new"] in text:
            continue  # already branded — idempotent
        hits = text.count(spec["old"])
        if hits != 1:
            problems.append(f"{spec['file']}: anchor found {hits}× ({spec['why']})")
            continue
        touched[path] = text.replace(spec["old"], spec["new"], 1)
        applied.append({"file": spec["file"], "why": spec["why"]})

    if problems:
        print("REBRAND FAILED — nothing written:")
        for p in problems:
            print("  ✗", p)
        return 1

    for path, new_text in touched.items():
        path.write_text(new_text, encoding="utf-8")

    write_audit(applied, touched)

    print(f"Linh rebrand applied: {len(applied)} edits across {len(touched)} files")
    for a in applied:
        print(f"  ✓ {a['file']:36s} {a['why']}")

    # Syntax gate: a rebrand that breaks imports is worse than no rebrand.
    # Skipped when nothing was touched (a plain re-run) — py_compile with an empty
    # file list exits non-zero, which would make an idempotent re-run look failed.
    if touched:
        bad = subprocess.run(
            [sys.executable, "-m", "py_compile", *[str(p) for p in touched]],
            capture_output=True, text=True)
        if bad.returncode != 0:
            print("SYNTAX CHECK FAILED:\n" + bad.stderr)
            return 1
        print("syntax check: OK")
    else:
        print("syntax check: skipped (already up to date)")

    # Import gate for the branding module itself.
    chk = subprocess.run(
        [sys.executable, "-c", "import linh_branding as b; print(b.LINH_NAME, b.version_label('0.21.1'))"],
        cwd=str(CORE), capture_output=True, text=True)
    print("branding import:", (chk.stdout or chk.stderr).strip())
    return 0 if chk.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
