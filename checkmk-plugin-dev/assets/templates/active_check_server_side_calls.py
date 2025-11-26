#!/usr/bin/env python3
"""
Active Check Server-Side Calls Template
========================================
Location: ~/local/lib/python3/cmk_addons/plugins/<family>/server_side_calls/

This file maps ruleset configuration to command line arguments for the active check.

The executable must be located at:
- ~/local/lib/nagios/plugins/check_<name>
- OR ~/local/lib/python3/cmk_addons/plugins/<family>/libexec/check_<name>

The variable name MUST start with "active_check_" prefix.
The "name" parameter determines which executable is called: check_<name>
"""

from collections.abc import Iterator, Mapping
from typing import Any

from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    HostConfig,
    Secret,
)


# =============================================================================
# COMMAND GENERATOR FUNCTION
# =============================================================================

def generate_myservice_commands(
    params: Mapping[str, Any],
    host_config: HostConfig,
) -> Iterator[ActiveCheckCommand]:
    """
    Generate command line arguments for the active check.
    
    Args:
        params: Configuration from ruleset (user input from GUI)
        host_config: Host information (name, IP, labels, etc.)
    
    Yields:
        ActiveCheckCommand instances (one per service to create)
    
    Available host_config attributes:
        host_config.name                    - Host name
        host_config.alias                   - Host alias
        host_config.primary_ip_config.address  - Primary IP address
        host_config.macros                  - Host macros dict
    """
    
    # Build command line arguments
    args: list[str | Secret] = []
    
    # Host: Use configured value or fall back to host address
    host = params.get("host")
    if not host:
        host = host_config.primary_ip_config.address
    args.extend(["-H", host])
    
    # Port (required)
    port = params.get("port", 443)
    args.extend(["-p", str(port)])
    
    # Timeout (optional)
    if "timeout" in params:
        args.extend(["-t", str(params["timeout"])])
    
    # Thresholds (optional)
    # Params format from SimpleLevels: ("fixed", (warn, crit)) or ("no_levels", None)
    if "response_time" in params:
        levels = params["response_time"]
        if isinstance(levels, tuple) and len(levels) == 2:
            if levels[0] == "fixed" and levels[1]:
                warn, crit = levels[1]
                args.extend(["-w", str(warn), "-c", str(crit)])
        elif isinstance(levels, tuple) and len(levels) == 2:
            # Direct tuple format
            warn, crit = levels
            args.extend(["-w", str(warn), "-c", str(crit)])
    
    # HTTP mode options
    if params.get("http_mode"):
        args.append("--http")
        
        if params.get("use_ssl"):
            args.append("--ssl")
        
        if "path" in params:
            args.extend(["--path", params["path"]])
        
        if "expected_code" in params:
            args.extend(["--expected-code", str(params["expected_code"])])
    
    # TCP mode options
    else:
        if "send_string" in params:
            args.extend(["--send", params["send_string"]])
        
        if "expect_string" in params:
            args.extend(["--expect", params["expect_string"]])
    
    # Password handling (if your check needs authentication)
    # The Secret type ensures passwords are handled securely
    if "password" in params:
        password = params["password"]
        if isinstance(password, Secret):
            args.extend(["--password", password])
        else:
            # Handle legacy format or plain string
            args.extend(["--password", Secret(password)])
    
    # Service description
    # Can be static or dynamic based on configuration
    service_description = params.get("service_description")
    if not service_description:
        # Auto-generate based on check parameters
        protocol = "HTTPS" if params.get("use_ssl") else "HTTP" if params.get("http_mode") else "TCP"
        service_description = f"{protocol} {host}:{port}"
    
    # Yield one command per service
    # Most active checks yield just one command, but you can yield multiple
    # to create multiple services from a single rule
    yield ActiveCheckCommand(
        service_description=service_description,
        command_arguments=args,
    )


# =============================================================================
# MULTIPLE SERVICES EXAMPLE
# =============================================================================

def generate_multi_service_commands(
    params: Mapping[str, Any],
    host_config: HostConfig,
) -> Iterator[ActiveCheckCommand]:
    """
    Example: Generate multiple services from one rule.
    Useful for checking multiple ports or endpoints.
    """
    host = params.get("host") or host_config.primary_ip_config.address
    
    # Check multiple ports from a single rule
    ports = params.get("ports", [80, 443])
    
    for port in ports:
        args = ["-H", host, "-p", str(port)]
        
        if port == 443:
            args.extend(["--http", "--ssl"])
        elif port == 80:
            args.append("--http")
        
        yield ActiveCheckCommand(
            service_description=f"Port {port} on {host}",
            command_arguments=args,
        )


# =============================================================================
# ACTIVE CHECK REGISTRATION
# =============================================================================

# Variable name MUST start with "active_check_"
# The "name" parameter determines which executable is called
# CheckMK will look for: ~/local/lib/nagios/plugins/check_myservice

active_check_myservice = ActiveCheckConfig(
    name="myservice",  # Corresponds to executable "check_myservice"
    parameter_parser=lambda params: params,  # Use params as-is from ruleset
    commands_function=generate_myservice_commands,
)


# =============================================================================
# ALTERNATIVE: WITH PARAMETER TRANSFORMATION
# =============================================================================

def parse_myservice_params(params: Mapping[str, Any]) -> Mapping[str, Any]:
    """
    Optional: Transform parameters before passing to command generator.
    
    Useful for:
    - Setting defaults
    - Converting data formats
    - Validating configuration
    """
    # Create a mutable copy
    parsed = dict(params)
    
    # Set defaults
    parsed.setdefault("port", 443)
    parsed.setdefault("timeout", 10)
    
    # Convert SimpleLevels format to simple tuple
    if "response_time" in parsed:
        levels = parsed["response_time"]
        if isinstance(levels, tuple) and levels[0] == "fixed":
            parsed["response_time"] = levels[1]
    
    return parsed


# Alternative registration with parameter parsing
# active_check_myservice_v2 = ActiveCheckConfig(
#     name="myservice",
#     parameter_parser=parse_myservice_params,
#     commands_function=generate_myservice_commands,
# )


# =============================================================================
# NOTES ON SECRET HANDLING
# =============================================================================
"""
For checks that need passwords or API keys:

1. In ruleset, use Password() form spec
2. In server_side_calls, use Secret type:

    from cmk.server_side_calls.v1 import Secret
    
    if "password" in params:
        args.extend(["--password", params["password"]])  # Already a Secret
    
3. In executable, password is passed via command line or environment
   CheckMK handles secure storage and retrieval

For extra security, consider using --pwstore format:
    args.extend(["--pwstore", f"{password_id}@{index}@{ident}"])
"""


# =============================================================================
# NOTES ON HOST MACROS
# =============================================================================
"""
Available macros via host_config.macros:
    $HOSTNAME$      - Host name
    $HOSTADDRESS$   - Primary IP
    $HOSTALIAS$     - Host alias
    $USER1$         - Plugin directory
    $_HOSTADDRESS_4$ - IPv4 address
    $_HOSTADDRESS_6$ - IPv6 address
    $_HOST<CUSTOM>$ - Custom host attributes

Example usage:
    custom_attr = host_config.macros.get("$_HOSTMYATTR$", "default")
"""
