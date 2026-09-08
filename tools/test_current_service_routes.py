"""Regression guards for the current iOS service routing contract."""

from pathlib import Path
import unittest

import build_failsafe
import validate_configs as validation


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "url-set-ios.conf"


def rules(lines):
    return validation.meaningful(validation.section_lines(lines, "[Rule]"))


def groups(lines):
    return {
        name.strip(): value.strip()
        for line in validation.meaningful(validation.section_lines(lines, "[Proxy Group]"))
        for name, value in [line.split("=", 1)]
    }


class CurrentServiceRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lines = PROFILE.read_text(encoding="utf-8").splitlines()
        cls.rules = rules(cls.lines)
        cls.groups = groups(cls.lines)

    def test_feather_catalogs_use_the_general_proxy_for_availability(self):
        for domain in ("getutm.app", "fastsign.dev", "apptesters.org", "hottubapp.io", "stikdebug.xyz"):
            with self.subTest(domain=domain):
                self.assertIn(f"DOMAIN-SUFFIX,{domain},PROXY", self.rules)
                self.assertNotIn(f"DOMAIN-SUFFIX,{domain},DIRECT", self.rules)
                self.assertNotIn(f"DOMAIN-SUFFIX,{domain},FINLAND", self.rules)

    def test_missing_openai_auxiliary_hosts_are_inline_ai_routes(self):
        expected = (
            "DOMAIN-SUFFIX,featuregates.org,AI",
            "DOMAIN-SUFFIX,segment.io,AI",
            "DOMAIN-SUFFIX,statsig.com,AI",
            "DOMAIN-SUFFIX,statsigapi.net,AI",
            "DOMAIN-SUFFIX,featureassets.org,AI",
            "DOMAIN-SUFFIX,prodregistryv2.org,AI",
            "DOMAIN,turn.livekit.cloud,AI",
            "DOMAIN,host.livekit.cloud,AI",
        )
        for rule in expected:
            with self.subTest(rule=rule):
                self.assertIn(rule, self.rules)

    def test_auxiliary_ai_routes_precede_remote_lists_and_geoip(self):
        boundary = next(i for i, rule in enumerate(self.rules)
                        if rule.startswith(("RULE-SET,", "GEOIP,")))
        for rule in (
            "DOMAIN-SUFFIX,featuregates.org,AI",
            "DOMAIN-SUFFIX,segment.io,AI",
            "DOMAIN-SUFFIX,statsig.com,AI",
            "DOMAIN-SUFFIX,statsigapi.net,AI",
            "DOMAIN,turn.livekit.cloud,AI",
            "DOMAIN,host.livekit.cloud,AI",
        ):
            self.assertIn(rule, self.rules[:boundary])

    def test_spotify_pool_is_unchanged(self):
        self.assertEqual(
            self.groups["SPOTIFY"],
            "url-test,🇫🇮 ALL VPN | ФИНЛЯНДИЯ,🇫🇮 PROXY TG | ФИНЛЯНДИЯ,"
            "🇫🇮 ДАРВИН ВПН | ФИНЛЯНДИЯ,🇫🇮 SODA VPN | ФИНЛЯНДИЯ,"
            "🇫🇮 HIT VPN | ФИНЛЯНДИЯ,🇫🇮 FASTCOM VPN | ФИНЛЯНДИЯ,"
            "policy-select-name=🇫🇮 ALL VPN | ФИНЛЯНДИЯ,interval=600,"
            "tolerance=100,timeout=5,url=http://www.gstatic.com/generate_204",
        )

    def test_fallback_matches_the_current_source_snapshots(self):
        self.assertEqual(
            build_failsafe.CONFIG_PATH.read_text(encoding="utf-8"),
            build_failsafe.build(),
        )


if __name__ == "__main__":
    unittest.main()
