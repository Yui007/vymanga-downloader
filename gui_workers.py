"""
Background worker threads for GUI operations.
Handles scraping, downloading, and converting operations in separate threads.
"""

from PyQt6.QtCore import QThread, pyqtSignal, QObject
from PyQt6.QtWidgets import QApplication
import time
import traceback

from models import Manga, Chapter, DownloadProgress
from scraper import VymangaScraper
from downloader import MangaDownloader
from converter import MangaConverter
from utils import logger, get_download_path


class WorkerSignals(QObject):
    """Signals for worker thread communication."""

    # Scraping signals
    scraping_started = pyqtSignal(str)
    scraping_progress = pyqtSignal(str, int, int)  # message, current, total
    scraping_finished = pyqtSignal(Manga)
    scraping_error = pyqtSignal(str)

    # Downloading signals
    download_started = pyqtSignal(str)
    download_progress = pyqtSignal(str, int, int, str)  # item_id, current, total, status
    download_finished = pyqtSignal(str)
    download_error = pyqtSignal(str, str)  # item_id, error

    # Conversion signals
    conversion_started = pyqtSignal(str)
    conversion_progress = pyqtSignal(str, int, int)
    conversion_finished = pyqtSignal(str)
    conversion_error = pyqtSignal(str)


class ScrapingWorker(QThread):
    """Worker thread for manga scraping operations."""

    def __init__(self, url: str, max_workers: int = 5):
        super().__init__()
        self.url = url
        self.max_workers = max_workers
        self.signals = WorkerSignals()

    def run(self):
        """Run the scraping operation in a separate thread."""
        try:
            self.signals.scraping_started.emit(f"Scraping manga from {self.url}")

            # Create scraper instance
            scraper = VymangaScraper()

            # Scrape manga info
            QApplication.processEvents()  # Keep UI responsive
            self.signals.scraping_progress.emit("Fetching manga information...", 0, 1)

            manga = scraper.scrape_manga_info(self.url)

            if not manga:
                self.signals.scraping_error.emit("Failed to scrape manga information. Please check the URL.")
                return

            # Note: Only scrape manga info, don't scrape chapter pages yet
            # Chapter pages will be scraped when user initiates download
            QApplication.processEvents()
            self.signals.scraping_progress.emit("Manga information scraped successfully!", 1, 1)

            self.signals.scraping_finished.emit(manga)

        except Exception as e:
            logger.error(f"Scraping error: {e}")
            logger.error(traceback.format_exc())
            self.signals.scraping_error.emit(f"Error during scraping: {str(e)}")


class DownloadWorker(QThread):
    """Worker thread for manga downloading operations."""

    def __init__(self, manga: Manga, download_path: str, chapter_workers: int = 2, image_workers: int = 4):
        super().__init__()
        self.manga = manga
        self.download_path = download_path
        self.chapter_workers = chapter_workers
        self.image_workers = image_workers
        self.signals = WorkerSignals()
        self.is_cancelled = False

    def run(self):
        """Run the download operation in a separate thread."""
        try:
            self.signals.download_started.emit(f"Starting download of {self.manga.title}")

            # First, scrape chapter pages
            QApplication.processEvents()
            scraper = VymangaScraper()

            self.signals.download_progress.emit(
                self.manga.title, 0, len(self.manga.chapters),
                "Scraping chapter pages..."
            )

            success = scraper.scrape_selected_chapters(
                self.manga.chapters,
                max_workers=self.chapter_workers
            )

            if not success:
                self.signals.download_error.emit(self.manga.title, "Failed to scrape chapter pages")
                return

            # Create downloader instance with progress callback
            downloader = MangaDownloader(
                chapter_workers=self.chapter_workers,
                image_workers=self.image_workers
            )

            # Add progress callback to emit signals
            def progress_callback(progress):
                """Progress callback to emit GUI signals."""
                QApplication.processEvents()  # Keep UI responsive

                # Calculate overall progress
                total_files = progress.total_files
                downloaded_files = progress.downloaded_files
                current_chapter = progress.current_chapter or ""
                current_file = progress.current_file or ""

                # Emit progress signal
                status = progress.status
                if status == "downloading":
                    status_msg = f"Downloading: {current_chapter} - {current_file}"
                else:
                    status_msg = status

                self.signals.download_progress.emit(
                    self.manga.title, downloaded_files, total_files, status_msg
                )

            downloader.add_progress_callback(progress_callback)

            # Download manga
            QApplication.processEvents()
            success = downloader.download_manga(self.manga, self.download_path)

            if success:
                self.signals.download_finished.emit(self.manga.title)
            else:
                self.signals.download_error.emit(self.manga.title, "Download failed")

        except Exception as e:
            logger.error(f"Download error: {e}")
            logger.error(traceback.format_exc())
            self.signals.download_error.emit(self.manga.title, str(e))

    def cancel(self):
        """Cancel the download operation."""
        self.is_cancelled = True
        # Note: Actual cancellation would need to be implemented in the downloader


class ConversionWorker(QThread):
    """Worker thread for format conversion operations."""

    def __init__(self, manga: Manga, output_format: str, separate_chapters: bool = True, delete_images: bool = False):
        super().__init__()
        self.manga = manga
        self.output_format = output_format
        self.separate_chapters = separate_chapters
        self.delete_images = delete_images
        self.signals = WorkerSignals()

    def run(self):
        """Run the conversion operation in a separate thread."""
        try:
            format_name = self.output_format.upper()
            self.signals.conversion_started.emit(f"Converting to {format_name} format...")

            # Create converter instance (same as CLI approach)
            converter = MangaConverter()

            # Set quality from settings (same as CLI approach)
            quality = self.manga.metadata.get('quality', 'medium') if hasattr(self.manga, 'metadata') else 'medium'
            converter.quality = quality

            # Filter to only chapters that have download paths (were actually downloaded)
            downloadable_chapters = [ch for ch in self.manga.chapters if ch.download_path]

            if not downloadable_chapters:
                self.signals.conversion_error.emit("No downloaded chapters found for conversion")
                return

            # Create a temporary manga object with only the downloaded chapters
            temp_manga = Manga(
                title=self.manga.title,
                url=self.manga.url,
                author=self.manga.author,
                status=self.manga.status,
                genres=self.manga.genres,
                summary=self.manga.summary,
                cover_url=self.manga.cover_url,
                chapters=downloadable_chapters
            )

            # Set download path on temp_manga (same as CLI approach)
            if self.manga.download_path:
                temp_manga.create_download_structure(self.manga.download_path)

            success = False

            # Use the same conversion approach as CLI
            if self.output_format == 'pdf':
                success = converter.convert_manga_to_pdf(
                    temp_manga,
                    separate_chapters=self.separate_chapters,
                    delete_images=self.delete_images
                )
            elif self.output_format == 'cbz':
                success = converter.convert_manga_to_cbz(
                    temp_manga,
                    separate_chapters=self.separate_chapters,
                    delete_images=self.delete_images
                )

            if success:
                self.signals.conversion_finished.emit(format_name)
            else:
                self.signals.conversion_error.emit(f"Conversion to {format_name} failed")

        except Exception as e:
            logger.error(f"Conversion error: {e}")
            logger.error(traceback.format_exc())
            self.signals.conversion_error.emit(str(e))


class SettingsWorker(QThread):
    """Worker thread for settings validation and updates."""

    def __init__(self, settings: dict):
        super().__init__()
        self.settings = settings
        self.signals = WorkerSignals()

    def run(self):
        """Validate and apply settings."""
        try:
            # Validate download path
            if 'download_path' in self.settings:
                download_path = self.settings['download_path']
                if download_path:
                    import os
                    os.makedirs(download_path, exist_ok=True)

            # Settings are validated, emit success
            self.signals.conversion_finished.emit("Settings updated successfully")

        except Exception as e:
            logger.error(f"Settings error: {e}")
            self.signals.conversion_error.emit(str(e))


class ProgressUpdater(QObject):
    """Helper class to update progress from background threads."""

    def __init__(self):
        super().__init__()
        self.download_progress = DownloadProgress()

    def update_download_progress(self, current: int, total: int, status: str = "downloading"):
        """Update download progress."""
        self.download_progress.current_chapter = f"Chapter {current}"
        self.download_progress.downloaded_files = current
        self.download_progress.total_files = total
        self.download_progress.status = status

        # Emit signal to update UI
        # This would be connected to the main window's progress update method

    def reset_progress(self):
        """Reset progress tracking."""
        self.download_progress.reset()


# Global progress updater instance
progress_updater = ProgressUpdater()