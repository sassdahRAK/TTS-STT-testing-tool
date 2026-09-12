"""
LLM API Testing Tab - Test and compare LLM model responses.
Modern dashboard layout with full-page scrolling.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QTextEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QCheckBox, QSpinBox, QDoubleSpinBox,
    QSplitter, QTabWidget, QScrollArea, QFrame, QLineEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from config import load_config, LLM_MODELS
from llm_providers import LLMProviderManager
from dynamic_providers import DynamicProviderManager, DynamicLLMCaller
from add_provider_dialog import AddProviderDialog, ManageProvidersDialog
from ui_components import Card, CONTENT_MARGINS, CARD_MARGINS, CONTENT_SPACING


# ──────────────────────────────────────────────────────────────────────────────
# Reusable Components
# ──────────────────────────────────────────────────────────────────────────────
class Card(QGroupBox):
    """Modern dashboard card."""

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setTitle(title)
        self.setStyleSheet("""
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


class LLMWorker(QThread):
    """Background worker for LLM API calls."""
    finished = pyqtSignal(dict)
    progress = pyqtSignal(str, str)

    def __init__(self, builtin_manager: LLMProviderManager, dynamic_manager: DynamicProviderManager,
                 prompt: str, model_map: dict, dynamic_models: dict,
                 system_prompt: str, temperature: float, max_tokens: int,
                 providers: list, dynamic_providers: list):
        super().__init__()
        self.builtin_manager = builtin_manager
        self.dynamic_manager = dynamic_manager
        self.prompt = prompt
        self.model_map = model_map
        self.dynamic_models = dynamic_models
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.providers = providers
        self.dynamic_providers = dynamic_providers

    def run(self):
        results = {}

        for name in self.providers:
            self.progress.emit(name, "Calling API...")
            model = self.model_map.get(name, "")
            result = self.builtin_manager.chat(name, self.prompt, model, self.system_prompt, self.temperature, self.max_tokens)
            results[name] = result
            status = "Done" if result["success"] else f"Failed: {result['error'][:50]}"
            self.progress.emit(name, status)

        for provider in self.dynamic_providers:
            self.progress.emit(provider.name, "Calling API...")
            model = self.dynamic_models.get(provider.id, provider.models[0] if provider.models else "default")
            result = DynamicLLMCaller.chat(provider, self.prompt, model, self.system_prompt, self.temperature, self.max_tokens)
            label = f"custom_{provider.id}"
            results[label] = result
            if result["success"]:
                results[label]["provider_name"] = provider.name
            status = "Done" if result["success"] else f"Failed: {result['error'][:50]}"
            self.progress.emit(provider.name, status)

        self.finished.emit(results)


# ──────────────────────────────────────────────────────────────────────────────
# Main LLM Tab — Full Page Scroll
# ──────────────────────────────────────────────────────────────────────────────
class LLMTab(QWidget):
    """Tab for testing LLM API models — full page scroll."""

    def __init__(self, dynamic_manager=None):
        super().__init__()
        self.config = load_config()
        self.builtin_manager = LLMProviderManager(self.config)
        self.dynamic_manager = dynamic_manager or DynamicProviderManager()
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

        # ── Card 1: Prompt Input ─────────────────────────────────
        prompt_card = Card("1. Prompt Input")
        prompt_layout = QVBoxLayout(prompt_card)
        prompt_layout.setContentsMargins(20, 16, 20, 20)
        prompt_layout.setSpacing(12)

        prompt_layout.addWidget(QLabel("System Prompt (optional):"))
        self.system_input = QTextEdit()
        self.system_input.setPlaceholderText("You are a helpful assistant...")
        self.system_input.setMaximumHeight(80)
        prompt_layout.addWidget(self.system_input)

        prompt_layout.addWidget(QLabel("User Prompt:"))
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("Enter your test prompt here...")
        self.prompt_input.setMaximumHeight(120)
        prompt_layout.addWidget(self.prompt_input)

        params_row = QHBoxLayout()
        params_row.addWidget(QLabel("Temperature:"))
        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0.0, 2.0)
        self.temp_spin.setValue(0.7)
        self.temp_spin.setSingleStep(0.1)
        params_row.addWidget(self.temp_spin)

        params_row.addWidget(QLabel("Max Tokens:"))
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(50, 8192)
        self.max_tokens_spin.setValue(1024)
        params_row.addWidget(self.max_tokens_spin)

        params_row.addStretch()
        prompt_layout.addLayout(params_row)

        self.content_layout.addWidget(prompt_card)

        # ── Card 2: Models to Test ───────────────────────────────
        provider_card = Card("2. Models to Test")
        provider_layout = QVBoxLayout(provider_card)
        provider_layout.setContentsMargins(20, 16, 20, 20)
        provider_layout.setSpacing(12)

        builtin_row = QHBoxLayout()
        builtin_row.addWidget(QLabel("Built-in:"))
        self.builtin_checks = {}
        self.builtin_model_combos = {}
        for key, label in [("openai", "OpenAI"), ("anthropic", "Anthropic"), ("custom_builtin", "Custom API")]:
            cb = QCheckBox(label)
            cb.setProperty("provider_key", key)
            self.builtin_checks[key] = cb
            builtin_row.addWidget(cb)

            model_combo = QComboBox()
            model_combo.setMinimumWidth(180)
            for model in LLM_MODELS.get(key.replace("_builtin", ""), []):
                model_combo.addItem(model)
            if "custom" in key:
                model_combo.setEditable(True)
            self.builtin_model_combos[key] = model_combo
            builtin_row.addWidget(model_combo)
        builtin_row.addStretch()
        provider_layout.addLayout(builtin_row)

        self.dynamic_row = QHBoxLayout()
        self.dynamic_row.addWidget(QLabel("Custom:"))
        self.dynamic_checks = {}
        self.dynamic_model_combos = {}
        self.dynamic_row.addStretch()
        provider_layout.addLayout(self.dynamic_row)

        btn_row = QHBoxLayout()
        self.add_provider_btn = QPushButton("+ Add Provider")
        self.add_provider_btn.setStyleSheet("QPushButton { background-color: #6366f1; color: white; padding: 8px 20px; }")
        self.add_provider_btn.clicked.connect(self._on_add_provider)
        btn_row.addWidget(self.add_provider_btn)

        self.manage_provider_btn = QPushButton("Manage Providers")
        self.manage_provider_btn.setStyleSheet("QPushButton { background-color: #f59e0b; color: white; padding: 8px 20px; }")
        self.manage_provider_btn.clicked.connect(self._on_manage_providers)
        btn_row.addWidget(self.manage_provider_btn)

        btn_row.addStretch()
        provider_layout.addLayout(btn_row)

        self.content_layout.addWidget(provider_card)

        # ── Card 3: Send ─────────────────────────────────────────
        send_card = Card("3. Send to Models")
        send_layout = QHBoxLayout(send_card)
        send_layout.setContentsMargins(20, 16, 20, 20)

        self.send_btn = QPushButton("▶  Send to All Selected")
        self.send_btn.setStyleSheet("""
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
        self.send_btn.clicked.connect(self._on_send)
        send_layout.addWidget(self.send_btn)

        send_layout.addStretch()
        self.content_layout.addWidget(send_card)

        # ── Card 4: Responses ────────────────────────────────────
        results_card = Card("4. Responses")
        results_layout = QVBoxLayout(results_card)
        results_layout.setContentsMargins(20, 16, 20, 20)

        self.results_tabs = QTabWidget()
        results_layout.addWidget(self.results_tabs)

        self.content_layout.addWidget(results_card)

        self.content_layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _refresh_providers(self):
        available = self.builtin_manager.get_available_providers()
        for key, cb in self.builtin_checks.items():
            lookup_key = key.replace("_builtin", "")
            cb.setChecked(lookup_key in available)
            cb.setEnabled(lookup_key in available)
            if lookup_key not in available:
                cb.setText(cb.text() + " (not configured)")

        for cb in self.dynamic_checks.values():
            cb.deleteLater()
        for combo in self.dynamic_model_combos.values():
            combo.deleteLater()
        self.dynamic_checks.clear()
        self.dynamic_model_combos.clear()

        for provider in self.dynamic_manager.get_by_type("llm"):
            cb = QCheckBox(provider.name)
            cb.setProperty("provider_id", provider.id)
            cb.setChecked(True)
            self.dynamic_checks[provider.id] = cb
            self.dynamic_row.addWidget(cb)

            model_combo = QComboBox()
            model_combo.setMinimumWidth(180)
            for model in provider.models:
                model_combo.addItem(model)
            model_combo.setEditable(True)
            self.dynamic_model_combos[provider.id] = model_combo
            self.dynamic_row.addWidget(model_combo)

    def _get_selected_builtin(self) -> list:
        return [key.replace("_builtin", "") for key, cb in self.builtin_checks.items() if cb.isChecked()]

    def _get_selected_dynamic(self) -> list:
        return [p for p in self.dynamic_manager.get_by_type("llm")
                if p.id in self.dynamic_checks and self.dynamic_checks[p.id].isChecked()]

    def _on_add_provider(self):
        dialog = AddProviderDialog(self.dynamic_manager, self)
        dialog.provider_added.connect(lambda _: self._refresh_providers())
        dialog.exec()

    def _on_manage_providers(self):
        dialog = ManageProvidersDialog(self.dynamic_manager, self)
        dialog.finished.connect(self._refresh_providers)
        dialog.exec()

    def _on_send(self):
        prompt = self.prompt_input.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "Prompt Required", "Please enter a prompt to send.")
            return

        builtin = self._get_selected_builtin()
        dynamic = self._get_selected_dynamic()

        if not builtin and not dynamic:
            QMessageBox.warning(self, "Provider Required", "Please select at least one provider.")
            return

        model_map = {}
        for key, combo in self.builtin_model_combos.items():
            lookup = key.replace("_builtin", "")
            if lookup in builtin:
                model_map[lookup] = combo.currentText()

        dynamic_models = {}
        for provider in dynamic:
            if provider.id in self.dynamic_model_combos:
                dynamic_models[provider.id] = self.dynamic_model_combos[provider.id].currentText()

        system_prompt = self.system_input.toPlainText().strip()
        temperature = self.temp_spin.value()
        max_tokens = self.max_tokens_spin.value()

        self.current_results.clear()
        self.results_tabs.clear()
        self.send_btn.setEnabled(False)

        self.worker = LLMWorker(self.builtin_manager, self.dynamic_manager,
                                prompt, model_map, dynamic_models,
                                system_prompt, temperature, max_tokens,
                                builtin, dynamic)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, provider: str, status: str):
        if self.results_tabs.findChild(QWidget, provider) is None:
            placeholder = QTextEdit()
            placeholder.setReadOnly(True)
            placeholder.setPlainText(f"Waiting... ({status})")
            self.results_tabs.addTab(placeholder, provider)

    def _on_finished(self, results: dict):
        self.send_btn.setEnabled(True)
        self.current_results = results
        self.results_tabs.clear()

        for key, result in results.items():
            provider_name = result.get("provider_name", key.capitalize())
            response_widget = QTextEdit()
            response_widget.setReadOnly(True)

            if result["success"]:
                text = result["text"]
                meta = f"---\nDuration: {result['duration_ms']:.0f}ms | Tokens: {result['tokens']}"
                response_widget.setPlainText(text + "\n\n" + meta)
            else:
                response_widget.setPlainText(f"ERROR: {result['error']}")
                response_widget.setStyleSheet("QTextEdit { color: #dc2626; }")

            self.results_tabs.addTab(response_widget, provider_name)
