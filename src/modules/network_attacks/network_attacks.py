import os
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
    QLineEdit,
    QFormLayout,
    QInputDialog,
    QScrollArea,
    QSizePolicy,
)
from PyQt5.QtCore import Qt

SCRIPT_DIR = Path(__file__).resolve().parent / "scripts"


class NetworkAttacksModule(QWidget):
    """Network Attacks: ARP spoofing, traffic capture, MitM (Bettercap)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.scripts_dir = SCRIPT_DIR
        self.sudo_password: Optional[str] = None

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        header = QLabel("Network Attacks")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(16)
        scroll_layout.setContentsMargins(0, 0, 8, 0)
        scroll_layout.addWidget(self._build_arp_group())
        scroll_layout.addWidget(self._build_capture_group())
        scroll_layout.addWidget(self._build_mitm_group())
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)

        layout.addWidget(scroll)

        self.output = QTextBrowser()
        self.output.setMinimumHeight(220)
        self.output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.output, 1)

    def _ensure_sudo(self) -> Optional[str]:
        if self.sudo_password:
            return self.sudo_password
        from PyQt5.QtWidgets import QLineEdit as QLE
        password, ok = QInputDialog.getText(
            self, "Sudo required", "These tools need root. Enter sudo password:",
            QLE.Password,
        )
        if ok and password:
            self.sudo_password = password
            return password
        return None

    def _build_arp_group(self) -> QGroupBox:
        group = QGroupBox("ARP Spoofing")
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        v = QVBoxLayout(group)
        v.setSpacing(10)
        desc = QLabel("Poison ARP so traffic between target and gateway flows through you. Requires arpspoof (dsniff).")
        desc.setWordWrap(True)
        v.addWidget(desc)
        form = QFormLayout()
        self.arp_interface = QLineEdit()
        self.arp_interface.setPlaceholderText("e.g. eth0")
        self.arp_interface.setMinimumWidth(200)
        self.arp_target = QLineEdit()
        self.arp_target.setPlaceholderText("e.g. 192.168.1.100")
        self.arp_target.setMinimumWidth(200)
        self.arp_gateway = QLineEdit()
        self.arp_gateway.setPlaceholderText("e.g. 192.168.1.1")
        self.arp_gateway.setMinimumWidth(200)
        form.addRow("Interface:", self.arp_interface)
        form.addRow("Target IP:", self.arp_target)
        form.addRow("Gateway IP:", self.arp_gateway)
        v.addLayout(form)
        h = QHBoxLayout()
        start_btn = QPushButton("Start ARP Spoofing")
        stop_btn = QPushButton("Stop ARP Spoofing")
        start_btn.clicked.connect(self._run_arp_start)
        stop_btn.clicked.connect(self._run_arp_stop)
        h.addWidget(start_btn)
        h.addWidget(stop_btn)
        h.addStretch()
        v.addLayout(h)
        return group

    def _build_capture_group(self) -> QGroupBox:
        group = QGroupBox("Traffic Capture")
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        v = QVBoxLayout(group)
        v.setSpacing(10)
        desc = QLabel("Capture packets on an interface with tcpdump. Saves to reports/network_attacks/.")
        desc.setWordWrap(True)
        v.addWidget(desc)
        form = QFormLayout()
        self.capture_interface = QLineEdit()
        self.capture_interface.setPlaceholderText("e.g. eth0")
        self.capture_interface.setMinimumWidth(200)
        form.addRow("Interface:", self.capture_interface)
        v.addLayout(form)
        h = QHBoxLayout()
        start_btn = QPushButton("Start Capture")
        stop_btn = QPushButton("Stop Capture")
        start_btn.clicked.connect(self._run_capture_start)
        stop_btn.clicked.connect(self._run_capture_stop)
        h.addWidget(start_btn)
        h.addWidget(stop_btn)
        h.addStretch()
        v.addLayout(h)
        return group

    def _build_mitm_group(self) -> QGroupBox:
        group = QGroupBox("MitM (Bettercap)")
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        v = QVBoxLayout(group)
        v.setSpacing(10)
        desc = QLabel("Start Bettercap on an interface (runs in background). Stop when done.")
        desc.setWordWrap(True)
        v.addWidget(desc)
        form = QFormLayout()
        self.mitm_interface = QLineEdit()
        self.mitm_interface.setPlaceholderText("e.g. eth0")
        self.mitm_interface.setMinimumWidth(200)
        form.addRow("Interface:", self.mitm_interface)
        v.addLayout(form)
        h = QHBoxLayout()
        start_btn = QPushButton("Start Bettercap")
        stop_btn = QPushButton("Stop Bettercap")
        start_btn.clicked.connect(self._run_bettercap_start)
        stop_btn.clicked.connect(self._run_bettercap_stop)
        h.addWidget(start_btn)
        h.addWidget(stop_btn)
        h.addStretch()
        v.addLayout(h)
        return group

    def _run(self, script_name: str, args: Optional[List[str]] = None, need_sudo: bool = True) -> None:
        path = self.scripts_dir / script_name
        if not path.exists():
            self._append(f"[!] Script not found: {path}")
            return
        if need_sudo and os.geteuid() != 0 and not self._ensure_sudo():
            return
        cmd = ["bash", str(path), *(args or [])]
        if need_sudo and os.geteuid() != 0:
            cmd = ["sudo", "-S", "bash", str(path), *(args or [])]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
                input=(self.sudo_password or "") + "\n" if need_sudo and os.geteuid() != 0 else None,
            )
            out = (res.stdout or "").strip()
            err = (res.stderr or "").strip()
            if res.returncode == 0:
                self._append(out or f"[+] {script_name} completed.")
            else:
                self._append(f"[!] {script_name} failed ({res.returncode}):\n{err or out}")
        except subprocess.TimeoutExpired:
            self._append(f"[!] {script_name} timed out.")
        except Exception as exc:
            self._append(f"[!] Error: {exc}")

    def _run_arp_start(self) -> None:
        iface = self.arp_interface.text().strip()
        target = self.arp_target.text().strip()
        gateway = self.arp_gateway.text().strip()
        if not iface or not target or not gateway:
            self._append("[!] Enter interface, target IP, and gateway IP.")
            return
        self._run("arp_spoof_start.sh", [iface, target, gateway])

    def _run_arp_stop(self) -> None:
        self._run("arp_spoof_stop.sh")

    def _run_capture_start(self) -> None:
        iface = self.capture_interface.text().strip()
        if not iface:
            self._append("[!] Enter interface (e.g. eth0).")
            return
        self._run("capture_start.sh", [iface])

    def _run_capture_stop(self) -> None:
        self._run("capture_stop.sh")

    def _run_bettercap_start(self) -> None:
        iface = self.mitm_interface.text().strip()
        if not iface:
            self._append("[!] Enter interface (e.g. eth0).")
            return
        self._run("bettercap_start.sh", [iface])

    def _run_bettercap_stop(self) -> None:
        self._run("bettercap_stop.sh")

    def _append(self, text: str) -> None:
        self.output.append(text)
        self.output.ensureCursorVisible()
