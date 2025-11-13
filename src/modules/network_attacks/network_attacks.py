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

print(f"[DEBUG] Loading NetworkAttacksModule from {__file__}")


class NetworkAttacksModule(QWidget):
    """Network Attacks workflows (e.g., ARP spoofing)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.scripts_dir = Path(__file__).resolve().parent / "scripts"

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        header = QLabel("Network Attacks")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header)

        layout.addWidget(self._build_arp_group())
        layout.addWidget(self._build_capture_group())
        layout.addWidget(self._build_mitm_group())

        self.output = QTextBrowser()
        self.output.setMinimumHeight(200)
        layout.addWidget(self.output)
        layout.addStretch()

    def _build_arp_group(self) -> QGroupBox:
        group = QGroupBox("ARP Spoofing")
        v = QVBoxLayout(group)
        v.addWidget(QLabel("Start/stop ARP spoofing with configured gateway/target."))
        h = QHBoxLayout()
        start_btn = QPushButton("Start ARP Spoofing")
        stop_btn = QPushButton("Stop ARP Spoofing")
        h.addWidget(start_btn)
        h.addWidget(stop_btn)
        h.addStretch()
        start_btn.clicked.connect(lambda: self._run("arp_spoof_start.sh"))
        stop_btn.clicked.connect(lambda: self._run("arp_spoof_stop.sh"))
        v.addLayout(h)
        return group

    def _build_capture_group(self) -> QGroupBox:
        group = QGroupBox("Traffic Capture")
        v = QVBoxLayout(group)
        v.addWidget(QLabel("Start/stop traffic capture during attacks."))
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

    def _build_mitm_group(self) -> QGroupBox:
        group = QGroupBox("MitM Tools")
        v = QVBoxLayout(group)
        v.addWidget(QLabel("Launch/stop tools like Bettercap for MitM operations."))
        h = QHBoxLayout()
        start_btn = QPushButton("Start Bettercap")
        stop_btn = QPushButton("Stop Bettercap")
        h.addWidget(start_btn)
        h.addWidget(stop_btn)
        h.addStretch()
        start_btn.clicked.connect(lambda: self._run("bettercap_start.sh"))
        stop_btn.clicked.connect(lambda: self._run("bettercap_stop.sh"))
        v.addLayout(h)
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


