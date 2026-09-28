# Bakery API

The Bakery API (commercial editions) allows packaging agent plugins for automatic distribution via the Agent Bakery. It handles plugin files, configuration files, package scriptlets, and Windows YAML configuration.

> **Note**: Only the commercial editions (Pro, Ultimate, Cloud) bake agents. Since 2.3.0 the Bakery API module can also be imported in the Community edition (formerly Raw), so an MKP containing a bakery plugin still loads there. It just has no effect.

## Contents

- [Which Version?](#which-version)
- [Version 1 (Stable — CheckMK 2.3+, also 2.5)](#version-1-stable--checkmk-23-also-25)
  - [Use Cases](#use-cases)
  - [Scope and Limitations](#scope-and-limitations)
  - [Directory Structure](#directory-structure)
  - [Complete Example](#complete-example)
  - [API Reference](#api-reference)
  - [File Locations](#file-locations)
  - [Minimal Example (Distribution Only)](#minimal-example-distribution-only)
  - [MKP Package Structure](#mkp-package-structure)
  - [Windows Configuration](#windows-configuration)
  - [Best Practices](#best-practices)
  - [Debugging](#debugging)
- [Version 2 (Unstable — CheckMK 2.5+)](#version-2-unstable--checkmk-25)
  - [Key Differences from v1](#key-differences-from-v1)
  - [Imports](#imports-1)
  - [Minimal Example](#minimal-example)
  - [Working with Secrets](#working-with-secrets)
  - [File Locations (v2_unstable)](#file-locations-v2_unstable)
  - [Migrating a v1 Plugin to v2_unstable](#migrating-a-v1-plugin-to-v2_unstable)
- [Related Topics](#related-topics)

## Which Version?

Two Bakery API versions exist side by side:

| | Version 1 | Version 2 |
|---|---|---|
| Import | `cmk.base.plugins.bakery.bakery_api.v1` (as `.bakery_api.v1` relative import) | `cmk.bakery.v2_unstable` |
| CheckMK version | 2.3+ (also 2.5) | 2.5+ only |
| Stability | Stable (deprecated in the next major release, see `SKILL.md` → *Stability and timeline*) | **Unstable** — may still change; not recommended for production yet |
| Registration | `register.bakery_plugin(...)` call at import time | `BakeryPlugin` instance, name must start with `bakery_plugin_` — discovered by the backend, not registered at import |
| `source` path for `Plugin`/`SystemBinary` | Relative to `~/local/share/check_mk/agents/` (`Plugin`: its `plugins/` subdir; Windows: `windows/plugins/`) | Relative to the plugin family's `agents/` directory (`cmk_addons/plugins/<FAMILY>/agents/`) |
| Secrets | No dedicated abstraction | `Secret` class instances passed to plugin functions instead of raw password-store access |
| Parameter validation | Runtime dict access (`conf.get(...)`) | Required `parameter_parser` callable (e.g. pydantic `Model.model_validate`, or `no_op_parser`) |
| Function arguments | Keyword args `conf` (+ `aghash` for scriptlets/Windows) | One positional argument: the parsed config; no `aghash` |
| Default parameters | — | Required `default_parameters` argument (`None` = only baked when a rule is configured) |

**Recommendation**: for CheckMK 2.4, use v1. For CheckMK 2.5, use v1 unless you specifically need the new plugin family layout or `Secret` handling — v2_unstable can still change. Timeline: see `SKILL.md` → *Stability and timeline*. Tell the user this trade-off explicitly if they're targeting 2.5.

> **Automation user (Werk #17344)**: new 2.5 sites no longer create a default `automation` user, and secrets of newly created automation users are no longer stored in clear text. Rules that rely on the automation secret (agent bakery / Agent Updater registration, auto-registration) need a user configured explicitly.

Template: `assets/templates/bakery_plugin.py` (v1) / `assets/templates/bakery_plugin_v2.py` (v2_unstable).

---

## Version 1 (Stable — CheckMK 2.3+, also 2.5)

### Use Cases

- Distribute agent plugins to specific hosts via rules
- Generate configuration files for plugins
- Run package scriptlets (postinst, prerm, etc.)
- Configure Windows agent YAML entries
- Bundle everything in an MKP package

### Scope and Limitations

**The Bakery API covers:**
- Deploying plugin files to agent packages
- Generating plugin configuration files
- Executing package scriptlets (RPM/DEB/Solaris PKG)
- Windows agent YAML configuration entries

**NOT covered by the Bakery API:**
- Definition of the ruleset configuration (use `AgentConfig` in Rulesets API)
- Writing the agent plugin scripts themselves
- Other additional files that plugins may require

### Directory Structure

```
~/local/lib/python3/cmk/base/cee/plugins/bakery/
└── hello_world.py              # Bakery plugin

~/local/share/check_mk/agents/
├── plugins/                    # Unix agent plugins
│   └── hello_world
├── windows/plugins/            # Windows agent plugins
│   └── hello_world.ps1
└── some_tool                   # SystemBinary source (agents/ root)
```

### Complete Example

#### 1. Ruleset (Agent Configuration)

File: `~/local/lib/python3/cmk_addons/plugins/hello_world/rulesets/agent_config.py`

```python
#!/usr/bin/env python3
from cmk.rulesets.v1 import Label, Title, Help
from cmk.rulesets.v1.form_specs import (
    Dictionary,
    DictElement,
    String,
    Integer,
    TimeSpan,
    TimeMagnitude,
    DefaultValue,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic

def _parameter_form():
    return Dictionary(
        elements={
            "user": DictElement(
                parameter_form=String(
                    title=Title("Username"),
                    help_text=Help("User to run the plugin as"),
                ),
                required=True,
            ),
            "api_endpoint": DictElement(
                parameter_form=String(
                    title=Title("API Endpoint"),
                    prefill=DefaultValue("http://localhost:8080"),
                ),
            ),
            "interval": DictElement(
                parameter_form=TimeSpan(
                    title=Title("Execution interval"),
                    label=Label("Run every"),
                    displayed_magnitudes=[
                        TimeMagnitude.SECOND,
                        TimeMagnitude.MINUTE,
                    ],
                    prefill=DefaultValue(300.0),
                ),
            ),
        }
    )

# Use AgentConfig instead of CheckParameters
rule_spec_hello_world_bakery = AgentConfig(
    name="hello_world",
    title=Title("Hello World Plugin"),
    topic=Topic.GENERAL,
    parameter_form=_parameter_form,
)
```

#### 2. Bakery Plugin

File: `~/local/lib/python3/cmk/base/cee/plugins/bakery/hello_world.py`

```python
#!/usr/bin/env python3
import json
from pathlib import Path
from typing import TypedDict, List

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


class HelloWorldConfig(TypedDict, total=False):
    """Type definition for the configuration from ruleset."""
    interval: float
    user: str
    api_endpoint: str


def get_hello_world_plugin_files(conf: HelloWorldConfig) -> FileGenerator:
    """Generate plugin files for all operating systems."""
    
    interval = conf.get("interval")
    
    # Linux plugin
    yield Plugin(
        base_os=OS.LINUX,
        source=Path("hello_world"),           # Source in agents/plugins/
        target=Path("hello_world"),           # Target name on host
        interval=int(interval) if interval else None,
    )
    
    # Windows plugin
    yield Plugin(
        base_os=OS.WINDOWS,
        source=Path("hello_world.ps1"),
        target=Path("hello_world.ps1"),
        interval=int(interval) if interval else None,
    )
    
    # Solaris plugin
    yield Plugin(
        base_os=OS.SOLARIS,
        source=Path("hello_world.solaris.ksh"),
        target=Path("hello_world"),
        interval=int(interval) if interval else None,
    )
    
    # Linux configuration file (generated)
    yield PluginConfig(
        base_os=OS.LINUX,
        lines=_get_linux_config_lines(conf),
        target=Path("hello_world.json"),
        include_header=False,  # No "# Created by CheckMK" header
    )
    
    # Solaris configuration file (shell format)
    yield PluginConfig(
        base_os=OS.SOLARIS,
        lines=_get_solaris_config_lines(conf),
        target=Path("hello_world.cfg"),
        include_header=True,
    )
    
    # Additional binary/script for Linux
    yield SystemBinary(
        base_os=OS.LINUX,
        source=Path("hello_world_cli"),  # From ~/local/share/check_mk/agents/
    )


def _get_linux_config_lines(conf: HelloWorldConfig) -> List[str]:
    """Generate JSON config for Linux plugin."""
    config = {
        "user": conf.get("user", ""),
        "api_endpoint": conf.get("api_endpoint", ""),
    }
    return json.dumps(config, indent=2).split("\n")


def _get_solaris_config_lines(conf: HelloWorldConfig) -> List[str]:
    """Generate shell-sourceable config for Solaris."""
    return [
        f'USER={quote_shell_string(conf.get("user", ""))}',
        f'API_ENDPOINT={quote_shell_string(conf.get("api_endpoint", ""))}',
    ]


def get_hello_world_scriptlets(conf: HelloWorldConfig) -> ScriptletGenerator:
    """Generate package manager scriptlets."""
    
    installed_lines = ['logger -p local3.info "Installed hello_world"']
    uninstalled_lines = ['logger -p local3.info "Uninstalled hello_world"']
    
    # Debian/Ubuntu (DEB)
    yield Scriptlet(step=DebStep.POSTINST, lines=installed_lines)
    yield Scriptlet(step=DebStep.POSTRM, lines=uninstalled_lines)
    
    # RedHat/CentOS (RPM)
    yield Scriptlet(step=RpmStep.POST, lines=installed_lines)
    yield Scriptlet(step=RpmStep.POSTUN, lines=uninstalled_lines)
    
    # Solaris PKG
    yield Scriptlet(step=SolStep.POSTINSTALL, lines=installed_lines)
    yield Scriptlet(step=SolStep.POSTREMOVE, lines=uninstalled_lines)


def get_hello_world_windows_config(conf: HelloWorldConfig) -> WindowsConfigGenerator:
    """Generate Windows agent YAML configuration entries."""
    
    # These entries appear in check_mk.yml on Windows
    yield WindowsConfigEntry(
        path=["hello_world", "user"],
        content=conf.get("user", ""),
    )
    yield WindowsConfigEntry(
        path=["hello_world", "api_endpoint"],
        content=conf.get("api_endpoint", ""),
    )


# Register the bakery plugin
register.bakery_plugin(
    name="hello_world",
    files_function=get_hello_world_plugin_files,
    scriptlets_function=get_hello_world_scriptlets,
    windows_config_function=get_hello_world_windows_config,
)
```

### API Reference

#### Imports

```python
from .bakery_api.v1 import (
    # Operating systems
    OS,                    # Enum: LINUX, WINDOWS, SOLARIS, AIX

    # Scriptlet steps (package manager hooks)
    DebStep,               # PREINST, POSTINST, PRERM, POSTRM
    RpmStep,               # PRE, POST, PREUN, POSTUN, PRETRANS, POSTTRANS
    SolStep,               # PREINSTALL, POSTINSTALL, PREREMOVE, POSTREMOVE

    # File artifacts
    Plugin,                # Agent plugin executable
    PluginConfig,          # Generated config file for plugin
    SystemBinary,          # Additional binary in /usr/bin
    SystemConfig,          # System-wide config file (/etc)
    Scriptlet,             # Package manager scriptlet

    # Windows config
    WindowsConfigEntry,    # Single YAML entry
    WindowsConfigItems,    # List of items (merged with existing)
    WindowsGlobalConfigEntry,   # Shortcut for global section
    WindowsSystemConfigEntry,   # Shortcut for system section

    # Registration
    register,              # register.bakery_plugin()

    # Type annotations
    FileGenerator,
    ScriptletGenerator,
    WindowsConfigGenerator,

    # Helpers (deprecated - use shlex.quote instead)
    quote_shell_string,
)
```

#### Operating Systems

```python
OS.LINUX    # Linux target system
OS.WINDOWS  # Windows target system
OS.SOLARIS  # Solaris target system
OS.AIX      # AIX target system
```

#### Artifact Classes

##### Plugin

Agent plugin file to be executed by the CheckMK agent:

```python
yield Plugin(
    base_os=OS.LINUX,
    source=Path("my_plugin"),      # Source file in agents/plugins/
    target=Path("my_plugin"),      # Target filename on host (optional, defaults to source)
    interval=300,                  # Caching interval in seconds (optional)
    asynchronous=True,             # Windows: don't wait for termination (optional)
    timeout=60,                    # Windows: max wait time in seconds (optional)
    retry_count=3,                 # Windows: max retries after failure (optional)
)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `base_os` | `OS` | Target operating system (required) |
| `source` | `Path` | Path relative to plugin source directory on CheckMK site (usually just filename) |
| `target` | `Path \| None` | Target path relative to plugin directory on host. If omitted, uses source path |
| `interval` | `int \| None` | Caching interval in seconds. Plugin only re-executes after interval elapses |
| `asynchronous` | `bool \| None` | Windows only: Don't wait for plugin termination. An `interval` implies async |
| `timeout` | `int \| None` | Windows only: Maximum wait time for plugin to terminate |
| `retry_count` | `int \| None` | Windows only: Maximum retries after failed execution |

> **Key Fact:** The `source` path is **relative** to the plugin source directory - usually just the filename. The API automatically determines the full path based on `base_os`:
>
> ```python
> # source is just the filename - API handles the rest
> Plugin(base_os=OS.LINUX, source=Path("my_plugin"))
> # → Full path: ~/local/share/check_mk/agents/plugins/my_plugin
>
> Plugin(base_os=OS.WINDOWS, source=Path("my_plugin.ps1"))
> # → Full path: ~/local/share/check_mk/agents/windows/plugins/my_plugin.ps1
> ```

##### PluginConfig

Configuration file generated for the plugin. Placed in the agent's config directory (default `/etc/check_mk`):

```python
yield PluginConfig(
    base_os=OS.LINUX,
    lines=["key=value", "other=data"],  # File content as list of lines
    target=Path("my_plugin.cfg"),       # Target in plugin config dir
    include_header=True,                # Add "# Created by CheckMK" header
)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `base_os` | `OS` | Target operating system (required) |
| `lines` | `Iterable[str]` | Lines of text for the config file |
| `target` | `Path` | Path relative to agent's config directory (usually just filename) |
| `include_header` | `bool` | If True, prepends "# Created by Check_MK Agent Bakery..." header |

##### SystemConfig

Configuration file for the target system (placed under `/etc`). Unix only:

```python
yield SystemConfig(
    base_os=OS.LINUX,
    lines=["[Unit]", "Description=My Service", "..."],
    target=Path("systemd/system/myservice.service"),  # Relative to /etc
    include_header=True,
)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `base_os` | `OS` | Target operating system (required) |
| `lines` | `list[str]` | Lines of text for the config file |
| `target` | `Path` | Path relative to `/etc` on target system |
| `include_header` | `bool` | If True, prepends "# Created by Check_MK Agent Bakery..." header |

Use this for deploying systemd service files, config files to service `.d` directories, etc.

##### SystemBinary

Additional executable placed in system path (`/usr/bin` on Unix, `bin/` folder on Windows):

```python
yield SystemBinary(
    base_os=OS.LINUX,
    source=Path("my_tool"),   # Source in ~/local/share/check_mk/agents/
    target=Path("my_tool"),   # Optional target name
)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `base_os` | `OS` | Target operating system (required) |
| `source` | `Path` | Path relative to `~/local/share/check_mk/agents/` (not `agents/custom/` — that folder belongs to the "custom files" agent rule) |
| `target` | `Path \| None` | Target path relative to binary directory. If omitted, uses source path |

##### Scriptlet

Package manager hook scripts (DEB maintainer scripts, RPM scriptlets, Solaris installation scripts):

```python
# Debian
yield Scriptlet(step=DebStep.POSTINST, lines=['echo "Installed"'])
yield Scriptlet(step=DebStep.PRERM, lines=['echo "Removing"'])

# RPM
yield Scriptlet(step=RpmStep.POST, lines=['systemctl start myservice'])
yield Scriptlet(step=RpmStep.PREUN, lines=['systemctl stop myservice'])
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `step` | `DebStep \| RpmStep \| SolStep` | Which package transaction step to execute at |
| `lines` | `list[str]` | Shell commands (no shebang needed, uses Bourne shell) |

**Important**: Do NOT end scriptlets with `exit 0` - CheckMK adds more commands after yours.

Available steps:

| Format | Steps | Description |
|--------|-------|-------------|
| **DEB** | `PREINST` | Before package installation |
| | `POSTINST` | Right after package installation |
| | `PRERM` | Right before package uninstallation |
| | `POSTRM` | After package uninstallation |
| **RPM** | `PRE` | Before package installation |
| | `POST` | Right after package installation |
| | `PREUN` | Right before package uninstallation |
| | `POSTUN` | Right after package uninstallation |
| | `PRETRANS` | Before complete package transaction |
| | `POSTTRANS` | After complete package transaction |
| **Solaris** | `PREINSTALL` | Before package installation |
| | `POSTINSTALL` | Right after package installation |
| | `PREREMOVE` | Right before package uninstallation |
| | `POSTREMOVE` | After package uninstallation |

##### WindowsConfigEntry

Entry in Windows agent YAML configuration (`check_mk.install.yml`):

```python
# Creates entry in check_mk.yml:
# hello_world:
#   user: "myuser"
yield WindowsConfigEntry(
    path=["hello_world", "user"],
    content="myuser",
)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | `list[str]` | Path in YAML structure: `["section", "name"]` or `["section", "subsection", "name"]` (2-3 elements) |
| `content` | `int \| str \| bool \| dict \| list` | Value for the entry (must be YAML-serializable) |

##### WindowsConfigItems

List of items that will be **merged** with existing lists (unlike `WindowsConfigEntry` which overwrites):

```python
# Adds items to an existing list in check_mk.yml
yield WindowsConfigItems(
    path=["plugins", "enabled_list"],
    content=["my_plugin", "other_plugin"],
)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | `list[str]` | Path in YAML structure (2-3 elements) |
| `content` | `list[...]` | List of items to merge (same types as WindowsConfigEntry content) |

##### WindowsGlobalConfigEntry

Shortcut for entries in the `global` section:

```python
# Equivalent to: WindowsConfigEntry(path=["global", "enabled"], content=True)
yield WindowsGlobalConfigEntry(name="enabled", content=True)
```

##### WindowsSystemConfigEntry

Shortcut for entries in the `system` section:

```python
# Equivalent to: WindowsConfigEntry(path=["system", "controller"], content="localhost")
yield WindowsSystemConfigEntry(name="controller", content="localhost")
```

#### Registration

```python
register.bakery_plugin(
    name="my_plugin",                              # Must match ruleset name
    files_function=get_files,                      # FileGenerator function
    scriptlets_function=get_scriptlets,            # ScriptletGenerator (optional)
    windows_config_function=get_windows_config,    # WindowsConfigGenerator (optional)
)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Plugin name. Must be unique and match the corresponding AgentConfig ruleset name. Only ASCII letters, digits, and underscores allowed |
| `files_function` | `Callable[..., FileGenerator] \| None` | Generator yielding `Plugin`, `PluginConfig`, `SystemConfig`, or `SystemBinary`. Receives `conf` keyword argument |
| `scriptlets_function` | `Callable[..., ScriptletGenerator] \| None` | Generator yielding `Scriptlet`. Receives `conf` and `aghash` keyword arguments |
| `windows_config_function` | `Callable[..., WindowsConfigGenerator] \| None` | Generator yielding Windows config entries. Receives `conf` and `aghash` keyword arguments |

#### Function Parameters (v1)

In v1, the generator functions receive keyword arguments based on their parameter names:

| Parameter | Available In | Description |
|-----------|--------------|-------------|
| `conf` | All functions | Configuration dictionary from the AgentConfig ruleset |
| `aghash` | `scriptlets_function`, `windows_config_function` | Hash of the current agent configuration and plugin files |

> **Why `aghash` is not available in `files_function`:** The `aghash` is formed from the packaged files - it can only be computed after the files are determined. Since `files_function` produces the files, `aghash` isn't available there yet.

```python
def get_files(conf: dict) -> FileGenerator:
    # conf contains ruleset configuration
    # aghash NOT available here
    ...

def get_scriptlets(conf: dict, aghash: str) -> ScriptletGenerator:
    # aghash is computed from packaged files
    ...

def get_windows_config(conf: dict, aghash: str) -> WindowsConfigGenerator:
    # aghash available for config versioning
    ...
```

Arguments are **keyword-only** - the function parameter names must match exactly (`conf`, `aghash`). Unused arguments can be omitted from the function signature.

### File Locations

| Path | Description |
|------|-------------|
| `~/local/lib/python3/cmk/base/cee/plugins/bakery/` | Bakery plugin files (the old `~/local/lib/check_mk` symlink was removed in 2.5, Werk #17969) |
| `~/local/share/check_mk/agents/plugins/` | Unix agent plugins |
| `~/local/share/check_mk/agents/windows/plugins/` | Windows agent plugins |
| `~/local/share/check_mk/agents/` | `SystemBinary` sources (Unix) |
| `~/local/share/check_mk/agents/windows/` | Additional binaries (Windows) |
| `~/local/lib/python3/cmk_addons/plugins/<name>/rulesets/` | Ruleset for AgentConfig |

### Minimal Example (Distribution Only)

If you just want to distribute a plugin without configuration:

```python
# Ruleset (minimal)
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import Dictionary
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic

def _parameter_form():
    return Dictionary(elements={})

rule_spec_simple_plugin = AgentConfig(
    name="simple_plugin",
    title=Title("Simple Plugin"),
    topic=Topic.GENERAL,
    parameter_form=_parameter_form,
)
```

```python
# Bakery plugin (minimal)
from pathlib import Path
from .bakery_api.v1 import OS, Plugin, register, FileGenerator

def get_files(conf: dict) -> FileGenerator:
    yield Plugin(
        base_os=OS.LINUX,
        source=Path("simple_plugin"),
        target=Path("simple_plugin"),
    )
    yield Plugin(
        base_os=OS.WINDOWS,
        source=Path("simple_plugin.ps1"),
        target=Path("simple_plugin.ps1"),
    )

register.bakery_plugin(
    name="simple_plugin",
    files_function=get_files,
)
```

### MKP Package Structure

When packaging a Bakery plugin as MKP:

```
my_plugin-1.0.0.mkp
├── agents/plugins/
│   ├── my_plugin              # Linux plugin
│   └── my_plugin.ps1          # Windows plugin
├── agents/
│   └── my_tool                # SystemBinary source
├── lib/python3/cmk/base/cee/plugins/bakery/
│   └── my_plugin.py           # Bakery plugin (manifest part 'lib')
└── cmk_addons_plugins/my_plugin/
    ├── agent_based/
    │   └── my_check.py        # Check plugin
    └── rulesets/
        └── agent_config.py    # AgentConfig ruleset
```

### Windows Configuration

The Windows agent reads configuration from `C:\ProgramData\checkmk\agent\check_mk.yml`. Entries added via `WindowsConfigEntry` appear there:

```yaml
# Generated by Bakery
plugins:
  enabled: yes
  
hello_world:
  user: "monitoring"
  api_endpoint: "http://localhost:8080"
```

Your Windows plugin can read this with PowerShell:

```powershell
$configPath = "C:\ProgramData\checkmk\agent\check_mk.yml"
$config = Get-Content $configPath | ConvertFrom-Yaml
$user = $config.hello_world.user
```

### Best Practices

1. **Name consistency**: Bakery plugin name must match AgentConfig ruleset name
2. **No exit 0**: Don't end scriptlets with `exit 0` - CheckMK adds more commands
3. **Use TypedDict**: Define configuration structure with TypedDict
4. **Quote strings**: Use `shlex.quote()` for shell config files (preferred over deprecated `quote_shell_string`)
5. **Test baking**: After changes, bake a new agent and verify content
6. **Interval as int**: Convert `interval` from float to int for Plugin class

#### Deprecation Note: quote_shell_string

`quote_shell_string()` is **deprecated** and is just an alias for `shlex.quote`. While it remains available in Bakery API v1, use `shlex.quote` for new code:

```python
import shlex

def _get_solaris_cfg_lines(user: str, content: str) -> list[str]:
    return [
        f'USER={shlex.quote(user)}',
        f'CONTENT={shlex.quote(content)}',
    ]
```

### Debugging

```bash
# Check bakery plugin syntax
python3 -m py_compile ~/local/lib/python3/cmk/base/cee/plugins/bakery/my_plugin.py

# Bake agents (all hosts, or given hosts)
cmk -A myhost

# View baked agent content
dpkg -c ~/var/check_mk/agents/linux_deb/packages/*/check-mk-agent_*.deb

# Bakery log
tail -f ~/var/log/agent_bakery.log
```

---

## Version 2 (Unstable — CheckMK 2.5+)

> **Unstable API**: `cmk.bakery.v2_unstable` may change without notice (timeline: see `SKILL.md` → *Stability and timeline*). Use v1 above for production plugins unless you specifically need what's described here.

### Key Differences from v1

1. **Discovery instead of registration**: plugins are no longer registered by calling a function at import time. Instead you create a `BakeryPlugin` instance in a module-level variable whose name starts with `bakery_plugin_`; the backend discovers it later — the same pattern already used by `check_plugin_`, `rule_spec_`, etc.
2. **New plugin family layout**: `source` paths for `Plugin` and `SystemBinary` are relative to the family's `agents/` folder (`cmk_addons/plugins/<FAMILY>/agents/`), not `~/local/share/check_mk/agents/` as in v1. (The upstream docstring says `.agent`; the code and shipped plugins such as `ceph` use `agents`.)
3. **`Secret` instead of raw password-store access**: functions that need a configured secret receive `Secret` instances directly (with `.revealed`, `.source`, `.id`) instead of reaching into the password store themselves. `str(secret)` returns a SHA-256 hash, not the value — always use `.revealed`.
4. **`parameter_parser`** (required): validates/transforms the ruleset configuration; the result is passed to every function. Upstream strongly recommends a real parser (shipped plugins use a pydantic `BaseModel.model_validate`); `no_op_parser` passes the dict through unchanged.
5. **`default_parameters`** (required, no default): `None` means the plugin is only baked for hosts with a matching rule; a mapping is merged with user parameters (and must be accepted by `parameter_parser`).
6. **Single positional argument**: `files_function`, `scriptlets_function` and `windows_config_function` are called as `fn(parsed_config)` — there is no `aghash` in v2.

### Imports

```python
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
    SystemBinary,
    Scriptlet,
    WindowsConfigEntry,
    WindowsConfigItems,
    WindowsGlobalConfigEntry,
    WindowsSystemConfigEntry,
    SystemConfig,
    # Secrets
    Secret,
    # Plugin definition
    BakeryPlugin,
    # Type annotations
    FileGenerator,
    ScriptletGenerator,
    WindowsConfigGenerator,
    PkgStep,               # DebStep | RpmStep | SolStep (type alias)
    WindowsConfigContent,  # allowed content types (type alias)
    # Parameter parsing
    no_op_parser,
    # Discovery helper
    entry_point_prefixes,
)
```

### Minimal Example

```python
#!/usr/bin/env python3
"""Bakery plugin, v2_unstable (CheckMK 2.5+)."""
from pathlib import Path
from cmk.bakery.v2_unstable import (
    OS, Plugin, BakeryPlugin, FileGenerator, no_op_parser,
)


def get_hello_world_files(conf: dict) -> FileGenerator:
    yield Plugin(base_os=OS.LINUX, source=Path("hello_world"))
    yield Plugin(base_os=OS.WINDOWS, source=Path("hello_world.ps1"))


bakery_plugin_hello_world = BakeryPlugin(
    name="hello_world",
    parameter_parser=no_op_parser,
    default_parameters=None,  # required: None = only bake for hosts with a rule
    files_function=get_hello_world_files,
)
```

### Working with Secrets

```python
def get_files(conf: dict) -> FileGenerator:
    secret: Secret = conf["api_token"]  # Provided as a Secret, not a raw string
    yield PluginConfig(
        base_os=OS.LINUX,
        lines=[f"API_TOKEN={secret.revealed}"],
        target=Path("my_plugin.cfg"),
    )
```

### File Locations (v2_unstable)

Plugin family layout mirrors the other 2.5 plugin types:

```
~/local/lib/python3/cmk_addons/plugins/<family>/
├── bakery/
│   └── my_plugin.py          # BakeryPlugin definition
├── agents/                   # Agent plugin sources (Unix + Windows)
│   ├── my_plugin
│   └── my_plugin.ps1
└── rulesets/
    └── agent_config.py       # AgentConfig ruleset (unchanged, cmk.rulesets.v1)
```

### Migrating a v1 Plugin to v2_unstable

1. Change the import from `.bakery_api.v1` to `cmk.bakery.v2_unstable`.
2. Replace the trailing `register.bakery_plugin(name=..., files_function=..., ...)` call with a module-level `bakery_plugin_<name> = BakeryPlugin(name=..., parameter_parser=..., default_parameters=None, files_function=..., ...)`.
3. Change function signatures to a single positional config argument (drop `aghash`).
4. Move agent plugin source files into the family's `agents/` directory.
5. If the plugin reads secrets, change the ruleset/config wiring so the function receives `Secret` objects and use `.revealed` instead of manual password-store lookups.
6. Test with a real bake — v2_unstable is new enough that behavior should be verified, not assumed.

---

## Related Topics

- **AgentConfig ruleset** → `rulesets_api.md` (parameter forms)
- **Agent plugin scripts** → `agent_plugins.md` (what runs on hosts)
- **Package as MKP** → `mkp_packaging.md`
- **Best practices** → `best_practices.md`
