"""Command-line interface for the VLSM calculator."""

import argparse
import json
import sys

from .vlsm import NetworkRequest, VLSMError, allocation_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Professional IPv4 VLSM calculator")
    parser.add_argument("parent", help="Parent IPv4 network, e.g. 192.168.10.0/24")
    parser.add_argument(
        "--subnet", action="append", nargs=2, metavar=("NAME", "HOSTS"), required=True,
        help="Requested subnet; repeat for each LAN, e.g. --subnet Users 100",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        requests = [NetworkRequest(name, int(hosts)) for name, hosts in args.subnet]
        report = allocation_report(args.parent, requests)
    except (ValueError, VLSMError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print(f"VLSM allocation for {report['parent_network']}")
    print(f"Address space: {report['allocated_addresses']:,} allocated / "
          f"{report['parent_total_addresses']:,} total; "
          f"{report['remaining_addresses']:,} remaining\n")
    headers = ("NAME", "REQUEST", "NETWORK", "MASK", "USABLE RANGE", "BROADCAST", "FREE")
    rows = []
    for item in report["allocations"]:
        rows.append((item["name"], str(item["requested_hosts"]), item["network"],
                     item["netmask"], f"{item['first_usable']} - {item['last_usable']}",
                     item["broadcast_address"], str(item["unused_hosts"])))
    widths = [max(len(headers[i]), *(len(row[i]) for row in rows)) for i in range(len(headers))]
    print(" | ".join(headers[i].ljust(widths[i]) for i in range(len(headers))))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(" | ".join(row[i].ljust(widths[i]) for i in range(len(row))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
