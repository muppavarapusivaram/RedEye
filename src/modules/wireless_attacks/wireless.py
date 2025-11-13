import subprocess
from pathlib import Path
from typing import Optional, List

from PyQt5.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QWidget,
    QGroupBox,
    QPushButton,
    QHBoxLayout,
    QTextBrowser,
)
from PyQt5.QtCore import Qt

print(f"[DEBUG] Loading WirelessAttacksModule from {__file__}")


class WirelessAttacksModule(QWidget):
    """Wireless Attacks workflows (Aircrack-ng)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.scripts_dir = Path(__file__).resolve().parent / "scripts"

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        header = QLabel("Wireless Attacks")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header)

        layout.addWidget(self._build_interface_group())
        layout.addWidget(self._build_capture_group())
        layout.addWidget(self._build_attack_group())
        layout.addWidget(self._build_cracking_group())

        self.output = QTextBrowser()
        self.output.setMinimumHeight(200)
        layout.addWidget(self.output)
        layout.addStretch()

    def _build_interface_group(self) -> QGroupBox:
        group = QGroupBox("Interface Management")
        v = QVBoxLayout(group)
        v.addWidget(QLabel("Enable/disable monitor mode and list interfaces."))
        h = QHBoxLayout()
        list_btn = QPushButton("List Interfaces")
        enable_btn = QPushButton("Enable Monitor Mode")
        disable_btn = QPushButton("Disable Monitor Mode")
        h.addWidget(list_btn)
        h.addWidget(enable_btn)
        h.addWidget(disable_btn)
        h.addStretch()
        list_btn.clicked.connect(lambda: self._run("list_interfaces.sh"))
        enable_btn.clicked.connect(lambda: self._run("airmon_start.sh"))
        disable_btn.clicked.connect(lambda: self._run("airmon_stop.sh"))
        v.addLayout(h)
        return group

    def _build_capture_group(self) -> QGroupBox:
        group = QGroupBox("Capture")
        v = QVBoxLayout(group)
        v.addWidget(QLabel("Start/stop packet capture for handshake collection."))
        h = QHBoxLayout()
        start_btn = QPushButton("Start Capture")
        stop_btn = QPushButton("Stop Capture")
        h.addWidget(start_btn)
        h.addWidget(stop_btn)
        h.addStretch()
        start_btn.clicked.connect(lambda: self._run("capture_start.sh"))
        stop_btn.clicked.connect(lambda: self._run("capture_stop.sh"))
        v.addLayout(h)
        return group

    def _build_attack_group(self) -> QGroupBox:
        group = QGroupBox("Attacks")
        v = QVBoxLayout(group)
        v.addWidget(QLabel("Common wireless attack actions."))
        deauth_btn = QPushButton("Deauth Attack")
        deauth_btn.clicked.connect(lambda: self._run("deauth.sh"))
        v.addWidget(deauth_btn, alignment=Qt.AlignLeft)
        return group

    def _build_cracking_group(self) -> QGroupBox:
        group = QGroupBox("Cracking")
        v = QVBoxLayout(group)
        v.addWidget(QLabel("Crack WPA/WPA2 handshakes with Aircrack-ng."))
        crack_btn = QPushButton("Crack Handshake")
        crack_btn.clicked.connect(lambda: self._run("crack_handshake.sh"))
        v.addWidget(crack_btn, alignment=Qt.AlignLeft)
        return group

    def _run(self, script_name: str, args: Optional[List[str]] = None) -> None:
        path = self.scripts_dir / script_name
        if not path.exists():
            self._append(f"[!] Script not found: {path}")
            return
        try:
            res = subprocess.run(["bash", str(path), *(args or [])], capture_output=True, text=True, timeout=600)
            out = res.stdout.strip()
            err = res.stderr.strip()
            if res.returncode == 0:
                self._append(out or f"[+] {script_name} completed.")
            else:
                self._append(f"[!] {script_name} failed ({res.returncode}):\n{err or out}")
        except subprocess.TimeoutExpired:
            self._append(f"[!] {script_name} timed out.")
        except Exception as exc:
            self._append(f"[!] Error running {script_name}: {exc}")

    def _append(self, text: str) -> None:
        self.output.append(text)
        self.output.ensureCursorVisible()


