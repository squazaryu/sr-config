"""Guard the Apple/watchOS direct routes without adding transport overrides."""

from pathlib import Path
import unittest

import validate_configs as validation


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "url-set-ios.conf"


class AppleWatchRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lines = PROFILE.read_text(encoding="utf-8").splitlines()

    def test_apple_watch_update_and_certificate_routes_are_direct(self):
        rules = validation.meaningful(validation.section_lines(self.lines, "[Rule]"))
        for required in validation.APPLE_WATCH_DIRECT_RULES:
            with self.subTest(rule=required):
                self.assertEqual(rules.count(required), 1)

    def test_primary_does_not_add_the_unproven_mdns_tun_override(self):
        routes = next(line for line in self.lines if line.startswith("tun-excluded-routes ="))
        self.assertNotIn("ff02::fb/128", routes.split("=", 1)[1].split(","))

    def test_observed_apple_relay_is_direct_before_external_sources(self):
        rules = validation.meaningful(validation.section_lines(self.lines, "[Rule]"))
        relay_rule = "DOMAIN,apple-relay.fastly-edge.com,DIRECT"
        first_external = next(i for i, rule in enumerate(rules) if rule.startswith("RULE-SET,"))
        self.assertEqual(rules.count(relay_rule), 1)
        self.assertLess(rules.index(relay_rule), first_external)


if __name__ == "__main__":
    unittest.main()
