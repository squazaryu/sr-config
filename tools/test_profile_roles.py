"""Guard the promoted September 8 iOS profile and archived experiments."""
import hashlib
from pathlib import Path
import unittest
import validate_configs as validation

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "archive/2026-09-08"
AI = "AI = url-test,FINLAND 🇫🇮,🇫🇮 ФИНЛЯНДИЯ,FINLAND 42 🇫🇮 → [📃 БЕЛЫЕ СПИСКИ]-2,FINLAND 52 🇫🇮 → [📃 БЕЛЫЕ СПИСКИ]-2,interval=600,tolerance=100,timeout=5,url=http://www.gstatic.com/generate_204"
FINLAND = "FINLAND = url-test,FINLAND 🇫🇮,🇫🇮 ФИНЛЯНДИЯ,FINLAND 42 🇫🇮 → [📃 БЕЛЫЕ СПИСКИ]-2,FINLAND 52 🇫🇮 → [📃 БЕЛЫЕ СПИСКИ]-2,🇫🇮 ФИНЛЯНДИЯ | РЕКЛАМА НА ЮТУБЕ,policy-select-name=FINLAND 🇫🇮,interval=300,tolerance=100,timeout=5,url=http://www.gstatic.com/generate_204"
INSTAGRAM = "INSTAGRAM = select,SERVERS,PROXY,AUTO,FINLAND,DIRECT,policy-select-name=AUTO"
ADDED_AI_RULES = (
    "DOMAIN-SUFFIX,featuregates.org,AI",
    "DOMAIN-SUFFIX,segment.io,AI",
    "DOMAIN-SUFFIX,statsig.com,AI",
    "DOMAIN-SUFFIX,statsigapi.net,AI",
    "DOMAIN-SUFFIX,featureassets.org,AI",
    "DOMAIN-SUFFIX,prodregistryv2.org,AI",
)
LIVEKIT_AI_RULES = (
    "DOMAIN,turn.livekit.cloud,AI",
    "DOMAIN,host.livekit.cloud,AI",
)
META_RULE_PREFIXES = (
    "DOMAIN-SUFFIX,instagram.com",
    "DOMAIN-SUFFIX,instagr.am",
    "DOMAIN-SUFFIX,cdninstagram.com",
    "DOMAIN-SUFFIX,ig.me",
    "DOMAIN-SUFFIX,igcdn.com",
    "DOMAIN-SUFFIX,igsonar.com",
    "DOMAIN-SUFFIX,igtv.com",
    "DOMAIN-SUFFIX,facebook.com",
    "DOMAIN-SUFFIX,facebook.net",
    "DOMAIN-SUFFIX,fb.com",
    "DOMAIN-SUFFIX,fb.me",
    "DOMAIN-SUFFIX,fbcdn.com",
    "DOMAIN-SUFFIX,fbcdn.net",
    "DOMAIN-SUFFIX,fbsbx.com",
    "DOMAIN-SUFFIX,fbsbx.net",
    "DOMAIN-SUFFIX,meta.com",
    "DOMAIN-SUFFIX,messenger.com",
    "DOMAIN-SUFFIX,m.me",
    "DOMAIN-SUFFIX,threads.net",
    "DOMAIN-SUFFIX,fbcdn-a.akamaihd.net",
    "DOMAIN-KEYWORD,instagram",
    "IP-ASN,32934",
    "IP-ASN,63293",
    "IP-CIDR,31.13.64.0/18",
    "IP-CIDR,129.134.0.0/17",
    "IP-CIDR,157.240.0.0/17",
    "IP-CIDR,173.252.64.0/18",
    "IP-CIDR6,2A03:2880::/32",
)
FEATHER_DOMAINS = (
    "getutm.app",
    "fastsign.dev",
    "apptesters.org",
    "hottubapp.io",
    "stikdebug.xyz",
)
FEATHER_RULES = tuple(
    f"DOMAIN-SUFFIX,{domain},PROXY" for domain in FEATHER_DOMAINS
)
LEGACY_FEATHER_RULES = tuple(
    f"DOMAIN-SUFFIX,{domain},DIRECT" for domain in FEATHER_DOMAINS
)
MAIL_RULES = (
    "DOMAIN-SUFFIX,mail.me.com,DIRECT",
    "DOMAIN-SUFFIX,mail.ru,DIRECT",
    "DOMAIN-SUFFIX,yandex.com,DIRECT",
    "DOMAIN-SUFFIX,gmail.com,PROXY",
    "DOMAIN-SUFFIX,googlemail.com,PROXY",
    "DOMAIN,accounts.google.com,PROXY",
)
MAIL_BLOCK = (
    "",
    "# Почта: явные маршруты для IMAP и SMTP. Доменные правила покрывают",
    "# стандартные порты 993, 465 и 587 без широких DST-PORT-переопределений.",
    *MAIL_RULES,
)


class ProfileRoleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.configs = {name: path.read_text(encoding="utf-8").splitlines()
                       for name, path in validation.CONFIGS.items()}
        cls.text = (ROOT / "url-set-ios.conf").read_text(encoding="utf-8")
        cls.reference = (ARCHIVE / "url-set-ios-ai-flat-test.conf").read_text(encoding="utf-8")
        cls.rules = validation.meaningful(validation.section_lines(cls.text.splitlines(), "[Rule]"))

    def errors_for(self, text, main=None):
        configs = dict(self.configs, ios=text.splitlines())
        if main is not None:
            configs["main"] = main
        errors = []
        validation.validate_ios_service_routes(configs, errors)
        return errors

    def test_user_profile_preserves_only_approved_changes(self):
        expected = []
        for line in self.reference.splitlines():
            if line.startswith("# Shadowrocket:"):
                line = "# Shadowrocket: 2026-09-08 19:25:40"
            elif line.startswith("update-url ="):
                continue
            elif line.startswith("AI ="):
                line = AI
            elif line.startswith("FINLAND ="):
                line = FINLAND
            elif line.startswith("YOUTUBE ="):
                expected.extend((line, INSTAGRAM))
                continue
            elif line == "DOMAIN-SUFFIX,platipomiru.com,PROXY":
                line = "DOMAIN-SUFFIX,platipomiru.com,TELEGRAM"
            elif line in LEGACY_FEATHER_RULES:
                line = line.rsplit(",", 1)[0] + ",PROXY"
            elif any(line.startswith(prefix + ",") for prefix in META_RULE_PREFIXES):
                fields = line.split(",")
                fields[2] = "INSTAGRAM"
                line = ",".join(fields)
            expected.append(line)
            if line == "DOMAIN-SUFFIX,aviasales.com,DIRECT":
                expected.extend(MAIL_BLOCK)
            if line == "DOMAIN-SUFFIX,ct.sendgrid.net,AI":
                expected.extend(ADDED_AI_RULES)
            if line == "DOMAIN,workos.imgix.net,AI":
                expected.extend(LIVEKIT_AI_RULES)
        self.assertEqual(self.text, "\n".join(expected) + "\n")

    def test_all_rules_keep_order_and_options(self):
        original = validation.meaningful(validation.section_lines(self.reference.splitlines(), "[Rule]"))
        updated = []
        for rule in original:
            if rule == "DOMAIN-SUFFIX,platipomiru.com,PROXY":
                rule = "DOMAIN-SUFFIX,platipomiru.com,TELEGRAM"
            elif rule in LEGACY_FEATHER_RULES:
                rule = rule.rsplit(",", 1)[0] + ",PROXY"
            elif any(rule.startswith(prefix + ",") for prefix in META_RULE_PREFIXES):
                fields = rule.split(",")
                fields[2] = "INSTAGRAM"
                rule = ",".join(fields)
            updated.append(rule)
            if rule == "DOMAIN-SUFFIX,aviasales.com,DIRECT":
                updated.extend(MAIL_RULES)
            if rule == "DOMAIN-SUFFIX,ct.sendgrid.net,AI":
                updated.extend(ADDED_AI_RULES)
            if rule == "DOMAIN,workos.imgix.net,AI":
                updated.extend(LIVEKIT_AI_RULES)
        original = updated
        self.assertEqual(self.rules, original)
        self.assertEqual(sum(rule.startswith("RULE-SET,") for rule in self.rules), 18)

    def test_fallback_and_macos_are_unchanged(self):
        hashes = {
            "url-set-main.conf": "541a7e558d60dca72ec128eedb2739f05d38e85bc8fe2bb0ddebc0b373e15da8",
            "url-set-macos.conf": "d19551c09ef344455566d324fd8479cce60afeb28506dfb10a9e23560a95d2b7",
        }
        for name, digest in hashes.items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest)

    def test_only_active_profiles_remain_at_root(self):
        self.assertEqual({p.name for p in ROOT.glob("*.conf")},
                         {"url-set-ios.conf", "url-set-macos.conf", "url-set-main.conf"})
        self.assertEqual(len(list(ARCHIVE.glob("*.conf"))), 5)

    def test_group_defaults_and_dependencies(self):
        groups = {}
        for line in validation.meaningful(validation.section_lines(self.text.splitlines(), "[Proxy Group]")):
            name, value = line.split("=", 1)
            fields = [part.strip() for part in value.split(",")]
            members = [part for part in fields[1:] if "=" not in part]
            for setting in fields[1:]:
                if setting.startswith("policy-select-name="):
                    self.assertIn(setting.split("=", 1)[1], members)
            groups[name.strip()] = members
        self.assertEqual(len(groups), 11)
        self.assertNotIn("FINLAND", groups["AI"])
        self.assertEqual(len(groups["AI"]), 4)
        self.assertEqual(len(groups["FINLAND"]), 5)
        self.assertEqual(groups["INSTAGRAM"], ["SERVERS", "PROXY", "AUTO", "FINLAND", "DIRECT"])
        for rule in FEATHER_RULES:
            self.assertIn(rule, self.rules)
        def walk(name, stack):
            self.assertNotIn(name, stack, "group cycle")
            for member in groups[name]:
                if member in groups:
                    walk(member, stack + [name])
        for name in groups:
            walk(name, [])

    def test_validator_accepts_current_profile(self):
        self.assertEqual(self.errors_for(self.text), [])

    def test_validator_rejects_changed_ai_and_finland_pools(self):
        for old, new in ((AI, "AI = select,PROXY"),
                         (FINLAND, "FINLAND = select,🇫🇮 ALL VPN | ФИНЛЯНДИЯ"),
                         ("AI = url-test,", "AI = url-test,SHD,")):
            self.assertTrue(self.errors_for(self.text.replace(old, new, 1)))

    def test_validator_rejects_late_or_missing_early_service_rules(self):
        for rule in ("DOMAIN-SUFFIX,chatgpt.com,AI", "DOMAIN,challenges.cloudflare.com,AI",
                     "DOMAIN-SUFFIX,icloud.com,DIRECT", "DOMAIN-SUFFIX,ru,DIRECT",
                     "DOMAIN-SUFFIX,platipomiru.com,TELEGRAM",
                     *FEATHER_RULES):
            changed = self.text.replace(rule + "\n", "", 1)
            self.assertTrue(self.errors_for(changed))
            self.assertTrue(self.errors_for(changed.replace("FINAL,PROXY", rule + "\nFINAL,PROXY")))

    def test_validator_rejects_removed_quic_guards(self):
        rule = "AND,((PROTOCOL,UDP),(DST-PORT,443),(DOMAIN-SUFFIX,openai.com)),REJECT-NO-DROP"
        self.assertTrue(self.errors_for(self.text.replace(rule + "\n", "", 1)))

    def test_validator_rejects_blanket_port_override(self):
        changed = self.text.replace("[Rule]", "[Rule]\nDST-PORT,443,FINLAND", 1)
        self.assertTrue(self.errors_for(changed))

    def test_validator_rejects_unrequested_update_url(self):
        changed = self.text.replace("[General]", "[General]\nupdate-url = https://example.com/test.conf", 1)
        self.assertTrue(self.errors_for(changed))

    def test_russian_direct_and_proxy_final_are_required(self):
        for old, new in (("GEOIP,RU,DIRECT", "GEOIP,RU,PROXY"), ("FINAL,PROXY", "FINAL,DIRECT")):
            self.assertTrue(self.errors_for(self.text.replace(old, new, 1)))

    def test_fallback_stays_independent_and_guarded(self):
        fallback = self.configs["main"]
        self.assertFalse(any(line.startswith("RULE-SET,") for line in fallback))
        for rule in ("DOMAIN-SUFFIX,github.com,DIRECT", "DOMAIN-SUFFIX,instagram.com,🇫🇮 Финляндия"):
            self.assertTrue(self.errors_for(self.text, main=[line for line in fallback if line != rule]))


if __name__ == "__main__":
    unittest.main()
