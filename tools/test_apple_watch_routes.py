"""Guard the local IPv6 mDNS route needed by Apple device discovery."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "url-set-ios.conf"


class AppleWatchRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lines = PROFILE.read_text(encoding="utf-8").splitlines()

    def test_ipv6_mdns_is_excluded_from_the_tun(self):
        routes = next(line for line in self.lines if line.startswith("tun-excluded-routes ="))
        self.assertIn("ff02::fb/128", routes.split("=", 1)[1].split(","))


if __name__ == "__main__":
    unittest.main()
