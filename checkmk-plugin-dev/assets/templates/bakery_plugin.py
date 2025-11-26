#!/usr/bin/env python3
# =============================================================================
# CheckMK Bakery Plugin Template
# =============================================================================
#
# This template creates a Bakery plugin for distributing agent plugins
# via the Agent Bakery (commercial editions).
#
# Installation:
#   ~/local/lib/check_mk/base/cee/plugins/bakery/my_plugin.py
#
# Required companion files:
#   1. Agent plugins in ~/local/share/check_mk/agents/plugins/
#   2. Windows plugins in ~/local/share/check_mk/agents/windows/plugins/
#   3. AgentConfig ruleset in ~/local/lib/python3/cmk_addons/plugins/<name>/rulesets/
#
# =============================================================================

import json
from pathlib import Path
from typing import TypedDict, List, Optional

from .bakery_api.v1 import (
    # Operating systems
    OS,
    # Package scriptlet steps
    DebStep,
    RpmStep,
    SolStep,
    # Artifact classes
    Plugin,
    PluginConfig,
    SystemBinary,
    Scriptlet,
    WindowsConfigEntry,
    # Registration
    register,
    # Type annotations
    FileGenerator,
    ScriptletGenerator,
    WindowsConfigGenerator,
    # Helpers
    quote_shell_string,
)


# =============================================================================
# Configuration
# =============================================================================

# Plugin name - must match the AgentConfig ruleset name
PLUGIN_NAME = "my_plugin"

# Source filenames (in ~/local/share/check_mk/agents/plugins/)
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
    api_url: str            # API endpoint URL
    username: str           # Username for authentication
    timeout: int            # Request timeout
    verify_ssl: bool        # SSL verification flag


# =============================================================================
# File Generators
# =============================================================================

def get_plugin_files(conf: MyPluginConfig) -> FileGenerator:
    """
    Generate plugin files and configurations for all operating systems.
    
    Args:
        conf: Configuration dictionary from the ruleset
        
    Yields:
        Plugin, PluginConfig, or SystemBinary artifacts
    """
    
    # Get execution interval (convert to int, bakery uses float)
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
    
    # Linux configuration file (JSON format)
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
    
    # Windows configuration is handled via WindowsConfigEntry in
    # get_windows_config() - entries go into check_mk.yml
    
    # -------------------------------------------------------------------------
    # Solaris Plugin (optional)
    # -------------------------------------------------------------------------
    # Uncomment if you have a Solaris plugin
    #
    # yield Plugin(
    #     base_os=OS.SOLARIS,
    #     source=Path(SOLARIS_PLUGIN),
    #     target=Path(LINUX_PLUGIN),  # Usually same target name
    #     interval=interval_int,
    # )
    #
    # # Solaris configuration file (shell format)
    # yield PluginConfig(
    #     base_os=OS.SOLARIS,
    #     lines=_generate_shell_config(conf),
    #     target=Path("my_plugin.cfg"),
    #     include_header=True,
    # )
    
    # -------------------------------------------------------------------------
    # Additional Binaries (optional)
    # -------------------------------------------------------------------------
    # Uncomment to include additional tools in /usr/bin
    #
    # yield SystemBinary(
    #     base_os=OS.LINUX,
    #     source=Path("my_helper_tool"),  # From agents/custom/
    # )


def _generate_json_config(conf: MyPluginConfig) -> List[str]:
    """Generate JSON configuration for Linux plugin."""
    config = {
        "api_url": conf.get("api_url", ""),
        "username": conf.get("username", ""),
        "timeout": conf.get("timeout", 30),
        "verify_ssl": conf.get("verify_ssl", True),
    }
    return json.dumps(config, indent=2).split("\n")


def _generate_shell_config(conf: MyPluginConfig) -> List[str]:
    """Generate shell-sourceable configuration for Solaris."""
    return [
        f'API_URL={quote_shell_string(conf.get("api_url", ""))}',
        f'USERNAME={quote_shell_string(conf.get("username", ""))}',
        f'TIMEOUT={conf.get("timeout", 30)}',
        f'VERIFY_SSL={"true" if conf.get("verify_ssl", True) else "false"}',
    ]


def _generate_ini_config(conf: MyPluginConfig) -> List[str]:
    """Generate INI-style configuration (alternative format)."""
    return [
        "[my_plugin]",
        f'api_url = {conf.get("api_url", "")}',
        f'username = {conf.get("username", "")}',
        f'timeout = {conf.get("timeout", 30)}',
        f'verify_ssl = {conf.get("verify_ssl", True)}',
    ]


# =============================================================================
# Package Scriptlets
# =============================================================================

def get_scriptlets(conf: MyPluginConfig) -> ScriptletGenerator:
    """
    Generate package manager scriptlets (post-install, pre-remove, etc.).
    
    These are shell commands executed during package installation/removal.
    
    Note: Do NOT end with 'exit 0' - CheckMK adds more commands after yours.
    
    Args:
        conf: Configuration dictionary from the ruleset
        
    Yields:
        Scriptlet artifacts for DEB, RPM, and Solaris packages
    """
    
    # Commands to run after installation
    postinstall_lines = [
        f'logger -p local3.info "CheckMK: Installed {PLUGIN_NAME} plugin"',
        # Add more post-install commands here, e.g.:
        # 'systemctl restart check_mk_agent',
        # 'mkdir -p /var/lib/my_plugin',
    ]
    
    # Commands to run before removal
    preremove_lines = [
        f'logger -p local3.info "CheckMK: Removing {PLUGIN_NAME} plugin"',
        # Add pre-remove commands here, e.g.:
        # 'rm -rf /var/lib/my_plugin',
    ]
    
    # Commands to run after removal
    postremove_lines = [
        f'logger -p local3.info "CheckMK: Removed {PLUGIN_NAME} plugin"',
    ]
    
    # -------------------------------------------------------------------------
    # Debian/Ubuntu (DEB packages)
    # -------------------------------------------------------------------------
    yield Scriptlet(step=DebStep.POSTINST, lines=postinstall_lines)
    yield Scriptlet(step=DebStep.PRERM, lines=preremove_lines)
    yield Scriptlet(step=DebStep.POSTRM, lines=postremove_lines)
    
    # -------------------------------------------------------------------------
    # RedHat/CentOS/SUSE (RPM packages)
    # -------------------------------------------------------------------------
    yield Scriptlet(step=RpmStep.POST, lines=postinstall_lines)
    yield Scriptlet(step=RpmStep.PREUN, lines=preremove_lines)
    yield Scriptlet(step=RpmStep.POSTUN, lines=postremove_lines)
    
    # -------------------------------------------------------------------------
    # Solaris PKG (optional)
    # -------------------------------------------------------------------------
    # yield Scriptlet(step=SolStep.POSTINSTALL, lines=postinstall_lines)
    # yield Scriptlet(step=SolStep.PREREMOVE, lines=preremove_lines)
    # yield Scriptlet(step=SolStep.POSTREMOVE, lines=postremove_lines)


# =============================================================================
# Windows Configuration
# =============================================================================

def get_windows_config(conf: MyPluginConfig) -> WindowsConfigGenerator:
    """
    Generate Windows agent YAML configuration entries.
    
    These entries are written to C:\\ProgramData\\checkmk\\agent\\check_mk.yml
    The Windows plugin can read these values from the YAML file.
    
    Args:
        conf: Configuration dictionary from the ruleset
        
    Yields:
        WindowsConfigEntry artifacts
    """
    
    # Each entry creates a path in the YAML structure
    # path=["my_plugin", "api_url"] creates:
    # my_plugin:
    #   api_url: "value"
    
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
# Registration
# =============================================================================

register.bakery_plugin(
    name=PLUGIN_NAME,
    files_function=get_plugin_files,
    scriptlets_function=get_scriptlets,
    windows_config_function=get_windows_config,
)
