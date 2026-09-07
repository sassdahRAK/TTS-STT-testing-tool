"""
Add Provider Dialog - UI for dynamically adding custom API providers.
Supports auto-detection of provider type from endpoint URL.
"""

import uuid
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QGroupBox, QFormLayout, QTextEdit,
    QMessageBox, QCheckBox, QSpinBox, QListWidget, QListWidgetItem,
    QInputDialog, QTabWidget, QWidget, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from dynamic_providers import (
    DynamicProviderManager, CustomProvider, ProviderType,
    detect_provider_type, DETECTION_PATTERNS
)


class AddProviderDialog(QDialog):
    """Dialog for adding a new custom API provider."""

    provider_added = pyqtSignal(object)  # Emits the new CustomProvider

    def __init__(self, manager: DynamicProviderManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.detected_info = None
        self.setWindowTitle("Add Custom Provider")
        self.setMinimumSize(550, 600)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # === Header ===
        header = QLabel("Add a Custom API Provider")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #1976D2; padding: 8px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        desc = QLabel("Connect any TTS, STT, or LLM API. Paste your endpoint URL and we'll auto-detect the type.")
        desc.setStyleSheet("color: #666; padding: 0 8px 12px 8px;")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

        # === Form ===
        form_group = QGroupBox("Provider Details")
        form_layout = QFormLayout(form_group)

        # Provider name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("My Custom Provider")
        form_layout.addRow("Name:", self.name_input)

        # Endpoint URL
        self.endpoint_input = QLineEdit()
        self.endpoint_input.setPlaceholderText("https://api.example.com/v1/endpoint")
        self.endpoint_input.textChanged.connect(self._on_endpoint_changed)
        form_layout.addRow("Endpoint URL:", self.endpoint_input)

        # Detect button
        detect_row = QHBoxLayout()
        self.detect_btn = QPushButton("Auto-Detect")
        self.detect_btn.clicked.connect(self._on_detect)
        self.detect_btn.setStyleSheet(
            "QPushButton { background-color: #FF9800; color: white; padding: 6px 16px; }"
        )
        detect_row.addWidget(self.detect_btn)
        self.detect_status = QLabel("")
        self.detect_status.setStyleSheet("color: #4CAF50;")
        detect_row.addWidget(self.detect_status)
        detect_row.addStretch()
        form_layout.addRow("", detect_row)

        # Provider type
        self.type_combo = QComboBox()
        self.type_combo.addItems(["TTS (Text-to-Speech)", "STT (Speech-to-Text)", "LLM (Language Model)"])
        form_layout.addRow("Provider Type:", self.type_combo)

        # API Key
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("sk-... or leave empty if no auth needed")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("API Key:", self.api_key_input)

        # Show key toggle
        self.show_key_check = QCheckBox("Show API Key")
        self.show_key_check.toggled.connect(self._toggle_key_visibility)
        form_layout.addRow("", self.show_key_check)

        # Models
        models_row = QHBoxLayout()
        self.models_input = QLineEdit()
        self.models_input.setPlaceholderText("model1, model2, model3")
        models_row.addWidget(self.models_input)
        add_model_btn = QPushButton("+")
        add_model_btn.setMaximumWidth(30)
        add_model_btn.clicked.connect(self._add_model_interactive)
        models_row.addWidget(add_model_btn)
        form_layout.addRow("Models (comma-sep):", models_row)

        # Region / extra config
        self.region_input = QLineEdit()
        self.region_input.setPlaceholderText("e.g., eastus, us-west (optional)")
        form_layout.addRow("Region (optional):", self.region_input)

        layout.addWidget(form_group)

        # === Quick Templates ===
        templates_group = QGroupBox("Quick Templates (click to auto-fill)")
        templates_layout = QVBoxLayout(templates_group)

        template_row = QHBoxLayout()
        templates = [
            ("OpenAI TTS", "https://api.openai.com/v1/audio/speech"),
            ("OpenAI Whisper", "https://api.openai.com/v1/audio/transcriptions"),
            ("OpenAI Chat", "https://api.openai.com/v1/chat/completions"),
            ("Anthropic", "https://api.anthropic.com/v1/messages"),
            ("Deepgram", "https://api.deepgram.com/v1/listen"),
            ("Groq", "https://api.groq.com/openai/v1/chat/completions"),
            ("OpenRouter", "https://openrouter.ai/api/v1/chat/completions"),
            ("ElevenLabs", "https://api.elevenlabs.io/v1/text-to-speech"),
            ("Together", "https://api.together.xyz/v1/chat/completions"),
        ]
        for name, url in templates:
            btn = QPushButton(name)
            btn.setStyleSheet(
                "QPushButton { padding: 4px 10px; background: #e3f2fd; border: 1px solid #90caf9; border-radius: 3px; }"
                "QPushButton:hover { background: #bbdefb; }"
            )
            btn.clicked.connect(lambda checked, u=url: self._fill_template(u))
            template_row.addWidget(btn)
        template_row.addStretch()
        templates_layout.addLayout(template_row)

        layout.addWidget(templates_group)

        # === Buttons ===
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        self.add_btn = QPushButton("Add Provider")
        self.add_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; padding: 8px 24px; font-weight: bold; }"
            "QPushButton:hover { background-color: #45a049; }"
        )
        self.add_btn.clicked.connect(self._on_add)
        btn_row.addWidget(self.add_btn)

        layout.addLayout(btn_row)

    def _toggle_key_visibility(self, checked):
        self.api_key_input.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )

    def _on_endpoint_changed(self, text):
        """Auto-detect when user pastes a URL."""
        if text.startswith("http"):
            self._on_detect()

    def _on_detect(self):
        """Detect provider type from endpoint URL."""
        endpoint = self.endpoint_input.text().strip()
        if not endpoint:
            return

        self.detected_info = detect_provider_type(endpoint)
        if self.detected_info:
            service = self.detected_info["service"]
            ptype = self.detected_info["type"]
            models = self.detected_info["models"]

            # Update UI
            idx = {"tts": 0, "stt": 1, "llm": 2}.get(ptype, 2)
            self.type_combo.setCurrentIndex(idx)
            self.models_input.setText(", ".join(models))
            self.detect_status.setText(f"Detected: {service.replace('_', ' ').title()}")
            self.detect_status.setStyleSheet("color: #4CAF50; font-weight: bold;")

            # Auto-fill name if empty
            if not self.name_input.text():
                self.name_input.setText(service.replace("_", " ").title())
        else:
            self.detect_status.setText("Unknown endpoint - please select type manually")
            self.detected_info = None

    def _fill_template(self, url: str):
        """Fill form from a template."""
        self.endpoint_input.setText(url)
        self._on_detect()

    def _add_model_interactive(self):
        """Add a model name interactively."""
        model, ok = QInputDialog.getText(self, "Add Model", "Enter model name:")
        if ok and model:
            current = self.models_input.text().strip()
            if current:
                self.models_input.setText(f"{current}, {model}")
            else:
                self.models_input.setText(model)

    def _on_add(self):
        """Validate and add the provider."""
        name = self.name_input.text().strip()
        endpoint = self.endpoint_input.text().strip()
        api_key = self.api_key_input.text().strip()
        models_text = self.models_input.text().strip()
        region = self.region_input.text().strip()

        # Validation
        if not name:
            QMessageBox.warning(self, "Required", "Please enter a provider name.")
            return
        if not endpoint:
            QMessageBox.warning(self, "Required", "Please enter an endpoint URL.")
            return
        if not endpoint.startswith("http"):
            QMessageBox.warning(self, "Invalid URL", "Endpoint must start with http:// or https://")
            return

        # Get type
        type_map = {0: "tts", 1: "stt", 2: "llm"}
        ptype = type_map[self.type_combo.currentIndex()]

        # Parse models
        models = [m.strip() for m in models_text.split(",") if m.strip()] if models_text else ["default"]

        # Build config
        config = {}
        if region:
            config["region"] = region

        # Create provider
        provider = CustomProvider(
            id=str(uuid.uuid4())[:8],
            name=name,
            provider_type=ptype,
            api_key=api_key,
            endpoint=endpoint,
            models=models,
            config=config,
        )

        self.manager.add_provider(provider)
        self.provider_added.emit(provider)
        QMessageBox.information(self, "Added!", f"Provider '{name}' ({ptype.upper()}) added successfully!")
        self.accept()


class ManageProvidersDialog(QDialog):
    """Dialog for managing (viewing/removing) custom providers."""

    def __init__(self, manager: DynamicProviderManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.setWindowTitle("Manage Custom Providers")
        self.setMinimumSize(500, 400)
        self._setup_ui()
        self._refresh_list()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel("Custom Providers")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #1976D2;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Provider list
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget { border: 1px solid #ddd; border-radius: 4px; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #eee; }
            QListWidget::item:selected { background: #e3f2fd; }
        """)
        layout.addWidget(self.list_widget)

        # Buttons
        btn_row = QHBoxLayout()

        remove_btn = QPushButton("Remove Selected")
        remove_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; padding: 6px 16px; }")
        remove_btn.clicked.connect(self._on_remove)
        btn_row.addWidget(remove_btn)

        btn_row.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

    def _refresh_list(self):
        self.list_widget.clear()
        for provider in self.manager.get_all():
            ptype_emoji = {"tts": "", "stt": "", "llm": ""}.get(provider.provider_type, "")
            item = QListWidgetItem(
                f"{ptype_emoji} [{provider.provider_type.upper()}] {provider.name}\n"
                f"    Endpoint: {provider.endpoint}\n"
                f"    Models: {', '.join(provider.models)}"
            )
            item.setData(Qt.ItemDataRole.UserRole, provider.id)
            self.list_widget.addItem(item)

    def _on_remove(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.information(self, "Select", "Please select a provider to remove.")
            return

        provider_id = item.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self, "Confirm Remove",
            "Remove this custom provider?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.manager.remove_provider(provider_id)
            self._refresh_list()
