"""Promote N01 without route changes; preserve the fully expanded fallback."""

import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch

import validate_configs as validation


ROOT = Path(__file__).resolve().parents[1]
MAIN_UPDATE = "update-url = https://raw.githubusercontent.com/squazaryu/sr-config/main/url-set-main.conf"
IOS_UPDATE = "update-url = https://raw.githubusercontent.com/squazaryu/sr-config/main/url-set-ios.conf"
N01_UPDATE = "update-url = https://raw.githubusercontent.com/squazaryu/sr-config/main/url-set-ios-names-test.conf"
IOS_HEADER = (
    "# iOS — основной конфиг с группами на базе N01.\n"
    "# Настройки N01 сохранены; у основного профиля своя ссылка обновления.\n"
    "# Самодостаточный резервный конфиг: url-set-main.conf.\n\n"
)
PROTECTED_HASHES = {
    "url-set-main.conf": "5280e461a1109c645cce7fdffb6e1066cbacd2b2aed3ada12cc75b6542f14832",
    "url-set-macos.conf": "d19551c09ef344455566d324fd8479cce60afeb28506dfb10a9e23560a95d2b7",
    "url-set-ios-simple-test.conf": "003a3576603331824b36aaf8e29fec888b89c6c2563dbb774e62959eefa54e00",
    "url-set-ios-names-test.conf": "08875f9f7d1ec0cec5b11917c42bb9631559b0ec6554c7fe3305e0c09775b058",
}


def section(lines, name):
    return validation.meaningful(validation.section_lines(lines, name))


class ProfileRoleTests(unittest.TestCase):
    maxDiff = 800

    @classmethod
    def setUpClass(cls):
        cls.configs = {name:path.read_text(encoding="utf-8").splitlines()
                       for name,path in validation.CONFIGS.items()}
        cls.source = (ROOT / "url-set-ios-names-test.conf").read_text(encoding="utf-8")
        cls.reference = cls.source.splitlines()
        cls.expected = IOS_HEADER + cls.source[cls.source.index("[General]"):].replace(N01_UPDATE, IOS_UPDATE, 1)
        cls.payload = (ROOT / "url-set-ios.conf").read_bytes()
        cls.lines = cls.configs["ios"]
        cls.rules = section(cls.lines, "[Rule]")
        cls.groups = {name.strip():value.strip() for line in section(cls.lines,"[Proxy Group]")
                      for name,value in [line.split("=",1)]}

    def errors_for(self, lines, reference=None, main=None):
        configs = dict(self.configs)
        configs["ios"] = lines
        if main is not None:
            configs["main"] = main
        errors = []
        if reference is None:
            validation.validate_ios_service_routes(configs, errors)
        else:
            with patch.object(validation, "read_config", return_value=reference):
                validation.validate_ios_service_routes(configs, errors)
        return errors

    def test_fallback_macos_and_test_profiles_are_unchanged(self):
        for name,digest in PROTECTED_HASHES.items():
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),digest)

    def test_fallback_preserves_the_previous_fully_expanded_ios(self):
        payload=(ROOT/"url-set-main.conf").read_bytes().replace(MAIN_UPDATE.encode(),IOS_UPDATE.encode(),1)
        self.assertEqual(hashlib.sha256(payload).hexdigest(),
                         "99432ef66ea01c5af1a7dc3c2bec244603601c40ca8869a8ccc61d0d96704be0")
        active=validation.meaningful(self.configs["main"])
        self.assertEqual([line for line in active if line.startswith("[")],["[General]","[Rule]"])
        self.assertFalse(any(line.startswith("RULE-SET,") for line in active))
        self.assertIn("DOMAIN-SUFFIX,openai.com,🇫🇮 Финляндия,pre-matching,extended-matching",active)

    def test_ios_is_exact_n01_copy_except_header_and_update_url(self):
        self.assertEqual(self.source.count(N01_UPDATE),1)
        self.assertEqual(self.payload,self.expected.encode())

    def test_all_active_settings_match_n01(self):
        expected=[IOS_UPDATE if line==N01_UPDATE else line for line in validation.meaningful(self.reference)]
        self.assertEqual(validation.meaningful(self.lines),expected)

    def test_group_names_and_finland_auto_path_are_preserved(self):
        self.assertEqual(list(self.groups),["AI","SPOTIFY","WEATHER","TELEGRAM","DEFAULT","YOUTUBE","ADS","FINLAND","SERVERS","AUTO"])
        self.assertEqual(self.groups.get("AI"),"select,FINLAND,policy-select-name=FINLAND")
        original=next(line.split("=",1)[1].strip() for line in section(self.reference,"[Proxy Group]")
                      if line.startswith("FINLAND ="))
        self.assertEqual(self.groups.get("FINLAND"),original)

    def test_all_rules_and_remote_sources_keep_order_and_options(self):
        self.assertEqual(self.rules,section(self.reference,"[Rule]"))
        self.assertEqual(len(self.rules),135)
        self.assertEqual(sum(line.startswith("RULE-SET,") for line in self.rules),18)

    def test_general_dns_and_transport_are_preserved(self):
        strip_url=lambda lines:[line for line in section(lines,"[General]") if not line.startswith("update-url =")]
        self.assertEqual(strip_url(self.lines),strip_url(self.reference))

    def test_each_profile_has_its_own_update_url(self):
        for name in ("url-set-main.conf","url-set-ios.conf","url-set-ios-names-test.conf"):
            lines=(ROOT/name).read_text().splitlines()
            self.assertEqual([line for line in section(lines,"[General]") if line.startswith("update-url =")],
                             [f"update-url = https://raw.githubusercontent.com/squazaryu/sr-config/main/{name}"])

    def test_russian_direct_and_proxy_final_are_preserved(self):
        self.assertIn("GEOIP,RU,DIRECT",self.rules)
        self.assertIn("DOMAIN-SUFFIX,ru,DIRECT",self.rules)
        self.assertEqual(self.rules[-1],"FINAL,PROXY")
        self.assertEqual(self.rules.count("FINAL,PROXY"),1)

    def test_validator_accepts_promoted_n01(self):
        self.assertEqual(self.errors_for(self.expected.splitlines()),[])

    def test_validator_rejects_flat_profile_in_ios_slot(self):
        flat=[IOS_UPDATE if line==MAIN_UPDATE else line for line in self.configs["main"]]
        self.assertTrue(any("ios:" in error for error in self.errors_for(flat)))

    def test_validator_rejects_group_routes_candidates_and_probe_changes(self):
        changes=(
            ("AI = select,FINLAND,policy-select-name=FINLAND","AI = select,PROXY,policy-select-name=PROXY"),
            ("AI = select,","AI = fallback,"),
            (",FINLAND,policy-select-name=FINLAND",",DIRECT,policy-select-name=DIRECT"),
            (",🇫🇮 FASTCON VPN | ФИНЛЯНДИЯ,",","),
            ("interval=300,tolerance=50","interval=60,tolerance=100"),
            ("http://www.gstatic.com/generate_204","https://ios.chat.openai.com/cdn-cgi/trace"),
        )
        for old,new in changes:
            with self.subTest(old=old):
                self.assertIn(old,self.expected)
                changed=self.expected.replace(old,new,1).splitlines()
                self.assertTrue(any("ios:" in e for e in self.errors_for(changed)))

    def test_validator_rejects_other_routing_dns_and_transport_changes(self):
        changes=(("GEOIP,RU,DIRECT","GEOIP,RU,PROXY"),("FINAL,PROXY","FINAL,DIRECT"),
                 ("dns-direct-system = true","dns-direct-system = false"),
                 ("block-quic = always-allow","block-quic = all"),
                 ("[Rule]","[Rule]\nDOMAIN-SUFFIX,openai.com,PROXY"))
        for old,new in changes:
            with self.subTest(old=old):
                changed=self.expected.replace(old,new,1).splitlines()
                self.assertTrue(any("ios:" in e for e in self.errors_for(changed)))

    def test_validator_rejects_missing_duplicate_or_wrong_ios_update_url(self):
        for replacement in ("",N01_UPDATE,MAIN_UPDATE,IOS_UPDATE+"\n"+IOS_UPDATE):
            changed=self.expected.replace(IOS_UPDATE,replacement,1).splitlines()
            self.assertTrue(any("ios:" in e for e in self.errors_for(changed)))

    def test_validator_requires_valid_n01_reference(self):
        for reference in ([],[line for line in self.reference if line!=N01_UPDATE],self.reference+[N01_UPDATE]):
            self.assertTrue(any("ios-reference:" in e for e in
                                self.errors_for(self.expected.splitlines(),reference=reference)))

    def test_validator_checks_fallback_update_url_independently(self):
        for main in ([line for line in self.configs["main"] if line!=MAIN_UPDATE],self.configs["main"]+[MAIN_UPDATE]):
            self.assertTrue(any("main:" in e for e in self.errors_for(self.expected.splitlines(),main=main)))

    def test_existing_fallback_service_guards_remain_active(self):
        for rule in ("DOMAIN-SUFFIX,github.com,DIRECT","DOMAIN-SUFFIX,rejail.ru,DIRECT",
                     "DOMAIN-SUFFIX,getutm.app,🇫🇮 Финляндия","DOMAIN-SUFFIX,platipomiru.com,🇫🇮 Финляндия",
                     "DOMAIN-SUFFIX,youtube.com,🇫🇮 Финляндия","DOMAIN-SUFFIX,instagram.com,🇫🇮 Финляндия"):
            with self.subTest(rule=rule):
                changed=[line for line in self.configs["main"] if line!=rule]
                self.assertTrue(any("main:" in e for e in self.errors_for(self.expected.splitlines(),main=changed)))


if __name__=="__main__":
    unittest.main()
