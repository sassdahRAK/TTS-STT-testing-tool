"""
STT Testing Tab - Test Speech-to-Text across multiple providers.
Modern dashboard layout with full-page scrolling.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QProgressBar, QMessageBox, QCheckBox,
    QComboBox, QSpinBox, QTextEdit, QTabWidget, QLineEdit,
    QScrollArea
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from config import load_config, STT_MODELS
from stt_providers import STTProviderManager
from dynamic_providers import DynamicProviderManager, DynamicSTTCaller
from audio_recorder import AudioRecorder
from add_provider_dialog import AddProviderDialog, ManageProvidersDialog
from nemo_scoring import get_scorer
from batch_testing import BatchTestingWidget
from ui_components import Card, CONTENT_MARGINS, CARD_MARGINS, CONTENT_SPACING


# ──────────────────────────────────────────────────────────────────────────────
# Background Worker
# ──────────────────────────────────────────────────────────────────────────────
class STTWorker(QThread):
    """Background worker for STT transcription."""
    finished = pyqtSignal(dict)
    progress = pyqtSignal(str, str)

    def __init__(self, builtin_manager: STTProviderManager, dynamic_manager: DynamicProviderManager,
                 audio_path: str, language: str, providers: list, dynamic_providers: list):
        super().__init__()
        self.builtin_manager = builtin_manager
        self.dynamic_manager = dynamic_manager
        self.audio_path = audio_path
        self.language = language
        self.providers = providers
        self.dynamic_providers = dynamic_providers

    def run(self):
        results = {}

        for name in self.providers:
            self.progress.emit(name, "Transcribing...")
            result = self.builtin_manager.transcribe(name, self.audio_path, self.language)
            results[name] = result
            status = "Done" if result["success"] else f"Failed: {result['error'][:50]}"
            self.progress.emit(name, status)

        for provider in self.dynamic_providers:
            self.progress.emit(provider.name, "Transcribing...")
            result = DynamicSTTCaller.transcribe(provider, self.audio_path, self.language)
            label = f"custom_{provider.id}"
            results[label] = result
            if result["success"]:
                results[label]["provider_name"] = provider.name
            status = "Done" if result["success"] else f"Failed: {result['error'][:50]}"
            self.progress.emit(provider.name, status)

        self.finished.emit(results)


# ──────────────────────────────────────────────────────────────────────────────
# Main STT Tab — Full Page Scroll
# ──────────────────────────────────────────────────────────────────────────────
class STTTab(QWidget):
    """Tab for testing Speech-to-Text providers — full page scroll."""

    results_ready = pyqtSignal(dict, str)

    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.builtin_manager = STTProviderManager(self.config)
        self.dynamic_manager = DynamicProviderManager()
        self.recorder = AudioRecorder(self.config.sample_rate, self.config.audio_channels)
        self.scorer = get_scorer()
        self.current_audio_path = None
        self.current_results = {}
        self._setup_ui()
        self._refresh_providers()

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

        # ── Card 1: Audio Input ──────────────────────────────────
        input_card = Card("1. Audio Input")
        input_layout = QVBoxLayout(input_card)
        input_layout.setContentsMargins(20, 16, 20, 20)
        input_layout.setSpacing(12)

        input_tabs = QTabWidget()

        # Mic tab
        mic_widget = QWidget()
        mic_layout = QVBoxLayout(mic_widget)
        mic_layout.setSpacing(10)

        mic_controls = QHBoxLayout()
        self.record_btn = QPushButton("● Record")
        self.record_btn.setStyleSheet("""
            QPushButton { background-color: #dc2626; color: white; padding: 12px 28px; font-weight: 600; font-size: 15px; }
            QPushButton:hover { background-color: #b91c1c; }
        """)
        self.record_btn.clicked.connect(self._toggle_recording)
        mic_controls.addWidget(self.record_btn)

        mic_controls.addWidget(QLabel("Duration:"))
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(3, 60)
        self.duration_spin.setValue(10)
        self.duration_spin.setSuffix(" sec")
        mic_controls.addWidget(self.duration_spin)

        mic_controls.addStretch()

        self.mic_status = QLabel("Ready to record")
        self.mic_status.setStyleSheet("color: #059669; font-weight: 600; padding: 6px 14px; background: #ecfdf5; border-radius: 6px;")
        mic_controls.addWidget(self.mic_status)

        mic_layout.addLayout(mic_controls)

        device_row = QHBoxLayout()
        device_row.addWidget(QLabel("Input Device:"))
        self.device_combo = QComboBox()
        devices = AudioRecorder.get_input_devices()
        for idx, name in devices:
            self.device_combo.addItem(name, idx)
        if not devices:
            self.device_combo.addItem("No input devices found")
        device_row.addWidget(self.device_combo)
        device_row.addStretch()
        mic_layout.addLayout(device_row)

        mic_layout.addStretch()
        input_tabs.addTab(mic_widget, "🎤 Microphone")

        # File tab
        file_widget = QWidget()
        file_layout = QVBoxLayout(file_widget)

        file_row = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Select an audio file (WAV, MP3, FLAC)...")
        self.file_path_edit.setReadOnly(True)
        file_row.addWidget(self.file_path_edit)

        browse_btn = QPushButton("Browse...")
        browse_btn.setStyleSheet("QPushButton { background-color: #eef2ff; color: #4f46e5; }")
        browse_btn.clicked.connect(self._browse_file)
        file_row.addWidget(browse_btn)

        file_layout.addLayout(file_row)
        file_layout.addStretch()
        input_tabs.addTab(file_widget, "📁 Audio File")

        input_layout.addWidget(input_tabs)
        self.content_layout.addWidget(input_card)

        # ── Card 2: Reference Text ───────────────────────────────
        ref_card = Card("2. Reference Text (Ground Truth)")
        ref_layout = QVBoxLayout(ref_card)
        ref_layout.setContentsMargins(20, 16, 20, 20)
        ref_layout.setSpacing(8)

        self.ref_text_edit = QTextEdit()
        self.ref_text_edit.setMaximumHeight(80)
        self.ref_text_edit.setPlaceholderText(
            "Enter the correct transcript here to auto-score each model's accuracy (CER). "
            "Leave empty to skip scoring."
        )
        ref_layout.addWidget(self.ref_text_edit)

        self.scorer_status = QLabel()
        if hasattr(self.scorer, 'is_available') and self.scorer.is_available():
            self.scorer_status.setText("✓ NeMo scoring: Active")
            self.scorer_status.setStyleSheet("color: #059669; padding: 6px 14px; background: #ecfdf5; border-radius: 6px;")
        else:
            self.scorer_status.setText("⚠ Scoring: Fallback mode (install nemo-toolkit[asr] for NeMo metrics)")
            self.scorer_status.setStyleSheet("color: #d97706; padding: 6px 14px; background: #fffbeb; border-radius: 6px;")
        ref_layout.addWidget(self.scorer_status)

        self.content_layout.addWidget(ref_card)

        # ── Card 3: STT Providers ────────────────────────────────
        provider_card = Card("3. STT Providers")
        provider_layout = QVBoxLayout(provider_card)
        provider_layout.setContentsMargins(20, 16, 20, 20)
        provider_layout.setSpacing(10)

        builtin_row = QHBoxLayout()
        builtin_row.addWidget(QLabel("Built-in:"))
        self.builtin_checks = {}
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

        btn_row = QHBoxLayout()
        self.add_provider_btn = QPushButton("+ Add Provider")
        self.add_provider_btn.setStyleSheet("QPushButton { background-color: #6366f1; color: white; padding: 8px 20px; }")
        self.add_provider_btn.clicked.connect(self._on_add_provider)
        btn_row.addWidget(self.add_provider_btn)

        self.manage_provider_btn = QPushButton("⚙ Manage")
        self.manage_provider_btn.setStyleSheet("QPushButton { background-color: #f59e0b; color: white; padding: 8px 20px; }")
        self.manage_provider_btn.clicked.connect(self._on_manage_providers)
        btn_row.addWidget(self.manage_provider_btn)

        btn_row.addStretch()

        btn_row.addWidget(QLabel("Language:"))
        self.language_combo = QComboBox()
        self.language_combo.addItems(["en-US", "en-GB", "fr-FR", "de-DE", "es-ES", "km-KH", "ja-JP", "zh-CN"])
        btn_row.addWidget(self.language_combo)

        provider_layout.addLayout(btn_row)
        self.content_layout.addWidget(provider_card)

        # ── Card 4: Transcribe ───────────────────────────────────
        transcribe_card = Card("4. Transcribe")
        transcribe_layout = QHBoxLayout(transcribe_card)
        transcribe_layout.setContentsMargins(20, 16, 20, 20)

        self.transcribe_btn = QPushButton("▶  Transcribe")
        self.transcribe_btn.setStyleSheet("""
            QPushButton {
                background-color: #6366f1;
                color: white;
                padding: 14px 36px;
                font-weight: 600;
                font-size: 15px;
            }
            QPushButton:hover { background-color: #4f46e5; }
            QPushButton:disabled { background-color: #94a3b8; }
        """)
        self.transcribe_btn.clicked.connect(self._on_transcribe)
        transcribe_layout.addWidget(self.transcribe_btn)

        transcribe_layout.addStretch()
        self.content_layout.addWidget(transcribe_card)

        # ── Card 5: Results ──────────────────────────────────────
        results_card = Card("5. Transcription Results")
        results_layout = QVBoxLayout(results_card)
        results_layout.setContentsMargins(20, 16, 20, 20)
        results_layout.setSpacing(8)

        self.results_table = QTableWidget(0, 7)
        self.results_table.setHorizontalHeaderLabels([
            "Provider", "Transcription", "Duration (ms)", "Status",
            "CER", "Accuracy", "Errors (S/D/I)"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setMinimumHeight(200)
        results_layout.addWidget(self.results_table)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        results_layout.addWidget(self.progress_bar)

        self.content_layout.addWidget(results_card)

        # ── Card 6: Batch Testing ────────────────────────────────
        self.batch_widget = BatchTestingWidget(
            self.builtin_manager, self.dynamic_manager,
            self.scorer, self.language_combo
        )
        batch_card = Card("6. Batch Testing")
        batch_layout = QVBoxLayout(batch_card)
        batch_layout.setContentsMargins(20, 16, 20, 20)
        batch_layout.addWidget(self.batch_widget)
        self.content_layout.addWidget(batch_card)

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

        for cb in self.dynamic_checks.values():
            cb.deleteLater()
        self.dynamic_checks.clear()

        for provider in self.dynamic_manager.get_by_type("stt"):
            cb = QCheckBox(provider.name)
            cb.setProperty("provider_id", provider.id)
            cb.setChecked(True)
            self.dynamic_checks[provider.id] = cb
            self.dynamic_row.addWidget(cb)

        self.batch_widget.builtin_manager = self.builtin_manager
        self.batch_widget.dynamic_manager = self.dynamic_manager
        self.batch_widget.refresh_providers()

    def _get_selected_builtin(self) -> list:
        return [key for key, cb in self.builtin_checks.items() if cb.isChecked()]

    def _get_selected_dynamic(self) -> list:
        return [p for p in self.dynamic_manager.get_by_type("stt")
                if p.id in self.dynamic_checks and self.dynamic_checks[p.id].isChecked()]

    def _on_add_provider(self):
        dialog = AddProviderDialog(self.dynamic_manager, self)
        dialog.provider_added.connect(lambda _: self._refresh_providers())
        dialog.exec()

    def _on_manage_providers(self):
        dialog = ManageProvidersDialog(self.dynamic_manager, self)
        dialog.finished.connect(self._refresh_providers())
        dialog.exec()

    def _toggle_recording(self):
        if self.recorder.is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        if not AudioRecorder.is_available():
            QMessageBox.warning(self, "Audio Error", "sounddevice not installed. Install with: pip install sounddevice soundfile")
            return
        try:
            self.recorder.start_recording()
            self.record_btn.setText("■ Stop")
            self.record_btn.setStyleSheet(
                "QPushButton { background-color: #f59e0b; color: white; padding: 12px 28px; font-weight: 600; font-size: 15px; }"
            )
            self.mic_status.setText("Recording...")
            self.mic_status.setStyleSheet("color: #dc2626; font-weight: 600;")
        except Exception as e:
            QMessageBox.critical(self, "Recording Error", str(e))

    def _stop_recording(self):
        try:
            path = self.recorder.stop_recording()
            self.record_btn.setText("● Record")
            self.record_btn.setStyleSheet(
                "QPushButton { background-color: #dc2626; color: white; padding: 12px 28px; font-weight: 600; font-size: 15px; }"
                "QPushButton:hover { background-color: #b91c1c; }"
            )
            if path:
                self.current_audio_path = path
                self.file_path_edit.setText(path)
                self.mic_status.setText("Recording saved!")
                self.mic_status.setStyleSheet("color: #059669; font-weight: 600;")
            else:
                self.mic_status.setText("No audio captured")
        except Exception as e:
            QMessageBox.critical(self, "Recording Error", str(e))

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Audio File", "",
            "Audio Files (*.wav *.mp3 *.flac *.ogg *.m4a *.wma);;All Files (*)"
        )
        if path:
            self.current_audio_path = path
            self.file_path_edit.setText(path)

    def _on_transcribe(self):
        if not self.current_audio_path:
            QMessageBox.warning(self, "Audio Required", "Please record audio or select a file first.")
            return

        builtin = self._get_selected_builtin()
        dynamic = self._get_selected_dynamic()

        if not builtin and not dynamic:
            QMessageBox.warning(self, "Provider Required", "Please select at least one provider.")
            return

        language = self.language_combo.currentText()
        self.current_results.clear()
        self.transcribe_btn.setEnabled(False)
        self.results_table.setRowCount(0)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(builtin) + len(dynamic))
        self.progress_bar.setValue(0)

        self.worker = STTWorker(self.builtin_manager, self.dynamic_manager,
                                self.current_audio_path, language, builtin, dynamic)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, provider: str, status: str):
        self.progress_bar.setValue(self.progress_bar.value() + 1)
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        self.results_table.setItem(row, 0, QTableWidgetItem(provider))
        self.results_table.setItem(row, 1, QTableWidgetItem("..."))
        self.results_table.setItem(row, 2, QTableWidgetItem("-"))
        self.results_table.setItem(row, 3, QTableWidgetItem(status))

    def _on_finished(self, results: dict):
        self.transcribe_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.current_results = results

        reference = self.ref_text_edit.toPlainText().strip()

        self.results_ready.emit(results, reference)

        for row in range(self.results_table.rowCount()):
            provider_item = self.results_table.item(row, 0)
            if provider_item:
                provider_name = provider_item.text()
                for key, r in results.items():
                    name_match = r.get("provider_name", key).lower() == provider_name.lower()
                    key_match = key.lower() == provider_name.lower()
                    if name_match or key_match:
                        if r["success"]:
                            self.results_table.item(row, 1).setText(r["text"])
                            self.results_table.setItem(row, 2, QTableWidgetItem(f"{r['duration_ms']:.0f}"))
                            self.results_table.item(row, 3).setText("Success")

                            if reference and r["text"]:
                                score_result = self.scorer.score(reference, r["text"], use_cer=True)
                                cer_item = QTableWidgetItem(score_result.cer_percent)
                                if score_result.cer <= 0.1:
                                    cer_item.setBackground(Qt.GlobalColor.darkGreen)
                                    cer_item.setForeground(Qt.GlobalColor.white)
                                elif score_result.cer <= 0.25:
                                    cer_item.setBackground(Qt.GlobalColor.yellow)
                                else:
                                    cer_item.setBackground(Qt.GlobalColor.red)
                                    cer_item.setForeground(Qt.GlobalColor.white)
                                self.results_table.setItem(row, 4, cer_item)

                                acc_item = QTableWidgetItem(score_result.accuracy_percent)
                                self.results_table.setItem(row, 5, acc_item)

                                err_str = f"{score_result.substitutions}/{score_result.deletions}/{score_result.insertions}"
                                self.results_table.setItem(row, 6, QTableWidgetItem(err_str))
                            else:
                                self.results_table.setItem(row, 4, QTableWidgetItem("-"))
                                self.results_table.setItem(row, 5, QTableWidgetItem("-"))
