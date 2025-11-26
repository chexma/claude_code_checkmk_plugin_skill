# Inventory Plugins (HW/SW Inventory)

Inventory plugins collect hardware and software information for CheckMK inventory.

## Concept

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

## Inventory Plugin Structure

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
# IMPORTANT: Prefix for auto-discovery
inventory_plugin_<name> = InventoryPlugin(...)
```

## Inventory Paths (Inventory Tree)

Standard paths that CheckMK recognizes:

```
hardware/
├── cpu/                    # CPU information
├── memory/                 # RAM details
├── storage/
│   ├── controller/         # Storage controller
│   └── disks/              # Hard drives
├── system/                 # System info
│   ├── bios/
│   ├── motherboard/
│   └── product/
└── video/                  # Graphics cards

networking/
├── interfaces/             # Network interfaces
├── routes/                 # Routing table
└── addresses/              # IP addresses

software/
├── os/                     # Operating system
├── packages/               # Installed packages
├── applications/           # Applications
│   └── <your_app>/         # Custom apps go here
├── configuration/          # Configuration
└── firmware/               # Firmware versions
```

## Attributes vs. TableRow

| Type | Use Case | Example |
|------|----------|---------|
| `Attributes` | Single key-value pairs | Version, install date |
| `TableRow` | List of items | Installed modules, licenses |

### Attributes Example

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

### TableRow Example

```python
# For multiple similar items (e.g., licenses, modules)
for license in licenses:
    yield TableRow(
        path=["software", "applications", "myapp", "licenses"],
        key_columns={
            "license_id": license["id"],  # Unique key
        },
        inventory_columns={
            "type": license["type"],
            "valid_until": license.get("expiry"),
            "seats": license.get("seats", "unlimited"),
        },
    )
```

## Status Columns (Change Detection)

`status_columns` are used for change detection:

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
        "version": package["version"],  # Changes are tracked
    },
)
```

- `key_columns`: Uniquely identify the item
- `inventory_columns`: Static data
- `status_columns`: Monitored for changes

## Agent Output for Inventory

```python
#!/usr/bin/env python3
# Agent plugin that provides inventory data

import json
import os

def main():
    # Normal section for check
    print("<<<myapp>>>")
    print("status|running")

    # Separate section for inventory
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

## Complex Inventory Plugin

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

## Running and Testing Inventory

```bash
# Run inventory for host
cmk -v --inventory-as-check myhost

# Inventory only (no check)
cmk -v -i myhost

# Inventory debug
cmk --debug -v -i myhost

# Show inventory data
cmk --paths | grep inventory
cat ~/var/check_mk/inventory/myhost

# Inventory tree in web UI
# Setup > Hosts > <host> > Inventory
```

## Inventory History

CheckMK stores inventory changes:

```bash
# History files
ls ~/var/check_mk/inventory_archive/myhost/

# Changes between two points in time
cmk --inventory-diff myhost
```

## Inventory as Service

Inventory can run as a regular check:

**Setup > Services > Service discovery > Hardware/Software inventory**

Options:
- Check interval
- Status on changes (WARN, CRIT)
- Inventory depth

## Best Practices

1. **Unique keys**: `key_columns` must uniquely identify items
2. **Consistent paths**: Use standard paths where possible
3. **Meaningful status columns**: Only track what's important
4. **Performance**: Inventory runs less frequently than checks
5. **Documentation**: Document inventory paths
