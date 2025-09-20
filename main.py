#!/usr/bin/env python3
"""
Main entry point for VYManga Downloader.
Supports both CLI and GUI modes.
"""

import sys
import argparse
from pathlib import Path

# Add current directory to Python path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from utils import logger, setup_logging


def check_dependencies():
    """Check if required dependencies are installed."""
    # Map package names to their import names
    dependency_map = {
        'requests': 'requests',
        'beautifulsoup4': 'bs4',
        'pillow': 'PIL'
    }

    missing_modules = []

    for package_name, import_name in dependency_map.items():
        try:
            __import__(import_name)
        except ImportError:
            missing_modules.append(package_name)

    if missing_modules:
        print("❌ Missing required dependencies:")
        for module in missing_modules:
            print(f"  • {module}")

        print("\n📦 Install dependencies:")
        print("  pip install -r requirements.txt")
        print("\n   or")
        print("  pip install requests beautifulsoup4 pillow")

        return False

    return True


def create_argument_parser():
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="VYManga Downloader - Modern manga downloader for vymanga.co",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Interactive CLI mode
  python main.py --gui              # GUI mode (if available)
  python main.py --url URL --format pdf  # Direct download
  python main.py --help             # Show detailed help

Supported formats: images, pdf, cbz
Supported qualities: high, medium, low
        """
    )

    # Mode selection
    parser.add_argument('--cli', action='store_true', default=True,
                       help='Run in CLI mode (default)')
    parser.add_argument('--gui', action='store_true',
                       help='Run in GUI mode (not yet implemented)')

    # Quick download options
    parser.add_argument('--url', help='Manga URL from vymanga.co')
    parser.add_argument('--range', nargs=2, metavar=('START', 'END'),
                       help='Chapter range (e.g., 1 10)')
    parser.add_argument('--chapter', type=float, help='Single chapter number')
    parser.add_argument('--format', choices=['images', 'pdf', 'cbz'],
                       default='images', help='Output format')
    parser.add_argument('--quality', choices=['high', 'medium', 'low'],
                       default='medium', help='Image quality')
    parser.add_argument('--output', help='Download directory')

    # Configuration
    parser.add_argument('--workers', type=int, default=4,
                       help='Number of download threads')
    parser.add_argument('--timeout', type=int, default=30,
                       help='Request timeout in seconds')

    # Logging
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')

    # Information
    parser.add_argument('--version', action='version', version='VYManga Downloader 1.0.0')

    return parser


def main():
    """Main application entry point."""
    # Set up logging first
    setup_logging('INFO')

    # Create argument parser
    parser = create_argument_parser()
    args = parser.parse_args()

    # Override logging level based on arguments
    if args.debug:
        setup_logging('DEBUG')
    elif args.verbose:
        setup_logging('INFO')

    # Display banner
    print("""
╔══════════════════════════════════════════════════════════════╗
║                    📖 VYManga Downloader                    ║
║                    Modern Manga Downloads                    ║
║                                                              ║
║  • Interactive CLI & Beautiful GUI                           ║
║  • Fast Multi-threaded Downloads                            ║
║  • PDF & CBZ Conversion                                      ║
║  • Resume Interrupted Downloads                              ║
╚══════════════════════════════════════════════════════════════╝
    """)

    # Check dependencies
    if not check_dependencies():
        return 1

    # Handle GUI mode (placeholder for future implementation)
    if args.gui:
        print("🎨 GUI mode requested, but not yet implemented.")
        print("💡 Use CLI mode for now: python main.py")
        return 0

    # Handle quick download mode
    if args.url:
        return run_quick_download(args)

    # Default to CLI mode
    try:
        from cli import InteractiveCLI
        cli = InteractiveCLI()
        cli.download_manga_interactive()
        return 0
    except ImportError as e:
        logger.error(f"Failed to import CLI module: {e}")
        print("❌ Error: Could not load CLI module.")
        print("💡 Make sure all files are in the same directory.")
        return 1
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"❌ Unexpected error: {e}")
        return 1


def run_quick_download(args):
    """Run a quick download with command line arguments."""
    try:
        # Import required modules
        from scraper import VymangaScraper
        from downloader import MangaDownloader
        from converter import MangaConverter
        from models import Manga

        print("🚀 Quick Download Mode")

        # Validate URL
        if not args.url.startswith(('http://', 'https://')):
            args.url = f"https://{args.url}"

        if 'vymanga.co' not in args.url:
            print("⚠️  Warning: This URL doesn't appear to be from vymanga.co")
            return 1

        # Initialize components
        scraper = VymangaScraper()
        downloader = MangaDownloader(max_workers=args.workers)
        converter = MangaConverter(quality=args.quality)

        # Set download path
        download_path = args.output or str(Path.home() / "Downloads" / "Manga")
        Path(download_path).mkdir(parents=True, exist_ok=True)

        # Scrape manga info
        print(f"📖 Scraping manga from: {args.url}")
        manga = scraper.scrape_manga_info(args.url)

        if not manga:
            print("❌ Failed to scrape manga information.")
            return 1

        print(f"📋 Found: {manga.title} ({len(manga.chapters)} chapters)")

        # Filter chapters based on arguments
        if args.chapter:
            chapters_to_download = [ch for ch in manga.chapters if ch.number == args.chapter]
            if not chapters_to_download:
                print(f"❌ Chapter {args.chapter} not found.")
                return 1
        elif args.range:
            try:
                start, end = float(args.range[0]), float(args.range[1])
                chapters_to_download = [ch for ch in manga.chapters if start <= ch.number <= end]
            except ValueError:
                print("❌ Invalid chapter range.")
                return 1
        else:
            chapters_to_download = manga.chapters

        if not chapters_to_download:
            print("❌ No chapters selected for download.")
            return 1

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

        print(f"⬇️  Downloading {len(chapters_to_download)} chapters to {download_path}...")

        # Scrape chapter pages
        for chapter in chapters_to_download:
            success = scraper.scrape_chapter_pages(chapter)
            if not success:
                print(f"⚠️  Warning: Failed to scrape pages for {chapter.title}")

        # Download manga
        success = downloader.download_manga(temp_manga, download_path)

        if not success:
            print("❌ Download failed.")
            return 1

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

        return 0

    except ImportError as e:
        print(f"❌ Error: Missing required module: {e}")
        print("💡 Install dependencies: pip install -r requirements.txt")
        return 1
    except KeyboardInterrupt:
        print("\n\n👋 Download cancelled by user.")
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())