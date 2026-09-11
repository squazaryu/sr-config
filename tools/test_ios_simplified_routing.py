"""Regression contract for the simplified grouped iOS profile."""

from pathlib import Path
import unittest

import validate_configs as validation


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "url-set-ios.conf"
IOS_UPDATE = "update-url = https://raw.githubusercontent.com/squazaryu/sr-config/main/url-set-ios.conf"

EXPECTED_GROUPS = {
    "AI",
    "SPOTIFY",
    "WEATHER",
    "TELEGRAM",
    "DEFAULT",
    "YOUTUBE",
    "INSTAGRAM",
    "ADS",
    "FINLAND",
    "SERVERS",
    "AUTO",
}

ALLOWED_REMOTE_SOURCES = {
    "raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Shadowrocket/Telegram/Telegram.list",
    "raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Shadowrocket/YouTube/YouTube.list",
    "raw.githubusercontent.com/squazaryu/sr-config/main/lists/ai-services.list",
    "raw.githubusercontent.com/squazaryu/sr-config/main/lists/apple.list",
    "raw.githubusercontent.com/squazaryu/sr-config/main/lists/general-proxy.list",
    "raw.githubusercontent.com/squazaryu/sr-config/main/lists/ru-direct-domains.list",
    "raw.githubusercontent.com/squazaryu/sr-config/main/lists/ru-direct-ips.list",
    "raw.githubusercontent.com/squazaryu/sr-config/main/lists/spotify.list",
    "raw.githubusercontent.com/squazaryu/sr-config/main/lists/telegram-domains.list",
    "raw.githubusercontent.com/squazaryu/sr-config/main/lists/telegram-ips.list",
    "raw.githubusercontent.com/squazaryu/sr-config/main/lists/trackers.list",
    "raw.githubusercontent.com/squazaryu/sr-config/main/lists/weather.list",
    "raw.githubusercontent.com/carrnot/shadowrocket-rules/release/reject.txt",
}


def section(lines, name):
    return validation.meaningful(validation.section_lines(lines, name))


def group_map(lines):
    return {
        name.strip(): value.strip()
        for line in section(lines, "[Proxy Group]")
        for name, value in [line.split("=", 1)]
    }


class SimplifiedIOSRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = PROFILE.read_text(encoding="utf-8")
        cls.lines = cls.text.splitlines()
        cls.rules = section(cls.lines, "[Rule]")
        cls.groups = group_map(cls.lines)

    def test_keeps_only_the_three_supported_sections_and_update_url(self):
        self.assertEqual(
            [line for line in self.lines if line.startswith("[")],
            ["[General]", "[Proxy Group]", "[Rule]"],
        )
        general = section(self.lines, "[General]")
        self.assertEqual([line for line in general if line.startswith("update-url")], [IOS_UPDATE])

    def test_ai_uses_one_finland_group_without_a_second_url_test(self):
        self.assertEqual(self.groups["AI"], "select,FINLAND,policy-select-name=FINLAND")
        self.assertTrue(self.groups["FINLAND"].startswith("url-test,"))
        self.assertIn("FINLAND 🇫🇮", self.groups["FINLAND"])
        self.assertIn("🇫🇮 ФИНЛЯНДИЯ", self.groups["FINLAND"])

    def test_removes_unproven_transport_and_broad_port_overrides(self):
        general = section(self.lines, "[General]")
        self.assertFalse(any(line.startswith("block-quic =") for line in general))
        self.assertFalse(any(line.startswith("AND,") for line in self.rules))
        self.assertFalse(any(line.startswith("DST-PORT,") for line in self.rules))
        self.assertNotIn("ff02::fb/128", next(
            line for line in general if line.startswith("tun-excluded-routes =")
        ).split("=", 1)[1].split(","))

    def test_removes_geoip_and_third_party_broad_proxy_rule_sets(self):
        self.assertNotIn("GEOIP,RU,DIRECT", self.rules)
        sources = [
            line.split(",", 2)[1]
            for line in self.rules
            if line.startswith("RULE-SET,") and line.split(",", 2)[1].startswith("https://")
        ]
        self.assertTrue(sources)
        for source in sources:
            with self.subTest(source=source):
                self.assertIn(source.removeprefix("https://"), ALLOWED_REMOTE_SOURCES)

    def test_uses_one_authoritative_source_per_service_with_small_bootstraps(self):
        for rule in (
            "DOMAIN-SUFFIX,apple.com,DIRECT",
            "DOMAIN-SUFFIX,icloud.com,DIRECT",
            "DOMAIN-SUFFIX,icloud-content.com,DIRECT",
            "DOMAIN-SUFFIX,chatgpt.com,AI",
            "DOMAIN-SUFFIX,openai.com,AI",
            "DOMAIN-SUFFIX,oaistatic.com,AI",
            "DOMAIN-SUFFIX,oaiusercontent.com,AI",
            "DOMAIN-SUFFIX,chatgpt.livekit.cloud,AI",
            "DOMAIN,challenges.cloudflare.com,AI",
            "DOMAIN-SUFFIX,ru,DIRECT",
            "DOMAIN-SUFFIX,su,DIRECT",
            "DOMAIN-SUFFIX,рф,DIRECT",
            "DOMAIN-SUFFIX,getutm.app,PROXY",
            "DOMAIN-SUFFIX,fastsign.dev,PROXY",
            "DOMAIN-SUFFIX,apptesters.org,PROXY",
            "DOMAIN-SUFFIX,hottubapp.io,PROXY",
            "DOMAIN-SUFFIX,stikdebug.xyz,PROXY",
            "DOMAIN-SUFFIX,platipomiru.com,TELEGRAM",
            "DOMAIN-SUFFIX,instagram.com,INSTAGRAM",
            "IP-ASN,32934,INSTAGRAM,no-resolve",
            "DOMAIN-SUFFIX,mail.ru,DIRECT",
            "DOMAIN-SUFFIX,yandex.com,DIRECT",
            "DOMAIN-SUFFIX,gmail.com,PROXY",
            "DOMAIN-SUFFIX,googlemail.com,PROXY",
            "DOMAIN,accounts.google.com,PROXY",
            "FINAL,PROXY",
        ):
            with self.subTest(rule=rule):
                self.assertIn(rule, self.rules)

        self.assertNotIn("*.cloudflareclient.com", next(
            line for line in section(self.lines, "[General]")
            if line.startswith("always-real-ip =")
        ))

    def test_preserves_spotify_and_service_group_controls(self):
        self.assertEqual(
            self.groups["SPOTIFY"],
            "url-test,🇫🇮 ALL VPN | ФИНЛЯНДИЯ,🇫🇮 PROXY TG | ФИНЛЯНДИЯ,"
            "🇫🇮 ДАРВИН ВПН | ФИНЛЯНДИЯ,🇫🇮 SODA VPN | ФИНЛЯНДИЯ,"
            "🇫🇮 HIT VPN | ФИНЛЯНДИЯ,🇫🇮 FASTCOM VPN | ФИНЛЯНДИЯ,"
            "policy-select-name=🇫🇮 ALL VPN | ФИНЛЯНДИЯ,interval=600,"
            "tolerance=100,timeout=5,url=http://www.gstatic.com/generate_204",
        )
        self.assertEqual(set(self.groups), EXPECTED_GROUPS)
        self.assertEqual(self.groups["INSTAGRAM"], "select,SERVERS,PROXY,AUTO,FINLAND,DIRECT,policy-select-name=AUTO")

    def test_required_routes_precede_external_lists(self):
        first_external = next(i for i, line in enumerate(self.rules) if line.startswith("RULE-SET,"))
        for rule in (
            "DOMAIN-SUFFIX,chatgpt.com,AI",
            "DOMAIN-SUFFIX,openai.com,AI",
            "DOMAIN-SUFFIX,apple.com,DIRECT",
            "DOMAIN-SUFFIX,icloud.com,DIRECT",
            "DOMAIN-SUFFIX,ru,DIRECT",
            "DOMAIN-SUFFIX,mail.ru,DIRECT",
            "DOMAIN-SUFFIX,instagram.com,INSTAGRAM",
            "DOMAIN-SUFFIX,platipomiru.com,TELEGRAM",
        ):
            with self.subTest(rule=rule):
                self.assertLess(self.rules.index(rule), first_external)

    def test_shared_validation_accepts_the_simplified_profile(self):
        errors = []
        _groups, parsed_rules = validation.validate_structure("ios-simplified", self.lines, errors)
        validation.validate_general("ios-simplified", self.lines, errors)
        validation.validate_apple_watch_rules("ios-simplified", self.lines, errors)
        validation.validate_sources("ios-simplified", parsed_rules, errors)
        self.assertEqual(errors, [])
        self.assertIsNone(validation.SECRET_PATTERN.search(self.text))


if __name__ == "__main__":
    unittest.main()
