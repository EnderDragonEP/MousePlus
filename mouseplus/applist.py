"""The Smooth tab's list of apps that scroll normally, and the dialog that adds one."""
import os

from PyQt6.QtCore import QFileInfo, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QFileDialog, QFileIconProvider, QHBoxLayout, QListWidgetItem, QSizePolicy, QVBoxLayout,
                             QWidget)
from qfluentwidgets import (BodyLabel, CaptionLabel, ExpandSettingCard, FluentIcon as FIF, ListWidget, MessageBoxBase,
                            PushButton, SubtitleLabel, ToolButton, TransparentPushButton, qconfig)

from . import winapi
from .config import IMAGE_VIEWERS

_SECONDARY = (QColor(96, 96, 96), QColor(206, 206, 206))  # light, dark
_TITLE_CHARS = 48  # longer window titles are shortened so the program name stays visible


class AppItem(QWidget):
    """One app in the list: its name and program file, with a remove button."""

    removed = pyqtSignal(str)

    def __init__(self, program: str, parent=None):
        super().__init__(parent)
        self.program = program
        name = IMAGE_VIEWERS.get(program)
        self.nameLabel = BodyLabel(name or program, self)
        self.programLabel = CaptionLabel(program, self)
        self.programLabel.setTextColor(*_SECONDARY)
        self.programLabel.setVisible(bool(name))  # unknown apps already show the program file
        self.removeButton = ToolButton(FIF.CLOSE, self)
        self.removeButton.setFixedSize(39, 29)
        self.removeButton.setIconSize(QSize(12, 12))
        self.removeButton.clicked.connect(lambda: self.removed.emit(self.program))

        text = QVBoxLayout()
        text.setSpacing(0)
        text.addStretch(1)  # keep the two lines together, centred in the row
        text.addWidget(self.nameLabel)
        text.addWidget(self.programLabel)
        text.addStretch(1)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(48, 0, 60, 0)  # lined up with the card's title, like a folder list
        layout.addLayout(text)
        layout.addStretch(1)
        layout.addWidget(self.removeButton, 0, Qt.AlignmentFlag.AlignRight)
        self.setFixedHeight(53)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)


class AppListCard(ExpandSettingCard):
    """Expandable card listing the programs in a list config item, with an "Add app" button."""

    def __init__(self, configItem, icon, title: str, content: str, parent=None):
        super().__init__(icon, title, content, parent)
        self.configItem = configItem
        self.items = {}
        self.addButton = PushButton("Add app", self, FIF.ADD)
        self.addButton.clicked.connect(self._pick)
        self.addWidget(self.addButton)
        self.viewLayout.setSpacing(0)
        self.viewLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        for program in configItem.value:
            self._addItem(program)

    def _pick(self):
        picker = AppPicker(set(self.configItem.value), self.window())
        if picker.exec() and picker.program and picker.program not in self.configItem.value:
            qconfig.set(self.configItem, [*self.configItem.value, picker.program])
            self._addItem(picker.program)
            self.setExpand(True)

    def _addItem(self, program: str):
        item = AppItem(program, self.view)
        item.removed.connect(self._remove)
        self.viewLayout.addWidget(item)
        item.show()
        self.items[program] = item
        self._adjustViewSize()

    def _remove(self, program: str):
        qconfig.set(self.configItem, [p for p in self.configItem.value if p != program])
        item = self.items.pop(program)
        self.viewLayout.removeWidget(item)
        item.deleteLater()
        self._adjustViewSize()


class AppPicker(MessageBoxBase):
    """Pick one of the open apps, or browse for a program file. `program` holds the choice."""

    def __init__(self, listed: set, parent=None):
        super().__init__(parent)
        self.program = ""
        self.titleLabel = SubtitleLabel("Add an app", self)
        self.hintLabel = BodyLabel("Pick an open app. In it, the wheel will scroll normally, one notch at a time.",
                                   self)
        self.hintLabel.setWordWrap(True)
        self.list = ListWidget(self)
        self.list.setIconSize(QSize(20, 20))
        self.list.setFixedHeight(264)
        icons = QFileIconProvider()
        for path, title in winapi.open_apps():
            program = os.path.basename(path).lower()
            if program in listed:
                continue
            title = title if len(title) <= _TITLE_CHARS else title[:_TITLE_CHARS - 1].rstrip() + "…"
            item = QListWidgetItem(icons.icon(QFileInfo(path)), f"{title}  ({program})")
            item.setData(Qt.ItemDataRole.UserRole, program)
            item.setToolTip(path)
            self.list.addItem(item)
        self.browseButton = TransparentPushButton("Browse for a program…", self, FIF.FOLDER)

        for widget in (self.titleLabel, self.hintLabel, self.list):
            self.viewLayout.addWidget(widget)
        self.viewLayout.addWidget(self.browseButton, 0, Qt.AlignmentFlag.AlignLeft)
        self.yesButton.setText("Add")
        self.yesButton.setEnabled(False)
        self.cancelButton.setText("Cancel")
        self.widget.setMinimumWidth(540)

        self.list.itemSelectionChanged.connect(lambda: self.yesButton.setEnabled(bool(self.list.selectedItems())))
        self.list.itemDoubleClicked.connect(lambda _: self.yesButton.click())
        self.browseButton.clicked.connect(self._browse)

    def validate(self) -> bool:
        items = self.list.selectedItems()
        self.program = items[0].data(Qt.ItemDataRole.UserRole) if items else ""
        return bool(self.program)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose a program", os.environ.get("ProgramFiles", ""),
                                              "Programs (*.exe)")
        if path:
            self.program = os.path.basename(path).lower()
            self.accept()
