"""N01 changes local identifiers only; it is not a Shadowrocket runtime emulator."""

import unittest
from pathlib import Path

import validate_configs as validation


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "url-set-ios-names-test.conf"
UPDATE_URL = (
    "update-url = https://raw.githubusercontent.com/squazaryu/sr-config/main/"
    "url-set-ios-names-test.conf"
)
NAMES = {
    "🤖 AI-сервисы (Финляндия)": "AI",
    "🎧 Spotify": "SPOTIFY",
    "🌤️ Погода v2": "WEATHER",
    "✈️ Telegram v2": "TELEGRAM",
    "🌍 Общий прокси": "DEFAULT",
    "📺 YouTube": "YOUTUBE",
    "🛡️ Реклама и трекеры": "ADS",
    "🇫🇮 Финляндия (авто)": "FINLAND",
    "🗺️ Выбор сервера": "SERVERS",
    "🚀 Авто (пинг)": "AUTO",
}


def section(lines, name):
    return validation.meaningful(validation.section_lines(lines, name))


def mapped_token(token):
    """Casefold identifies OLD local aliases for this explicit rename, not runtime matching."""
    lookup = {old.casefold(): new for old, new in NAMES.items()}
    stripped = token.strip()
    replacement = lookup.get(stripped.casefold())
    return token.replace(stripped, replacement, 1) if replacement is not None else token


def expected_lines(base):
    result = []
    current = None
    for line in validation.meaningful(base):
        if line.startswith("["):
            current = line
        elif current == "[General]" and line.startswith("update-url ="):
            line = UPDATE_URL
        elif current == "[Proxy Group]":
            name, value = line.split("=", 1)
            fields = value.split(",")
            for index, field in enumerate(fields[1:], 1):
                if field.strip().startswith("policy-select-name="):
                    key, target = field.split("=", 1)
                    fields[index] = key + "=" + mapped_token(target)
                elif "=" not in field:
                    fields[index] = mapped_token(field)
            line = mapped_token(name) + "=" + ",".join(fields)
        elif current == "[Rule]":
            fields = line.split(",")
            index = -1 if fields[0] == "AND" else 1 if fields[0] == "FINAL" else 2
            fields[index] = mapped_token(fields[index])
            line = ",".join(fields)
        result.append(line)
    return result


class NamesTestProfileTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(PROFILE.is_file(), "The requested separate naming test must exist")
        self.text = PROFILE.read_text(encoding="utf-8")
        self.lines = self.text.splitlines()
        self.base = (ROOT / "url-set-ios.conf").read_text(encoding="utf-8").splitlines()
        self.rules = section(self.lines, "[Rule]")
        self.groups = {
            name.strip(): value.strip()
            for line in section(self.lines, "[Proxy Group]")
            for name, value in [line.split("=", 1)]
        }

    def test_only_declared_renames_and_own_update_url(self):
        self.assertEqual(validation.meaningful(self.lines), expected_lines(self.base))

    def test_unique_minimal_names_without_builtin_collisions(self):
        self.assertEqual(list(self.groups), list(NAMES.values()))
        self.assertEqual(len(section(self.lines, "[Proxy Group]")), len(NAMES))
        for name in self.groups:
            self.assertRegex(name, r"^[A-Z][A-Z0-9]*$")
            self.assertNotIn(name.upper(), validation.BUILTIN_POLICIES)

    def test_network_settings_unchanged_except_own_update_url(self):
        general = section(self.lines, "[General]")
        self.assertEqual([line for line in general if line.startswith("update-url")], [UPDATE_URL])
        without_url = lambda lines: [line for line in lines if not line.startswith("update-url")]
        self.assertEqual(without_url(general), without_url(section(self.base, "[General]")))

    def test_finland_automatic_pool_and_probe_are_identical(self):
        original = next(line for line in section(self.base, "[Proxy Group]")
                        if line.startswith("🇫🇮 Финляндия (авто) ="))
        self.assertIn("FINLAND", self.groups)
        self.assertEqual(self.groups["FINLAND"], original.split("=", 1)[1].strip())
        self.assertTrue(self.groups["FINLAND"].startswith("url-test,"))
        self.assertEqual(self.groups["AI"], "select,FINLAND,policy-select-name=FINLAND")

    def test_every_local_reference_has_exact_case(self):
        targets = []
        for value in self.groups.values():
            for field in value.split(",")[1:]:
                if field.startswith("policy-select-name="):
                    targets.append(field.split("=", 1)[1].strip())
                elif "=" not in field:
                    targets.append(field.strip())
        for rule in self.rules:
            fields = rule.split(",")
            targets.append(fields[-1] if fields[0] == "AND" else fields[1] if fields[0] == "FINAL" else fields[2])
        for target in targets:
            folded_matches = [name for name in self.groups if name.casefold() == target.casefold()]
            if folded_matches:
                self.assertIn(target, self.groups)
            self.assertNotIn(target.casefold(), {name.casefold() for name in NAMES})

    def test_external_candidates_and_non_name_options_unchanged(self):
        local = {name.casefold() for name in NAMES}
        for line in section(self.base, "[Proxy Group]"):
            name, value = line.split("=", 1)
            original = value.strip().split(",")
            renamed = self.groups[NAMES[name.strip()]].split(",")
            self.assertEqual(len(original), len(renamed))
            for old, new in zip(original, renamed):
                target = old.split("=", 1)[1] if old.startswith("policy-select-name=") else old
                if target.strip().casefold() not in local:
                    self.assertEqual(new, old)

    def test_all_remote_sources_options_and_rule_order_preserved(self):
        before = section(self.base, "[Rule]")
        self.assertEqual(len(before), len(self.rules))
        sources = [rule for rule in self.rules if rule.startswith("RULE-SET,")]
        self.assertEqual(len(sources), 18)
        for old, new in zip(before, self.rules):
            old_fields, new_fields = old.split(","), new.split(",")
            index = -1 if old_fields[0] == "AND" else 1 if old_fields[0] == "FINAL" else 2
            old_fields[index] = new_fields[index] = "<policy>"
            self.assertEqual(old_fields, new_fields)

    def test_russian_direct_apple_and_github_unchanged(self):
        direct_before = [rule for rule in section(self.base, "[Rule]") if ",DIRECT" in rule]
        self.assertEqual([rule for rule in self.rules if ",DIRECT" in rule], direct_before)
        self.assertIn("GEOIP,RU,DIRECT", self.rules)
        self.assertEqual(self.rules[-1], "FINAL,PROXY")

    def test_general_weather_telegram_paths_are_not_rebound(self):
        for name in ("DEFAULT", "WEATHER", "TELEGRAM"):
            self.assertIn(name, self.groups)
        self.assertEqual(self.groups["DEFAULT"], "select,PROXY,policy-select-name=PROXY")
        self.assertEqual(self.groups["WEATHER"], "select,PROXY,DIRECT,FINLAND,policy-select-name=PROXY")
        self.assertEqual(self.groups["TELEGRAM"], "select,PROXY,SERVERS,FINLAND,AUTO,policy-select-name=PROXY")

    def test_structure_and_no_secrets(self):
        errors = []
        _groups, rules = validation.validate_structure("ios-names-test", self.lines, errors)
        validation.validate_general("ios-names-test", self.lines, errors)
        validation.validate_apple_watch_rules("ios-names-test", self.lines, errors)
        validation.validate_sources("ios-names-test", rules, errors)
        self.assertEqual(errors, [])
        self.assertIsNone(validation.SECRET_PATTERN.search(self.text))
        self.assertEqual([line for line in self.lines if line.startswith("[")],
                         ["[General]", "[Proxy Group]", "[Rule]"])


if __name__ == "__main__":
    unittest.main()
