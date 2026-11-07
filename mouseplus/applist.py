"""The Smooth tab's list of apps that scroll normally, and the dialog that adds one."""
import os

from PyQt6.QtCore import QFileInfo, QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QFileIconProvider, QHBoxLayout, QListWidgetItem, QSizePolicy, QWidget
from qfluentwidgets import (BodyLabel, ExpandSettingCard, FluentIcon as FIF, ListWidget, MessageBoxBase, PushButton,
                            SubtitleLabel, ToolButton, TransparentPushButton, qconfig)

from . import winapi
from .config import program_label

_TITLE_CHARS = 48  # longer window titles are shortened so the program name stays visible


class AppItem(QWidget):
    """One app in the list, "XnView MP (xnviewmp.exe)", with a remove button."""

    removed = pyqtSignal(str)

    def __init__(self, program: str, parent=None):
        super().__init__(parent)
        self.program = program
        self.label = BodyLabel(program_label(program), self)
        self.removeButton = ToolButton(FIF.CLOSE, self)
        self.removeButton.setFixedSize(39, 29)
        self.removeButton.setIconSize(QSize(12, 12))
        self.removeButton.clicked.connect(lambda: self.removed.emit(self.program))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(48, 0, 60, 0)  # lined up with the card's title, like a folder list
        layout.addWidget(self.label)
        layout.addStretch(1)
        layout.addWidget(self.removeButton, 0, Qt.AlignmentFlag.AlignRight)
        self.setFixedHeight(53)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)

    def refresh(self):
        self.label.setText(program_label(self.program))


class AppListCard(ExpandSettingCard):
    """Expandable card listing the programs in a list config item, with an "Add app" button.
    `namesItem` keeps the names of the apps added here (program file -> name)."""

    def __init__(self, configItem, namesItem, icon, title: str, content: str, parent=None):
        super().__init__(icon, title, content, parent)
        self.configItem = configItem
        self.namesItem = namesItem
        self.items = {}
        self.addButton = PushButton("Add app", self, FIF.ADD)
        self.addButton.clicked.connect(self._pick)
        self.addWidget(self.addButton)
        self.viewLayout.setSpacing(0)
        self.viewLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        for program in configItem.value:
            self._addItem(program)

    def showEvent(self, e):
        super().showEvent(e)
        self._nameOpenApps()

    def wheelEvent(self, e):
        # The card is a scroll area (for its expand animation) that swallows the wheel, so the page
        # wouldn't scroll with the cursor over the open list. Hand the wheel on to the page instead.
        e.ignore()

    def _pick(self):
        picker = AppPicker(set(self.configItem.value), self.window())
        if picker.exec() and picker.program and picker.program not in self.configItem.value:
            self._setName(picker.program, picker.name)
            qconfig.set(self.configItem, [*self.configItem.value, picker.program])
            self._addItem(picker.program)
            self.setExpand(True)

    def _setName(self, program: str, name: str):
        names = dict(self.namesItem.value)
        if name:
            names[program] = name
        else:
            names.pop(program, None)
        if names != self.namesItem.value:
            qconfig.set(self.namesItem, names)

    def _nameOpenApps(self):
        """Name the listed apps whose name isn't known yet (added before names were kept) if they're open now."""
        unnamed = {program for program in self.configItem.value if program_label(program) == program}
        if not unnamed:
            return
        for path, _ in winapi.open_apps():
            program = os.path.basename(path).lower()
            name = winapi.program_description(path) if program in unnamed else ""
            if name:
                self._setName(program, name)
                self.items[program].refresh()
                unnamed.discard(program)

    def _addItem(self, program: str):
        item = AppItem(program, self.view)
        item.removed.connect(self._remove)
        self.viewLayout.addWidget(item)
        item.show()
        self.items[program] = item
        self._adjustViewSize()

    def _remove(self, program: str):
        qconfig.set(self.configItem, [p for p in self.configItem.value if p != program])
        self._setName(program, "")
        item = self.items.pop(program)
        self.viewLayout.removeWidget(item)
        item.deleteLater()
        self._adjustViewSize()


class AppPicker(MessageBoxBase):
    """Pick one of the open apps, or browse for a program file. `program` and `name` hold the choice."""

    def __init__(self, listed: set, parent=None):
        super().__init__(parent)
        self.program, self.name = "", ""
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
            name = winapi.program_description(path)
            # Without a name of its own, show the window title (but don't keep it: it often names a document).
            shown = name or (title if len(title) <= _TITLE_CHARS else title[:_TITLE_CHARS - 1].rstrip() + "…")
            item = QListWidgetItem(icons.icon(QFileInfo(path)), f"{shown} ({program})")
            item.setData(Qt.ItemDataRole.UserRole, (program, name))
            item.setToolTip(f"{title}\n{path}")
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
        self.program, self.name = items[0].data(Qt.ItemDataRole.UserRole) if items else ("", "")
        return bool(self.program)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose a program", os.environ.get("ProgramFiles", ""),
                                              "Programs (*.exe)")
        if path:
            self.program, self.name = os.path.basename(path).lower(), winapi.program_description(path)
            self.accept()
