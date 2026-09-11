"""Protect the primary iOS role and the independent fallback profile."""

import hashlib
from pathlib import Path
import unittest

import validate_configs as validation


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "archive/2026-09-08"
IOS_UPDATE = "update-url = https://raw.githubusercontent.com/squazaryu/sr-config/main/url-set-ios.conf"
AI = "AI = select,FINLAND,policy-select-name=FINLAND"
FINLAND = (
    "FINLAND = url-test,FINLAND 🇫🇮,🇫🇮 ФИНЛЯНДИЯ,"
    "FINLAND 42 🇫🇮 → [📃 БЕЛЫЕ СПИСКИ]-2,"
    "FINLAND 52 🇫🇮 → [📃 БЕЛЫЕ СПИСКИ]-2,"
    "🇫🇮 ФИНЛЯНДИЯ | РЕКЛАМА НА ЮТУБЕ,"
    "policy-select-name=FINLAND 🇫🇮,interval=300,tolerance=100,"
    "timeout=5,url=http://www.gstatic.com/generate_204"
)
INSTAGRAM = "INSTAGRAM = select,SERVERS,PROXY,AUTO,FINLAND,DIRECT,policy-select-name=AUTO"
FEATHER_RULES = tuple(
    f"DOMAIN-SUFFIX,{domain},PROXY"
    for domain in ("getutm.app", "fastsign.dev", "apptesters.org", "hottubapp.io", "stikdebug.xyz")
)


def section(lines, name):
    return validation.meaningful(validation.section_lines(lines, name))


def group_map(lines):
    return {
        name.strip(): value.strip()
        for line in section(lines, "[Proxy Group]")
        for name, value in [line.split("=", 1)]
    }


class ProfileRoleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.configs = {
            name: path.read_text(encoding="utf-8").splitlines()
            for name, path in validation.CONFIGS.items()
        }
        cls.text = (ROOT / "url-set-ios.conf").read_text(encoding="utf-8")
        cls.lines = cls.text.splitlines()
        cls.rules = section(cls.lines, "[Rule]")
        cls.groups = group_map(cls.lines)

    def errors_for(self, text, main=None):
        configs = dict(self.configs, ios=text.splitlines())
        if main is not None:
            configs["main"] = main
        errors = []
        validation.validate_ios_service_routes(configs, errors)
        return errors

    def test_fallback_and_macos_are_unchanged(self):
        hashes = {
            "url-set-main.conf": "541a7e558d60dca72ec128eedb2739f05d38e85bc8fe2bb0ddebc0b373e15da8",
            "url-set-macos.conf": "d19551c09ef344455566d324fd8479cce60afeb28506dfb10a9e23560a95d2b7",
        }
        for name, digest in hashes.items():
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest)

    def test_only_active_profiles_remain_at_root(self):
        self.assertEqual(
            {path.name for path in ROOT.glob("*.conf")},
            {"url-set-ios.conf", "url-set-macos.conf", "url-set-main.conf"},
        )
        self.assertEqual(len(list(ARCHIVE.glob("*.conf"))), 5)

    def test_group_defaults_and_dependencies_are_explicit_and_acyclic(self):
        self.assertEqual(
            set(self.groups),
            {"AI", "SPOTIFY", "WEATHER", "TELEGRAM", "DEFAULT", "YOUTUBE", "INSTAGRAM", "ADS", "FINLAND", "SERVERS", "AUTO"},
        )
        self.assertEqual(self.groups["AI"], "select,FINLAND,policy-select-name=FINLAND")
        self.assertEqual(self.groups["FINLAND"], FINLAND.split("=", 1)[1].strip())
        self.assertEqual(self.groups["INSTAGRAM"], INSTAGRAM.split("=", 1)[1].strip())

        graph = {}
        for name, value in self.groups.items():
            fields = [part.strip() for part in value.split(",")]
            members = [part for part in fields[1:] if "=" not in part]
            graph[name] = members
            for field in fields[1:]:
                if field.startswith("policy-select-name="):
                    self.assertIn(field.split("=", 1)[1], members)

        def walk(name, stack):
            self.assertNotIn(name, stack, "group cycle")
            for member in graph[name]:
                if member in graph:
                    walk(member, stack + [name])

        for name in graph:
            walk(name, [])

    def test_primary_contains_required_service_routes(self):
        for rule in (
            "DOMAIN,apple-relay.fastly-edge.com,DIRECT",
            "DOMAIN-SUFFIX,apple.com,DIRECT",
            "DOMAIN-SUFFIX,icloud.com,DIRECT",
            "DOMAIN-SUFFIX,icloud-content.com,DIRECT",
            "DOMAIN-SUFFIX,ru,DIRECT",
            "DOMAIN-SUFFIX,su,DIRECT",
            "DOMAIN-SUFFIX,рф,DIRECT",
            "DOMAIN-SUFFIX,mail.ru,DIRECT",
            "DOMAIN-SUFFIX,yandex.com,DIRECT",
            "DOMAIN-SUFFIX,gmail.com,PROXY",
            "DOMAIN-SUFFIX,googlemail.com,PROXY",
            "DOMAIN,accounts.google.com,PROXY",
            "DOMAIN-SUFFIX,chatgpt.com,AI",
            "DOMAIN-SUFFIX,openai.com,AI",
            "DOMAIN-SUFFIX,oaistatic.com,AI",
            "DOMAIN-SUFFIX,oaiusercontent.com,AI",
            "DOMAIN,challenges.cloudflare.com,AI",
            "DOMAIN-SUFFIX,platipomiru.com,TELEGRAM",
            *FEATHER_RULES,
            "DOMAIN-SUFFIX,instagram.com,INSTAGRAM",
            "IP-ASN,32934,INSTAGRAM,no-resolve",
            "FINAL,PROXY",
        ):
            with self.subTest(rule=rule):
                self.assertIn(rule, self.rules)

    def test_validator_accepts_current_profile(self):
        self.assertEqual(self.errors_for(self.text), [])

    def test_validator_rejects_the_old_nested_ai_probe(self):
        changed = self.text.replace(AI, "AI = url-test,FINLAND,interval=600,tolerance=100,timeout=5,url=http://www.gstatic.com/generate_204", 1)
        self.assertTrue(self.errors_for(changed))

    def test_validator_rejects_experimental_transport_geoip_and_broad_lists(self):
        variants = (
            self.text.replace("[Rule]", "[Rule]\nAND,((PROTOCOL,UDP),(DST-PORT,443)),REJECT-NO-DROP", 1),
            self.text.replace("[Rule]", "[Rule]\nGEOIP,RU,DIRECT", 1),
            self.text.replace(
                "RULE-SET,https://raw.githubusercontent.com/squazaryu/sr-config/main/lists/general-proxy.list,DEFAULT",
                "RULE-SET,https://raw.githubusercontent.com/helmiau/clashrules/refs/heads/main/shadowrocket/Game_Discord_Ports.list,DEFAULT",
                1,
            ),
        )
        for changed in variants:
            with self.subTest(changed=changed[:80]):
                self.assertTrue(self.errors_for(changed))

    def test_validator_rejects_missing_early_route_or_wrong_final(self):
        for rule in ("DOMAIN-SUFFIX,chatgpt.com,AI", "DOMAIN-SUFFIX,icloud.com,DIRECT", *FEATHER_RULES):
            without = self.text.replace(rule + "\n", "", 1)
            with self.subTest(rule=rule):
                self.assertTrue(self.errors_for(without))
        self.assertTrue(self.errors_for(self.text.replace("FINAL,PROXY", "FINAL,DIRECT", 1)))

    def test_validator_requires_the_primary_update_url(self):
        self.assertTrue(self.errors_for(self.text.replace(IOS_UPDATE, "update-url = https://example.com/test.conf", 1)))
        self.assertTrue(self.errors_for(self.text.replace(IOS_UPDATE + "\n", "", 1)))

    def test_fallback_stays_independent(self):
        fallback = self.configs["main"]
        self.assertFalse(any(line.startswith("RULE-SET,") for line in fallback))
        self.assertIn("DOMAIN-SUFFIX,github.com,DIRECT", fallback)
        self.assertEqual(self.rules[-1], "FINAL,PROXY")


if __name__ == "__main__":
    unittest.main()
