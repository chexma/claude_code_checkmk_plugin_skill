# CheckMK Extension Development Overview

## When to Extend CheckMK

CheckMK provides over 2000 ready-made check plugins, but you may need custom extensions when:
- Hardware is too new
- Software is too exotic  
- Organization-specific development
- Custom data sources (REST APIs, databases)
- Specialized monitoring requirements

## Extension Types Comparison

| Type | Execution Location | Thresholds | Metrics | Complexity | Use When |
|------|-------------------|------------|---------|------------|----------|
| **Local Checks** | Host only | Single pair per metric | Multiple, no units | Lowest | Simple status checks |
| **Agent Plugins** | Host (data) + Server (eval) | Flexible, multiple | Full control | Medium | Complex parsing, trends |
| **Special Agents** | Server only | Flexible, multiple | Full control | Medium-High | REST API, no agent access |
| **Active Checks** | Server only | Flexible | Nagios format | Medium | Network service monitoring |
| **SNMP Plugins** | Server only | Flexible, multiple | Full control | Medium | Network devices |
| **Nagios Plugins** | Host (MRPE) or Server | Limited | Limited | Low | Nagios compatibility |

## Decision Tree

```
Need to monitor something?
│
├─ Can you install an agent on the host?
│   │
│   ├─ YES: Is the check simple (single status)?
│   │   │
│   │   ├─ YES → Local Check (simplest)
│   │   │
│   │   └─ NO: Need complex evaluation, trends, or multiple services?
│   │       │
│   │       └─ YES → Agent Plugin + Check Plugin
│   │
│   └─ NO: Is it a network service check (HTTP, TCP, SSL)?
│       │
│       ├─ YES → Active Check (server-side)
│       │
│       └─ NO: Does the device support SNMP?
│           │
│           ├─ YES → SNMP Check Plugin
│           │
│           └─ NO: Is there a REST API or other remote access?
│               │
│               └─ YES → Special Agent (Datasource Program)
│
└─ Need Nagios compatibility?
    │
    └─ YES → Nagios Plugin (MRPE or Active Check)
```

## Extension Types in Detail

### 1. Local Checks (Simplest)

**What**: Script on monitored host outputs status directly.

**Output format**: `STATUS "SERVICE_NAME" METRICS STATUS_TEXT`

**Example**:
```bash
#!/bin/bash
# /usr/lib/check_mk_agent/local/backup_check

if [ -f /var/backup/last_success ]; then
    age=$(($(date +%s) - $(stat -c %Y /var/backup/last_success)))
    if [ $age -lt 86400 ]; then
        echo "0 \"Backup Status\" age=${age}s Backup OK, age: ${age}s"
    else
        echo "2 \"Backup Status\" age=${age}s Backup too old: ${age}s"
    fi
else
    echo "2 \"Backup Status\" - No backup found"
fi
```

**Pros**:
- No Python required
- Any programming language
- No CheckMK API knowledge needed
- Quick to implement

**Cons**:
- Limited threshold management (single warn/crit pair per metric)
- No automatic unit handling
- Status determined on host (can't change centrally)

**Best for**: Quick checks, backup status, simple file/process monitoring

### 2. Agent Plugins + Check Plugins

**What**: Two-part system:
1. **Agent plugin** (on host): Collects raw data, outputs as section
2. **Check plugin** (on server): Parses data, evaluates status

**Agent plugin example** (Python):
```python
#!/usr/bin/env python3
# /usr/lib/check_mk_agent/plugins/myapp

print("<<<myapp>>>")
print("temperature 45.2")
print("humidity 62")
```

**Check plugin** (on server):
```python
from cmk.agent_based.v2 import AgentSection, CheckPlugin, Service, Result, State

def parse_myapp(string_table):
    return {line[0]: float(line[1]) for line in string_table}

def discover_myapp(section):
    yield Service()

def check_myapp(params, section):
    temp = section.get("temperature", 0)
    if temp > params["crit"]:
        yield Result(state=State.CRIT, summary=f"Temperature: {temp}°C")
    elif temp > params["warn"]:
        yield Result(state=State.WARN, summary=f"Temperature: {temp}°C")
    else:
        yield Result(state=State.OK, summary=f"Temperature: {temp}°C")

agent_section_myapp = AgentSection(name="myapp", parse_function=parse_myapp)
check_plugin_myapp = CheckPlugin(
    name="myapp",
    service_name="MyApp Status",
    discovery_function=discover_myapp,
    check_function=check_myapp,
    check_default_parameters={"warn": 40.0, "crit": 50.0},
)
```

**Pros**:
- Full threshold control via rulesets
- Multiple metrics with proper units
- Trend analysis possible
- Multiple services from one section
- Supports labels and inventory

**Cons**:
- Requires Python knowledge
- Must learn CheckMK APIs
- Two-part development

**Best for**: Complex monitoring, applications with multiple metrics, trend analysis

### 3. Special Agents (Datasource Programs)

**What**: Program on CheckMK server that:
1. Connects to external data source (REST API, database, etc.)
2. Outputs data in agent format
3. Processed by check plugins on server

**Architecture**:
```
[External API] <--REST/HTTP--> [Special Agent] --> [Check Plugin]
                                (on CMK server)    (on CMK server)
```

**Example** (simplified):
```python
#!/usr/bin/env python3
# ~/local/lib/python3/cmk_addons/plugins/myapi/libexec/agent_myapi

import requests
import sys

host = sys.argv[1]
response = requests.get(f"https://{host}/api/status")
data = response.json()

print("<<<myapi_status>>>")
print(f"cpu {data['cpu_percent']}")
print(f"memory {data['memory_percent']}")
```

**Pros**:
- No agent installation needed
- Can monitor anything with an API
- Full server-side control
- Supports piggyback for multiple hosts

**Cons**:
- More complex setup (3 files minimum)
- Requires network access from CMK server
- Must handle authentication

**Best for**: REST APIs, cloud services (AWS, Azure), virtualization platforms (VMware, Proxmox), network devices

### 4. Active Checks

**What**: Programs executed by CheckMK server to check network services from the outside.

**Architecture**:
```
[CheckMK Server]
       │
       ├── Ruleset (GUI) ──► Server-Side Calls ──► Executable
       │                          │                    │
       │                          │                    ▼
       │                          └─────────────► [Remote Service]
       │                                          (HTTP, TCP, SSL)
       ▼
   [Service Result]
```

**Three components**:
1. **Executable**: Nagios-compatible program (any language)
2. **Server-Side Calls**: Maps config to command line
3. **Ruleset**: GUI form for configuration

**Example** (server-side calls):
```python
from cmk.server_side_calls.v1 import (
    ActiveCheckCommand, ActiveCheckConfig, HostConfig,
)

def generate_mycheck_commands(params, host_config):
    args = ["-H", host_config.primary_ip_config.address]
    args.extend(["-p", str(params.get("port", 443))])
    
    yield ActiveCheckCommand(
        service_description=f"Port {params.get('port', 443)}",
        command_arguments=args,
    )

active_check_mycheck = ActiveCheckConfig(
    name="mycheck",  # Calls: check_mycheck
    parameter_parser=lambda p: p,
    commands_function=generate_mycheck_commands,
)
```

**Pros**:
- Checks services from external perspective (end-user view)
- No agent installation needed
- Simple Nagios plugin format
- Continue checking even when host is DOWN

**Cons**:
- Only single-service output (unlike agent-based checks)
- No complex data parsing or trends
- Must handle network connectivity

**Best for**: HTTP/HTTPS checks, TCP port monitoring, SSL certificate validation, DNS resolution, mail server checks

### 6. SNMP Check Plugins

**What**: Check plugin that queries SNMP OIDs directly from CheckMK server.

**Two-phase process**:
1. **Detection**: Check sysDescr/sysObjectID to identify device
2. **Fetch**: Retrieve specific OIDs for monitoring

**Example**:
```python
from cmk.agent_based.v2 import (
    SimpleSNMPSection, SNMPTree, CheckPlugin,
    Service, Result, State, startswith,
)

def parse_router(string_table):
    if not string_table:
        return None
    return {"uptime": int(string_table[0][0])}

def discover_router(section):
    yield Service()

def check_router(section):
    uptime_seconds = section["uptime"] / 100
    yield Result(state=State.OK, summary=f"Uptime: {uptime_seconds:.0f}s")

snmp_section_router = SimpleSNMPSection(
    name="router_uptime",
    parse_function=parse_router,
    detect=startswith(".1.3.6.1.2.1.1.1.0", "Cisco"),
    fetch=SNMPTree(base=".1.3.6.1.2.1.1", oids=["3.0"]),  # sysUpTime
)

check_plugin_router = CheckPlugin(
    name="router_uptime",
    service_name="Router Uptime",
    discovery_function=discover_router,
    check_function=check_router,
)
```

**Pros**:
- No agent needed on network devices
- Standard protocol for network equipment
- Full CheckMK API features

**Cons**:
- SNMP is inherently slow
- Must identify correct OIDs
- Detection runs on ALL SNMP devices

**Best for**: Switches, routers, firewalls, UPS, printers - any SNMP-enabled device

**Note**: If a device offers both SNMP and REST API, prefer REST API via special agent (faster, more efficient).

### 7. Nagios Plugins (Legacy)

**What**: Scripts using Nagios plugin format for backward compatibility.

**Two modes**:
- **MRPE**: Execute on host via agent
- **Active Check**: Execute on CheckMK server

**Output format**:
```
STATUS MESSAGE | metric1=value;warn;crit;min;max metric2=value
```

**Example**:
```bash
#!/bin/bash
# check_myservice

value=$(get_some_value)
if [ $value -gt 90 ]; then
    echo "CRITICAL - Value is $value | value=$value;80;90;0;100"
    exit 2
elif [ $value -gt 80 ]; then
    echo "WARNING - Value is $value | value=$value;80;90;0;100"
    exit 1
else
    echo "OK - Value is $value | value=$value;80;90;0;100"
    exit 0
fi
```

**Pros**:
- Compatible with existing Nagios plugins
- Large ecosystem of existing plugins

**Cons**:
- Cumbersome troubleshooting
- Limited integration with CheckMK features
- Exit codes for status (error-prone)

**Best for**: Migrating from Nagios, using existing Nagios plugins

## Additional Mechanisms

### Spool Directory

External programs write agent output directly to files:
- Linux: `/var/lib/check_mk_agent/spool/`
- Windows: `C:\ProgramData\checkmk\agent\spool\`

**Use cases**:
- Backup scripts writing status on completion
- Long-running processes
- Cronjob results
- Testing agent plugin output

### Piggyback

Data from one host assigned to another:
- VM data from hypervisor
- Container data from Docker host
- Cloud resources from API

**Example output**:
```
<<<<vm-server01>>>>
<<<cpu>>>
0.15 0.10 0.05
<<<<>>>>
```

### MKP Packages

Bundle extensions for distribution:
- Version control
- Easy installation
- Share via CheckMK Exchange

## Choosing the Right Approach

| Scenario | Recommended Approach |
|----------|---------------------|
| Simple backup status check | Local Check |
| Complex application with 20 metrics | Agent Plugin + Check Plugin |
| Cloud API (AWS, Azure) | Special Agent |
| Network switch monitoring | SNMP Check Plugin |
| HTTP/HTTPS endpoint monitoring | Active Check |
| SSL certificate validation | Active Check |
| TCP port availability check | Active Check |
| Existing Nagios plugin | MRPE or Active Check |
| VM monitoring from hypervisor | Special Agent + Piggyback |
| External program output | Spool Directory |

## Development Effort Comparison

| Approach | Files Needed | Time to Implement |
|----------|--------------|-------------------|
| Local Check | 1 | Minutes |
| Active Check (simple) | 3 | Hours |
| Active Check (full) | 3-4 | Hours-Day |
| Agent Plugin (simple) | 2 | Hours |
| Agent Plugin (with rules) | 4-5 | Day |
| Special Agent | 3-4 | Day |
| Special Agent (full) | 5-7 | Days |
| SNMP Plugin | 1-2 | Hours |

## Getting Started

1. **Read the skill documentation** for your chosen approach
2. **Use templates** from `assets/templates/`
3. **Test incrementally** with `cmk -v --detect-plugins=`
4. **Package as MKP** for distribution

## Contributing to CheckMK

1. Submit to [CheckMK Exchange](https://exchange.checkmk.com) first
2. Quality requirements are lower than core plugins
3. If mature, consider [contributing to CheckMK](https://github.com/Checkmk/checkmk/blob/master/CONTRIBUTING.md)
