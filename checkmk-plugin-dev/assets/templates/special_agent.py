#!/usr/bin/env python3
"""
Special Agent Executable Template
=================================
Location: ~/local/lib/python3/cmk_addons/plugins/<family>/libexec/agent_myagent
Note: NO .py extension! Make executable: chmod 755 agent_myagent

This script queries an API and outputs data in Checkmk agent format.
"""

import argparse
import json
import sys

# Optional: requests for HTTP APIs
try:
    import requests
except ImportError:
    requests = None


def parse_arguments():
    """Parse command line arguments passed from server_side_calls."""
    parser = argparse.ArgumentParser(
        description="My Special Agent",
        prog="agent_myagent",
    )
    
    parser.add_argument(
        "--hostname",
        required=True,
        help="Target hostname or IP address",
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="API port (default: 8080)",
    )
    
    parser.add_argument(
        "--username",
        help="API username",
    )
    
    parser.add_argument(
        "--password",
        help="API password",
    )
    
    parser.add_argument(
        "--protocol",
        choices=["http", "https"],
        default="https",
        help="Protocol (default: https)",
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Connection timeout in seconds (default: 30)",
    )
    
    parser.add_argument(
        "--verify-ssl",
        action="store_true",
        default=True,
        help="Verify SSL certificate",
    )
    
    parser.add_argument(
        "--no-verify-ssl",
        action="store_false",
        dest="verify_ssl",
        help="Do not verify SSL certificate",
    )
    
    return parser.parse_args()


def fetch_data(args):
    """Fetch data from the API."""
    if requests is None:
        sys.stderr.write("Error: requests module not available\n")
        sys.exit(1)
    
    url = f"{args.protocol}://{args.hostname}:{args.port}/api/status"
    
    auth = None
    if args.username and args.password:
        auth = (args.username, args.password)
    
    try:
        response = requests.get(
            url,
            auth=auth,
            timeout=args.timeout,
            verify=args.verify_ssl,
        )
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.ConnectionError as e:
        sys.stderr.write(f"Connection error: {e}\n")
        sys.exit(1)
    except requests.exceptions.Timeout:
        sys.stderr.write(f"Connection timeout after {args.timeout}s\n")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        sys.stderr.write(f"HTTP error: {e}\n")
        sys.exit(1)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"Invalid JSON response: {e}\n")
        sys.exit(1)


def output_section(section_name, data, separator=None):
    """Output a section in Checkmk agent format."""
    if separator:
        print(f"<<<{section_name}:sep({ord(separator)})>>>")
    else:
        print(f"<<<{section_name}>>>")
    
    if isinstance(data, dict):
        # JSON output
        print(json.dumps(data))
    elif isinstance(data, list):
        # Table output
        for row in data:
            if isinstance(row, (list, tuple)):
                print(separator.join(str(x) for x in row) if separator else " ".join(str(x) for x in row))
            else:
                print(str(row))
    else:
        print(str(data))


def main():
    args = parse_arguments()
    
    # Fetch data from API
    data = fetch_data(args)
    
    # Output main section (JSON format)
    output_section("myagent", data)
    
    # Output additional structured section
    if "items" in data:
        items_table = []
        for name, item_data in data["items"].items():
            items_table.append([
                name,
                str(item_data.get("value", 0)),
                item_data.get("status", "unknown"),
            ])
        output_section("myagent_items", items_table, separator=";")
    
    # Example: Output simple values
    # output_section("myagent_status", [
    #     ["status", data.get("status", "unknown")],
    #     ["version", data.get("version", "unknown")],
    # ], separator=";")


if __name__ == "__main__":
    main()
