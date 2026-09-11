"""Verify the iOS hybrid profile used for a controlled runtime A/B test."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
HYBRID = ROOT / "archive/2026-09-10/url-set-ios-hybrid-test.conf"


def section(text, name):
    lines = text.splitlines()
    start = lines.index(name) + 1
    end = next((i for i in range(start, len(lines))
                if lines[i].startswith("[") and lines[i].endswith("]")), len(lines))
    result = lines[start:end]
    while result and not result[-1].strip():
        result.pop()
    return result


class HybridProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hybrid = HYBRID.read_text(encoding="utf-8")

    def test_general_is_the_reference_profile(self):
        self.assertEqual(
            section(self.hybrid, "[General]"),
            [
                "hijack-dns = 8.8.8.8,1.1.1.1",
                "always-real-ip = *.apple.com,apple.com",
                "bypass-system = true",
                "skip-proxy = 192.168.0.0/16,10.0.0.0/8,172.16.0.0/12,localhost,*.local,captive.apple.com,apple.com,*.apple.com,whoer.net",
                "tun-excluded-routes = 10.0.0.0/8, 100.64.0.0/10, 127.0.0.0/8, 169.254.0.0/16, 172.16.0.0/12, 192.0.0.0/24, 192.0.2.0/24, 192.88.99.0/24, 192.168.0.0/16, 198.51.100.0/24, 203.0.113.0/24, 224.0.0.0/4, 255.255.255.255/32, 239.255.255.250/32",
                "dns-server = system",
                "fallback-dns-server = system",
                "ipv6 = false",
                "prefer-ipv6 = false",
                "dns-fallback-system = false",
                "dns-direct-system = false",
                "icmp-auto-reply = true",
                "always-reject-url-rewrite = false",
                "private-ip-answer = true",
                "dns-direct-fallback-proxy = true",
                "udp-policy-not-supported-behaviour = REJECT",
            ],
        )

    def test_hybrid_keeps_its_explicit_ai_override_and_frozen_rules(self):
        hybrid_groups = section(self.hybrid, "[Proxy Group]")
        hybrid_rules = section(self.hybrid, "[Rule]")
        self.assertEqual(
            next(line for line in hybrid_groups if line.startswith("AI =")),
            "AI = url-test,FINLAND 🇫🇮,🇫🇮 ФИНЛЯНДИЯ,"
            "FINLAND 42 🇫🇮 → [📃 БЕЛЫЕ СПИСКИ]-2,"
            "FINLAND 52 🇫🇮 → [📃 БЕЛЫЕ СПИСКИ]-2,"
            "interval=600,tolerance=100,timeout=5,"
            "url=http://www.gstatic.com/generate_204",
        )
        self.assertIn("DOMAIN-SUFFIX,chatgpt.com,AI", hybrid_rules)
        self.assertIn("GEOIP,RU,DIRECT", hybrid_rules)
        self.assertEqual(hybrid_rules[-1], "FINAL,PROXY")

    def test_hybrid_is_not_an_auto_updating_primary_profile(self):
        self.assertFalse(any(line.startswith("update-url =")
                             for line in section(self.hybrid, "[General]")))


if __name__ == "__main__":
    unittest.main()
