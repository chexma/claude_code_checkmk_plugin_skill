# Bakery API

The Bakery API (commercial editions) allows packaging agent plugins for automatic distribution via the Agent Bakery. It handles plugin files, configuration files, package scriptlets, and Windows YAML configuration.

> **Note**: Since CheckMK 2.3.0, the Bakery API exists in all editions. On CheckMK Raw, the functionality is simply ignored.

## Use Cases

- Distribute agent plugins to specific hosts via rules
- Generate configuration files for plugins
- Run package scriptlets (postinst, prerm, etc.)
- Configure Windows agent YAML entries
- Bundle everything in an MKP package

## Directory Structure

```
~/local/lib/check_mk/base/cee/plugins/bakery/
└── hello_world.py              # Bakery plugin

~/local/share/check_mk/agents/
├── plugins/                    # Unix agent plugins
│   └── hello_world
├── windows/plugins/            # Windows agent plugins
│   └── hello_world.ps1
└── custom/                     # Additional binaries
    └── some_tool
```

## Complete Example

### 1. Ruleset (Agent Configuration)

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

### 2. Bakery Plugin

File: `~/local/lib/check_mk/base/cee/plugins/bakery/hello_world.py`

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
        source=Path("hello_world_cli"),  # From agents/custom/
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

## API Reference

### Imports

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

    # Helpers
    quote_shell_string,    # Escape string for shell (deprecated, use shlex.quote)
)
```

### Operating Systems

```python
OS.LINUX    # Linux target system
OS.WINDOWS  # Windows target system
OS.SOLARIS  # Solaris target system
OS.AIX      # AIX target system
```

### Artifact Classes

#### Plugin

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

#### PluginConfig

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

#### SystemConfig

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

#### SystemBinary

Additional executable placed in system path (`/usr/bin` on Unix, `bin/` folder on Windows):

```python
yield SystemBinary(
    base_os=OS.LINUX,
    source=Path("my_tool"),   # Source in agents/ directory on site
    target=Path("my_tool"),   # Optional target name
)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `base_os` | `OS` | Target operating system (required) |
| `source` | `Path` | Path relative to agent source directory on CheckMK site |
| `target` | `Path \| None` | Target path relative to binary directory. If omitted, uses source path |

#### Scriptlet

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

#### WindowsConfigEntry

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

#### WindowsConfigItems

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

#### WindowsGlobalConfigEntry

Shortcut for entries in the `global` section:

```python
# Equivalent to: WindowsConfigEntry(path=["global", "enabled"], content=True)
yield WindowsGlobalConfigEntry(name="enabled", content=True)
```

#### WindowsSystemConfigEntry

Shortcut for entries in the `system` section:

```python
# Equivalent to: WindowsConfigEntry(path=["system", "controller"], content="localhost")
yield WindowsSystemConfigEntry(name="controller", content="localhost")
```

### Registration

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

### Function Parameters

The generator functions receive keyword arguments based on their parameter names:

| Parameter | Available In | Description |
|-----------|--------------|-------------|
| `conf` | All functions | Configuration dictionary from the AgentConfig ruleset |
| `aghash` | `scriptlets_function`, `windows_config_function` | Hash of the current agent configuration and plugin files |

```python
def get_files(conf: dict) -> FileGenerator:
    # conf contains ruleset configuration
    ...

def get_scriptlets(conf: dict, aghash: str) -> ScriptletGenerator:
    # aghash is the agent configuration hash
    ...

def get_windows_config(conf: dict, aghash: str) -> WindowsConfigGenerator:
    ...
```

## File Locations

| Path | Description |
|------|-------------|
| `~/local/lib/check_mk/base/cee/plugins/bakery/` | Bakery plugin files |
| `~/local/share/check_mk/agents/plugins/` | Unix agent plugins |
| `~/local/share/check_mk/agents/windows/plugins/` | Windows agent plugins |
| `~/local/share/check_mk/agents/custom/` | Additional binaries (Unix) |
| `~/local/share/check_mk/agents/windows/` | Additional binaries (Windows) |
| `~/local/lib/python3/cmk_addons/plugins/<name>/rulesets/` | Ruleset for AgentConfig |

## Minimal Example (Distribution Only)

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

## MKP Package Structure

When packaging a Bakery plugin as MKP:

```
my_plugin-1.0.0.mkp
├── agents/plugins/
│   ├── my_plugin              # Linux plugin
│   └── my_plugin.ps1          # Windows plugin
├── agents/custom/
│   └── my_tool                # Additional binary
├── base/cee/plugins/bakery/
│   └── my_plugin.py           # Bakery plugin
└── cmk_addons_plugins/my_plugin/
    ├── agent_based/
    │   └── my_check.py        # Check plugin
    └── rulesets/
        └── agent_config.py    # AgentConfig ruleset
```

## Windows Configuration

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

## Best Practices

1. **Name consistency**: Bakery plugin name must match AgentConfig ruleset name
2. **No exit 0**: Don't end scriptlets with `exit 0` - CheckMK adds more commands
3. **Use TypedDict**: Define configuration structure with TypedDict
4. **Quote strings**: Use `quote_shell_string()` for shell config files
5. **Test baking**: After changes, bake a new agent and verify content
6. **Interval as int**: Convert `interval` from float to int for Plugin class

## Debugging

```bash
# Check bakery plugin syntax
python3 -m py_compile ~/local/lib/check_mk/base/cee/plugins/bakery/my_plugin.py

# View baked agent content
tar -tvf ~/var/check_mk/agents/linux/check-mk-agent_*.deb

# Check agent package logs
tail -f ~/var/log/agent-bakery.log
```
