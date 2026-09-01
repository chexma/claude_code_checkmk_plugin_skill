#!/usr/bin/env python3
# =============================================================================
# CheckMK Bakery Plugin Template — v2_unstable (CheckMK 2.5+)
# =============================================================================
#
# UNSTABLE API: cmk.bakery.v2_unstable may change before it stabilizes
# (planned for 2.6, per Werk #18600). For CheckMK 2.4, or for stable 2.5
# production plugins, use bakery_plugin.py (v1) instead.
#
# This template creates a Bakery plugin for distributing agent plugins
# via the Agent Bakery (commercial editions), using the new plugin family
# layout introduced in 2.5.
#
# Installation:
#   ~/local/lib/python3/cmk_addons/plugins/<family>/bakery/my_plugin.py
#
# Required companion files:
#   1. Agent plugins in ~/local/lib/python3/cmk_addons/plugins/<family>/agent/
#   2. AgentConfig ruleset in ~/local/lib/python3/cmk_addons/plugins/<family>/rulesets/
#
# =============================================================================

import json
from pathlib import Path
from typing import TypedDict, List

from cmk.bakery.v2_unstable import (
    # Operating systems
    OS,
    # Package scriptlet steps
    DebStep,
    RpmStep,
    SolStep,
    # Artifact classes
    Plugin,
    PluginConfig,
    SystemConfig,       # System-wide config files (under /etc)
    SystemBinary,
    Scriptlet,
    WindowsConfigEntry,
    WindowsConfigItems,  # For merging lists in Windows YAML config
    # Secrets (v2_unstable only — replaces raw password-store access)
    Secret,
    # Plugin definition
    BakeryPlugin,
    # Type annotations
    FileGenerator,
    ScriptletGenerator,
    WindowsConfigGenerator,
    # Parameter parsing (v2_unstable only)
    no_op_parser,
)


# =============================================================================
# Configuration
# =============================================================================

# Plugin name - must match the AgentConfig ruleset name
PLUGIN_NAME = "my_plugin"

# Source filenames, relative to this family's agent/ directory
LINUX_PLUGIN = "my_plugin"
WINDOWS_PLUGIN = "my_plugin.ps1"
SOLARIS_PLUGIN = "my_plugin.solaris.ksh"

# Configuration filenames (generated on target host)
LINUX_CONFIG = "my_plugin.json"
WINDOWS_CONFIG_SECTION = "my_plugin"  # Section name in check_mk.yml


# =============================================================================
# Type Definitions
# =============================================================================

class MyPluginConfig(TypedDict, total=False):
    """
    Type definition matching the AgentConfig ruleset parameters.

    This should mirror the Dictionary elements defined in your ruleset.
    """
    interval: float          # Execution interval in seconds
    api_url: str             # API endpoint URL
    username: str            # Username for authentication
    api_token: Secret        # Secret, resolved by the backend before this runs
    timeout: int             # Request timeout
    verify_ssl: bool         # SSL verification flag


# =============================================================================
# File Generators
# =============================================================================

def get_plugin_files(conf: MyPluginConfig) -> FileGenerator:
    """
    Generate plugin files and configurations for all operating systems.

    Args:
        conf: Configuration dictionary from the ruleset (as parsed by parameter_parser)

    Yields:
        Plugin, PluginConfig, SystemConfig, or SystemBinary artifacts
    """

    interval = conf.get("interval")
    interval_int = int(interval) if interval else None

    # -------------------------------------------------------------------------
    # Linux Plugin
    # -------------------------------------------------------------------------
    yield Plugin(
        base_os=OS.LINUX,
        source=Path(LINUX_PLUGIN),
        target=Path(LINUX_PLUGIN),
        interval=interval_int,
    )

    yield PluginConfig(
        base_os=OS.LINUX,
        lines=_generate_json_config(conf),
        target=Path(LINUX_CONFIG),
        include_header=False,
    )

    # -------------------------------------------------------------------------
    # Windows Plugin
    # -------------------------------------------------------------------------
    yield Plugin(
        base_os=OS.WINDOWS,
        source=Path(WINDOWS_PLUGIN),
        target=Path(WINDOWS_PLUGIN),
        interval=interval_int,
    )

    # -------------------------------------------------------------------------
    # Solaris Plugin (optional)
    # -------------------------------------------------------------------------
    # yield Plugin(
    #     base_os=OS.SOLARIS,
    #     source=Path(SOLARIS_PLUGIN),
    #     target=Path(LINUX_PLUGIN),
    #     interval=interval_int,
    # )

    # -------------------------------------------------------------------------
    # Additional Binaries (optional)
    # -------------------------------------------------------------------------
    # yield SystemBinary(
    #     base_os=OS.LINUX,
    #     source=Path("my_helper_tool"),  # From this family's agent/ directory
    # )

    # -------------------------------------------------------------------------
    # System Configuration Files (optional)
    # -------------------------------------------------------------------------
    # yield SystemConfig(
    #     base_os=OS.LINUX,
    #     lines=["[Unit]", "Description=My Plugin Service"],
    #     target=Path("systemd/system/my_plugin.service"),
    #     include_header=True,
    # )


def _generate_json_config(conf: MyPluginConfig) -> List[str]:
    """Generate JSON configuration for Linux plugin."""
    api_token = conf.get("api_token")
    config = {
        "api_url": conf.get("api_url", ""),
        "username": conf.get("username", ""),
        # Reveal the secret only here, right before it's written out.
        "api_token": api_token.revealed if api_token else "",
        "timeout": conf.get("timeout", 30),
        "verify_ssl": conf.get("verify_ssl", True),
    }
    return json.dumps(config, indent=2).split("\n")


# =============================================================================
# Package Scriptlets
# =============================================================================

def get_scriptlets(conf: MyPluginConfig, aghash: str = "") -> ScriptletGenerator:
    """
    Generate package manager scriptlets (post-install, pre-remove, etc.).

    Note: Do NOT end with 'exit 0' - CheckMK adds more commands after yours.
    """
    postinstall_lines = [f'logger -p local3.info "CheckMK: Installed {PLUGIN_NAME} plugin"']
    preremove_lines = [f'logger -p local3.info "CheckMK: Removing {PLUGIN_NAME} plugin"']
    postremove_lines = [f'logger -p local3.info "CheckMK: Removed {PLUGIN_NAME} plugin"']

    yield Scriptlet(step=DebStep.POSTINST, lines=postinstall_lines)
    yield Scriptlet(step=DebStep.PRERM, lines=preremove_lines)
    yield Scriptlet(step=DebStep.POSTRM, lines=postremove_lines)

    yield Scriptlet(step=RpmStep.POST, lines=postinstall_lines)
    yield Scriptlet(step=RpmStep.PREUN, lines=preremove_lines)
    yield Scriptlet(step=RpmStep.POSTUN, lines=postremove_lines)


# =============================================================================
# Windows Configuration
# =============================================================================

def get_windows_config(conf: MyPluginConfig, aghash: str = "") -> WindowsConfigGenerator:
    """Generate Windows agent YAML configuration entries."""
    yield WindowsConfigEntry(
        path=[WINDOWS_CONFIG_SECTION, "api_url"],
        content=conf.get("api_url", ""),
    )
    yield WindowsConfigEntry(
        path=[WINDOWS_CONFIG_SECTION, "username"],
        content=conf.get("username", ""),
    )
    yield WindowsConfigEntry(
        path=[WINDOWS_CONFIG_SECTION, "timeout"],
        content=conf.get("timeout", 30),
    )
    yield WindowsConfigEntry(
        path=[WINDOWS_CONFIG_SECTION, "verify_ssl"],
        content=conf.get("verify_ssl", True),
    )


# =============================================================================
# Plugin Definition (v2_unstable: discovered, not registered at import time)
# =============================================================================

bakery_plugin_my_plugin = BakeryPlugin(
    name=PLUGIN_NAME,
    parameter_parser=no_op_parser,
    files_function=get_plugin_files,
    scriptlets_function=get_scriptlets,
    windows_config_function=get_windows_config,
)
