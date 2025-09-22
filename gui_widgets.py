"""
Custom GUI widgets and components for the manga downloader.
Provides styled and functional widgets for the modern interface.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QGroupBox, QCheckBox, QSpinBox,
    QComboBox, QTextEdit, QScrollArea, QSizePolicy, QSplitter,
    QTabWidget, QLineEdit, QGridLayout, QFormLayout
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QPixmap, QImage, QFont, QIcon

from styles import apply_widget_style, create_styled_label, theme
from models import Manga, Chapter, DownloadProgress


class ModernCard(QFrame):
    """A modern styled card widget with hover effects."""

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.Box)
        self.setLineWidth(1)

        # Apply card styling
        apply_widget_style(self, "card")

        # Layout
        self.card_layout = QVBoxLayout(self)
        self.card_layout.setContentsMargins(20, 20, 20, 20)
        self.card_layout.setSpacing(15)

        # Title
        if title:
            title_label = create_styled_label(title, "title")
            self.card_layout.addWidget(title_label)

    def add_widget(self, widget):
        """Add a widget to the card."""
        self.card_layout.addWidget(widget)

    def add_layout(self, layout):
        """Add a layout to the card."""
        self.card_layout.addLayout(layout)


class MangaCard(ModernCard):
    """A card displaying manga information with cover image."""

    def __init__(self, manga: Manga, parent=None):
        super().__init__(parent=parent)
        self.manga = manga
        self.setup_ui()

    def setup_ui(self):
        """Setup the manga card UI."""
        if not self.manga:
            return

        # Main layout with image and info
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # Left side - Cover image
        image_container = QVBoxLayout()

        self.cover_label = QLabel()
        self.cover_label.setFixedSize(120, 160)
        self.cover_label.setStyleSheet(f"""
            QLabel {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 {theme.BG_TERTIARY},
                                          stop: 1 {theme.BG_HOVER});
                border: 2px solid {theme.BORDER_PRIMARY};
                border-radius: 8px;
            }}
        """)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Try to load cover image
        if self.manga.cover_url:
            self.load_cover_image()

        image_container.addWidget(self.cover_label)
        content_layout.addLayout(image_container)

        # Right side - Manga info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)

        # Title
        title_label = create_styled_label(self.manga.title, "title")
        title_label.setWordWrap(True)
        info_layout.addWidget(title_label)

        # Author
        if self.manga.author:
            author_label = create_styled_label(f"By {self.manga.author}", "subtitle")
            info_layout.addWidget(author_label)

        # Status and chapters
        meta_layout = QHBoxLayout()
        status_label = create_styled_label(f"Status: {self.manga.status}")
        chapters_label = create_styled_label(f"Chapters: {self.manga.total_chapters}")

        meta_layout.addWidget(status_label)
        meta_layout.addWidget(chapters_label)
        info_layout.addLayout(meta_layout)

        # Genres
        if self.manga.genres:
            genres_text = ", ".join(self.manga.genres[:3])  # Show first 3 genres
            if len(self.manga.genres) > 3:
                genres_text += "..."
            genres_label = create_styled_label(f"Genres: {genres_text}")
            info_layout.addWidget(genres_label)

        content_layout.addLayout(info_layout, 1)  # Stretch to fill space

        self.card_layout.addLayout(content_layout)

    def load_cover_image(self):
        """Load and display the manga cover image."""
        if not self.manga.cover_url:
            # Show placeholder if no cover URL
            self.cover_label.setText("📖")
            self.cover_label.setStyleSheet(f"""
                QLabel {{
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                              stop: 0 {theme.PRIMARY_COLOR},
                                              stop: 1 {theme.SECONDARY_COLOR});
                    border: 2px solid {theme.BORDER_PRIMARY};
                    border-radius: 8px;
                    font-size: 48px;
                    color: {theme.TEXT_PRIMARY};
                }}
            """)
            return

        # Load image from URL using requests and QPixmap
        try:
            import requests
            from PyQt6.QtCore import QByteArray

            # Download image data
            response = requests.get(self.manga.cover_url, timeout=10)
            response.raise_for_status()

            # Convert to QPixmap
            image_data = QByteArray(response.content)
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)

            if not pixmap.isNull():
                # Scale pixmap to fit the label
                scaled_pixmap = pixmap.scaled(
                    self.cover_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.cover_label.setPixmap(scaled_pixmap)
                return

            # If loading failed, show error placeholder
            self.cover_label.setText("❌")
            self.cover_label.setStyleSheet(f"""
                QLabel {{
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                              stop: 0 {theme.ERROR_COLOR},
                                              stop: 1 {theme.WARNING_COLOR});
                    border: 2px solid {theme.BORDER_PRIMARY};
                    border-radius: 8px;
                    font-size: 24px;
                    color: {theme.TEXT_PRIMARY};
                }}
            """)

        except Exception as e:
            # If any error occurs, show placeholder
            print(f"Failed to load cover image: {e}")  # Use print instead of logger
            self.cover_label.setText("📖")
            self.cover_label.setStyleSheet(f"""
                QLabel {{
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                              stop: 0 {theme.PRIMARY_COLOR},
                                              stop: 1 {theme.SECONDARY_COLOR});
                    border: 2px solid {theme.BORDER_PRIMARY};
                    border-radius: 8px;
                    font-size: 48px;
                    color: {theme.TEXT_PRIMARY};
                }}
            """)


class ChapterListWidget(QWidget):
    """Widget for displaying and selecting chapters."""

    chapter_selection_changed = pyqtSignal(list)  # Emits list of selected chapter numbers

    def __init__(self, parent=None):
        super().__init__(parent)
        self.chapters = []
        self.chapter_checkboxes = []
        self.setup_ui()

    def setup_ui(self):
        """Setup the chapter list UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header_layout = QHBoxLayout()

        self.select_all_btn = create_animated_button("Select All")
        self.select_all_btn.setFixedWidth(100)
        self.select_all_btn.clicked.connect(self.select_all_chapters)

        self.clear_selection_btn = create_animated_button("Clear", primary=False)
        self.clear_selection_btn.setFixedWidth(100)
        self.clear_selection_btn.clicked.connect(self.clear_selection)

        header_layout.addWidget(create_styled_label("Chapters", "title"))
        header_layout.addStretch()
        header_layout.addWidget(self.clear_selection_btn)
        header_layout.addWidget(self.select_all_btn)

        layout.addLayout(header_layout)

        # Scroll area for chapters - make it wider
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setMinimumHeight(400)  # Make it taller
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        apply_widget_style(scroll, "card")

        # Container for checkboxes - make it wider
        self.checkbox_container = QWidget()
        self.checkbox_container.setMinimumWidth(600)  # Make it wider
        self.checkbox_layout = QVBoxLayout(self.checkbox_container)
        self.checkbox_layout.setSpacing(8)  # More spacing between items

        scroll.setWidget(self.checkbox_container)
        layout.addWidget(scroll)

    def set_chapters(self, chapters: list[Chapter]):
        """Set the chapters to display."""
        self.chapters = chapters
        self.chapter_checkboxes = []

        # Clear existing checkboxes
        while self.checkbox_layout.count():
            item = self.checkbox_layout.takeAt(0)
            if item and item.widget():
                widget = item.widget()
                if widget:
                    widget.deleteLater()

        # Add checkboxes for each chapter
        for chapter in chapters:
            checkbox = QCheckBox(f"Chapter {chapter.number:.1f} - {chapter.title}")
            checkbox.setChecked(True)  # Default to selected
            checkbox.setStyleSheet(f"""
                QCheckBox {{
                    color: {theme.TEXT_PRIMARY};
                    background: transparent;
                    padding: 5px;
                    border-radius: 4px;
                }}
                QCheckBox:hover {{
                    background: {theme.BG_HOVER};
                }}
                QCheckBox::indicator {{
                    width: 16px;
                    height: 16px;
                }}
                QCheckBox::indicator:checked {{
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                              stop: 0 {theme.SUCCESS_COLOR},
                                              stop: 1 {theme.ACCENT_COLOR});
                }}
            """)

            checkbox.stateChanged.connect(self.on_chapter_selection_changed)
            self.checkbox_layout.addWidget(checkbox)
            self.chapter_checkboxes.append(checkbox)

    def select_all_chapters(self):
        """Select all chapters."""
        for checkbox in self.chapter_checkboxes:
            checkbox.setChecked(True)

    def clear_selection(self):
        """Clear all selections."""
        for checkbox in self.chapter_checkboxes:
            checkbox.setChecked(False)

    def on_chapter_selection_changed(self):
        """Handle chapter selection changes."""
        selected_chapters = []
        for i, checkbox in enumerate(self.chapter_checkboxes):
            if checkbox.isChecked():
                selected_chapters.append(self.chapters[i].number)

        self.chapter_selection_changed.emit(selected_chapters)

    def get_selected_chapters(self) -> list[float]:
        """Get list of selected chapter numbers."""
        selected = []
        for i, checkbox in enumerate(self.chapter_checkboxes):
            if checkbox.isChecked():
                selected.append(self.chapters[i].number)
        return selected


class DownloadProgressWidget(QWidget):
    """Widget for displaying download progress."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.download_items = {}
        self.setup_ui()

    def setup_ui(self):
        """Setup the download progress UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Header
        header_layout = QHBoxLayout()
        header_layout.addWidget(create_styled_label("Downloads", "title"))
        header_layout.addStretch()

        self.clear_completed_btn = create_animated_button("Clear Completed", primary=False)
        self.clear_completed_btn.setFixedWidth(150)
        header_layout.addWidget(self.clear_completed_btn)

        layout.addLayout(header_layout)

        # Scroll area for progress items
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        apply_widget_style(self.scroll_area, "card")

        # Container for progress items
        self.progress_container = QWidget()
        self.progress_layout = QVBoxLayout(self.progress_container)
        self.progress_layout.setSpacing(10)

        self.scroll_area.setWidget(self.progress_container)
        layout.addWidget(self.scroll_area)

    def add_download_item(self, item_id: str, title: str, total_files: int):
        """Add a new download item."""
        progress_item = DownloadItemWidget(item_id, title, total_files)
        self.progress_layout.addWidget(progress_item)
        self.download_items[item_id] = progress_item

        # Note: Auto-scroll disabled due to type checking issues
        # Can be re-enabled later with proper type handling

        return progress_item

    def update_progress(self, item_id: str, current: int, total: int, status: str = "downloading"):
        """Update progress for a download item."""
        if item_id in self.download_items:
            self.download_items[item_id].update_progress(current, total, status)

    def remove_item(self, item_id: str):
        """Remove a download item."""
        if item_id in self.download_items:
            self.download_items[item_id].deleteLater()
            del self.download_items[item_id]


class DownloadItemWidget(QWidget):
    """Individual download progress item."""

    def __init__(self, item_id: str, title: str, total_files: int, parent=None):
        super().__init__(parent)
        self.item_id = item_id
        self.total_files = total_files
        self.setup_ui(title)

    def setup_ui(self, title: str):
        """Setup the download item UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)

        # Left side - Title and progress
        left_layout = QVBoxLayout()
        left_layout.setSpacing(5)

        # Title
        title_label = create_styled_label(title)
        title_label.setMaximumWidth(300)
        title_label.setWordWrap(True)
        left_layout.addWidget(title_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, self.total_files)
        self.progress_bar.setValue(0)
        apply_widget_style(self.progress_bar, "progress")
        left_layout.addWidget(self.progress_bar)

        layout.addLayout(left_layout, 1)

        # Right side - Status and controls
        right_layout = QVBoxLayout()
        right_layout.setSpacing(5)

        # Status label
        self.status_label = create_styled_label("Preparing...")
        right_layout.addWidget(self.status_label)

        # Cancel button
        self.cancel_btn = create_animated_button("Cancel", primary=False)
        self.cancel_btn.setFixedWidth(80)
        right_layout.addWidget(self.cancel_btn)

        layout.addLayout(right_layout)

    def update_progress(self, current: int, total: int, status: str = "downloading"):
        """Update the progress display."""
        self.progress_bar.setValue(current)
        self.progress_bar.setMaximum(total)

        # Update status
        status_colors = {
            "downloading": theme.PRIMARY_COLOR,
            "completed": theme.SUCCESS_COLOR,
            "error": theme.ERROR_COLOR,
            "cancelled": theme.WARNING_COLOR
        }

        status_text = {
            "downloading": f"Downloading... ({current}/{total})",
            "completed": "Completed",
            "error": "Error",
            "cancelled": "Cancelled"
        }

        color = status_colors.get(status, theme.TEXT_SECONDARY)
        text = status_text.get(status, status)

        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")


class SettingsWidget(QWidget):
    """Widget for application settings."""

    settings_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = {}
        self.setup_ui()

    def setup_ui(self):
        """Setup the settings UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # Title
        layout.addWidget(create_styled_label("Settings", "title"))

        # Performance settings
        performance_group = ModernCard("Performance")
        performance_layout = QFormLayout()

        # Scraping workers
        self.scraping_workers_spin = QSpinBox()
        self.scraping_workers_spin.setRange(1, 5)
        self.scraping_workers_spin.setValue(3)
        self.scraping_workers_spin.setSuffix(" workers")
        apply_widget_style(self.scraping_workers_spin, "input")
        performance_layout.addRow("Chapter Scraping:", self.scraping_workers_spin)

        # Chapter workers
        self.chapter_workers_spin = QSpinBox()
        self.chapter_workers_spin.setRange(1, 5)
        self.chapter_workers_spin.setValue(2)
        self.chapter_workers_spin.setSuffix(" workers")
        apply_widget_style(self.chapter_workers_spin, "input")
        performance_layout.addRow("Chapter Downloads:", self.chapter_workers_spin)

        # Image workers
        self.image_workers_spin = QSpinBox()
        self.image_workers_spin.setRange(2, 8)
        self.image_workers_spin.setValue(4)
        self.image_workers_spin.setSuffix(" images")
        apply_widget_style(self.image_workers_spin, "input")
        performance_layout.addRow("Images per Chapter:", self.image_workers_spin)

        performance_group.add_layout(performance_layout)
        layout.addWidget(performance_group)

        # Quality settings
        quality_group = ModernCard("Quality")
        quality_layout = QFormLayout()

        # Image quality
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["High", "Medium", "Low"])
        self.quality_combo.setCurrentText("Medium")
        apply_widget_style(self.quality_combo, "input")
        quality_layout.addRow("Image Quality:", self.quality_combo)

        # Download format
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Images only", "PDF format", "CBZ format"])
        self.format_combo.setCurrentText("Images only")
        apply_widget_style(self.format_combo, "input")
        quality_layout.addRow("Download Format:", self.format_combo)

        # Separate chapters option
        self.separate_chapters_check = QCheckBox("Create separate files per chapter")
        self.separate_chapters_check.setChecked(True)
        self.separate_chapters_check.setStyleSheet(f"""
            QCheckBox {{
                color: {theme.TEXT_PRIMARY};
                background: transparent;
                padding: 5px;
            }}
        """)
        quality_layout.addRow("", self.separate_chapters_check)

        # Delete images after conversion
        self.delete_images_check = QCheckBox("Delete original images after conversion")
        self.delete_images_check.setChecked(False)
        self.delete_images_check.setStyleSheet(f"""
            QCheckBox {{
                color: {theme.TEXT_PRIMARY};
                background: transparent;
                padding: 5px;
            }}
        """)
        quality_layout.addRow("", self.delete_images_check)

        quality_group.add_layout(quality_layout)
        layout.addWidget(quality_group)

        # Download path
        path_group = ModernCard("Download Path")
        path_layout = QHBoxLayout()

        self.download_path_edit = QLineEdit()
        self.download_path_edit.setText("/default/path")  # Will be set from utils
        apply_widget_style(self.download_path_edit, "input")
        path_layout.addWidget(self.download_path_edit)

        browse_btn = create_animated_button("Browse")
        browse_btn.setFixedWidth(80)
        path_layout.addWidget(browse_btn)

        path_group.add_layout(path_layout)
        layout.addWidget(path_group)

        # Save button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        save_btn = create_animated_button("Save Settings")
        save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

        # Connect signals
        self.scraping_workers_spin.valueChanged.connect(self.on_settings_changed)
        self.chapter_workers_spin.valueChanged.connect(self.on_settings_changed)
        self.image_workers_spin.valueChanged.connect(self.on_settings_changed)
        self.quality_combo.currentTextChanged.connect(self.on_settings_changed)
        self.format_combo.currentTextChanged.connect(self.on_settings_changed)
        self.separate_chapters_check.stateChanged.connect(self.on_settings_changed)
        self.delete_images_check.stateChanged.connect(self.on_settings_changed)
        self.download_path_edit.textChanged.connect(self.on_settings_changed)

    def on_settings_changed(self):
        """Handle settings changes."""
        self.collect_settings()

    def collect_settings(self):
        """Collect current settings values."""
        format_map = {
            "Images only": "images",
            "PDF format": "pdf",
            "CBZ format": "cbz"
        }

        quality_map = {
            "High": "high",
            "Medium": "medium",
            "Low": "low"
        }

        self.settings = {
            'scraping_workers': self.scraping_workers_spin.value(),
            'chapter_workers': self.chapter_workers_spin.value(),
            'image_workers': self.image_workers_spin.value(),
            'quality': quality_map.get(self.quality_combo.currentText(), "medium"),
            'format': format_map.get(self.format_combo.currentText(), "images"),
            'separate_chapters': self.separate_chapters_check.isChecked(),
            'delete_images': self.delete_images_check.isChecked(),
            'download_path': self.download_path_edit.text()
        }

    def save_settings(self):
        """Save settings and emit signal."""
        self.collect_settings()
        self.settings_changed.emit(self.settings)

    def get_settings(self) -> dict:
        """Get current settings."""
        self.collect_settings()
        return self.settings.copy()


def create_animated_button(text: str, primary: bool = True) -> QPushButton:
    """Create a styled button with hover effects."""
    button = QPushButton(text)

    if primary:
        apply_widget_style(button, "button_primary")
    else:
        apply_widget_style(button, "button_secondary")

    return button