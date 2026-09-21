"""Guard the user-confirmed final iOS profile identity and defaults."""

from pathlib import Path
import unittest

import validate_configs as validation


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "url-set-ios.conf"
HEADER = "# Shadowrocket: 2026-09-21 12:49:46"
WEATHER = "url-test,AUTO,PROXY,policy-select-name=AUTO,interval=600,tolerance=100,timeout=5,url=http://www.gstatic.com/generate_204"
TELEGRAM = "select,AUTO,PROXY,SERVERS,FINLAND,policy-select-name=AUTO"
YOUTUBE = "select,SERVERS,PROXY,AUTO,FINLAND,DIRECT,policy-select-name=PROXY"
INSTAGRAM = "select,SERVERS,PROXY,AUTO,FINLAND,DIRECT,policy-select-name=PROXY"
AUTO = "url-test,⚡️ULTRA,AUTO 2 → [🚀 ОПТИМАЛЬНАЯ],AUTO 4 → [🚀 ОПТИМАЛЬНАЯ],AUTO 5 → [🚀 ОПТИМАЛЬНАЯ],AUTO 3 → [🚀 ОПТИМАЛЬНАЯ],AUTO → [🚀 ОПТИМАЛЬНАЯ ЛОКАЦИЯ],interval=300,tolerance=50,timeout=5,url=http://www.gstatic.com/generate_204"


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

    def test_user_selected_service_defaults_and_auto_pool_are_exact(self):
        self.assertEqual(self.groups["WEATHER"], WEATHER)
        self.assertEqual(self.groups["TELEGRAM"], TELEGRAM)
        self.assertEqual(self.groups["YOUTUBE"], YOUTUBE)
        self.assertEqual(self.groups["INSTAGRAM"], INSTAGRAM)
        self.assertEqual(self.groups["AUTO"], AUTO)


if __name__ == "__main__":
    unittest.main()
