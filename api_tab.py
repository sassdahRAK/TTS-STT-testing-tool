"""
API Management Tab - Central hub for adding and managing custom API providers.
Modern dashboard layout with full-page scrolling.
"""

import uuid
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QDialog, QFormLayout, QGridLayout, QTextEdit,
    QCheckBox, QSpinBox, QDoubleSpinBox, QTabWidget, QFrame,
    QScrollArea, QSizePolicy, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from dynamic_providers import (
    DynamicProviderManager, CustomProvider,
    detect_provider_type, DETECTION_PATTERNS
)
from ui_components import Card, CONTENT_MARGINS, CARD_MARGINS, CONTENT_SPACING


# ──────────────────────────────────────────────────────────────────────────────
# Reusable Card Widget
# ──────────────────────────────────────────────────────────────────────────────
class Card(QGroupBox):
    """Modern dashboard card with consistent styling."""

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


class SectionHeader(QWidget):
    """Section header with title and optional subtitle."""

    def __init__(self, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 18px; font-weight: 700; color: #0f172a;")
        layout.addWidget(title_label)

        if subtitle:
            sub_label = QLabel(subtitle)
            sub_label.setStyleSheet("font-size: 13px; color: #64748b; margin-bottom: 8px;")
            layout.addWidget(sub_label)


# ──────────────────────────────────────────────────────────────────────────────
# Provider Card (visual card in the list)
# ──────────────────────────────────────────────────────────────────────────────
class ProviderCard(QFrame):
    """Visual card displaying a provider's info."""

    def __init__(self, provider: CustomProvider, parent=None):
        super().__init__(parent)
        self.provider = provider
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            ProviderCard {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                padding: 16px;
                margin: 4px 0;
            }
            ProviderCard:hover {
                border-color: #6366f1;
                background: #fafbff;
            }
        """)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(16)

        # Left: Info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(6)

        header = QHBoxLayout()
        name_label = QLabel(f"<b>{self.provider.name}</b>")
        name_label.setStyleSheet("font-size: 16px; color: #0f172a;")
        header.addWidget(name_label)

        type_badge = QLabel(f" {self.provider.provider_type.upper()} ")
        color = {"tts": "#10b981", "stt": "#3b82f6", "llm": "#8b5cf6"}.get(
            self.provider.provider_type, "#64748b"
        )
        type_badge.setStyleSheet(f"""
            QLabel {{
                background: {color};
                color: white;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 12px;
                font-weight: 600;
            }}
        """)
        header.addWidget(type_badge)
        header.addStretch()
        info_layout.addLayout(header)

        endpoint_label = QLabel(f"<span style='color:#64748b;'>{self.provider.endpoint}</span>")
        endpoint_label.setWordWrap(True)
        endpoint_label.setMaximumWidth(600)
        info_layout.addWidget(endpoint_label)

        models_text = ", ".join(self.provider.models) if self.provider.models else "default"
        models_label = QLabel(f"<span style='color:#94a3b8; font-size:13px;'>Models: {models_text}</span>")
        info_layout.addWidget(models_label)

        layout.addLayout(info_layout, stretch=1)

        # Right: Actions
        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(6)

        edit_btn = QPushButton("Edit")
        edit_btn.setStyleSheet("""
            QPushButton { padding: 6px 18px; background: #eef2ff; color: #4f46e5; }
            QPushButton:hover { background: #e0e7ff; }
        """)
        edit_btn.clicked.connect(self._on_edit)
        actions_layout.addWidget(edit_btn)

        remove_btn = QPushButton("Remove")
        remove_btn.setStyleSheet("""
            QPushButton { padding: 6px 18px; background: #fef2f2; color: #dc2626; }
            QPushButton:hover { background: #fee2e2; }
        """)
        remove_btn.clicked.connect(self._on_remove)
        actions_layout.addWidget(remove_btn)

        layout.addLayout(actions_layout)

    def _on_edit(self):
        dialog = EditProviderDialog(self.provider, self)
        dialog.provider_updated.connect(self._on_updated)
        dialog.exec()

    def _on_updated(self, provider):
        self.parent()._refresh() if hasattr(self.parent(), '_refresh') else None

    def _on_remove(self):
        reply = QMessageBox.question(
            self, "Remove Provider",
            f"Remove '{self.provider.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            parent = self.parent()
            while parent and not isinstance(parent, APITab):
                parent = parent.parent()
            if parent:
                parent.dynamic_manager.remove_provider(self.provider.id)
                parent._refresh()


# ──────────────────────────────────────────────────────────────────────────────
# Dialogs
# ──────────────────────────────────────────────────────────────────────────────
class AddProviderDialog(QDialog):
    """Dialog for adding a new custom provider."""

    provider_added = pyqtSignal(object)

    def __init__(self, manager: DynamicProviderManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.detected_info = None
        self.setWindowTitle("Add New Provider")
        # Wide enough that template buttons never clip; resizable by user
        self.setMinimumSize(620, 620)
        self.resize(680, 680)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # ── Header ───────────────────────────────────────────────
        header = QLabel("+ Add New Provider")
        header.setStyleSheet("font-size: 18px; font-weight: 700; color: #0f172a;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        desc = QLabel("Connect any TTS, STT, or LLM API. Paste your endpoint URL and we'll auto-detect the type.")
        desc.setStyleSheet("color: #64748b; font-size: 13px; margin-bottom: 4px;")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

        # ── Provider Details form ────────────────────────────────
        form_group = QGroupBox("Provider Details")
        form_group.setStyleSheet("""
            QGroupBox {
                font-weight: 600;
                font-size: 13px;
                color: #0f172a;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 18px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 6px; }
            QGroupBox QLabel {
                font-size: 14px;
                font-weight: 500;
                color: #1e293b;
            }
        """)
        form_layout = QFormLayout(form_group)
        form_layout.setContentsMargins(16, 12, 16, 14)
        form_layout.setSpacing(10)
        # Label column fixed width so inputs get the rest of the space
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("My Custom Provider")
        form_layout.addRow("Name *:", self.name_input)

        self.endpoint_input = QLineEdit()
        self.endpoint_input.setPlaceholderText("https://api.example.com/v1/endpoint")
        self.endpoint_input.textChanged.connect(self._on_endpoint_changed)
        form_layout.addRow("Endpoint URL *:", self.endpoint_input)

        # Auto-detect row
        detect_row = QHBoxLayout()
        detect_row.setSpacing(10)
        self.detect_btn = QPushButton("⚡ Auto-Detect Type")
        self.detect_btn.setStyleSheet("""
            QPushButton {
                background-color: #f59e0b; color: white;
                padding: 6px 16px; font-weight: 600; font-size: 13px;
                border-radius: 7px;
            }
            QPushButton:hover { background-color: #d97706; }
        """)
        self.detect_btn.clicked.connect(self._on_detect)
        detect_row.addWidget(self.detect_btn)
        self.detect_status = QLabel("")
        self.detect_status.setMinimumWidth(160)
        self.detect_status.setStyleSheet("font-size: 14px; font-weight: 600;")
        detect_row.addWidget(self.detect_status)
        detect_row.addStretch()
        form_layout.addRow("", detect_row)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["TTS (Text-to-Speech)", "STT (Speech-to-Text)", "LLM (Language Model)"])
        self.type_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        form_layout.addRow("Provider Type *:", self.type_combo)

        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("sk-... or leave empty if no auth needed")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("API Key:", self.api_key_input)

        self.show_key_check = QCheckBox("Show API Key")
        self.show_key_check.toggled.connect(self._toggle_key_visibility)
        form_layout.addRow("", self.show_key_check)

        self.models_input = QLineEdit()
        self.models_input.setPlaceholderText("model1, model2, model3")
        form_layout.addRow("Models:", self.models_input)

        self.region_input = QLineEdit()
        self.region_input.setPlaceholderText("e.g., eastus, us-west (optional)")
        form_layout.addRow("Region:", self.region_input)

        layout.addWidget(form_group)

        # ── Quick Templates — wrapping grid ─────────────────────
        templates_group = QGroupBox("Quick Templates (click to auto-fill)")
        templates_group.setStyleSheet("""
            QGroupBox {
                font-weight: 600;
                font-size: 13px;
                color: #0f172a;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 18px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 6px; }
        """)

        # Use a grid layout (3 columns) so buttons never overflow or clip
        grid = QGridLayout(templates_group)
        grid.setContentsMargins(12, 10, 12, 12)
        grid.setSpacing(8)

        templates = [
            ("OpenAI TTS",    "https://api.openai.com/v1/audio/speech"),
            ("OpenAI Whisper","https://api.openai.com/v1/audio/transcriptions"),
            ("OpenAI Chat",   "https://api.openai.com/v1/chat/completions"),
            ("Anthropic",     "https://api.anthropic.com/v1/messages"),
            ("Deepgram",      "https://api.deepgram.com/v1/listen"),
            ("Groq",          "https://api.groq.com/openai/v1/chat/completions"),
            ("OpenRouter",    "https://openrouter.ai/api/v1/chat/completions"),
            ("ElevenLabs",    "https://api.elevenlabs.io/v1/text-to-speech"),
            ("Together AI",   "https://api.together.xyz/v1/chat/completions"),
        ]

        COLS = 3
        for i, (name, url) in enumerate(templates):
            btn = QPushButton(name)
            btn.setStyleSheet("""
                QPushButton {
                    padding: 7px 14px;
                    background: #eef2ff;
                    border: 1px solid #c7d2fe;
                    border-radius: 7px;
                    font-size: 13px;
                    font-weight: 500;
                    color: #4f46e5;
                }
                QPushButton:hover { background: #e0e7ff; border-color: #a5b4fc; }
                QPushButton:pressed { background: #c7d2fe; }
            """)
            # Each button stretches to fill its grid cell equally
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(lambda checked, u=url: self._fill_template(u))
            grid.addWidget(btn, i // COLS, i % COLS)

        # Make all columns share space equally
        for col in range(COLS):
            grid.setColumnStretch(col, 1)

        layout.addWidget(templates_group)

        # ── Footer buttons ───────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumWidth(90)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        self.add_btn = QPushButton("Add Provider")
        self.add_btn.setMinimumWidth(130)
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #6366f1;
                color: white;
                padding: 10px 28px;
                font-weight: 600;
                font-size: 13px;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #4f46e5; }
            QPushButton:pressed { background-color: #4338ca; }
        """)
        self.add_btn.clicked.connect(self._on_add)
        btn_row.addWidget(self.add_btn)

        layout.addLayout(btn_row)

    def _toggle_key_visibility(self, checked):
        self.api_key_input.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )

    def _on_endpoint_changed(self, text):
        if text.startswith("http"):
            self._on_detect()

    def _on_detect(self):
        endpoint = self.endpoint_input.text().strip()
        if not endpoint:
            return

        self.detected_info = detect_provider_type(endpoint)
        if self.detected_info:
            service = self.detected_info["service"]
            ptype = self.detected_info["type"]
            models = self.detected_info["models"]

            idx = {"tts": 0, "stt": 1, "llm": 2}.get(ptype, 2)
            self.type_combo.setCurrentIndex(idx)
            self.models_input.setText(", ".join(models))
            self.detect_status.setText(f"Detected: {service.replace('_', ' ').title()}")
            self.detect_status.setStyleSheet("color: #059669; font-weight: 600;")

            if not self.name_input.text():
                self.name_input.setText(service.replace("_", " ").title())
        else:
            self.detect_status.setText("Unknown endpoint - please select type manually")
            self.detected_info = None

    def _fill_template(self, url: str):
        self.endpoint_input.setText(url)
        self._on_detect()

    def _on_add(self):
        name = self.name_input.text().strip()
        endpoint = self.endpoint_input.text().strip()
        api_key = self.api_key_input.text().strip()
        models_text = self.models_input.text().strip()
        region = self.region_input.text().strip()

        if not name:
            QMessageBox.warning(self, "Required", "Please enter a provider name.")
            return
        if not endpoint:
            QMessageBox.warning(self, "Required", "Please enter an endpoint URL.")
            return
        if not endpoint.startswith("http"):
            QMessageBox.warning(self, "Invalid URL", "Endpoint must start with http:// or https://")
            return

        type_map = {0: "tts", 1: "stt", 2: "llm"}
        ptype = type_map[self.type_combo.currentIndex()]

        models = [m.strip() for m in models_text.split(",") if m.strip()] if models_text else ["default"]

        config = {}
        if region:
            config["region"] = region

        provider = CustomProvider(
            id=str(uuid.uuid4())[:8],
            name=name, provider_type=ptype, api_key=api_key,
            endpoint=endpoint, models=models, config=config,
        )

        self.manager.add_provider(provider)
        self.provider_added.emit(provider)
        QMessageBox.information(self, "Added!", f"Provider '{name}' ({ptype.upper()}) added successfully!")
        self.accept()


class EditProviderDialog(QDialog):
    """Dialog for editing an existing provider."""

    provider_updated = pyqtSignal(object)

    def __init__(self, provider: CustomProvider, parent=None):
        super().__init__(parent)
        self.provider = provider
        self.setWindowTitle("Edit Provider")
        self.setMinimumSize(480, 450)
        self._setup_ui()
        self._fill_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        form_group = QGroupBox("Provider Details")
        form_layout = QFormLayout(form_group)

        self.name_input = QLineEdit()
        form_layout.addRow("Name:", self.name_input)

        self.endpoint_input = QLineEdit()
        form_layout.addRow("Endpoint URL:", self.endpoint_input)

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("API Key:", self.api_key_input)

        self.show_key_check = QCheckBox("Show API Key")
        self.show_key_check.toggled.connect(lambda c: self.api_key_input.setEchoMode(
            QLineEdit.EchoMode.Normal if c else QLineEdit.EchoMode.Password
        ))
        form_layout.addRow("", self.show_key_check)

        self.models_input = QLineEdit()
        form_layout.addRow("Models:", self.models_input)

        layout.addWidget(form_group)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save Changes")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #6366f1;
                color: white;
                padding: 10px 28px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #4f46e5; }
        """)
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)

    def _fill_data(self):
        self.name_input.setText(self.provider.name)
        self.endpoint_input.setText(self.provider.endpoint)
        self.api_key_input.setText(self.provider.api_key)
        self.models_input.setText(", ".join(self.provider.models))

    def _on_save(self):
        self.provider.name = self.name_input.text().strip()
        self.provider.endpoint = self.endpoint_input.text().strip()
        self.provider.api_key = self.api_key_input.text().strip()
        models_text = self.models_input.text().strip()
        self.provider.models = [m.strip() for m in models_text.split(",") if m.strip()] if models_text else ["default"]

        self.provider_updated.emit(self.provider)
        self.accept()


# ──────────────────────────────────────────────────────────────────────────────
# Main API Tab — Full Page Scroll
# ──────────────────────────────────────────────────────────────────────────────
class APITab(QWidget):
    """Dedicated tab for managing custom API providers — full page scroll."""

    def __init__(self):
        super().__init__()
        self.dynamic_manager = DynamicProviderManager()
        self._setup_ui()
        self._refresh()

    def _setup_ui(self):
        # Main layout contains just the scroll area
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: #f1f5f9; }")

        # Content widget
        content = QWidget()
        content.setStyleSheet("background: #f1f5f9;")
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(32, 28, 32, 40)
        self.content_layout.setSpacing(20)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ── Section: Header ──────────────────────────────────────
        header_card = Card("API Provider Manager")
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(20, 16, 20, 16)

        title_col = QVBoxLayout()
        title = QLabel("API Provider Manager")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #0f172a;")
        title_col.addWidget(title)

        subtitle = QLabel("Add any TTS, STT, or LLM API provider. They will appear in the corresponding test tabs.")
        subtitle.setStyleSheet("font-size: 13px; color: #64748b; margin-top: 4px;")
        title_col.addWidget(subtitle)

        header_layout.addLayout(title_col, stretch=1)

        self.add_btn = QPushButton("+ Add New Provider")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #6366f1;
                color: white;
                padding: 12px 28px;
                font-weight: 600;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #4f46e5; }
        """)
        self.add_btn.clicked.connect(self._on_add_provider)
        header_layout.addWidget(self.add_btn)

        self.content_layout.addWidget(header_card)

        # ── Section: Filter ───────────────────────────────────────
        filter_card = Card("")
        filter_layout = QHBoxLayout(filter_card)
        filter_layout.setContentsMargins(20, 12, 20, 12)

        filter_layout.addWidget(QLabel("Filter:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All Providers", "TTS Only", "STT Only", "LLM Only"])
        self.filter_combo.currentIndexChanged.connect(self._refresh)
        self.filter_combo.setMinimumWidth(180)
        filter_layout.addWidget(self.filter_combo)
        filter_layout.addStretch()

        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: #94a3b8; font-size: 13px;")
        filter_layout.addWidget(self.stats_label)

        self.content_layout.addWidget(filter_card)

        # ── Section: Provider Cards ───────────────────────────────
        providers_card = Card("Providers")
        self.providers_layout = QVBoxLayout(providers_card)
        self.providers_layout.setContentsMargins(20, 16, 20, 20)
        self.providers_layout.setSpacing(10)
        self.providers_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.content_layout.addWidget(providers_card)

        # Stretch at bottom
        self.content_layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _refresh(self):
        """Refresh the provider cards display."""
        # Clear existing cards
        while self.providers_layout.count():
            item = self.providers_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        filter_map = {0: "all", 1: "tts", 2: "stt", 3: "llm"}
        filter_type = filter_map.get(self.filter_combo.currentIndex(), "all")

        all_providers = self.dynamic_manager.get_all()
        if filter_type == "all":
            providers = all_providers
        else:
            providers = [p for p in all_providers if p.provider_type == filter_type]

        if not providers:
            empty_label = QLabel(
                "No custom providers yet.\n\n"
                "Click '+ Add New Provider' to connect your first API.\n\n"
                "You can add providers like:\n"
                "  • OpenAI (TTS, Whisper, Chat)\n"
                "  • Google Cloud (STT, TTS)\n"
                "  • Azure Speech\n"
                "  • Deepgram, Groq, OpenRouter\n"
                "  • Any custom endpoint"
            )
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet("""
                QLabel {
                    color: #94a3b8;
                    font-size: 15px;
                    padding: 60px 40px;
                }
            """)
            self.providers_layout.addWidget(empty_label)
        else:
            for provider in providers:
                card = ProviderCard(provider, self)
                self.providers_layout.addWidget(card)

        self.providers_layout.addStretch()

        tts_count = len([p for p in all_providers if p.provider_type == "tts"])
        stt_count = len([p for p in all_providers if p.provider_type == "stt"])
        llm_count = len([p for p in all_providers if p.provider_type == "llm"])
        self.stats_label.setText(
            f"Total: {len(all_providers)} providers  ·  TTS: {tts_count}  ·  STT: {stt_count}  ·  LLM: {llm_count}"
        )

    def _on_add_provider(self):
        dialog = AddProviderDialog(self.dynamic_manager, self)
        dialog.provider_added.connect(lambda _: self._refresh())
        dialog.exec()
