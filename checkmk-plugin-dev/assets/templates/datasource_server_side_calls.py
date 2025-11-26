#!/usr/bin/env python3
"""
Server-side calls configuration for MyCloud special agent.

Location: ~/local/lib/python3/cmk_addons/plugins/mycloud/server_side_calls/special_agent.py
"""

from cmk.server_side_calls.v1 import (
    noop_parser,
    SpecialAgentConfig,
    SpecialAgentCommand,
)


def _agent_arguments(params, host_config):
    """
    Convert GUI parameters to command line arguments.
    
    Parameters:
        params: Dictionary from ruleset form
        host_config: Host configuration object with:
            - host_config.name: Host name
            - host_config.primary_ip_config.address: IP address
            - host_config.alias: Host alias
    
    Yields:
        SpecialAgentCommand with command line arguments
    """
    args = [
        "--hostname", host_config.primary_ip_config.address,
    ]
    
    # Port
    if "port" in params:
        args.extend(["--port", str(params["port"])])
    
    # Authentication
    if "username" in params:
        args.extend(["--username", params["username"]])
    
    if "password" in params:
        # Password object - use unsafe() to get plain text
        # Consider using stdin for better security (see below)
        args.extend(["--password", params["password"].unsafe()])
    
    # Optional parameters
    if "timeout" in params:
        args.extend(["--timeout", str(params["timeout"])])
    
    if not params.get("verify_ssl", True):
        args.append("--no-cert-check")
    
    if params.get("debug"):
        args.append("--debug")
    
    if params.get("no_piggyback"):
        args.append("--no-piggyback")
    
    yield SpecialAgentCommand(command_arguments=args)


# Alternative: Passwort via stdin (sicherer!)
def _agent_arguments_secure(params, host_config):
    """Alternative version with password via stdin (more secure)."""
    args = [
        "--hostname", host_config.primary_ip_config.address,
    ]
    
    if "port" in params:
        args.extend(["--port", str(params["port"])])
    
    if "username" in params:
        args.extend(["--username", params["username"]])
    
    if "timeout" in params:
        args.extend(["--timeout", str(params["timeout"])])
    
    if not params.get("verify_ssl", True):
        args.append("--no-cert-check")
    
    # Password via stdin
    stdin_data = None
    if "password" in params:
        stdin_data = params["password"].unsafe()
    
    yield SpecialAgentCommand(
        command_arguments=args,
        stdin=stdin_data,
    )


# Variable name MUST start with special_agent_
special_agent_mycloud = SpecialAgentConfig(
    name="mycloud",                     # Must match ruleset name
    parameter_parser=noop_parser,       # Use noop_parser for simple params
    commands_function=_agent_arguments,
)
