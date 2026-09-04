"""Exact rollback contract; these tests do not emulate Shadowrocket or OpenAI."""

import hashlib
import unittest
from pathlib import Path

import validate_configs as validation


ROOT = Path(__file__).resolve().parents[1]
MAIN_UPDATE = "update-url = https://raw.githubusercontent.com/squazaryu/sr-config/main/url-set-main.conf"
IOS_UPDATE = "update-url = https://raw.githubusercontent.com/squazaryu/sr-config/main/url-set-ios.conf"
FINLAND = "🇫🇮 Финляндия"
CHATGPT = f"DOMAIN-SUFFIX,chatgpt.com,{FINLAND},pre-matching,extended-matching"
# The user chose the main snapshot at 974fccc as the recovery baseline.
# Updating the baseline requires explicit review, not an automatic refetch.
PROTECTED_HASHES = {
    "url-set-main.conf": "5280e461a1109c645cce7fdffb6e1066cbacd2b2aed3ada12cc75b6542f14832",
    "url-set-macos.conf": "d19551c09ef344455566d324fd8479cce60afeb28506dfb10a9e23560a95d2b7",
    "url-set-ios-simple-test.conf": "003a3576603331824b36aaf8e29fec888b89c6c2563dbb774e62959eefa54e00",
    "url-set-ios-names-test.conf": "08875f9f7d1ec0cec5b11917c42bb9631559b0ec6554c7fe3305e0c09775b058",
}


class IOSRecoveryTests(unittest.TestCase):
    maxDiff = 800

    @classmethod
    def setUpClass(cls):
        cls.configs = {
            name: path.read_text(encoding="utf-8").splitlines()
            for name, path in validation.CONFIGS.items()
        }
        cls.source = (ROOT / "url-set-main.conf").read_bytes()
        cls.payload = (ROOT / "url-set-ios.conf").read_bytes()
        cls.expected = cls.source.replace(MAIN_UPDATE.encode(), IOS_UPDATE.encode(), 1)
        cls.lines = cls.configs["ios"]
        cls.rules = validation.meaningful(validation.section_lines(cls.lines, "[Rule]"))

    def errors_for(self, lines, source=None):
        configs = dict(self.configs)
        configs["ios"] = lines
        if source is not None:
            configs["main"] = source
        errors = []
        validation.validate_ios_service_routes(configs, errors)
        return errors

    def test_other_profiles_and_reference_snapshot_are_unchanged(self):
        for name, digest in PROTECTED_HASHES.items():
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest)

    def test_exact_copy_with_only_own_update_url(self):
        self.assertEqual(self.source.count(MAIN_UPDATE.encode()), 1)
        self.assertEqual(self.payload.count(IOS_UPDATE.encode()), 1)
        self.assertEqual(self.payload, self.expected)

    def test_no_local_groups_remote_lists_or_auto_selection(self):
        active = validation.meaningful(self.lines)
        self.assertEqual([line for line in active if line.startswith("[")], ["[General]", "[Rule]"])
        self.assertFalse(any(line.startswith(("RULE-SET,", "DOMAIN-SET,")) for line in active))
        self.assertFalse(any("= url-test," in line or "= fallback," in line for line in active))

    def test_rule_order_flags_and_existing_duplicates_are_identical(self):
        self.assertEqual(validation.section_lines(self.lines, "[Rule]"),
                         validation.section_lines(self.configs["main"], "[Rule]"))

    def test_general_dns_tun_and_transport_are_identical(self):
        def general(lines):
            return [line for line in validation.section_lines(lines, "[General]")
                    if not line.startswith("update-url =")]
        self.assertEqual(general(self.lines), general(self.configs["main"]))

    def test_every_ai_rule_is_inlined_with_original_policy_and_flags(self):
        for rule in validation.meaningful((ROOT / "lists/ai-services.list").read_text().splitlines()):
            with self.subTest(rule=rule):
                expected = f"{rule},{FINLAND},pre-matching,extended-matching"
                self.assertEqual(self.rules.count(expected), 1)

    def test_screenshot_chatgpt_rules_keep_specific_policy_before_general_duplicates(self):
        # Text order only; this is not the closed-source runtime matcher.
        matches = [line for line in self.rules if line.startswith("DOMAIN-SUFFIX,chatgpt.com,")]
        self.assertEqual(matches, [CHATGPT, "DOMAIN-SUFFIX,chatgpt.com,PROXY",
                                   "DOMAIN-SUFFIX,chatgpt.com,PROXY"])
        self.assertIn(f"DOMAIN,ios.chat.openai.com,{FINLAND},pre-matching,extended-matching", self.rules)

    def test_russian_direct_and_selected_proxy_final_are_preserved(self):
        self.assertIn("GEOIP,RU,DIRECT", self.rules)
        self.assertIn("DOMAIN-SUFFIX,ru,DIRECT", self.rules)
        self.assertIn("DOMAIN-SUFFIX,github.com,DIRECT", self.rules)
        self.assertEqual(self.rules[-1], "FINAL,PROXY")
        self.assertEqual(self.rules.count("FINAL,PROXY"), 1)

    def test_validator_accepts_exact_recovery_copy(self):
        self.assertEqual(self.errors_for(self.expected.decode().splitlines()), [])

    def test_validator_rejects_ai_policy_and_matching_changes(self):
        for replacement in (
            "DOMAIN-SUFFIX,chatgpt.com,PROXY,pre-matching,extended-matching",
            "DOMAIN-SUFFIX,chatgpt.com,DIRECT,pre-matching,extended-matching",
            "DOMAIN-SUFFIX,chatgpt.com,🇫🇮 Финляндия (авто),pre-matching,extended-matching",
            f"DOMAIN-SUFFIX,chatgpt.com,{FINLAND}",
        ):
            with self.subTest(replacement=replacement):
                changed = self.expected.decode().replace(CHATGPT, replacement, 1).splitlines()
                self.assertTrue(any("ios:" in error for error in self.errors_for(changed)))

    def test_validator_rejects_rule_reordering_dns_and_direct_changes(self):
        changes = (
            ("[Rule]", "[Rule]\nDOMAIN-SUFFIX,chatgpt.com,PROXY"),
            ("GEOIP,RU,DIRECT", "GEOIP,RU,PROXY"),
            ("FINAL,PROXY", "FINAL,DIRECT"),
            ("dns-direct-system = true", "dns-direct-system = false"),
            ("[General]", "[General]\nblock-quic = always-allow"),
        )
        for old, new in changes:
            with self.subTest(old=old):
                changed = self.expected.decode().replace(old, new, 1).splitlines()
                self.assertTrue(any("ios:" in error for error in self.errors_for(changed)))

    def test_validator_rejects_return_of_experimental_groups_lists_and_exceptions(self):
        for extra in (
            "[Proxy Group]\nAI = select,PROXY",
            "DOMAIN,sub.alvsub.cc,PROXY",
            "RULE-SET,https://example.com/ai.list,PROXY",
        ):
            with self.subTest(extra=extra):
                changed = self.expected.decode().replace("[Rule]", extra + "\n[Rule]", 1).splitlines()
                self.assertTrue(any("ios:" in error for error in self.errors_for(changed)))

    def test_validator_rejects_missing_duplicate_or_wrong_update_url(self):
        for replacement in ("", MAIN_UPDATE, IOS_UPDATE + "\n" + IOS_UPDATE):
            with self.subTest(replacement=replacement):
                changed = self.expected.decode().replace(IOS_UPDATE, replacement, 1).splitlines()
                self.assertTrue(any("ios:" in error for error in self.errors_for(changed)))

    def test_validator_rejects_invalid_reference_update_url(self):
        for source in (
            [line for line in self.configs["main"] if line != MAIN_UPDATE],
            self.configs["main"] + [MAIN_UPDATE],
        ):
            self.assertTrue(self.errors_for(self.expected.decode().splitlines(), source=source))

    def test_main_service_guards_remain_active(self):
        for rule in (
            "DOMAIN-SUFFIX,github.com,DIRECT",
            "DOMAIN-SUFFIX,rejail.ru,DIRECT",
            f"DOMAIN-SUFFIX,getutm.app,{FINLAND}",
            f"DOMAIN-SUFFIX,platipomiru.com,{FINLAND}",
            f"DOMAIN-SUFFIX,youtube.com,{FINLAND}",
            f"DOMAIN-SUFFIX,instagram.com,{FINLAND}",
        ):
            with self.subTest(rule=rule):
                # Remove it from both copies: equality must not disable existing guards.
                source = [line for line in self.configs["main"] if line != rule]
                actual = [IOS_UPDATE if line == MAIN_UPDATE else line for line in source]
                self.assertTrue(any("main:" in error for error in self.errors_for(actual, source)))


if __name__ == "__main__":
    unittest.main()
