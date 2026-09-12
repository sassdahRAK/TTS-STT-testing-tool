"""
Comparison Tab - Side-by-side comparison of all test results.
Modern dashboard layout with full-page scrolling.
"""

import csv
import json
import os
from datetime import datetime
from typing import Optional
from collections import defaultdict

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QTextEdit, QMessageBox, QFileDialog, QComboBox, QSpinBox,
    QTabWidget, QSplitter, QDoubleSpinBox, QScrollArea
)
from PyQt6.QtCore import Qt

from config import load_config
from nemo_scoring import get_scorer
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


# ──────────────────────────────────────────────────────────────────────────────
# Main Comparison Tab — Full Page Scroll
# ──────────────────────────────────────────────────────────────────────────────
class ComparisonTab(QWidget):
    """Tab for comparing results across all tests — full page scroll."""

    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.scorer = get_scorer()
        self.test_history = []
        self._setup_ui()

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

        # ── Card 1: Controls & Stats ─────────────────────────────
        controls_card = Card("Controls & Statistics")
        controls_layout = QVBoxLayout(controls_card)
        controls_layout.setContentsMargins(20, 16, 20, 20)
        controls_layout.setSpacing(12)

        # Controls row
        controls_row = QHBoxLayout()
        controls_row.setSpacing(10)

        self.export_json_btn = QPushButton("Export JSON")
        self.export_json_btn.setStyleSheet("QPushButton { background-color: #eef2ff; color: #4f46e5; padding: 10px 20px; }")
        self.export_json_btn.clicked.connect(self._on_export_json)
        controls_row.addWidget(self.export_json_btn)

        self.export_csv_btn = QPushButton("Export CSV")
        self.export_csv_btn.setStyleSheet("QPushButton { background-color: #ecfdf5; color: #059669; padding: 10px 20px; }")
        self.export_csv_btn.clicked.connect(self._on_export_csv)
        controls_row.addWidget(self.export_csv_btn)

        self.export_summary_btn = QPushButton("Summary")
        self.export_summary_btn.setStyleSheet("QPushButton { background-color: #faf5ff; color: #7c3aed; padding: 10px 20px; }")
        self.export_summary_btn.clicked.connect(self._on_export_summary)
        controls_row.addWidget(self.export_summary_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setStyleSheet("QPushButton { background-color: #fef2f2; color: #dc2626; padding: 10px 20px; }")
        self.clear_btn.clicked.connect(self._on_clear)
        controls_row.addWidget(self.clear_btn)

        self.refresh_btn = QPushButton("↻  Refresh")
        self.refresh_btn.setStyleSheet("""
            QPushButton { 
                background-color: #16a34a; 
                color: white; 
                padding: 10px 20px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #15803d; }
        """)
        self.refresh_btn.setToolTip("Reload and re-sort the results table and rankings")
        self.refresh_btn.clicked.connect(self._refresh_table)
        controls_row.addWidget(self.refresh_btn)

        controls_row.addStretch()

        controls_row.addWidget(QLabel("Filter:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All", "TTS", "STT", "LLM"])
        self.filter_combo.currentTextChanged.connect(self._refresh_table)
        controls_row.addWidget(self.filter_combo)

        controls_layout.addLayout(controls_row)

        # Stats row
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(12)

        self.stat_total = QLabel("Total: 0")
        self.stat_total.setStyleSheet("font-size: 15px; font-weight: 700; color: #0f172a; padding: 10px 20px; background: #f1f5f9; border-radius: 20px;")
        stats_layout.addWidget(self.stat_total)

        self.stat_tts = QLabel("TTS: 0")
        self.stat_tts.setStyleSheet("font-size: 15px; color: #059669; padding: 10px 20px; background: #ecfdf5; border-radius: 20px;")
        stats_layout.addWidget(self.stat_tts)

        self.stat_stt = QLabel("STT: 0")
        self.stat_stt.setStyleSheet("font-size: 15px; color: #2563eb; padding: 10px 20px; background: #eff6ff; border-radius: 20px;")
        stats_layout.addWidget(self.stat_stt)

        self.stat_llm = QLabel("LLM: 0")
        self.stat_llm.setStyleSheet("font-size: 15px; color: #7c3aed; padding: 10px 20px; background: #faf5ff; border-radius: 20px;")
        stats_layout.addWidget(self.stat_llm)

        stats_layout.addStretch()
        controls_layout.addLayout(stats_layout)

        self.content_layout.addWidget(controls_card)

        # ── Card 2: Results Table ────────────────────────────────
        results_card = Card("Test Results")
        results_layout = QVBoxLayout(results_card)
        results_layout.setContentsMargins(20, 16, 20, 20)

        self.results_table = QTableWidget(0, 10)
        self.results_table.setHorizontalHeaderLabels([
            "Timestamp", "Test Type", "Provider", "Model/Voice",
            "Status", "Duration (ms)", "CER", "Accuracy %",
            "Score (1-5)", "Notes"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setMinimumHeight(500)
        results_layout.addWidget(self.results_table)

        self.content_layout.addWidget(results_card)

        # ── Card 3: Manual Rating ────────────────────────────────
        score_card = Card("Manual Rating (TTS/LLM)")
        score_layout = QHBoxLayout(score_card)
        score_layout.setContentsMargins(20, 16, 20, 20)
        score_layout.setSpacing(10)

        self.nemo_status_label = QLabel()
        if hasattr(self.scorer, 'is_available') and self.scorer.is_available():
            self.nemo_status_label.setText("✓ NeMo Active")
            self.nemo_status_label.setStyleSheet("color: #059669; font-weight: 600; padding: 6px 16px; background: #ecfdf5; border-radius: 12px;")
        else:
            self.nemo_status_label.setText("⚠ Fallback Mode")
            self.nemo_status_label.setStyleSheet("color: #d97706; font-weight: 600; padding: 6px 16px; background: #fffbeb; border-radius: 12px;")
        score_layout.addWidget(self.nemo_status_label)

        score_layout.addStretch()

        score_layout.addWidget(QLabel("Provider:"))
        self.score_provider = QComboBox()
        self.score_provider.addItems(["OpenAI", "Google", "Azure", "Local", "Anthropic", "Custom"])
        score_layout.addWidget(self.score_provider)

        score_layout.addWidget(QLabel("Type:"))
        self.score_type = QComboBox()
        self.score_type.addItems(["TTS", "STT", "LLM"])
        score_layout.addWidget(self.score_type)

        score_layout.addWidget(QLabel("Score:"))
        self.score_value = QDoubleSpinBox()
        self.score_value.setRange(1.0, 5.0)
        self.score_value.setValue(3.0)
        self.score_value.setSingleStep(0.5)
        self.score_value.setSuffix(" / 5")
        score_layout.addWidget(self.score_value)

        score_layout.addWidget(QLabel("Notes:"))
        self.score_notes = QTextEdit()
        self.score_notes.setMaximumHeight(40)
        self.score_notes.setPlaceholderText("Why this score?")
        score_layout.addWidget(self.score_notes)

        self.add_score_btn = QPushButton("+ Add Rating")
        self.add_score_btn.setStyleSheet("QPushButton { background-color: #f59e0b; color: white; padding: 10px 22px; }")
        self.add_score_btn.clicked.connect(self._on_add_score)
        score_layout.addWidget(self.add_score_btn)

        self.content_layout.addWidget(score_card)

        # ── Card 4: Rankings ─────────────────────────────────────
        ranking_card = Card("Model Rankings")
        ranking_layout = QVBoxLayout(ranking_card)
        ranking_layout.setContentsMargins(20, 16, 20, 20)

        self.ranking_table = QTableWidget(0, 6)
        self.ranking_table.setHorizontalHeaderLabels([
            "Rank", "Provider", "Avg CER", "Avg Accuracy", "Avg Score (1-5)", "Tests"
        ])
        self.ranking_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.ranking_table.setMaximumHeight(180)
        ranking_layout.addWidget(self.ranking_table)

        self.content_layout.addWidget(ranking_card)

        self.content_layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def add_test_result(self, test_type: str, provider: str, model: str,
                        success: bool, duration_ms: float, notes: str = ""):
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "test_type": test_type, "provider": provider, "model": model,
            "success": success, "duration_ms": duration_ms, "score": None,
            "cer": None, "accuracy": None, "notes": notes,
        }
        self.test_history.append(entry)
        self._refresh_table()

    def add_stt_scored_result(self, provider: str, model: str,
                              reference: str, hypothesis: str,
                              success: bool, duration_ms: float, notes: str = ""):
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "test_type": "STT", "provider": provider, "model": model,
            "success": success, "duration_ms": duration_ms, "score": None,
            "cer": None, "accuracy": None, "notes": notes,
        }

        if success and reference and hypothesis:
            try:
                score_result = self.scorer.score(reference, hypothesis, use_cer=True)
                entry["cer"] = score_result.cer
                entry["accuracy"] = score_result.accuracy
                entry["score"] = min(5.0, max(1.0, score_result.accuracy * 5.0))
                entry["notes"] = f"CER: {score_result.cer_percent} | {notes}"
            except Exception as e:
                entry["notes"] = f"Scoring failed: {e} | {notes}"

        self.test_history.append(entry)
        self._refresh_table()

    def _refresh_table(self):
        filter_type = self.filter_combo.currentText()

        filtered = self.test_history
        if filter_type != "All":
            filtered = [e for e in filtered if e["test_type"] == filter_type]

        self.results_table.setRowCount(0)
        for entry in filtered:
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)
            self.results_table.setItem(row, 0, QTableWidgetItem(entry["timestamp"]))
            self.results_table.setItem(row, 1, QTableWidgetItem(entry["test_type"]))
            self.results_table.setItem(row, 2, QTableWidgetItem(entry["provider"]))
            self.results_table.setItem(row, 3, QTableWidgetItem(entry["model"]))
            status_item = QTableWidgetItem("Success" if entry["success"] else "Failed")
            status_item.setForeground(
                Qt.GlobalColor.darkGreen if entry["success"] else Qt.GlobalColor.red
            )
            self.results_table.setItem(row, 4, status_item)
            self.results_table.setItem(row, 5, QTableWidgetItem(f"{entry['duration_ms']:.0f}"))

            cer = entry.get("cer")
            if cer is not None:
                cer_item = QTableWidgetItem(f"{cer * 100:.1f}%")
                if cer <= 0.1:
                    cer_item.setBackground(Qt.GlobalColor.darkGreen)
                    cer_item.setForeground(Qt.GlobalColor.white)
                elif cer <= 0.25:
                    cer_item.setBackground(Qt.GlobalColor.yellow)
                else:
                    cer_item.setBackground(Qt.GlobalColor.red)
                    cer_item.setForeground(Qt.GlobalColor.white)
                self.results_table.setItem(row, 6, cer_item)
            else:
                self.results_table.setItem(row, 6, QTableWidgetItem("-"))

            acc = entry.get("accuracy")
            if acc is not None:
                self.results_table.setItem(row, 7, QTableWidgetItem(f"{acc * 100:.1f}%"))
            else:
                self.results_table.setItem(row, 7, QTableWidgetItem("-"))

            score_str = f"{entry['score']:.1f}" if entry["score"] is not None else "-"
            self.results_table.setItem(row, 8, QTableWidgetItem(score_str))

            self.results_table.setItem(row, 9, QTableWidgetItem(entry.get("notes", "")))

        self.stat_total.setText(f"Total Tests: {len(self.test_history)}")
        self.stat_tts.setText(f"TTS: {sum(1 for e in self.test_history if e['test_type'] == 'TTS')}")
        self.stat_stt.setText(f"STT: {sum(1 for e in self.test_history if e['test_type'] == 'STT')}")
        self.stat_llm.setText(f"LLM: {sum(1 for e in self.test_history if e['test_type'] == 'LLM')}")

        self._update_rankings()

    def _update_rankings(self):
        data = defaultdict(lambda: {"scores": [], "cers": [], "accuracies": []})
        for entry in self.test_history:
            key = f"{entry['provider']} ({entry['test_type']})"
            if entry.get("score") is not None:
                data[key]["scores"].append(entry["score"])
            if entry.get("cer") is not None:
                data[key]["cers"].append(entry["cer"])
            if entry.get("accuracy") is not None:
                data[key]["accuracies"].append(entry["accuracy"])

        ranked = []
        for key, vals in data.items():
            avg_score = sum(vals["scores"]) / len(vals["scores"]) if vals["scores"] else 0
            avg_cer = sum(vals["cers"]) / len(vals["cers"]) if vals["cers"] else None
            avg_acc = sum(vals["accuracies"]) / len(vals["accuracies"]) if vals["accuracies"] else None
            count = len(vals["scores"]) + len(vals["cers"])
            sort_val = avg_acc if avg_acc is not None else (avg_score / 5.0)
            ranked.append((key, avg_cer, avg_acc, avg_score, count, sort_val))

        ranked.sort(key=lambda x: x[5], reverse=True)

        self.ranking_table.setRowCount(0)
        for i, (key, avg_cer, avg_acc, avg_score, count, _) in enumerate(ranked):
            row = self.ranking_table.rowCount()
            self.ranking_table.insertRow(row)
            self.ranking_table.setItem(row, 0, QTableWidgetItem(f"#{i+1}"))
            self.ranking_table.setItem(row, 1, QTableWidgetItem(key))

            cer_str = f"{avg_cer * 100:.1f}%" if avg_cer is not None else "-"
            self.ranking_table.setItem(row, 2, QTableWidgetItem(cer_str))

            acc_str = f"{avg_acc * 100:.1f}%" if avg_acc is not None else "-"
            self.ranking_table.setItem(row, 3, QTableWidgetItem(acc_str))

            score_str = f"{avg_score:.1f}" if avg_score > 0 else "-"
            self.ranking_table.setItem(row, 4, QTableWidgetItem(score_str))

            self.ranking_table.setItem(row, 5, QTableWidgetItem(str(count)))

    def _on_add_score(self):
        provider = self.score_provider.currentText()
        test_type = self.score_type.currentText()
        score = self.score_value.value()
        notes = self.score_notes.toPlainText().strip()

        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "test_type": test_type, "provider": provider, "model": "-",
            "success": True, "duration_ms": 0, "score": score,
            "notes": notes or "Manual rating",
        }
        self.test_history.append(entry)
        self._refresh_table()
        self.score_notes.clear()
        QMessageBox.information(self, "Rating Added", f"Added {score}/5 rating for {provider} ({test_type})")

    def _on_export_json(self):
        if not self.test_history:
            QMessageBox.information(self, "No Data", "No test results to export.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Results to JSON", "model_test_results.json", "JSON Files (*.json)"
        )
        if not path:
            return

        export_data = {
            "export_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_results": len(self.test_history),
            "results": self.test_history,
            "summary": self._get_summary_data(),
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        QMessageBox.information(self, "Exported", f"Results saved to {path}")

    def _on_export_csv(self):
        if not self.test_history:
            QMessageBox.information(self, "No Data", "No test results to export.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Results to CSV", "model_test_results.csv", "CSV Files (*.csv)"
        )
        if not path:
            return

        fieldnames = [
            "timestamp", "test_type", "provider", "model", "success",
            "duration_ms", "cer", "accuracy", "score", "notes"
        ]

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for entry in self.test_history:
                row = dict(entry)
                if row.get("cer") is not None:
                    row["cer"] = f"{row['cer'] * 100:.2f}%"
                if row.get("accuracy") is not None:
                    row["accuracy"] = f"{row['accuracy'] * 100:.2f}%"
                writer.writerow(row)

        QMessageBox.information(self, "Exported", f"Results saved to {path}")

    def _on_export_summary(self):
        if not self.test_history:
            QMessageBox.information(self, "No Data", "No test results to export.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Summary Report", "model_test_summary.json", "JSON Files (*.json)"
        )
        if not path:
            return

        summary = self._get_summary_data()

        with open(path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        QMessageBox.information(self, "Exported", f"Summary saved to {path}")

    def _get_summary_data(self) -> dict:
        data = defaultdict(lambda: {
            "scores": [], "cers": [], "accuracies": [],
            "total_duration_ms": 0, "success_count": 0, "fail_count": 0
        })

        for entry in self.test_history:
            key = f"{entry['provider']} ({entry['test_type']})"
            if entry.get("score") is not None:
                data[key]["scores"].append(entry["score"])
            if entry.get("cer") is not None:
                data[key]["cers"].append(entry["cer"])
            if entry.get("accuracy") is not None:
                data[key]["accuracies"].append(entry["accuracy"])
            data[key]["total_duration_ms"] += entry.get("duration_ms", 0)
            if entry.get("success"):
                data[key]["success_count"] += 1
            else:
                data[key]["fail_count"] += 1

        providers = []
        for key, vals in data.items():
            avg_score = sum(vals["scores"]) / len(vals["scores"]) if vals["scores"] else None
            avg_cer = sum(vals["cers"]) / len(vals["cers"]) if vals["cers"] else None
            avg_acc = sum(vals["accuracies"]) / len(vals["accuracies"]) if vals["accuracies"] else None
            total_tests = vals["success_count"] + vals["fail_count"]
            providers.append({
                "provider": key, "total_tests": total_tests,
                "success_count": vals["success_count"], "fail_count": vals["fail_count"],
                "avg_cer": f"{avg_cer * 100:.2f}%" if avg_cer is not None else None,
                "avg_accuracy": f"{avg_acc * 100:.2f}%" if avg_acc is not None else None,
                "avg_score_1to5": f"{avg_score:.2f}" if avg_score is not None else None,
                "avg_duration_ms": round(vals["total_duration_ms"] / total_tests, 1) if total_tests > 0 else 0,
            })

        providers.sort(
            key=lambda x: (
                float(x["avg_accuracy"].replace("%", "")) if x["avg_accuracy"] else 0
            ),
            reverse=True
        )

        return {
            "export_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_results": len(self.test_history),
            "providers_ranked": providers,
        }

    def _on_clear(self):
        reply = QMessageBox.question(
            self, "Clear History", "Are you sure you want to clear all test results?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.test_history.clear()
            self._refresh_table()
