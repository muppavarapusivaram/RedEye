import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
    QRadioButton,
)

from core.ai_manager import AIManager


SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts" / "recon"
REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports"


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
        """Execute AI analysis in the background thread."""
        try:
            # Debug: Check if AI manager is properly configured
            is_enabled = self.ai_manager.is_enabled()
            provider = self.ai_manager.provider_name()
            print(f"[AI Worker] Starting analysis. Enabled: {is_enabled}, Provider: {provider}")
            print(f"[AI Worker] Output length: {len(self.raw_output)} chars")
            
            if not is_enabled:
                self.finished_signal.emit(False, "", "AI is not enabled. Please configure AI in Dashboard.")
                return
                
            success, result = self.ai_manager.generate_analysis(self.tool_name, self.raw_output)
            print(f"[AI Worker] Analysis complete. Success: {success}, Result length: {len(result) if result else 0}")
            
            if success:
                self.finished_signal.emit(True, result, "")
            else:
                self.finished_signal.emit(False, "", result)
        except Exception as e:
            print(f"[AI Worker] Exception: {e}")
            import traceback
            traceback.print_exc()
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
        """Cancel the running scan."""
        self._cancelled = True
        
    def run(self):
        """Execute the scan script in the background thread."""
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
            command = ["sudo", "-S", str(script_path), *self.args]
            stdin_data = self.sudo_password + "\n"
        else:
            command = [str(script_path), *self.args]
            
        try:
            # Use Popen for real-time output streaming
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE if stdin_data else None,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )
            
            # Write sudo password if needed
            if stdin_data:
                process.stdin.write(stdin_data)
                process.stdin.flush()
                process.stdin.close()
            
            # Stream output in real-time
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
                
            # Wait for process to finish (stdout already consumed)
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


class ReconnaissanceModule(QWidget):
    """Nmap automation with optional AI summarisation."""

    def __init__(self, ai_manager: AIManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ai_manager = ai_manager
        self.sudo_password: Optional[str] = None
        self.scan_worker: Optional[ScanWorker] = None
        self.current_raw_output: str = ""  # Store raw output for AI fallback

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
        layout.addWidget(self._build_nmap_group())

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
        
        self.cancel_button = QPushButton("Cancel Scan")
        self.cancel_button.clicked.connect(self._cancel_scan)
        self.cancel_button.setEnabled(False)
        
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
        # Re-enable buttons when scan finishes
        self.run_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        
        if not result.success:
            self._append_output(f"[!] Scan failed: {result.error or result.output}")
            return

        # The bash script already handles saving the report and prints status messages
        # Just display the output which includes the save confirmation
        self._append_output("\n" + "="*60)
        self._append_output("[+] Nmap scan completed!")
        self._append_output("="*60 + "\n")
        self._append_output(result.output)
        self._append_output("\n[+] Report has been automatically saved to the reports directory.")
        self._append_output("[+] You can view it in the Reports tab.\n")

    def _run_ai_analysis(self, title: str, raw_output: str, timestamp: str) -> None:
        """Run AI analysis in a background thread."""
        self.ai_worker = AIAnalysisWorker(self.ai_manager, "Nmap", raw_output)
        self.ai_worker.finished_signal.connect(
            lambda success, report, error: self._handle_ai_result(title, success, report, error, timestamp)
        )
        self.ai_worker.start()
        
    def _handle_ai_result(self, title: str, success: bool, report: str, error: str, timestamp: str) -> None:
        """Handle AI analysis result and save organized report."""
        if success and report:
            try:
                # Ensure reports directory exists
                REPORTS_DIR.mkdir(parents=True, exist_ok=True)
                
                # Save AI-generated organized report
                report_path = REPORTS_DIR / f"nmap_ai_report_{timestamp}.md"
                report_path.write_text(report, encoding="utf-8")
                
                self._append_output("\n" + "="*60)
                self._append_output("[+] AI Analysis Complete!")
                self._append_output("="*60 + "\n")
                self._append_output("AI-Generated Organized Report:")
                self._append_output("-"*60)
                self._append_output(report)
                self._append_output("-"*60 + "\n")
                self._append_output(f"[+] Organized report saved to: {report_path}")
                self._append_output(f"[+] Full path: {report_path.absolute()}")
                self._append_output(f"[+] Report file: {report_path.name}\n")
            except Exception as e:
                self._append_output(f"\n[!] Failed to save AI report: {e}")
                self._append_output(f"[!] Error details: {type(e).__name__}")
                # Fallback: save raw output
                try:
                    report_path = REPORTS_DIR / f"nmap_output_{timestamp}.txt"
                    report_path.write_text(self.current_raw_output, encoding="utf-8")
                    self._append_output(f"[+] Raw scan output saved to {report_path} as fallback.")
                except Exception as e2:
                    self._append_output(f"[!] Failed to save fallback report: {e2}")
        else:
            self._append_output(f"\n[!] AI analysis failed: {error}")
            self._append_output(f"[!] Error details: {error if error else 'Unknown error'}")
            # Fallback: save raw output
            try:
                REPORTS_DIR.mkdir(parents=True, exist_ok=True)
                report_path = REPORTS_DIR / f"nmap_output_{timestamp}.txt"
                report_path.write_text(self.current_raw_output, encoding="utf-8")
                self._append_output(f"[+] Raw scan output saved to {report_path} as fallback.")
            except Exception as e:
                self._append_output(f"[!] Failed to save fallback report: {e}")

    def _append_output(self, text: str) -> None:
        self.output_browser.append(text)
        self.output_browser.ensureCursorVisible()

    def _run_script(
        self,
        script_name: str,
        args: Optional[List[str]] = None,
        require_root: bool = False,
    ) -> ScanResult:
        script_path = SCRIPT_DIR / script_name
        if not script_path.exists():
            return ScanResult(False, "", f"Script not found: {script_path}")

        command: List[str]
        stdin_data: Optional[str] = None
        arg_list = args or []

        if require_root and os.geteuid() != 0:
            password = self._ensure_sudo_password()
            if not password:
                return ScanResult(False, "", "Operation cancelled (sudo password required).")
            command = ["sudo", "-S", str(script_path), *arg_list]
            stdin_data = password + "\n"
        else:
            command = [str(script_path), *arg_list]

        try:
            # Increased timeout to 10 minutes for subnet scans which can take longer
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                input=stdin_data,
                timeout=600,
            )
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            output = stdout if stdout else stderr
            if result.returncode != 0:
                if "incorrect password" in (output or "").lower():
                    self.sudo_password = None
                    return ScanResult(False, "", "Incorrect sudo password. Please retry.")
                return ScanResult(False, stdout, stderr or "Unknown error")
            return ScanResult(True, stdout or "Scan completed with no output")
        except FileNotFoundError:
            return ScanResult(False, "", f"Unable to execute script: {script_path}")
        except subprocess.TimeoutExpired:
            return ScanResult(False, "", "Scan timed out after 10 minutes. For large subnets, consider using a custom scan with a smaller target range or faster scan options.")

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


