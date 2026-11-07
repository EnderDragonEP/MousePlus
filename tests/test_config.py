import unittest

from mouseplus.config import (IMAGE_VIEWERS, ProgramListValidator, ProgramNamesValidator, cfg, program_label,
                              program_names)


class ProgramListTest(unittest.TestCase):
    def test_names_are_cleaned_up(self):
        self.assertEqual(program_names([" XnViewMP.exe ", "xnviewmp.exe", "", 42, None, "I_View64.EXE"]),
                         ["xnviewmp.exe", "i_view64.exe"])

    def test_anything_but_a_list_becomes_empty(self):
        for value in (None, "xnviewmp.exe", {"a": 1}, 3):
            self.assertEqual(program_names(value), [])

    def test_validator(self):
        validator = ProgramListValidator()
        self.assertTrue(validator.validate(["xnviewmp.exe"]))
        self.assertFalse(validator.validate(["XnViewMP.exe"]))
        self.assertEqual(validator.correct(["XnViewMP.exe"]), ["xnviewmp.exe"])

    def test_label_shows_the_name_and_the_program_file(self):
        self.assertEqual(program_label("xnviewmp.exe"), "XnView MP (xnviewmp.exe)")
        self.assertEqual(program_label("notepad.exe"), "notepad.exe")  # no name known

    def test_label_uses_the_name_kept_for_an_app_added_by_hand(self):
        saved = cfg.smoothAppNames.value
        self.addCleanup(setattr, cfg.smoothAppNames, "value", saved)
        cfg.smoothAppNames.value = {"notepad.exe": "Notepad", "xnviewmp.exe": "Something else"}
        self.assertEqual(program_label("notepad.exe"), "Notepad (notepad.exe)")
        self.assertEqual(program_label("xnviewmp.exe"), "XnView MP (xnviewmp.exe)")  # the built-in name wins

    def test_names_validator(self):
        validator = ProgramNamesValidator()
        self.assertEqual(validator.correct({" Notepad.EXE ": " Notepad ", "blank.exe": " ", 3: "x", "y.exe": None}),
                         {"notepad.exe": "Notepad"})
        self.assertEqual(validator.correct(["notepad.exe"]), {})
        self.assertTrue(validator.validate({"notepad.exe": "Notepad"}))
        self.assertFalse(validator.validate({"Notepad.exe": "Notepad"}))

    def test_image_viewers_are_on_the_list_by_default(self):
        self.assertEqual(cfg.smoothExcluded.defaultValue, list(IMAGE_VIEWERS))
        self.assertIn("xnviewmp.exe", cfg.smoothExcluded.defaultValue)
        self.assertEqual(list(IMAGE_VIEWERS), program_names(list(IMAGE_VIEWERS)))  # stored as written


if __name__ == "__main__":
    unittest.main()
