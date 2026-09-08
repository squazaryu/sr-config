"""Protect the separately published iOS profile supplied by the user."""

from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

import check_remote_sources
import validate_configs as validation


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "url-set-ios-working.conf"
EXPECTED_SHA256 = "4f84a91a696d59ede05a0922b3c9d2e482e5a7c7d68aec57cf77e2225ca5f209"
EXPECTED_GROUPS = [
    "AI",
    "SPOTIFY",
    "WEATHER",
    "TELEGRAM",
    "DEFAULT",
    "YOUTUBE",
    "ADS",
    "FINLAND",
    "SERVERS",
    "AUTO",
]
BUILTIN_RULE_POLICIES = validation.BUILTIN_POLICIES | {"REJECT-NO-DROP"}


def meaningful_section(lines: list[str], name: str) -> list[str]:
    return validation.meaningful(validation.section_lines(lines, name))


class IOSWorkingProfileTests(unittest.TestCase):
    maxDiff = 1000

    def read_payload(self) -> bytes:
        self.assertTrue(PROFILE.is_file(), f"missing profile: {PROFILE.name}")
        return PROFILE.read_bytes()

    def read_lines(self) -> list[str]:
        return self.read_payload().decode("utf-8").splitlines()

    def read_groups(self) -> dict[str, str]:
        return {
            name.strip(): value.strip()
            for line in meaningful_section(self.read_lines(), "[Proxy Group]")
            for name, value in [line.split("=", 1)]
        }

    def test_profile_is_the_exact_user_supplied_snapshot(self):
        payload = self.read_payload()
        self.assertEqual(hashlib.sha256(payload).hexdigest(), EXPECTED_SHA256)

    def test_profile_is_standalone_and_has_only_expected_sections(self):
        lines = self.read_lines()
        self.assertEqual(
            [line.strip() for line in lines if line.strip().startswith("[")],
            ["[General]", "[Proxy Group]", "[Rule]"],
        )
        self.assertFalse(any(line.strip().startswith("update-url =") for line in lines))

    def test_group_names_order_and_core_routes_are_preserved(self):
        groups = self.read_groups()
        self.assertEqual(list(groups), EXPECTED_GROUPS)
        self.assertEqual(groups["AI"], "select,FINLAND,policy-select-name=FINLAND")
        self.assertEqual(
            groups["FINLAND"],
            "url-test,FINLAND 52 🇫🇮 → [📃 БЕЛЫЕ СПИСКИ],FINLAND 🇫🇮,"
            "FINLAND 42 🇫🇮 → [📃 БЕЛЫЕ СПИСКИ],🇫🇮 ФИНЛЯНДИЯ,"
            "policy-select-name=🇫🇮 ФИНЛЯНДИЯ,interval=300,tolerance=100,"
            "timeout=5,url=http://www.gstatic.com/generate_204",
        )
        self.assertEqual(
            groups["SERVERS"],
            "url-test,DUREV,BASE | ALL IN 1,PREMIUM | ALL IN 1,"
            "policy-select-name=DUREV,interval=600,tolerance=100,timeout=5,"
            "url=http://www.gstatic.com/generate_204",
        )
        self.assertEqual(
            groups["AUTO"],
            "url-test,BASE | ALL IN 1,DUREV,PREMIUM | ALL IN 1,"
            "policy-select-name=PREMIUM | ALL IN 1,interval=300,tolerance=50,"
            "timeout=5,url=http://www.gstatic.com/generate_204",
        )

    def test_every_group_default_is_an_explicit_member(self):
        for name, value in self.read_groups().items():
            fields = [field.strip() for field in value.split(",")]
            members = [field for field in fields[1:] if "=" not in field]
            defaults = [field.split("=", 1)[1] for field in fields if field.startswith("policy-select-name=")]
            with self.subTest(group=name):
                self.assertLessEqual(len(defaults), 1)
                if defaults:
                    self.assertIn(defaults[0], members)

    def test_group_dependencies_resolve_to_declared_groups(self):
        groups = self.read_groups()
        expected_dependencies = {
            "AI": {"FINLAND"},
            "WEATHER": {"AUTO"},
            "TELEGRAM": {"AUTO", "SERVERS", "FINLAND"},
            "YOUTUBE": {"SERVERS", "AUTO", "FINLAND"},
        }
        for name, dependencies in expected_dependencies.items():
            members = {field.strip() for field in groups[name].split(",")[1:] if "=" not in field}
            with self.subTest(group=name):
                self.assertTrue(dependencies <= members)
                self.assertTrue(dependencies <= groups.keys())

    def test_rules_keep_count_order_and_declared_policies(self):
        rules = meaningful_section(self.read_lines(), "[Rule]")
        self.assertEqual(len(rules), 135)
        self.assertEqual(len(set(rules)), len(rules))
        self.assertEqual(sum(line.startswith("RULE-SET,") for line in rules), 18)
        self.assertEqual(rules[-1], "FINAL,PROXY")
        self.assertEqual(rules.count("FINAL,PROXY"), 1)

        groups = set(self.read_groups())
        for line in rules:
            fields = [field.strip() for field in line.split(",")]
            if fields[0] == "FINAL":
                policy = fields[1]
            elif fields[0] == "AND":
                policy = fields[-1]
            else:
                policy = fields[2]
            with self.subTest(rule=line):
                self.assertIn(policy, groups | BUILTIN_RULE_POLICIES)

    def test_critical_service_routes_are_preserved(self):
        rules = meaningful_section(self.read_lines(), "[Rule]")
        for rule in (
            "DOMAIN-SUFFIX,getutm.app,DIRECT",
            "DOMAIN-SUFFIX,fastsign.dev,DIRECT",
            "DOMAIN-SUFFIX,apptesters.org,DIRECT",
            "DOMAIN-SUFFIX,hottubapp.io,DIRECT",
            "DOMAIN-SUFFIX,stikdebug.xyz,DIRECT",
            "DOMAIN-SUFFIX,platipomiru.com,PROXY",
            "RULE-SET,https://raw.githubusercontent.com/squazaryu/sr-config/main/lists/ai-services.list,AI,pre-matching,extended-matching",
            "RULE-SET,https://raw.githubusercontent.com/squazaryu/sr-config/main/lists/general-proxy.list,DEFAULT",
            "GEOIP,RU,DIRECT",
        ):
            with self.subTest(rule=rule):
                self.assertIn(rule, rules)

    def test_shared_structural_source_and_secret_checks_accept_profile(self):
        lines = self.read_lines()
        errors: list[str] = []
        _groups, rules = validation.validate_structure("ios-working", lines, errors)
        validation.validate_general("ios-working", lines, errors)
        validation.validate_apple_watch_rules("ios-working", lines, errors)
        validation.validate_sources("ios-working", rules, errors)
        for line_number, line in enumerate(lines, start=1):
            if validation.SECRET_PATTERN.search(line):
                errors.append(f"ios-working: possible secret on line {line_number}")
        self.assertEqual(errors, [])

    def test_remote_source_checker_includes_the_published_profile(self):
        self.assertIn(PROFILE, check_remote_sources.CONFIG_PATHS)
        sources, errors = check_remote_sources.collect_sources()
        self.assertEqual(errors, [])
        references = [reference for source in sources.values() for reference in source.references]
        self.assertEqual(
            sum(reference.startswith(f"{PROFILE.name}:") for reference in references),
            18,
        )


if __name__ == "__main__":
    unittest.main()
