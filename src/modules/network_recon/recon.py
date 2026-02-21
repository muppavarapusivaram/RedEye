import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QFileDialog,
    QInputDialog,
    QLabel, 
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
    QRadioButton,
    QComboBox,
    QSpinBox,
)

from gui.core.ai_manager import AIManager

print(f"[DEBUG] Loading ReconnaissanceModule from {__file__}")


SCRIPT_DIR = Path(__file__).resolve().parent / "scripts"
REPORTS_DIR = Path(__file__).resolve().parents[3] / "reports" / "network_recon"


@dataclass
class ScanResult:
    success: bool
    output: str
    error: Optional[str] = None


class AIAnalysisWorker(QThread):
    """Background thread worker for AI analysis to keep GUI responsive."""
    
    finished_signal = pyqtSignal(bool, str, str)  # success, report, error_message
    
    def __init__(self, ai_manager: AIManager, tool_name: str, raw_output: str):
        super().__init__()
        self.ai_manager = ai_manager
        self.tool_name = tool_name
        self.raw_output = raw_output
        
    def run(self):
        try:
            is_enabled = self.ai_manager.is_enabled()
            if not is_enabled:
                self.finished_signal.emit(False, "", "AI is not enabled. Please configure AI in Dashboard.")
                return
            success, result = self.ai_manager.generate_analysis(self.tool_name, self.raw_output)
            if success:
                self.finished_signal.emit(True, result, "")
            else:
                self.finished_signal.emit(False, "", result)
        except Exception as e:
            self.finished_signal.emit(False, "", f"AI analysis exception: {e}")


class ScanWorker(QThread):
    """Background thread worker for running Nmap scans without blocking the GUI."""
    
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(ScanResult)
    
    def __init__(self, script_name: str, args: Optional[List[str]] = None, require_root: bool = False, sudo_password: Optional[str] = None):
        super().__init__()
        self.script_name = script_name
        self.args = args or []
        self.require_root = require_root
        self.sudo_password = sudo_password
        self._cancelled = False
        
    def cancel(self):
        self._cancelled = True
        
    def run(self):
        script_path = SCRIPT_DIR / self.script_name
        if not script_path.exists():
            self.finished_signal.emit(ScanResult(False, "", f"Script not found: {script_path}"))
            return
        command: List[str]
        stdin_data: Optional[str] = None
        if self.require_root and os.geteuid() != 0:
            if not self.sudo_password:
                self.finished_signal.emit(ScanResult(False, "", "Operation cancelled (sudo password required)."))
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
                universal_newlines=True,
            )
            if stdin_data:
                process.stdin.write(stdin_data)
                process.stdin.flush()
                process.stdin.close()
            output_lines = []
            while True:
                if self._cancelled:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    self.finished_signal.emit(ScanResult(False, "", "Scan cancelled by user."))
                    return
                line = process.stdout.readline()
                if not line:
                    if process.poll() is not None:
                        break
                    continue
                line = line.rstrip()
                output_lines.append(line)
                self.output_signal.emit(line)
            returncode = process.wait()
            output = '\n'.join(output_lines)
            if returncode != 0:
                if "incorrect password" in output.lower():
                    self.finished_signal.emit(ScanResult(False, "", "Incorrect sudo password. Please retry."))
                else:
                    self.finished_signal.emit(ScanResult(False, output, "Scan failed with non-zero exit code."))
            else:
                self.finished_signal.emit(ScanResult(True, output or "Scan completed with no output"))
        except subprocess.TimeoutExpired:
            process.kill()
            self.finished_signal.emit(ScanResult(False, "", "Scan timed out after 10 minutes. For large subnets, consider using a custom scan with a smaller target range."))
        except FileNotFoundError:
            self.finished_signal.emit(ScanResult(False, "", f"Unable to execute script: {script_path}"))
        except Exception as exc:
            self.finished_signal.emit(ScanResult(False, "", f"Unexpected error: {exc}"))


class NmapDialog(QDialog):
    """Prompt user for Nmap scan options."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Run Nmap Scan")
        self.setModal(True)
        self.selection: Optional[str] = None
        self.target: str = ""
        self.extra_args: str = ""
        layout = QVBoxLayout(self)
        self.auto_radio = QRadioButton("Scan my subnet (auto-detect)")
        self.custom_radio = QRadioButton("Customize Nmap scan")
        self.auto_radio.setChecked(True)
        layout.addWidget(self.auto_radio)
        layout.addWidget(self.custom_radio)
        self.form = QFormLayout()
        self.target_edit = QLineEdit()
        self.target_edit.setPlaceholderText("e.g., 192.168.1.10 or example.com")
        self.args_edit = QLineEdit()
        self.args_edit.setPlaceholderText("Additional Nmap options (optional)")
        self.form.addRow("Target:", self.target_edit)
        self.form.addRow("Extra Flags:", self.args_edit)
        form_widget = QWidget()
        form_widget.setLayout(self.form)
        form_widget.setEnabled(False)
        layout.addWidget(form_widget)
        self.custom_radio.toggled.connect(form_widget.setEnabled)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        if self.auto_radio.isChecked():
            self.selection = "auto"
            self.accept()
            return
        target = self.target_edit.text().strip()
        if not target:
            QMessageBox.warning(self, "Missing Target", "Please provide a target host or network.")
            return
        self.selection = "custom"
        self.target = target
        self.extra_args = self.args_edit.text().strip()
        self.accept()


class HarvesterDialog(QDialog):
    """Collect input for TheHarvester."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Run TheHarvester")
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.domain_edit = QLineEdit()
        self.domain_edit.setPlaceholderText("example.com")
        form.addRow("Domain:", self.domain_edit)

        self.sources_combo = QComboBox()
        self.sources_combo.addItems(
            [
                "all",
                "bing",
                "duckduckgo",
                "google",
                "linkedin",
                "twitter",
                "yahoo",
                "crtsh",
            ]
        )
        form.addRow("Sources:", self.sources_combo)

        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(1, 5000)
        self.limit_spin.setValue(200)
        form.addRow("Result Limit:", self.limit_spin)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        if not self.domain_edit.text().strip():
            QMessageBox.warning(self, "Missing Domain", "Please enter a domain to enumerate.")
            return
        self.accept()

    def values(self) -> Tuple[str, str, int]:
        return (
            self.domain_edit.text().strip(),
            self.sources_combo.currentText(),
            self.limit_spin.value(),
        )


class ReconNgDialog(QDialog):
    """Collect input for Recon-ng run."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Run Recon-ng")
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.domain_edit = QLineEdit()
        self.domain_edit.setPlaceholderText("example.com")
        form.addRow("Domain:", self.domain_edit)

        self.workspace_edit = QLineEdit()
        self.workspace_edit.setPlaceholderText("workspace_default")
        form.addRow("Workspace:", self.workspace_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        if not self.domain_edit.text().strip():
            QMessageBox.warning(self, "Missing Domain", "Please enter a domain to use as SOURCE.")
            return
        if not self.workspace_edit.text().strip():
            QMessageBox.warning(self, "Missing Workspace", "Please enter a workspace name.")
            return
        self.accept()

    def values(self) -> Tuple[str, str]:
        return (
            self.domain_edit.text().strip(),
            self.workspace_edit.text().strip(),
        )


class AmassDialog(QDialog):
    """Collect input for Amass enumeration."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Run Amass")
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.domain_edit = QLineEdit()
        self.domain_edit.setPlaceholderText("example.com")
        form.addRow("Domain:", self.domain_edit)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(
            [
                "passive",
                "active",
                "bruteforce",
            ]
        )
        form.addRow("Mode:", self.mode_combo)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        if not self.domain_edit.text().strip():
            QMessageBox.warning(self, "Missing Domain", "Please enter a domain for Amass enumeration.")
            return
        self.accept()

    def values(self) -> Tuple[str, str]:
        return (
            self.domain_edit.text().strip(),
            self.mode_combo.currentText(),
        )


class GobusterDialog(QDialog):
    """Collect input for Gobuster scans."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Run Gobuster")
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["dir", "dns"])
        form.addRow("Mode:", self.mode_combo)

        self.target_edit = QLineEdit()
        self.target_edit.setPlaceholderText("https://target.tld or example.com")
        form.addRow("Target:", self.target_edit)

        wordlist_container = QHBoxLayout()
        self.wordlist_edit = QLineEdit()
        self.wordlist_edit.setPlaceholderText("/path/to/wordlist.txt")
        browse_button = QPushButton("Browse…")
        browse_button.clicked.connect(self._browse_wordlist)
        wordlist_container.addWidget(self.wordlist_edit)
        wordlist_container.addWidget(browse_button)
        form.addRow("Wordlist:", wordlist_container)

        self.extensions_edit = QLineEdit()
        self.extensions_edit.setPlaceholderText("php,txt,backup (optional, dir mode only)")
        form.addRow("Extensions:", self.extensions_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_wordlist(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Wordlist", str(Path.home()))
        if path:
            self.wordlist_edit.setText(path)

    def _accept(self) -> None:
        target = self.target_edit.text().strip()
        if not target:
            QMessageBox.warning(self, "Missing Target", "Please provide a target URL/domain.")
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
            self.mode_combo.currentText(),
            self.target_edit.text().strip(),
            str(Path(self.wordlist_edit.text().strip()).expanduser()),
            self.extensions_edit.text().strip(),
        )

class ReconnaissanceModule(QWidget):
    """Nmap automation with optional AI summarisation."""

    def __init__(self, ai_manager: AIManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ai_manager = ai_manager
        self.sudo_password: Optional[str] = None
        self.scan_worker: Optional[ScanWorker] = None
        self.tool_worker: Optional[ScanWorker] = None
        self.current_tool_name: Optional[str] = None
        self.current_raw_output: str = ""
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        header = QLabel("Reconnaissance & Scanning")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header.setFont(header_font)
        header.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        description = QLabel(
            "Execute reconnaissance workflows starting with Nmap. Additional tooling will be added in subsequent iterations."
        )
        description.setWordWrap(True)
        layout.addWidget(header)
        layout.addWidget(description)

        tool_status_layout = QHBoxLayout()
        self.tool_status_label = QLabel("No additional reconnaissance task running.")
        self.tool_status_label.setStyleSheet("color: #a9f5d0;")
        self.tool_cancel_button = QPushButton("Cancel Current Task")
        self.tool_cancel_button.setEnabled(False)
        self.tool_cancel_button.clicked.connect(self._cancel_tool_task)
        tool_status_layout.addWidget(self.tool_status_label)
        tool_status_layout.addStretch()
        tool_status_layout.addWidget(self.tool_cancel_button)
        layout.addLayout(tool_status_layout)

        layout.addWidget(self._build_nmap_group())
        layout.addWidget(self._build_theharvester_group())
        layout.addWidget(self._build_reconng_group())
        layout.addWidget(self._build_amass_group())
        layout.addWidget(self._build_gobuster_group())
        self.output_browser = QTextBrowser()
        self.output_browser.setPlaceholderText("Scan output and AI analysis will appear here.")
        self.output_browser.setMinimumHeight(240)
        layout.addWidget(self.output_browser)
        layout.addStretch()

    def _build_nmap_group(self) -> QGroupBox:
        group = QGroupBox("Nmap Port Scanning")
        layout = QVBoxLayout(group)
        description = QLabel(
            "Perform port scanning, service detection, and OS fingerprinting. Choose automatic subnet scanning or customise the command."
        )
        description.setWordWrap(True)
        button_layout = QHBoxLayout()
        self.run_button = QPushButton("Run Nmap…")
        self.run_button.clicked.connect(self._open_nmap_dialog)
        self.run_button.setMinimumWidth(180)
        self.run_button.setMinimumHeight(36)
        self.cancel_button = QPushButton("Cancel Scan")
        self.cancel_button.clicked.connect(self._cancel_scan)
        self.cancel_button.setEnabled(False)
        self.cancel_button.setMinimumWidth(160)
        self.cancel_button.setMinimumHeight(36)
        button_layout.addWidget(self.run_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addStretch()
        layout.addWidget(description)
        layout.addLayout(button_layout)
        return group

    def _open_nmap_dialog(self) -> None:
        dialog = NmapDialog(self)
        if dialog.exec_() != QDialog.Accepted or not dialog.selection:
            return
        if dialog.selection == "auto":
            self._run_nmap_auto()
        else:
            self._run_nmap_custom(dialog.target, dialog.extra_args)

    def _run_nmap_auto(self) -> None:
        if self.scan_worker and self.scan_worker.isRunning():
            QMessageBox.warning(self, "Scan Running", "A scan is already in progress. Please cancel it first.")
            return
        if os.geteuid() != 0:
            password = self._ensure_sudo_password()
            if not password:
                return
        else:
            password = None
        self.output_browser.clear()
        self._append_output("[+] Starting automatic subnet scan…")
        self._append_output("[!] This may take several minutes depending on subnet size. Please wait...")
        self._append_output("[!] The GUI will remain responsive during the scan.")
        self.run_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.scan_worker = ScanWorker("nmap_subnet.sh", require_root=True, sudo_password=password)
        self.scan_worker.output_signal.connect(self._append_output)
        self.scan_worker.finished_signal.connect(lambda result: self._handle_scan_result("Nmap Auto Subnet Scan", result))
        self.scan_worker.start()

    def _run_nmap_custom(self, target: str, extra_args: str) -> None:
        if self.scan_worker and self.scan_worker.isRunning():
            QMessageBox.warning(self, "Scan Running", "A scan is already in progress. Please cancel it first.")
            return
        if os.geteuid() != 0:
            password = self._ensure_sudo_password()
            if not password:
                return
        else:
            password = None
        args: List[str] = [target]
        if extra_args:
            args.extend(extra_args.split())
        self.output_browser.clear()
        self._append_output(f"[+] Starting custom Nmap scan against {target}…")
        self._append_output("[!] The GUI will remain responsive during the scan.")
        self.run_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.scan_worker = ScanWorker("nmap_custom.sh", args=args, require_root=True, sudo_password=password)
        self.scan_worker.output_signal.connect(self._append_output)
        self.scan_worker.finished_signal.connect(lambda result: self._handle_scan_result(f"Nmap Custom Scan ({target})", result))
        self.scan_worker.start()
        
    def _cancel_scan(self) -> None:
        if self.scan_worker and self.scan_worker.isRunning():
            self.scan_worker.cancel()
            self._append_output("[!] Scan cancellation requested...")
        else:
            self.run_button.setEnabled(True)
            self.cancel_button.setEnabled(False)

    def _handle_scan_result(self, title: str, result: ScanResult) -> None:
        self.run_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        if not result.success:
            self._append_output(f"[!] Scan failed: {result.error or result.output}")
            return
        self._append_output("\n" + "="*60)
        self._append_output("[+] Nmap scan completed!")
        self._append_output("="*60 + "\n")
        self._append_output(result.output)
        self._append_output("\n[+] Report has been automatically saved to the reports directory.")
        self._append_output("[+] You can view it in the Reports tab.\n")

    def _append_output(self, text: str) -> None:
        self.output_browser.append(text)
        self.output_browser.ensureCursorVisible()

    def _start_tool(self, tool_name: str, script_name: str, args: List[str], require_root: bool = False) -> None:
        if self.tool_worker and self.tool_worker.isRunning():
            QMessageBox.warning(
                self,
                "Task Running",
                "Another reconnaissance task is currently running. Please wait for it to finish.",
            )
            return

        password = None
        if require_root and os.geteuid() != 0:
            password = self._ensure_sudo_password()
            if not password:
                return

        self._append_output(f"[+] Starting {tool_name}…")
        self.tool_status_label.setText(f"{tool_name} is running…")
        self.tool_status_label.setStyleSheet("color: #ffd700;")
        self.tool_cancel_button.setEnabled(True)
        self.current_tool_name = tool_name
        worker = ScanWorker(
            script_name,
            args=args,
            require_root=require_root,
            sudo_password=password,
        )
        worker.output_signal.connect(self._append_output)
        worker.finished_signal.connect(lambda result, name=tool_name: self._handle_tool_result(name, result))
        self.tool_worker = worker
        worker.start()

    def _handle_tool_result(self, tool_name: str, result: ScanResult) -> None:
        if result.success:
            if result.output:
                self._append_output(result.output)
            self._append_output(f"[+] {tool_name} completed successfully.")
            self.tool_status_label.setText(f"{tool_name} completed successfully.")
            self.tool_status_label.setStyleSheet("color: #a9f5d0;")
        else:
            message = result.error or result.output or "Unknown error."
            self._append_output(f"[!] {tool_name} failed: {message}")
            if "cancelled" in message.lower():
                self.tool_status_label.setText("Reconnaissance task cancelled.")
            else:
                self.tool_status_label.setText(f"{tool_name} failed.")
            self.tool_status_label.setStyleSheet("color: #ffaeaa;")
        self.tool_cancel_button.setEnabled(False)
        self.tool_worker = None
        self.current_tool_name = None
        QTimer.singleShot(4000, self._reset_tool_status)

    def _reset_tool_status(self) -> None:
        if self.tool_worker and self.tool_worker.isRunning():
            return
        self.tool_status_label.setText("No additional reconnaissance task running.")
        self.tool_status_label.setStyleSheet("color: #a9f5d0;")

    def _cancel_tool_task(self) -> None:
        if self.tool_worker and self.tool_worker.isRunning():
            self._append_output("[!] Cancelling current reconnaissance task...")
            self.tool_worker.cancel()
            self.tool_cancel_button.setEnabled(False)
            self.tool_status_label.setText("Cancelling task…")
            self.tool_status_label.setStyleSheet("color: #ffd700;")
        else:
            self.tool_cancel_button.setEnabled(False)
            self.tool_status_label.setText("No additional reconnaissance task running.")
            self.tool_status_label.setStyleSheet("color: #a9f5d0;")

    def _ensure_sudo_password(self) -> Optional[str]:
        if self.sudo_password:
            return self.sudo_password
        password, ok = QInputDialog.getText(
            self,
            "Sudo Password Required",
            "Enter sudo password to continue:",
            QLineEdit.Password,
        )
        if ok and password:
            self.sudo_password = password
            return password
        return None


    #################################################################
    # THEHARVESTER — Email, Subdomain, Personnel Intel Gathering
    #################################################################
    def _build_theharvester_group(self) -> QGroupBox:
        group = QGroupBox("TheHarvester – OSINT Enumeration")
        layout = QVBoxLayout(group)

        description = QLabel(
            "Collect emails, names, subdomains, and other public information from "
            "multiple search engines. Ideal for initial intelligence gathering."
        )
        description.setWordWrap(True)

        btn_layout = QHBoxLayout()
        run_button = QPushButton("Run TheHarvester…")
        run_button.clicked.connect(self._run_theharvester)
        run_button.setMinimumWidth(220)
        run_button.setMinimumHeight(36)

        btn_layout.addWidget(run_button)
        btn_layout.addStretch()

        layout.addWidget(description)
        layout.addLayout(btn_layout)
        return group

    def _run_theharvester(self) -> None:
        dialog = HarvesterDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return
        domain, sources, limit = dialog.values()
        self._start_tool("TheHarvester", "theharvester.sh", [domain, sources, str(limit)])

    def _run_reconng(self) -> None:
        dialog = ReconNgDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return
        domain, workspace = dialog.values()
        safe_workspace = workspace.replace(" ", "_")
        self._start_tool("Recon-ng", "reconng_basic.sh", [domain, safe_workspace])

    def _run_amass(self) -> None:
        dialog = AmassDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return
        domain, mode = dialog.values()
        self._start_tool("Amass", "amass_enum.sh", [domain, mode])

    def _run_gobuster(self) -> None:
        dialog = GobusterDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return
        mode, target, wordlist, extensions = dialog.values()
        args = [mode, target, wordlist]
        if extensions:
            args.append(extensions)
        self._start_tool("Gobuster", "gobuster_scan.sh", args)


    #################################################################
    # RECON-NG — Recon Framework
    #################################################################
    def _build_reconng_group(self) -> QGroupBox:
        group = QGroupBox("Recon-ng – Reconnaissance Framework")
        layout = QVBoxLayout(group)

        description = QLabel(
            "A modular reconnaissance framework with powerful automation and "
            "built-in intelligence gathering modules."
        )
        description.setWordWrap(True)

        btn_layout = QHBoxLayout()
        run_button = QPushButton("Run Recon-ng…")
        run_button.clicked.connect(self._run_reconng)
        run_button.setMinimumWidth(220)
        run_button.setMinimumHeight(36)

        btn_layout.addWidget(run_button)
        btn_layout.addStretch()

        layout.addWidget(description)
        layout.addLayout(btn_layout)
        return group


    #################################################################
    # AMASS — Subdomain Enumeration
    #################################################################
    def _build_amass_group(self) -> QGroupBox:
        group = QGroupBox("Amass – Subdomain Enumeration")
        layout = QVBoxLayout(group)

        description = QLabel(
            "Perform deep subdomain enumeration using passive, active, or "
            "brute-force reconnaissance techniques."
        )
        description.setWordWrap(True)

        btn_layout = QHBoxLayout()
        run_button = QPushButton("Run Amass…")
        run_button.clicked.connect(self._run_amass)
        run_button.setMinimumWidth(220)
        run_button.setMinimumHeight(36)

        btn_layout.addWidget(run_button)
        btn_layout.addStretch()

        layout.addWidget(description)
        layout.addLayout(btn_layout)
        return group


    #################################################################
    # GOBUSTER – Directory/Domain Brute Forcing
    #################################################################
    def _build_gobuster_group(self) -> QGroupBox:
        group = QGroupBox("Gobuster – Directory & DNS Enumeration")
        layout = QVBoxLayout(group)

        description = QLabel(
            "Brute-force directories, files, and DNS subdomains with high performance. "
            "Useful for discovering hidden paths and domain assets."
        )
        description.setWordWrap(True)

        btn_layout = QHBoxLayout()
        run_button = QPushButton("Run Gobuster…")
        run_button.clicked.connect(self._run_gobuster)
        run_button.setMinimumWidth(220)
        run_button.setMinimumHeight(36)

        btn_layout.addWidget(run_button)
        btn_layout.addStretch()

        layout.addWidget(description)
        layout.addLayout(btn_layout)
        return group
