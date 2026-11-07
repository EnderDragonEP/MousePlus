import sys
import unittest

from mouseplus.winapi import program_description


class ProgramDescriptionTest(unittest.TestCase):
    def test_reads_the_name_from_the_version_info(self):
        self.assertEqual(program_description(sys.executable), "Python")  # python.exe calls itself "Python"

    def test_missing_or_unversioned_files_have_no_name(self):
        self.assertEqual(program_description(r"C:\does\not\exist.exe"), "")
        self.assertEqual(program_description(__file__), "")


if __name__ == "__main__":
    unittest.main()
