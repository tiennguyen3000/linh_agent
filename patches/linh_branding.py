"""Linh branding — single source of truth for Linh identity inside the core.

Linh — personal AI engineering agent of Linh Nguyen, running on the Hermes core
architecture (Nous Research).

This module is part of the Linh rebrand layer. Core logic is untouched: only the
display/identity surfaces import from here, so re-branding Linh never requires
editing core behaviour again. See Linh/docs/REBRAND.md.
"""

LINH_NAME = "Linh"
LINH_EXPANSION = ""  # no expansion for this distribution (KTAI had "Khánh Tiển AI")
LINH_OWNER = "Linh Nguyen"
LINH_TAGLINE = "Personal AI Engineering Agent"
LINH_VERSION = "1.0.0"
LINH_CORE = "Hermes core (Nous Research)"

# ANSI-Shadow wordmark "LINH" (Rich markup; colours are the Linh palette).
LINH_LOGO = """[bold #38BDF8]██╗      ██╗ ███╗   ██╗ ██╗  ██╗[/]
[bold #38BDF8]██║      ██║ ████╗  ██║ ██║  ██║[/]
[#22D3EE]██║      ██║ ██╔██╗ ██║ ███████║[/]
[#22D3EE]██║      ██║ ██║╚██╗██║ ██╔══██║[/]
[#2563EB]███████╗ ██║ ██║ ╚████║ ██║  ██║[/]
[#2563EB]╚══════╝ ╚═╝ ╚═╝  ╚═══╝ ╚═╝  ╚═╝[/]"""

# Hero art: a "chip" motif — reads as engineering, pure box/block glyphs (safe in
# any terminal, unlike braille art). Rendered in the banner's left column.
LINH_HERO = """[#22D3EE]      ╔═══════════════╗[/]
[#22D3EE]      ║  ▓▓▓▓▓▓▓▓▓▓▓  ║[/]
[#38BDF8]      ║   ▓ Linh ▓    ║[/]
[#38BDF8]      ║   ▓▓▓▓▓▓▓▓▓   ║[/]
[#2563EB]      ╚═══════════════╝[/]"""

# Display branding consumed by hermes_cli/skin_engine.py and the CLI.
# Keys match the core's branding contract.
LINH_BRANDING = {
    "agent_name": LINH_NAME,
    "welcome": f"{LINH_NAME} ready — {LINH_TAGLINE} of {LINH_OWNER}. Type your message or /help for commands.",
    "goodbye": "Linh signing off ⚡",
    "response_label": " ⚡ Linh ",
    "prompt_symbol": "❯",
    "help_header": "(⚡) Available Commands",
    "tiny_line": "⚡ Linh",
}

# Spinner wings / verbs — engineering flavour, distinct from the Hermes gold persona.
LINH_SPINNER = {
    "waiting_faces": ["(⚡)", "(⌬)", "(▚)", "(⚙)", "(<>)"],
    "thinking_faces": ["(⚡)", "(⚙)", "(⌬)", "(▞)", "(<>)"],
    "thinking_verbs": [
        "inspecting the repo", "tracing the call path", "reading the diff",
        "running the tests", "checking the premise", "profiling the hot path",
        "reviewing the invariants", "wiring the tools"],
}

LINH_TOOL_PREFIX = "⚡"


def display_name() -> str:
    """Name with the optional expansion — this distribution has none."""
    return f"{LINH_NAME} ({LINH_EXPANSION})" if LINH_EXPANSION else LINH_NAME


def version_label(core_version: str = "", release_date: str = "") -> str:
    """Version label for banners: Linh's own version first, core version second."""
    seat = f"{LINH_NAME} v{LINH_VERSION}"
    if core_version:
        seat += f" · core {core_version}"
        if release_date:
            seat += f" ({release_date})"
    return seat


def identity_lines() -> list:
    """Human-readable identity card (used by ``linh identity``)."""
    return [
        f"Name        : {display_name()}",
        f"Role        : {LINH_TAGLINE}",
        f"Owner       : {LINH_OWNER}",
        f"Core        : {LINH_CORE}",
        f"Linh version: {LINH_VERSION}",
    ]
