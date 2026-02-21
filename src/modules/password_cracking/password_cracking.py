import os
import subprocess
from pathlib import Path
from typing import Optional, List, Tuple

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QWidget,
    QGroupBox,
    QPushButton,
    QHBoxLayout,
    QTextBrowser,
    QLineEdit,
    QFileDialog,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QComboBox,
    QMessageBox,
    QScrollArea,
    QSizePolicy,
)

SCRIPT_DIR = Path(__file__).resolve().parent / "scripts"
REPORTS_DIR = Path(__file__).resolve().parents[3] / "reports" / "password_cracking"


class ScriptWorker(QThread):
    """Run a script in background and emit output and result."""
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)  # success, message

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
            self.finished_signal.emit(False, f"Script not found: {script_path}")
            return
        command: List[str]
        stdin_data: Optional[str] = None
        if self.require_root and os.geteuid() != 0:
            if not self.sudo_password:
                self.finished_signal.emit(False, "Operation cancelled (sudo required).")
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
                self.finished_signal.emit(False, f"Exit code {process.returncode}: {out}")
            else:
                self.finished_signal.emit(True, out or "Completed successfully")
        except FileNotFoundError:
            self.finished_signal.emit(False, f"Script not found: {script_path}")
        except Exception as exc:
            self.finished_signal.emit(False, str(exc))


class JohnDialog(QDialog):
    """Collect input for John the Ripper."""

    def __init__(self, default_wordlist: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Run John the Ripper")
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.hash_file_edit = QLineEdit()
        self.hash_file_edit.setPlaceholderText("/path/to/hashes.txt")
        browse_hash = QPushButton("Browse…")
        browse_hash.clicked.connect(self._browse_hash_file)
        hash_container = QHBoxLayout()
        hash_container.addWidget(self.hash_file_edit)
        hash_container.addWidget(browse_hash)
        form.addRow("Hash file:", hash_container)

        wordlist_container = QHBoxLayout()
        self.wordlist_edit = QLineEdit()
        self.wordlist_edit.setPlaceholderText("/path/to/wordlist.txt")
        if default_wordlist:
            self.wordlist_edit.setText(default_wordlist)
        browse_wordlist = QPushButton("Browse…")
        browse_wordlist.clicked.connect(self._browse_wordlist)
        wordlist_container.addWidget(self.wordlist_edit)
        wordlist_container.addWidget(browse_wordlist)
        form.addRow("Wordlist:", wordlist_container)

        self.format_edit = QLineEdit()
        self.format_edit.setPlaceholderText("e.g., md5crypt, sha512crypt, raw-md5 (optional)")
        form.addRow("Hash format:", self.format_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_hash_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select hash file", str(Path.home()),
            "Text files (*.txt);;All files (*.*)",
        )
        if path:
            self.hash_file_edit.setText(path)

    def _browse_wordlist(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select wordlist", str(Path.home()),
            "Text files (*.txt);;All files (*.*)",
        )
        if path:
            self.wordlist_edit.setText(path)

    def _accept(self) -> None:
        hash_file = self.hash_file_edit.text().strip()
        if not hash_file:
            QMessageBox.warning(self, "Missing Hash File", "Please select a hash file.")
            return
        if not Path(hash_file).expanduser().exists():
            QMessageBox.warning(self, "Invalid Hash File", "The selected hash file does not exist.")
            return
        wordlist = self.wordlist_edit.text().strip()
        if not wordlist:
            QMessageBox.warning(self, "Missing Wordlist", "Please select a wordlist file.")
            return
        if not Path(wordlist).expanduser().exists():
            QMessageBox.warning(self, "Invalid Wordlist", "The selected wordlist file does not exist.")
            return
        self.accept()

    def values(self) -> Tuple[str, str, str]:
        return (
            str(Path(self.hash_file_edit.text().strip()).expanduser()),
            str(Path(self.wordlist_edit.text().strip()).expanduser()),
            self.format_edit.text().strip(),
        )


class HashcatDialog(QDialog):
    """Collect input for Hashcat."""

    def __init__(self, default_wordlist: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Run Hashcat")
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.hash_file_edit = QLineEdit()
        self.hash_file_edit.setPlaceholderText("/path/to/hashes.txt")
        browse_hash = QPushButton("Browse…")
        browse_hash.clicked.connect(self._browse_hash_file)
        hash_container = QHBoxLayout()
        hash_container.addWidget(self.hash_file_edit)
        hash_container.addWidget(browse_hash)
        form.addRow("Hash file:", hash_container)

        self.hash_type_combo = QComboBox()
        self.hash_type_combo.addItems([
            "0", "100", "1000", "1400", "1700", "1800", "2500", "3200",
            "500", "501", "10000", "1500", "1600", "3000", "5500",
        ])
        self.hash_type_combo.setEditable(True)
        self.hash_type_combo.setCurrentText("0")
        form.addRow("Hash type (-m):", self.hash_type_combo)

        wordlist_container = QHBoxLayout()
        self.wordlist_edit = QLineEdit()
        self.wordlist_edit.setPlaceholderText("/path/to/wordlist.txt")
        if default_wordlist:
            self.wordlist_edit.setText(default_wordlist)
        browse_wordlist = QPushButton("Browse…")
        browse_wordlist.clicked.connect(self._browse_wordlist)
        wordlist_container.addWidget(self.wordlist_edit)
        wordlist_container.addWidget(browse_wordlist)
        form.addRow("Wordlist:", wordlist_container)

        self.extra_args_edit = QLineEdit()
        self.extra_args_edit.setPlaceholderText("Additional Hashcat options (optional)")
        form.addRow("Extra args:", self.extra_args_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_hash_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select hash file", str(Path.home()),
            "Text files (*.txt);;All files (*.*)",
        )
        if path:
            self.hash_file_edit.setText(path)

    def _browse_wordlist(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select wordlist", str(Path.home()),
            "Text files (*.txt);;All files (*.*)",
        )
        if path:
            self.wordlist_edit.setText(path)

    def _accept(self) -> None:
        hash_file = self.hash_file_edit.text().strip()
        if not hash_file:
            QMessageBox.warning(self, "Missing Hash File", "Please select a hash file.")
            return
        if not Path(hash_file).expanduser().exists():
            QMessageBox.warning(self, "Invalid Hash File", "The selected hash file does not exist.")
            return
        hash_type = self.hash_type_combo.currentText().strip()
        if not hash_type:
            QMessageBox.warning(self, "Missing Hash Type", "Please specify a hash type.")
            return
        wordlist = self.wordlist_edit.text().strip()
        if not wordlist:
            QMessageBox.warning(self, "Missing Wordlist", "Please select a wordlist file.")
            return
        if not Path(wordlist).expanduser().exists():
            QMessageBox.warning(self, "Invalid Wordlist", "The selected wordlist file does not exist.")
            return
        self.accept()

    def values(self) -> Tuple[str, str, str, str]:
        return (
            str(Path(self.hash_file_edit.text().strip()).expanduser()),
            self.hash_type_combo.currentText().strip(),
            str(Path(self.wordlist_edit.text().strip()).expanduser()),
            self.extra_args_edit.text().strip(),
        )


class HydraDialog(QDialog):
    """Collect input for Hydra."""

    def __init__(self, default_wordlist: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Run Hydra")
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.target_edit = QLineEdit()
        self.target_edit.setPlaceholderText("192.168.1.100 or example.com")
        form.addRow("Target:", self.target_edit)

        self.service_combo = QComboBox()
        self.service_combo.addItems([
            "ssh", "ftp", "telnet", "http", "https", "smb", "rdp", "vnc",
            "mysql", "postgresql", "mssql", "snmp", "ldap", "pop3", "imap",
        ])
        self.service_combo.setEditable(True)
        form.addRow("Service:", self.service_combo)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("admin or /path/to/userlist.txt")
        form.addRow("Username:", self.username_edit)

        wordlist_container = QHBoxLayout()
        self.wordlist_edit = QLineEdit()
        self.wordlist_edit.setPlaceholderText("/path/to/wordlist.txt")
        if default_wordlist:
            self.wordlist_edit.setText(default_wordlist)
        browse_wordlist = QPushButton("Browse…")
        browse_wordlist.clicked.connect(self._browse_wordlist)
        wordlist_container.addWidget(self.wordlist_edit)
        wordlist_container.addWidget(browse_wordlist)
        form.addRow("Wordlist:", wordlist_container)

        self.port_edit = QLineEdit()
        self.port_edit.setPlaceholderText("Leave empty for default port")
        form.addRow("Port (optional):", self.port_edit)

        self.extra_args_edit = QLineEdit()
        self.extra_args_edit.setPlaceholderText("Additional Hydra options (optional)")
        form.addRow("Extra args:", self.extra_args_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_wordlist(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select wordlist", str(Path.home()),
            "Text files (*.txt);;All files (*.*)",
        )
        if path:
            self.wordlist_edit.setText(path)

    def _accept(self) -> None:
        target = self.target_edit.text().strip()
        if not target:
            QMessageBox.warning(self, "Missing Target", "Please provide a target.")
            return
        service = self.service_combo.currentText().strip()
        if not service:
            QMessageBox.warning(self, "Missing Service", "Please specify a service.")
            return
        username = self.username_edit.text().strip()
        if not username:
            QMessageBox.warning(self, "Missing Username", "Please provide a username or userlist file.")
            return
        wordlist = self.wordlist_edit.text().strip()
        if not wordlist:
            QMessageBox.warning(self, "Missing Wordlist", "Please select a wordlist file.")
            return
        if not Path(wordlist).expanduser().exists():
            QMessageBox.warning(self, "Invalid Wordlist", "The selected wordlist file does not exist.")
            return
        self.accept()

    def values(self) -> Tuple[str, str, str, str, str, str]:
        return (
            self.target_edit.text().strip(),
            self.service_combo.currentText().strip(),
            self.username_edit.text().strip(),
            str(Path(self.wordlist_edit.text().strip()).expanduser()),
            self.port_edit.text().strip(),
            self.extra_args_edit.text().strip(),
        )


class PasswordCrackingModule(QWidget):
    """Password Cracking workflows (John, Hashcat, Hydra)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.scripts_dir = SCRIPT_DIR
        self.selected_wordlist: str = ""
        self.john_worker: Optional[ScriptWorker] = None
        self.hashcat_worker: Optional[ScriptWorker] = None
        self.hydra_worker: Optional[ScriptWorker] = None

        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        header = QLabel("Password Cracking")
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
        scroll_layout.addWidget(self._build_wordlist_group())
        scroll_layout.addWidget(self._build_john_group())
        scroll_layout.addWidget(self._build_hashcat_group())
        scroll_layout.addWidget(self._build_hydra_group())
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)

        layout.addWidget(scroll)

        self.output = QTextBrowser()
        self.output.setMinimumHeight(220)
        self.output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.output, 1)

    def _build_wordlist_group(self) -> QGroupBox:
        group = QGroupBox("Wordlist Selection")
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        v = QVBoxLayout(group)
        v.setSpacing(10)
        desc = QLabel(
            "Select a wordlist file to use with all password cracking tools. "
            "This wordlist will be pre-filled in each tool's dialog."
        )
        desc.setWordWrap(True)
        v.addWidget(desc)
        h = QHBoxLayout()
        h.setSpacing(8)
        self.wordlist_label = QLabel("No wordlist selected")
        self.wordlist_label.setStyleSheet("color: #8892a6;")
        select_btn = QPushButton("Select Wordlist…")
        select_btn.setMinimumWidth(160)
        select_btn.setMinimumHeight(36)
        select_btn.clicked.connect(self._select_wordlist)
        h.addWidget(self.wordlist_label)
        h.addWidget(select_btn)
        h.addStretch()
        v.addLayout(h)
        return group

    def _select_wordlist(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select wordlist", str(Path.home()),
            "Text files (*.txt);;All files (*.*)",
        )
        if path:
            self.selected_wordlist = path
            self.wordlist_label.setText(f"Selected: {Path(path).name}")
            self.wordlist_label.setStyleSheet("color: #a9f5d0;")

    def _build_john_group(self) -> QGroupBox:
        group = QGroupBox("John the Ripper")
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        v = QVBoxLayout(group)
        v.setSpacing(10)
        desc = QLabel(
            "Crack password hashes using John the Ripper. Supports various hash formats "
            "including MD5, SHA, bcrypt, and more."
        )
        desc.setWordWrap(True)
        v.addWidget(desc)
        h = QHBoxLayout()
        h.setSpacing(8)
        run_btn = QPushButton("Run John…")
        run_btn.setMinimumWidth(160)
        run_btn.setMinimumHeight(36)
        run_btn.clicked.connect(self._run_john)
        stop_btn = QPushButton("Stop John")
        stop_btn.setMinimumWidth(140)
        stop_btn.setMinimumHeight(36)
        stop_btn.clicked.connect(self._stop_john)
        stop_btn.setEnabled(False)
        self.john_stop_btn = stop_btn
        h.addWidget(run_btn)
        h.addWidget(stop_btn)
        h.addStretch()
        v.addLayout(h)
        return group

    def _build_hashcat_group(self) -> QGroupBox:
        group = QGroupBox("Hashcat")
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        v = QVBoxLayout(group)
        v.setSpacing(10)
        desc = QLabel(
            "GPU-accelerated password cracking with Hashcat. Supports hundreds of hash types "
            "and can leverage GPU hardware for faster cracking."
        )
        desc.setWordWrap(True)
        v.addWidget(desc)
        h = QHBoxLayout()
        h.setSpacing(8)
        run_btn = QPushButton("Run Hashcat…")
        run_btn.setMinimumWidth(160)
        run_btn.setMinimumHeight(36)
        run_btn.clicked.connect(self._run_hashcat)
        h.addWidget(run_btn)
        h.addStretch()
        v.addLayout(h)
        return group

    def _build_hydra_group(self) -> QGroupBox:
        group = QGroupBox("Hydra")
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        v = QVBoxLayout(group)
        v.setSpacing(10)
        desc = QLabel(
            "Online password attacks with Hydra. Brute-force passwords for various services "
            "including SSH, FTP, HTTP, SMB, and more."
        )
        desc.setWordWrap(True)
        v.addWidget(desc)
        h = QHBoxLayout()
        h.setSpacing(8)
        run_btn = QPushButton("Run Hydra…")
        run_btn.setMinimumWidth(160)
        run_btn.setMinimumHeight(36)
        run_btn.clicked.connect(self._run_hydra)
        h.addWidget(run_btn)
        h.addStretch()
        v.addLayout(h)
        return group

    def _run_john(self) -> None:
        if self.john_worker and self.john_worker.isRunning():
            QMessageBox.warning(self, "John Running", "John is already running. Please stop it first.")
            return
        dialog = JohnDialog(self.selected_wordlist, self)
        if dialog.exec_() != QDialog.Accepted:
            return
        hash_file, wordlist, format_arg = dialog.values()
        args = [hash_file, wordlist]
        if format_arg:
            args.extend(["--format", format_arg])
        self._append(f"[+] Starting John the Ripper...")
        self._append(f"[+] Hash file: {hash_file}")
        self._append(f"[+] Wordlist: {wordlist}")
        self.john_stop_btn.setEnabled(True)
        self.john_worker = ScriptWorker("john_run.sh", args=args)
        self.john_worker.output_signal.connect(self._append)
        self.john_worker.finished_signal.connect(lambda success, msg: self._handle_john_finished(success, msg))
        self.john_worker.start()

    def _stop_john(self) -> None:
        if self.john_worker and self.john_worker.isRunning():
            self._append("[!] Stopping John...")
            worker = ScriptWorker("john_stop.sh")
            worker.finished_signal.connect(lambda success, msg: self._handle_john_stopped(success, msg))
            worker.start()
        else:
            self.john_stop_btn.setEnabled(False)

    def _handle_john_finished(self, success: bool, message: str) -> None:
        self.john_stop_btn.setEnabled(False)
        if success:
            self._append(f"[+] John completed: {message}")
        else:
            self._append(f"[!] John failed: {message}")

    def _handle_john_stopped(self, success: bool, message: str) -> None:
        if self.john_worker and self.john_worker.isRunning():
            self.john_worker.terminate()
            self.john_worker.wait()
        self.john_stop_btn.setEnabled(False)
        if success:
            self._append(f"[+] John stopped: {message}")
        else:
            self._append(f"[!] Stop command: {message}")

    def _run_hashcat(self) -> None:
        if self.hashcat_worker and self.hashcat_worker.isRunning():
            QMessageBox.warning(self, "Hashcat Running", "Hashcat is already running. Please wait for it to finish.")
            return
        dialog = HashcatDialog(self.selected_wordlist, self)
        if dialog.exec_() != QDialog.Accepted:
            return
        hash_file, hash_type, wordlist, extra_args = dialog.values()
        args = [hash_file, hash_type, wordlist]
        if extra_args:
            args.extend(extra_args.split())
        self._append(f"[+] Starting Hashcat...")
        self._append(f"[+] Hash file: {hash_file}")
        self._append(f"[+] Hash type: {hash_type}")
        self._append(f"[+] Wordlist: {wordlist}")
        self.hashcat_worker = ScriptWorker("hashcat_run.sh", args=args)
        self.hashcat_worker.output_signal.connect(self._append)
        self.hashcat_worker.finished_signal.connect(lambda success, msg: self._handle_hashcat_finished(success, msg))
        self.hashcat_worker.start()

    def _handle_hashcat_finished(self, success: bool, message: str) -> None:
        if success:
            self._append(f"[+] Hashcat completed: {message}")
        else:
            self._append(f"[!] Hashcat failed: {message}")

    def _run_hydra(self) -> None:
        if self.hydra_worker and self.hydra_worker.isRunning():
            QMessageBox.warning(self, "Hydra Running", "Hydra is already running. Please wait for it to finish.")
            return
        dialog = HydraDialog(self.selected_wordlist, self)
        if dialog.exec_() != QDialog.Accepted:
            return
        target, service, username, wordlist, port, extra_args = dialog.values()
        args = [target, service, username, wordlist]
        if port:
            args.extend(["-s", port])
        if extra_args:
            args.extend(extra_args.split())
        self._append(f"[+] Starting Hydra...")
        self._append(f"[+] Target: {target}")
        self._append(f"[+] Service: {service}")
        self._append(f"[+] Username: {username}")
        self._append(f"[+] Wordlist: {wordlist}")
        self.hydra_worker = ScriptWorker("hydra_run.sh", args=args)
        self.hydra_worker.output_signal.connect(self._append)
        self.hydra_worker.finished_signal.connect(lambda success, msg: self._handle_hydra_finished(success, msg))
        self.hydra_worker.start()

    def _handle_hydra_finished(self, success: bool, message: str) -> None:
        if success:
            self._append(f"[+] Hydra completed: {message}")
        else:
            self._append(f"[!] Hydra failed: {message}")

    def _append(self, text: str) -> None:
        self.output.append(text)
        self.output.ensureCursorVisible()
