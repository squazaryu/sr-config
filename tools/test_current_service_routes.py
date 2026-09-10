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

    def test_finland_pool_contains_the_user_added_nodes(self):
        self.assertEqual(
            self.groups["FINLAND"],
            "url-test,FINLAND 🇫🇮,🇫🇮 ФИНЛЯНДИЯ,"
            "FINLAND 42 🇫🇮 → [📃 БЕЛЫЕ СПИСКИ]-2,"
            "FINLAND 52 🇫🇮 → [📃 БЕЛЫЕ СПИСКИ]-2,"
            "🇫🇮 ФИНЛЯНДИЯ | РЕКЛАМА НА ЮТУБЕ,"
            "policy-select-name=FINLAND 🇫🇮,interval=300,tolerance=100,"
            "timeout=5,url=http://www.gstatic.com/generate_204",
        )

    def test_ai_delegates_to_the_finland_group(self):
        self.assertEqual(
            self.groups["AI"],
            "url-test,FINLAND,interval=600,tolerance=100,timeout=5,"
            "url=http://www.gstatic.com/generate_204",
        )

    def test_mail_provider_domains_have_explicit_smtp_and_imap_routes(self):
        expected_direct = (
            "DOMAIN-SUFFIX,mail.me.com,DIRECT",
            "DOMAIN-SUFFIX,mail.ru,DIRECT",
            "DOMAIN-SUFFIX,yandex.com,DIRECT",
        )
        expected_proxy = (
            "DOMAIN-SUFFIX,gmail.com,PROXY",
            "DOMAIN-SUFFIX,googlemail.com,PROXY",
            "DOMAIN,accounts.google.com,PROXY",
        )
        for rule in expected_direct + expected_proxy:
            with self.subTest(rule=rule):
                self.assertIn(rule, self.rules)

        boundary = next(i for i, rule in enumerate(self.rules)
                        if rule.startswith(("RULE-SET,", "GEOIP,")))
        for rule in expected_direct + expected_proxy:
            with self.subTest(position=rule):
                self.assertIn(rule, self.rules[:boundary])

    def test_instagram_isolated_group_routes_all_meta_rules_through_proxy(self):
        self.assertEqual(
            self.groups.get("INSTAGRAM"),
            "select,SERVERS,PROXY,AUTO,FINLAND,DIRECT,policy-select-name=AUTO",
        )
        meta_rules = [
            rule for rule in self.rules
            if rule.startswith((
                "DOMAIN-SUFFIX,instagram.com,",
                "DOMAIN-SUFFIX,instagr.am,",
                "DOMAIN-SUFFIX,cdninstagram.com,",
                "DOMAIN-SUFFIX,ig.",
                "DOMAIN-SUFFIX,igcdn.com,",
                "DOMAIN-SUFFIX,igsonar.com,",
                "DOMAIN-SUFFIX,igtv.com,",
                "DOMAIN-SUFFIX,facebook.com,",
                "DOMAIN-SUFFIX,facebook.net,",
                "DOMAIN-SUFFIX,fb.",
                "DOMAIN-SUFFIX,fbcdn.com,",
                "DOMAIN-SUFFIX,fbcdn.net,",
                "DOMAIN-SUFFIX,fbsbx",
                "DOMAIN-SUFFIX,meta.com,",
                "DOMAIN-SUFFIX,messenger.com,",
                "DOMAIN-SUFFIX,m.me,",
                "DOMAIN-SUFFIX,threads.net,",
                "DOMAIN-SUFFIX,fbcdn-a.akamaihd.net,",
                "DOMAIN-KEYWORD,instagram,",
                "IP-ASN,32934,",
                "IP-ASN,63293,",
                "IP-CIDR,31.13.64.0/18,",
                "IP-CIDR,129.134.0.0/17,",
                "IP-CIDR,157.240.0.0/17,",
                "IP-CIDR,173.252.64.0/18,",
                "IP-CIDR6,2A03:2880::/32,",
            ))
        ]
        self.assertEqual(len(meta_rules), 28)
        for rule in meta_rules:
            with self.subTest(rule=rule):
                self.assertEqual(rule.split(",")[2], "INSTAGRAM")

    def test_instagram_has_a_separate_proxy_group(self):
        self.assertEqual(
            self.groups.get("INSTAGRAM"),
            "select,SERVERS,PROXY,AUTO,FINLAND,DIRECT,policy-select-name=AUTO",
        )
        meta_prefixes = (
            "DOMAIN-SUFFIX,instagram.com",
            "DOMAIN-SUFFIX,instagr.am",
            "DOMAIN-SUFFIX,cdninstagram.com",
            "DOMAIN-SUFFIX,facebook.com",
            "DOMAIN-SUFFIX,fbcdn.net",
            "DOMAIN-SUFFIX,meta.com",
            "DOMAIN-SUFFIX,messenger.com",
            "DOMAIN-SUFFIX,threads.net",
            "DOMAIN-KEYWORD,instagram",
            "IP-ASN,32934",
            "IP-ASN,63293",
            "IP-CIDR6,2A03:2880::/32",
        )
        for prefix in meta_prefixes:
            matches = [rule for rule in self.rules if rule.startswith(prefix + ",")]
            with self.subTest(prefix=prefix):
                self.assertEqual(len(matches), 1)
                self.assertEqual(matches[0].split(",")[2], "INSTAGRAM")

    def test_fallback_matches_the_current_source_snapshots(self):
        self.assertEqual(
            build_failsafe.CONFIG_PATH.read_text(encoding="utf-8"),
            build_failsafe.build(),
        )


if __name__ == "__main__":
    unittest.main()
