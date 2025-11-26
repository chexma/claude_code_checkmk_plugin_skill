# Inventory Plugins (HW/SW Inventory)

Inventory Plugins sammeln Hardware- und Software-Informationen für die CheckMK Inventory.

## Konzept

```
Agent Output → Inventory Plugin → Inventory Tree
                                  ├── Hardware
                                  │   ├── CPU
                                  │   ├── Memory
                                  │   └── Storage
                                  └── Software
                                      ├── OS
                                      ├── Packages
                                      └── Applications
```

## Inventory Plugin Struktur

```python
#!/usr/bin/env python3
"""Inventory plugin for MyApp."""

from cmk.agent_based.v2 import (
    AgentSection,
    InventoryPlugin,
    Attributes,
    TableRow,
    InventoryResult,
)


def parse_myapp_inventory(string_table):
    """Parse agent output for inventory."""
    parsed = {}
    for line in string_table:
        if len(line) >= 2:
            key, value = line[0], line[1]
            parsed[key] = value
    return parsed


def inventory_myapp(section) -> InventoryResult:
    """Generate inventory data."""
    if not section:
        return
    
    # 1. Attributes: Single values
    yield Attributes(
        path=["software", "applications", "myapp"],
        inventory_attributes={
            "version": section.get("version", "unknown"),
            "install_date": section.get("installed"),
            "license_type": section.get("license"),
        },
    )
    
    # 2. Table rows: Multiple items
    for module in section.get("modules", []):
        yield TableRow(
            path=["software", "applications", "myapp", "modules"],
            key_columns={
                "name": module["name"],  # Unique identifier
            },
            inventory_columns={
                "version": module.get("version"),
                "enabled": module.get("enabled", True),
                "description": module.get("description", ""),
            },
        )


agent_section_myapp_inventory = AgentSection(
    name="myapp_inventory",
    parse_function=parse_myapp_inventory,
)

inventory_plugin_myapp = InventoryPlugin(
    name="myapp",
    inventory_function=inventory_myapp,
    sections=["myapp_inventory"],
)
```

## Variable Naming

```python
# WICHTIG: Prefix für Auto-Discovery
inventory_plugin_<name> = InventoryPlugin(...)
```

## Inventory Pfade (Inventory Tree)

Standard-Pfade die CheckMK kennt:

```
hardware/
├── cpu/                    # CPU Informationen
├── memory/                 # RAM Details
├── storage/
│   ├── controller/         # Storage Controller
│   └── disks/              # Festplatten
├── system/                 # Systeminfo
│   ├── bios/
│   ├── motherboard/
│   └── product/
└── video/                  # Grafikkarten

networking/
├── interfaces/             # Netzwerk-Interfaces
├── routes/                 # Routing-Tabelle
└── addresses/              # IP-Adressen

software/
├── os/                     # Betriebssystem
├── packages/               # Installierte Pakete
├── applications/           # Anwendungen
│   └── <your_app>/         # Custom Apps hier
├── configuration/          # Konfiguration
└── firmware/               # Firmware-Versionen
```

## Attributes vs. TableRow

| Typ | Anwendung | Beispiel |
|-----|-----------|----------|
| `Attributes` | Einzelne Key-Value Paare | Version, Install-Datum |
| `TableRow` | Liste von Items | Installierte Module, Lizenzen |

### Attributes Beispiel

```python
yield Attributes(
    path=["software", "applications", "myapp"],
    inventory_attributes={
        "name": "My Application",
        "version": "2.4.1",
        "vendor": "MyCompany",
        "install_path": "/opt/myapp",
        "install_date": "2024-01-15",
    },
)
```

### TableRow Beispiel

```python
# Für mehrere ähnliche Items (z.B. Lizenzen, Module)
for license in licenses:
    yield TableRow(
        path=["software", "applications", "myapp", "licenses"],
        key_columns={
            "license_id": license["id"],  # Eindeutiger Schlüssel
        },
        inventory_columns={
            "type": license["type"],
            "valid_until": license.get("expiry"),
            "seats": license.get("seats", "unlimited"),
        },
    )
```

## Status Columns (Änderungserkennung)

`status_columns` werden für die Änderungserkennung verwendet:

```python
yield TableRow(
    path=["software", "packages"],
    key_columns={
        "name": package["name"],
    },
    inventory_columns={
        "arch": package.get("arch"),
        "package_type": "rpm",
    },
    status_columns={
        "version": package["version"],  # Änderungen werden getrackt
    },
)
```

- `key_columns`: Identifizieren das Item eindeutig
- `inventory_columns`: Statische Daten
- `status_columns`: Werden auf Änderungen überwacht

## Agent Output für Inventory

```python
#!/usr/bin/env python3
# Agent plugin that provides inventory data

import json
import os

def main():
    # Normal section für Check
    print("<<<myapp>>>")
    print("status|running")
    
    # Separate section für Inventory
    print("<<<myapp_inventory:sep(0)>>>")
    
    inventory_data = {
        "version": "2.4.1",
        "installed": "2024-01-15",
        "license": "enterprise",
        "modules": [
            {"name": "core", "version": "2.4.1", "enabled": True},
            {"name": "analytics", "version": "1.2.0", "enabled": True},
            {"name": "reporting", "version": "1.0.5", "enabled": False},
        ]
    }
    
    print(json.dumps(inventory_data))

if __name__ == "__main__":
    main()
```

## Komplexes Inventory Plugin

```python
#!/usr/bin/env python3
"""Complete inventory plugin with hardware and software data."""

from typing import Mapping, Any
from cmk.agent_based.v2 import (
    AgentSection,
    InventoryPlugin,
    Attributes,
    TableRow,
    InventoryResult,
)


Section = Mapping[str, Any]


def parse_mydevice(string_table) -> Section | None:
    """Parse JSON inventory data."""
    if not string_table:
        return None
    
    import json
    try:
        return json.loads(" ".join(string_table[0]))
    except (json.JSONDecodeError, IndexError):
        return None


def inventory_mydevice(section: Section | None) -> InventoryResult:
    """Generate comprehensive inventory."""
    if not section:
        return
    
    # Hardware: System Info
    if "system" in section:
        sys = section["system"]
        yield Attributes(
            path=["hardware", "system"],
            inventory_attributes={
                "manufacturer": sys.get("vendor"),
                "product": sys.get("model"),
                "serial": sys.get("serial_number"),
                "uuid": sys.get("uuid"),
            },
        )
    
    # Hardware: CPU
    if "cpu" in section:
        cpu = section["cpu"]
        yield Attributes(
            path=["hardware", "cpu"],
            inventory_attributes={
                "model": cpu.get("model"),
                "cores": cpu.get("cores"),
                "threads": cpu.get("threads"),
                "frequency": cpu.get("frequency"),
            },
        )
    
    # Hardware: Storage (Table)
    for disk in section.get("disks", []):
        yield TableRow(
            path=["hardware", "storage", "disks"],
            key_columns={
                "device": disk["device"],
            },
            inventory_columns={
                "vendor": disk.get("vendor"),
                "model": disk.get("model"),
                "size": disk.get("size"),
                "type": disk.get("type"),
            },
            status_columns={
                "firmware": disk.get("firmware"),
                "health": disk.get("health"),
            },
        )
    
    # Software: Application
    if "application" in section:
        app = section["application"]
        yield Attributes(
            path=["software", "applications", "mydevice"],
            inventory_attributes={
                "name": app.get("name", "MyDevice Controller"),
                "version": app.get("version"),
                "build": app.get("build"),
                "license": app.get("license_type"),
            },
        )
    
    # Networking: Interfaces
    for iface in section.get("interfaces", []):
        yield TableRow(
            path=["networking", "interfaces"],
            key_columns={
                "name": iface["name"],
            },
            inventory_columns={
                "type": iface.get("type"),
                "mac_address": iface.get("mac"),
                "speed": iface.get("speed"),
            },
            status_columns={
                "oper_status": iface.get("status"),
                "ip_address": iface.get("ip"),
            },
        )


agent_section_mydevice_inventory = AgentSection(
    name="mydevice_inventory",
    parse_function=parse_mydevice,
)

inventory_plugin_mydevice = InventoryPlugin(
    name="mydevice",
    sections=["mydevice_inventory"],
    inventory_function=inventory_mydevice,
)
```

## Inventory ausführen und testen

```bash
# Inventory für Host ausführen
cmk -v --inventory-as-check myhost

# Nur Inventory (kein Check)
cmk -v -i myhost

# Inventory Debug
cmk --debug -v -i myhost

# Inventory-Daten anzeigen
cmk --paths | grep inventory
cat ~/var/check_mk/inventory/myhost

# Inventory Tree im Web
# Setup > Hosts > <host> > Inventory
```

## Inventory History

CheckMK speichert Inventory-Änderungen:

```bash
# History-Dateien
ls ~/var/check_mk/inventory_archive/myhost/

# Änderungen zwischen zwei Zeitpunkten
cmk --inventory-diff myhost
```

## Inventory als Service

Inventory kann als regelmäßiger Check laufen:

**Setup > Services > Service discovery > Hardware/Software inventory**

Optionen:
- Check-Intervall
- Status bei Änderungen (WARN, CRIT)
- Inventory-Tiefe

## Best Practices

1. **Eindeutige Keys**: `key_columns` müssen Items eindeutig identifizieren
2. **Konsistente Pfade**: Standard-Pfade nutzen wo möglich
3. **Sinnvolle Status-Columns**: Nur tracken was wichtig ist
4. **Performance**: Inventory läuft seltener als Checks
5. **Dokumentation**: Inventory-Pfade dokumentieren
