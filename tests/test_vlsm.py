import unittest

from network_toolkit.vlsm import NetworkRequest, VLSMError, allocate_vlsm, allocation_report


class VLSMTests(unittest.TestCase):
    def test_allocates_largest_first_and_expected_prefixes(self):
        result = allocate_vlsm("192.168.10.0/24", [
            NetworkRequest("Users", 100),
            NetworkRequest("Servers", 50),
            NetworkRequest("Voice", 20),
            NetworkRequest("Management", 10),
        ])
        self.assertEqual([item.prefix for item in result], [25, 26, 27, 28])
        self.assertEqual([item.network for item in result], [
            "192.168.10.0/25", "192.168.10.128/26",
            "192.168.10.192/27", "192.168.10.224/28",
        ])

    def test_no_overlap(self):
        result = allocate_vlsm("10.0.0.0/16", [
            NetworkRequest("A", 500), NetworkRequest("B", 200), NetworkRequest("C", 50)
        ])
        networks = [__import__("ipaddress").ip_network(item.network) for item in result]
        for index, left in enumerate(networks):
            for right in networks[index + 1:]:
                self.assertFalse(left.overlaps(right))

    def test_insufficient_space(self):
        with self.assertRaises(VLSMError):
            allocate_vlsm("192.168.1.0/28", [NetworkRequest("LAN", 30)])

    def test_rejects_ipv6(self):
        with self.assertRaises(VLSMError):
            allocate_vlsm("2001:db8::/64", [NetworkRequest("LAN", 10)])

    def test_rejects_duplicate_names(self):
        with self.assertRaises(VLSMError):
            allocate_vlsm("10.0.0.0/24", [
                NetworkRequest("LAN", 10), NetworkRequest("LAN", 5)
            ])

    def test_rejects_zero_hosts(self):
        with self.assertRaises(VLSMError):
            allocate_vlsm("10.0.0.0/24", [NetworkRequest("LAN", 0)])

    def test_report_totals(self):
        report = allocation_report("192.168.1.0/24", [NetworkRequest("LAN", 50)])
        self.assertEqual(report["allocated_addresses"], 64)
        self.assertEqual(report["remaining_addresses"], 192)


if __name__ == "__main__":
    unittest.main()
