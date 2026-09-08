"""Static scope and precedence guards; this does not emulate Shadowrocket."""

from pathlib import Path
import unittest

import validate_configs as validation


ROOT = Path(__file__).resolve().parents[1]


class AIRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (ROOT / "url-set-ios-ai-routing.conf").read_text(encoding="utf-8")
        cls.lines = cls.text.splitlines()
        cls.rules = validation.meaningful(validation.section_lines(cls.lines, "[Rule]"))

    def test_changes_are_confined_to_header_and_scoped_routing_blocks(self):
        before_direct, direct_rest = self.text.split("# BEGIN APPLE AND RU DIRECT\n", 1)
        direct_block, after_direct = direct_rest.split("# END APPLE AND RU DIRECT\n\n", 1)
        without_direct = before_direct + after_direct
        zones = "".join(f"DOMAIN-SUFFIX,{zone},DIRECT\n"
                        for zone in ("ru", "su", "рф", "moscow", "tatar"))
        without_direct = without_direct.replace("GEOIP,RU,DIRECT", zones + "GEOIP,RU,DIRECT", 1)
        before, rest = without_direct.split("# BEGIN CHATGPT ROUTING\n", 1)
        block, after = rest.split("# END CHATGPT ROUTING\n\n", 1)
        restored = before.replace(
            "# iOS AI routing revision 2026-09-08; based on url-set-ios-working.conf.\n"
            "# Import as a separate profile. No embedded update-url.",
            "# Shadowrocket: 2026-09-08 12:17:33",
        ) + after
        self.assertEqual(restored, (ROOT / "url-set-ios-working.conf").read_text(encoding="utf-8"))
        self.assertTrue(block.strip())
        self.assertTrue(direct_block.strip())

    def test_core_and_auxiliary_routes_precede_all_remote_and_geoip_rules(self):
        boundary = min(i for i, rule in enumerate(self.rules)
                       if rule.startswith(("RULE-SET,", "GEOIP,")))
        for rule in (
            "DOMAIN-SUFFIX,chatgpt.com,AI",
            "DOMAIN-SUFFIX,openai.com,AI",
            "DOMAIN-SUFFIX,oaistatic.com,AI",
            "DOMAIN-SUFFIX,oaiusercontent.com,AI",
            "DOMAIN-SUFFIX,oaistatsig.com,AI",
            "DOMAIN,challenges.cloudflare.com,AI",
            "DOMAIN,cdn.workos.com,AI",
            "DOMAIN,o33249.ingest.us.sentry.io,AI",
            "DOMAIN-SUFFIX,chatgpt.livekit.cloud,AI",
        ):
            with self.subTest(rule=rule):
                self.assertLess(self.rules.index(rule), boundary)

    def test_quic_guard_is_domain_scoped_and_precedes_core_routes(self):
        for domain in ("chatgpt.com", "openai.com", "oaistatic.com", "oaiusercontent.com"):
            guard = f"AND,((PROTOCOL,UDP),(DST-PORT,443),(DOMAIN-SUFFIX,{domain})),REJECT-NO-DROP"
            self.assertLess(self.rules.index(guard),
                            self.rules.index(f"DOMAIN-SUFFIX,{domain},AI"))
        self.assertFalse(any(rule.startswith("DST-PORT,") for rule in self.rules))
        self.assertNotIn("AND,((PROTOCOL,UDP),(DST-PORT,443)),REJECT-NO-DROP", self.rules)
        self.assertNotIn("DOMAIN-SUFFIX,cloudflare.com,AI", self.rules)
        self.assertNotIn("DOMAIN-SUFFIX,sentry.io,AI", self.rules)

    def test_local_references_and_public_sources_are_valid(self):
        errors = []
        groups, rules = validation.validate_structure("ai-routing", self.lines, errors)
        validation.validate_general("ai-routing", self.lines, errors)
        validation.validate_apple_watch_rules("ai-routing", self.lines, errors)
        validation.validate_sources("ai-routing", rules, errors)
        self.assertEqual(errors, [])
        for rule in self.rules:
            fields = rule.split(",")
            policy = fields[-1] if fields[0] == "AND" else fields[1 if fields[0] == "FINAL" else 2]
            self.assertIn(policy, groups | validation.BUILTIN_POLICIES | {"REJECT-NO-DROP"})
        self.assertFalse(validation.SECRET_PATTERN.search(self.text))

    def test_russian_direct_and_apple_routes_are_retained(self):
        self.assertIn("GEOIP,RU,DIRECT", self.rules)
        self.assertIn("DOMAIN-SUFFIX,ru,DIRECT", self.rules)
        self.assertIn("DOMAIN,mesu.apple.com,DIRECT", self.rules)
        self.assertIn("DOMAIN,ocsp2.apple.com,DIRECT", self.rules)
        self.assertEqual(self.rules[-1], "FINAL,PROXY")

    def test_logged_apple_and_russian_hosts_have_early_inline_direct_routes(self):
        boundary = next(i for i, rule in enumerate(self.rules) if rule.startswith("RULE-SET,"))
        for host in ("gateway.icloud.com", "metrics.icloud.com", "mesu.apple.com",
                     "ocsp2.apple.com", "appstorrent.ru", "suggest.yandex.net"):
            matches = []
            for rule in self.rules[:boundary]:
                fields = rule.split(",")
                if fields[0] == "DOMAIN" and fields[1] == host:
                    matches.append(fields[2])
                elif fields[0] == "DOMAIN-SUFFIX" and (
                    host == fields[1] or host.endswith("." + fields[1])
                ):
                    matches.append(fields[2])
            with self.subTest(host=host):
                self.assertTrue(matches)
                self.assertEqual(matches[0], "DIRECT")


if __name__ == "__main__":
    unittest.main()
