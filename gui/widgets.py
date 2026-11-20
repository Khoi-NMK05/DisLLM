"""
Small shared widgets for the Discord-styled desktop UI.
"""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class Card(QFrame):
    """A flat #2b2d31 surface with an uppercase section header; add content to `body`."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("class", "card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 16)
        outer.setSpacing(12)

        self.header = QLabel(title.upper())
        self.header.setProperty("class", "cardTitle")
        outer.addWidget(self.header)

        self.body = QVBoxLayout()
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(10)
        outer.addLayout(self.body, stretch=1)  # extra height goes to content, not around the header

    def setTitle(self, title: str) -> None:  # noqa: N802 - mirrors QGroupBox API
        self.header.setText(title.upper())

    def title(self) -> str:
        return self.header.text()


class StatusLabel(QLabel):
    """A word-wrapped feedback label that stays hidden until it has text."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setWordWrap(True)
        if not text:
            self.hide()

    def setText(self, text: str) -> None:  # noqa: N802 - Qt override
        super().setText(text)
        # A parentless widget would pop up as its own window if shown.
        if self.parentWidget() is not None or not text:
            self.setVisible(bool(text))
