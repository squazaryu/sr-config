"""Guard the explicitly selected Finnish recovery route (no auto-testing)."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_GROUP = (
    "🤖 AI-сервисы v2 = select,🇫🇮 ALL VPN | ФИНЛЯНДИЯ,"
    "🇫🇮 Финляндия (авто),policy-select-name=🇫🇮 ALL VPN | ФИНЛЯНДИЯ"
)


class AIRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.lines = (ROOT / "url-set-ios.conf").read_text().splitlines()
        self.ai_groups = [line for line in self.lines if line.startswith("🤖 AI-сервисы")]

    def test_exact_recovery_group_once(self):
        self.assertEqual(self.ai_groups, [EXPECTED_GROUP])

    def test_ai_has_no_background_test_or_subscription_parameters(self):
        self.assertEqual(len(self.ai_groups), 1)
        for parameter in ("interval=", "timeout=", "url=", "tolerance=", "use=true"):
            self.assertNotIn(parameter, self.ai_groups[0])

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


if __name__ == "__main__":
    unittest.main()
