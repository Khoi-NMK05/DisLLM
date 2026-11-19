"""
Modern dark styling and theme definition for the Discord AI Companion Desktop app.
"""

DARK_THEME_QSS = """
/* Global Application Styles */
QWidget {
    background-color: #1e1f22;
    color: #dbdee1;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
    selection-background-color: #5865f2;
    selection-color: #ffffff;
}

/* Card / Group Container */
QFrame.card, QGroupBox {
    background-color: #2b2d31;
    border: 1px solid #35373c;
    border-radius: 8px;
    margin-top: 12px;
    padding: 14px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: #949ba4;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Tab Widget */
QTabWidget::pane {
    border: 1px solid #2b2d31;
    background-color: #1e1f22;
    border-radius: 6px;
    top: -1px;
}

QTabBar::tab {
    background-color: #2b2d31;
    color: #949ba4;
    padding: 10px 18px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: 600;
}

QTabBar::tab:hover {
    background-color: #35373c;
    color: #dbdee1;
}

QTabBar::tab:selected {
    background-color: #1e1f22;
    color: #5865f2;
    border-bottom: 2px solid #5865f2;
}

/* Push Buttons */
QPushButton {
    background-color: #4e5058;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 13px;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #6d6f78;
}

QPushButton:pressed {
    background-color: #404249;
}

QPushButton:disabled {
    background-color: #2b2d31;
    color: #5c5e66;
    border: 1px solid #35373c;
}

/* Primary Action Button */
QPushButton.primary {
    background-color: #5865f2;
    color: #ffffff;
}

QPushButton.primary:hover {
    background-color: #4752c4;
}

QPushButton.primary:pressed {
    background-color: #3c45a5;
}

/* Success Button */
QPushButton.success {
    background-color: #23a55a;
    color: #ffffff;
}

QPushButton.success:hover {
    background-color: #1f9450;
}

/* Danger Button */
QPushButton.danger {
    background-color: #da373c;
    color: #ffffff;
}

QPushButton.danger:hover {
    background-color: #c03135;
}

/* Line Inputs & Text Boxes */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {
    background-color: #111214;
    color: #dbdee1;
    border: 1px solid #35373c;
    border-radius: 6px;
    padding: 8px 10px;
    selection-background-color: #5865f2;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #5865f2;
}

/* ComboBox Styling with Explicit Dropdown Arrow */
QComboBox {
    background-color: #111214;
    color: #dbdee1;
    border: 1px solid #35373c;
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 20px;
    selection-background-color: #5865f2;
}

QComboBox:hover, QComboBox:focus {
    border: 1px solid #5865f2;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border-left: 1px solid #35373c;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
    background-color: #2b2d31;
}

QComboBox::drop-down:hover {
    background-color: #404249;
}

QComboBox::down-arrow {
    width: 0;
    height: 0;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #dbdee1;
    margin: auto;
}

QComboBox::down-arrow:hover {
    border-top: 6px solid #ffffff;
}

/* Dropdown Popup List */
QComboBox QAbstractItemView {
    background-color: #1e1f22;
    color: #dbdee1;
    border: 1px solid #35373c;
    border-radius: 6px;
    padding: 4px;
    selection-background-color: #5865f2;
    selection-color: #ffffff;
    outline: none;
}

QComboBox QAbstractItemView::item {
    min-height: 26px;
    padding: 4px 8px;
    border-radius: 4px;
}

QComboBox QAbstractItemView::item:hover {
    background-color: #2b2d31;
}

QComboBox QAbstractItemView::item:selected {
    background-color: #5865f2;
    color: #ffffff;
}

/* Labels */
QLabel {
    color: #dbdee1;
}

QLabel.muted {
    color: #949ba4;
    font-size: 12px;
}

QLabel.heading {
    font-size: 16px;
    font-weight: bold;
    color: #ffffff;
}

/* Scrollbars */
QScrollBar:vertical {
    background-color: #1e1f22;
    width: 10px;
    margin: 0;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #2b2d31;
    min-height: 24px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #4e5058;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Status Bar */
QStatusBar {
    background-color: #111214;
    color: #949ba4;
    border-top: 1px solid #2b2d31;
    padding: 4px;
}
"""
