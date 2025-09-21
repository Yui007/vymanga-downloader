"""
Central styling and animations for the modern GUI theme.
Provides consistent colors, gradients, and animations across all components.
"""

from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPalette, QColor, QLinearGradient, QFont
from PyQt6.QtWidgets import QApplication


class ModernTheme:
    """Modern dark theme with gradients and animations."""

    # Color palette
    PRIMARY_COLOR = "#6366f1"      # Indigo
    SECONDARY_COLOR = "#8b5cf6"     # Purple
    ACCENT_COLOR = "#06b6d4"       # Cyan
    SUCCESS_COLOR = "#10b981"      # Emerald
    WARNING_COLOR = "#f59e0b"      # Amber
    ERROR_COLOR = "#ef4444"        # Red

    # Background colors
    BG_PRIMARY = "#0f0f23"         # Dark navy
    BG_SECONDARY = "#1a1a2e"       # Lighter navy
    BG_TERTIARY = "#16213e"        # Card background
    BG_HOVER = "#1e1e3f"           # Hover state

    # Text colors
    TEXT_PRIMARY = "#ffffff"       # White
    TEXT_SECONDARY = "#a3a3a3"     # Light gray
    TEXT_MUTED = "#6b7280"         # Muted gray

    # Border colors
    BORDER_PRIMARY = "#374151"     # Gray border
    BORDER_HOVER = "#4b5563"       # Lighter border

    def __init__(self):
        self.setup_theme()

    def setup_theme(self):
        """Apply the modern dark theme to the application."""
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app and isinstance(app, QApplication):
                # Set application palette
                palette = QPalette()

                # Window background
                palette.setColor(QPalette.ColorRole.Window, QColor(self.BG_PRIMARY))
                palette.setColor(QPalette.ColorRole.WindowText, QColor(self.TEXT_PRIMARY))

                # Base background
                palette.setColor(QPalette.ColorRole.Base, QColor(self.BG_SECONDARY))
                palette.setColor(QPalette.ColorRole.AlternateBase, QColor(self.BG_TERTIARY))

                # Text colors
                palette.setColor(QPalette.ColorRole.Text, QColor(self.TEXT_PRIMARY))
                palette.setColor(QPalette.ColorRole.BrightText, QColor(self.TEXT_PRIMARY))

                # Button colors
                palette.setColor(QPalette.ColorRole.Button, QColor(self.BG_TERTIARY))
                palette.setColor(QPalette.ColorRole.ButtonText, QColor(self.TEXT_PRIMARY))

                # Highlight colors
                palette.setColor(QPalette.ColorRole.Highlight, QColor(self.PRIMARY_COLOR))
                palette.setColor(QPalette.ColorRole.HighlightedText, QColor(self.TEXT_PRIMARY))

                # Tooltips
                palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(self.BG_TERTIARY))
                palette.setColor(QPalette.ColorRole.ToolTipText, QColor(self.TEXT_PRIMARY))

                app.setPalette(palette)

                # Set global font
                font = QFont("Segoe UI", 10)
                font.setStyleHint(QFont.StyleHint.System)
                app.setFont(font)
        except (ImportError, AttributeError):
            # QApplication not available or methods not found, skip styling
            pass

    def create_gradient(self, start_color: str, end_color: str, vertical: bool = True):
        """Create a linear gradient for backgrounds and buttons."""
        gradient = QLinearGradient()

        if vertical:
            gradient.setStart(0, 0)
            gradient.setFinalStop(0, 1)
        else:
            gradient.setStart(0, 0)
            gradient.setFinalStop(1, 0)

        gradient.setColorAt(0, QColor(start_color))
        gradient.setColorAt(1, QColor(end_color))

        return gradient

    def create_button_gradient(self):
        """Create gradient for primary buttons."""
        return self.create_gradient(self.PRIMARY_COLOR, self.SECONDARY_COLOR)

    def create_card_gradient(self):
        """Create subtle gradient for cards."""
        return self.create_gradient(self.BG_TERTIARY, self.BG_HOVER)

    def create_hover_animation(self, widget, duration: int = 200):
        """Create a smooth hover animation for widgets."""
        animation = QPropertyAnimation(widget, b"geometry")

        # Store original geometry
        original_geometry = widget.geometry()

        animation.setDuration(duration)
        animation.setEasingCurve(QEasingCurve.Type.InOutCubic)

        def on_hover_enter():
            # Slightly expand the widget on hover
            new_geometry = original_geometry.adjusted(-2, -2, 2, 2)
            animation.setStartValue(original_geometry)
            animation.setEndValue(new_geometry)
            animation.start()

        def on_hover_leave():
            # Return to original size
            animation.setStartValue(widget.geometry())
            animation.setEndValue(original_geometry)
            animation.start()

        return on_hover_enter, on_hover_leave

    def create_fade_animation(self, widget, duration: int = 300):
        """Create a fade in/out animation."""
        fade_animation = QPropertyAnimation(widget, b"windowOpacity")
        fade_animation.setDuration(duration)
        fade_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)

        return fade_animation

    def create_scale_animation(self, widget, duration: int = 200):
        """Create a scale animation for buttons and cards."""
        # Note: For scale animations, we'll use geometry changes
        scale_animation = QPropertyAnimation(widget, b"geometry")
        scale_animation.setDuration(duration)
        scale_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)

        return scale_animation


# Global theme instance
theme = ModernTheme()


def apply_widget_style(widget, style_type: str = "card"):
    """Apply consistent styling to widgets based on type."""
    if style_type == "card":
        widget.setStyleSheet(f"""
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                      stop: 0 {theme.BG_TERTIARY},
                                      stop: 1 {theme.BG_HOVER});
            border: 1px solid {theme.BORDER_PRIMARY};
            border-radius: 12px;
            color: {theme.TEXT_PRIMARY};
        """)

    elif style_type == "button_primary":
        widget.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 {theme.PRIMARY_COLOR},
                                          stop: 1 {theme.SECONDARY_COLOR});
                border: none;
                border-radius: 8px;
                color: {theme.TEXT_PRIMARY};
                padding: 12px 24px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 {theme.ACCENT_COLOR},
                                          stop: 1 {theme.PRIMARY_COLOR});
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 {theme.SECONDARY_COLOR},
                                          stop: 1 {theme.PRIMARY_COLOR});
            }}
        """)

    elif style_type == "button_secondary":
        widget.setStyleSheet(f"""
            QPushButton {{
                background: {theme.BG_TERTIARY};
                border: 1px solid {theme.BORDER_PRIMARY};
                border-radius: 8px;
                color: {theme.TEXT_PRIMARY};
                padding: 10px 20px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: {theme.BG_HOVER};
                border-color: {theme.BORDER_HOVER};
            }}
            QPushButton:pressed {{
                background: {theme.BORDER_HOVER};
            }}
        """)

    elif style_type == "input":
        widget.setStyleSheet(f"""
            QLineEdit, QTextEdit, QSpinBox, QComboBox {{
                background: {theme.BG_TERTIARY};
                border: 1px solid {theme.BORDER_PRIMARY};
                border-radius: 6px;
                color: {theme.TEXT_PRIMARY};
                padding: 8px 12px;
                selection-background-color: {theme.PRIMARY_COLOR};
            }}
            QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
                border-color: {theme.PRIMARY_COLOR};
                background: {theme.BG_HOVER};
            }}
        """)

    elif style_type == "tab":
        widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {theme.BORDER_PRIMARY};
                background: {theme.BG_SECONDARY};
                border-radius: 8px;
            }}
            QTabBar::tab {{
                background: {theme.BG_TERTIARY};
                border: 1px solid {theme.BORDER_PRIMARY};
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                color: {theme.TEXT_SECONDARY};
                padding: 12px 20px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 {theme.PRIMARY_COLOR},
                                          stop: 1 {theme.SECONDARY_COLOR});
                color: {theme.TEXT_PRIMARY};
                border-color: {theme.PRIMARY_COLOR};
            }}
            QTabBar::tab:hover {{
                background: {theme.BG_HOVER};
                color: {theme.TEXT_PRIMARY};
            }}
        """)

    elif style_type == "progress":
        widget.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {theme.BORDER_PRIMARY};
                border-radius: 4px;
                background: {theme.BG_TERTIARY};
                color: {theme.TEXT_PRIMARY};
                text-align: center;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                          stop: 0 {theme.SUCCESS_COLOR},
                                          stop: 1 {theme.ACCENT_COLOR});
                border-radius: 3px;
            }}
        """)

    elif style_type == "label":
        widget.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_PRIMARY};
                background: transparent;
            }}
        """)


def create_animated_button(text: str, primary: bool = True):
    """Create a styled button with hover animations."""
    from PyQt6.QtWidgets import QPushButton

    button = QPushButton(text)

    if primary:
        apply_widget_style(button, "button_primary")
    else:
        apply_widget_style(button, "button_secondary")

    # Note: Hover animations will be handled by CSS hover effects in the stylesheet
    # For now, we rely on the CSS transitions defined in the button styles

    return button


def create_styled_label(text: str, style: str = "normal"):
    """Create a styled label."""
    from PyQt6.QtWidgets import QLabel

    label = QLabel(text)

    if style == "title":
        label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_PRIMARY};
                font-size: 24px;
                font-weight: bold;
                background: transparent;
            }}
        """)
    elif style == "subtitle":
        label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SECONDARY};
                font-size: 16px;
                background: transparent;
            }}
        """)
    else:
        apply_widget_style(label, "label")

    return label