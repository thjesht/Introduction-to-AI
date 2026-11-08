"""IPv4 VLSM allocation engine.

Allocates requested LANs from a parent IPv4 network, largest host requirement
first, without overlapping subnets. Uses only the Python standard library.
"""

from __future__ import annotations

import ipaddress
from dataclasses import asdict, dataclass
from typing import Iterable, List, Union

IPv4Network = ipaddress.IPv4Network


class VLSMError(ValueError):
    """Raised when a VLSM request is invalid or cannot fit in the parent."""


@dataclass(frozen=True)
class NetworkRequest:
    name: str
    hosts: int


@dataclass(frozen=True)
class VLSMAllocation:
    name: str
    requested_hosts: int
    network: str
    prefix: int
    netmask: str
    network_address: str
    first_usable: str
    last_usable: str
    broadcast_address: str
    total_addresses: int
    usable_hosts: int
    unused_hosts: int

    def to_dict(self) -> dict:
        return asdict(self)


def _required_prefix(hosts: int) -> int:
    """Return the smallest IPv4 prefix with at least `hosts` usable addresses.

    This uses conventional LAN subnet accounting: network and broadcast
    addresses are reserved, so a /31 or /32 is not used for LAN allocation.
    """
    if isinstance(hosts, bool) or not isinstance(hosts, int) or hosts < 1:
        raise VLSMError("Host requirements must be positive integers.")
    host_bits = 2
    while (1 << host_bits) - 2 < hosts:
        host_bits += 1
    if host_bits > 32:
        raise VLSMError(f"Host requirement {hosts:,} exceeds IPv4 capacity.")
    return 32 - host_bits


def allocate_vlsm(
    parent: Union[str, IPv4Network],
    requests: Iterable[NetworkRequest],
) -> List[VLSMAllocation]:
    """Allocate non-overlapping IPv4 subnets, largest request first.

    The input order is preserved for requests with equal host counts.
    `parent` may include host bits; it is normalized to its network address.
    """
    try:
        parent_net = ipaddress.ip_network(parent, strict=False) if isinstance(parent, str) else parent
    except ValueError as exc:
        raise VLSMError(f"Invalid parent network: {exc}") from exc

    if not isinstance(parent_net, ipaddress.IPv4Network):
        raise VLSMError("VLSM currently supports IPv4 parent networks only.")

    normalized: List[NetworkRequest] = []
    names = set()
    for item in requests:
        if not isinstance(item, NetworkRequest):
            raise VLSMError("Each request must be a NetworkRequest(name, hosts).")
        name = item.name.strip()
        if not name:
            raise VLSMError("Every subnet request must have a non-empty name.")
        if name in names:
            raise VLSMError(f"Duplicate subnet name: {name}")
        _required_prefix(item.hosts)
        names.add(name)
        normalized.append(NetworkRequest(name=name, hosts=item.hosts))

    if not normalized:
        raise VLSMError("At least one subnet request is required.")

    # Stable sort: largest subnet first; same-size requests keep user order.
    ordered = sorted(normalized, key=lambda request: request.hosts, reverse=True)
    cursor = int(parent_net.network_address)
    parent_end = int(parent_net.broadcast_address)
    allocations: List[VLSMAllocation] = []

    for request in ordered:
        prefix = _required_prefix(request.hosts)
        block_size = 1 << (32 - prefix)
        network_start = ((cursor + block_size - 1) // block_size) * block_size
        network_end = network_start + block_size - 1

        if network_start < int(parent_net.network_address) or network_end > parent_end:
            raise VLSMError(
                f"Insufficient address space in {parent_net}: "
                f"'{request.name}' needs /{prefix} ({block_size:,} addresses)."
            )

        subnet = ipaddress.IPv4Network((network_start, prefix))
        usable = max(subnet.num_addresses - 2, 0)
        allocations.append(
            VLSMAllocation(
                name=request.name,
                requested_hosts=request.hosts,
                network=str(subnet),
                prefix=prefix,
                netmask=str(subnet.netmask),
                network_address=str(subnet.network_address),
                first_usable=str(subnet.network_address + 1),
                last_usable=str(subnet.broadcast_address - 1),
                broadcast_address=str(subnet.broadcast_address),
                total_addresses=subnet.num_addresses,
                usable_hosts=usable,
                unused_hosts=usable - request.hosts,
            )
        )
        cursor = network_end + 1

    return allocations


def allocation_report(parent: str, requests: Iterable[NetworkRequest]) -> dict:
    """Return a JSON-serializable report for CLI/API/UI consumers."""
    parent_net = ipaddress.ip_network(parent, strict=False)
    allocations = allocate_vlsm(parent_net, requests)
    used = sum(item.total_addresses for item in allocations)
    return {
        "parent_network": str(parent_net),
        "parent_total_addresses": parent_net.num_addresses,
        "allocated_addresses": used,
        "remaining_addresses": parent_net.num_addresses - used,
        "allocations": [item.to_dict() for item in allocations],
    }
