"""Guard the user-confirmed final iOS profile identity and defaults."""

from pathlib import Path
import unittest

import validate_configs as validation


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "url-set-ios.conf"
HEADER = "# Shadowrocket: 2026-09-11 22:50:53"
TELEGRAM = "select,AUTO,PROXY,SERVERS,FINLAND,policy-select-name=PROXY"


class IOSFinalProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lines = PROFILE.read_text(encoding="utf-8").splitlines()
        cls.groups = {
            name.strip(): value.strip()
            for line in validation.meaningful(validation.section_lines(cls.lines, "[Proxy Group]"))
            for name, value in [line.split("=", 1)]
        }

    def test_final_profile_header_is_exact(self):
        self.assertEqual(self.lines[0], HEADER)

    def test_telegram_defaults_to_the_selected_proxy(self):
        self.assertEqual(self.groups["TELEGRAM"], TELEGRAM)


if __name__ == "__main__":
    unittest.main()
