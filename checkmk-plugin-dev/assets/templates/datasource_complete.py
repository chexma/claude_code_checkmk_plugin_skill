#!/usr/bin/env python3
"""
Special Agent Template: Cloud Controller Monitoring

This template demonstrates a complete special agent setup similar to
the CheckMK Nutanix Prism integration. It includes:

- REST API client with error handling
- Main host data collection
- Piggyback data for sub-resources (VMs, Nodes)
- Multiple sections with different separators
- Proper authentication handling
- Rate limiting awareness

Directory structure:
~/local/lib/python3/cmk_addons/plugins/mycloud/
├── libexec/
│   └── agent_mycloud           # This file (executable, no extension!)
├── server_side_calls/
│   └── special_agent.py
├── rulesets/
│   └── special_agent.py
├── agent_based/
│   ├── mycloud_cluster.py
│   ├── mycloud_vms.py
│   └── mycloud_nodes.py
├── graphing/
│   └── mycloud.py
└── checkman/
    ├── mycloud_cluster
    ├── mycloud_vms
    └── mycloud_nodes
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urljoin

# Versuche requests zu importieren, Fallback auf urllib
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    import urllib.error
    import ssl
    HAS_REQUESTS = False


# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.WARNING,
    format='%(levelname)s: %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


# ============================================================================
# API CLIENT
# ============================================================================

class CloudAPIError(Exception):
    """Custom exception for API errors."""
    pass


class CloudAPIClient:
    """REST API client for the cloud controller."""
    
    def __init__(
        self,
        hostname: str,
        port: int,
        username: str,
        password: str,
        verify_ssl: bool = True,
        timeout: int = 30,
    ):
        self.base_url = f"https://{hostname}:{port}/api/v1"
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.session = None
        
        if HAS_REQUESTS:
            self._setup_session()
    
    def _setup_session(self):
        """Setup requests session with auth."""
        self.session = requests.Session()
        self.session.auth = (self.username, self.password)
        self.session.verify = self.verify_ssl
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
    
    def _request(self, endpoint: str, method: str = "GET") -> dict:
        """Make API request."""
        url = urljoin(self.base_url + "/", endpoint.lstrip("/"))
        
        if HAS_REQUESTS:
            return self._request_with_requests(url, method)
        else:
            return self._request_with_urllib(url, method)
    
    def _request_with_requests(self, url: str, method: str) -> dict:
        """Make request using requests library."""
        try:
            response = self.session.request(
                method=method,
                url=url,
                timeout=self.timeout,
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(f"Rate limited, waiting {retry_after}s")
                time.sleep(retry_after)
                return self._request_with_requests(url, method)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.SSLError as e:
            raise CloudAPIError(f"SSL Error: {e}")
        except requests.exceptions.ConnectionError as e:
            raise CloudAPIError(f"Connection Error: {e}")
        except requests.exceptions.Timeout:
            raise CloudAPIError(f"Timeout after {self.timeout}s")
        except requests.exceptions.HTTPError as e:
            raise CloudAPIError(f"HTTP Error: {e}")
        except json.JSONDecodeError:
            raise CloudAPIError("Invalid JSON response")
    
    def _request_with_urllib(self, url: str, method: str) -> dict:
        """Fallback using urllib."""
        import base64
        
        # Setup SSL context
        ctx = ssl.create_default_context()
        if not self.verify_ssl:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        
        # Build request
        req = urllib.request.Request(url, method=method)
        
        # Basic auth
        credentials = base64.b64encode(
            f"{self.username}:{self.password}".encode()
        ).decode()
        req.add_header("Authorization", f"Basic {credentials}")
        req.add_header("Accept", "application/json")
        
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            raise CloudAPIError(f"HTTP Error {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise CloudAPIError(f"URL Error: {e.reason}")
    
    # API Methods
    def get_cluster_info(self) -> dict:
        """Get cluster information."""
        return self._request("/cluster")
    
    def get_nodes(self) -> list:
        """Get all nodes/hosts."""
        return self._request("/nodes")
    
    def get_vms(self) -> list:
        """Get all virtual machines."""
        return self._request("/vms")
    
    def get_storage_pools(self) -> list:
        """Get storage pools."""
        return self._request("/storage/pools")
    
    def get_alerts(self) -> list:
        """Get active alerts."""
        return self._request("/alerts")


# ============================================================================
# OUTPUT FUNCTIONS
# ============================================================================

def output_cluster_sections(cluster: dict, alerts: list, storage: list):
    """Output sections for the main cluster host."""
    
    # Cluster Info - sep(59) = semicolon separated
    print("<<<mycloud_cluster_info:sep(59)>>>")
    print(f"name;{cluster.get('name', 'unknown')}")
    print(f"version;{cluster.get('version', 'unknown')}")
    print(f"uuid;{cluster.get('uuid', '')}")
    print(f"num_nodes;{cluster.get('num_nodes', 0)}")
    print(f"num_vms;{cluster.get('num_vms', 0)}")
    
    # Cluster Stats - sep(0) = JSON
    print("<<<mycloud_cluster_stats:sep(0)>>>")
    stats = {
        "cpu_usage": cluster.get("cpu_usage_percent", 0),
        "memory_usage": cluster.get("memory_usage_percent", 0),
        "storage_usage": cluster.get("storage_usage_percent", 0),
        "iops": cluster.get("iops", 0),
        "throughput": cluster.get("throughput_mbps", 0),
    }
    print(json.dumps(stats))
    
    # Alerts
    print("<<<mycloud_alerts:sep(0)>>>")
    for alert in alerts:
        print(json.dumps({
            "id": alert.get("id"),
            "severity": alert.get("severity"),
            "message": alert.get("message"),
            "created": alert.get("created_at"),
            "acknowledged": alert.get("acknowledged", False),
        }))
    
    # Storage Pools
    print("<<<mycloud_storage:sep(59)>>>")
    for pool in storage:
        print(f"{pool['name']};{pool.get('total_bytes', 0)};{pool.get('used_bytes', 0)};{pool.get('status', 'unknown')}")


def output_vm_piggyback(vm: dict):
    """Output piggyback data for a VM."""
    
    # Sanitize hostname
    vm_name = sanitize_hostname(vm.get("name", "unknown"))
    
    # Start piggyback block
    print(f"<<<<{vm_name}>>>>")
    
    # VM Status
    print("<<<mycloud_vm:sep(59)>>>")
    print(f"uuid;{vm.get('uuid', '')}")
    print(f"power_state;{vm.get('power_state', 'unknown')}")
    print(f"num_vcpus;{vm.get('num_vcpus', 0)}")
    print(f"memory_mb;{vm.get('memory_mb', 0)}")
    print(f"host;{vm.get('host_name', '')}")
    
    # VM Stats (if running)
    if vm.get("power_state") == "ON":
        print("<<<mycloud_vm_stats:sep(0)>>>")
        print(json.dumps({
            "cpu_usage": vm.get("cpu_usage_percent", 0),
            "memory_usage": vm.get("memory_usage_percent", 0),
            "disk_iops": vm.get("disk_iops", 0),
            "network_rx": vm.get("network_rx_bytes", 0),
            "network_tx": vm.get("network_tx_bytes", 0),
        }))
    
    # VM Disks
    disks = vm.get("disks", [])
    if disks:
        print("<<<mycloud_vm_disks:sep(59)>>>")
        for disk in disks:
            print(f"{disk.get('id', '')};{disk.get('size_bytes', 0)};{disk.get('used_bytes', 0)}")
    
    # Guest Tools
    print("<<<mycloud_vm_tools>>>")
    tools = vm.get("guest_tools", {})
    print(f"installed {tools.get('installed', False)}")
    print(f"version {tools.get('version', 'none')}")
    
    # End piggyback block
    print("<<<<>>>>")


def output_node_piggyback(node: dict):
    """Output piggyback data for a hypervisor node."""
    
    node_name = sanitize_hostname(node.get("name", "unknown"))
    
    print(f"<<<<{node_name}>>>>")
    
    # Node Info
    print("<<<mycloud_node:sep(59)>>>")
    print(f"uuid;{node.get('uuid', '')}")
    print(f"state;{node.get('state', 'unknown')}")
    print(f"hypervisor;{node.get('hypervisor_type', '')}")
    print(f"num_vcpus;{node.get('num_vcpus', 0)}")
    print(f"memory_mb;{node.get('memory_mb', 0)}")
    
    # Node Stats
    print("<<<mycloud_node_stats:sep(0)>>>")
    print(json.dumps({
        "cpu_usage": node.get("cpu_usage_percent", 0),
        "memory_usage": node.get("memory_usage_percent", 0),
        "num_vms": node.get("num_vms", 0),
    }))
    
    # NICs
    nics = node.get("nics", [])
    if nics:
        print("<<<mycloud_node_nics:sep(59)>>>")
        for nic in nics:
            print(f"{nic.get('name', '')};{nic.get('mac', '')};{nic.get('speed_mbps', 0)};{nic.get('status', 'unknown')}")
    
    print("<<<<>>>>")


def sanitize_hostname(name: str) -> str:
    """Convert name to valid hostname."""
    import re
    name = name.lower()
    name = re.sub(r'[^a-z0-9-]', '-', name)
    name = re.sub(r'-+', '-', name)
    return name.strip('-')[:63]  # Max 63 chars


# ============================================================================
# MAIN
# ============================================================================

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="CheckMK Special Agent for Cloud Controller"
    )
    
    parser.add_argument(
        "--hostname",
        required=True,
        help="Cloud controller hostname or IP"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9440,
        help="API port (default: 9440)"
    )
    parser.add_argument(
        "--username",
        required=True,
        help="API username"
    )
    parser.add_argument(
        "--password",
        required=True,
        help="API password"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="API timeout in seconds"
    )
    parser.add_argument(
        "--no-cert-check",
        action="store_true",
        help="Disable SSL certificate verification"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output"
    )
    parser.add_argument(
        "--no-piggyback",
        action="store_true",
        help="Disable piggyback output for VMs/Nodes"
    )
    
    return parser.parse_args()


def main():
    args = parse_arguments()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    try:
        # Create API client
        client = CloudAPIClient(
            hostname=args.hostname,
            port=args.port,
            username=args.username,
            password=args.password,
            verify_ssl=not args.no_cert_check,
            timeout=args.timeout,
        )
        
        # Collect data
        logger.debug("Fetching cluster info...")
        cluster = client.get_cluster_info()
        
        logger.debug("Fetching alerts...")
        alerts = client.get_alerts()
        
        logger.debug("Fetching storage pools...")
        storage = client.get_storage_pools()
        
        logger.debug("Fetching VMs...")
        vms = client.get_vms()
        
        logger.debug("Fetching nodes...")
        nodes = client.get_nodes()
        
        # Output cluster sections (main host)
        output_cluster_sections(cluster, alerts, storage)
        
        # Output piggyback data
        if not args.no_piggyback:
            for vm in vms:
                output_vm_piggyback(vm)
            
            for node in nodes:
                output_node_piggyback(node)
        
    except CloudAPIError as e:
        # Output error section so check plugin can report it
        print("<<<mycloud_error>>>")
        print(str(e))
        sys.exit(1)
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
