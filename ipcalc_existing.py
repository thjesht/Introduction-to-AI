#!/usr/bin/env python3
"""
Professional IP Calculator
--------------------------
IPv4/IPv6 subnet calculator inspired by the feature set of jodies.de/ipcalc.

Features:
- IPv4 and IPv6 address/interface parsing
- CIDR prefix and IPv4 dotted-decimal netmask input
- Network, netmask, wildcard, broadcast and usable host range
- Private/public, loopback, multicast, link-local and reserved classification
- Binary representation for IPv4
- Subnet splitting and supernet calculation
- JSON output
- Input validation and safe subnet output limits

Python: 3.9+
No third-party dependencies.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import sys
from typing import Any, Dict, Iterable, Optional


APP_NAME = "Professional IP Calculator"
VERSION = "1.0.0"
DEFAULT_SUBNET_LIMIT = 256


def parse_network(
    address: str,
    netmask: Optional[str] = None,
    strict: bool = False,
) -> ipaddress.IPv4Network | ipaddress.IPv6Network:
    """Parse CIDR notation or an address with an optional netmask."""
    address = address.strip()

    if not address:
        raise ValueError("An IP address or network is required.")

    if netmask:
        if "/" in address:
            raise ValueError("Specify the prefix in the address OR use --netmask, not both.")
        if ":" in address:
            raise ValueError("Dotted-decimal netmasks are only valid for IPv4.")
        candidate = f"{address}/{netmask.strip()}"
    else:
        candidate = address

    try:
        return ipaddress.ip_network(candidate, strict=strict)
    except ValueError as exc:
        # Give a useful hint when a bare host address was supplied.
        if "/" not in candidate:
            try:
                ip = ipaddress.ip_address(candidate)
                return ipaddress.ip_network(f"{ip}/{ip.max_prefixlen}", strict=True)
            except ValueError:
                pass
        raise ValueError(f"Invalid IP/network or netmask: {exc}") from exc


def classify_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> list[str]:
    labels = []
    checks = (
        ("Private", ip.is_private),
        ("Global/Public", ip.is_global),
        ("Loopback", ip.is_loopback),
        ("Link-local", ip.is_link_local),
        ("Multicast", ip.is_multicast),
        ("Reserved", ip.is_reserved),
        ("Unspecified", ip.is_unspecified),
    )
    for label, matched in checks:
        if matched:
            labels.append(label)
    return labels or ["Unclassified"]


def binary_ipv4(value: ipaddress.IPv4Address | ipaddress.IPv4Network) -> str:
    """Return dotted 8-bit binary octets."""
    address = value if isinstance(value, ipaddress.IPv4Address) else value.network_address
    return ".".join(f"{octet:08b}" for octet in address.packed)


def ipv4_wildcard(network: ipaddress.IPv4Network) -> str:
    inverse = (1 << 32) - 1 - int(network.netmask)
    return str(ipaddress.IPv4Address(inverse))


def host_range(
    network: ipaddress.IPv4Network | ipaddress.IPv6Network,
) -> tuple[str, str, int]:
    """Return first usable host, last usable host and usable host count."""
    if network.version == 4:
        if network.prefixlen >= 31:
            # RFC 3021: both addresses are usable on /31 point-to-point links.
            if network.prefixlen == 31:
                return str(network.network_address), str(network.broadcast_address), 2
            # A /32 represents one host route.
            return str(network.network_address), str(network.network_address), 1

        return (
            str(network.network_address + 1),
            str(network.broadcast_address - 1),
            max(network.num_addresses - 2, 0),
        )

    # IPv6 has no broadcast address; all addresses in the prefix are counted.
    return (
        str(network.network_address),
        str(network.broadcast_address),
        network.num_addresses,
    )


def network_report(
    network: ipaddress.IPv4Network | ipaddress.IPv6Network,
    include_binary: bool = True,
    input_ip: Optional[ipaddress.IPv4Address | ipaddress.IPv6Address] = None,
) -> Dict[str, Any]:
    first_host, last_host, usable_hosts = host_range(network)
    ip = input_ip or network.network_address

    report: Dict[str, Any] = {
        "version": f"IPv{network.version}",
        "address": str(ip),
        "network": str(network),
        "prefix_length": network.prefixlen,
        "netmask": str(network.netmask),
        "wildcard_mask": ipv4_wildcard(network) if network.version == 4 else None,
        "network_address": str(network.network_address),
        "broadcast_address": (
            str(network.broadcast_address) if network.version == 4 else None
        ),
        "first_usable_host": first_host,
        "last_usable_host": last_host,
        "total_addresses": network.num_addresses,
        "usable_hosts": usable_hosts,
        "ip_classification": classify_ip(ip),
    }

    if include_binary and network.version == 4:
        report["binary"] = {
            "address": binary_ipv4(ip),
            "netmask": binary_ipv4(network.netmask),
            "wildcard_mask": binary_ipv4(ipaddress.IPv4Address(ipv4_wildcard(network))),
            "network": binary_ipv4(network.network_address),
            "broadcast": binary_ipv4(network.broadcast_address),
        }

    return report


def subnet_report(
    network: ipaddress.IPv4Network | ipaddress.IPv6Network,
    target_prefix: int,
    limit: int,
) -> Dict[str, Any]:
    """Split into smaller subnets or calculate the containing supernet."""
    max_prefix = network.max_prefixlen
    if not 0 <= target_prefix <= max_prefix:
        raise ValueError(f"Prefix must be between 0 and {max_prefix}.")

    if target_prefix == network.prefixlen:
        return {
            "operation": "unchanged",
            "target_prefix": target_prefix,
            "message": "The target prefix is identical to the original prefix.",
            "subnets": [str(network)],
        }

    if target_prefix < network.prefixlen:
        parent = network.supernet(new_prefix=target_prefix)
        return {
            "operation": "supernet",
            "target_prefix": target_prefix,
            "supernet": str(parent),
            "message": "Containing supernet calculated. This does not prove that adjacent networks are allocated to you.",
        }

    count = 1 << (target_prefix - network.prefixlen)
    if count > limit:
        raise ValueError(
            f"This would create {count:,} subnets, exceeding the safety limit "
            f"of {limit:,}. Increase --limit if you really need the full list."
        )

    children = [str(item) for item in network.subnets(new_prefix=target_prefix)]
    return {
        "operation": "subnet",
        "target_prefix": target_prefix,
        "subnet_count": count,
        "addresses_per_subnet": 1 << (max_prefix - target_prefix),
        "subnets": children,
    }


def print_text(report: Dict[str, Any], subnet_data: Optional[Dict[str, Any]]) -> None:
    print(f"\n{APP_NAME} v{VERSION}")
    print("=" * 66)
    print(f"IP Version          : {report['version']}")
    print(f"Address             : {report['address']}")
    print(f"Network             : {report['network']}")
    print(f"Netmask             : {report['netmask']}")
    if report["wildcard_mask"] is not None:
        print(f"Wildcard Mask       : {report['wildcard_mask']}")
    print(f"Network Address     : {report['network_address']}")
    if report["broadcast_address"] is not None:
        print(f"Broadcast Address   : {report['broadcast_address']}")
    print(f"First Usable Host   : {report['first_usable_host']}")
    print(f"Last Usable Host    : {report['last_usable_host']}")
    print(f"Total Addresses     : {report['total_addresses']:,}")
    print(f"Usable Hosts        : {report['usable_hosts']:,}")
    print(f"Classification      : {', '.join(report['ip_classification'])}")

    if "binary" in report:
        print("\nBinary representation")
        print("-" * 66)
        for key, value in report["binary"].items():
            print(f"{key.replace('_', ' ').title():20}: {value}")

    if subnet_data:
        print("\nSubnet / Supernet analysis")
        print("-" * 66)
        print(f"Operation           : {subnet_data['operation']}")
        print(f"Target prefix       : /{subnet_data['target_prefix']}")
        if "supernet" in subnet_data:
            print(f"Supernet            : {subnet_data['supernet']}")
            print(f"Note                : {subnet_data['message']}")
        else:
            if "subnet_count" in subnet_data:
                print(f"Subnet count        : {subnet_data['subnet_count']:,}")
                print(f"Addresses per subnet: {subnet_data['addresses_per_subnet']:,}")
            for index, subnet in enumerate(subnet_data["subnets"], start=1):
                print(f"{index:4}. {subnet}")
            if "message" in subnet_data:
                print(f"Note                : {subnet_data['message']}")

    print("\n" + "=" * 66)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ipcalc.py",
        description=(
            "Professional IPv4/IPv6 calculator: network, broadcast, host range, "
            "wildcard mask, binary output, subnetting and supernetting."
        ),
        epilog=(
            "Examples:\n"
            "  python ipcalc.py 192.168.1.10/24\n"
            "  python ipcalc.py 192.168.1.10 --netmask 255.255.255.0\n"
            "  python ipcalc.py 10.10.0.0/16 --subnet-prefix 24\n"
            "  python ipcalc.py 10.10.5.0/24 --subnet-prefix 20\n"
            "  python ipcalc.py 2001:db8::1/64 --json\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("address", help="IP address or CIDR network, e.g. 192.168.1.10/24")
    parser.add_argument(
        "-m", "--netmask",
        help="IPv4 dotted netmask or prefix length, e.g. 255.255.255.0 or 24",
    )
    parser.add_argument(
        "-s", "--subnet-prefix",
        type=int,
        help="Optional target prefix for subnetting or supernetting, e.g. 26",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_SUBNET_LIMIT,
        help=f"Maximum number of child subnets to print (default: {DEFAULT_SUBNET_LIMIT})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON",
    )
    parser.add_argument(
        "--no-binary",
        action="store_true",
        help="Skip IPv4 binary representation",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Reject host bits set in the supplied network address",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.limit < 1:
        parser.error("--limit must be at least 1.")

    try:
        network = parse_network(args.address, args.netmask, strict=args.strict)
        raw_ip = args.address.split("/", 1)[0].strip()
        input_ip = ipaddress.ip_address(raw_ip)
        report = network_report(
            network, include_binary=not args.no_binary, input_ip=input_ip
        )

        subnet_data = None
        if args.subnet_prefix is not None:
            subnet_data = subnet_report(network, args.subnet_prefix, args.limit)

        if args.json:
            payload = {"calculator": APP_NAME, "version": VERSION, "result": report}
            if subnet_data is not None:
                payload["subnet_analysis"] = subnet_data
            print(json.dumps(payload, indent=2))
        else:
            print_text(report, subnet_data)

        return 0

    except (ValueError, TypeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
