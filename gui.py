"""
Main GUI entry point for VYManga Downloader.
Sets up the PyQt6 application and displays the main window.
"""

import sys
import os
from pathlib import Path

# Add current directory to Python path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt, QTranslator, QLocale
from PyQt6.QtGui import QIcon

from gui_main_window import MainWindow
from utils import logger, setup_logging


def check_dependencies():
    """Check if required dependencies are installed."""
    missing_modules = []

    # Check PyQt6
    try:
        import PyQt6
    except ImportError:
        missing_modules.append("PyQt6")

    # Check other core dependencies
    dependency_map = {
        'requests': 'requests',
        'beautifulsoup4': 'bs4',
        'pillow': 'PIL'
    }

    for package_name, import_name in dependency_map.items():
        try:
            __import__(import_name)
        except ImportError:
            missing_modules.append(package_name)

    if missing_modules:
        error_msg = "Missing required dependencies:\n\n"
        for module in missing_modules:
            error_msg += f"• {module}\n"

        error_msg += "\nInstall dependencies:\n"
        error_msg += "pip install -r requirements.txt\n\n"
        error_msg += "or\n\n"
        error_msg += "pip install PyQt6 requests beautifulsoup4 pillow"

        return False, error_msg

    return True, ""


def setup_application():
    """Setup the PyQt6 application."""
    # Create QApplication instance
    app = QApplication(sys.argv)

    # Set application properties
    app.setApplicationName("VYManga Downloader")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("VYManga")
    app.setOrganizationDomain("vymanga.co")

    # Set application icon (if available)
    # app.setWindowIcon(QIcon("icon.png"))

    # Note: High DPI scaling attributes removed due to type checking issues
    # The application will still work correctly without them

    # Set the application to use the system locale
    QLocale.setDefault(QLocale.system())

    return app


def show_splash_screen():
    """Show a splash screen while loading."""
    # For now, we'll skip the splash screen to keep it simple
    # In a production app, you might want to show a splash screen
    pass


def main_gui():
    """Main GUI entry point."""
    # Set up logging
    setup_logging('INFO')

    logger.info("Starting VYManga Downloader GUI")

    # Check dependencies
    dependencies_ok, error_msg = check_dependencies()

    if not dependencies_ok:
        # Show error message and exit
        app = QApplication(sys.argv)
        QMessageBox.critical(None, "Missing Dependencies", error_msg)
        return 1

    # Setup application
    app = setup_application()

    # Show splash screen
    show_splash_screen()

    try:
        # Create and show main window
        logger.info("Creating main window")
        main_window = MainWindow()

        # Show the main window
        main_window.show()

        # Set window to be maximized for better user experience
        main_window.showMaximized()

        logger.info("GUI started successfully")

        # Start event loop
        return app.exec()

    except Exception as e:
        logger.error(f"Error starting GUI: {e}")
        logger.error(f"Traceback: {sys.exc_info()}")

        # Show error message
        error_msg = f"An error occurred while starting the application:\n\n{str(e)}"
        QMessageBox.critical(None, "Application Error", error_msg)

        return 1


def run_gui_with_args(args):
    """Run GUI with command line arguments."""
    # For now, we'll ignore command line arguments in GUI mode
    # In a more advanced implementation, you could parse args to pre-fill URLs, etc.
    return main_gui()


if __name__ == "__main__":
    sys.exit(main_gui())