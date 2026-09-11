"""Verify the Apple Watch A/B profile isolates local Apple/TUN handling."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PRIMARY = ROOT / "url-set-ios.conf"
PROFILE = ROOT / "archive/2026-09-11/url-set-ios-watch-apple-bypass-test.conf"


def section(text, name):
    lines = text.splitlines()
    start = lines.index(name) + 1
    end = next((i for i in range(start, len(lines))
                if lines[i].startswith("[") and lines[i].endswith("]")), len(lines))
    result = lines[start:end]
    while result and not result[-1].strip():
        result.pop()
    return result


class WatchAppleBypassProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = PROFILE.read_text(encoding="utf-8")
        cls.primary = PRIMARY.read_text(encoding="utf-8")

    def test_apple_domains_bypass_shadowrocket_proxy_processing(self):
        skip_proxy = next(line for line in section(self.profile, "[General]")
                          if line.startswith("skip-proxy ="))
        values = skip_proxy.split("=", 1)[1].split(",")
        for value in ("apple.com", "*.apple.com", "icloud.com", "*.icloud.com",
                      "icloud-content.com", "*.icloud-content.com",
                      "apple-cloudkit.com", "*.apple-cloudkit.com"):
            self.assertIn(value, values)

    def test_canary_cannot_be_overwritten_by_the_primary_update_url(self):
        self.assertFalse(any(line.startswith("update-url =")
                             for line in section(self.profile, "[General]")))

    def test_local_ipv6_ranges_stay_out_of_the_tun(self):
        routes = next(line for line in section(self.profile, "[General]")
                      if line.startswith("tun-excluded-routes ="))
        values = routes.split("=", 1)[1].split(",")
        for value in ("::1/128", "fe80::/10", "ff02::fb/128"):
            self.assertIn(value, values)

    def test_groups_and_rules_match_the_primary_profile(self):
        self.assertEqual(section(self.profile, "[Proxy Group]"),
                         section(self.primary, "[Proxy Group]"))
        self.assertEqual(section(self.profile, "[Rule]"),
                         section(self.primary, "[Rule]"))


if __name__ == "__main__":
    unittest.main()
