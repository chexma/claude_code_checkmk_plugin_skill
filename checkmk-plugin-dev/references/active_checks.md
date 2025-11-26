# Active Checks Development Reference

## Overview

Active Checks are programs executed by the CheckMK server to monitor network services from the outside. Unlike agent-based checks, they:

- Run on the CheckMK server (not the monitored host)
- Check accessibility, response times, and service status
- Continue checking even when host is DOWN
- Execute independently with their own interval
- Generate services automatically (no discovery needed)

## When to Use Active Checks

| Use Case | Example |
|----------|---------|
| Network service reachability | HTTP, SMTP, FTP, SSH |
| Response time monitoring | Web page load time |
| Certificate validation | SSL/TLS certificate expiry |
| Port availability | TCP/UDP port checks |
| External perspective | End-user experience simulation |

## Active Check vs Special Agent

| Aspect | Active Check | Special Agent |
|--------|--------------|---------------|
| Output format | Nagios-style (exit code + text) | Agent sections |
| Services | One service per check execution | Multiple services possible |
| Data processing | Direct status determination | Requires check plugin |
| Complexity | Lower | Higher |
| Use case | Simple service checks | Complex data collection |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      CheckMK Server                             │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Ruleset    │───▶│ Server-Side  │───▶│   Active     │      │
│  │ (WATO GUI)   │    │    Calls     │    │   Check      │      │
│  └──────────────┘    └──────────────┘    │  Executable  │      │
│                                          └──────┬───────┘      │
│                                                 │              │
└─────────────────────────────────────────────────┼──────────────┘
                                                  │
                                                  ▼
                                          ┌──────────────┐
                                          │   Remote     │
                                          │   Service    │
                                          │ (HTTP, SMTP) │
                                          └──────────────┘
```

## File Locations (CheckMK 2.4)

```
~/local/lib/python3/cmk_addons/plugins/<family>/
├── server_side_calls/
│   └── mycheck.py              # ActiveCheckConfig definition
├── rulesets/
│   └── mycheck.py              # ActiveCheck ruleset (GUI form)
└── libexec/
    └── check_mycheck           # Executable (no extension!)

# Alternative location for Nagios-compatible plugins
~/local/lib/nagios/plugins/
└── check_mycheck               # Executable
```

## Component Overview

An active check consists of 3 files:

1. **Executable** (`libexec/check_mycheck`) - The actual check program
2. **Server-Side Calls** (`server_side_calls/mycheck.py`) - Maps config to command line
3. **Ruleset** (`rulesets/mycheck.py`) - GUI form for configuration

## 1. The Executable

### Nagios Plugin Format

Active checks use Nagios plugin conventions:

```
OUTPUT FORMAT:
STATUS_TEXT | metric1=value;warn;crit;min;max metric2=value

EXIT CODES:
0 = OK
1 = WARNING
2 = CRITICAL
3 = UNKNOWN
```

### Example: Simple HTTP Check (Bash)

```bash
#!/bin/bash
# ~/local/lib/nagios/plugins/check_myhttp

# Parse arguments
HOST=""
PORT=80
TIMEOUT=10
WARNING=1
CRITICAL=5

while [[ $# -gt 0 ]]; do
    case "$1" in
        -H|--host) HOST="$2"; shift 2 ;;
        -p|--port) PORT="$2"; shift 2 ;;
        -t|--timeout) TIMEOUT="$2"; shift 2 ;;
        -w|--warning) WARNING="$2"; shift 2 ;;
        -c|--critical) CRITICAL="$2"; shift 2 ;;
        *) shift ;;
    esac
done

if [[ -z "$HOST" ]]; then
    echo "UNKNOWN - No host specified"
    exit 3
fi

# Perform check
START=$(date +%s.%N)
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    --connect-timeout "$TIMEOUT" \
    "http://${HOST}:${PORT}/")
CURL_EXIT=$?
END=$(date +%s.%N)

# Calculate response time
RESPONSE_TIME=$(echo "$END - $START" | bc)

# Evaluate result
if [[ $CURL_EXIT -ne 0 ]]; then
    echo "CRITICAL - Connection failed | response_time=${RESPONSE_TIME}s;${WARNING};${CRITICAL};0"
    exit 2
fi

if [[ "$HTTP_CODE" -ge 400 ]]; then
    echo "CRITICAL - HTTP $HTTP_CODE | response_time=${RESPONSE_TIME}s;${WARNING};${CRITICAL};0"
    exit 2
fi

if (( $(echo "$RESPONSE_TIME > $CRITICAL" | bc -l) )); then
    echo "CRITICAL - Response time ${RESPONSE_TIME}s | response_time=${RESPONSE_TIME}s;${WARNING};${CRITICAL};0"
    exit 2
fi

if (( $(echo "$RESPONSE_TIME > $WARNING" | bc -l) )); then
    echo "WARNING - Response time ${RESPONSE_TIME}s | response_time=${RESPONSE_TIME}s;${WARNING};${CRITICAL};0"
    exit 1
fi

echo "OK - HTTP $HTTP_CODE in ${RESPONSE_TIME}s | response_time=${RESPONSE_TIME}s;${WARNING};${CRITICAL};0"
exit 0
```

### Example: Python Check

```python
#!/usr/bin/env python3
# ~/local/lib/nagios/plugins/check_myservice

import argparse
import sys
import time
import socket


def main():
    parser = argparse.ArgumentParser(description="Check TCP service")
    parser.add_argument("-H", "--host", required=True, help="Host to check")
    parser.add_argument("-p", "--port", type=int, required=True, help="Port to check")
    parser.add_argument("-t", "--timeout", type=float, default=10, help="Timeout in seconds")
    parser.add_argument("-w", "--warning", type=float, default=1.0, help="Warning threshold (seconds)")
    parser.add_argument("-c", "--critical", type=float, default=5.0, help="Critical threshold (seconds)")
    args = parser.parse_args()

    start_time = time.time()
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(args.timeout)
        sock.connect((args.host, args.port))
        sock.close()
        response_time = time.time() - start_time
        
        perfdata = f"response_time={response_time:.4f}s;{args.warning};{args.critical};0"
        
        if response_time >= args.critical:
            print(f"CRITICAL - Response time {response_time:.3f}s | {perfdata}")
            return 2
        elif response_time >= args.warning:
            print(f"WARNING - Response time {response_time:.3f}s | {perfdata}")
            return 1
        else:
            print(f"OK - Port {args.port} open, response time {response_time:.3f}s | {perfdata}")
            return 0
            
    except socket.timeout:
        print(f"CRITICAL - Connection timeout after {args.timeout}s | response_time={args.timeout}s;{args.warning};{args.critical};0")
        return 2
    except socket.error as e:
        print(f"CRITICAL - Connection failed: {e}")
        return 2
    except Exception as e:
        print(f"UNKNOWN - {e}")
        return 3


if __name__ == "__main__":
    sys.exit(main())
```

**Important**: Make executable!
```bash
chmod 755 ~/local/lib/nagios/plugins/check_myservice
```

## 2. Server-Side Calls Configuration

Maps ruleset configuration to command line arguments.

```python
#!/usr/bin/env python3
# ~/local/lib/python3/cmk_addons/plugins/mycheck/server_side_calls/mycheck.py

from collections.abc import Iterator, Mapping
from typing import Any

from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    HostConfig,
    Secret,
)


def generate_mycheck_commands(
    params: Mapping[str, Any],
    host_config: HostConfig,
) -> Iterator[ActiveCheckCommand]:
    """Generate command line for active check."""
    
    args: list[str | Secret] = []
    
    # Host - use configured or host address
    host = params.get("host") or host_config.primary_ip_config.address
    args.extend(["-H", host])
    
    # Port
    if "port" in params:
        args.extend(["-p", str(params["port"])])
    
    # Timeout
    if "timeout" in params:
        args.extend(["-t", str(params["timeout"])])
    
    # Thresholds
    if "response_time" in params:
        warn, crit = params["response_time"]
        args.extend(["-w", str(warn), "-c", str(crit)])
    
    # Password handling (if needed)
    if "password" in params:
        args.extend(["--password", params["password"]])  # Secret type
    
    # Service description
    service_description = params.get("service_description", "My Service Check")
    
    yield ActiveCheckCommand(
        service_description=service_description,
        command_arguments=args,
    )


# Register the active check configuration
# Variable name MUST start with "active_check_"
active_check_mycheck = ActiveCheckConfig(
    name="mycheck",
    parameter_parser=lambda p: p,  # Use params as-is
    commands_function=generate_mycheck_commands,
)
```

### Key Points

- Variable must be named `active_check_<name>`
- `name` must match the executable: `check_<name>`
- Executable location: `~/local/lib/nagios/plugins/check_<name>` or `~/local/lib/python3/cmk_addons/plugins/<family>/libexec/check_<name>`
- Use `Secret` type for passwords (handled securely)

## 3. Ruleset Definition

Creates the GUI form in Setup > Services.

```python
#!/usr/bin/env python3
# ~/local/lib/python3/cmk_addons/plugins/mycheck/rulesets/mycheck.py

from cmk.rulesets.v1 import Title, Help, Label
from cmk.rulesets.v1.form_specs import (
    Dictionary,
    DictElement,
    String,
    Integer,
    Float,
    Password,
    Tuple,
    DefaultValue,
    validators,
)
from cmk.rulesets.v1.rule_specs import ActiveCheck, Topic


rule_spec_mycheck = ActiveCheck(
    name="mycheck",
    title=Title("My Custom Service Check"),
    topic=Topic.NETWORKING,
    parameter_form=lambda: Dictionary(
        title=Title("Check parameters"),
        elements={
            "service_description": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Service description"),
                    help_text=Help("Name of the service in monitoring"),
                    prefill=DefaultValue("My Service"),
                ),
            ),
            "host": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("Hostname or IP"),
                    help_text=Help("Leave empty to use host address"),
                ),
            ),
            "port": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("Port number"),
                    prefill=DefaultValue(443),
                    custom_validate=(validators.NumberInRange(min_value=1, max_value=65535),),
                ),
            ),
            "timeout": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Timeout (seconds)"),
                    prefill=DefaultValue(10),
                    custom_validate=(validators.NumberInRange(min_value=1, max_value=300),),
                ),
            ),
            "response_time": DictElement(
                required=False,
                parameter_form=Tuple(
                    title=Title("Response time thresholds"),
                    help_text=Help("Warning and critical thresholds in seconds"),
                    elements=[
                        Float(title=Title("Warning"), prefill=DefaultValue(1.0)),
                        Float(title=Title("Critical"), prefill=DefaultValue(5.0)),
                    ],
                ),
            ),
        },
    ),
)
```

## Complete Example: Certificate Check

### 1. Executable

```python
#!/usr/bin/env python3
# ~/local/lib/nagios/plugins/check_cert_expiry

import argparse
import socket
import ssl
import sys
from datetime import datetime, timezone


def main():
    parser = argparse.ArgumentParser(description="Check SSL certificate expiry")
    parser.add_argument("-H", "--host", required=True)
    parser.add_argument("-p", "--port", type=int, default=443)
    parser.add_argument("-w", "--warning", type=int, default=30, help="Warning days before expiry")
    parser.add_argument("-c", "--critical", type=int, default=7, help="Critical days before expiry")
    parser.add_argument("-t", "--timeout", type=float, default=10)
    args = parser.parse_args()

    try:
        context = ssl.create_default_context()
        with socket.create_connection((args.host, args.port), timeout=args.timeout) as sock:
            with context.wrap_socket(sock, server_hostname=args.host) as ssock:
                cert = ssock.getpeercert()
        
        # Parse expiry date
        not_after = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
        not_after = not_after.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        days_left = (not_after - now).days
        
        perfdata = f"days_left={days_left};{args.warning};{args.critical};0"
        
        if days_left <= args.critical:
            print(f"CRITICAL - Certificate expires in {days_left} days | {perfdata}")
            return 2
        elif days_left <= args.warning:
            print(f"WARNING - Certificate expires in {days_left} days | {perfdata}")
            return 1
        else:
            print(f"OK - Certificate valid for {days_left} days | {perfdata}")
            return 0
            
    except ssl.SSLError as e:
        print(f"CRITICAL - SSL error: {e}")
        return 2
    except socket.error as e:
        print(f"CRITICAL - Connection error: {e}")
        return 2
    except Exception as e:
        print(f"UNKNOWN - {e}")
        return 3


if __name__ == "__main__":
    sys.exit(main())
```

### 2. Server-Side Calls

```python
#!/usr/bin/env python3
# ~/local/lib/python3/cmk_addons/plugins/certcheck/server_side_calls/cert_expiry.py

from collections.abc import Iterator, Mapping
from typing import Any

from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    HostConfig,
)


def generate_cert_commands(
    params: Mapping[str, Any],
    host_config: HostConfig,
) -> Iterator[ActiveCheckCommand]:
    args: list[str] = []
    
    # Host
    host = params.get("host") or host_config.name
    args.extend(["-H", host])
    
    # Port
    args.extend(["-p", str(params.get("port", 443))])
    
    # Thresholds
    warn = params.get("warning_days", 30)
    crit = params.get("critical_days", 7)
    args.extend(["-w", str(warn), "-c", str(crit)])
    
    # Timeout
    if "timeout" in params:
        args.extend(["-t", str(params["timeout"])])
    
    service_desc = params.get("service_description", f"Certificate {host}")
    
    yield ActiveCheckCommand(
        service_description=service_desc,
        command_arguments=args,
    )


active_check_cert_expiry = ActiveCheckConfig(
    name="cert_expiry",
    parameter_parser=lambda p: p,
    commands_function=generate_cert_commands,
)
```

### 3. Ruleset

```python
#!/usr/bin/env python3
# ~/local/lib/python3/cmk_addons/plugins/certcheck/rulesets/cert_expiry.py

from cmk.rulesets.v1 import Title, Help
from cmk.rulesets.v1.form_specs import (
    Dictionary,
    DictElement,
    String,
    Integer,
    DefaultValue,
    validators,
)
from cmk.rulesets.v1.rule_specs import ActiveCheck, Topic


rule_spec_cert_expiry = ActiveCheck(
    name="cert_expiry",
    title=Title("Check SSL Certificate Expiry"),
    topic=Topic.NETWORKING,
    parameter_form=lambda: Dictionary(
        elements={
            "service_description": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("Service description"),
                    help_text=Help("Leave empty for auto-generated name"),
                ),
            ),
            "host": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("Hostname"),
                    help_text=Help("Leave empty to use monitored host"),
                ),
            ),
            "port": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Port"),
                    prefill=DefaultValue(443),
                ),
            ),
            "warning_days": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Warning threshold (days)"),
                    prefill=DefaultValue(30),
                ),
            ),
            "critical_days": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Critical threshold (days)"),
                    prefill=DefaultValue(7),
                ),
            ),
            "timeout": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Connection timeout (seconds)"),
                    prefill=DefaultValue(10),
                ),
            ),
        },
    ),
)
```

## Using Built-in Nagios Plugins

CheckMK includes many Nagios plugins in `~/lib/nagios/plugins/`:

```bash
# List available plugins
ls ~/lib/nagios/plugins/

# Common plugins:
check_http      # HTTP/HTTPS checks
check_tcp       # TCP port checks
check_smtp      # SMTP checks
check_dns       # DNS resolution
check_ping      # ICMP ping
check_ssh       # SSH connectivity
check_ftp       # FTP service
check_ntp_peer  # NTP synchronization
```

### Using via "Integrate Nagios plugins" Rule

For quick integration without custom development:

1. Go to **Setup > Services > Other services > Integrate Nagios plugins**
2. Configure service description and command line
3. Use macros like `$HOSTNAME$`, `$HOSTADDRESS$`

## Testing Active Checks

```bash
# Test executable directly
~/local/lib/nagios/plugins/check_cert_expiry -H google.com -p 443 -w 30 -c 7

# Check command line generation (after activating changes)
cmk -N myhost | grep "check_cert_expiry"

# Debug
cmk --debug -N myhost
```

## Macros Available in Active Checks

| Macro | Description |
|-------|-------------|
| `$HOSTNAME$` | Host name |
| `$HOSTADDRESS$` | IP address |
| `$HOSTALIAS$` | Host alias |
| `$USER1$` | Plugin directory path |
| `$_HOSTADDRESS_4$` | IPv4 address |
| `$_HOSTADDRESS_6$` | IPv6 address |

## Best Practices

1. **Exit codes**: Always return proper Nagios exit codes (0-3)
2. **Single line output**: First line is the status summary
3. **Performance data**: Include metrics after `|` separator
4. **Timeout handling**: Always implement timeouts
5. **Error messages**: Be descriptive in UNKNOWN states
6. **No file extension**: Executable should not have `.py` or `.sh` extension
7. **Permissions**: Make executable with `chmod 755`

## Troubleshooting

### Rule not visible in GUI

```bash
# Check for syntax errors
python3 -m py_compile ~/local/lib/python3/cmk_addons/plugins/mycheck/rulesets/mycheck.py

# Restart Apache
omd restart apache
```

### Check not executing

```bash
# Verify executable exists and is executable
ls -la ~/local/lib/nagios/plugins/check_mycheck

# Test manually
~/local/lib/nagios/plugins/check_mycheck -H testhost -p 443
```

### Wrong arguments passed

```bash
# Check generated Nagios config
cmk -N myhost | grep check_mycheck
```

## Files and Directories

| Path | Description |
|------|-------------|
| `~/lib/nagios/plugins/` | Built-in Nagios plugins |
| `~/local/lib/nagios/plugins/` | Custom Nagios plugins |
| `~/local/lib/python3/cmk_addons/plugins/<family>/libexec/` | Custom executables (alternative) |
| `~/local/lib/python3/cmk_addons/plugins/<family>/server_side_calls/` | ActiveCheckConfig |
| `~/local/lib/python3/cmk_addons/plugins/<family>/rulesets/` | ActiveCheck rulesets |
