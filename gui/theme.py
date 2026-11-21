"""
Discord-native dark theme for the Discord AI Companion desktop app.

Surfaces step up in lightness only (no outlines on cards):
  BASE #1e1f22 (window, sidebar) -> CARD #2b2d31 -> RAISED #35373c (hover) / #404249 (selected)
Insets (inputs, wells) sink below their card: #1e1f22 / #111214.
One accent: Blurple #5865f2. Status colors follow Discord presence.
"""

import os
import tempfile

# Qt 6 stylesheets can't draw arrows/ticks from CSS borders, so we ship tiny SVGs.
# They are written to a temp folder at startup so this also works in the frozen .exe.
_ICONS = {
    "CHEVRON_DOWN": '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 12 12">'
    '<path d="M2.5 4.5 6 8l3.5-3.5" fill="none" stroke="#b5bac1" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "CHEVRON_UP": '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 12 12">'
    '<path d="M2.5 7.5 6 4l3.5 3.5" fill="none" stroke="#b5bac1" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "CHECK_MARK": '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 14 14">'
    '<path d="M3 7.2 5.8 10 11 4" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
}


def _icon_urls() -> dict[str, str]:
    folder = os.path.join(tempfile.gettempdir(), "discord_ai_companion_icons")
    os.makedirs(folder, exist_ok=True)
    urls = {}
    for name, svg in _ICONS.items():
        path = os.path.join(folder, name.lower() + ".svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)
        urls[name] = '"' + path.replace("\\", "/") + '"'  # quoted: temp paths may contain spaces
    return urls


TOKENS = {
    "BASE": "#1e1f22",
    "CARD": "#2b2d31",
    "RAISED": "#35373c",
    "SELECTED": "#404249",
    "INSET": "#1e1f22",
    "WELL": "#111214",
    "TEXT": "#dbdee1",
    "TEXT_STRONG": "#f2f3f5",
    "TEXT_MUTED": "#949ba4",
    "TEXT_FAINT": "#6d6f78",
    "HAIRLINE": "rgba(255, 255, 255, 0.06)",
    "BLURPLE": "#5865f2",
    "BLURPLE_HOVER": "#4752c4",
    "BLURPLE_PRESSED": "#3c45a5",
    "GREY_BTN": "#4e5058",
    "GREY_BTN_HOVER": "#6d6f78",
    "GREEN": "#23a55a",
    "RED": "#da373c",
    "RED_HOVER": "#a12828",
    # Feedback text (StatusLabel tones). Lighter than the button fills so they pass 4.5:1 on CARD.
    "TEXT_SUCCESS": "#2dc770",
    "TEXT_WARNING": "#f0b232",
    "TEXT_DANGER": "#fa777c",
}

_QSS = """
/* Text defaults only: backgrounds are set per surface so labels never paint boxes on cards. */
QWidget {
    color: TEXT;
    font-family: "Segoe UI", "gg sans", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
    selection-background-color: BLURPLE;
    selection-color: #ffffff;
}

QMainWindow, QDialog, QMessageBox, QStackedWidget {
    background-color: BASE;
}

QLabel, QCheckBox, QRadioButton {
    background: transparent;
}

/* ---- Sidebar: Discord channel list ------------------------------------ */
QFrame#sidebar {
    background-color: BASE;
    border-right: 1px solid HAIRLINE;
}

QLabel#sidebarHeader {
    color: TEXT_STRONG;
    font-size: 15px;
    font-weight: 600;
    padding: 0 16px;
    min-height: 48px;
    max-height: 48px;
    border-bottom: 1px solid HAIRLINE;
}

QLabel#sidebarSection {
    color: TEXT_MUTED;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.4px;
    padding: 18px 16px 6px 16px;
}

QListWidget#nav {
    background: transparent;
    border: none;
    outline: none;
    padding: 0 8px;
    font-size: 14px;
    font-weight: 500;
}

QListWidget#nav::item {
    color: TEXT_MUTED;
    padding: 7px 8px;
    margin: 1px 0;
    border-radius: 4px;
    border-left: 3px solid transparent;
}

QListWidget#nav::item:hover {
    background-color: RAISED;
    color: TEXT;
}

QListWidget#nav::item:selected {
    background-color: SELECTED;
    color: #ffffff;
    border-left: 3px solid BLURPLE;
}

/* Pinned status panel: Discord's bottom-left user panel */
QFrame#statusPanel {
    background-color: CARD;
    border-top: 1px solid HAIRLINE;
}

QLabel#statusAvatar {
    background-color: BLURPLE;
    color: #ffffff;
    border-radius: 17px;
    font-size: 15px;
    font-weight: 700;
}

QLabel#statusDot {
    border-radius: 7px;
    border: 3px solid CARD;
}

QLabel#statusName {
    color: TEXT_STRONG;
    font-size: 13px;
    font-weight: 600;
}

QLabel#statusState {
    color: TEXT_MUTED;
    font-size: 12px;
}

/* ---- Cards ------------------------------------------------------------- */
QFrame.card {
    background-color: CARD;
    border: none;
    border-radius: 8px;
}

QLabel.cardTitle {
    color: TEXT_MUTED;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.4px;
}

/* Recessed wells inside cards (tool rows, editors, composers) */
QFrame.inset {
    background-color: INSET;
    border: none;
    border-radius: 6px;
}

/* Inputs inside a well sink one level further so they stay visible */
QFrame.inset QLineEdit, QFrame.inset QTextEdit, QFrame.inset QPlainTextEdit,
QFrame.inset QComboBox, QFrame.inset QSpinBox, QFrame.inset QTextBrowser {
    background-color: WELL;
}

QTableWidget QPushButton { padding: 4px 12px; }

QFrame.replyBanner {
    background-color: INSET;
    border-left: 3px solid BLURPLE;
    border-radius: 4px;
}

/* ---- Buttons ----------------------------------------------------------- */
QPushButton {
    background-color: GREY_BTN;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 7px 16px;
    font-weight: 500;
    font-size: 13px;
    min-height: 18px;
}

QPushButton:hover { background-color: GREY_BTN_HOVER; }
QPushButton:pressed { background-color: SELECTED; }

QPushButton:disabled {
    background-color: RAISED;
    color: TEXT_FAINT;
}

QPushButton.primary { background-color: BLURPLE; }
QPushButton.primary:hover { background-color: BLURPLE_HOVER; }
QPushButton.primary:pressed { background-color: BLURPLE_PRESSED; }
QPushButton.primary:disabled { background-color: RAISED; color: TEXT_FAINT; }

QPushButton.success { background-color: GREEN; }
QPushButton.success:hover { background-color: #1a8a4a; }
QPushButton.success:disabled { background-color: RAISED; color: TEXT_FAINT; }

QPushButton.danger { background-color: RED; }
QPushButton.danger:hover { background-color: RED_HOVER; }
QPushButton.danger:disabled { background-color: RAISED; color: TEXT_FAINT; }

/* ---- Inputs: sunk below the card --------------------------------------- */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QTextBrowser {
    background-color: INSET;
    color: TEXT;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 7px 10px;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid BLURPLE;
}

QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {
    color: TEXT_FAINT;
}

QComboBox {
    background-color: INSET;
    color: TEXT;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 6px 10px;
    min-height: 20px;
}

QComboBox:hover, QComboBox:focus { border: 1px solid BLURPLE; }

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 26px;
    border: none;
}

QComboBox::down-arrow { image: url(CHEVRON_DOWN); width: 12px; height: 12px; }

QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {
    subcontrol-origin: border;
    width: 20px;
    border: none;
    background: transparent;
}
QAbstractSpinBox::up-button { subcontrol-position: top right; }
QAbstractSpinBox::down-button { subcontrol-position: bottom right; }
QAbstractSpinBox::up-arrow { image: url(CHEVRON_UP); width: 10px; height: 10px; }
QAbstractSpinBox::down-arrow { image: url(CHEVRON_DOWN); width: 10px; height: 10px; }
QAbstractSpinBox::up-button:hover, QAbstractSpinBox::down-button:hover { background: RAISED; border-radius: 3px; }

/* Discord-style checkbox: rounded square, Blurple when checked */
QCheckBox { spacing: 8px; }
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid TEXT_FAINT;
    border-radius: 4px;
    background: INSET;
}
QCheckBox::indicator:hover { border-color: TEXT_MUTED; }
QCheckBox::indicator:checked { background: BLURPLE; border-color: BLURPLE; image: url(CHECK_MARK); }
QCheckBox::indicator:disabled { background: RAISED; border-color: RAISED; }

QComboBox QAbstractItemView {
    background-color: CARD;
    color: TEXT;
    border: 1px solid HAIRLINE;
    border-radius: 4px;
    padding: 4px;
    outline: none;
}

QComboBox QAbstractItemView::item { min-height: 26px; padding: 4px 8px; border-radius: 3px; }
QComboBox QAbstractItemView::item:hover { background-color: RAISED; }
QComboBox QAbstractItemView::item:selected { background-color: BLURPLE; color: #ffffff; }

/* ---- Sliders ----------------------------------------------------------- */
QSlider::groove:horizontal { height: 6px; background: GREY_BTN; border-radius: 3px; }
QSlider::sub-page:horizontal { background: BLURPLE; border-radius: 3px; }
QSlider::handle:horizontal {
    background: #ffffff;
    width: 14px;
    height: 14px;
    margin: -4px 0;
    border-radius: 7px;
}
QSlider::groove:horizontal:disabled, QSlider::sub-page:horizontal:disabled { background: RAISED; }

/* ---- Tables & lists inside cards --------------------------------------- */
QTableWidget, QListWidget {
    background-color: INSET;
    border: none;
    border-radius: 4px;
    gridline-color: HAIRLINE;
}

QHeaderView::section {
    background-color: CARD;
    color: TEXT_MUTED;
    border: none;
    padding: 6px 8px;
    font-size: 11px;
    font-weight: 700;
}

/* ---- Labels ------------------------------------------------------------ */
QLabel.muted { color: TEXT_MUTED; font-size: 12px; }
QLabel.heading { font-size: 16px; font-weight: 600; color: TEXT_STRONG; }

/* ---- Menus, tooltips, splitters, scrollbars ---------------------------- */
QMenu {
    background-color: WELL;
    border: 1px solid HAIRLINE;
    border-radius: 4px;
    padding: 6px;
}
QMenu::item { padding: 6px 12px; border-radius: 3px; }
QMenu::item:selected { background-color: BLURPLE; color: #ffffff; }

QToolTip {
    background-color: WELL;
    color: TEXT;
    border: none;
    padding: 6px 8px;
}

QSplitter::handle { background: transparent; }

QScrollBar:vertical { background: transparent; width: 8px; margin: 2px; }
QScrollBar::handle:vertical { background-color: WELL; min-height: 24px; border-radius: 4px; }
QScrollBar::handle:vertical:hover { background-color: GREY_BTN; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }

QStatusBar {
    background-color: BASE;
    color: TEXT_MUTED;
    border-top: 1px solid HAIRLINE;
    font-size: 12px;
}
"""

# Longest token names first so e.g. BLURPLE_HOVER isn't clobbered by BLURPLE.
DARK_THEME_QSS = _QSS
_values = {**TOKENS, **_icon_urls()}
for _name in sorted(_values, key=len, reverse=True):
    DARK_THEME_QSS = DARK_THEME_QSS.replace(_name, _values[_name])
