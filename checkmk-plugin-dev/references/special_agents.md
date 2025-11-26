# Special Agents API Reference

## Directory Structure

```
~/local/lib/python3/cmk_addons/plugins/<family>/
├── libexec/
│   └── agent_myagent           # Executable (no .py extension!)
├── server_side_calls/
│   └── special_agent.py        # Call configuration
├── rulesets/
│   └── special_agent.py        # Rule configuration
└── agent_based/
    └── myagent.py              # Optional: check plugin for the data
```

## 1. The Special Agent Executable

Location: `libexec/agent_myagent` (no file extension!)

```python
#!/usr/bin/env python3

import argparse
import json
import requests
import sys

def main():
    parser = argparse.ArgumentParser("agent_myagent")
    parser.add_argument("--hostname", required=True, help="Target hostname")
    parser.add_argument("--port", type=int, default=8080, help="API port")
    parser.add_argument("--username", help="API username")
    parser.add_argument("--password", help="API password")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds")
    
    args = parser.parse_args()
    
    try:
        # Build URL
        url = f"http://{args.hostname}:{args.port}/api/status"
        
        # Optional authentication
        auth = None
        if args.username and args.password:
            auth = (args.username, args.password)
        
        # Make request
        response = requests.get(url, auth=auth, timeout=args.timeout)
        response.raise_for_status()
        data = response.json()
        
        # Output agent section
        print("<<<myagent:sep(0)>>>")
        print(json.dumps(data))
        
        # Multiple sections possible
        print("<<<myagent_details>>>")
        for item, details in data.get("items", {}).items():
            print(f"{item};{details['status']};{details['value']}")
        
    except requests.RequestException as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"Invalid JSON response: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

**Important:** Make the file executable!
```bash
chmod 755 ~/local/lib/python3/cmk_addons/plugins/myagent/libexec/agent_myagent
```

## 2. Rule Configuration

Location: `rulesets/special_agent.py`

```python
#!/usr/bin/env python3

from cmk.rulesets.v1 import Title, Label, Help
from cmk.rulesets.v1.form_specs import (
    Dictionary,
    DictElement,
    String,
    Integer,
    Password,
    BooleanChoice,
    DefaultValue,
    migrate_to_password,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _formspec():
    return Dictionary(
        title=Title("My Special Agent"),
        help_text=Help("Configure the special agent for My Service"),
        elements={
            "port": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("API Port"),
                    prefill=DefaultValue(8080),
                ),
            ),
            "username": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("Username"),
                ),
            ),
            "password": DictElement(
                required=False,
                parameter_form=Password(
                    title=Title("Password"),
                    migrate=migrate_to_password,
                ),
            ),
            "timeout": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Connection timeout"),
                    prefill=DefaultValue(30),
                ),
            ),
            "verify_ssl": DictElement(
                required=False,
                parameter_form=BooleanChoice(
                    title=Title("Verify SSL certificate"),
                    prefill=DefaultValue(True),
                ),
            ),
        },
    )


rule_spec_myagent = SpecialAgent(
    name="myagent",                    # Links to agent_myagent
    title=Title("My Special Agent"),
    topic=Topic.GENERAL,               # Or APPLICATIONS, CLOUD, etc.
    parameter_form=_formspec,
)
```

## 3. Call Configuration

Location: `server_side_calls/special_agent.py`

```python
#!/usr/bin/env python3

from cmk.server_side_calls.v1 import (
    noop_parser,
    SpecialAgentConfig,
    SpecialAgentCommand,
)


def _agent_arguments(params, host_config):
    """
    Convert GUI parameters to command line arguments.
    
    params: Dictionary from ruleset
    host_config: Host configuration object with:
        - host_config.name: Host name
        - host_config.primary_ip_config.address: IP address
        - host_config.alias: Host alias
    """
    args = [
        "--hostname", host_config.primary_ip_config.address,
    ]
    
    # Optional parameters
    if "port" in params:
        args.extend(["--port", str(params["port"])])
    
    if "username" in params:
        args.extend(["--username", params["username"]])
    
    if "password" in params:
        # Password is an object, use unsafe() to get plain text
        args.extend(["--password", params["password"].unsafe()])
    
    if "timeout" in params:
        args.extend(["--timeout", str(params["timeout"])])
    
    yield SpecialAgentCommand(command_arguments=args)


special_agent_myagent = SpecialAgentConfig(
    name="myagent",                    # Must match rule_spec name
    parameter_parser=noop_parser,      # Use noop_parser for simple cases
    commands_function=_agent_arguments,
)
```

## 4. Check Plugin (Optional)

Location: `agent_based/myagent.py`

```python
#!/usr/bin/env python3

import json
import itertools
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    Service,
    Result,
    State,
    Metric,
)


def parse_myagent(string_table):
    """Parse JSON output from special agent."""
    if not string_table:
        return None
    
    # Flatten nested list and join
    flatlist = list(itertools.chain.from_iterable(string_table))
    json_str = " ".join(flatlist).replace("'", '"')
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None


def discover_myagent(section):
    if section:
        for item in section.get("items", {}):
            yield Service(item=item)


def check_myagent(item, section):
    if not section:
        yield Result(state=State.UNKNOWN, summary="No data received")
        return
    
    items = section.get("items", {})
    data = items.get(item)
    
    if not data:
        yield Result(state=State.UNKNOWN, summary="Item not found")
        return
    
    status = data.get("status", "unknown")
    value = data.get("value", 0)
    
    if status == "ok":
        state = State.OK
    elif status == "warning":
        state = State.WARN
    else:
        state = State.CRIT
    
    yield Result(state=state, summary=f"Status: {status}")
    yield Metric("myagent_value", value)


agent_section_myagent = AgentSection(
    name="myagent",
    parse_function=parse_myagent,
)

check_plugin_myagent = CheckPlugin(
    name="myagent",
    service_name="My Agent %s",
    discovery_function=discover_myagent,
    check_function=check_myagent,
)
```

## Host Configuration

For the special agent to run, configure the host:

1. Go to **Setup > Hosts > Properties of host**
2. In **Monitoring agents** section:
   - Set **Checkmk agent / API integrations** to one of:
     - "Configured API integrations and Checkmk agent"
     - "Configured API integrations, no Checkmk agent"
     - "API integrations if configured, else Checkmk agent"

3. Create a rule at **Setup > Agents > Other integrations > My Special Agent**

## Testing

```bash
# Test the executable directly
~/local/lib/python3/cmk_addons/plugins/myagent/libexec/agent_myagent \
    --hostname 192.168.1.100 --port 8080

# After rule configuration, test via CheckMK
cmk -d myhost --debug

# Service discovery
cmk -vI --detect-plugins=myagent myhost

# Execute check
cmk -v --detect-plugins=myagent myhost
```

## Password Handling Security

**Warning:** Passwords passed as command line arguments are visible in the process table!

Mitigate with one of:

1. **Environment variables:**
```python
import os

def _agent_arguments(params, host_config):
    # In server_side_calls
    os.environ["MYAGENT_PASSWORD"] = params["password"].unsafe()
    yield SpecialAgentCommand(command_arguments=args)

# In agent executable
password = os.environ.get("MYAGENT_PASSWORD")
```

2. **Stdin:**
```python
# In server_side_calls
yield SpecialAgentCommand(
    command_arguments=args,
    stdin=params["password"].unsafe(),
)

# In agent executable
password = sys.stdin.read().strip()
```

3. **Python module setproctitle:**
```python
# In agent executable
try:
    import setproctitle
    setproctitle.setproctitle("agent_myagent")
except ImportError:
    pass
```

## SSL Verification Gotchas

### session.verify = False Doesn't Work Reliably!

**GOTCHA:** Setting `verify` on a `requests.Session` object doesn't reliably disable SSL verification. You must pass `verify=` explicitly to each request!

```python
# WRONG - may still fail with SSL certificate errors!
session = requests.Session()
session.verify = False
session.get(url)  # Can still verify SSL!

# CORRECT - pass verify explicitly to each request
session.get(url, verify=False)
session.post(url, data, verify=False)
```

### Suppress urllib3 Warnings

When disabling SSL verification, suppress the noisy warnings:

```python
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
```

### Complete SSL Pattern for Special Agents

```python
#!/usr/bin/env python3
import argparse
import json
import sys
import requests

try:
    import urllib3
except ImportError:
    urllib3 = None


class APIClient:
    def __init__(self, hostname, port, verify_ssl=True, timeout=30):
        self.base_url = f"https://{hostname}:{port}"
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.session = requests.Session()

        # Suppress warnings when SSL verification is disabled
        if not verify_ssl and urllib3:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def get(self, endpoint):
        url = f"{self.base_url}{endpoint}"
        # Always pass verify= explicitly!
        return self.session.get(url, verify=self.verify_ssl, timeout=self.timeout)

    def post(self, endpoint, data):
        url = f"{self.base_url}{endpoint}"
        return self.session.post(url, json=data, verify=self.verify_ssl, timeout=self.timeout)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hostname", required=True)
    parser.add_argument("--port", type=int, default=443)
    parser.add_argument("--no-verify-ssl", action="store_true")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    client = APIClient(
        hostname=args.hostname,
        port=args.port,
        verify_ssl=not args.no_verify_ssl,
        timeout=args.timeout,
    )

    try:
        response = client.get("/api/status")
        response.raise_for_status()
        data = response.json()

        print("<<<myagent:sep(0)>>>")
        print(json.dumps(data))

    except requests.RequestException as e:
        sys.stderr.write(f"API Error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### Passing verify_ssl from Ruleset

In `server_side_calls/special_agent.py`:

```python
def _agent_arguments(params, host_config):
    args = ["--hostname", host_config.primary_ip_config.address]

    # Pass SSL verification setting
    if not params.get("verify_ssl", True):
        args.append("--no-verify-ssl")

    yield SpecialAgentCommand(command_arguments=args)
```

## Topic Options for Rule Placement

```python
Topic.APPLICATIONS           # Application monitoring
Topic.CLOUD                  # Cloud monitoring
Topic.CONFIGURATION_MANAGEMENT  # Config management
Topic.DATABASES              # Database monitoring
Topic.ENVIRONMENTAL          # Environment/sensors
Topic.GENERAL               # General / Various
Topic.LINUX                 # Linux specific
Topic.MIDDLEWARE            # Middleware
Topic.NETWORKING            # Network monitoring
Topic.NOTIFICATIONS         # Notification systems
Topic.OPERATING_SYSTEM      # OS monitoring
Topic.PERIPHERALS           # Peripheral devices
Topic.POWER                 # Power supply
Topic.SERVER_HARDWARE       # Server hardware
Topic.STORAGE               # Storage systems
Topic.SYNTHETIC_MONITORING  # Synthetic monitoring
Topic.VIRTUALIZATION        # Virtualization
Topic.WINDOWS               # Windows specific
```

## Minimal Example (Hello World)

The simplest possible special agent with just three files:

### 1. Executable (`libexec/agent_hellospecial`)

```bash
#!/bin/bash
echo '<<<local>>>'
echo '0 "Hello special" - This static service is always OK'
```

```bash
chmod 755 ~/local/lib/python3/cmk_addons/plugins/hellospecial/libexec/agent_hellospecial
```

### 2. Rule Configuration (`rulesets/special_agent.py`)

```python
#!/usr/bin/env python3
from cmk.rulesets.v1.form_specs import Dictionary
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic, Help, Title

def _formspec():
    return Dictionary(
        title=Title("Hello special!"),
        help_text=Help("Minimal special agent demonstration."),
        elements={}
    )

rule_spec_hellospecial = SpecialAgent(
    topic=Topic.GENERAL,
    name="hellospecial",
    title=Title("Hello special!"),
    parameter_form=_formspec
)
```

### 3. Call Configuration (`server_side_calls/special_agent.py`)

```python
#!/usr/bin/env python3
from cmk.server_side_calls.v1 import noop_parser, SpecialAgentConfig, SpecialAgentCommand

def _agent_arguments(params, host_config):
    yield SpecialAgentCommand(command_arguments=[])

special_agent_hellospecial = SpecialAgentConfig(
    name="hellospecial",
    parameter_parser=noop_parser,
    commands_function=_agent_arguments
)
```

After creating files, restart: `omd restart apache`

## Troubleshooting

### Rule Not Visible in "Other integrations"

**Cause:** Syntax error in `rulesets/special_agent.py`

**Check:**
```bash
# View web server errors
tail -f ~/var/log/web.log

# Example error:
# Error converting to legacy rulespec 'myagent': name 'migrate_to_password' is not defined
```

**Fix:** Check imports and syntax in the ruleset file.

### Check_MK Service Shows WARN/CRIT

**Cause:** Special agent configured but host settings incorrect

**Fix:** In host properties, set **Checkmk agent / API integrations** to:
- "Configured API integrations and Checkmk agent" (to use both)
- "Configured API integrations, no Checkmk agent" (special agent only)

### Yellow Warning During "Activate Changes"

**Cause:** Error in `server_side_calls/special_agent.py` or the agent executable

**Debug:**
```bash
# Test agent execution
cmk -d myhost --debug | less

# Example error:
# KeyError: 'username'  # Trying to access non-existent param
```

**Fix:** Check that all params accessed in `_agent_arguments()` exist in the ruleset.

### No Data From Special Agent

**Debug:**
```bash
# Test executable directly
~/local/lib/python3/cmk_addons/plugins/myagent/libexec/agent_myagent \
    --hostname 192.168.1.100 --port 8080

# Check agent output through CheckMK
cmk -d myhost --debug | less
```

### Service Not Discovered

**Check:**
1. Agent outputs valid section header: `<<<mysection>>>`
2. Check plugin name matches section name
3. Discovery function yields services

```bash
# Force rediscovery
cmk -vI --detect-plugins=myagent myhost --debug
```

## Files and Directories

| Path | Description |
|------|-------------|
| `~/local/lib/python3/cmk_addons/plugins/<family>/` | Base directory for plugin files |
| `<family>/libexec/` | Executable special agents |
| `<family>/server_side_calls/` | Call configuration |
| `<family>/rulesets/` | Rule configuration |
| `<family>/agent_based/` | Check plugins for the data |
| `~/lib/python3/cmk/special_agents/` | Built-in special agents |
| `~/local/bin/` | Alternative location for executables (in PATH) |

## Complete Workflow

```
1. Create rule at Setup > Agents > Other integrations > My Agent
                              ↓
2. Rule configuration (rulesets/special_agent.py)
   - Defines GUI form elements
   - Returns params dictionary
                              ↓
3. Call configuration (server_side_calls/special_agent.py)
   - Receives params + host_config
   - Yields SpecialAgentCommand with CLI arguments
                              ↓
4. Special agent executable (libexec/agent_myagent)
   - Receives CLI arguments
   - Queries external system
   - Outputs agent sections to stdout
                              ↓
5. Check plugin (agent_based/myagent.py)
   - Parses agent sections
   - Discovers services
   - Checks and yields Results
```

## Best Practices

1. **No file extension** for executables in `libexec/`
2. **Make executable**: `chmod 755`
3. **Use site user** for file creation (not root)
4. **Name consistency**: `agent_myagent` → `rule_spec_myagent` → `special_agent_myagent`
5. **Password via stdin** for better security
6. **Always yield** `SpecialAgentCommand` (even with empty args)
7. **String conversion**: All command arguments must be strings
8. **Error handling**: Write errors to stderr, exit with non-zero code
9. **Restart Apache** after ruleset changes: `omd restart apache`
