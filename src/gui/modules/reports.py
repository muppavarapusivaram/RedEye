from pathlib import Path
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
    QMessageBox,
)

from core.ai_manager import AIManager


REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports"


class AIAnalysisWorker(QThread):
    """Background thread worker for AI analysis to keep GUI responsive."""
    
    finished_signal = pyqtSignal(bool, str, str)  # success, summary, error_message
    
    def __init__(self, ai_manager: AIManager, report_name: str, report_content: str):
        super().__init__()
        self.ai_manager = ai_manager
        self.report_name = report_name
        self.report_content = report_content
    
    def run(self):
        """Execute AI analysis in the background thread."""
        try:
            if not self.ai_manager.is_enabled():
                self.finished_signal.emit(False, "", "AI is not enabled. Please configure AI in Dashboard.")
                return
                
            # Use "Report Analysis" as tool name for better AI context
            success, result = self.ai_manager.generate_analysis("Report Analysis", self.report_content)
            
            if success:
                self.finished_signal.emit(True, result, "")
            else:
                self.finished_signal.emit(False, "", result)
        except Exception as e:
            self.finished_signal.emit(False, "", f"AI analysis exception: {e}")


class ReportsTab(QWidget):
    """Display and manage generated reconnaissance reports."""

    def __init__(self, ai_manager: AIManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ai_manager = ai_manager
        self.current_report_path: Path | None = None
        self.current_report_content: str = ""
        self.ai_summary: str = ""
        self.showing_ai_summary: bool = False
        self.ai_worker: AIAnalysisWorker | None = None
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Header
        header = QLabel("Generated Reports")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header)
        
        # Reports list and preview
        content_layout = QHBoxLayout()
        
        # Left: Reports list
        list_group = QGroupBox("Available Reports")
        list_layout = QVBoxLayout(list_group)
        
        button_layout = QHBoxLayout()
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self._refresh_reports)
        open_button = QPushButton("Open Report File")
        open_button.clicked.connect(self._open_report_file)
        button_layout.addWidget(refresh_button)
        button_layout.addWidget(open_button)
        button_layout.addStretch()
        
        self.reports_list = QListWidget()
        self.reports_list.itemClicked.connect(self._on_report_selected)
        
        list_layout.addLayout(button_layout)
        list_layout.addWidget(self.reports_list)
        
        # Right: Report preview
        preview_group = QGroupBox("Report Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        # Preview controls
        preview_controls = QHBoxLayout()
        self.analyze_button = QPushButton("Analyze with AI")
        self.analyze_button.setEnabled(False)
        self.analyze_button.clicked.connect(self._analyze_with_ai)
        self.view_raw_button = QPushButton("View Raw Report")
        self.view_raw_button.setEnabled(False)
        self.view_raw_button.clicked.connect(self._view_raw_report)
        preview_controls.addWidget(self.analyze_button)
        preview_controls.addWidget(self.view_raw_button)
        preview_controls.addStretch()
        preview_layout.addLayout(preview_controls)
        
        self.report_preview = QTextBrowser()
        self.report_preview.setPlaceholderText("Select a report from the list to view its contents.")
        
        preview_layout.addWidget(self.report_preview)
        
        content_layout.addWidget(list_group, 1)
        content_layout.addWidget(preview_group, 2)
        
        layout.addLayout(content_layout)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # Initial load
        self._refresh_reports()
    
    def _refresh_reports(self) -> None:
        """Scan reports directory and update the list."""
        self.reports_list.clear()
        
        # Ensure directory exists
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Find all report files
        report_files = []
        for pattern in ["*.md", "*.txt"]:
            report_files.extend(REPORTS_DIR.glob(pattern))
        
        # Sort by modification time (newest first)
        report_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        
        if not report_files:
            self.status_label.setText(f"No reports found in {REPORTS_DIR}")
            self.status_label.setStyleSheet("color: #ffaeaa;")
            return
        
        for report_path in report_files:
            item = QListWidgetItem(report_path.name)
            item.setData(Qt.UserRole, str(report_path))
            # Add file size and date
            try:
                stat = report_path.stat()
                size_kb = stat.st_size / 1024
                from datetime import datetime
                mod_time = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                item.setText(f"{report_path.name} ({size_kb:.1f} KB, {mod_time})")
            except:
                pass
            self.reports_list.addItem(item)
        
        self.status_label.setText(f"Found {len(report_files)} report(s) in {REPORTS_DIR}")
        self.status_label.setStyleSheet("color: #a9f5d0;")
    
    def _on_report_selected(self, item: QListWidgetItem) -> None:
        """Load and display the selected report."""
        report_path = Path(item.data(Qt.UserRole))
        if not report_path.exists():
            self.report_preview.setPlainText(f"Error: Report file not found: {report_path}")
            self.analyze_button.setEnabled(False)
            return
        
        try:
            content = report_path.read_text(encoding="utf-8")
            self.current_report_path = report_path
            self.current_report_content = content
            
            # Display the raw report
            if report_path.suffix == ".md":
                # For markdown, use HTML rendering
                self.report_preview.setMarkdown(content)
            else:
                self.report_preview.setPlainText(content)
            
            # Reset view state
            self.showing_ai_summary = False
            self.ai_summary = ""
            
            # Reload AI settings to ensure we have latest config
            self.ai_manager._load()
            
            # Enable analyze button if AI is configured
            self.analyze_button.setEnabled(self.ai_manager.is_enabled())
            self.view_raw_button.setEnabled(False)
            if not self.ai_manager.is_enabled():
                self.status_label.setText("AI is not configured. Go to Dashboard -> 'Use AI...' to enable AI analysis.")
                self.status_label.setStyleSheet("color: #ffaeaa;")
            else:
                self.status_label.setText(f"Report loaded: {report_path.name}")
                self.status_label.setStyleSheet("color: #a9f5d0;")
        except Exception as e:
            self.report_preview.setPlainText(f"Error reading report: {e}")
            self.analyze_button.setEnabled(False)
    
    def _analyze_with_ai(self) -> None:
        """Analyze the currently selected report with AI."""
        if not self.current_report_content:
            QMessageBox.warning(self, "No Report Selected", "Please select a report to analyze.")
            return
        
        if not self.ai_manager.is_enabled():
            QMessageBox.warning(
                self,
                "AI Not Configured",
                "AI is not configured. Please go to Dashboard -> 'Use AI...' to configure AI."
            )
            return
        
        # Disable button during analysis
        self.analyze_button.setEnabled(False)
        self.status_label.setText("Analyzing report with AI... This may take a few moments.")
        self.status_label.setStyleSheet("color: #ffd700;")
        
        # Show loading message in preview
        self.report_preview.setPlainText("Analyzing report with AI... Please wait...")
        
        # Run AI analysis in background thread
        self.ai_worker = AIAnalysisWorker(
            self.ai_manager,
            self.current_report_path.name if self.current_report_path else "Report",
            self.current_report_content
        )
        self.ai_worker.finished_signal.connect(self._handle_ai_result)
        self.ai_worker.start()
    
    def _handle_ai_result(self, success: bool, summary: str, error: str) -> None:
        """Handle AI analysis result."""
        self.analyze_button.setEnabled(True)
        
        if success and summary:
            # Store AI summary
            self.ai_summary = summary
            self.showing_ai_summary = True
            
            # Display AI-generated summary
            self.report_preview.setMarkdown(summary)
            self.view_raw_button.setEnabled(True)
            self.status_label.setText("AI analysis completed successfully!")
            self.status_label.setStyleSheet("color: #a9f5d0;")
            
            # Optionally save the AI summary to a new file
            if self.current_report_path:
                try:
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    summary_path = REPORTS_DIR / f"{self.current_report_path.stem}_ai_summary_{timestamp}.md"
                    summary_path.write_text(summary, encoding="utf-8")
                    self.status_label.setText(
                        f"AI analysis completed! Summary saved to: {summary_path.name}"
                    )
                except Exception as e:
                    self.status_label.setText(f"AI analysis completed, but failed to save summary: {e}")
                    self.status_label.setStyleSheet("color: #ffaeaa;")
        else:
            # Show error
            error_msg = error or "Unknown error occurred during AI analysis."
            self.report_preview.setPlainText(f"AI Analysis Failed:\n\n{error_msg}\n\nOriginal report content is still available above.")
            self.status_label.setText(f"AI analysis failed: {error_msg}")
            self.status_label.setStyleSheet("color: #ffaeaa;")
            self.view_raw_button.setEnabled(True)  # Allow viewing raw report even after error
    
    def _view_raw_report(self) -> None:
        """Switch back to viewing the raw report content."""
        if not self.current_report_content:
            return
        
        self.showing_ai_summary = False
        self.view_raw_button.setEnabled(False)
        
        # Display the raw report
        if self.current_report_path and self.current_report_path.suffix == ".md":
            self.report_preview.setMarkdown(self.current_report_content)
        else:
            self.report_preview.setPlainText(self.current_report_content)
        
        self.status_label.setText(f"Showing raw report: {self.current_report_path.name if self.current_report_path else 'Report'}")
        self.status_label.setStyleSheet("color: #a9f5d0;")
    
    def _open_report_file(self) -> None:
        """Open a report file using system file manager."""
        if REPORTS_DIR.exists():
            from PyQt5.QtGui import QDesktopServices
            from PyQt5.QtCore import QUrl
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(REPORTS_DIR)))
        else:
            self.status_label.setText(f"Reports directory does not exist: {REPORTS_DIR}")
            self.status_label.setStyleSheet("color: #ffaeaa;")


