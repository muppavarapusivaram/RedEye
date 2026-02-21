import sys

from PyQt5.QtWidgets import QApplication

from core.disclaimer import ensure_disclaimer_acknowledged
from main_window import MainWindow


APP_STYLESHEET = """
QWidget {
    background-color: #0a0408;
    color: #f7eef1;
}
QGroupBox {
    border: 1px solid rgba(90, 42, 54, 0.6);
    border-radius: 8px;
    margin-top: 12px;
    padding: 12px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #ffe9ed;
}
QTextBrowser {
    background-color: rgba(34, 12, 22, 0.9);
    border: 1px solid rgba(90, 42, 54, 0.45);
    border-radius: 8px;
}
QListWidget {
    background-color: rgba(30, 10, 20, 0.95);
    border: 1px solid rgba(90, 42, 54, 0.45);
    border-radius: 8px;
}
"""


def apply_global_styles(app: QApplication) -> None:
    """Apply the shared stylesheet to the QApplication."""
    app.setStyleSheet(APP_STYLESHEET)


def main() -> None:
    """Entry point for launching the PyQt application."""
    app = QApplication(sys.argv)
    app.setApplicationName("RedEye")
    app.setOrganizationName("RedEye")
    apply_global_styles(app)

    if not ensure_disclaimer_acknowledged():
        sys.exit(0)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

