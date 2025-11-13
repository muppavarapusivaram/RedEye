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

print(f"[DEBUG] Loading PasswordCrackingModule from {__file__}")


class PasswordCrackingModule(QWidget):
    """Password Cracking workflows (John, Hashcat, Hydra)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.scripts_dir = Path(__file__).resolve().parent / "scripts"

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        header = QLabel("Password Cracking")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header)

        layout.addWidget(self._build_john_group())
        layout.addWidget(self._build_hashcat_group())
        layout.addWidget(self._build_hydra_group())
        layout.addWidget(self._build_wordlists_group())

        self.output = QTextBrowser()
        self.output.setMinimumHeight(200)
        layout.addWidget(self.output)
        layout.addStretch()

    def _build_john_group(self) -> QGroupBox:
        group = QGroupBox("John the Ripper")
        v = QVBoxLayout(group)
        v.addWidget(QLabel("Run and stop John cracking sessions."))
        h = QHBoxLayout()
        run_btn = QPushButton("Run John")
        stop_btn = QPushButton("Stop John")
        h.addWidget(run_btn)
        h.addWidget(stop_btn)
        h.addStretch()
        run_btn.clicked.connect(lambda: self._run("john_run.sh"))
        stop_btn.clicked.connect(lambda: self._run("john_stop.sh"))
        v.addLayout(h)
        return group

    def _build_hashcat_group(self) -> QGroupBox:
        group = QGroupBox("Hashcat")
        v = QVBoxLayout(group)
        v.addWidget(QLabel("Run GPU-accelerated cracking with Hashcat."))
        run_btn = QPushButton("Run Hashcat")
        run_btn.clicked.connect(lambda: self._run("hashcat_run.sh"))
        v.addWidget(run_btn, alignment=Qt.AlignLeft)
        return group

    def _build_hydra_group(self) -> QGroupBox:
        group = QGroupBox("Hydra")
        v = QVBoxLayout(group)
        v.addWidget(QLabel("Run online password attacks with Hydra."))
        run_btn = QPushButton("Run Hydra")
        run_btn.clicked.connect(lambda: self._run("hydra_run.sh"))
        v.addWidget(run_btn, alignment=Qt.AlignLeft)
        return group

    def _build_wordlists_group(self) -> QGroupBox:
        group = QGroupBox("Wordlists")
        v = QVBoxLayout(group)
        v.addWidget(QLabel("Generate wordlists with Crunch."))
        gen_btn = QPushButton("Generate with Crunch")
        gen_btn.clicked.connect(lambda: self._run("crunch_generate.sh"))
        v.addWidget(gen_btn, alignment=Qt.AlignLeft)
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


