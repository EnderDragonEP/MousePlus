import json
import tempfile
import unittest
import winreg
from pathlib import Path

from mouseplus import APP_ID, OLD_APP_ID, config
from mouseplus.migrate import map_old_settings, migrate_autostart, migrate_settings

OLD_CONFIG = {
    "General": {"Enabled": False, "Trigger": "back", "ToggleMode": True,
                "DisableInFullscreen": False, "TrayHintShown": True},
    "Scrolling": {"Reverse": True, "Speed": 23},
    "QFluentWidgets": {"ThemeMode": "Auto", "ThemeColor": "#ff775817"},
}

SCRATCH_KEY = r"Software\MousePlusTest\Run"  # stands in for the real Run key


class MapSettingsTest(unittest.TestCase):
    def test_maps_every_old_setting(self):
        self.assertEqual(map_old_settings(OLD_CONFIG), {
            "HorizontalScroll": {"Enabled": False, "Trigger": "back", "ToggleMode": True,
                                 "Reverse": True, "Speed": 23},
            "General": {"DisableInFullscreen": False, "TrayHintShown": True},
        })

    def test_missing_or_odd_values_are_skipped(self):
        self.assertEqual(map_old_settings({}), {})
        self.assertEqual(map_old_settings({"General": "oops", "Scrolling": {"Speed": 7}}),
                         {"HorizontalScroll": {"Speed": 7}})


class MigrateSettingsTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        root = Path(self.dir.name)
        self.old = root / OLD_APP_ID / "config.json"
        self.new = root / APP_ID / "config.json"
        self.old.parent.mkdir()
        self.old.write_text(json.dumps(OLD_CONFIG), encoding="utf-8")

    def tearDown(self):
        self.dir.cleanup()

    def test_copies_once_and_keeps_the_old_file(self):
        self.assertTrue(migrate_settings(self.old, self.new))
        self.assertEqual(json.loads(self.new.read_text(encoding="utf-8")), map_old_settings(OLD_CONFIG))
        self.assertTrue(self.old.exists())
        self.assertFalse(migrate_settings(self.old, self.new))  # never overwrites newer settings

    def test_nothing_to_migrate(self):
        self.old.unlink()
        self.assertFalse(migrate_settings(self.old, self.new))
        self.assertFalse(self.new.exists())

    def test_broken_old_file_is_ignored(self):
        self.old.write_text("{not json", encoding="utf-8")
        self.assertFalse(migrate_settings(self.old, self.new))


class MigrateAutostartTest(unittest.TestCase):
    def tearDown(self):
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, SCRATCH_KEY)
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, SCRATCH_KEY.rsplit("\\", 1)[0])

    def test_replaces_the_old_entry(self):
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, SCRATCH_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, OLD_APP_ID, 0, winreg.REG_SZ, r'"C:\old\HorizontalScroll.exe" --tray')
        self.assertTrue(migrate_autostart(SCRATCH_KEY))
        self.assertIsNone(config.run_value(OLD_APP_ID, SCRATCH_KEY))
        self.assertEqual(config.run_value(APP_ID, SCRATCH_KEY), config.launch_command())

    def test_no_old_entry_means_no_new_entry(self):
        winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, SCRATCH_KEY, 0, winreg.KEY_SET_VALUE).Close()
        self.assertFalse(migrate_autostart(SCRATCH_KEY))
        self.assertIsNone(config.run_value(APP_ID, SCRATCH_KEY))


if __name__ == "__main__":
    unittest.main()
