"""
Main GUI window implementation with tabbed interface.
Contains the 4 main tabs: Scraping, Manga Details, Settings, and Downloads.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QPushButton, QLineEdit, QTextEdit, QProgressBar,
    QSplitter, QGroupBox, QStatusBar, QMessageBox, QFileDialog,
    QScrollArea
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon

from styles import apply_widget_style, create_styled_label, theme
from gui_widgets import (
    ModernCard, MangaCard, ChapterListWidget, DownloadProgressWidget,
    SettingsWidget, create_animated_button
)
from gui_workers import (
    ScrapingWorker, DownloadWorker, ConversionWorker, SettingsWorker,
    WorkerSignals
)
from models import Manga
from utils import get_download_path, logger


class MainWindow(QMainWindow):
    """Main application window with tabbed interface."""

    def __init__(self):
        super().__init__()
        self.manga = None
        self.selected_chapters = []
        self.current_settings = {}

        self.setup_ui()
        self.setup_connections()
        self.load_settings()

    def setup_ui(self):
        """Setup the main window UI."""
        self.setWindowTitle("📖 VYManga Downloader")
        self.setMinimumSize(1000, 700)

        # Apply theme
        theme.setup_theme()

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create tab widget
        self.tab_widget = QTabWidget()
        apply_widget_style(self.tab_widget, "tab")

        # Create tabs
        self.create_scraping_tab()
        self.create_manga_details_tab()
        self.create_settings_tab()
        self.create_downloads_tab()

        main_layout.addWidget(self.tab_widget)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Set focus to first tab
        self.tab_widget.setCurrentIndex(0)

    def create_scraping_tab(self):
        """Create the scraping tab for manga URL input."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Title
        title_label = create_styled_label("Manga Scraping", "title")
        layout.addWidget(title_label)

        # URL input section
        url_card = ModernCard("Manga URL")
        url_layout = QVBoxLayout()

        url_input_layout = QHBoxLayout()
        url_input_layout.setSpacing(10)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter manga URL from vymanga.co...")
        apply_widget_style(self.url_input, "input")
        url_input_layout.addWidget(self.url_input)

        scrape_btn = create_animated_button("Scrape Manga")
        scrape_btn.clicked.connect(self.start_scraping)
        url_input_layout.addWidget(scrape_btn)

        url_layout.addLayout(url_input_layout)

        # URL validation info
        url_info = create_styled_label(
            "💡 Enter a valid manga URL from vymanga.co to fetch manga information and chapters.",
            "subtitle"
        )
        url_info.setWordWrap(True)
        url_layout.addWidget(url_info)

        url_card.add_layout(url_layout)
        layout.addWidget(url_card)

        # Progress section
        progress_card = ModernCard("Scraping Progress")
        progress_layout = QVBoxLayout()

        self.scraping_progress = QProgressBar()
        self.scraping_progress.setRange(0, 0)  # Indeterminate progress
        self.scraping_progress.setVisible(False)
        apply_widget_style(self.scraping_progress, "progress")
        progress_layout.addWidget(self.scraping_progress)

        self.scraping_status = create_styled_label("Ready to scrape")
        progress_layout.addWidget(self.scraping_status)

        progress_card.add_layout(progress_layout)
        layout.addWidget(progress_card)

        # Add stretch to push content to top
        layout.addStretch()

        self.tab_widget.addTab(tab, "🔍 Scraping")

    def create_manga_details_tab(self):
        """Create the manga details tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Title
        title_label = create_styled_label("Manga Details", "title")
        layout.addWidget(title_label)

        # Manga info section
        self.manga_info_card = ModernCard("Manga Information")
        self.manga_info_layout = QVBoxLayout()
        self.manga_info_card.add_layout(self.manga_info_layout)
        layout.addWidget(self.manga_info_card)

        # Chapter selection section
        self.chapter_section = ModernCard("Chapter Selection")
        self.chapter_layout = QVBoxLayout()

        self.chapter_list = ChapterListWidget()
        self.chapter_list.chapter_selection_changed.connect(self.on_chapter_selection_changed)
        self.chapter_layout.addWidget(self.chapter_list)

        # Download button
        download_btn_layout = QHBoxLayout()
        download_btn_layout.addStretch()

        self.download_btn = create_animated_button("Start Download")
        self.download_btn.clicked.connect(self.start_download)
        self.download_btn.setEnabled(False)
        download_btn_layout.addWidget(self.download_btn)

        self.chapter_layout.addLayout(download_btn_layout)
        self.chapter_section.add_layout(self.chapter_layout)
        layout.addWidget(self.chapter_section)

        # Add stretch
        layout.addStretch()

        self.tab_widget.addTab(tab, "📚 Details")

    def create_settings_tab(self):
        """Create the settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Title
        title_label = create_styled_label("Settings", "title")
        layout.addWidget(title_label)

        # Settings widget
        self.settings_widget = SettingsWidget()
        self.settings_widget.settings_changed.connect(self.on_settings_changed)
        layout.addWidget(self.settings_widget)

        # Add stretch
        layout.addStretch()

        self.tab_widget.addTab(tab, "⚙️ Settings")

    def create_downloads_tab(self):
        """Create the downloads tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Title
        title_label = create_styled_label("Downloads", "title")
        layout.addWidget(title_label)

        # Status section
        status_card = ModernCard("Download Status")
        status_layout = QVBoxLayout()

        self.download_status_label = create_styled_label("No downloads in progress")
        self.download_status_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        status_layout.addWidget(self.download_status_label)

        # Progress bar for overall download
        self.overall_progress = QProgressBar()
        self.overall_progress.setRange(0, 100)
        self.overall_progress.setValue(0)
        self.overall_progress.setVisible(False)
        apply_widget_style(self.overall_progress, "progress")
        status_layout.addWidget(self.overall_progress)

        # Current operation label
        self.current_operation_label = create_styled_label("")
        status_layout.addWidget(self.current_operation_label)

        status_card.add_layout(status_layout)
        layout.addWidget(status_card)

        # Active downloads section
        downloads_card = ModernCard("Active Downloads")
        downloads_layout = QVBoxLayout()

        # Scroll area for individual download items
        self.downloads_scroll = QScrollArea()
        self.downloads_scroll.setWidgetResizable(True)
        self.downloads_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.downloads_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.downloads_scroll.setMinimumHeight(300)
        apply_widget_style(self.downloads_scroll, "card")

        # Container for download items
        self.downloads_container = QWidget()
        self.downloads_container_layout = QVBoxLayout(self.downloads_container)
        self.downloads_container_layout.setSpacing(10)

        self.downloads_scroll.setWidget(self.downloads_container)
        downloads_layout.addWidget(self.downloads_scroll)

        downloads_card.add_layout(downloads_layout)
        layout.addWidget(downloads_card)

        # Control buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        self.clear_completed_btn = create_animated_button("Clear Completed", primary=False)
        self.clear_completed_btn.clicked.connect(self.clear_completed_downloads)
        buttons_layout.addWidget(self.clear_completed_btn)

        self.cancel_all_btn = create_animated_button("Cancel All", primary=False)
        self.cancel_all_btn.clicked.connect(self.cancel_all_downloads)
        buttons_layout.addWidget(self.cancel_all_btn)

        layout.addLayout(buttons_layout)

        # Add stretch
        layout.addStretch()

        self.tab_widget.addTab(tab, "⬇️ Downloads")

        # Initialize download tracking
        self.active_downloads = {}
        self.download_counters = {}

    def setup_connections(self):
        """Setup signal connections."""
        # URL input
        self.url_input.returnPressed.connect(self.start_scraping)

    def load_settings(self):
        """Load settings from storage or defaults."""
        default_settings = {
            'scraping_workers': 3,
            'chapter_workers': 2,
            'image_workers': 4,
            'quality': 'high',  # Default to high quality for best results
            'format': 'images',
            'separate_chapters': True,
            'delete_images': False,
            'download_path': get_download_path()
        }

        self.current_settings = default_settings
        self.settings_widget.download_path_edit.setText(default_settings['download_path'])

    def start_scraping(self):
        """Start the scraping process."""
        url = self.url_input.text().strip()

        if not url:
            QMessageBox.warning(self, "Input Required", "Please enter a manga URL.")
            return

        # Validate URL
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"

        if 'vymanga.co' not in url:
            reply = QMessageBox.question(
                self, "URL Warning",
                "This URL doesn't appear to be from vymanga.co. Continue anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.No:
                return

        # Start scraping worker
        self.scraping_progress.setVisible(True)
        self.scraping_status.setText("Scraping manga information...")

        self.scraping_worker = ScrapingWorker(url, self.current_settings.get('scraping_workers', 3))
        self.scraping_worker.signals.scraping_started.connect(self.on_scraping_started)
        self.scraping_worker.signals.scraping_progress.connect(self.on_scraping_progress)
        self.scraping_worker.signals.scraping_finished.connect(self.on_scraping_finished)
        self.scraping_worker.signals.scraping_error.connect(self.on_scraping_error)

        self.scraping_worker.start()

    def on_scraping_started(self, message: str):
        """Handle scraping started."""
        self.status_bar.showMessage(message)
        self.scraping_status.setText(message)

    def on_scraping_progress(self, message: str, current: int, total: int):
        """Handle scraping progress."""
        self.scraping_status.setText(message)

    def on_scraping_finished(self, manga: Manga):
        """Handle scraping finished."""
        self.manga = manga
        self.scraping_progress.setVisible(False)
        self.scraping_status.setText("Scraping completed successfully!")

        # Update manga details tab
        self.update_manga_details()
        self.download_btn.setEnabled(True)

        # Switch to details tab
        self.tab_widget.setCurrentIndex(1)

        self.status_bar.showMessage(f"Successfully scraped: {manga.title}")

    def on_scraping_error(self, error: str):
        """Handle scraping error."""
        self.scraping_progress.setVisible(False)
        self.scraping_status.setText(f"Error: {error}")

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Scraping Error")
        msg_box.setText(error)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setStyleSheet(f"""
            QMessageBox {{
                background: {theme.BG_PRIMARY};
                color: {theme.TEXT_PRIMARY};
            }}
            QMessageBox QLabel {{
                color: {theme.TEXT_PRIMARY};
                background: {theme.BG_PRIMARY};
            }}
            QMessageBox QPushButton {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 {theme.ERROR_COLOR},
                                          stop: 1 {theme.WARNING_COLOR});
                color: {theme.TEXT_PRIMARY};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }}
        """)
        msg_box.exec()
        self.status_bar.showMessage("Scraping failed")

    def update_manga_details(self):
        """Update the manga details display."""
        if not self.manga:
            return

        # Clear existing content
        while self.manga_info_layout.count():
            item = self.manga_info_layout.takeAt(0)
            if item and item.widget():
                widget = item.widget()
                if widget:
                    widget.deleteLater()

        # Create manga card
        manga_card = MangaCard(self.manga)
        self.manga_info_layout.addWidget(manga_card)

        # Update chapter list
        self.chapter_list.set_chapters(self.manga.chapters)

    def on_chapter_selection_changed(self, selected_chapters: list):
        """Handle chapter selection changes."""
        self.selected_chapters = selected_chapters
        count = len(selected_chapters)

        if count == 0:
            self.download_btn.setEnabled(False)
            self.download_btn.setText("Start Download")
        else:
            self.download_btn.setEnabled(True)
            self.download_btn.setText(f"Download {count} Chapters")

    def start_download(self):
        """Start the download process."""
        if not self.manga or not self.selected_chapters:
            return

        # Filter selected chapters
        selected_chapter_objects = [
            ch for ch in self.manga.chapters
            if ch.number in self.selected_chapters
        ]

        if not selected_chapter_objects:
            QMessageBox.warning(self, "No Chapters", "Please select at least one chapter to download.")
            return

        # Create filtered manga with download path
        download_manga = Manga(
            title=self.manga.title,
            url=self.manga.url,
            author=self.manga.author,
            status=self.manga.status,
            genres=self.manga.genres,
            summary=self.manga.summary,
            cover_url=self.manga.cover_url,
            chapters=selected_chapter_objects
        )

        # Set download path
        download_path = self.current_settings.get('download_path', get_download_path())
        download_manga.create_download_structure(download_path)

        # Get download path
        download_path = self.current_settings.get('download_path', get_download_path())

        # Start download worker
        self.download_worker = DownloadWorker(
            download_manga,
            download_path,
            self.current_settings.get('chapter_workers', 2),
            self.current_settings.get('image_workers', 4)
        )

        # Connect progress signals
        self.download_worker.signals.download_progress.connect(self.on_download_progress)

        self.download_worker.signals.download_started.connect(self.on_download_started)
        self.download_worker.signals.download_progress.connect(self.on_download_progress)
        self.download_worker.signals.download_finished.connect(self.on_download_finished)
        self.download_worker.signals.download_error.connect(self.on_download_error)

        self.download_worker.start()

        # Switch to downloads tab
        self.tab_widget.setCurrentIndex(3)

    def on_download_started(self, message: str):
        """Handle download started."""
        self.status_bar.showMessage(message)

        # Add download item to downloads tab
        if self.manga:
            total_chapters = len(self.selected_chapters) if self.selected_chapters else len(self.manga.chapters)
            item_id = self.manga.title
            self.add_download_item(item_id, self.manga.title, total_chapters)

    def on_download_progress(self, item_id: str, current: int, total: int, status: str):
        """Handle download progress."""
        self.update_download_progress(item_id, current, total, status)

    def on_download_finished(self, item_id: str):
        """Handle download finished."""
        self.status_bar.showMessage(f"Download completed: {item_id}")

        # Start conversion if needed
        output_format = self.current_settings.get('format', 'images')
        if output_format in ['pdf', 'cbz']:
            self.start_conversion(item_id, output_format)

    def on_download_error(self, item_id: str, error: str):
        """Handle download error."""
        self.status_bar.showMessage(f"Download failed: {item_id}")
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Download Error")
        msg_box.setText(f"Failed to download {item_id}: {error}")
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setStyleSheet(f"""
            QMessageBox {{
                background: {theme.BG_PRIMARY};
                color: {theme.TEXT_PRIMARY};
            }}
            QMessageBox QLabel {{
                color: {theme.TEXT_PRIMARY};
                background: {theme.BG_PRIMARY};
            }}
            QMessageBox QPushButton {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 {theme.ERROR_COLOR},
                                          stop: 1 {theme.WARNING_COLOR});
                color: {theme.TEXT_PRIMARY};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }}
        """)
        msg_box.exec()

    def start_conversion(self, item_id: str, output_format: str):
        """Start format conversion."""
        if not self.manga:
            return

        # Make sure manga has download path set
        download_path = self.current_settings.get('download_path', get_download_path())
        if not self.manga.download_path:
            self.manga.create_download_structure(download_path)

        # Create conversion worker with quality setting
        self.conversion_worker = ConversionWorker(
            self.manga,
            output_format,
            self.current_settings.get('quality', 'high'),  # Default to high quality
            self.current_settings.get('separate_chapters', True),
            self.current_settings.get('delete_images', False)
        )

        self.conversion_worker.signals.conversion_started.connect(self.on_conversion_started)
        self.conversion_worker.signals.conversion_finished.connect(self.on_conversion_finished)
        self.conversion_worker.signals.conversion_error.connect(self.on_conversion_error)

        self.conversion_worker.start()

    def on_conversion_started(self, message: str):
        """Handle conversion started."""
        self.status_bar.showMessage(message)

    def on_conversion_finished(self, format_name: str):
        """Handle conversion finished."""
        self.status_bar.showMessage(f"Conversion to {format_name} completed successfully!")
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Conversion Complete")
        msg_box.setText(f"Successfully converted manga to {format_name} format!")
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setStyleSheet(f"""
            QMessageBox {{
                background: {theme.BG_PRIMARY};
                color: {theme.TEXT_PRIMARY};
            }}
            QMessageBox QLabel {{
                color: {theme.TEXT_PRIMARY};
                background: {theme.BG_PRIMARY};
            }}
            QMessageBox QPushButton {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 {theme.SUCCESS_COLOR},
                                          stop: 1 {theme.ACCENT_COLOR});
                color: {theme.TEXT_PRIMARY};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }}
        """)
        msg_box.exec()

    def on_conversion_error(self, error: str):
        """Handle conversion error."""
        self.status_bar.showMessage("Conversion failed")
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Conversion Error")
        msg_box.setText(f"Conversion failed: {error}")
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setStyleSheet(f"""
            QMessageBox {{
                background: {theme.BG_PRIMARY};
                color: {theme.TEXT_PRIMARY};
            }}
            QMessageBox QLabel {{
                color: {theme.TEXT_PRIMARY};
                background: {theme.BG_PRIMARY};
            }}
            QMessageBox QPushButton {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 {theme.ERROR_COLOR},
                                          stop: 1 {theme.WARNING_COLOR});
                color: {theme.TEXT_PRIMARY};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }}
        """)
        msg_box.exec()

    def on_settings_changed(self, settings: dict):
        """Handle settings changes."""
        self.current_settings.update(settings)

        # Save settings to storage
        self.save_settings()

    def save_settings(self):
        """Save settings to storage."""
        try:
            # In a real application, you would save to a config file
            # For now, just update the status
            self.status_bar.showMessage("Settings updated")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def clear_completed_downloads(self):
        """Clear completed downloads from the list."""
        # Remove completed download items from the UI
        for i in reversed(range(self.downloads_container_layout.count())):
            item = self.downloads_container_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                # Check if this is a completed download (you'd need to track status)
                # For now, just remove all items
                if widget:
                    widget.deleteLater()

        self.status_bar.showMessage("Completed downloads cleared")

    def cancel_all_downloads(self):
        """Cancel all active downloads."""
        # Cancel all active download workers
        if hasattr(self, 'download_worker') and self.download_worker:
            self.download_worker.cancel()

        self.status_bar.showMessage("All downloads cancelled")

    def add_download_item(self, item_id: str, title: str, total_files: int):
        """Add a new download item to the downloads tab."""
        from gui_widgets import DownloadItemWidget

        # Create download item widget
        download_item = DownloadItemWidget(item_id, title, total_files)
        self.downloads_container_layout.addWidget(download_item)
        self.active_downloads[item_id] = download_item

        # Update status
        self.download_status_label.setText(f"Downloading: {title}")
        self.overall_progress.setVisible(True)
        self.overall_progress.setRange(0, total_files)
        self.overall_progress.setValue(0)

        # Scroll to show new item
        scroll_bar = self.downloads_scroll.verticalScrollBar()
        if scroll_bar:
            scroll_bar.setValue(scroll_bar.maximum())

    def update_download_progress(self, item_id: str, current: int, total: int, status: str):
        """Update download progress for an item."""
        if item_id in self.active_downloads:
            download_item = self.active_downloads[item_id]
            download_item.update_progress(current, total, status)

            # Update overall progress
            if total > 0:
                overall_current = sum(
                    item.progress_bar.value()
                    for item in self.active_downloads.values()
                    if hasattr(item, 'progress_bar')
                )
                overall_total = sum(
                    item.progress_bar.maximum()
                    for item in self.active_downloads.values()
                    if hasattr(item, 'progress_bar')
                )

                if overall_total > 0:
                    self.overall_progress.setValue(overall_current)
                    self.overall_progress.setMaximum(overall_total)

            # Update current operation
            if status == "downloading":
                self.current_operation_label.setText(f"Progress: {current}/{total} files")
            elif status == "completed":
                self.current_operation_label.setText("Download completed!")

    def remove_download_item(self, item_id: str):
        """Remove a download item."""
        if item_id in self.active_downloads:
            download_item = self.active_downloads[item_id]
            download_item.deleteLater()
            del self.active_downloads[item_id]

            # Update status if no more active downloads
            if not self.active_downloads:
                self.download_status_label.setText("No downloads in progress")
                self.overall_progress.setVisible(False)
                self.current_operation_label.setText("")