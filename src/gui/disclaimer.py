import json
from pathlib import Path
from typing import Dict

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)


STATE_FILE = Path(__file__).resolve().parents[2] / "config" / "user_state.json"


class DisclaimerDialog(QDialog):
    """Displays the legal and ethical disclaimer before the user accesses the GUI."""

    DISCLAIMER_TEXT = (
        "Automated Red Teaming Assistant (ARTA) is an educational tool designed for "
        "authorized security testing in controlled environments. By continuing, you confirm "
        "that you:\n\n"
        "• Have explicit permission to assess the targets you will interact with\n"
        "• Understand and will comply with all applicable laws and regulations\n"
        "• Accept full responsibility for any actions performed using this application\n\n"
        "Misuse of this software may lead to legal consequences. Always follow responsible "
        "disclosure practices."
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Legal & Ethical Disclaimer")
        self.setModal(True)
        self.resize(520, 340)

        layout = QVBoxLayout(self)

        heading = QLabel("Ethical Use Confirmation")
        heading_font = QFont()
        heading_font.setPointSize(14)
        heading_font.setBold(True)
        heading.setFont(heading_font)
        heading.setAlignment(Qt.AlignCenter)

        message = QTextBrowser()
        message.setPlainText(self.DISCLAIMER_TEXT)
        message.setReadOnly(True)
        message.setMinimumHeight(220)

        self.agree_checkbox = QCheckBox("I agree and wish to continue responsibly.")
        self.agree_checkbox.stateChanged.connect(self._update_accept_state)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setEnabled(False)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(heading)
        layout.addWidget(message)
        layout.addWidget(self.agree_checkbox)
        layout.addWidget(buttons)

    def _update_accept_state(self, _state: int) -> None:
        """Enable the OK button only when the acknowledgement is checked."""
        dialog_buttons: QDialogButtonBox = self.findChild(QDialogButtonBox)
        if dialog_buttons:
            ok_button = dialog_buttons.button(QDialogButtonBox.Ok)
            if ok_button:
                ok_button.setEnabled(self.agree_checkbox.isChecked())


def _ensure_state_file() -> Dict[str, bool]:
    """Return the persisted user state, initialising the file if needed."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if STATE_FILE.exists():
        try:
            with STATE_FILE.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _persist_state(data: Dict[str, bool]) -> None:
    """Persist the user state to disk."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with STATE_FILE.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


def ensure_disclaimer_acknowledged(parent: QWidget | None = None) -> bool:
    """Show the disclaimer once unless the user has already accepted it."""
    state = _ensure_state_file()
    if state.get("disclaimerAccepted", False):
        return True

    dialog = DisclaimerDialog(parent)
    if dialog.exec_() == QDialog.Accepted and dialog.agree_checkbox.isChecked():
        state["disclaimerAccepted"] = True
        _persist_state(state)
        return True
    return False

