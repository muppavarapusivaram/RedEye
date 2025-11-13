from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
    QDialog,
    QMessageBox,
)

from core.ai_manager import AIManager


class AIConfigDialog(QDialog):
    """Inline dialog for configuring AI provider and API key."""

    def __init__(self, ai_manager: AIManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ai_manager = ai_manager
        self.setWindowTitle("Configure AI Provider")
        self.setFixedSize(420, 180)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.chatgpt_radio = QRadioButton("ChatGPT (OpenAI)")
        self.gemini_radio = QRadioButton("Gemini (Google)")

        current = ai_manager.settings.provider
        if current == "chatgpt":
            self.chatgpt_radio.setChecked(True)
        elif current == "gemini":
            self.gemini_radio.setChecked(True)
        else:
            self.chatgpt_radio.setChecked(True)

        form.addRow("Select Provider:", self.chatgpt_radio)
        form.addRow("", self.gemini_radio)

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setPlaceholderText("Enter API key")
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        if ai_manager.settings.api_key:
            self.api_key_edit.setText(ai_manager.settings.api_key)

        form.addRow("API Key:", self.api_key_edit)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #ffaeaa; font-size: 11px;")
        layout.addWidget(self.status_label)

        buttons = QHBoxLayout()
        save_button = QPushButton("Save")
        cancel_button = QPushButton("Cancel")
        clear_button = QPushButton("Clear")

        save_button.clicked.connect(self._save)
        cancel_button.clicked.connect(self.close)
        clear_button.clicked.connect(self._clear)

        buttons.addWidget(save_button)
        buttons.addWidget(cancel_button)
        buttons.addStretch()
        buttons.addWidget(clear_button)

        layout.addLayout(form)
        layout.addLayout(buttons)

    def _save(self) -> None:
        provider = "chatgpt" if self.chatgpt_radio.isChecked() else "gemini"
        api_key = self.api_key_edit.text().strip()
        if not api_key:
            self.status_label.setText("Please enter an API key.")
            self.status_label.setStyleSheet("color: #ffaeaa; font-size: 11px;")
            return

        # Validate API key
        self.status_label.setText("Validating API key, please wait...")
        self.status_label.setStyleSheet("color: #ffd700; font-size: 11px;")
        QApplication.processEvents()  # Update UI immediately
        
        is_valid, message = self.ai_manager.validate_api_key(provider, api_key)
        
        if is_valid:
            self.ai_manager.configure(provider, api_key)
            self.status_label.setText("")
            QMessageBox.information(self, "Success", f"API key validated and saved successfully!\n\n{message}")
            self.accept()
        else:
            self.status_label.setText(f"Validation failed: {message}")
            self.status_label.setStyleSheet("color: #ffaeaa; font-size: 11px;")

    def _clear(self) -> None:
        self.api_key_edit.clear()
        self.ai_manager.clear()
        self.accept()


class DashboardTab(QWidget):
    """Landing page summarising project status, recent activity, and quick actions."""

    def __init__(self, ai_manager: AIManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ai_manager = ai_manager
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        hero = QGroupBox("Automated Red Teaming Assistant (ARTA)")
        hero_layout = QVBoxLayout(hero)
        hero_copy = QLabel(
            "Centralised interface for orchestrating reconnaissance, vulnerability assessments, "
            "and reporting workflows. This preview focuses on the GUI scaffolding; backend tool "
            "integration and AI workflows will be added in later phases."
        )
        hero_copy.setWordWrap(True)
        hero_layout.addWidget(hero_copy)

        status_group = QGroupBox("Project Roadmap")
        status_layout = QVBoxLayout(status_group)
        milestones = QListWidget()
        for milestone in [
            "Phase 1 – GUI foundation (in progress)",
            "Phase 2 – Tool orchestration (up next)",
            "Phase 3 – Gemini AI integration",
            "Phase 4 – UX polish & feedback",
            "Phase 5 – Testing & documentation",
        ]:
            item = QListWidgetItem(milestone)
            milestones.addItem(item)
        status_layout.addWidget(milestones)

        quick_actions = QGroupBox("Quick Actions")
        quick_layout = QHBoxLayout(quick_actions)
        quick_layout.addWidget(QPushButton("Create New Project"))
        quick_layout.addWidget(QPushButton("Open Existing Project"))
        quick_layout.addWidget(QPushButton("View Audit Log"))
        ai_button = QPushButton("Use AI…")
        ai_button.clicked.connect(self._open_ai_config)
        quick_layout.addWidget(ai_button)

        # AI Status indicator
        ai_status_group = QGroupBox("AI Configuration Status")
        ai_status_layout = QVBoxLayout(ai_status_group)
        self.ai_status_label = QLabel()
        self._update_ai_status()
        ai_status_layout.addWidget(self.ai_status_label)

        layout.addWidget(hero)
        layout.addWidget(status_group)
        layout.addWidget(quick_actions)
        layout.addWidget(ai_status_group)
        layout.addStretch()

    def _update_ai_status(self) -> None:
        """Update the AI status label based on current configuration."""
        self.ai_manager._load()  # Reload to ensure we have latest settings
        is_enabled = self.ai_manager.is_enabled()
        provider = self.ai_manager.provider_name()
        
        if is_enabled:
            self.ai_status_label.setText(
                f"✓ AI is <b>ACTIVE</b><br>"
                f"Provider: <b>{provider}</b><br>"
                f"API Key: Configured (length: {len(self.ai_manager.settings.api_key) if self.ai_manager.settings.api_key else 0} chars)"
            )
            self.ai_status_label.setStyleSheet("color: #a9f5d0; font-size: 12px;")
        else:
            self.ai_status_label.setText(
                "✗ AI is <b>INACTIVE</b><br>"
                "Click 'Use AI…' to configure ChatGPT or Gemini API."
            )
            self.ai_status_label.setStyleSheet("color: #ffaeaa; font-size: 12px;")

    def _open_ai_config(self) -> None:
        dialog = AIConfigDialog(self.ai_manager, self)
        dialog.setWindowModality(Qt.ApplicationModal)
        if dialog.exec_() == QDialog.Accepted:
            # Reload settings and update status after configuration
            self.ai_manager._load()
            self._update_ai_status()


