import time
import unittest

from PyQt6.QtCore import QCoreApplication, QObject, pyqtSignal

from mouseplus import __version__
from mouseplus.updates import Release, StartupCheck, is_newer, parse_version, version_from_tag

app = QCoreApplication.instance() or QCoreApplication([])  # for the startup check's timer and signals


class UpdateVersionTest(unittest.TestCase):
    def test_parse_version(self):
        self.assertEqual(parse_version("v1.2.3"), (1, 2, 3))
        self.assertEqual(parse_version("1.2"), (1, 2, 0))
        self.assertEqual(parse_version("V2"), (2, 0, 0))
        self.assertEqual(parse_version("1.4.0-beta.2"), (1, 4, 0))

    def test_version_from_tag(self):
        self.assertEqual(version_from_tag("v1.2.3"), "1.2.3")
        self.assertEqual(version_from_tag("V1.2.3"), "1.2.3")
        self.assertEqual(version_from_tag("v.1.0.1"), "1.0.1")
        self.assertEqual(version_from_tag("1.0.0"), "1.0.0")

    def test_is_newer(self):
        self.assertTrue(is_newer("1.0.1", "1.0.0"))
        self.assertTrue(is_newer("v1.10.0", "1.9.9"))  # numeric, not alphabetical
        self.assertTrue(is_newer("2", "1.9"))
        self.assertFalse(is_newer("1.0.0", "1.0.0"))
        self.assertFalse(is_newer("v1.0", "1.0.0"))
        self.assertFalse(is_newer("0.9.0", "1.0.0"))


class FakeChecker(QObject):
    """Answers each check with the next scripted result: a Release, None (nothing published) or an error text."""

    finished = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, results):
        super().__init__()
        self.results = list(results)
        self.calls = 0

    def check(self):
        self.calls += 1
        result = self.results.pop(0)
        if isinstance(result, str):
            self.failed.emit(result)
        else:
            self.finished.emit(result)


class StartupCheckTest(unittest.TestCase):
    NEWER = Release("99.0.0", "https://example.com/release")

    def run_startup(self, results, enabled=lambda: True):
        """Run a startup check against scripted results; return (checks made, versions reported)."""
        checker = FakeChecker(results)
        check = StartupCheck(enabled, checker=checker, delays=(0, 0, 0))
        reported = []
        check.available.connect(lambda release: reported.append(release.version))
        check.start()
        end = time.monotonic() + 0.3
        while time.monotonic() < end:
            app.processEvents()
            time.sleep(0.005)
        return checker.calls, reported

    def test_reports_a_newer_version(self):
        self.assertEqual(self.run_startup([self.NEWER]), (1, ["99.0.0"]))

    def test_quiet_when_up_to_date_or_nothing_published(self):
        self.assertEqual(self.run_startup([Release(__version__, "url")]), (1, []))
        self.assertEqual(self.run_startup([None]), (1, []))

    def test_retries_a_failed_check_a_few_times(self):
        self.assertEqual(self.run_startup(["offline", "offline", self.NEWER]), (3, ["99.0.0"]))
        self.assertEqual(self.run_startup(["offline"] * 5), (3, []))  # then gives up quietly

    def test_turned_off_means_no_check(self):
        self.assertEqual(self.run_startup([self.NEWER], enabled=lambda: False), (0, []))

    def test_turned_off_while_checking_means_no_report(self):
        answers = iter([True, False])  # on when the check starts, off when the answer arrives
        self.assertEqual(self.run_startup([self.NEWER], enabled=lambda: next(answers)), (1, []))


if __name__ == "__main__":
    unittest.main()
