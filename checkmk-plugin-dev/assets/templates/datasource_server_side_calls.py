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
              (raises ValueError if the host has no IP address configured)
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
        # params["password"] is a Secret (never a str). It only works inside
        # command_arguments - NOT in stdin= or os.environ (both need a str).
        # CheckMK 2.5 (recommended): pass the password-store reference; the agent
        # resolves it with cmk.password_store.v1_unstable.resolve_secret_option
        args.extend(["--password-id", params["password"]])
        # CheckMK 2.4 (also works on 2.5): plaintext on the command line
        # args.extend(["--password", params["password"].unsafe()])
    
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


# Variable name MUST start with special_agent_
special_agent_mycloud = SpecialAgentConfig(
    name="mycloud",                     # Must match ruleset name
    parameter_parser=noop_parser,       # Use noop_parser for simple params
    commands_function=_agent_arguments,
)
