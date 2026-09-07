"""
Batch Testing Module - Test multiple audio files across all STT providers.
Modern dashboard layout.
"""

import csv
import json
import os
from dataclasses import dataclass, field

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
    QMessageBox, QProgressBar, QGroupBox, QTabWidget, QTextEdit,
    QAbstractItemView, QScrollArea, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from nemo_scoring import get_scorer


@dataclass
class BatchTestItem:
    """Single audio file with optional reference text."""
    audio_path: str
    reference: str = ""
    duration: float = 0.0


class BatchSTTWorker(QThread):
    """Background worker that processes multiple audio files across all providers."""
    file_started = pyqtSignal(int, str)
    file_finished = pyqtSignal(int, dict)
    all_finished = pyqtSignal()
    progress = pyqtSignal(str, str)

    def __init__(self, builtin_manager, dynamic_manager,
                 items: list, language: str, providers: list, dynamic_providers: list):
        super().__init__()
        self.builtin_manager = builtin_manager
        self.dynamic_manager = dynamic_manager
        self.items = items
        self.language = language
        self.providers = providers
        self.dynamic_providers = dynamic_providers
        self._stop_requested = False

    def stop(self):
        self._stop_requested = True

    def run(self):
        for i, item in enumerate(self.items):
            if self._stop_requested:
                break
            self.file_started.emit(i, os.path.basename(item.audio_path))

            from stt_providers import STTProviderManager
            from dynamic_providers import DynamicSTTCaller

            results = {}
            for name in self.providers:
                self.progress.emit(name, "Transcribing...")
                result = self.builtin_manager.transcribe(name, item.audio_path, self.language)
                results[name] = result
                status = "Done" if result["success"] else f"Failed: {result['error'][:50]}"
                self.progress.emit(name, status)

            for provider in self.dynamic_providers:
                self.progress.emit(provider.name, "Transcribing...")
                result = DynamicSTTCaller.transcribe(provider, item.audio_path, self.language)
                results[provider.id] = result
                status = "Done" if result["success"] else f"Failed: {result['error'][:50]}"
                self.progress.emit(provider.name, status)

            self.file_finished.emit(i, results)

        self.all_finished.emit()


class BatchTestingWidget(QWidget):
    """Widget for batch testing multiple audio files."""

    results_ready = pyqtSignal(str, str, str, str, bool, float)

    def __init__(self, builtin_manager, dynamic_manager, scorer, language_combo, parent=None):
        super().__init__(parent)
        self.builtin_manager = builtin_manager
        self.dynamic_manager = dynamic_manager
        self.scorer = scorer
        self.language_combo = language_combo
        self.items = []
        self.worker = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # === File Selection ===
        file_group = QGroupBox("Audio Files")
        file_group.setStyleSheet("""
            QGroupBox {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                margin-top: 14px;
                padding-top: 24px;
                font-weight: 600;
                font-size: 15px;
                color: #0f172a;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 20px;
                padding: 0 10px;
                color: #0f172a;
            }
        """)
        file_layout = QVBoxLayout(file_group)

        btn_row = QHBoxLayout()
        self.add_files_btn = QPushButton("Add Audio Files...")
        self.add_files_btn.setStyleSheet("QPushButton { background-color: #6366f1; color: white; padding: 8px 20px; }")
        self.add_files_btn.clicked.connect(self._add_files)
        btn_row.addWidget(self.add_files_btn)

        self.add_folder_btn = QPushButton("Add Folder...")
        self.add_folder_btn.setStyleSheet("QPushButton { background-color: #6366f1; color: white; padding: 8px 20px; }")
        self.add_folder_btn.clicked.connect(self._add_folder)
        btn_row.addWidget(self.add_folder_btn)

        self.load_refs_btn = QPushButton("Load References (CSV/JSON)...")
        self.load_refs_btn.setStyleSheet("QPushButton { background-color: #8b5cf6; color: white; padding: 8px 20px; }")
        self.load_refs_btn.clicked.connect(self._load_references)
        btn_row.addWidget(self.load_refs_btn)

        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.setStyleSheet("QPushButton { background-color: #fef2f2; color: #dc2626; padding: 8px 20px; }")
        self.clear_btn.clicked.connect(self._clear_files)
        btn_row.addWidget(self.clear_btn)

        btn_row.addStretch()
        file_layout.addLayout(btn_row)

        self.file_table = QTableWidget(0, 4)
        self.file_table.setHorizontalHeaderLabels(["#", "File", "Reference Text", "Status"])
        self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.file_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.file_table.setAlternatingRowColors(True)
        self.file_table.setMaximumHeight(150)
        file_layout.addWidget(self.file_table)

        self.file_count_label = QLabel("0 files loaded")
        self.file_count_label.setStyleSheet("color: #94a3b8; font-size: 13px;")
        file_layout.addWidget(self.file_count_label)

        layout.addWidget(file_group)

        # === Provider Selection ===
        provider_group = QGroupBox("Providers to Test")
        provider_group.setStyleSheet("""
            QGroupBox {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                margin-top: 14px;
                padding-top: 24px;
                font-weight: 600;
                font-size: 15px;
                color: #0f172a;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 20px;
                padding: 0 10px;
                color: #0f172a;
            }
        """)
        provider_layout = QVBoxLayout(provider_group)

        self.provider_label = QLabel("Providers: (uses same selection as Single File tab)")
        self.provider_label.setStyleSheet("color: #64748b; font-size: 13px;")
        provider_layout.addWidget(self.provider_label)

        self.builtin_checks = {}
        builtin_row = QHBoxLayout()
        builtin_row.addWidget(QLabel("Built-in:"))
        for key, label in [("openai", "OpenAI Whisper"), ("google", "Google Cloud"), ("azure", "Azure"), ("local", "Local Vosk")]:
            cb = QCheckBox(label)
            cb.setProperty("provider_key", key)
            self.builtin_checks[key] = cb
            builtin_row.addWidget(cb)
        builtin_row.addStretch()
        provider_layout.addLayout(builtin_row)

        self.dynamic_row = QHBoxLayout()
        self.dynamic_row.addWidget(QLabel("Custom:"))
        self.dynamic_checks = {}
        self.dynamic_row.addStretch()
        provider_layout.addLayout(self.dynamic_row)

        layout.addWidget(provider_group)

        # === Controls ===
        controls_row = QHBoxLayout()
        self.run_btn = QPushButton("▶  Run Batch Test")
        self.run_btn.setStyleSheet("""
            QPushButton {
                background-color: #6366f1;
                color: white;
                padding: 12px 28px;
                font-weight: 600;
                font-size: 15px;
            }
            QPushButton:hover { background-color: #4f46e5; }
            QPushButton:disabled { background-color: #94a3b8; }
        """)
        self.run_btn.clicked.connect(self._run_batch)
        controls_row.addWidget(self.run_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setStyleSheet("QPushButton { background-color: #dc2626; color: white; padding: 12px 28px; }")
        self.stop_btn.clicked.connect(self._stop_batch)
        self.stop_btn.setEnabled(False)
        controls_row.addWidget(self.stop_btn)

        controls_row.addStretch()

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        controls_row.addWidget(self.progress_bar)

        layout.addLayout(controls_row)

        # === Results ===
        results_group = QGroupBox("Batch Results")
        results_group.setStyleSheet("""
            QGroupBox {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                margin-top: 14px;
                padding-top: 24px;
                font-weight: 600;
                font-size: 15px;
                color: #0f172a;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 20px;
                padding: 0 10px;
                color: #0f172a;
            }
        """)
        results_layout = QVBoxLayout(results_group)

        self.results_table = QTableWidget(0, 8)
        self.results_table.setHorizontalHeaderLabels([
            "File", "Provider", "Transcription", "Duration (ms)",
            "CER", "Accuracy", "Errors (S/D/I)", "Status"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setMinimumHeight(200)
        results_layout.addWidget(self.results_table)

        self.summary_label = QLabel("No results yet")
        self.summary_label.setStyleSheet("font-weight: 600; padding: 4px; color: #64748b;")
        results_layout.addWidget(self.summary_label)

        layout.addWidget(results_group)

    def refresh_providers(self):
        available = self.builtin_manager.get_available_providers()
        for key, cb in self.builtin_checks.items():
            cb.setChecked(key in available)
            cb.setEnabled(key in available)
            if key not in available:
                cb.setText(cb.text() + " (not configured)")

        for cb in self.dynamic_checks.values():
            cb.deleteLater()
        self.dynamic_checks.clear()

        for provider in self.dynamic_manager.get_by_type("stt"):
            cb = QCheckBox(provider.name)
            cb.setProperty("provider_id", provider.id)
            cb.setChecked(True)
            self.dynamic_checks[provider.id] = cb
            self.dynamic_row.addWidget(cb)

    def _add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Add Audio Files", "",
            "Audio Files (*.wav *.mp3 *.flac *.ogg *.m4a *.wma);;All Files (*)"
        )
        if paths:
            for path in paths:
                self.items.append(BatchTestItem(audio_path=path))
            self._refresh_file_table()

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder with Audio Files")
        if folder:
            extensions = {'.wav', '.mp3', '.flac', '.ogg', '.m4a', '.wma'}
            for filename in sorted(os.listdir(folder)):
                ext = os.path.splitext(filename)[1].lower()
                if ext in extensions:
                    path = os.path.join(folder, filename)
                    self.items.append(BatchTestItem(audio_path=path))
            self._refresh_file_table()

    def _load_references(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load References", "",
            "CSV Files (*.csv);;JSON Files (*.json);;All Files (*)"
        )
        if not path:
            return

        try:
            if path.endswith('.json'):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        audio_path = item.get('audio_path', item.get('file', ''))
                        reference = item.get('reference', item.get('text', item.get('transcript', '')))
                        if audio_path:
                            self.items.append(BatchTestItem(audio_path=audio_path, reference=reference))
                elif isinstance(data, dict):
                    for audio_path, reference in data.items():
                        self.items.append(BatchTestItem(audio_path=audio_path, reference=reference))
            else:
                with open(path, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if len(row) >= 2:
                            self.items.append(BatchTestItem(audio_path=row[0].strip(), reference=row[1].strip()))
                        elif len(row) == 1:
                            self.items.append(BatchTestItem(audio_path=row[0].strip()))

            self._refresh_file_table()
            QMessageBox.information(self, "Loaded", f"Loaded references for {len(self.items)} files.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load references:\n{e}")

    def _clear_files(self):
        self.items.clear()
        self._refresh_file_table()

    def _refresh_file_table(self):
        self.file_table.setRowCount(0)
        for i, item in enumerate(self.items):
            row = self.file_table.rowCount()
            self.file_table.insertRow(row)
            self.file_table.setItem(row, 0, QTableWidgetItem(str(i + 1)))
            self.file_table.setItem(row, 1, QTableWidgetItem(os.path.basename(item.audio_path)))
            self.file_table.setItem(row, 2, QTableWidgetItem(item.reference[:100]))
            self.file_table.setItem(row, 3, QTableWidgetItem("Pending"))
        self.file_count_label.setText(f"{len(self.items)} files loaded")

    def _run_batch(self):
        if not self.items:
            QMessageBox.warning(self, "No Files", "Add audio files first.")
            return

        providers = [key for key, cb in self.builtin_checks.items() if cb.isChecked()]
        dynamic = [p for p in self.dynamic_manager.get_by_type("stt")
                   if p.id in self.dynamic_checks and self.dynamic_checks[p.id].isChecked()]

        if not providers and not dynamic:
            QMessageBox.warning(self, "No Providers", "Select at least one provider.")
            return

        language = self.language_combo.currentText()
        self.results_table.setRowCount(0)
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(self.items) * (len(providers) + len(dynamic)))
        self.progress_bar.setValue(0)

        self.worker = BatchSTTWorker(
            self.builtin_manager, self.dynamic_manager,
            self.items, language, providers, dynamic
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.file_finished.connect(self._on_file_finished)
        self.worker.all_finished.connect(self._on_all_finished)
        self.worker.start()

    def _stop_batch(self):
        if self.worker:
            self.worker.stop()
        self.stop_btn.setEnabled(False)

    def _on_progress(self, provider: str, status: str):
        self.progress_bar.setValue(self.progress_bar.value() + 1)

    def _on_file_finished(self, file_index: int, results: dict):
        item = self.items[file_index]
        self.file_table.item(file_index, 3).setText("Done")

        for key, r in results.items():
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)
            self.results_table.setItem(row, 0, QTableWidgetItem(os.path.basename(item.audio_path)))
            self.results_table.setItem(row, 1, QTableWidgetItem(key))
            self.results_table.setItem(row, 2, QTableWidgetItem(r.get("text", "")[:100]))
            self.results_table.setItem(row, 3, QTableWidgetItem(f"{r.get('duration_ms', 0):.0f}"))

            if r.get("success") and item.reference and r.get("text"):
                try:
                    score_result = self.scorer.score(item.reference, r["text"], use_cer=True)
                    self.results_table.setItem(row, 4, QTableWidgetItem(score_result.cer_percent))
                    self.results_table.setItem(row, 5, QTableWidgetItem(score_result.accuracy_percent))
                    err_str = f"{score_result.substitutions}/{score_result.deletions}/{score_result.insertions}"
                    self.results_table.setItem(row, 6, QTableWidgetItem(err_str))
                    self.results_table.setItem(row, 7, QTableWidgetItem("Success"))

                    self.results_ready.emit(
                        key, "STT", item.reference, r["text"],
                        True, r.get("duration_ms", 0)
                    )
                except Exception:
                    self.results_table.setItem(row, 4, QTableWidgetItem("-"))
                    self.results_table.setItem(row, 5, QTableWidgetItem("-"))
                    self.results_table.setItem(row, 6, QTableWidgetItem("-"))
                    self.results_table.setItem(row, 7, QTableWidgetItem("Scoring failed"))
            else:
                self.results_table.setItem(row, 4, QTableWidgetItem("-"))
                self.results_table.setItem(row, 5, QTableWidgetItem("-"))
                self.results_table.setItem(row, 6, QTableWidgetItem("-"))
                self.results_table.setItem(row, 7, QTableWidgetItem("Failed" if not r.get("success") else "No ref"))

    def _on_all_finished(self):
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.summary_label.setText(f"Completed testing {len(self.items)} files.")
