from typing import Dict, List

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt5.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ai_manager import AIManager
from anonymity import AnonymityModule
from dashboard import DashboardTab
from module_panel import ModulePanel
from recon import ReconnaissanceModule
from reports import ReportsTab


class MainWindow(QMainWindow):
    """Primary window hosting tabbed interfaces for each ARTA module."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Automated Red Teaming Assistant (Prototype GUI)")
        self.resize(1320, 860)
        self.ai_manager = AIManager()

        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(16, 16, 16, 16)
        central_layout.setSpacing(0)
        self.setCentralWidget(central)

        outer_frame = QFrame()
        outer_frame.setObjectName("OuterFrame")
        outer_frame.setStyleSheet(
            """
            #OuterFrame {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #14080f,
                    stop: 0.45 #1b0c16,
                    stop: 1 #23101c
                );
                border: none;
                border-radius: 18px;
            }
            """
        )
        outer_layout = QVBoxLayout(outer_frame)
        outer_layout.setContentsMargins(24, 24, 24, 24)
        outer_layout.setSpacing(16)

        self.menu_visible = True
        self.nav_buttons: Dict[str, QPushButton] = {}

        top_bar = self._build_top_bar()

        content_frame = QFrame()
        content_frame.setObjectName("ContentFrame")
        content_frame.setStyleSheet(
            """
            #ContentFrame {
                background-color: #141a2b;
                border: none;
                border-radius: 12px;
            }
            """
        )

        content_layout = QHBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.menu_frame = self._build_menu()
        content_layout.addWidget(self.menu_frame)

        self.stacked_widget = QStackedWidget()
        self.pages: Dict[str, QWidget] = {}

        self._register_pages()
        content_layout.addWidget(self.stacked_widget)

        outer_layout.addWidget(top_bar)
        outer_layout.addWidget(content_frame)

        central_layout.addWidget(outer_frame)

        self._select_page("Dashboard")

    def _build_top_bar(self) -> QWidget:
        """Create the header bar with toggle button and logo space."""
        top_bar = QFrame()
        top_bar.setObjectName("TopBar")
        top_bar.setStyleSheet(
            """
            #TopBar {
                background-color: rgba(32, 12, 20, 0.88);
                border: none;
            }
            """
        )
        layout = QHBoxLayout(top_bar)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(16)

        self.menu_toggle_btn = QPushButton("☰")
        self.menu_toggle_btn.setFixedSize(52, 52)
        self.menu_toggle_btn.setCheckable(True)
        self.menu_toggle_btn.setChecked(True)
        self.menu_toggle_btn.setStyleSheet(
            """
            QPushButton {
                font-size: 24px;
                background-color: #ff3b3f;
                color: #ffffff;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #ff5c64;
            }
            """
        )
        self.menu_toggle_btn.clicked.connect(self._toggle_menu_visibility)

        logo_label = QLabel()
        logo_label.setPixmap(self._build_logo_pixmap())
        logo_label.setFixedSize(120, 60)
        logo_label.setAlignment(Qt.AlignCenter)

        title = QLabel("Automated Red Teaming Assistant")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #f1f3f6;")

        subtitle = QLabel("Prototype GUI • Phase 1")
        subtitle.setStyleSheet("color: #8892a6; font-size: 12px;")

        text_container = QVBoxLayout()
        text_container.setSpacing(2)
        text_container.addWidget(title)
        text_container.addWidget(subtitle)

        layout.addWidget(self.menu_toggle_btn)
        layout.addWidget(logo_label)
        layout.addLayout(text_container)
        layout.addStretch()

        return top_bar

    def _build_menu(self) -> QWidget:
        """Create the vertical navigation menu."""
        menu = QFrame()
        menu.setObjectName("MenuFrame")
        menu.setFixedWidth(280)
        menu.setStyleSheet(
            """
            #MenuFrame {
                background-color: rgba(28, 11, 19, 0.94);
                border-right: 1px solid #3a1a25;
                border-top-left-radius: 12px;
                border-bottom-left-radius: 12px;
            }
            QPushButton {
                background-color: transparent;
                color: #f4d7db;
                text-align: left;
                padding: 14px 18px;
                font-size: 14px;
                border: none;
                border-left: 4px solid transparent;
            }
            QPushButton:hover {
                background-color: rgba(58, 24, 36, 0.86);
            }
            QPushButton:checked {
                background-color: rgba(58, 24, 36, 0.94);
                border-left: 4px solid #ff3b3f;
                color: #ffffff;
            }
            """
        )

        layout = QVBoxLayout(menu)
        layout.setContentsMargins(18, 24, 18, 24)
        layout.setSpacing(8)

        section_label = QLabel("Navigation")
        section_label.setStyleSheet("color: #b58a92; font-weight: bold;")
        layout.addWidget(section_label)

        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        nav_items = [
            ("Dashboard", "Dashboard"),
            ("Anonymity & Evasion", "Anonymity & Evasion"),
            ("Reconnaissance & Scanning", "Reconnaissance & Scanning"),
            ("Vulnerability Scanning", "Vulnerability Scanning"),
            ("Wireless Attacks", "Wireless Attacks"),
            ("Network Attacks", "Network Attacks"),
            ("System Hacking", "System Hacking"),
            ("Password Cracking", "Password Cracking"),
            ("Reports", "Reports"),
        ]

        for page_key, label in nav_items:
            button = QPushButton(label)
            button.setCheckable(True)
            button.clicked.connect(lambda _, key=page_key: self._select_page(key))
            layout.addWidget(button)
            self.button_group.addButton(button)
            self.nav_buttons[page_key] = button

        layout.addStretch()
        helper = QLabel("Tip: Collapse the menu with the toggle button to maximise workspace.")
        helper.setWordWrap(True)
        helper.setStyleSheet("color: #b58a92; font-size: 11px;")
        layout.addWidget(helper)

        return menu

    def _register_pages(self) -> None:
        """Populate the stacked widget with all application pages."""
        self.anonymity_module = AnonymityModule()
        self.recon_module = ReconnaissanceModule(self.ai_manager)
        pages: Dict[str, QWidget] = {
            "Dashboard": DashboardTab(self.ai_manager),
            "Anonymity & Evasion": self.anonymity_module,
            "Reconnaissance & Scanning": self.recon_module,
            "Reports": ReportsTab(self.ai_manager),
        }

        modules: List[Dict[str, List[str] | str]] = [
            {
                "name": "Vulnerability Scanning",
                "description": (
                    "Correlate data from OpenVAS and Lynis to identify vulnerabilities, track severity, "
                    "and prepare inputs for AI-driven prioritisation."
                ),
                "objectives": [
                    "Import reconnaissance findings into scan templates",
                    "Visualise scanning progress and outcomes",
                    "Normalise vulnerability results for downstream analysis",
                ],
                "tools": [
                    "OpenVAS workflow wrapper",
                    "Lynis audit runner",
                    "Result parsing pipelines",
                    "Severity scoring utilities",
                ],
            },
            {
                "name": "Wireless Attacks",
                "description": (
                    "Manage monitor mode, capture handshakes, and perform wireless offensive actions "
                    "using the Aircrack-ng suite."
                ),
                "objectives": [
                    "Detect and select wireless interfaces",
                    "Capture and manage handshake files",
                    "Guide users through ethical wireless testing scenarios",
                ],
                "tools": [
                    "Airmon-ng interface handler",
                    "Airodump-ng capture controller",
                    "Aireplay-ng attack presets",
                    "Aircrack-ng cracking wizard",
                ],
            },
            {
                "name": "Network Attacks",
                "description": (
                    "Coordinate ARP spoofing operations and traffic monitoring while enforcing safeguards "
                    "against collateral impact."
                ),
                "objectives": [
                    "Configure gateway/target pairs safely",
                    "Visualise intercepted session data",
                    "Log actions for audit and rollback",
                ],
                "tools": [
                    "ARP spoofing orchestrator",
                    "Packet inspection console",
                    "Mitigation checklist",
                ],
            },
            {
                "name": "System Hacking",
                "description": (
                    "Run Responder for credential harvesting and generate cross-platform reverse shell "
                    "payloads with operational guidance."
                ),
                "objectives": [
                    "Centrally manage listener configurations",
                    "Template reverse shell payloads",
                    "Document captured credentials securely",
                ],
                "tools": [
                    "Responder automation",
                    "Reverse shell generator",
                    "Listener setup assistant",
                ],
            },
            {
                "name": "Password Cracking",
                "description": (
                    "Leverage multi-tool cracking workflows with John, Hydra, Hashcat, Medusa, and Crunch "
                    "while monitoring resource usage."
                ),
                "objectives": [
                    "Support diverse hash and protocol types",
                    "Track cracking progress and wordlist usage",
                    "Store cracked credentials with safeguards",
                ],
                "tools": [
                    "John the Ripper presets",
                    "Hydra protocol runners",
                    "Hashcat mode catalogue",
                    "Medusa concurrent job manager",
                    "Crunch wordlist builder",
                ],
            },
        ]

        for module in modules:
            if module["name"] == "Anonymity & Evasion":
                continue
            if module["name"] == "Reconnaissance & Scanning":
                continue
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            module_panel = ModulePanel(
                module["name"],  # type: ignore[arg-type]
                module["description"],  # type: ignore[arg-type]
                module["objectives"],  # type: ignore[arg-type]
                module["tools"],  # type: ignore[arg-type]
            )
            module_panel.setObjectName(module["name"])  # type: ignore[arg-type]
            scroll_area.setWidget(module_panel)
            pages[module["name"]] = scroll_area  # type: ignore[index]

        for key, widget in pages.items():
            self.pages[key] = widget
            self.stacked_widget.addWidget(widget)

    def _select_page(self, key: str) -> None:
        """Switch the stacked widget page and update navigation state."""
        widget = self.pages.get(key)
        if not widget:
            return
        self.stacked_widget.setCurrentWidget(widget)

        button = self.nav_buttons.get(key)
        if button and not button.isChecked():
            button.setChecked(True)

    def _toggle_menu_visibility(self) -> None:
        """Hide or show the left navigation menu."""
        self.menu_visible = not self.menu_visible
        self.menu_frame.setVisible(self.menu_visible)
        self.menu_toggle_btn.setChecked(self.menu_visible)

    @staticmethod
    def _build_logo_pixmap() -> QPixmap:
        """Generate a placeholder logo to reserve space in the header."""
        pixmap = QPixmap(120, 60)
        pixmap.fill(QColor("#12070b"))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#ff3b3f"))
        painter.setPen(QColor("#ff3b3f"))
        painter.drawRoundedRect(22, 12, 76, 36, 14, 14)
        painter.setPen(QColor("#2c0507"))
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "ARTA")
        painter.end()
        return pixmap

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Gracefully stop background processes when the window closes."""
        if hasattr(self, "anonymity_module") and self.anonymity_module:
            self.anonymity_module.shutdown()
        super().closeEvent(event)

