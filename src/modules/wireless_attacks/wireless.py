import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QWidget,
    QGroupBox,
    QPushButton,
    QHBoxLayout,
    QTextBrowser,
    QLineEdit,
    QMessageBox,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QSpinBox,
    QFormLayout,
    QScrollArea,
    QSizePolicy,
)

SCRIPT_DIR = Path(__file__).resolve().parent / "scripts"
REPORTS_DIR = Path(__file__).resolve().parents[3] / "reports" / "wireless_attacks"


@dataclass
class ScanResult:
    success: bool
    output: str
    error: Optional[str] = None


@dataclass
class TargetAp:
    num: int
    bssid: str
    channel: str
    essid: str


class ScriptWorker(QThread):
    """Run a script in background and emit output and result."""
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(ScanResult)

    def __init__(
        self,
        script_name: str,
        args: Optional[List[str]] = None,
        require_root: bool = False,
        sudo_password: Optional[str] = None,
    ):
        super().__init__()
        self.script_name = script_name
        self.args = args or []
        self.require_root = require_root
        self.sudo_password = sudo_password

    def run(self):
        script_path = SCRIPT_DIR / self.script_name
        if not script_path.exists():
            self.finished_signal.emit(ScanResult(False, "", f"Script not found: {script_path}"))
            return
        command: List[str]
        stdin_data: Optional[str] = None
        if self.require_root and os.geteuid() != 0:
            if not self.sudo_password:
                self.finished_signal.emit(ScanResult(False, "", "Operation cancelled (sudo required)."))
                return
            command = ["sudo", "-S", "bash", str(script_path), *self.args]
            stdin_data = self.sudo_password + "\n"
        else:
            command = ["bash", str(script_path), *self.args]
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE if stdin_data else None,
                text=True,
                bufsize=1,
            )
            if stdin_data:
                process.stdin.write(stdin_data)
                process.stdin.flush()
                process.stdin.close()
            output_lines = []
            for line in iter(process.stdout.readline, ""):
                if not line:
                    break
                line = line.rstrip()
                output_lines.append(line)
                self.output_signal.emit(line)
            process.wait()
            out = "\n".join(output_lines)
            if process.returncode != 0:
                self.finished_signal.emit(ScanResult(False, out, f"Exit code {process.returncode}"))
            else:
                self.finished_signal.emit(ScanResult(True, out, None))
        except FileNotFoundError:
            self.finished_signal.emit(ScanResult(False, "", f"Script not found: {script_path}"))
        except Exception as exc:
            self.finished_signal.emit(ScanResult(False, "", str(exc)))


class WirelessAttacksModule(QWidget):
    """Wireless Attacks workflows (Aircrack-ng)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.scripts_dir = SCRIPT_DIR
        self.sudo_password: Optional[str] = None
        self.monitor_interface: Optional[str] = None
        self.scan_worker: Optional[ScriptWorker] = None
        self.tool_worker: Optional[ScriptWorker] = None
        self.ap_list: List[TargetAp] = []
        self.cap_base: Optional[str] = None
        self.capture_log_path: Optional[str] = None
        self.selected_bssid: Optional[str] = None
        self.selected_channel: Optional[str] = None
        self.handshake_timer: Optional[QTimer] = None

        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        header = QLabel("Wireless Attacks")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header)

        # Scrollable area for the four groups so they use natural height and don't get compressed
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
        scroll_layout.addWidget(self._build_interface_group())
        scroll_layout.addWidget(self._build_capture_group())
        scroll_layout.addWidget(self._build_attack_group())
        scroll_layout.addWidget(self._build_cracking_group())
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)

        layout.addWidget(scroll)

        self.output = QTextBrowser()
        self.output.setMinimumHeight(220)
        self.output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.output, 1)

    def _build_interface_group(self) -> QGroupBox:
        group = QGroupBox("Interface Management")
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        v = QVBoxLayout(group)
        v.setSpacing(10)
        desc = QLabel(
            "List interfaces with airmon-ng, then enable monitor mode on one interface (e.g. wlan0). "
            "Use the monitor interface name (e.g. mon0) for capture and deauth."
        )
        desc.setWordWrap(True)
        v.addWidget(desc)
        v.addWidget(QLabel("Interface to put in monitor mode (e.g. wlan0):"))
        self.interface_edit = QLineEdit()
        self.interface_edit.setPlaceholderText("wlan0")
        self.interface_edit.setMinimumWidth(200)
        v.addWidget(self.interface_edit)

        h = QHBoxLayout()
        list_btn = QPushButton("List Interfaces")
        enable_btn = QPushButton("Enable Monitor Mode")
        disable_btn = QPushButton("Disable Monitor Mode")
        list_btn.clicked.connect(self._run_list_interfaces)
        enable_btn.clicked.connect(self._run_airmon_start)
        disable_btn.clicked.connect(self._run_airmon_stop)
        h.addWidget(list_btn)
        h.addWidget(enable_btn)
        h.addWidget(disable_btn)
        h.addStretch()
        v.addLayout(h)

        self.monitor_status = QLabel("Monitor interface: none")
        self.monitor_status.setStyleSheet("color: #ffaeaa;")
        v.addWidget(self.monitor_status)
        return group

    def _build_capture_group(self) -> QGroupBox:
        group = QGroupBox("Capture")
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        v = QVBoxLayout(group)
        v.setSpacing(10)
        desc = QLabel(
            "1) Click 'Scan for networks' to list APs (uses airodump-ng for ~15s). "
            "2) Select target by number and click 'Start monitoring'. "
            "3) Click 'Deauth attack' to force handshake. 4) When handshake is captured, stop capture. "
            "Capture files are saved under reports/wireless_attacks/."
        )
        desc.setWordWrap(True)
        v.addWidget(desc)

        scan_btn = QPushButton("Scan for networks")
        scan_btn.clicked.connect(self._run_capture_scan)
        v.addWidget(scan_btn)

        v.addWidget(QLabel("Networks found (select by number):"))
        self.ap_list_widget = QListWidget()
        self.ap_list_widget.setMinimumHeight(140)
        self.ap_list_widget.setMaximumHeight(320)
        v.addWidget(self.ap_list_widget)

        form = QFormLayout()
        self.target_number_spin = QSpinBox()
        self.target_number_spin.setMinimum(1)
        self.target_number_spin.setMaximum(999)
        self.target_number_spin.setValue(1)
        form.addRow("Target number:", self.target_number_spin)

        start_monitor_btn = QPushButton("Start monitoring selected target")
        start_monitor_btn.clicked.connect(self._run_capture_start)
        v.addLayout(form)
        v.addWidget(start_monitor_btn)

        h = QHBoxLayout()
        stop_btn = QPushButton("Stop Capture")
        stop_btn.clicked.connect(self._run_capture_stop)
        h.addWidget(stop_btn)
        h.addStretch()
        v.addLayout(h)

        self.capture_status = QLabel("No capture in progress.")
        self.capture_status.setStyleSheet("color: #8892a6;")
        v.addWidget(self.capture_status)
        return group

    def _build_attack_group(self) -> QGroupBox:
        group = QGroupBox("Attacks")
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        v = QVBoxLayout(group)
        v.setSpacing(8)
        v.addWidget(QLabel("Send deauth packets to the current capture target to force WPA handshake."))
        deauth_btn = QPushButton("Deauth attack (current target)")
        deauth_btn.clicked.connect(self._run_deauth)
        v.addWidget(deauth_btn, alignment=Qt.AlignLeft)
        return group

    def _build_cracking_group(self) -> QGroupBox:
        group = QGroupBox("Cracking")
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        v = QVBoxLayout(group)
        v.setSpacing(8)
        v.addWidget(QLabel("Crack WPA/WPA2 handshakes with Aircrack-ng (you will configure this later)."))
        crack_btn = QPushButton("Crack handshake")
        crack_btn.clicked.connect(lambda: self._run("crack_handshake.sh"))
        v.addWidget(crack_btn, alignment=Qt.AlignLeft)
        return group

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

    def _run_list_interfaces(self) -> None:
        if os.geteuid() != 0 and not self._ensure_sudo():
            return
        self._append("[+] Listing interfaces...")
        self.scan_worker = ScriptWorker("list_interfaces.sh", require_root=True, sudo_password=self.sudo_password)
        self.scan_worker.output_signal.connect(self._append)
        self.scan_worker.finished_signal.connect(self._on_list_interfaces_finished)
        self.scan_worker.start()

    def _on_list_interfaces_finished(self, result: ScanResult) -> None:
        self.scan_worker = None
        if not result.success and result.error:
            self._append(f"[!] {result.error}")

    def _run_airmon_start(self) -> None:
        iface = self.interface_edit.text().strip()
        if not iface:
            QMessageBox.warning(self, "Interface required", "Enter an interface (e.g. wlan0) to enable monitor mode.")
            return
        if os.geteuid() != 0 and not self._ensure_sudo():
            return
        self._append(f"[+] Enabling monitor mode on {iface}...")
        self.scan_worker = ScriptWorker(
            "airmon_start.sh", args=[iface], require_root=True, sudo_password=self.sudo_password
        )
        self.scan_worker.output_signal.connect(self._append)
        self.scan_worker.finished_signal.connect(lambda r: self._on_airmon_start_finished(r, iface))
        self.scan_worker.start()

    def _on_airmon_start_finished(self, result: ScanResult, _iface: str) -> None:
        self.scan_worker = None
        if result.success and result.output:
            for line in result.output.splitlines():
                if line.strip().startswith("MONITOR_INTERFACE="):
                    self.monitor_interface = line.split("=", 1)[1].strip()
                    self.monitor_status.setText(f"Monitor interface: {self.monitor_interface}")
                    self.monitor_status.setStyleSheet("color: #a9f5d0;")
                    break
        if not result.success and result.error:
            self._append(f"[!] {result.error}")

    def _run_airmon_stop(self) -> None:
        if not self.monitor_interface:
            QMessageBox.warning(self, "No monitor", "Enable monitor mode first so we know which interface to disable.")
            return
        if os.geteuid() != 0 and not self._ensure_sudo():
            return
        self._append(f"[+] Disabling monitor on {self.monitor_interface}...")
        self.scan_worker = ScriptWorker(
            "airmon_stop.sh", args=[self.monitor_interface], require_root=True, sudo_password=self.sudo_password
        )
        self.scan_worker.output_signal.connect(self._append)
        self.scan_worker.finished_signal.connect(self._on_airmon_stop_finished)
        self.scan_worker.start()

    def _on_airmon_stop_finished(self, result: ScanResult) -> None:
        self.scan_worker = None
        self.monitor_interface = None
        self.monitor_status.setText("Monitor interface: none")
        self.monitor_status.setStyleSheet("color: #ffaeaa;")
        if not result.success and result.error:
            self._append(f"[!] {result.error}")

    def _run_capture_scan(self) -> None:
        if not self.monitor_interface:
            QMessageBox.warning(self, "Monitor required", "Enable monitor mode first and wait for 'Monitor interface: mon0' (or similar).")
            return
        if os.geteuid() != 0 and not self._ensure_sudo():
            return
        self._append("[+] Scanning for networks (about 15 seconds)...")
        self.ap_list.clear()
        self.ap_list_widget.clear()
        self.scan_worker = ScriptWorker(
            "capture_scan.sh", args=[self.monitor_interface], require_root=True, sudo_password=self.sudo_password
        )
        self.scan_worker.output_signal.connect(self._append)
        self.scan_worker.finished_signal.connect(self._on_capture_scan_finished)
        self.scan_worker.start()

    def _on_capture_scan_finished(self, result: ScanResult) -> None:
        self.scan_worker = None
        if not result.success:
            if result.error:
                self._append(f"[!] {result.error}")
            return
        cap_base = None
        for line in result.output.splitlines():
            line = line.strip()
            if line.startswith("CAP_BASE="):
                cap_base = line.split("=", 1)[1].strip()
                continue
            parts = line.split()
            if len(parts) >= 4 and parts[0].isdigit():
                try:
                    num = int(parts[0])
                    bssid = parts[1]
                    ch = parts[2]
                    essid = " ".join(parts[3:]) if len(parts) > 3 else "(hidden)"
                    self.ap_list.append(TargetAp(num=num, bssid=bssid, channel=ch, essid=essid))
                    self.ap_list_widget.addItem(QListWidgetItem(f"{num}. {bssid}  ch{ch}  {essid}"))
                except (ValueError, IndexError):
                    pass
        if self.ap_list:
            self.target_number_spin.setMaximum(max(a.num for a in self.ap_list))
            self.target_number_spin.setValue(self.ap_list[0].num)
        if not result.output.strip():
            self._append("[!] No networks found or scan failed.")

    def _run_capture_start(self) -> None:
        if not self.monitor_interface:
            QMessageBox.warning(self, "Monitor required", "Enable monitor mode first.")
            return
        num = self.target_number_spin.value()
        ap = next((a for a in self.ap_list if a.num == num), None)
        if not ap:
            QMessageBox.warning(self, "Select target", "Scan for networks first and select a valid target number.")
            return
        if os.geteuid() != 0 and not self._ensure_sudo():
            return
        # Run capture_scan to get CAP_BASE, or we need cap_base from last scan - we didn't store it. So we must get cap_base from capture_start. Actually capture_start.sh expects cap_base as 4th argument. We get cap_base from the scan output - we didn't save it. So we need to save cap_base when we parse the scan output.
        # Redesign: in _on_capture_scan_finished we store self.last_cap_base = cap_base. Then in _run_capture_start we call capture_start.sh monitor bssid channel self.last_cap_base. But capture_start generates a NEW cap base with a new timestamp. So we don't need to pass cap_base from scan - we can generate it in capture_start.sh. So capture_start.sh only needs 3 args: interface bssid channel. I'll update the script to take 3 args and generate cap_base inside.
        self._append(f"[+] Starting capture on {ap.bssid} channel {ap.channel}...")
        self.tool_worker = ScriptWorker(
            "capture_start.sh",
            args=[self.monitor_interface, ap.bssid, ap.channel],
            require_root=True,
            sudo_password=self.sudo_password,
        )
        self.selected_bssid = ap.bssid
        self.selected_channel = ap.channel
        self.tool_worker.output_signal.connect(self._append)
        self.tool_worker.finished_signal.connect(self._on_capture_start_finished)
        self.tool_worker.start()

    def _on_capture_start_finished(self, result: ScanResult) -> None:
        self.tool_worker = None
        if not result.success and result.error:
            self._append(f"[!] {result.error}")
            return
        self.cap_base = None
        self.capture_log_path = None
        for line in result.output.splitlines():
            line = line.strip()
            if line.startswith("CAPTURE_LOG="):
                self.capture_log_path = line.split("=", 1)[1].strip()
            elif line.startswith("CAPTURE_BASE="):
                self.cap_base = line.split("=", 1)[1].strip()
        if self.capture_log_path and Path(self.capture_log_path).exists():
            self.capture_status.setText("Capture running. Polling for handshake...")
            self.capture_status.setStyleSheet("color: #ffd700;")
            self._start_handshake_poll()
        else:
            self.capture_status.setText("Capture started (log path not found for handshake check).")
            self.capture_status.setStyleSheet("color: #ffd700;")

    def _start_handshake_poll(self) -> None:
        if self.handshake_timer:
            self.handshake_timer.stop()
        self.handshake_timer = QTimer(self)
        self.handshake_timer.timeout.connect(self._check_handshake)
        self.handshake_timer.start(2000)

    def _check_handshake(self) -> None:
        if not self.capture_log_path or not Path(self.capture_log_path).exists():
            return
        try:
            text = Path(self.capture_log_path).read_text(errors="ignore")
            if "handshake" in text.lower() or "WPA" in text and "handshake" in text.lower():
                self._stop_handshake_poll()
                self.capture_status.setText("WPA handshake captured! You can stop capture.")
                self.capture_status.setStyleSheet("color: #a9f5d0;")
                QMessageBox.information(
                    self,
                    "Handshake captured",
                    "WPA handshake has been captured for the target. You can click 'Stop Capture' and use the .cap file for cracking.",
                )
        except Exception:
            pass

    def _stop_handshake_poll(self) -> None:
        if self.handshake_timer:
            self.handshake_timer.stop()
            self.handshake_timer = None

    def _run_capture_stop(self) -> None:
        if os.geteuid() != 0 and not self._ensure_sudo():
            return
        self._stop_handshake_poll()
        self._append("[+] Stopping capture...")
        self.tool_worker = ScriptWorker("capture_stop.sh", require_root=True, sudo_password=self.sudo_password)
        self.tool_worker.output_signal.connect(self._append)
        self.tool_worker.finished_signal.connect(self._on_capture_stop_finished)
        self.tool_worker.start()

    def _on_capture_stop_finished(self, result: ScanResult) -> None:
        self.tool_worker = None
        self.capture_status.setText("No capture in progress.")
        self.capture_status.setStyleSheet("color: #8892a6;")
        self.capture_log_path = None
        if not result.success and result.error:
            self._append(f"[!] {result.error}")

    def _run_deauth(self) -> None:
        if not self.monitor_interface or not self.selected_bssid:
            QMessageBox.warning(
                self,
                "Target required",
                "Start monitoring a target first (scan, select number, Start monitoring). Then run deauth.",
            )
            return
        if os.geteuid() != 0 and not self._ensure_sudo():
            return
        self._append(f"[+] Sending deauth to {self.selected_bssid}...")
        self.tool_worker = ScriptWorker(
            "deauth.sh",
            args=[self.monitor_interface, self.selected_bssid],
            require_root=True,
            sudo_password=self.sudo_password,
        )
        self.tool_worker.output_signal.connect(self._append)
        self.tool_worker.finished_signal.connect(self._on_tool_finished)
        self.tool_worker.start()

    def _on_tool_finished(self, result: ScanResult) -> None:
        self.tool_worker = None
        if not result.success and result.error:
            self._append(f"[!] {result.error}")

    def _run(self, script_name: str, args: Optional[List[str]] = None) -> None:
        path = self.scripts_dir / script_name
        if not path.exists():
            self._append(f"[!] Script not found: {path}")
            return
        if os.geteuid() != 0 and not self._ensure_sudo():
            return
        try:
            cmd = ["sudo", "-S", "bash", str(path), *(args or [])]
            if os.geteuid() == 0:
                cmd = ["bash", str(path), *(args or [])]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=600, input=(self.sudo_password or "") + "\n")
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

    def _append(self, text: str) -> None:
        self.output.append(text)
        self.output.ensureCursorVisible()
