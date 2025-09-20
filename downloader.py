"""
Threaded download engine for manga images.
Handles concurrent downloads with retries and progress tracking.
"""

import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Callable, Dict, Any
import requests
from urllib.parse import urlparse

from models import Manga, Chapter, Page, DownloadProgress
from utils import logger, ensure_directory, format_bytes, format_time, calculate_file_hash


class DownloadWorker:
    """Handles individual file downloads with retry logic."""

    def __init__(self, session: requests.Session, max_retries: int = 3):
        """
        Initialize download worker.

        Args:
            session: Requests session for connection pooling
            max_retries: Maximum number of retry attempts
        """
        self.session = session
        self.max_retries = max_retries

    def download_file(self, url: str, file_path: str, timeout: int = 30) -> bool:
        """
        Download a single file with retries.

        Args:
            url: File URL to download
            file_path: Local path to save the file
            timeout: Request timeout in seconds

        Returns:
            True if download successful, False otherwise
        """
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Downloading {url} (attempt {attempt + 1})")

                # Make request with streaming for large files
                response = self.session.get(url, stream=True, timeout=timeout)
                response.raise_for_status()

                # Get file size if available
                file_size = int(response.headers.get('content-length', 0))

                # Create directory if it doesn't exist
                ensure_directory(os.path.dirname(file_path))

                # Download with progress tracking
                downloaded = 0
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

                # Verify file was downloaded
                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    logger.debug(f"Successfully downloaded: {file_path}")
                    return True
                else:
                    logger.warning(f"Download completed but file is empty: {file_path}")
                    return False

            except requests.RequestException as e:
                logger.warning(f"Download attempt {attempt + 1} failed for {url}: {e}")
                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    time.sleep(2 ** attempt)

            except Exception as e:
                logger.error(f"Unexpected error downloading {url}: {e}")
                break

        logger.error(f"Failed to download {url} after {self.max_retries} attempts")
        return False


class MangaDownloader:
    """Main downloader class for manga with concurrency support."""

    def __init__(self, max_workers: int = 4, max_retries: int = 3):
        """
        Initialize the manga downloader.

        Args:
            max_workers: Maximum number of concurrent download threads
            max_retries: Maximum number of retry attempts per file
        """
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

        # Progress tracking
        self.progress = DownloadProgress()
        self.progress_callbacks: List[Callable[[DownloadProgress], None]] = []

        # Threading
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def add_progress_callback(self, callback: Callable[[DownloadProgress], None]):
        """
        Add a progress callback function.

        Args:
            callback: Function to call with progress updates
        """
        with self._lock:
            self.progress_callbacks.append(callback)

    def _notify_progress(self):
        """Notify all progress callbacks."""
        with self._lock:
            for callback in self.progress_callbacks:
                try:
                    callback(self.progress)
                except Exception as e:
                    logger.error(f"Progress callback error: {e}")

    def download_manga(self, manga: Manga, download_path: Optional[str] = None) -> bool:
        """
        Download a complete manga series.

        Args:
            manga: Manga object to download
            download_path: Base path for downloads (optional)

        Returns:
            True if download successful, False otherwise
        """
        logger.info(f"Starting download of: {manga.title}")

        # Set up download path
        if download_path:
            manga.download_path = download_path
        elif not manga.download_path:
            manga.create_download_structure(os.path.join(os.getcwd(), "downloads"))

        # Count total files
        total_files = sum(len(chapter.pages) for chapter in manga.chapters)
        self.progress.total_files = total_files
        self.progress.downloaded_files = 0
        self.progress.status = "downloading"

        logger.info(f"Total files to download: {total_files}")

        # Download chapters concurrently
        success = True
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all chapters for download
            future_to_chapter = {
                executor.submit(self._download_chapter, manga, chapter): chapter
                for chapter in manga.chapters
            }

            # Process completed downloads
            for future in as_completed(future_to_chapter):
                chapter = future_to_chapter[future]
                try:
                    chapter_success = future.result()
                    if not chapter_success:
                        success = False
                        logger.warning(f"Failed to download chapter: {chapter.title}")
                except Exception as e:
                    success = False
                    logger.error(f"Error downloading chapter {chapter.title}: {e}")

        # Update final status
        self.progress.status = "completed" if success else "error"
        self._notify_progress()

        logger.info(f"Manga download {'completed' if success else 'failed'}: {manga.title}")
        return success

    def _download_chapter(self, manga: Manga, chapter: Chapter) -> bool:
        """
        Download a single chapter.

        Args:
            manga: Parent manga object
            chapter: Chapter to download

        Returns:
            True if download successful, False otherwise
        """
        if not chapter.pages:
            logger.warning(f"No pages found for chapter: {chapter.title}")
            return False

        # Create chapter directory
        if not manga.download_path:
            logger.error("Manga download path not set")
            return False

        chapter_path = os.path.join(manga.download_path, chapter.chapter_folder_name)
        ensure_directory(chapter_path)
        chapter.download_path = chapter_path

        logger.info(f"Downloading chapter: {chapter.title} ({len(chapter.pages)} pages)")

        # Update progress
        with self._lock:
            self.progress.current_chapter = chapter.title

        # Download pages concurrently
        worker = DownloadWorker(self.session, self.max_retries)
        chapter_success = True

        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(chapter.pages))) as executor:
            # Submit all pages for download
            future_to_page = {}
            for page in chapter.pages:
                page.file_path = os.path.join(chapter_path, page.filename)
                future_to_page[executor.submit(worker.download_file, page.url, page.file_path)] = page

            # Process completed downloads
            for future in as_completed(future_to_page):
                page = future_to_page[future]
                try:
                    success = future.result()
                    page.downloaded = success

                    # Update progress
                    with self._lock:
                        self.progress.downloaded_files += 1
                        self.progress.current_file = page.filename

                    if success:
                        logger.debug(f"Downloaded page: {page.filename}")
                    else:
                        chapter_success = False
                        logger.error(f"Failed to download page: {page.filename}")

                except Exception as e:
                    chapter_success = False
                    logger.error(f"Error downloading page {page.filename}: {e}")

        # Mark chapter as downloaded if all pages succeeded
        chapter.downloaded = chapter_success

        # Update progress
        with self._lock:
            self.progress.current_chapter = None
            self.progress.current_file = None

        self._notify_progress()
        return chapter_success

    def download_chapter_range(self, manga: Manga, start_chapter: float, end_chapter: float,
                              download_path: Optional[str] = None) -> bool:
        """
        Download a range of chapters from a manga.

        Args:
            manga: Manga object
            start_chapter: Starting chapter number
            end_chapter: Ending chapter number
            download_path: Base path for downloads (optional)

        Returns:
            True if download successful, False otherwise
        """
        # Filter chapters in range
        chapters_in_range = manga.get_chapters_in_range(start_chapter, end_chapter)

        if not chapters_in_range:
            logger.warning(f"No chapters found in range {start_chapter}-{end_chapter}")
            return False

        logger.info(f"Downloading {len(chapters_in_range)} chapters ({start_chapter}-{end_chapter})")

        # Create temporary manga object with filtered chapters
        temp_manga = Manga(
            title=f"{manga.title} (Chapters {start_chapter}-{end_chapter})",
            url=manga.url,
            author=manga.author,
            status=manga.status,
            genres=manga.genres,
            summary=manga.summary,
            cover_url=manga.cover_url,
            chapters=chapters_in_range
        )

        return self.download_manga(temp_manga, download_path)

    def download_single_chapter(self, chapter: Chapter, download_path: str) -> bool:
        """
        Download a single chapter.

        Args:
            chapter: Chapter to download
            download_path: Path to save the chapter

        Returns:
            True if download successful, False otherwise
        """
        # Create temporary manga object
        temp_manga = Manga(
            title=f"Chapter {chapter.number}",
            url=chapter.url,
            chapters=[chapter]
        )

        return self.download_manga(temp_manga, download_path)

    def pause_download(self):
        """Pause the current download."""
        logger.info("Pausing download...")
        self.progress.status = "paused"
        self._stop_event.set()
        self._notify_progress()

    def resume_download(self):
        """Resume a paused download."""
        logger.info("Resuming download...")
        self.progress.status = "downloading"
        self._stop_event.clear()
        self._notify_progress()

    def stop_download(self):
        """Stop the current download."""
        logger.info("Stopping download...")
        self.progress.status = "idle"
        self._stop_event.set()
        self._notify_progress()

    def get_download_stats(self) -> Dict[str, Any]:
        """
        Get current download statistics.

        Returns:
            Dictionary with download statistics
        """
        return {
            "total_files": self.progress.total_files,
            "downloaded_files": self.progress.downloaded_files,
            "progress_percent": self.progress.progress_percent,
            "current_chapter": self.progress.current_chapter,
            "current_file": self.progress.current_file,
            "speed": self.progress.speed,
            "eta": self.progress.eta,
            "status": self.progress.status
        }