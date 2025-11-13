import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from PyQt5.QtCore import Qt, QProcess
from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)


@dataclass
class ProxyEntry:
    scheme: str
    host: str
    port: int


@dataclass
class ProxyConfiguration:
    chain_mode: str
    entries: List[ProxyEntry]


SCRIPT_DIR = Path(__file__).resolve().parent / "scripts"


class ProxyConfigDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configure Proxychains")
        self.setModal(True)
        self.proxy_configuration: Optional[ProxyConfiguration] = None
        self.proxy_entries: List[ProxyEntry] = []

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.scheme_combo = QComboBox()
        self.scheme_combo.addItems(["socks5", "socks4"])

        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("127.0.0.1")

        self.port_edit = QLineEdit()
        self.port_edit.setPlaceholderText("9050")
        self.port_edit.setValidator(QIntValidator(1, 65535, self))

        self.chain_combo = QComboBox()
        self.chain_combo.addItems(["dynamic_chain", "strict_chain", "random_chain"])

        add_row = QHBoxLayout()
        add_button = QPushButton("Add Proxy")
        add_button.clicked.connect(self._on_add_proxy)
        add_row.addStretch()
        add_row.addWidget(add_button)

        self.proxy_list = QListWidget()
        self.proxy_list.setMinimumHeight(120)

        form.addRow("Proxy Type:", self.scheme_combo)
        form.addRow("Host/IP:", self.host_edit)
        form.addRow("Port:", self.port_edit)
        form.addRow("Chain Mode:", self.chain_combo)

        layout.addLayout(form)
        layout.addLayout(add_row)
        layout.addWidget(QLabel("Configured Proxies:"))
        layout.addWidget(self.proxy_list)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #ff5c64;")
        layout.addWidget(self.error_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_add_proxy(self) -> None:
        host = self.host_edit.text().strip()
        port_text = self.port_edit.text().strip()
        if not host or not port_text:
            self.error_label.setText("Host and port are required to add a proxy.")
            return
        try:
            port = int(port_text)
        except ValueError:
            self.error_label.setText("Port must be numeric.")
            return
        entry = ProxyEntry(scheme=self.scheme_combo.currentText(), host=host, port=port)
        self.proxy_entries.append(entry)
        self.proxy_list.addItem(QListWidgetItem(f"{entry.scheme} {entry.host}:{entry.port}"))
        self.host_edit.clear()
        self.port_edit.clear()
        self.error_label.clear()

    def _on_accept(self) -> None:
        if not self.proxy_entries:
            self.error_label.setText("Add at least one proxy before saving.")
            return
        self.proxy_configuration = ProxyConfiguration(
            chain_mode=self.chain_combo.currentText(),
            entries=self.proxy_entries.copy(),
        )
        self.accept()


class AnonymityModule(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.openvpn_process: Optional[QProcess] = None
        self.sudo_password: Optional[str] = None

        layout = QVBoxLayout(self)
        layout.setSpacing(18)

        intro = QLabel(
            "Manage operational security tooling. Configure proxychains, start the TOR service, "
            "or launch an OpenVPN tunnel. Ensure you have the necessary privileges before executing "
            "these actions."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        proxy_group = self._build_proxy_section()
        tor_group = self._build_tor_section()
        vpn_group = self._build_vpn_section()

        layout.addWidget(proxy_group)
        layout.addWidget(tor_group)
        layout.addWidget(vpn_group)

        self.instructions_browser = QTextBrowser()
        self.instructions_browser.setMinimumHeight(180)
        self.instructions_browser.setPlaceholderText(
            "Action-specific guidance will appear here after each operation."
        )
        layout.addWidget(self.instructions_browser)
        layout.addStretch()

    def _build_proxy_section(self) -> QGroupBox:
        group = QGroupBox("Proxychains Configuration")
        layout = QVBoxLayout(group)
        description = QLabel(
            "Define the SOCKS proxy and chain mode used by proxychains. Configuration requires elevated privileges."
        )
        description.setWordWrap(True)
        self.proxy_status = QLabel("Status: awaiting configuration")
        self.proxy_status.setStyleSheet("color: #f7eef1;")
        configure_button = QPushButton("Configure Proxychains…")
        configure_button.clicked.connect(self._on_configure_proxychains)
        layout.addWidget(description)
        layout.addWidget(configure_button)
        layout.addWidget(self.proxy_status)
        return group

    def _build_tor_section(self) -> QGroupBox:
        group = QGroupBox("TOR Service")
        layout = QVBoxLayout(group)
        description = QLabel(
            "Start the TOR service to route traffic through the onion network. Service control typically requires sudo privileges."
        )
        description.setWordWrap(True)
        self.tor_status = QLabel("Status: inactive")
        self.tor_status.setStyleSheet("color: #ffaeaa;")
        controls = QHBoxLayout()
        start_button = QPushButton("Start TOR")
        start_button.clicked.connect(self._on_start_tor)
        stop_button = QPushButton("Stop TOR")
        stop_button.clicked.connect(self._on_stop_tor)
        refresh_button = QPushButton("Refresh Status")
        refresh_button.clicked.connect(self._refresh_tor_status)
        controls.addWidget(start_button)
        controls.addWidget(stop_button)
        controls.addWidget(refresh_button)
        controls.addStretch()
        layout.addWidget(description)
        layout.addLayout(controls)
        layout.addWidget(self.tor_status)
        return group

    def _build_vpn_section(self) -> QGroupBox:
        group = QGroupBox("OpenVPN Tunnel")
        layout = QVBoxLayout(group)
        description = QLabel(
            "Launch an OpenVPN tunnel using an `.ovpn` profile. Ensure the profile contains valid credentials."
        )
        description.setWordWrap(True)
        self.vpn_status = QLabel("Status: no tunnel running")
        self.vpn_status.setStyleSheet("color: #f7eef1;")
        controls = QHBoxLayout()
        launch_button = QPushButton("Start OpenVPN…")
        launch_button.clicked.connect(self._on_start_openvpn)
        stop_button = QPushButton("Stop OpenVPN")
        stop_button.clicked.connect(self._on_stop_openvpn)
        controls.addWidget(launch_button)
        controls.addWidget(stop_button)
        controls.addStretch()
        layout.addWidget(description)
        layout.addLayout(controls)
        layout.addWidget(self.vpn_status)
        return group

    def _on_configure_proxychains(self) -> None:
        dialog = ProxyConfigDialog(self)
        if dialog.exec_() != QDialog.Accepted or not dialog.proxy_configuration:
            return
        result, message, guidance = self._apply_proxychains_settings(dialog.proxy_configuration)
        self._update_status_label(self.proxy_status, result, message)
        if guidance:
            self._set_instructions("Proxychains Ready", guidance)

    def _apply_proxychains_settings(self, settings: ProxyConfiguration) -> Tuple[bool, str, str]:
        script_args = [
            settings.chain_mode,
            *[f"{entry.scheme},{entry.host},{entry.port}" for entry in settings.entries],
        ]
        success, output = self._run_script("configure_proxychains.sh", script_args, require_root=True)
        if not success:
            return False, output or "Failed to update proxychains.", ""
        guidance = (
            "Proxychains updated successfully.\n\n"
            "Usage tips:\n"
            " • Run commands through proxychains: `proxychains nmap target.com`\n"
            " • Chain mode set to `{chain}`; adjust as needed via the configuration dialog.\n"
            " • Confirm connectivity with: `proxychains curl https://check.torproject.org/`\n"
            " • Multiple proxies rotate according to the selected chain behaviour."
        ).format(chain=settings.chain_mode)
        proxy_summary = ", ".join(f"{entry.scheme}://{entry.host}:{entry.port}" for entry in settings.entries)
        message = output.strip() if output else (
            f"Proxychains configured with chain mode {settings.chain_mode} and proxies [{proxy_summary}]."
        )
        return True, message, guidance

    def _on_start_tor(self) -> None:
        success, output = self._run_script("start_tor.sh", require_root=True)
        if not success:
            self._update_status_label(self.tor_status, False, f"Failed to start TOR: {output}")
            return
        self._refresh_tor_status()
        self._set_instructions(
            "TOR Active",
            "TOR service started.\n\n"
            "Usage tips:\n"
            " • Use Tor Browser or set your application SOCKS5 proxy to 127.0.0.1:9050.\n"
            " • Confirm exit IP with `torsocks curl https://check.torproject.org/`.\n"
            " • Combine with proxychains by using `torsocks proxychains <command>` if needed.\n"
            " • Stop service with `sudo systemctl stop tor` (or the Stop controls you configure) when finished."
        )

    def _refresh_tor_status(self) -> None:
        success, output = self._run_script("tor_status.sh")
        detail = output.strip() if output else "inactive"
        if success:
            self._update_status_label(self.tor_status, True, "TOR is active. Traffic must be proxied via 127.0.0.1:9050.")
        else:
            self._update_status_label(self.tor_status, False, f"TOR status: {detail}.")

    def _on_stop_tor(self) -> None:
        success, output = self._run_script("stop_tor.sh", require_root=True)
        message = output or ("TOR service stopped." if success else "Failed to stop TOR service.")
        self._update_status_label(self.tor_status, success, message)
        self._refresh_tor_status()
        self._set_instructions(
            "TOR Stopped",
            "TOR service has been halted.\n\n"
            "Post-actions:\n"
            " • Close any applications that were using TOR proxies to avoid connection errors.\n"
            " • Restore your browser or system proxy settings if they were pointed at 127.0.0.1:9050.\n"
            " • Restart TOR from this panel if you need to resume anonymous routing."
        )

    def _on_start_openvpn(self) -> None:
        if self.openvpn_process and self.openvpn_process.state() == QProcess.Running:
            QMessageBox.warning(self, "OpenVPN Active", "An OpenVPN process is already running.")
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select OpenVPN Profile",
            str(Path.home()),
            "OpenVPN profiles (*.ovpn);;All files (*.*)",
        )
        if not file_path:
            return
        self._start_openvpn_process(Path(file_path))

    def _start_openvpn_process(self, profile_path: Path) -> None:
        if not profile_path.exists():
            self._update_status_label(self.vpn_status, False, f"Profile does not exist: {profile_path}")
            return
        script_path = SCRIPT_DIR / "start_openvpn.sh"
        if not script_path.exists():
            self._update_status_label(self.vpn_status, False, f"Start script not found: {script_path}")
            return
        self.openvpn_process = QProcess(self)
        if os.geteuid() == 0:
            program = "bash"
            arguments = [str(script_path), str(profile_path)]
            password = None
        else:
            password = self._ensure_sudo_password()
            if not password:
                self._update_status_label(self.vpn_status, False, "OpenVPN launch cancelled (no sudo password).")
                self.openvpn_process = None
                return
            program = "sudo"
            arguments = ["-S", "bash", str(script_path), str(profile_path)]
        self.openvpn_process.started.connect(
            lambda: self._update_status_label(self.vpn_status, True, f"OpenVPN started with {profile_path.name}.")
        )
        self.openvpn_process.errorOccurred.connect(
            lambda error: self._update_status_label(self.vpn_status, False, f"OpenVPN error: {error}.")
        )
        self.openvpn_process.finished.connect(
            lambda code, status: self._update_status_label(
                self.vpn_status,
                False,
                f"OpenVPN exited (code {code}, status {status}).",
            )
        )
        self.openvpn_process.start(program, arguments)
        if not self.openvpn_process.waitForStarted(5000):
            self._update_status_label(self.vpn_status, False, "Failed to launch OpenVPN (insufficient privileges?).")
            self.openvpn_process = None
            return
        if password:
            self.openvpn_process.write((password + "\n").encode())
        self._set_instructions(
            "OpenVPN Tunnel Active",
            "OpenVPN process launched.\n\n"
            "Usage tips:\n"
            " • Monitor logs in this terminal or via `journalctl -u openvpn`.\n"
            " • Verify new IP with `curl ifconfig.me`.\n"
            " • Stop the tunnel here or with `sudo killall openvpn`."
        )

    def _on_stop_openvpn(self) -> None:
        if self.openvpn_process and self.openvpn_process.state() == QProcess.Running:
            self.openvpn_process.terminate()
            if not self.openvpn_process.waitForFinished(3000):
                self.openvpn_process.kill()
            self.openvpn_process = None
        success, output = self._run_script("stop_openvpn.sh", require_root=True)
        self._update_status_label(
            self.vpn_status,
            success,
            output or ("OpenVPN tunnel stopped." if success else "Failed to stop OpenVPN."),
        )
        self._set_instructions(
            "OpenVPN Tunnel Stopped",
            "OpenVPN process terminated.\n\n"
            "Remember to revert any routing changes and confirm your external IP has reverted."
        )

    def _set_instructions(self, heading: str, body: str) -> None:
        self.instructions_browser.setHtml(
            f"<h3 style='color:#ff8689;'>{heading}</h3>"
            f"<pre style='font-size:13px; color:#f7eef1;'>{body}</pre>"
        )

    @staticmethod
    def _update_status_label(label: QLabel, success: bool, text: str) -> None:
        color = "#a9f5d0" if success else "#ffaeaa"
        label.setStyleSheet(f"color: {color};")
        label.setText(text)

    def _run_script(
        self,
        script_name: str,
        args: Optional[List[str]] = None,
        require_root: bool = False,
    ) -> Tuple[bool, str]:
        script_path = SCRIPT_DIR / script_name
        if not script_path.exists():
            return False, f"Script not found: {script_path}"
        command: List[str]
        input_data: Optional[str] = None
        arg_list = args or []
        if require_root and os.geteuid() != 0:
            password = self._ensure_sudo_password()
            if not password:
                return False, "Operation cancelled (sudo password required)."
            command = ["sudo", "-S", "bash", str(script_path), *arg_list]
            input_data = password + "\n"
        else:
            command = ["bash", str(script_path), *arg_list]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                input=input_data,
                timeout=30,
            )
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            output = stdout if stdout else stderr
            if result.returncode != 0 and "incorrect password" in output.lower():
                self.sudo_password = None
                return False, "Incorrect sudo password. Please retry."
            return result.returncode == 0, output
        except FileNotFoundError:
            return False, f"Unable to execute script: {script_path}"
        except subprocess.TimeoutExpired:
            return False, "Script timed out."

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

    def shutdown(self) -> None:
        if self.openvpn_process and self.openvpn_process.state() == QProcess.Running:
            self.openvpn_process.terminate()
            self.openvpn_process.waitForFinished(2000)
            self.openvpn_process = None


