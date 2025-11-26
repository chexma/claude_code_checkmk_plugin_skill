# Piggyback Data Mechanism

Piggyback ermöglicht es einem Special Agent, Daten für **andere Hosts** bereitzustellen - z.B. VMs, Container, Cloud-Ressourcen.

## Konzept

```
┌─────────────────────┐     ┌──────────────┐
│  Nutanix Prism API  │ --> │  agent_prism │ --> Cluster-Daten
│                     │     │              │ --> Piggyback: VM1
│                     │     │              │ --> Piggyback: VM2
│                     │     │              │ --> Piggyback: Host1
└─────────────────────┘     └──────────────┘
```

## Special Agent Output Format

```python
#!/usr/bin/env python3
"""agent_mycloud - Special agent with piggyback data."""

import sys
import json
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hostname", required=True)
    args = parser.parse_args()
    
    # Fetch data from API
    data = fetch_cloud_api(args.hostname)
    
    # 1. Main host data (the cloud controller itself)
    print("<<<mycloud_controller>>>")
    print(f"status|{data['controller_status']}")
    print(f"version|{data['version']}")
    
    # 2. Piggyback data for each VM
    for vm in data.get("vms", []):
        # Switch to piggyback host context
        print(f"<<<<{vm['name']}>>>>")
        
        # Now output sections for THIS piggyback host
        print("<<<mycloud_vm>>>")
        print(f"state|{vm['state']}")
        print(f"cpu|{vm['cpu_usage']}")
        print(f"memory|{vm['memory_usage']}")
        
        # Can have multiple sections per piggyback host
        print("<<<mycloud_vm_disks>>>")
        for disk in vm.get("disks", []):
            print(f"{disk['name']}|{disk['size']}|{disk['used']}")
        
        # End piggyback block - return to main host
        print("<<<<>>>>")
    
    # 3. Can continue with more main host data
    print("<<<mycloud_summary>>>")
    print(f"total_vms|{len(data.get('vms', []))}")

def fetch_cloud_api(hostname):
    # Implement API call
    pass

if __name__ == "__main__":
    main()
```

## Piggyback Marker Syntax

| Marker | Bedeutung |
|--------|-----------|
| `<<<<hostname>>>>` | Start piggyback block für hostname |
| `<<<<>>>>` | Ende piggyback block, zurück zum Main-Host |
| `<<<section_name>>>` | Normale Section innerhalb eines Blocks |

## Check Plugin für Piggyback-Daten

```python
#!/usr/bin/env python3
"""Check plugin for piggyback VM data."""

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    Service,
    Result,
    State,
    Metric,
    HostLabel,
)


def parse_mycloud_vm(string_table):
    """Parse piggyback VM data."""
    parsed = {}
    for line in string_table:
        if len(line) >= 2:
            key, value = line[0], line[1]
            parsed[key] = value
    return parsed


def host_label_function(section):
    """Auto-generate host labels from piggyback data."""
    # Useful for dynamic host labeling
    if section.get("state"):
        yield HostLabel("cmk/cloud_vm", "yes")
        yield HostLabel("mycloud/state", section.get("state", "unknown"))


def discover_mycloud_vm(section):
    """Discover VM service."""
    if section:
        yield Service()


def check_mycloud_vm(section):
    """Check VM state and metrics."""
    if not section:
        yield Result(state=State.UNKNOWN, summary="No data")
        return
    
    state_str = section.get("state", "unknown")
    
    state_map = {
        "running": State.OK,
        "stopped": State.WARN,
        "error": State.CRIT,
    }
    
    yield Result(
        state=state_map.get(state_str, State.UNKNOWN),
        summary=f"VM State: {state_str}"
    )
    
    # Metrics
    if "cpu" in section:
        cpu = float(section["cpu"])
        yield Metric("cpu_usage", cpu, boundaries=(0.0, 100.0))
    
    if "memory" in section:
        mem = float(section["memory"])
        yield Metric("memory_usage", mem, boundaries=(0.0, 100.0))


agent_section_mycloud_vm = AgentSection(
    name="mycloud_vm",
    parse_function=parse_mycloud_vm,
    host_label_function=host_label_function,
)

check_plugin_mycloud_vm = CheckPlugin(
    name="mycloud_vm",
    service_name="VM Status",
    discovery_function=discover_mycloud_vm,
    check_function=check_mycloud_vm,
)
```

## Piggyback Host Erstellung

Piggyback-Hosts müssen in CheckMK existieren! Optionen:

### 1. Manuelle Erstellung
- Hosts manuell anlegen
- Piggyback-Namen müssen exakt übereinstimmen

### 2. Automatische Erstellung via DCD (Enterprise)
Dynamic Configuration Daemon kann Hosts automatisch erstellen.

### 3. Via API / Script
```python
# create_piggyback_hosts.py
import requests

CMK_URL = "http://mycmk/mysite/check_mk/api/1.0"
API_USER = "automation"
API_SECRET = "secret"

def create_host(hostname, folder="/piggyback"):
    response = requests.post(
        f"{CMK_URL}/domain-types/host_config/collections/all",
        headers={"Authorization": f"Bearer {API_USER} {API_SECRET}"},
        json={
            "folder": folder,
            "host_name": hostname,
            "attributes": {
                "tag_agent": "no-agent",  # No direct agent
            }
        }
    )
    return response.json()
```

## Host Konfiguration für Piggyback

Piggyback-Hosts benötigen spezielle Konfiguration:

1. **Tag `Agent type`**: "No API integrations, no Checkmk agent"
2. **Piggyback aktivieren**: Setup > Hosts > Properties > "Use piggyback data from other hosts"

Oder via Regel: **Setup > Agents > General Settings > Piggyback**

```
Use piggyback data from other hosts:
☑ Use piggyback data from other hosts if present
```

## Piggyback mit Namens-Mapping

Wenn API-Namen nicht direkt als Hostnamen nutzbar sind:

### Via Translation Rule
**Setup > Agents > Agent access rules > Hostname translation for piggybacked hosts**

```python
# Regex-basierte Übersetzung
# API Name: "vm-123-web-server"
# CMK Name: "web-server"
("vm-[0-9]+-(.+)", "\1")
```

### Im Special Agent
```python
def sanitize_hostname(name):
    """Convert API name to valid hostname."""
    import re
    # Lowercase, replace spaces/special chars
    name = name.lower()
    name = re.sub(r'[^a-z0-9-]', '-', name)
    name = re.sub(r'-+', '-', name)  # Multiple dashes to single
    return name.strip('-')

# Output with sanitized name
print(f"<<<<{sanitize_hostname(vm['name'])}>>>>")
```

## Prism-Style Multi-Section Piggyback

Das Nutanix Prism Plugin demonstriert komplexe Piggyback-Nutzung:

```python
# Vereinfachte Struktur wie in agent_prism

def output_cluster_data(cluster):
    """Main cluster data - no piggyback."""
    print("<<<prism_info:sep(59)>>>")  # sep(59) = semicolon
    print(f"name;{cluster['name']}")
    print(f"version;{cluster['version']}")
    
    print("<<<prism_alerts:sep(0)>>>")
    for alert in cluster.get("alerts", []):
        print(json.dumps(alert))


def output_vm_piggyback(vm):
    """Piggyback data for a single VM."""
    print(f"<<<<{vm['name']}>>>>")
    
    print("<<<prism_vms:sep(59)>>>")
    print(f"uuid;{vm['uuid']}")
    print(f"state;{vm['powerState']}")
    print(f"cpu;{vm['numVCpus']}")
    print(f"memory;{vm['memoryMb']}")
    
    print("<<<prism_vm_tools>>>")
    print(f"installed;{vm.get('nutanixGuestTools', {}).get('enabled', False)}")
    
    print("<<<<>>>>")


def output_host_piggyback(host):
    """Piggyback data for a hypervisor host."""
    print(f"<<<<{host['name']}>>>>")
    
    print("<<<prism_hosts:sep(59)>>>")
    print(f"uuid;{host['uuid']}")
    print(f"state;{host['state']}")
    
    print("<<<prism_host_stats>>>")
    for stat_name, stat_value in host.get("stats", {}).items():
        print(f"{stat_name}={stat_value}")
    
    print("<<<<>>>>")


def main():
    data = fetch_prism_api()
    
    output_cluster_data(data["cluster"])
    
    for vm in data.get("vms", []):
        output_vm_piggyback(vm)
    
    for host in data.get("hosts", []):
        output_host_piggyback(host)
```

## Debugging Piggyback

```bash
# Piggyback-Dateien prüfen
ls -la ~/tmp/check_mk/piggyback/

# Inhalt einer Piggyback-Datei
cat ~/tmp/check_mk/piggyback/<target-host>/<source-host>

# Piggyback-Quellen für einen Host
cmk --list-piggyback-sources <hostname>

# Agent-Output mit Piggyback prüfen
cmk -d <source-host> | grep -A5 "<<<<"
```

## Best Practices

1. **Konsistente Namen**: Piggyback-Namen müssen exakt mit Hostnamen übereinstimmen
2. **Eindeutige Namen**: Keine Duplikate über verschiedene Quellen
3. **Fehlerbehandlung**: Was passiert wenn VM nicht mehr existiert?
4. **Performance**: Bei vielen VMs kann die Datenmenge groß werden
5. **Staleness**: Konfiguriere angemessene Piggyback-Timeouts
