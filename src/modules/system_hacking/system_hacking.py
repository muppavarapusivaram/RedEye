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

print(f"[DEBUG] Loading SystemHackingModule from {__file__}")


class SystemHackingModule(QWidget):
    """System Hacking workflows (Responder, reverse shells)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.scripts_dir = Path(__file__).resolve().parent / "scripts"

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        header = QLabel("System Hacking")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header)

        layout.addWidget(self._build_responder_group())
        layout.addWidget(self._build_reverse_shell_group())
        layout.addWidget(self._build_credentials_group())

        self.output = QTextBrowser()
        self.output.setMinimumHeight(200)
        layout.addWidget(self.output)
        layout.addStretch()

    def _build_responder_group(self) -> QGroupBox:
        group = QGroupBox("Responder")
        v = QVBoxLayout(group)
        v.addWidget(QLabel("Start/stop Responder for credential harvesting."))
        h = QHBoxLayout()
        start_btn = QPushButton("Start Responder")
        stop_btn = QPushButton("Stop Responder")
        h.addWidget(start_btn)
        h.addWidget(stop_btn)
        h.addStretch()
        start_btn.clicked.connect(lambda: self._run("responder_start.sh"))
        stop_btn.clicked.connect(lambda: self._run("responder_stop.sh"))
        v.addLayout(h)
        return group

    def _build_reverse_shell_group(self) -> QGroupBox:
        group = QGroupBox("Reverse Shells")
        v = QVBoxLayout(group)
        v.addWidget(QLabel("Generate payloads and start listeners."))
        h = QHBoxLayout()
        gen_btn = QPushButton("Generate Reverse Shell")
        listen_btn = QPushButton("Start Listener")
        h.addWidget(gen_btn)
        h.addWidget(listen_btn)
        h.addStretch()
        gen_btn.clicked.connect(lambda: self._run("generate_shell.sh"))
        listen_btn.clicked.connect(lambda: self._run("start_listener.sh"))
        v.addLayout(h)
        return group

    def _build_credentials_group(self) -> QGroupBox:
        group = QGroupBox("Credentials")
        v = QVBoxLayout(group)
        v.addWidget(QLabel("Open captured credentials and artifacts."))
        open_btn = QPushButton("View Captured Credentials")
        open_btn.clicked.connect(lambda: self._run("view_credentials.sh"))
        v.addWidget(open_btn, alignment=Qt.AlignLeft)
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


