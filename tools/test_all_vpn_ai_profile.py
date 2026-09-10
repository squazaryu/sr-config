"""Verify the single-node ALL VPN AI canary differs only in its AI group."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
HYBRID = ROOT / "archive/2026-09-10/url-set-ios-hybrid-test.conf"
FIXED = ROOT / "archive/2026-09-10/url-set-ios-ai-all-vpn-test.conf"


def section(text, name):
    lines = text.splitlines()
    start = lines.index(name) + 1
    end = next((i for i in range(start, len(lines))
                if lines[i].startswith("[") and lines[i].endswith("]")), len(lines))
    result = lines[start:end]
    while result and not result[-1].strip():
        result.pop()
    return result


class AllVPNAIProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hybrid = HYBRID.read_text(encoding="utf-8")
        cls.fixed = FIXED.read_text(encoding="utf-8")

    def test_fixed_profile_exists_and_uses_one_known_unstable_node(self):
        groups = section(self.fixed, "[Proxy Group]")
        ai = next(line for line in groups if line.startswith("AI ="))
        self.assertEqual(ai, "AI = select,🇫🇮 ALL VPN | ФИНЛЯНДИЯ,policy-select-name=🇫🇮 ALL VPN | ФИНЛЯНДИЯ")
        self.assertNotIn("PROXY", ai)

    def test_fixed_profile_keeps_reference_general_and_all_rules(self):
        self.assertEqual(section(self.fixed, "[General]"),
                         section(self.hybrid, "[General]"))
        self.assertEqual(section(self.fixed, "[Rule]"),
                         section(self.hybrid, "[Rule]"))

    def test_only_ai_group_differs_from_hybrid(self):
        hybrid_groups = section(self.hybrid, "[Proxy Group]")
        fixed_groups = section(self.fixed, "[Proxy Group]")
        self.assertEqual(len(hybrid_groups), len(fixed_groups))
        for hybrid, fixed in zip(hybrid_groups, fixed_groups):
            if hybrid.startswith("AI ="):
                continue
            self.assertEqual(hybrid, fixed)


if __name__ == "__main__":
    unittest.main()
