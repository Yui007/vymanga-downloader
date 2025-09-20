"""
Interactive CLI for the manga downloader.
Provides both guided prompts and command-line argument support.
"""

import argparse
import sys
import os
from typing import Optional, List
from pathlib import Path

from models import Manga
from scraper import VymangaScraper
from downloader import MangaDownloader
from converter import MangaConverter
from utils import logger, setup_logging, get_download_path, sanitize_filename


class InteractiveCLI:
    """Interactive command-line interface for the manga downloader."""

    def __init__(self):
        """Initialize the CLI."""
        self.scraper = VymangaScraper()
        self.downloader = MangaDownloader()
        self.converter = MangaConverter()

    def show_banner(self):
        """Display the application banner."""
        banner = """
╔══════════════════════════════════════════════════════════════╗
║                    📖 VYManga Downloader                    ║
║                    Modern Manga Downloads                    ║
║                                                              ║
║  • Interactive CLI & Beautiful GUI                           ║
║  • Fast Multi-threaded Downloads                            ║
║  • PDF & CBZ Conversion                                      ║
║  • Resume Interrupted Downloads                              ║
╚══════════════════════════════════════════════════════════════╝
        """
        print(banner)

    def get_user_input(self, prompt: str, default: str = "") -> str:
        """
        Get user input with optional default value.

        Args:
            prompt: Input prompt
            default: Default value if user enters nothing

        Returns:
            User input or default value
        """
        try:
            response = input(f"{prompt} [{default}]: ").strip()
            return response if response else default
        except KeyboardInterrupt:
            print("\n\nOperation cancelled by user.")
            sys.exit(0)

    def select_download_format(self) -> tuple:
        """Let user select download format and options."""
        print("\n📁 Select download format:")
        print("1. Images only (JPG/PNG)")
        print("2. PDF format")
        print("3. CBZ format (Comic Book Archive)")

        while True:
            choice = self.get_user_input("Enter choice (1-3)", "1")
            if choice in ['1', '2', '3']:
                formats = { '1': 'images', '2': 'pdf', '3': 'cbz' }
                format_choice = formats[choice]

                # Ask about separate chapters for PDF/CBZ
                separate_chapters = True
                if format_choice in ['pdf', 'cbz']:
                    separate_choice = self.get_user_input("Create separate files per chapter? (Y/n)", "y")
                    separate_chapters = not separate_choice.lower().startswith('n')

                    # Ask about deleting images after conversion
                    delete_choice = self.get_user_input("Delete original images after conversion? (y/N)", "n")
                    delete_images = delete_choice.lower().startswith('y')
                else:
                    delete_images = False

                return format_choice, separate_chapters, delete_images
            print("❌ Invalid choice. Please select 1, 2, or 3.")

    def select_quality(self) -> str:
        """Let user select image quality."""
        print("\n🎨 Select image quality:")
        print("1. High (Best quality, larger files)")
        print("2. Medium (Balanced quality/size)")
        print("3. Low (Smaller files, lower quality)")

        while True:
            choice = self.get_user_input("Enter choice (1-3)", "2")
            if choice in ['1', '2', '3']:
                qualities = { '1': 'high', '2': 'medium', '3': 'low' }
                return qualities[choice]
            print("❌ Invalid choice. Please select 1, 2, or 3.")

    def select_threading_options(self) -> tuple:
        """Let user select threading options for downloads and scraping."""
        print("\n⚡ Select performance options:")

        # Scraping workers
        print("\n🔍 Parallel chapter scraping:")
        print("  How many chapters to scrape simultaneously")
        scraping_workers = self.get_user_input("Scraping workers (1-5)", "3")

        # Chapter workers
        print("\n📚 Parallel chapter downloads:")
        print("  How many chapters to download simultaneously")
        chapter_workers = self.get_user_input("Download workers (1-5)", "2")

        # Image workers
        print("\n🖼️  Images per chapter:")
        print("  How many images to download simultaneously per chapter")
        image_workers = self.get_user_input("Images at once (2-8)", "4")

        try:
            scraping_workers = max(1, min(5, int(scraping_workers)))
            chapter_workers = max(1, min(5, int(chapter_workers)))
            image_workers = max(2, min(8, int(image_workers)))
        except ValueError:
            scraping_workers = 3
            chapter_workers = 2
            image_workers = 4

        return scraping_workers, chapter_workers, image_workers

    def select_chapters(self, manga: Manga) -> List[float]:
        """
        Let user select which chapters to download.

        Args:
            manga: Manga object with chapter list

        Returns:
            List of chapter numbers to download
        """
        if not manga.chapters:
            print("❌ No chapters found for this manga.")
            return []

        print(f"\n📚 Found {len(manga.chapters)} chapters:")
        for i, chapter in enumerate(manga.chapters[:10]):  # Show first 10
            print(f"  {chapter.number:6.1f} - {chapter.title}")
        if len(manga.chapters) > 10:
            print(f"  ... and {len(manga.chapters) - 10} more chapters")

        print("\n📋 Chapter selection options:")
        print("1. Download all chapters")
        print("2. Download specific range (e.g., 1-10)")
        print("3. Download single chapter")

        while True:
            choice = self.get_user_input("Enter choice (1-3)", "1")

            if choice == '1':
                return [ch.number for ch in manga.chapters]

            elif choice == '2':
                start = self.get_user_input("Start chapter", "1")
                end = self.get_user_input("End chapter", str(manga.chapters[-1].number))

                try:
                    start_num = float(start)
                    end_num = float(end)
                    return [ch.number for ch in manga.chapters if start_num <= ch.number <= end_num]
                except ValueError:
                    print("❌ Invalid chapter numbers. Please try again.")
                    continue

            elif choice == '3':
                chapter_num = self.get_user_input("Chapter number", "")
                try:
                    num = float(chapter_num)
                    if any(ch.number == num for ch in manga.chapters):
                        return [num]
                    else:
                        print(f"❌ Chapter {num} not found.")
                        continue
                except ValueError:
                    print("❌ Invalid chapter number. Please try again.")
                    continue

            else:
                print("❌ Invalid choice. Please select 1, 2, or 3.")

    def download_manga_interactive(self):
        """Interactive manga download workflow."""
        self.show_banner()

        print("\n🚀 Welcome to VYManga Downloader!")
        print("Let's download some manga step by step.\n")

        # Get manga URL
        manga_url = self.get_user_input("Enter manga URL from vymanga.co")
        if not manga_url:
            print("❌ No URL provided. Exiting.")
            return

        # Validate URL
        if not manga_url.startswith(('http://', 'https://')):
            manga_url = f"https://{manga_url}"

        if 'vymanga.co' not in manga_url:
            print("⚠️  Warning: This URL doesn't appear to be from vymanga.co")
            if not self.get_user_input("Continue anyway? (y/N)", "n").lower().startswith('y'):
                return

        # Scrape manga info
        print("\n📖 Scraping manga information...")
        manga = self.scraper.scrape_manga_info(manga_url)

        if not manga:
            print("❌ Failed to scrape manga information. Please check the URL and try again.")
            return

        # Display manga info
        print("\n📋 Manga Information:")
        print(f"  Title: {manga.title}")
        print(f"  Author: {manga.author}")
        print(f"  Status: {manga.status}")
        print(f"  Genres: {', '.join(manga.genres)}")
        print(f"  Chapters: {len(manga.chapters)}")

        if manga.summary:
            print(f"  Summary: {manga.summary[:200]}{'...' if len(manga.summary) > 200 else ''}")

        # Select chapters
        chapters_to_download = self.select_chapters(manga)
        if not chapters_to_download:
            print("❌ No chapters selected. Exiting.")
            return

        # Filter manga to selected chapters
        selected_chapters = [ch for ch in manga.chapters if ch.number in chapters_to_download]
        temp_manga = Manga(
            title=manga.title,
            url=manga.url,
            author=manga.author,
            status=manga.status,
            genres=manga.genres,
            summary=manga.summary,
            cover_url=manga.cover_url,
            chapters=selected_chapters
        )

        # Select download format and options
        download_format, separate_chapters, delete_images = self.select_download_format()

        # Select quality
        quality = self.select_quality()
        self.converter.quality = quality

        # Select threading options
        scraping_workers, chapter_workers, image_workers = self.select_threading_options()

        # Set download path
        default_path = get_download_path()
        download_path = self.get_user_input("Download path", default_path)

        # Create download directory
        os.makedirs(download_path, exist_ok=True)

        # Start download
        print("\n⬇️  Starting download...")
        print(f"  Format: {download_format}")
        print(f"  Quality: {quality}")
        print(f"  Path: {download_path}")
        print(f"  Chapters: {len(selected_chapters)}")
        print(f"  Separate chapters: {'Yes' if separate_chapters else 'No'}")
        print(f"  Parallel scraping: {scraping_workers}")
        print(f"  Parallel downloads: {chapter_workers}")
        print(f"  Images per chapter: {image_workers}")
        if download_format in ['pdf', 'cbz']:
            print(f"  Delete images after conversion: {'Yes' if delete_images else 'No'}")

        if self.get_user_input("Start download? (Y/n)", "y").lower().startswith('n'):
            print("❌ Download cancelled.")
            return

        # Initialize downloader with threading options
        self.downloader = MangaDownloader(
            chapter_workers=chapter_workers,
            image_workers=image_workers
        )

        # Scrape chapter pages with parallel processing
        print(f"\n📄 Scraping chapter pages using {scraping_workers} parallel workers...")
        success = self.scraper.scrape_selected_chapters(
            temp_manga.chapters,
            max_workers=scraping_workers
        )

        if not success:
            print("❌ Failed to scrape chapter pages.")
            return

        # Download manga
        success = self.downloader.download_manga(temp_manga, download_path)

        if not success:
            print("❌ Download failed.")
            return

        # Convert if needed
        if download_format in ['pdf', 'cbz']:
            print(f"\n🔄 Converting to {download_format.upper()} format...")
            print(f"  Creating {'separate files per chapter' if separate_chapters else 'single combined file'}...")

            if download_format == 'pdf':
                success = self.converter.convert_manga_to_pdf(
                    temp_manga,
                    separate_chapters=separate_chapters,
                    delete_images=delete_images
                )
            else:
                success = self.converter.convert_manga_to_cbz(
                    temp_manga,
                    separate_chapters=separate_chapters,
                    delete_images=delete_images
                )

            if success:
                print("✅ Conversion completed successfully!")
            else:
                print("❌ Conversion failed.")

        print("\n🎉 Download completed successfully!")
        print(f"  Files saved to: {download_path}")

    def show_help(self):
        """Display help information."""
        help_text = """
📖 VYManga Downloader - Help

Interactive Mode:
  Run without arguments for guided setup

Command Line Arguments:
  --url URL              Manga URL to download
  --range START END      Chapter range (e.g., --range 1 10)
  --chapter NUM          Single chapter number
  --format FORMAT        Output format: images, pdf, cbz (default: images)
  --quality QUALITY      Image quality: high, medium, low (default: medium)
  --output PATH          Download directory (default: ~/Downloads/Manga)
  --scraping-workers NUM Chapters to scrape simultaneously (default: 3)
  --chapter-workers NUM  Chapters to download simultaneously (default: 2)
  --image-workers NUM    Images to download simultaneously per chapter (default: 4)
  --workers NUM          Deprecated: use --chapter-workers and --image-workers
  --verbose              Enable verbose logging
  --quiet                Minimal output

Examples:
  python main.py --url https://vymanga.co/manga/example --range 1 10 --format pdf
  python main.py --url https://vymanga.co/manga/example --chapter 5 --format cbz
  python main.py --url https://vymanga.co/manga/example --format images --quality high
  python main.py --url https://vymanga.co/manga/example --scraping-workers 5 --chapter-workers 3 --image-workers 6
  python main.py --url https://vymanga.co/manga/example --scraping-workers 5 --chapter-workers 3 --image-workers 6
        """
        print(help_text)


def create_argument_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Modern manga downloader for vymanga.co",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --url https://vymanga.co/manga/example --range 1 10 --format pdf
  python main.py --url https://vymanga.co/manga/example --chapter 5 --format cbz
  python main.py --url https://vymanga.co/manga/example --format images --quality high
        """
    )

    parser.add_argument('--url', help='Manga URL from vymanga.co')
    parser.add_argument('--range', nargs=2, metavar=('START', 'END'),
                       help='Chapter range to download (e.g., 1 10)')
    parser.add_argument('--chapter', type=float, help='Single chapter number to download')
    parser.add_argument('--format', choices=['images', 'pdf', 'cbz'],
                       default='images', help='Output format (default: images)')
    parser.add_argument('--quality', choices=['high', 'medium', 'low'],
                       default='medium', help='Image quality (default: medium)')
    parser.add_argument('--output', help='Download directory')
    parser.add_argument('--workers', type=int, default=4,
                       help='Number of download threads (deprecated, use --chapter-workers and --image-workers)')
    parser.add_argument('--scraping-workers', type=int, default=3,
                        help='Number of chapters to scrape simultaneously (default: 3)')
    parser.add_argument('--chapter-workers', type=int, default=2,
                        help='Number of chapters to download simultaneously (default: 2)')
    parser.add_argument('--image-workers', type=int, default=4,
                        help='Number of images to download simultaneously per chapter (default: 4)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Minimal output')

    return parser


def main_cli():
    """Main CLI entry point."""
    # Parse command line arguments
    parser = create_argument_parser()
    args = parser.parse_args()

    # Set up logging
    log_level = 'DEBUG' if args.verbose else 'WARNING' if args.quiet else 'INFO'
    setup_logging(log_level)

    # Interactive mode if no URL provided
    if not args.url:
        cli = InteractiveCLI()
        cli.download_manga_interactive()
        return

    # Command line mode
    print("🚀 VYManga Downloader (Command Line Mode)")

    # Validate URL
    if not args.url.startswith(('http://', 'https://')):
        args.url = f"https://{args.url}"

    if 'vymanga.co' not in args.url:
        print("⚠️  Warning: This URL doesn't appear to be from vymanga.co")
        return

    # Initialize components
    scraper = VymangaScraper()
    downloader = MangaDownloader(
        chapter_workers=args.chapter_workers,
        image_workers=args.image_workers
    )
    converter = MangaConverter(quality=args.quality)

    # Set download path
    download_path = args.output or get_download_path()
    os.makedirs(download_path, exist_ok=True)

    # Scrape manga info
    print(f"📖 Scraping manga from: {args.url}")
    manga = scraper.scrape_manga_info(args.url)

    if not manga:
        print("❌ Failed to scrape manga information.")
        return

    print(f"📋 Found: {manga.title} ({len(manga.chapters)} chapters)")

    # Filter chapters based on arguments
    if args.chapter:
        # Single chapter
        chapters_to_download = [ch for ch in manga.chapters if ch.number == args.chapter]
        if not chapters_to_download:
            print(f"❌ Chapter {args.chapter} not found.")
            return
    elif args.range:
        # Chapter range
        try:
            start, end = float(args.range[0]), float(args.range[1])
            chapters_to_download = [ch for ch in manga.chapters if start <= ch.number <= end]
        except ValueError:
            print("❌ Invalid chapter range.")
            return
    else:
        # All chapters
        chapters_to_download = manga.chapters

    if not chapters_to_download:
        print("❌ No chapters selected for download.")
        return

    # Create filtered manga object
    temp_manga = Manga(
        title=manga.title,
        url=manga.url,
        author=manga.author,
        status=manga.status,
        genres=manga.genres,
        summary=manga.summary,
        cover_url=manga.cover_url,
        chapters=chapters_to_download
    )

    print(f"⬇️  Downloading {len(chapters_to_download)} chapters...")

    # Scrape chapter pages with parallel processing
    print(f"📄 Scraping chapter pages using {args.scraping_workers} parallel workers...")
    success = scraper.scrape_selected_chapters(
        temp_manga.chapters,
        max_workers=args.scraping_workers
    )

    if not success:
        print("❌ Failed to scrape chapter pages.")
        return

    # Download manga
    success = downloader.download_manga(temp_manga, download_path)

    if not success:
        print("❌ Download failed.")
        return

    # Convert if needed
    if args.format in ['pdf', 'cbz']:
        print(f"🔄 Converting to {args.format.upper()} format...")

        if args.format == 'pdf':
            success = converter.convert_manga_to_pdf(temp_manga)
        else:
            success = converter.convert_manga_to_cbz(temp_manga)

        if success:
            print("✅ Conversion completed successfully!")
        else:
            print("❌ Conversion failed.")

    print("\n🎉 Download completed successfully!")
    print(f"  Files saved to: {download_path}")


if __name__ == "__main__":
    main_cli()