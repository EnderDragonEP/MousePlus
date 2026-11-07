"""Checks GitHub for a newer release, without blocking the UI."""
import json
import re
from dataclasses import dataclass

from PyQt6.QtCore import QObject, QUrl, pyqtSignal
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from . import REPO_URL, __version__

LATEST_RELEASE_API = REPO_URL.replace("https://github.com/", "https://api.github.com/repos/") + "/releases/latest"


def parse_version(text: str) -> tuple:
    """'v1.2.3', '1.2' or '1.2.3-beta' -> (1, 2, 3); missing parts count as 0."""
    numbers = [int(n) for n in re.findall(r"\d+", text.split("-")[0])[:3]]
    return tuple(numbers + [0] * (3 - len(numbers)))


def version_from_tag(tag: str) -> str:
    """'v1.2.3', 'V1.2.3' or 'v.1.2.3' -> '1.2.3' (everything before the first digit is dropped)."""
    return re.sub(r"^\D+", "", tag)


def is_newer(latest: str, current: str = __version__) -> bool:
    return parse_version(latest) > parse_version(current)


@dataclass(frozen=True)
class Release:
    version: str  # without any prefix, e.g. "1.1.0"
    url: str      # the release page on GitHub


class UpdateChecker(QObject):
    """Asks the GitHub API for the latest published release (drafts and pre-releases are skipped)."""

    finished = pyqtSignal(object)  # Release, or None when no release has been published yet
    failed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._network = QNetworkAccessManager(self)

    def check(self):
        request = QNetworkRequest(QUrl(LATEST_RELEASE_API))
        request.setRawHeader(b"Accept", b"application/vnd.github+json")
        request.setHeader(QNetworkRequest.KnownHeaders.UserAgentHeader, f"MousePlus/{__version__}")
        request.setTransferTimeout(10_000)
        reply = self._network.get(request)
        reply.finished.connect(lambda: self._onFinished(reply))

    def _onFinished(self, reply: QNetworkReply):
        reply.deleteLater()
        if reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute) == 404:
            self.finished.emit(None)
            return
        if reply.error() != QNetworkReply.NetworkError.NoError:
            self.failed.emit(reply.errorString())
            return
        try:
            data = json.loads(bytes(reply.readAll()))
            self.finished.emit(Release(version_from_tag(data["tag_name"]), data["html_url"]))
        except (ValueError, KeyError, TypeError, AttributeError):
            self.failed.emit("GitHub sent an unexpected response.")
