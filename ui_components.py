"""
Shared UI components for Model Tester Tool.
Import from here to avoid duplicating Card and helpers across tab files.
"""

import sys
from PyQt6.QtWidgets import QGroupBox, QWidget, QVBoxLayout, QLabel, QScrollArea
from PyQt6.QtCore import Qt


# ──────────────────────────────────────────────────────────────────────────────
# Platform helpers
# ──────────────────────────────────────────────────────────────────────────────
IS_MAC = sys.platform == "darwin"

# Content margins that adapt to window width.
# On macOS the window can be as narrow as ~900px; use tighter margins.
CONTENT_MARGINS = (24, 20, 24, 32) if IS_MAC else (32, 28, 32, 40)
CARD_MARGINS    = (16, 12, 16, 16) if IS_MAC else (20, 16, 20, 20)
CONTENT_SPACING = 16 if IS_MAC else 20

# Minimum sizes chosen to work on 13" MacBook screens (2560×1600 @2x → ~1280 logical px)
MIN_WINDOW_W = 960
MIN_WINDOW_H = 660


# ──────────────────────────────────────────────────────────────────────────────
# Card – shared styled GroupBox used on every tab
# ──────────────────────────────────────────────────────────────────────────────
class Card(QGroupBox):
    """Modern dashboard card — shared across all tabs."""

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setTitle(title)
        self.setStyleSheet("""
            QGroupBox {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                margin-top: 12px;
                padding-top: 22px;
                font-weight: 600;
                font-size: 14px;
                color: #0f172a;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
                color: #0f172a;
            }
        """)


# ──────────────────────────────────────────────────────────────────────────────
# ScrollPage – scroll-area wrapper used by every tab
# ──────────────────────────────────────────────────────────────────────────────
class ScrollPage(QWidget):
    """
    Wraps a QScrollArea + content widget so each tab gets a consistent
    scrollable page with responsive margins.

    Usage:
        page = ScrollPage()
        page.layout.addWidget(some_card)
        main_layout.addWidget(page)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: #f1f5f9; }")

        self._content = QWidget()
        self._content.setStyleSheet("background: #f1f5f9;")
        l, t, r, b = CONTENT_MARGINS
        self.layout = QVBoxLayout(self._content)
        self.layout.setContentsMargins(l, t, r, b)
        self.layout.setSpacing(CONTENT_SPACING)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(self._content)
        outer.addWidget(scroll)
