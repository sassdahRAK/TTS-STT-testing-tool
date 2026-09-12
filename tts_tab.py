"""
TTS Testing Tab - Test Text-to-Speech with test case management.
Modern dashboard layout with full-page scrolling.
"""

import os
import json
import csv
import io
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QComboBox,
    QPushButton, QLabel, QGroupBox, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QCheckBox, QTabWidget, QLineEdit, QFrame, QSpinBox,
    QFileDialog, QInputDialog, QScrollArea, QSizePolicy,
    QDialog, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from config import load_config, TTS_VOICES
from tts_providers import TTSProviderManager
from dynamic_providers import DynamicProviderManager, DynamicTTSCaller
from edge_tts_provider import EdgeTTSProvider, EDGE_VOICES
from add_provider_dialog import AddProviderDialog, ManageProvidersDialog
from ui_components import Card, CONTENT_MARGINS, CARD_MARGINS, CONTENT_SPACING


TEST_CASES_FILE = Path(__file__).parent / "tts_test_cases.json"


# ──────────────────────────────────────────────────────────────────────────────
# Data Models
# ──────────────────────────────────────────────────────────────────────────────
class TestCase:
    """A single TTS test case."""

    def __init__(self, name: str, text: str, case_id: str = None):
        self.id = case_id or f"tc_{id(self)}"
        self.name = name
        self.text = text

    def to_dict(self):
        return {"id": self.id, "name": self.name, "text": self.text}

    @classmethod
    def from_dict(cls, data):
        return cls(data["name"], data["text"], data["id"])


class TestCaseManager:
    """Manages TTS test cases with persistence."""

    def __init__(self):
        self.test_cases: list[TestCase] = []
        self._load()

    def _load(self):
        if TEST_CASES_FILE.exists():
            try:
                with open(TEST_CASES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.test_cases = [TestCase.from_dict(tc) for tc in data]
            except (json.JSONDecodeError, KeyError):
                self.test_cases = []

    def _save(self):
        data = [tc.to_dict() for tc in self.test_cases]
        with open(TEST_CASES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add(self, test_case: TestCase):
        self.test_cases.append(test_case)
        self._save()

    def remove(self, case_id: str):
        self.test_cases = [tc for tc in self.test_cases if tc.id != case_id]
        self._save()

    def update(self, case_id: str, name: str = None, text: str = None):
        for tc in self.test_cases:
            if tc.id == case_id:
                if name is not None:
                    tc.name = name
                if text is not None:
                    tc.text = text
        self._save()

    def get_all(self) -> list[TestCase]:
        return self.test_cases


class TTSWorker(QThread):
    """Background worker for TTS synthesis."""
    finished = pyqtSignal(dict)
    progress = pyqtSignal(str, str)

    def __init__(self, builtin_manager, dynamic_manager, edge_tts,
                 test_case, voice, edge_voice, output_dir, providers, dynamic_providers, use_edge):
        super().__init__()
        self.builtin_manager = builtin_manager
        self.dynamic_manager = dynamic_manager
        self.edge_tts = edge_tts
        self.test_case = test_case
        self.voice = voice
        self.edge_voice = edge_voice
        self.output_dir = output_dir
        self.providers = providers
        self.dynamic_providers = dynamic_providers
        self.use_edge = use_edge

    def run(self):
        results = {}
        text = self.test_case.text

        for name in self.providers:
            self.progress.emit(f"{self.test_case.name} | {name}", "Synthesizing...")
            path = os.path.join(self.output_dir, f"tts_{name}_{self.test_case.id}.wav")
            result = self.builtin_manager.synthesize(name, text, self.voice, path)
            if result["success"]:
                result["output_path"] = path
            results[name] = result
            status = "Done" if result["success"] else "Failed"
            self.progress.emit(f"{self.test_case.name} | {name}", status)

        if self.use_edge:
            self.progress.emit(f"{self.test_case.name} | Edge TTS", "Synthesizing...")
            path = os.path.join(self.output_dir, f"tts_edge_{self.test_case.id}.wav")
            result = self.edge_tts.synthesize(text, self.edge_voice, path)
            results["edge"] = result
            if result["success"]:
                results["edge"]["output_path"] = path
            status = "Done" if result["success"] else "Failed"
            self.progress.emit(f"{self.test_case.name} | Edge TTS", status)

        for provider in self.dynamic_providers:
            label = f"custom_{provider.id}"
            self.progress.emit(f"{self.test_case.name} | {provider.name}", "Synthesizing...")
            path = os.path.join(self.output_dir, f"tts_custom_{provider.id}_{self.test_case.id}.wav")
            result = DynamicTTSCaller.synthesize(provider, text, self.voice, path)
            results[label] = result
            if result["success"]:
                results[label]["output_path"] = path
                results[label]["provider_name"] = provider.name
            status = "Done" if result["success"] else "Failed"
            self.progress.emit(f"{self.test_case.name} | {provider.name}", status)

        self.finished.emit(results)


class TestCaseWidget(QWidget):
    """Widget for a single test case."""

    text_changed = pyqtSignal(str, str)

    def __init__(self, test_case: TestCase, parent=None):
        super().__init__(parent)
        self.test_case = test_case
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        header = QHBoxLayout()

        self.name_label = QLabel(f"<b>{self.test_case.name}</b>")
        self.name_label.setStyleSheet("font-size: 15px; color: #0f172a;")
        header.addWidget(self.name_label)

        header.addStretch()

        rename_btn = QPushButton("Rename")
        rename_btn.setStyleSheet("QPushButton { padding: 4px 12px; font-size: 12px; }")
        rename_btn.clicked.connect(self._on_rename)
        header.addWidget(rename_btn)

        upload_btn = QPushButton("Upload")
        upload_btn.setStyleSheet("QPushButton { padding: 4px 12px; font-size: 12px; background: #eef2ff; color: #4f46e5; }")
        upload_btn.clicked.connect(self._on_upload)
        header.addWidget(upload_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet("QPushButton { padding: 4px 12px; font-size: 12px; }")
        clear_btn.clicked.connect(self._on_clear)
        header.addWidget(clear_btn)

        delete_btn = QPushButton("Delete")
        delete_btn.setStyleSheet("QPushButton { padding: 4px 12px; font-size: 12px; background: #fef2f2; color: #dc2626; }")
        delete_btn.clicked.connect(self._on_delete)
        header.addWidget(delete_btn)

        layout.addLayout(header)

        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(self.test_case.text)
        self.text_edit.setPlaceholderText("Enter text to synthesize...")
        self.text_edit.setMaximumHeight(80)
        self.text_edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.text_edit)

        self.char_count = QLabel(f"{len(self.test_case.text)} characters")
        self.char_count.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(self.char_count)

        self.setStyleSheet("""
            TestCaseWidget {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
            }
        """)

    def _on_text_changed(self):
        text = self.text_edit.toPlainText()
        self.test_case.text = text
        self.char_count.setText(f"{len(text)} characters")
        self.text_changed.emit(self.test_case.id, text)

    def _on_rename(self):
        name, ok = QInputDialog.getText(self, "Rename Test Case", "New name:", text=self.test_case.name)
        if ok and name.strip():
            self.test_case.name = name.strip()
            self.name_label.setText(f"<b>{self.test_case.name}</b>")

    def _on_upload(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Upload Text File", "",
            "Text Files (*.txt *.md *.csv);;All Files (*)"
        )
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    text = f.read()
                self.text_edit.setPlainText(text)
                if self.test_case.name.startswith("Test Case"):
                    name = Path(path).stem
                    self.test_case.name = name
                    self.name_label.setText(f"<b>{name}</b>")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not read file: {e}")

    def _on_clear(self):
        self.text_edit.clear()

    def _on_delete(self):
        self.parent()._delete_test_case(self.test_case.id)

    def get_text(self) -> str:
        return self.text_edit.toPlainText().strip()


class CSVPreviewDialog(QDialog):
    """Dialog to preview TSV/CSV data and select which rows to import."""

    def __init__(self, rows: list, parent=None):
        super().__init__(parent)
        self.rows = rows
        self.selected_rows = []
        self.setWindowTitle("TSV Preview - Select Test Cases")
        self.setMinimumSize(700, 500)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel("TSV/CSV Preview")
        header.setStyleSheet("font-size: 18px; font-weight: 700; color: #0f172a;")
        layout.addWidget(header)

        col_row = QHBoxLayout()
        col_row.addWidget(QLabel("ID Column:"))
        self.id_col_combo = QComboBox()
        self.id_col_combo.setMinimumWidth(150)
        col_row.addWidget(self.id_col_combo)

        col_row.addWidget(QLabel("Text Column:"))
        self.text_col_combo = QComboBox()
        self.text_col_combo.setMinimumWidth(150)
        col_row.addWidget(self.text_col_combo)

        col_row.addStretch()

        self.has_header_check = QCheckBox("First row is header")
        self.has_header_check.setChecked(False)
        self.has_header_check.toggled.connect(self._on_header_toggled)
        col_row.addWidget(self.has_header_check)

        layout.addLayout(col_row)

        select_row = QHBoxLayout()
        select_row.addStretch()

        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self._select_all)
        select_row.addWidget(self.select_all_btn)

        self.select_none_btn = QPushButton("Select None")
        self.select_none_btn.clicked.connect(self._select_none)
        select_row.addWidget(self.select_none_btn)

        layout.addLayout(select_row)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Select", "ID", "Text"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        self._update_column_combos()

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        self.import_btn = QPushButton("Import Selected")
        self.import_btn.setStyleSheet("""
            QPushButton {
                background-color: #6366f1;
                color: white;
                padding: 10px 28px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #4f46e5; }
        """)
        self.import_btn.clicked.connect(self._on_import)
        btn_row.addWidget(self.import_btn)

        layout.addLayout(btn_row)

        self._load_preview()

        self.id_col_combo.currentIndexChanged.connect(self._load_preview)
        self.text_col_combo.currentIndexChanged.connect(self._load_preview)

    def _on_header_toggled(self, checked):
        self._update_column_combos()
        self._load_preview()

    def _update_column_combos(self):
        self.id_col_combo.clear()
        self.text_col_combo.clear()

        if not self.rows:
            return

        has_header = self.has_header_check.isChecked()

        if has_header and len(self.rows) > 1:
            headers = self.rows[0]
            for i, header in enumerate(headers):
                self.id_col_combo.addItem(f"Col {i}: {header}", i)
                self.text_col_combo.addItem(f"Col {i}: {header}", i)
        else:
            num_cols = len(self.rows[0]) if self.rows else 2
            for i in range(num_cols):
                self.id_col_combo.addItem(f"Column {i}", i)
                self.text_col_combo.addItem(f"Column {i}", i)

        if self.id_col_combo.count() >= 2:
            self.id_col_combo.setCurrentIndex(0)
            self.text_col_combo.setCurrentIndex(1)
        elif self.id_col_combo.count() == 1:
            self.id_col_combo.setCurrentIndex(0)
            self.text_col_combo.setCurrentIndex(0)

    def _load_preview(self):
        self.table.setRowCount(0)
        id_col = self.id_col_combo.currentData() or 0
        text_col = self.text_col_combo.currentData() or 1

        has_header = self.has_header_check.isChecked()

        if has_header and len(self.rows) > 1:
            preview_rows = self.rows[1:101]
        else:
            preview_rows = self.rows[:100]

        for row in preview_rows:
            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)

            cb = QCheckBox()
            cb.setChecked(True)
            self.table.setCellWidget(row_idx, 0, cb)

            row_id = row[id_col] if id_col < len(row) else ""
            self.table.setItem(row_idx, 1, QTableWidgetItem(row_id))

            text = row[text_col] if text_col < len(row) else ""
            self.table.setItem(row_idx, 2, QTableWidgetItem(text))

        total = len(preview_rows)
        self.import_btn.setText(f"Import Selected ({total})")

    def _select_all(self):
        for row in range(self.table.rowCount()):
            cb = self.table.cellWidget(row, 0)
            if cb:
                cb.setChecked(True)

    def _select_none(self):
        for row in range(self.table.rowCount()):
            cb = self.table.cellWidget(row, 0)
            if cb:
                cb.setChecked(False)

    def get_selected_rows(self) -> list:
        return self.selected_rows

    def get_text_column(self) -> int:
        return self.text_col_combo.currentData() or 1

    def get_id_column(self) -> int:
        return self.id_col_combo.currentData() or 0

    def _on_import(self):
        has_header = self.has_header_check.isChecked()

        self.selected_rows = []
        for row in range(self.table.rowCount()):
            cb = self.table.cellWidget(row, 0)
            if cb and cb.isChecked():
                if has_header:
                    actual_row = self.rows[row + 1]
                else:
                    actual_row = self.rows[row]
                self.selected_rows.append(actual_row)

        if not self.selected_rows:
            QMessageBox.information(self, "No Selection", "Please select at least one row.")
            return

        self.accept()


# ──────────────────────────────────────────────────────────────────────────────
# Main TTS Tab — Full Page Scroll
# ──────────────────────────────────────────────────────────────────────────────
class TTSTab(QWidget):
    """Tab for testing Text-to-Speech — full page scroll."""

    # Emitted per provider result: (provider, voice, success, duration_ms)
    result_ready = pyqtSignal(str, str, bool, float)

    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.builtin_manager = TTSProviderManager(self.config)
        self.dynamic_manager = DynamicProviderManager()
        self.edge_tts = EdgeTTSProvider(self.config)
        self.test_case_manager = TestCaseManager()
        self.current_results = {}
        self._workers = []  # keep references so threads aren't GC'd while running
        self.player = None
        self.audio_output = None
        self.test_case_widgets = {}
        self._setup_ui()
        self._refresh_providers()
        self._load_test_cases()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: #f1f5f9; }")

        content = QWidget()
        content.setStyleSheet("background: #f1f5f9;")
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(32, 28, 32, 40)
        self.content_layout.setSpacing(20)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ── Card 1: Select Providers ─────────────────────────────
        provider_card = Card("1. Select Providers")
        provider_layout = QVBoxLayout(provider_card)
        provider_layout.setContentsMargins(20, 16, 20, 20)
        provider_layout.setSpacing(12)

        builtin_row = QHBoxLayout()
        builtin_row.addWidget(QLabel("Built-in:"))
        self.builtin_checks = {}
        for key, label in [
            ("openai",  "OpenAI"),
            ("google",  "Google"),
            ("azure",   "Azure"),
            ("local",   "Local pyttsx3"),
            ("mms_tts", "Meta MMS TTS"),
        ]:
            cb = QCheckBox(label)
            cb.setProperty("provider_key", key)
            self.builtin_checks[key] = cb
            builtin_row.addWidget(cb)
        builtin_row.addStretch()
        provider_layout.addLayout(builtin_row)

        edge_row = QHBoxLayout()
        edge_row.addWidget(QLabel("Free:"))
        self.edge_check = QCheckBox("Edge TTS (Microsoft — No Key Needed!)")
        self.edge_check.setStyleSheet("color: #059669; font-weight: 600;")
        self.edge_check.toggled.connect(self._on_edge_toggled)
        edge_row.addWidget(self.edge_check)
        edge_row.addStretch()
        provider_layout.addLayout(edge_row)

        self.dynamic_row = QHBoxLayout()
        self.dynamic_row.addWidget(QLabel("Custom:"))
        self.dynamic_checks = {}
        self.dynamic_row.addStretch()
        provider_layout.addLayout(self.dynamic_row)

        add_row = QHBoxLayout()
        self.add_provider_btn = QPushButton("+ Add Custom Provider")
        self.add_provider_btn.setStyleSheet("QPushButton { background-color: #6366f1; color: white; padding: 8px 20px; }")
        self.add_provider_btn.clicked.connect(self._on_add_provider)
        add_row.addWidget(self.add_provider_btn)

        self.manage_provider_btn = QPushButton("Manage Providers")
        self.manage_provider_btn.setStyleSheet("QPushButton { background-color: #f59e0b; color: white; padding: 8px 20px; }")
        self.manage_provider_btn.clicked.connect(self._on_manage_providers)
        add_row.addWidget(self.manage_provider_btn)

        add_row.addStretch()

        add_row.addWidget(QLabel("Voice:"))
        self.voice_combo = QComboBox()
        self.voice_combo.setMinimumWidth(250)
        add_row.addWidget(self.voice_combo)

        provider_layout.addLayout(add_row)
        self.content_layout.addWidget(provider_card)

        # ── Card 2: Create Test Cases ────────────────────────────
        testcase_card = Card("2. Create Test Cases")
        testcase_layout = QVBoxLayout(testcase_card)
        testcase_layout.setContentsMargins(20, 16, 20, 20)
        testcase_layout.setSpacing(12)

        add_tc_row = QHBoxLayout()
        self.add_tc_btn = QPushButton("+ Add Test Case")
        self.add_tc_btn.setStyleSheet("""
            QPushButton {
                background-color: #6366f1;
                color: white;
                padding: 10px 24px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #4f46e5; }
        """)
        self.add_tc_btn.clicked.connect(self._on_add_test_case)
        add_tc_row.addWidget(self.add_tc_btn)

        self.add_preset_btn = QPushButton("+ Load Presets")
        self.add_preset_btn.setStyleSheet("QPushButton { padding: 8px 18px; background: #ecfdf5; color: #059669; }")
        self.add_preset_btn.clicked.connect(self._on_load_presets)
        add_tc_row.addWidget(self.add_preset_btn)

        self.upload_csv_btn = QPushButton("+ Upload TSV Dataset")
        self.upload_csv_btn.setStyleSheet("QPushButton { padding: 8px 18px; background: #fff7ed; border: 1px solid #fb923c; }")
        self.upload_csv_btn.clicked.connect(self._on_upload_csv)
        add_tc_row.addWidget(self.upload_csv_btn)

        add_tc_row.addStretch()
        testcase_layout.addLayout(add_tc_row)

        tc_scroll = QScrollArea()
        tc_scroll.setWidgetResizable(True)
        tc_scroll.setMinimumHeight(200)
        tc_scroll.setMaximumHeight(350)
        tc_scroll.setStyleSheet("QScrollArea { border: 1px solid #e2e8f0; border-radius: 8px; background: white; }")

        self.tc_container = QWidget()
        self.tc_layout = QVBoxLayout(self.tc_container)
        self.tc_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.tc_layout.setSpacing(8)
        tc_scroll.setWidget(self.tc_container)

        testcase_layout.addWidget(tc_scroll)
        self.content_layout.addWidget(testcase_card)

        # ── Card 3: Run ──────────────────────────────────────────
        run_card = Card("3. Run Test Cases")
        run_layout = QHBoxLayout(run_card)
        run_layout.setContentsMargins(20, 16, 20, 20)

        self.run_all_btn = QPushButton("▶  Run All Test Cases")
        self.run_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #6366f1;
                color: white;
                padding: 14px 32px;
                font-weight: 600;
                font-size: 15px;
            }
            QPushButton:hover { background-color: #4f46e5; }
            QPushButton:disabled { background-color: #94a3b8; }
        """)
        self.run_all_btn.clicked.connect(self._on_run_all)
        run_layout.addWidget(self.run_all_btn)

        self.run_selected_btn = QPushButton("Run Selected Only")
        self.run_selected_btn.setStyleSheet("QPushButton { padding: 12px 24px; }")
        self.run_selected_btn.clicked.connect(self._on_run_selected)
        run_layout.addWidget(self.run_selected_btn)

        run_layout.addStretch()
        self.content_layout.addWidget(run_card)

        # ── Card 4: Results ──────────────────────────────────────
        results_card = Card("4. Results — Listen & Compare")
        results_layout = QVBoxLayout(results_card)
        results_layout.setContentsMargins(20, 16, 20, 20)
        results_layout.setSpacing(10)

        self.results_table = QTableWidget(0, 6)
        self.results_table.setHorizontalHeaderLabels([
            "Test Case", "Provider", "Status", "Duration (ms)", "Output File", "Play"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setMinimumHeight(200)
        results_layout.addWidget(self.results_table)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        results_layout.addWidget(self.progress_bar)

        self.content_layout.addWidget(results_card)

        self.content_layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _refresh_providers(self):
        available = self.builtin_manager.get_available_providers()
        for key, cb in self.builtin_checks.items():
            cb.setChecked(key in available)
            cb.setEnabled(key in available)
            if key not in available:
                cb.setText(cb.text() + " (not configured)")

        if self.edge_tts.is_available():
            self.edge_check.setEnabled(True)
            self.edge_check.setChecked(True)
        else:
            self.edge_check.setEnabled(False)
            self.edge_check.setText("Edge TTS (install: pip install edge-tts)")

        for cb in self.dynamic_checks.values():
            cb.deleteLater()
        self.dynamic_checks.clear()

        for provider in self.dynamic_manager.get_by_type("tts"):
            cb = QCheckBox(provider.name)
            cb.setProperty("provider_id", provider.id)
            cb.setChecked(True)
            self.dynamic_checks[provider.id] = cb
            self.dynamic_row.addWidget(cb)

        self._update_voices()

    def _on_edge_toggled(self, checked):
        if checked:
            self._update_voices_edge()
        else:
            self._update_voices()

    def _update_voices_edge(self):
        self.voice_combo.clear()
        for voice_id, description in EDGE_VOICES.items():
            self.voice_combo.addItem(description, voice_id)

    def _update_voices(self):
        self.voice_combo.clear()
        for key, cb in self.builtin_checks.items():
            if cb.isChecked():
                voices = TTS_VOICES.get(key, ["default"])
                for v in voices:
                    self.voice_combo.addItem(v)
                break
        if self.voice_combo.count() == 0:
            self.voice_combo.addItem("en-US-AriaNeural")

    def _load_test_cases(self):
        for tc in self.test_case_manager.get_all():
            self._create_test_case_widget(tc)

        if not self.test_case_manager.get_all():
            self._add_default_test_cases()

    def _add_default_test_cases(self):
        defaults = [
            TestCase("Basic English", "Hello! This is a test of text to speech. How does it sound?"),
            TestCase("Pronunciation", "The quick brown fox jumps over the lazy dog. She sells seashells by the seashore."),
            TestCase("Numbers", "Call us at 1-800-555-0199. The price is $49.99 for 3 items."),
        ]
        for tc in defaults:
            self.test_case_manager.add(tc)
            self._create_test_case_widget(tc)

    def _create_test_case_widget(self, test_case: TestCase):
        widget = TestCaseWidget(test_case)
        widget.text_changed.connect(self._on_test_case_text_changed)
        self.test_case_widgets[test_case.id] = widget
        self.tc_layout.addWidget(widget)

    def _on_add_test_case(self):
        count = len(self.test_case_manager.get_all()) + 1
        tc = TestCase(f"Test Case {count}", "")
        self.test_case_manager.add(tc)
        self._create_test_case_widget(tc)

    def _on_load_presets(self):
        presets = [
            TestCase("Greeting", "Good morning! Welcome to our service. How can I help you today?"),
            TestCase("Weather", "Today's weather is sunny with a high of 75 degrees Fahrenheit. Perfect day for outdoor activities!"),
            TestCase("Navigation", "In 500 feet, turn right onto Main Street. Your destination will be on the left."),
            TestCase("News", "Breaking news: Scientists have discovered a new species of deep-sea fish in the Pacific Ocean."),
            TestCase("Technical", "The API endpoint returns a JSON response with status code 200. Check the documentation for query parameters."),
            TestCase("Emotion", "Wow! That's absolutely amazing! I can't believe how incredible this is!"),
            TestCase("Questions", "What time does the store close? Could you tell me where the nearest hospital is?"),
            TestCase("Khmer", "សួស្តី! ខ្ញុំសង្ឃឹមថាអ្នកសុខសប្បាយ។"),
        ]

        dialog = QDialog(self)
        dialog.setWindowTitle("Load Preset Test Cases")
        dialog.setMinimumSize(400, 300)
        dlg_layout = QVBoxLayout(dialog)

        dlg_layout.addWidget(QLabel("Select presets to add:"))

        list_widget = QListWidget()
        for preset in presets:
            item = QListWidgetItem(f"{preset.name}\n    {preset.text[:60]}...")
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, preset)
            list_widget.addItem(item)
        dlg_layout.addWidget(list_widget)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        btn_row.addWidget(cancel_btn)
        add_btn = QPushButton("Add Selected")
        add_btn.setStyleSheet("QPushButton { background: #6366f1; color: white; padding: 8px 20px; }")
        btn_row.addWidget(add_btn)
        dlg_layout.addLayout(btn_row)

        def on_add():
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                if item.checkState() == Qt.CheckState.Checked:
                    preset = item.data(Qt.ItemDataRole.UserRole)
                    self.test_case_manager.add(preset)
                    self._create_test_case_widget(preset)
            dialog.accept()

        add_btn.clicked.connect(on_add)
        dialog.exec()

    def _on_upload_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Upload TSV Dataset", "",
            "TSV Files (*.tsv);;CSV Files (*.csv);;Text Files (*.txt);;All Files (*)"
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            if path.endswith('.tsv') or path.endswith('.txt'):
                delimiter = "\t"
            else:
                sniffer = csv.Sniffer()
                try:
                    dialect = sniffer.sniff(content[:1024])
                    delimiter = dialect.delimiter
                except:
                    delimiter = ","

            reader = csv.reader(io.StringIO(content), delimiter=delimiter)
            rows = list(reader)

            rows = [row for row in rows if any(cell.strip() for cell in row)]

            if not rows:
                QMessageBox.warning(self, "Empty File", "The file is empty or could not be parsed.")
                return

            dialog = CSVPreviewDialog(rows, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                selected_rows = dialog.get_selected_rows()
                text_col = dialog.get_text_column()
                id_col = dialog.get_id_column()

                created = 0
                errors = []
                for i, row in enumerate(selected_rows):
                    try:
                        if len(row) > max(text_col, id_col):
                            text = row[text_col].strip()
                            row_id = row[id_col].strip() if id_col < len(row) else ""
                            if text:
                                name = row_id if row_id else f"Test Case {created + 1}"
                                tc = TestCase(name, text)
                                self.test_case_manager.add(tc)
                                self._create_test_case_widget(tc)
                                created += 1
                            else:
                                errors.append(f"Row {i+1}: Empty text")
                        else:
                            errors.append(f"Row {i+1}: Not enough columns (has {len(row)}, need {max(text_col, id_col)+1})")
                    except Exception as e:
                        errors.append(f"Row {i+1}: {str(e)}")

                msg = f"Created {created} test cases from {len(selected_rows)} selected rows."
                if errors:
                    msg += f"\n\n{len(errors)} errors:\n" + "\n".join(errors[:10])
                QMessageBox.information(self, "TSV Uploaded", msg)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not read file:\n{e}")

    def _on_test_case_text_changed(self, case_id, text):
        self.test_case_manager.update(case_id, text=text)

    def _delete_test_case(self, case_id: str):
        if case_id in self.test_case_widgets:
            widget = self.test_case_widgets.pop(case_id)
            widget.deleteLater()
        self.test_case_manager.remove(case_id)

    def _get_selected_builtin(self) -> list:
        return [key for key, cb in self.builtin_checks.items() if cb.isChecked()]

    def _get_selected_dynamic(self) -> list:
        return [p for p in self.dynamic_manager.get_by_type("tts")
                if p.id in self.dynamic_checks and self.dynamic_checks[p.id].isChecked()]

    def _on_add_provider(self):
        dialog = AddProviderDialog(self.dynamic_manager, self)
        dialog.provider_added.connect(lambda _: self._refresh_providers())
        dialog.exec()

    def _on_manage_providers(self):
        dialog = ManageProvidersDialog(self.dynamic_manager, self)
        dialog.finished.connect(self._refresh_providers)
        dialog.exec()

    def _on_run_all(self):
        test_cases = self.test_case_manager.get_all()
        if not test_cases:
            QMessageBox.warning(self, "No Test Cases", "Add at least one test case first.")
            return
        self._run_test_cases(test_cases)

    def _on_run_selected(self):
        test_cases = [tc for tc in self.test_case_manager.get_all() if tc.text.strip()]
        if not test_cases:
            QMessageBox.warning(self, "No Text", "Add text to at least one test case.")
            return
        self._run_test_cases(test_cases)

    def _run_test_cases(self, test_cases: list):
        builtin = self._get_selected_builtin()
        dynamic = self._get_selected_dynamic()
        use_edge = self.edge_check.isChecked()

        if not builtin and not dynamic and not use_edge:
            QMessageBox.warning(self, "Provider Required", "Select at least one provider.")
            return

        voice = self.voice_combo.currentData() or self.voice_combo.currentText() or "en-US-AriaNeural"

        # If edge is checked but the selected voice isn't a valid Edge voice,
        # use a safe default Edge voice so it doesn't receive "alloy" etc.
        edge_voice = voice
        valid_edge = any(voice == vid or voice == desc
                         for vid, desc in EDGE_VOICES.items())
        if use_edge and not valid_edge:
            edge_voice = "en-US-AriaNeural"  # safe fallback
        self.current_results.clear()

        self.run_all_btn.setEnabled(False)
        self.results_table.setRowCount(0)
        self.progress_bar.setVisible(True)
        total = len(test_cases) * (len(builtin) + len(dynamic) + (1 if use_edge else 0))
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(0)

        self._pending_test_cases = test_cases
        self._current_tc_index = 0
        self._run_single_test_case(voice, edge_voice, builtin, dynamic, use_edge)

    def _run_single_test_case(self, voice, edge_voice, builtin, dynamic, use_edge):
        if self._current_tc_index >= len(self._pending_test_cases):
            self.run_all_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            self._workers.clear()  # all done — release all thread references
            return

        tc = self._pending_test_cases[self._current_tc_index]
        if not tc.text.strip():
            self._current_tc_index += 1
            self._run_single_test_case(voice, edge_voice, builtin, dynamic, use_edge)
            return

        self.worker = TTSWorker(
            self.builtin_manager, self.dynamic_manager, self.edge_tts,
            tc, voice, edge_voice, self.config.output_dir, builtin, dynamic, use_edge
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(lambda results: self._on_single_finished(results, tc, voice, edge_voice, builtin, dynamic, use_edge))
        self._workers.append(self.worker)
        self.worker.start()

    def _on_progress(self, provider: str, status: str):
        self.progress_bar.setValue(self.progress_bar.value() + 1)
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        parts = provider.split(" | ")
        if len(parts) == 2:
            self.results_table.setItem(row, 0, QTableWidgetItem(parts[0]))
            self.results_table.setItem(row, 1, QTableWidgetItem(parts[1]))
        else:
            self.results_table.setItem(row, 0, QTableWidgetItem(""))
            self.results_table.setItem(row, 1, QTableWidgetItem(provider))
        self.results_table.setItem(row, 2, QTableWidgetItem(status))
        self.results_table.setItem(row, 3, QTableWidgetItem("-"))
        self.results_table.setItem(row, 4, QTableWidgetItem("-"))

    def _on_single_finished(self, results, tc, voice, edge_voice, builtin, dynamic, use_edge):
        self.current_results[tc.id] = results

        for row in range(self.results_table.rowCount()):
            tc_item = self.results_table.item(row, 0)
            prov_item = self.results_table.item(row, 1)
            if tc_item and prov_item:
                if tc_item.text() == tc.name:
                    for key, r in results.items():
                        prov_name = r.get("provider_name", key).capitalize()
                        if prov_item.text().lower() == prov_name.lower() or prov_item.text().lower() == key.lower():
                            if r["success"]:
                                self.results_table.item(row, 2).setText("Success")
                                self.results_table.setItem(row, 3, QTableWidgetItem(f"{r['duration_ms']:.0f}"))
                                path = r.get("output_path", "")
                                self.results_table.setItem(row, 4, QTableWidgetItem(path))
                                play_btn = QPushButton("Play")
                                play_btn.setStyleSheet("QPushButton { background: #eef2ff; color: #4f46e5; padding: 4px 12px; }")
                                play_btn.clicked.connect(lambda checked, p=path: self._play_file(p))
                                self.results_table.setCellWidget(row, 5, play_btn)
                            else:
                                self.results_table.item(row, 2).setText("Failed")
                            break

        # Emit each result to the Compare & Rank tab
        for key, r in results.items():
            provider_name = r.get("provider_name", key)
            self.result_ready.emit(
                provider_name,
                voice or "default",
                r.get("success", False),
                r.get("duration_ms", 0.0)
            )

        self._current_tc_index += 1
        self._workers = [w for w in self._workers if not w.isFinished()]
        self._run_single_test_case(voice, edge_voice, builtin, dynamic, use_edge)

    def _play_file(self, path: str):
        if not os.path.exists(path):
            return
        try:
            if self.player is None:
                self.player = QMediaPlayer()
                self.audio_output = QAudioOutput()
                self.player.setAudioOutput(self.audio_output)
            self.player.setSource(QUrl.fromLocalFile(path))
            self.player.play()
        except Exception as e:
            QMessageBox.warning(self, "Playback Error", f"Could not play audio: {e}")
