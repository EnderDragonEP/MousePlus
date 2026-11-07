import unittest

from mouseplus.config import IMAGE_VIEWERS, ProgramListValidator, cfg, program_label, program_names


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
        self.assertEqual(program_label("notepad.exe"), "notepad.exe")  # added by hand: no name to show

    def test_image_viewers_are_on_the_list_by_default(self):
        self.assertEqual(cfg.smoothExcluded.defaultValue, list(IMAGE_VIEWERS))
        self.assertIn("xnviewmp.exe", cfg.smoothExcluded.defaultValue)
        self.assertEqual(list(IMAGE_VIEWERS), program_names(list(IMAGE_VIEWERS)))  # stored as written


if __name__ == "__main__":
    unittest.main()
