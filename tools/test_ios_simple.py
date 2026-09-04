"""Static checks for the isolated experiment, not a Shadowrocket/IP emulator."""

import ipaddress
import unittest
from pathlib import Path

import validate_configs as validation


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "url-set-ios-simple-test.conf"
UPDATE_URL = (
    "update-url = https://raw.githubusercontent.com/squazaryu/sr-config/main/"
    "url-set-ios-simple-test.conf"
)
FINLAND_NODES = [
    "🇫🇮 PROXY TG | ФИНЛЯНДИЯ", "🇫🇮 FASTCON VPN | ФИНЛЯНДИЯ",
    "🇫🇮 SODA VPN | ФИНЛЯНДИЯ", "🇫🇮 HIT VPN | ФИНЛЯНДИЯ",
    "🇫🇮 ALL VPN | ФИНЛЯНДИЯ", "🇫🇮 ДАРВИН ВПН | ФИНЛЯНДИЯ",
    "🇫🇮 FASTCOM VPN | ФИНЛЯНДИЯ",
]


def section(lines, name):
    return validation.meaningful(validation.section_lines(lines, name))


def domain_policy(rules, hostname):
    """Domain-only order check. Does not evaluate GEOIP, DNS, transport or IP rules."""
    for line in rules:
        fields = line.split(",")
        kind = fields[0]
        if kind == "FINAL":
            return fields[1]
        if kind == "DOMAIN" and hostname == fields[1]:
            return fields[2]
        if kind == "DOMAIN-SUFFIX" and (hostname == fields[1] or hostname.endswith("." + fields[1])):
            return fields[2]
        if kind == "DOMAIN-KEYWORD" and fields[1] in hostname:
            return fields[2]
    return None


class SimpleIOSConfigTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(PROFILE.is_file(), "The requested separate test profile must exist")
        self.text = PROFILE.read_text(encoding="utf-8")
        self.lines = self.text.splitlines()
        self.rules = section(self.lines, "[Rule]")
        self.groups = {
            name.strip(): [field.strip() for field in value.split(",")]
            for line in section(self.lines, "[Proxy Group]")
            for name, value in [line.split("=", 1)]
        }

    def test_isolated_profile_and_frozen_network_settings(self):
        self.assertEqual([line for line in self.lines if line.startswith("[")],
                         ["[General]", "[Proxy Group]", "[Rule]"])
        reference = (ROOT / "tools/fixtures/ios-f08.conf").read_text().splitlines()
        general = section(self.lines, "[General]")
        self.assertEqual([line for line in general if line.startswith("update-url")], [UPDATE_URL])
        self.assertEqual([line for line in general if not line.startswith("update-url")],
                         section(reference, "[General]"))

    def test_three_flat_manual_groups(self):
        self.assertEqual(set(self.groups), {"TEST-FI", "TEST-MEDIA", "TEST-ADS"})
        self.assertEqual(len(section(self.lines, "[Proxy Group]")), 3)
        for name, fields in self.groups.items():
            with self.subTest(group=name):
                self.assertEqual(fields[0], "select")
                members = [field for field in fields[1:] if "=" not in field]
                options = dict(field.split("=", 1) for field in fields[1:] if "=" in field)
                self.assertEqual(set(options), {"policy-select-name"})
                self.assertIn(options["policy-select-name"], members)
                self.assertFalse(set(members) & set(self.groups))
        self.assertEqual(self.groups["TEST-FI"], ["select", *FINLAND_NODES, "PROXY",
                         "policy-select-name=🇫🇮 ALL VPN | ФИНЛЯНДИЯ"])
        self.assertEqual(self.groups["TEST-MEDIA"], ["select", "PREMIUM | ALL IN 1",
                         "BASE | ALL IN 1", "PROXY", "policy-select-name=PREMIUM | ALL IN 1"])
        self.assertEqual(self.groups["TEST-ADS"], ["select", "REJECT", "DIRECT", "policy-select-name=REJECT"])

    def test_no_remote_lists_extra_matching_or_secrets(self):
        active = validation.meaningful(self.lines)
        self.assertFalse(any(line.startswith(("RULE-SET,", "DOMAIN-SET,")) for line in active))
        self.assertFalse(any("pre-matching" in line or "extended-matching" in line for line in active))
        self.assertIsNone(validation.SECRET_PATTERN.search(self.text))
        self.assertLess(len(self.rules), 350)

    def test_ai_spotify_weather_and_russian_domain_lists_are_embedded(self):
        sources = {
            "ai-services.list": "TEST-FI", "spotify.list": "TEST-FI",
            "weather.list": "PROXY", "telegram-domains.list": "PROXY",
            "ru-direct-domains.list": "DIRECT", "apple.list": "DIRECT",
            "trackers.list": "TEST-ADS",
        }
        for filename, policy in sources.items():
            for rule in validation.meaningful((ROOT / "lists" / filename).read_text().splitlines()):
                with self.subTest(source=filename, rule=rule):
                    self.assertIn(f"{rule},{policy}", self.rules)

    def test_all_custom_ip_lists_are_embedded_with_no_resolve(self):
        for filename, policy in (("telegram-ips.list", "PROXY"), ("ru-direct-ips.list", "DIRECT")):
            for rule in validation.meaningful((ROOT / "lists" / filename).read_text().splitlines()):
                self.assertIn(f"{rule},{policy},no-resolve", self.rules)

    def test_core_domain_routes_and_unknown_fallback(self):
        expected = {
            "ios.chat.openai.com": "TEST-FI", "ab.chatgpt.com": "TEST-FI",
            "ws.chatgpt.com": "TEST-FI", "claude.ai": "TEST-FI",
            "gemini.google.com": "TEST-FI", "api.manus.im": "TEST-FI",
            "accounts.spotify.com": "TEST-FI", "location.meetcarrot.com": "PROXY",
            "t.me": "PROXY", "front.platipomiru.com": "PROXY",
            "api.github.com": "DIRECT", "raw.githubusercontent.com": "DIRECT",
            "gdmf.apple.com": "DIRECT", "itunes.apple.com": "DIRECT",
            "iapps.rejail.ru": "DIRECT", "mos.ru": "DIRECT", "emias.info": "DIRECT",
            "imap.mail.ru": "DIRECT", "example.ru": "DIRECT", "vk.com": "DIRECT",
            "api.instagram.com": "TEST-MEDIA", "scontent.cdninstagram.com": "TEST-MEDIA",
            "youtubei.googleapis.com": "TEST-MEDIA", "i.ytimg.com": "TEST-MEDIA",
            "rr1.googlevideo.com": "TEST-MEDIA", "discord.com": "PROXY",
            "fastsign.dev": "TEST-FI", "api.revenuecat.com": "PROXY",
            "google-analytics.com": "TEST-ADS", "unlisted-example.test": "PROXY",
        }
        for host, policy in expected.items():
            with self.subTest(host=host):
                self.assertEqual(domain_policy(self.rules, host), policy)

    def test_apple_github_and_subscription_exceptions_remain_direct_or_proxy(self):
        for rule in validation.APPLE_WATCH_DIRECT_RULES:
            self.assertIn(rule, self.rules)
        for host in validation.GITHUB_DIRECT_DOMAINS:
            self.assertIn(f"DOMAIN-SUFFIX,{host},DIRECT", self.rules)
        self.assertEqual(self.rules[:3], [f"DOMAIN,{host},PROXY" for host in
                         ("shdnetwork.website", "sub.alvsub.cc", "your-durev.com")])

    def test_telegram_snapshot_asns_and_ipv6_remain_proxy(self):
        for asn in (211157, 44907, 59930, 62014, 62041):
            self.assertIn(f"IP-ASN,{asn},PROXY,no-resolve", self.rules)
        self.assertIn("IP-CIDR6,2001:b28:f23c::/47,PROXY,no-resolve", self.rules)

    def test_youtube_transport_and_meta_ip_routes_remain(self):
        for rule in validation.IOS_YOUTUBE_QUIC_RULES:
            self.assertIn(rule, self.rules)
            self.assertLess(self.rules.index(rule), self.rules.index("DOMAIN-SUFFIX,youtube.com,TEST-MEDIA"))
        for rule in (*validation.IOS_YOUTUBE_CRITICAL_RULES, *validation.IOS_INSTAGRAM_CRITICAL_RULES):
            self.assertIn(validation.with_rule_policy(rule, "TEST-MEDIA"), self.rules)
        self.assertFalse(any(line.startswith("AND,") and "instagram" in line for line in self.rules))

    def test_geoip_and_final_order(self):
        self.assertEqual(self.rules.count("GEOIP,RU,DIRECT"), 1)
        self.assertEqual([rule for rule in self.rules if rule.startswith("FINAL,")], ["FINAL,PROXY"])
        self.assertEqual(self.rules[-1], "FINAL,PROXY")
        geoip_index = self.rules.index("GEOIP,RU,DIRECT")
        for rule in self.rules:
            if rule.endswith(",TEST-FI") or ",TEST-MEDIA" in rule:
                self.assertLess(self.rules.index(rule), geoip_index)

    def test_unique_rules_valid_networks_and_defined_policies(self):
        self.assertEqual(len(self.rules), len(set(self.rules)))
        allowed = set(self.groups) | {"PROXY", "DIRECT", "REJECT-NO-DROP"}
        for rule in self.rules:
            fields = rule.split(",")
            policy = fields[1] if fields[0] == "FINAL" else fields[2]
            if fields[0] == "AND":
                policy = fields[-1]
            self.assertIn(policy, allowed, rule)
            if fields[0] in ("IP-CIDR", "IP-CIDR6"):
                network = ipaddress.ip_network(fields[1], strict=False)
                self.assertEqual(network.version, 6 if fields[0] == "IP-CIDR6" else 4, rule)

    def test_shared_structural_checks(self):
        errors = []
        validation.validate_structure("ios-simple-test", self.lines, errors)
        validation.validate_general("ios-simple-test", self.lines, errors)
        validation.validate_apple_watch_rules("ios-simple-test", self.lines, errors)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
