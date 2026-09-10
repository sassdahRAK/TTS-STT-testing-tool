"""
Model Tester Tool - Main Application Entry Point
A PyQt6 desktop app for testing TTS, STT, and LLM API models.

Usage:
    python main.py

Requirements:
    pip install -r requirements.txt
    Copy .env.example to .env and fill in your API keys.
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QStatusBar, QMenuBar, QMenu, QMessageBox, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QAction, QFont

from config import load_config, ProviderStatus
from ui_components import MIN_WINDOW_W, MIN_WINDOW_H, IS_MAC
from api_tab import APITab
from tts_tab import TTSTab
from stt_tab import STTTab
from llm_tab import LLMTab
from comparison_tab import ComparisonTab


# ──────────────────────────────────────────────────────────────────────────────
# Modern SaaS Dashboard Global Stylesheet
# ──────────────────────────────────────────────────────────────────────────────
STYLESHEET = """
QMainWindow {
    background: #f1f5f9;
}

/* ── Base typography ─────────────────────────────────────────── */
QWidget {
    font-family: -apple-system, "SF Pro Text", "Helvetica Neue", "Segoe UI", system-ui, sans-serif;
    font-size: 13px;
    color: #1e293b;
}

/* ── ScrollArea (full-page scrolling) ───────────────────────── */
QScrollArea {
    border: none;
    background: transparent;
}
QScrollArea > QWidget > QWidget {
    background: #f1f5f9;
}

/* ── GroupBox → Card ─────────────────────────────────────────── */
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

/* ── Buttons ─────────────────────────────────────────────────── */
QPushButton {
    border-radius: 7px;
    padding: 8px 18px;
    font-weight: 600;
    font-size: 13px;
    border: 1px solid transparent;
    color: #334155;
    background: #f1f5f9;
}
QPushButton:hover {
    background: #e2e8f0;
}
QPushButton:pressed {
    background: #cbd5e1;
}
QPushButton:disabled {
    background: #f1f5f9;
    color: #94a3b8;
    border-color: #e2e8f0;
}

/* ── Tables ──────────────────────────────────────────────────── */
QTableWidget {
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    background: white;
    gridline-color: #f1f5f9;
    selection-background-color: rgba(99, 102, 241, 0.08);
    font-size: 13px;
    alternate-background-color: #f8fafc;
}
QTableWidget::item {
    padding: 8px 10px;
    border-bottom: 1px solid #f1f5f9;
}
QTableWidget::item:hover {
    background: rgba(99, 102, 241, 0.04);
}
QTableWidget::item:selected {
    background: rgba(99, 102, 241, 0.1);
    color: #1e293b;
}
QHeaderView::section {
    background: #f8fafc;
    border: none;
    border-bottom: 2px solid #e2e8f0;
    padding: 8px 10px;
    font-weight: 600;
    color: #64748b;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.4px;
}
QHeaderView::section:first {
    border-top-left-radius: 10px;
}

/* ── Text inputs ─────────────────────────────────────────────── */
QTextEdit, QPlainTextEdit {
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 10px;
    background: white;
    font-size: 13px;
    selection-background-color: rgba(99, 102, 241, 0.2);
}
QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #6366f1;
}

QLineEdit {
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 8px 12px;
    background: white;
    font-size: 13px;
    selection-background-color: rgba(99, 102, 241, 0.2);
}
QLineEdit:focus {
    border-color: #6366f1;
}

/* ── ComboBox ────────────────────────────────────────────────── */
QComboBox {
    border: 1px solid #e2e8f0;
    border-radius: 7px;
    padding: 6px 12px;
    background: white;
    min-height: 22px;
    font-size: 13px;
}
QComboBox:hover { border-color: #6366f1; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView {
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    background: white;
    padding: 4px;
    font-size: 13px;
    selection-background-color: rgba(99, 102, 241, 0.1);
    selection-color: #1e293b;
}

/* ── Progress bar ────────────────────────────────────────────── */
QProgressBar {
    border: none;
    border-radius: 5px;
    background: #e2e8f0;
    text-align: center;
    height: 18px;
    font-size: 11px;
    color: #64748b;
    font-weight: 600;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6366f1, stop:1 #8b5cf6);
    border-radius: 5px;
}

/* ── Top-level tab bar (API / TTS / STT / LLM / Compare) ─────── */
QMainWindow QTabWidget > QTabBar::tab,
QMainWindow QTabBar::tab {
    padding: 10px 20px;
    margin-right: 2px;
    border: none;
    border-bottom: 2px solid transparent;
    background: transparent;
    color: #64748b;
    font-size: 13px;
    font-weight: 500;
}
QMainWindow QTabWidget > QTabBar::tab:hover,
QMainWindow QTabBar::tab:hover {
    color: #6366f1;
    background: rgba(99, 102, 241, 0.05);
}
QMainWindow QTabWidget > QTabBar::tab:selected,
QMainWindow QTabBar::tab:selected {
    color: #6366f1;
    border-bottom: 2px solid #6366f1;
    font-weight: 600;
}

/* ── Inner tab bars (e.g. Mic / File, response tabs) ─────────── */
QTabWidget::pane {
    border: none;
    background: transparent;
}
QTabBar::tab {
    padding: 8px 16px;
    margin-right: 2px;
    border: none;
    border-bottom: 2px solid transparent;
    background: transparent;
    color: #64748b;
    font-size: 13px;
    font-weight: 500;
}
QTabBar::tab:hover {
    color: #6366f1;
    background: rgba(99, 102, 241, 0.05);
}
QTabBar::tab:selected {
    color: #6366f1;
    border-bottom: 2px solid #6366f1;
    font-weight: 600;
}

/* ── Scrollbars — thin macOS-style ──────────────────────────── */
QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 8px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: rgba(148, 163, 184, 0.6);
    border-radius: 4px;
    min-height: 32px;
}
QScrollBar::handle:vertical:hover { background: rgba(100, 116, 139, 0.8); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    border: none;
    background: transparent;
    height: 8px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: rgba(148, 163, 184, 0.6);
    border-radius: 4px;
    min-width: 32px;
}
QScrollBar::handle:horizontal:hover { background: rgba(100, 116, 139, 0.8); }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ── Status bar ──────────────────────────────────────────────── */
QStatusBar {
    background: #f8fafc;
    border-top: 1px solid #e2e8f0;
    color: #64748b;
    font-size: 12px;
    padding: 3px;
}

/* ── CheckBox ────────────────────────────────────────────────── */
QCheckBox {
    spacing: 6px;
    padding: 3px;
    font-size: 13px;
    color: #334155;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 2px solid #cbd5e1;
}
QCheckBox::indicator:hover { border-color: #6366f1; }
QCheckBox::indicator:checked {
    background: #6366f1;
    border-color: #6366f1;
}

/* ── SpinBox ─────────────────────────────────────────────────── */
QSpinBox, QDoubleSpinBox {
    border: 1px solid #e2e8f0;
    border-radius: 7px;
    padding: 5px 8px;
    background: white;
    font-size: 13px;
}
QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #6366f1;
}

/* ── Label ───────────────────────────────────────────────────── */
QLabel {
    color: #334155;
}

/* ── Menu bar ────────────────────────────────────────────────── */
QMenuBar {
    background: white;
    border-bottom: 1px solid #e2e8f0;
    color: #334155;
    padding: 2px;
    font-size: 13px;
}
QMenuBar::item:selected {
    background: rgba(99, 102, 241, 0.1);
    border-radius: 4px;
}
QMenu {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 4px;
    font-size: 13px;
}
QMenu::item {
    padding: 7px 20px;
    border-radius: 4px;
}
QMenu::item:selected {
    background: rgba(99, 102, 241, 0.1);
    color: #6366f1;
}
"""


class MainWindow(QMainWindow):
    """Main application window with tabbed interface."""

    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.provider_status = ProviderStatus.from_config(self.config)
        self.setWindowTitle("Model Tester Tool — TTS / STT / LLM Accuracy Testing")
        self.setMinimumSize(MIN_WINDOW_W, MIN_WINDOW_H)
        # Start at a comfortable default on macOS retina displays
        self.resize(1100, 760)
        self._setup_ui()
        self._setup_menu()
        self._check_providers()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header ───────────────────────────────────────────────
        header_widget = QWidget()
        header_widget.setMinimumHeight(56)
        header_widget.setMaximumHeight(72)
        header_widget.setStyleSheet("""
            QWidget {
                background: white;
                border-bottom: 1px solid #e2e8f0;
            }
        """)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(20, 0, 20, 0)
        header_layout.setSpacing(0)

        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        text_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        title = QLabel("Model Tester Tool")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #0f172a;")
        text_col.addWidget(title)

        subtitle = QLabel("Test and compare TTS, STT, and LLM models  ·  Powered by NVIDIA NeMo")
        subtitle.setStyleSheet("font-size: 12px; color: #94a3b8;")
        text_col.addWidget(subtitle)

        header_layout.addLayout(text_col)
        header_layout.addStretch()
        layout.addWidget(header_widget)

        # ── Tab widget ───────────────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: none; }
        """)

        self.api_tab = APITab()
        self.tts_tab = TTSTab()
        self.stt_tab = STTTab()
        self.llm_tab = LLMTab()
        self.comparison_tab = ComparisonTab()

        self.tabs.addTab(self.api_tab, "API")
        self.tabs.addTab(self.tts_tab, "TTS")
        self.tabs.addTab(self.stt_tab, "STT")
        self.tabs.addTab(self.llm_tab, "LLM API")
        self.tabs.addTab(self.comparison_tab, "Compare & Rank")

        self.stt_tab.results_ready.connect(self._on_stt_results_ready)
        self.stt_tab.batch_widget.results_ready.connect(self._on_stt_results_ready)

        layout.addWidget(self.tabs)

        # ── Status bar ───────────────────────────────────────────
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._update_status_bar()

    def _setup_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        export_action = QAction("Export Results", self)
        export_action.setShortcut("Ctrl+S")
        export_action.triggered.connect(lambda: self.comparison_tab._on_export_json())
        file_menu.addAction(export_action)
        file_menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        help_menu = menubar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
        setup_action = QAction("Setup Guide", self)
        setup_action.triggered.connect(self._show_setup_guide)
        help_menu.addAction(setup_action)

    def _check_providers(self):
        available = []
        if self.provider_status.openai: available.append("OpenAI")
        if self.provider_status.google: available.append("Google Cloud")
        if self.provider_status.azure: available.append("Azure")
        if self.provider_status.anthropic: available.append("Anthropic")
        if self.provider_status.custom: available.append("Custom API")
        if not available:
            QTimer.singleShot(500, self._show_setup_guide)

    def _update_status_bar(self):
        parts = []
        if self.provider_status.openai: parts.append("OpenAI")
        if self.provider_status.google: parts.append("Google")
        if self.provider_status.azure: parts.append("Azure")
        if self.provider_status.anthropic: parts.append("Anthropic")
        if self.provider_status.custom: parts.append("Custom")
        parts.append("Local (always)")
        custom_count = len(self.api_tab.dynamic_manager.get_all())
        if custom_count > 0:
            parts.append(f"{custom_count} custom")
        self.status_bar.showMessage(f"Configured providers: {', '.join(parts)}")

    def _on_stt_results_ready(self, *args):
        if len(args) == 2:
            results, reference = args
            for key, r in results.items():
                provider = r.get("provider_name", key)
                model = "STT"
                self.comparison_tab.add_stt_scored_result(
                    provider=provider, model=model, reference=reference,
                    hypothesis=r.get("text", ""), success=r.get("success", False),
                    duration_ms=r.get("duration_ms", 0),
                )
        elif len(args) == 6:
            provider, model, reference, hypothesis, success, duration = args
            self.comparison_tab.add_stt_scored_result(
                provider=provider, model=model, reference=reference,
                hypothesis=hypothesis, success=success, duration_ms=duration,
            )

    def _show_about(self):
        QMessageBox.about(
            self, "About Model Tester Tool",
            "<h3>Model Tester Tool</h3>"
            "<p>Version 1.0</p>"
            "<p>A desktop tool for testing and comparing TTS, STT, and LLM API models.</p>"
            "<p>Built with Python + PyQt6</p>"
        )

    def _show_setup_guide(self):
        QMessageBox.information(
            self, "Setup Guide",
            "<h3>Getting Started</h3>"
            "<ol>"
            "<li>Go to the <b>API</b> tab to add your custom providers</li>"
            "<li>Or copy <code>.env.example</code> to <code>.env</code> for built-in providers</li>"
            "<li>Install required packages: <code>pip install -r requirements.txt</code></li>"
            "<li>Go to TTS, STT, or LLM API tab to test</li>"
            "</ol>"
            "<h4>Two Ways to Add Providers:</h4>"
            "<ul>"
            "<li><b>API Tab:</b> Click '+ Add New Provider' for any custom endpoint</li>"
            "<li><b>.env File:</b> Built-in providers (OpenAI, Google, Azure, Anthropic)</li>"
            "</ul>"
        )


def main():
    app = QApplication(sys.argv)
    # Use the native macOS style for proper system integration, then layer our QSS on top
    if IS_MAC:
        app.setStyle("macOS")
    else:
        app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
