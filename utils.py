"""
Utility functions for the manga downloader.
Includes logging setup, file operations, and other helper functions.
"""

import os
import sys
import logging
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import hashlib


def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """
    Set up logging configuration.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path

    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger("vymanga_downloader")
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # Always log debug to file
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def ensure_directory(path: str) -> str:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path to create

    Returns:
        The absolute path of the directory
    """
    Path(path).mkdir(parents=True, exist_ok=True)
    return os.path.abspath(path)


def get_download_path() -> str:
    """
    Get the default download path for manga.

    Returns:
        Default download directory path
    """
    home = Path.home()
    download_path = home / "Downloads" / "Manga"
    return str(download_path)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing invalid characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename safe for filesystem
    """
    # Characters to replace with underscore
    invalid_chars = '<>:"/\\|?*'
    sanitized = filename

    for char in invalid_chars:
        sanitized = sanitized.replace(char, '_')

    # Remove multiple consecutive underscores
    while '__' in sanitized:
        sanitized = sanitized.replace('__', '_')

    # Remove leading/trailing whitespace and underscores
    sanitized = sanitized.strip(' _')

    # Ensure it's not empty
    if not sanitized:
        sanitized = "untitled"

    return sanitized


def calculate_file_hash(file_path: str) -> str:
    """
    Calculate SHA256 hash of a file.

    Args:
        file_path: Path to the file

    Returns:
        SHA256 hash as hex string
    """
    hash_sha256 = hashlib.sha256()

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)

    return hash_sha256.hexdigest()


def format_bytes(bytes_size: float) -> str:
    """
    Format bytes into human readable format.

    Args:
        bytes_size: Size in bytes

    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    size = float(bytes_size)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def format_time(seconds: float) -> str:
    """
    Format seconds into human readable time.

    Args:
        seconds: Time in seconds

    Returns:
        Formatted time string (e.g., "1h 30m 45s")
    """
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes:.0f}m {remaining_seconds:.0f}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        remaining_seconds = seconds % 60
        return f"{hours:.0f}h {minutes:.0f}m {remaining_seconds:.0f}s"


def save_json(data: Dict[str, Any], file_path: str) -> None:
    """
    Save data to JSON file with pretty formatting.

    Args:
        data: Data to save
        file_path: Path to save the JSON file
    """
    ensure_directory(os.path.dirname(file_path))

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_json(file_path: str) -> Dict[str, Any]:
    """
    Load data from JSON file.

    Args:
        file_path: Path to the JSON file

    Returns:
        Loaded data as dictionary
    """
    if not os.path.exists(file_path):
        return {}

    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_file_size(file_path: str) -> int:
    """
    Get file size in bytes.

    Args:
        file_path: Path to the file

    Returns:
        File size in bytes
    """
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0


def is_valid_image_url(url: str) -> bool:
    """
    Check if URL points to a valid image format.

    Args:
        url: Image URL to check

    Returns:
        True if URL has valid image extension or appears to be an image URL
    """
    if not url:
        logger.debug("URL validation: empty URL")
        return False

    valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
    url_lower = url.lower()

    logger.debug(f"Validating URL: {url}")

    # Check for standard image extensions
    if any(url_lower.endswith(ext) for ext in valid_extensions):
        logger.debug("URL validation: has valid extension")
        return True

    # For URLs without extensions (like those from vymanga), check if they look like image URLs
    # These typically contain image-related keywords or are from known image hosts
    image_keywords = {'image', 'img', 'photo', 'picture', 'cdn', 'data'}
    image_hosts = {'beercdn.info', 'imgur.com', 'i.imgur.com', 'cdn', 'blogspot.com', 'bp.blogspot.com'}

    # Check if URL contains image-related keywords
    if any(keyword in url_lower for keyword in image_keywords):
        logger.debug("URL validation: contains image keywords")
        return True

    # Check if URL is from known image hosting domains
    if any(host in url_lower for host in image_hosts):
        logger.debug("URL validation: from known image host")
        return True

    # For vymanga specifically, allow URLs that don't have extensions but look like data URLs
    if 'vymanga' in url_lower or 'data.beercdn' in url_lower:
        logger.debug("URL validation: vymanga/data.beercdn URL")
        return True

    logger.debug("URL validation: rejected")
    return False


def create_progress_callback(description: str = "Progress"):
    """
    Create a progress callback function for use with downloaders.

    Args:
        description: Description for the progress

    Returns:
        Progress callback function
    """
    def progress_callback(current: int, total: int, speed: float = 0.0):
        """Progress callback function."""
        percent = (current / total) * 100 if total > 0 else 0
        speed_str = f"{format_bytes(speed)}/s" if speed > 0 else ""
        print(f"\r{description}: {percent:.1f}% ({current}/{total}) {speed_str}", end="", flush=True)

        if current >= total:
            print()  # New line when complete

    return progress_callback


class Timer:
    """Simple timer class for measuring execution time."""

    def __init__(self):
        self.start_time = None
        self.end_time = None

    def start(self):
        """Start the timer."""
        self.start_time = datetime.now()
        return self

    def stop(self):
        """Stop the timer."""
        self.end_time = datetime.now()
        return self

    @property
    def elapsed(self) -> float:
        """Get elapsed time in seconds."""
        if self.start_time is None:
            return 0.0
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()

    @property
    def elapsed_str(self) -> str:
        """Get elapsed time as formatted string."""
        return format_time(self.elapsed)


# Global logger instance
logger = setup_logging()