"""Guard the exact AI group exported by the user on 2026-09-04 at 10:12:53."""

import unittest
from pathlib import Path

import validate_configs


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_GROUP = (
    "🤖 AI-сервисы v2 = url-test,🇫🇮 PROXY TG | ФИНЛЯНДИЯ,"
    "🇫🇮 ДАРВИН ВПН | ФИНЛЯНДИЯ,🇫🇮 SODA VPN | ФИНЛЯНДИЯ,"
    "🇫🇮 HIT VPN | ФИНЛЯНДИЯ,🇫🇮 FASTCOM VPN | ФИНЛЯНДИЯ,"
    "🇫🇮 ALL VPN | ФИНЛЯНДИЯ,policy-select-name=🇫🇮 ДАРВИН ВПН | ФИНЛЯНДИЯ,"
    "interval=600,tolerance=100,timeout=5,url=http://www.gstatic.com/generate_204"
)


class AIRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.lines = (ROOT / "url-set-ios.conf").read_text().splitlines()
        self.ai_groups = [line for line in self.lines if line.startswith("🤖 AI-сервисы")]

    def test_exact_user_export_group_once(self):
        self.assertEqual(self.ai_groups, [EXPECTED_GROUP])

    def test_ai_keeps_explicit_candidates_without_subscription_expansion(self):
        self.assertEqual(len(self.ai_groups), 1)
        fields = [part.strip() for part in self.ai_groups[0].split("=", 1)[1].split(",")]
        members = [field for field in fields[1:] if "=" not in field]
        self.assertEqual(members, [
            "🇫🇮 PROXY TG | ФИНЛЯНДИЯ",
            "🇫🇮 ДАРВИН ВПН | ФИНЛЯНДИЯ",
            "🇫🇮 SODA VPN | ФИНЛЯНДИЯ",
            "🇫🇮 HIT VPN | ФИНЛЯНДИЯ",
            "🇫🇮 FASTCOM VPN | ФИНЛЯНДИЯ",
            "🇫🇮 ALL VPN | ФИНЛЯНДИЯ",
        ])
        options = dict(field.split("=", 1) for field in fields[1:] if "=" in field)
        self.assertEqual(options, {
            "policy-select-name": "🇫🇮 ДАРВИН ВПН | ФИНЛЯНДИЯ",
            "interval": "600",
            "tolerance": "100",
            "timeout": "5",
            "url": "http://www.gstatic.com/generate_204",
        })

    def test_ai_list_uses_only_recovery_group(self):
        references = [line for line in self.lines if line.startswith("RULE-SET,")
                      and "/lists/ai-services.list," in line]
        self.assertEqual(references, [
            "RULE-SET,https://raw.githubusercontent.com/squazaryu/sr-config/main/"
            "lists/ai-services.list,🤖 AI-сервисы v2,pre-matching,extended-matching"
        ])

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


class AIExportValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baselines = {
            name: path.read_text(encoding="utf-8").splitlines()
            for name, path in validate_configs.CONFIGS.items()
        }

    def errors_for_group(self, group):
        configs = dict(self.baselines)
        configs["ios"] = [
            group if line.startswith("🤖 AI-сервисы") else line
            for line in configs["ios"]
        ]
        errors = []
        validate_configs.validate_ios_service_routes(configs, errors)
        return errors

    def test_validator_accepts_exact_user_export(self):
        self.assertEqual(self.errors_for_group(EXPECTED_GROUP), [])

    def test_validator_rejects_drift_from_user_export(self):
        changes = (
            ("= url-test,", "= fallback,"),
            ("= url-test,", "= select,"),
            ("interval=600", "interval=60"),
            ("tolerance=100", "tolerance=50"),
            ("timeout=5", "timeout=10"),
            ("http://www.gstatic.com/generate_204", "https://ios.chat.openai.com/cdn-cgi/trace"),
            ("policy-select-name=🇫🇮 ДАРВИН ВПН | ФИНЛЯНДИЯ", "policy-select-name=🇫🇮 ALL VPN | ФИНЛЯНДИЯ"),
            ("policy-select-name=🇫🇮 ДАРВИН ВПН | ФИНЛЯНДИЯ", "policy-select-name=🇫🇮 ДАРВИН ВПН |"),
            ("= url-test,", "= url-test,PROXY,"),
            ("= url-test,", "= url-test,🇫🇮 FASTCON VPN | ФИНЛЯНДИЯ,"),
            ("= url-test,", "= url-test,🇫🇮 ФИНЛЯНДИЯ,"),
            ("= url-test,", "= url-test,use=true,"),
        )
        for old, new in changes:
            with self.subTest(old=old, new=new):
                errors = self.errors_for_group(EXPECTED_GROUP.replace(old, new, 1))
                self.assertTrue(any("🤖 AI-сервисы v2" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
