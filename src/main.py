import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QMenuBar, QMenu, QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QDialog, QLabel, QPushButton
from PyQt6.QtGui import QAction, QDesktopServices, QPixmap
from PyQt6.QtCore import QDir, Qt, QUrl, QSize, QLocale, QTranslator, QSettings
from .ui.prompt_manager_widget import PromptManager
from .theme_manager import ThemeManager

__version__ = "0.1.1"

# Custom About Dialog for displaying SVG and text
class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("About PromptVault (v{0})").format(__version__))
        self.setFixedSize(450, 400) # Fixed size for the dialog

        layout = QVBoxLayout(self)

        # Load and display SVG logo
        logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "images", "promptvault_logo.svg")
        logo_label = QLabel(self)
        pixmap = QPixmap(logo_path)
        if not pixmap.isNull():
            # Scale pixmap to fit within a reasonable size, e.g., 200x200
            scaled_pixmap = pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            logo_label.setText(self.tr("Logo not found or could not be loaded."))
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo_label)

        # App description
        description_label = QLabel(self.tr("PromptVault (v{0}) is a desktop application designed to help users manage, organize, and quickly access their AI prompts.").format(__version__), self)
        description_label.setWordWrap(True)
        description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(description_label)

        # Add a spacer to push content up
        layout.addStretch(1)

        # OK button
        ok_button = QPushButton(self.tr("OK"), self)
        ok_button.clicked.connect(self.accept)
        layout.addWidget(ok_button)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr('Prompt Manager'))
        self.setGeometry(200, 200, 950, 600)  # Set a default size
        self.initUI()

    def initUI(self):
        # Initialize ThemeManager
        current_dir = os.path.dirname(os.path.abspath(__file__))
        assets_path = os.path.join(current_dir, "..", "assets")
        QDir.addSearchPath("assets", assets_path)
        themes_path = os.path.join(assets_path, "themes")
        QDir.addSearchPath("themes", themes_path)
        self.theme_manager = ThemeManager(QApplication.instance(), themes_path)
        self.theme_manager.load_theme("light") # Set initial theme
        
        # Create a container widget for the central area
        central_widget_container = QWidget()
        central_layout = QHBoxLayout(central_widget_container)
        central_layout.setContentsMargins(0, 0, 0, 0) # Remove margins

        # Create the PromptManager widget
        self.prompt_manager = PromptManager()
        central_layout.addWidget(self.prompt_manager)

        # Set the central widget container as the central widget
        self.setCentralWidget(central_widget_container)

        # Create the right panel (QDockWidget)
        self.right_dock = QDockWidget(self.tr("Prompt Editor"), self)
        self.right_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        self.right_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.right_dock.setVisible(True) # Set to visible by default
        self.right_dock.setMinimumWidth(800) # Double the minimum width for the dock widget

        # Create a placeholder widget for the dock content
        # This will be replaced by PromptDialog content later
        prompt_editor_panel_content = QWidget()
        prompt_editor_panel_content.setLayout(QVBoxLayout()) # Use a layout for future content
        self.right_dock.setWidget(prompt_editor_panel_content)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.right_dock)

        # Pass the dock widget and its content widget to PromptManager
        self.prompt_manager.set_editor_panel(self.right_dock, prompt_editor_panel_content)

        # Create the menu bar
        menubar = self.menuBar()
        
        # Create PromptVault menu (first position)
        self.promptvault_menu = menubar.addMenu(self.tr('PromptVault'))

        # About PromptVault action
        self.about_action = QAction(self.tr('About PromptVault'), self)
        self.about_action.triggered.connect(self.show_about_dialog)
        self.about_action.setMenuRole(QAction.MenuRole.NoRole) # Prevent macOS from moving it to the application menu
        self.promptvault_menu.addAction(self.about_action)

        # Codeberg repository action
        self.codeberg_action = QAction(self.tr('Codeberg repository'), self)
        self.codeberg_action.triggered.connect(self.open_codeberg_repo)
        self.promptvault_menu.addAction(self.codeberg_action)

        # Create the File menu
        self.file_menu = menubar.addMenu(self.tr('File'))

        # Create Import action
        self.import_action = QAction(self.tr('Import'), self)
        self.import_action.triggered.connect(self.prompt_manager.import_prompts)
        self.file_menu.addAction(self.import_action)

        # Create Export action
        self.export_action = QAction(self.tr('Export'), self)
        self.export_action.triggered.connect(self.prompt_manager.export_prompts)
        self.file_menu.addAction(self.export_action)

        # Create the View menu for themes
        self.view_menu = menubar.addMenu(self.tr('View'))

        # Create Light Theme action
        self.light_theme_action = QAction(self.tr('Light Theme'), self)
        self.light_theme_action.triggered.connect(self.theme_manager.set_light_theme)
        self.view_menu.addAction(self.light_theme_action)

        # Create Dark Theme action
        self.dark_theme_action = QAction(self.tr('Dark Theme'), self)
        self.dark_theme_action.triggered.connect(self.theme_manager.set_dark_theme)
        self.view_menu.addAction(self.dark_theme_action)

        # Add separator
        self.view_menu.addSeparator()

        # Create Toggle Prompt Editor Panel action
        self.toggle_editor_panel_action = QAction(self.tr('Toggle Prompt Editor Panel'), self)
        self.toggle_editor_panel_action.setCheckable(True)
        self.toggle_editor_panel_action.setChecked(self.right_dock.isVisible())
        self.toggle_editor_panel_action.triggered.connect(self.right_dock.setVisible)
        self.right_dock.visibilityChanged.connect(self.toggle_editor_panel_action.setChecked) # Keep menu item in sync
        self.view_menu.addAction(self.toggle_editor_panel_action)

        # Create Toggle Fullscreen action
        self.fullscreen_action = QAction(self.tr('Toggle Fullscreen'), self)
        self.fullscreen_action.setCheckable(True)
        self.fullscreen_action.triggered.connect(lambda: self.toggle_fullscreen(self.fullscreen_action))
        self.view_menu.addAction(self.fullscreen_action)

        # Add language submenu
        self.view_menu.addSeparator()
        self.language_menu = self.view_menu.addMenu(self.tr('Language'))

        # Add language change messages
        self.language_changed_title = self.tr("Language Changed")
        self.language_changed_message = self.tr("Language has been changed. Some elements may require a restart to display correctly.")
        self.translation_error_title = self.tr("Translation Error")
        self.translation_error_message = self.tr("Could not load translation for the selected language.")

        # English
        self.english_action = QAction('English', self)
        self.english_action.triggered.connect(lambda: self.change_language('en'))
        self.language_menu.addAction(self.english_action)

        # French
        self.french_action = QAction('Français', self)
        self.french_action.triggered.connect(lambda: self.change_language('fr'))
        self.language_menu.addAction(self.french_action)

        # Spanish
        self.spanish_action = QAction('Español', self)
        self.spanish_action.triggered.connect(lambda: self.change_language('es'))
        self.language_menu.addAction(self.spanish_action)

        # German
        self.german_action = QAction('Deutsch', self)
        self.german_action.triggered.connect(lambda: self.change_language('de'))
        self.language_menu.addAction(self.german_action)
    
    def toggle_fullscreen(self, action):
        if self.isFullScreen():
            self.showNormal()
            action.setChecked(False)
        else:
            self.showFullScreen()
            action.setChecked(True)

    def show_about_dialog(self):
        dialog = AboutDialog(self)
        dialog.exec()

    def open_codeberg_repo(self):
        url = QUrl("https://codeberg.org/medenor/promptvault")
        QDesktopServices.openUrl(url)

    def change_language(self, language_code):
        """Change the application language at runtime"""
        global translator
        if 'translator' not in globals():
            translator = QTranslator()

        # Remove current translator
        QApplication.instance().removeTranslator(translator)

        # Load new translation
        translation_file = os.path.join(os.path.dirname(__file__), '..', 'i18n', f'promptvault_{language_code}.qm')
        if translator.load(translation_file):
            QApplication.instance().installTranslator(translator)

            # Save language preference
            settings = QSettings('PromptVault', 'PromptVault')
            settings.setValue('language', language_code)

            # Retranslate the UI
            self.retranslateUi()

            # Show message about restart recommendation
            QMessageBox.information(self, self.tr("Language Changed"),
                                  self.tr("Language has been changed. Some elements may require a restart to display correctly."))
        else:
            QMessageBox.warning(self, self.tr("Translation Error"),
                              self.tr("Could not load translation for the selected language."))

    def retranslateUi(self):
        """Retranslate all UI elements after language change"""
        self.setWindowTitle(self.tr('Prompt Manager'))
        self.right_dock.setWindowTitle(self.tr("Prompt Editor"))

        # Update menu titles
        self.promptvault_menu.setTitle(self.tr('PromptVault'))
        self.file_menu.setTitle(self.tr('File'))
        self.view_menu.setTitle(self.tr('View'))
        self.language_menu.setTitle(self.tr('Language'))

        # Update menu actions
        self.about_action.setText(self.tr('About PromptVault'))
        self.codeberg_action.setText(self.tr('Codeberg repository'))
        self.import_action.setText(self.tr('Import'))
        self.export_action.setText(self.tr('Export'))
        self.light_theme_action.setText(self.tr('Light Theme'))
        self.dark_theme_action.setText(self.tr('Dark Theme'))
        self.toggle_editor_panel_action.setText(self.tr('Toggle Prompt Editor Panel'))
        self.fullscreen_action.setText(self.tr('Toggle Fullscreen'))

        # Update language change messages
        self.language_changed_title = self.tr("Language Changed")
        self.language_changed_message = self.tr("Language has been changed. Some elements may require a restart to display correctly.")
        self.translation_error_title = self.tr("Translation Error")
        self.translation_error_message = self.tr("Could not load translation for the selected language.")

if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Load translations - check saved preference first, then system locale
    translator = QTranslator()
    settings = QSettings('PromptVault', 'PromptVault')
    saved_language = settings.value('language', None)

    translation_loaded = False

    if saved_language:
        # Try to load saved language preference
        translation_file = os.path.join(os.path.dirname(__file__), '..', 'i18n', f'promptvault_{saved_language}.qm')
        if translator.load(translation_file):
            app.installTranslator(translator)
            translation_loaded = True

    if not translation_loaded:
        # Fallback to system locale
        locale = QLocale.system().name()
        translation_file = os.path.join(os.path.dirname(__file__), '..', 'i18n', f'promptvault_{locale}.qm')

        if translator.load(translation_file):
            app.installTranslator(translator)
        else:
            # Try loading just the language part (e.g., 'fr' instead of 'fr_FR')
            language = locale.split('_')[0]
            translation_file = os.path.join(os.path.dirname(__file__), '..', 'i18n', f'promptvault_{language}.qm')
            if translator.load(translation_file):
                app.installTranslator(translator)

    main_window = MainWindow()
    # Show the main window maximized
    main_window.showMaximized()
    sys.exit(app.exec())
