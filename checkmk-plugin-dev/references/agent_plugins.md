# Agent Plugins (Host-Side)

Agent Plugins sind Scripts die **auf dem überwachten Host** laufen und zusätzliche Daten sammeln. Sie werden vom CheckMK Agent aufgerufen.

## Unterschied zu Special Agents

| Typ | Läuft auf | Verbindung | Anwendung |
|-----|-----------|------------|-----------|
| **Agent Plugin** | Überwachter Host | Lokal | Lokale Daten (Logs, Apps, Prozesse) |
| **Special Agent** | CheckMK Server | Remote (API) | Externe Systeme (Cloud, Appliances) |

## Verzeichnisse auf dem Host

```
/usr/lib/check_mk_agent/plugins/           # Standard-Plugins
/usr/lib/check_mk_agent/local/             # Local Checks
/etc/check_mk/conf.d/                      # Konfiguration

# Mit Intervall (z.B. alle 5 Minuten)
/usr/lib/check_mk_agent/plugins/300/       # 300 Sekunden = 5 Min
/usr/lib/check_mk_agent/plugins/3600/      # 3600 Sekunden = 1 Stunde
```

## Einfaches Agent Plugin (Bash)

```bash
#!/bin/bash
# /usr/lib/check_mk_agent/plugins/myapp

echo "<<<myapp>>>"

# Prüfe ob Service läuft
if systemctl is-active --quiet myapp; then
    echo "status running"
else
    echo "status stopped"
fi

# Sammle Metriken
if [ -f /var/log/myapp/metrics.log ]; then
    tail -1 /var/log/myapp/metrics.log
fi
```

## Agent Plugin (Python) - Offizieller Stil

Basierend auf offiziellen Plugins wie `mk_docker.py` und `mk_mongodb.py`:

```python
#!/usr/bin/env python3
"""CheckMK Agent Plugin for MyApp.

INSTALLATION:
    Copy to /usr/lib/check_mk_agent/plugins/mk_myapp
    
    For async execution (every 5 min):
    Copy to /usr/lib/check_mk_agent/plugins/300/mk_myapp

CONFIGURATION:
    Create /etc/check_mk/myapp.cfg (optional)
"""

import configparser
import json
import os
import subprocess
import sys
from pathlib import Path

# Config directory (set by agent)
MK_CONFDIR = Path(os.environ.get("MK_CONFDIR", "/etc/check_mk"))

def read_config():
    """Read INI-style configuration."""
    config = {"enabled": True, "timeout": 30}
    config_file = MK_CONFDIR / "myapp.cfg"
    
    if not config_file.exists():
        return config
    
    parser = configparser.ConfigParser()
    parser.read(str(config_file))
    
    if parser.has_section("MYAPP"):
        if parser.has_option("MYAPP", "enabled"):
            config["enabled"] = parser.getboolean("MYAPP", "enabled")
        if parser.has_option("MYAPP", "timeout"):
            config["timeout"] = parser.getint("MYAPP", "timeout")
    
    return config


def collect_service_status():
    """Collect systemd service status."""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "myapp"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def collect_metrics():
    """Collect application metrics."""
    metrics = {"timestamp": int(time.time())}
    
    # Read from status file
    status_file = Path("/var/lib/myapp/status.json")
    if status_file.exists():
        try:
            with open(status_file) as f:
                metrics.update(json.load(f))
        except Exception:
            pass
    
    return metrics


def main():
    config = read_config()
    
    if not config.get("enabled"):
        return 0
    
    # Section: Service Status (pipe-separated)
    print("<<<myapp_status:sep(124)>>>")
    status = collect_service_status()
    print(f"myapp|{status}")
    
    # Section: Metrics (JSON)
    print("<<<myapp_metrics:sep(0)>>>")
    print(json.dumps(collect_metrics()))
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

## Konfigurationsdatei für Linux Plugins

```ini
# /etc/check_mk/myapp.cfg
# Configuration for mk_myapp plugin

[MYAPP]
# Enable or disable the plugin
enabled = true

# Timeout for external commands
timeout = 30

# Sections to skip (comma-separated)
# skip_sections = metrics,logs

# Debug output to stderr
debug = false
```

## Windows Agent Plugin (PowerShell)

### Verzeichnisse auf Windows

```
C:\ProgramData\checkmk\agent\plugins\      # Agent Plugins
C:\ProgramData\checkmk\agent\config\       # Konfigurationsdateien
C:\ProgramData\checkmk\agent\local\        # Local Checks
C:\ProgramData\checkmk\agent\spool\        # Spool-Dateien

# Mit Intervall (z.B. alle 5 Minuten)
C:\ProgramData\checkmk\agent\plugins\300\  # 300 Sekunden = 5 Min
```

### Einfaches PowerShell Plugin

```powershell
# C:\ProgramData\checkmk\agent\plugins\myapp.ps1

Write-Host "<<<myapp>>>"

# Service Status
$service = Get-Service -Name "MyApp" -ErrorAction SilentlyContinue
if ($service) {
    Write-Host "status $($service.Status)"
} else {
    Write-Host "status notfound"
}

# Process Info
$proc = Get-Process -Name "myapp" -ErrorAction SilentlyContinue
if ($proc) {
    Write-Host "cpu $($proc.CPU)"
    Write-Host "memory $($proc.WorkingSet64)"
}

# Custom Metrics from Registry
$regPath = "HKLM:\SOFTWARE\MyApp\Metrics"
if (Test-Path $regPath) {
    $metrics = Get-ItemProperty -Path $regPath
    Write-Host "version $($metrics.Version)"
    Write-Host "connections $($metrics.ActiveConnections)"
}
```

### PowerShell Plugin mit Konfigurationsdatei (MSSQL-Stil)

```powershell
# C:\ProgramData\checkmk\agent\plugins\mydb.ps1
# Database Monitoring Plugin with Config Support

$configDir = $env:MK_CONFDIR
if (-not $configDir) {
    $configDir = "C:\ProgramData\checkmk\agent\config"
}

$configFile = Join-Path $configDir "mydb.cfg"

# Default Configuration
$config = @{
    Instances = @()
    Timeout = 30
}

# Read Configuration if exists
if (Test-Path $configFile) {
    $section = ""
    Get-Content $configFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -match '^\[(.+)\]$') {
            $section = $Matches[1]
        } elseif ($line -match '^(\w+)\s*=\s*(.+)$' -and $section -eq "mydb") {
            $key = $Matches[1]
            $value = $Matches[2]
            $config[$key] = $value
        }
    }
}

# Output Sections
Write-Host "<<<mydb_instances>>>"

# Discover local database instances
try {
    $instances = Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Microsoft SQL Server\Instance Names\SQL" -ErrorAction Stop
    foreach ($prop in $instances.PSObject.Properties) {
        if ($prop.Name -notmatch '^PS') {
            Write-Host "$($prop.Name)|$($prop.Value)"
        }
    }
} catch {
    # No SQL Server instances found - exit silently
    exit 0
}

# Query each instance
Write-Host "<<<mydb_status:sep(124)>>>"
# ... database queries here
```

### Konfigurationsdatei für Windows Plugin

```ini
# C:\ProgramData\checkmk\agent\config\mydb.cfg
[mydb]
timeout = 60
instances = MSSQLSERVER,SQLEXPRESS
auth_type = windows

[instance_MSSQLSERVER]
port = 1433
database = master

[instance_SQLEXPRESS]
port = 1434
database = master
```

### Async Plugin für Windows (check_mk.user.yml)

Für asynchrone Ausführung unter Windows muss die Agent-Konfiguration angepasst werden:

```yaml
# C:\ProgramData\checkmk\agent\check_mk.user.yml
plugins:
  enabled: yes
  execution:
    - pattern: mydb.ps1
      async: yes
      timeout: 120
      cache_age: 300
      retry_count: 3
    - pattern: expensive_check.ps1
      async: yes
      cache_age: 3600
```

## Caching und Intervalle

Für ressourcenintensive Checks - Cache nutzen:

```python
#!/usr/bin/env python3
# /usr/lib/check_mk_agent/plugins/600/myexpensive_check

"""
Expensive check that runs every 600 seconds (10 minutes).
Uses caching to handle agent queries between runs.
"""

import json
import os
import time

CACHE_FILE = "/var/cache/check_mk/myexpensive.cache"
CACHE_MAX_AGE = 900  # 15 minutes - slightly longer than interval

def load_cache():
    """Load cached data if still valid."""
    if not os.path.exists(CACHE_FILE):
        return None
    
    try:
        stat = os.stat(CACHE_FILE)
        age = time.time() - stat.st_mtime
        
        if age > CACHE_MAX_AGE:
            return None
        
        with open(CACHE_FILE) as f:
            return json.load(f)
    except Exception:
        return None


def save_cache(data):
    """Save data to cache."""
    cache_dir = os.path.dirname(CACHE_FILE)
    os.makedirs(cache_dir, exist_ok=True)
    
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f)


def collect_expensive_data():
    """The actual expensive data collection."""
    # Simulate expensive operation
    import subprocess
    result = subprocess.run(
        ["some_expensive_command"],
        capture_output=True,
        text=True,
        timeout=300
    )
    return {"output": result.stdout, "timestamp": time.time()}


def main():
    # Try cache first
    data = load_cache()
    
    if data is None:
        # Need to collect fresh data
        data = collect_expensive_data()
        save_cache(data)
    
    # Output the data
    print("<<<myexpensive>>>")
    print(json.dumps(data))


if __name__ == "__main__":
    main()
```

## Async Agent Plugins (Linux)

Async plugins laufen im Hintergrund:

```bash
# /usr/lib/check_mk_agent/plugins/86400/myasync
#!/bin/bash

# Marker für async
# MK_ASYNC=1

echo "<<<myasync:cached($(date +%s),86400)>>>"
# expensive_command_here
find /data -type f -size +100M 2>/dev/null | wc -l
```

Das `cached(timestamp,max_age)` in der Section Header signalisiert dem Agent das Caching.

## Konfigurierbare Plugins

Standard-Methode für konfigurierbare Plugins:

### Linux Config Format
```ini
# /etc/check_mk/myapp.cfg
enabled = true
log_path = /var/log/myapp
threshold_warn = 80
threshold_crit = 95
```

### Windows Config Format
```ini
# C:\ProgramData\checkmk\agent\config\myapp.cfg
[myapp]
enabled = true
log_path = C:\ProgramData\MyApp\logs
threshold_warn = 80
threshold_crit = 95
```

## Verteilung via Agent Bakery (Enterprise)

### Bakery Rule (Server-seitig)

```python
# ~/local/lib/python3/cmk_addons/plugins/myplugin/rulesets/bakery.py

from cmk.rulesets.v1 import Title, Help
from cmk.rulesets.v1.form_specs import (
    Dictionary,
    DictElement,
    Integer,
    String,
    BooleanChoice,
    DefaultValue,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def _form_spec():
    return Dictionary(
        title=Title("MyApp Monitoring"),
        elements={
            "enabled": DictElement(
                required=False,
                parameter_form=BooleanChoice(
                    title=Title("Enable monitoring"),
                    prefill=DefaultValue(True),
                ),
            ),
            "log_path": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("Log path"),
                    prefill=DefaultValue("/var/log/myapp"),
                ),
            ),
            "threshold": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Warning threshold"),
                    prefill=DefaultValue(80),
                ),
            ),
        },
    )


rule_spec_agent_config_myapp = AgentConfig(
    name="myapp",
    title=Title("MyApp Monitoring"),
    topic=Topic.APPLICATIONS,
    parameter_form=_form_spec,
)
```

### Bakery Plugin (Enterprise)

```python
# ~/local/lib/python3/cmk/base/cee/plugins/bakery/myapp.py

from pathlib import Path
from typing import Any

from cmk.base.cee.plugins.bakery.bakery_api.v1 import (
    OS,
    FileGenerator,
    Plugin,
    PluginConfig,
    register,
)


def get_myapp_plugin_files(conf: dict[str, Any]) -> FileGenerator:
    """Generate plugin files for agent bakery."""
    
    # Linux plugin
    yield Plugin(
        base_os=OS.LINUX,
        source=Path("myapp"),  # From agents/plugins/
        interval=300,  # Run every 5 minutes
    )
    
    # Linux config file
    config_content = f"""
enabled = {str(conf.get('enabled', True)).lower()}
log_path = {conf.get('log_path', '/var/log/myapp')}
threshold_warn = {conf.get('threshold', 80)}
"""
    yield PluginConfig(
        base_os=OS.LINUX,
        lines=config_content.strip().split('\n'),
        target=Path("myapp.cfg"),
        include_header=True,
    )
    
    # Windows plugin
    yield Plugin(
        base_os=OS.WINDOWS,
        source=Path("myapp.ps1"),
    )


register.bakery_plugin(
    name="myapp",
    files_function=get_myapp_plugin_files,
)
```

## Check Plugin für Agent-Daten

```python
# ~/local/lib/python3/cmk_addons/plugins/myplugin/agent_based/myapp.py

import json
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    Service,
    Result,
    State,
    Metric,
    check_levels,
)


def parse_myapp(string_table):
    """Parse myapp agent output."""
    if not string_table:
        return None
    
    # JSON format (sep(0))
    try:
        return json.loads(string_table[0][0])
    except (json.JSONDecodeError, IndexError):
        return None


def discover_myapp(section):
    """Discover myapp service."""
    if section:
        yield Service()


def check_myapp(section):
    """Check myapp status."""
    if not section:
        yield Result(state=State.UNKNOWN, summary="No data from agent")
        return
    
    status = section.get("status", "unknown")
    
    if status == "active" or status == "running":
        yield Result(state=State.OK, summary=f"Service is {status}")
    elif status == "inactive" or status == "stopped":
        yield Result(state=State.CRIT, summary=f"Service is {status}")
    else:
        yield Result(state=State.WARN, summary=f"Service status: {status}")


agent_section_myapp = AgentSection(
    name="myapp",
    parse_function=parse_myapp,
)

check_plugin_myapp = CheckPlugin(
    name="myapp",
    service_name="MyApp",
    discovery_function=discover_myapp,
    check_function=check_myapp,
)
```

## Debugging Agent Plugins

```bash
# Auf dem überwachten Host:

# Plugin manuell ausführen
/usr/lib/check_mk_agent/plugins/myapp

# Gesamte Agent-Ausgabe prüfen
check_mk_agent

# Nur bestimmte Section
check_mk_agent | sed -n '/<<<myapp>>>/,/<<<[^>]*>>>/p'

# Cache-Dateien prüfen
ls -la /var/cache/check_mk/

# Plugin-Berechtigungen
ls -la /usr/lib/check_mk_agent/plugins/

# Plugin-Fehler im Agent-Log
journalctl -u check-mk-agent
```

## Best Practices

1. **Timeout**: Plugins sollten in < 60 Sekunden fertig sein
2. **Fehlerbehandlung**: Keine Exceptions nach stdout
3. **Exit Codes**: 0 = OK, auch bei Warnungen (Output zählt)
4. **Caching**: Für teure Operationen Intervall-Ordner nutzen
5. **Idempotenz**: Mehrfaches Ausführen = gleiches Ergebnis
6. **Minimale Abhängigkeiten**: Nur Standard-Tools verwenden
7. **Sichere Pfade**: Absolute Pfade für Executables
