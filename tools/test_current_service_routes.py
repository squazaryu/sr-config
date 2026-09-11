"""Regression guards for the simplified grouped iOS service routing."""

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

    def test_documented_openai_auxiliary_hosts_remain_inline(self):
        expected = (
            "DOMAIN-SUFFIX,oaistatsig.com,AI",
            "DOMAIN-SUFFIX,intercom.io,AI",
            "DOMAIN-SUFFIX,intercomcdn.com,AI",
            "DOMAIN-SUFFIX,ct.sendgrid.net,AI",
            "DOMAIN-SUFFIX,featuregates.org,AI",
            "DOMAIN-SUFFIX,segment.io,AI",
            "DOMAIN-SUFFIX,statsig.com,AI",
            "DOMAIN-SUFFIX,statsigapi.net,AI",
            "DOMAIN-SUFFIX,featureassets.org,AI",
            "DOMAIN-SUFFIX,prodregistryv2.org,AI",
            "DOMAIN,cdn.openaimerge.com,AI",
            "DOMAIN,cdn.workos.com,AI",
            "DOMAIN,challenges.cloudflare.com,AI",
            "DOMAIN,forwarder.workos.com,AI",
            "DOMAIN,images.workoscdn.com,AI",
            "DOMAIN,js.stripe.com,AI",
            "DOMAIN,o207216.ingest.sentry.io,AI",
            "DOMAIN,o33249.ingest.sentry.io,AI",
            "DOMAIN,rum.browser-intake-datadoghq.com,AI",
            "DOMAIN,setup.workos.com,AI",
            "DOMAIN,workos.imgix.net,AI",
        )
        for rule in expected:
            with self.subTest(rule=rule):
                self.assertIn(rule, self.rules)

    def test_inline_ai_routes_precede_remote_lists(self):
        boundary = next(i for i, rule in enumerate(self.rules) if rule.startswith("RULE-SET,"))
        for rule in (
            "DOMAIN-SUFFIX,chatgpt.com,AI",
            "DOMAIN-SUFFIX,openai.com,AI",
            "DOMAIN-SUFFIX,oaistatic.com,AI",
            "DOMAIN-SUFFIX,oaiusercontent.com,AI",
            "DOMAIN,challenges.cloudflare.com,AI",
            "DOMAIN-SUFFIX,oaistatsig.com,AI",
            "DOMAIN,cdn.workos.com,AI",
            "DOMAIN,o33249.ingest.sentry.io,AI",
        ):
            with self.subTest(rule=rule):
                self.assertLess(self.rules.index(rule), boundary)

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

    def test_ai_delegates_to_finland_without_nested_url_test(self):
        self.assertEqual(self.groups["AI"], "select,FINLAND,policy-select-name=FINLAND")

    def test_mail_provider_domains_have_explicit_smtp_and_imap_routes(self):
        expected = (
            "DOMAIN-SUFFIX,mail.me.com,DIRECT",
            "DOMAIN-SUFFIX,mail.ru,DIRECT",
            "DOMAIN-SUFFIX,yandex.com,DIRECT",
            "DOMAIN-SUFFIX,gmail.com,PROXY",
            "DOMAIN-SUFFIX,googlemail.com,PROXY",
            "DOMAIN,accounts.google.com,PROXY",
        )
        boundary = next(i for i, rule in enumerate(self.rules) if rule.startswith("RULE-SET,"))
        for rule in expected:
            with self.subTest(rule=rule):
                self.assertIn(rule, self.rules[:boundary])

    def test_instagram_remains_a_separate_proxy_group(self):
        self.assertEqual(
            self.groups["INSTAGRAM"],
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
        self.assertTrue(all(rule.split(",")[2] == "INSTAGRAM" for rule in meta_rules))

    def test_no_experimental_transport_geoip_or_broad_proxy_sets_remain(self):
        self.assertFalse(any(rule.startswith(("AND,", "DST-PORT,")) for rule in self.rules))
        self.assertNotIn("GEOIP,RU,DIRECT", self.rules)
        self.assertFalse(any("misha-tgshv/" in rule or "helmiau/" in rule for rule in self.rules))
        self.assertEqual(self.rules[-1], "FINAL,PROXY")

    def test_fallback_matches_the_current_source_snapshots(self):
        self.assertEqual(build_failsafe.CONFIG_PATH.read_text(encoding="utf-8"), build_failsafe.build())


if __name__ == "__main__":
    unittest.main()
