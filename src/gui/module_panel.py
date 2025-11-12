from typing import List

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QLabel,
    QPushButton,
    QGroupBox,
    QVBoxLayout,
    QWidget,
)


class ModulePanel(QWidget):
    """Reusable widget that summarizes a red teaming module and its tooling."""

    def __init__(
        self,
        title: str,
        description: str,
        objectives: List[str],
        tools: List[str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        root_layout = QVBoxLayout(self)
        root_layout.setSpacing(12)

        heading = QLabel(title)
        heading_font = QFont()
        heading_font.setPointSize(13)
        heading_font.setBold(True)
        heading.setFont(heading_font)
        heading.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        description_label = QLabel(description)
        description_label.setWordWrap(True)

        objectives_group = QGroupBox("Learning Objectives")
        objectives_layout = QVBoxLayout(objectives_group)
        for objective in objectives:
            item = QLabel(f"• {objective}")
            item.setWordWrap(True)
            objectives_layout.addWidget(item)

        tools_group = QGroupBox("Toolchain Preview")
        tools_layout = QVBoxLayout(tools_group)
        for tool in tools:
            tool_label = QLabel(f"• {tool}")
            tool_label.setWordWrap(True)
            tools_layout.addWidget(tool_label)

        actions_group = QGroupBox("Prototype Actions")
        actions_layout = QVBoxLayout(actions_group)
        actions_layout.addWidget(QLabel("Execute Tool (placeholder)"))
        actions_layout.addWidget(QPushButton("Configure Module…"))
        actions_layout.addWidget(QPushButton("View Saved Results"))

        root_layout.addWidget(heading)
        root_layout.addWidget(description_label)
        root_layout.addWidget(objectives_group)
        root_layout.addWidget(tools_group)
        root_layout.addWidget(actions_group)
        root_layout.addStretch()

