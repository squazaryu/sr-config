"""Guard the macOS-style AI path while preserving the approved iOS node pool."""

import unittest
from pathlib import Path

import validate_configs


ROOT = Path(__file__).resolve().parents[1]
AI_GROUP = "🤖 AI-сервисы (Финляндия)"
FINLAND_GROUP = "🇫🇮 Финляндия (авто)"
EXPECTED_GROUP = f"{AI_GROUP} = select, {FINLAND_GROUP}"
EXPECTED_RULE = (
    "RULE-SET,https://raw.githubusercontent.com/squazaryu/sr-config/main/"
    f"lists/ai-services.list,{AI_GROUP},pre-matching,extended-matching"
)


class AIRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.lines = (ROOT / "url-set-ios.conf").read_text(encoding="utf-8").splitlines()
        self.macos = (ROOT / "url-set-macos.conf").read_text(encoding="utf-8").splitlines()
        self.ai_groups = [line for line in self.lines if line.startswith("🤖 AI-сервисы")]

    def test_new_ai_group_once(self):
        self.assertEqual(self.ai_groups, [EXPECTED_GROUP])

    def test_outer_ai_policy_matches_macos(self):
        self.assertEqual(len(self.ai_groups), 1)
        macos_group = next(line for line in self.macos if line.startswith("🤖 AI-сервисы ="))
        self.assertEqual(
            self.ai_groups[0].split("=", 1)[1].strip(),
            macos_group.split("=", 1)[1].strip(),
        )

    def test_ai_has_one_local_group_and_no_independent_test(self):
        self.assertEqual(len(self.ai_groups), 1)
        fields = [part.strip() for part in self.ai_groups[0].split("=", 1)[1].split(",")]
        self.assertEqual(fields, ["select", FINLAND_GROUP])
        self.assertEqual(sum(line.startswith(f"{FINLAND_GROUP} =") for line in self.lines), 1)

    def test_shared_finland_pool_keeps_seven_approved_candidates(self):
        group = next(line for line in self.lines if line.startswith(f"{FINLAND_GROUP} ="))
        fields = [part.strip() for part in group.split("=", 1)[1].split(",")]
        self.assertEqual(fields[0], "url-test")
        members = [field for field in fields[1:] if "=" not in field]
        self.assertEqual(members, [
            "🇫🇮 PROXY TG | ФИНЛЯНДИЯ",
            "🇫🇮 FASTCON VPN | ФИНЛЯНДИЯ",
            "🇫🇮 SODA VPN | ФИНЛЯНДИЯ",
            "🇫🇮 HIT VPN | ФИНЛЯНДИЯ",
            "🇫🇮 ALL VPN | ФИНЛЯНДИЯ",
            "🇫🇮 ДАРВИН ВПН | ФИНЛЯНДИЯ",
            "🇫🇮 FASTCOM VPN | ФИНЛЯНДИЯ",
        ])
        options = dict(field.split("=", 1) for field in fields[1:] if "=" in field)
        self.assertEqual(options, {
            "policy-select-name": "🇫🇮 PROXY TG | ФИНЛЯНДИЯ",
            "interval": "300",
            "tolerance": "50",
            "timeout": "5",
            "url": "http://www.gstatic.com/generate_204",
        })

    def test_ai_list_uses_only_recovery_group(self):
        references = [line for line in self.lines if line.startswith("RULE-SET,")
                      and "/lists/ai-services.list," in line]
        self.assertEqual(references, [EXPECTED_RULE])
        macos_rule = next(line for line in self.macos if line.startswith("RULE-SET,")
                         and "/lists/ai-services.list," in line)
        ios_fields = references[0].split(",")
        macos_fields = macos_rule.split(",")
        self.assertEqual(ios_fields[:2] + ios_fields[3:], macos_fields[:2] + macos_fields[3:])

    def test_telegram_and_weather_keep_selected_proxy(self):
        for prefix in ("✈️ Telegram v2 =", "🌤️ Погода v2 ="):
            group = next(line for line in self.lines if line.startswith(prefix))
            self.assertIn("= select,PROXY,", group)
            self.assertIn("policy-select-name=PROXY", group)

    def test_stale_finland_candidates_do_not_return(self):
        group = next(line for line in self.lines if line.startswith("🇫🇮 Финляндия (авто) ="))
        fields = [part.strip() for part in group.split("=", 1)[1].split(",")]
        members = [field for field in fields[1:] if "=" not in field]
        self.assertEqual(len(members), 7)
        for old in ("🇫🇮 ФИНЛЯНДИЯ", "🇫🇮 ФИНЛЯНДИЯ 2", "FINLAND 🇫🇮"):
            self.assertNotIn(old, members)


class AIPathValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baselines = {
            name: path.read_text(encoding="utf-8").splitlines()
            for name, path in validate_configs.CONFIGS.items()
        }

    def errors_for_group(self, group):
        configs = dict(self.baselines)
        ios_lines = []
        for line in configs["ios"]:
            if line.startswith("🤖 AI-сервисы"):
                ios_lines.extend(group.splitlines())
            elif line.startswith("RULE-SET,") and "/lists/ai-services.list," in line:
                ios_lines.append(EXPECTED_RULE)
            else:
                ios_lines.append(line)
        configs["ios"] = ios_lines
        errors = []
        validate_configs.validate_ios_service_routes(configs, errors)
        return errors

    def test_validator_accepts_macos_style_path(self):
        self.assertEqual(self.errors_for_group(EXPECTED_GROUP), [])

    def test_validator_rejects_independent_ai_selection(self):
        changes = (
            ("= select,", "= url-test,"),
            ("= select,", "= fallback,"),
            (FINLAND_GROUP, "PROXY"),
            (FINLAND_GROUP, "DIRECT"),
            (FINLAND_GROUP, "🇫🇮 ALL VPN | ФИНЛЯНДИЯ"),
            (FINLAND_GROUP, "🇫🇮 ФИНЛЯНДИЯ"),
            (FINLAND_GROUP, f"{FINLAND_GROUP},PROXY"),
            (FINLAND_GROUP, f"{FINLAND_GROUP},use=true"),
            (FINLAND_GROUP, f"{FINLAND_GROUP},interval=600"),
            (AI_GROUP, "🤖 AI-сервисы v2"),
            (AI_GROUP, "🤖 AI-сервисы v3"),
        )
        for old, new in changes:
            with self.subTest(old=old, new=new):
                errors = self.errors_for_group(EXPECTED_GROUP.replace(old, new, 1))
                self.assertTrue(any("🤖 AI-сервисы" in error for error in errors), errors)

    def test_validator_rejects_legacy_ai_groups_alongside_new_group(self):
        for legacy in ("🤖 AI-сервисы", "🤖 AI-сервисы v2", "🤖 AI-сервисы v3"):
            with self.subTest(legacy=legacy):
                group = EXPECTED_GROUP + f"\n{legacy} = select,PROXY"
                errors = self.errors_for_group(group)
                self.assertTrue(any("устаревшая service group" in error and legacy in error
                                    for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
