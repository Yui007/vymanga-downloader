"""
Data models for the manga downloader.
Defines the core data structures for Manga, Chapter, and Page objects.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
import os


@dataclass
class Page:
    """Represents a single page/image in a chapter."""
    url: str
    filename: str
    page_number: int
    downloaded: bool = False
    file_path: Optional[str] = None

    def __post_init__(self):
        if not self.filename:
            self.filename = f"page_{self.page_number:03d}.jpg"


@dataclass
class Chapter:
    """Represents a manga chapter."""
    title: str
    number: float  # Support for decimal chapters (e.g., 1.5)
    url: str
    pages: List[Page] = field(default_factory=list)
    downloaded: bool = False
    download_path: Optional[str] = None
    published_date: Optional[datetime] = None
    chapter_id: Optional[str] = None

    @property
    def chapter_folder_name(self) -> str:
        """Generate a clean folder name for this chapter."""
        if self.number.is_integer():
            return f"Chapter_{int(self.number)}"
        else:
            return f"Chapter_{self.number:.1f}"

    def add_page(self, page_url: str, page_number: int) -> Page:
        """Add a page to this chapter."""
        page = Page(
            url=page_url,
            filename=f"page_{page_number:03d}.jpg",
            page_number=page_number
        )
        self.pages.append(page)
        return page


@dataclass
class Manga:
    """Represents a complete manga series."""
    title: str
    url: str
    author: str = ""
    status: str = ""  # Ongoing, Completed, etc.
    genres: List[str] = field(default_factory=list)
    summary: str = ""
    cover_url: str = ""
    chapters: List[Chapter] = field(default_factory=list)
    downloaded: bool = False
    download_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_chapters(self) -> int:
        """Get total number of chapters."""
        return len(self.chapters)

    @property
    def downloaded_chapters(self) -> int:
        """Get number of downloaded chapters."""
        return sum(1 for chapter in self.chapters if chapter.downloaded)

    def add_chapter(self, chapter: Chapter) -> None:
        """Add a chapter to this manga."""
        self.chapters.append(chapter)
        # Sort chapters by number
        self.chapters.sort(key=lambda x: x.number)

    def get_chapters_in_range(self, start: float, end: float) -> List[Chapter]:
        """Get chapters within a specific range."""
        return [ch for ch in self.chapters if start <= ch.number <= end]

    def create_download_structure(self, base_path: str) -> str:
        """Create the folder structure for downloading this manga."""
        # Clean title for folder name
        folder_name = "".join(c for c in self.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        if not folder_name:
            folder_name = "untitled_manga"

        self.download_path = os.path.join(base_path, folder_name)
        os.makedirs(self.download_path, exist_ok=True)
        return self.download_path


@dataclass
class DownloadProgress:
    """Tracks download progress for UI updates."""
    total_files: int = 0
    downloaded_files: int = 0
    current_chapter: Optional[str] = None
    current_file: Optional[str] = None
    speed: float = 0.0  # bytes per second
    eta: Optional[str] = None
    status: str = "idle"  # idle, downloading, paused, completed, error

    @property
    def progress_percent(self) -> float:
        """Get progress as percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.downloaded_files / self.total_files) * 100

    def reset(self):
        """Reset progress tracking."""
        self.total_files = 0
        self.downloaded_files = 0
        self.current_chapter = None
        self.current_file = None
        self.speed = 0.0
        self.eta = None
        self.status = "idle"