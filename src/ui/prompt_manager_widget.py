import json
import os
from collections import defaultdict
import csv
import uuid # Added for UUID generation
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
                             QPushButton, QMessageBox, QLabel, QListWidget,
                             QListWidgetItem, QApplication, QAbstractItemView,
                             QToolTip, QDialog, QCheckBox, QSizePolicy,
                             QSpacerItem, QFrame, QMenu, QFileDialog, QStackedWidget, QSplitter) # Added QStackedWidget, QSplitter
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction
from PyQt6.QtCore import Qt, QSize, pyqtSignal # Added pyqtSignal

from .prompt_dialog import PromptDialog
from .category_dialog import CategoryDialog
from .tag_dialog import TagDialog
from .version_history_dialog import VersionHistoryDialog # Import the new dialog

from ..services.prompt_data_service import PromptDataService
from ..services.prompt_filter_service import PromptFilterService
from ..services.prompt_versioning_service import PromptVersioningService
from ..services.prompt_import_export_service import PromptImportExportService
from ..services.backup_service import BackupService

class PromptManager(QWidget):
    # Define a signal to request the main window to show/hide the editor panel
    def __init__(self, data_file_path: str = None):
        super().__init__()

        # Initialize services
        self.data_service = PromptDataService(data_file_path)
        self.filter_service = PromptFilterService()
        self.versioning_service = PromptVersioningService()
        self.import_export_service = PromptImportExportService()
        self.backup_service = BackupService()

        # Load data using the data service
        self.data_service.load_prompts()
        
        # Expose data service properties for backward compatibility
        self.prompts = self.data_service.prompts
        self.next_id = self.data_service.next_id
        self.categories = self.data_service.categories
        self.global_tags = self.data_service.global_tags
        
        self.current_editor_instance = None # To keep track of the active PromptDialog instance
        self.prompt_editor_widget = None # Reference to the prompt editor widget

        self.initUI()
        self.update_category_list()
        self.update_tag_list()
        self.update_prompt_list()

    def initUI(self):
        self.setGeometry(200, 200, 950, 600)
        self.setWindowTitle(self.tr('Prompt Manager'))

        # Create the main splitter
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Create widget to hold the left panel layout
        left_panel_widget = QWidget()
        left_layout = self._init_left_panel()
        left_panel_widget.setLayout(left_layout)

        # The right panel is now a QSplitter directly
        right_splitter_widget = self._init_right_panel()

        # Add widgets to the main splitter
        self.main_splitter.addWidget(left_panel_widget)
        self.main_splitter.addWidget(right_splitter_widget)

        # Set initial sizes (e.g., 1 for left, 4 for right)
        self.main_splitter.setSizes([self.width() // 4, self.width() * 3 // 4])

        main_layout = QVBoxLayout(self) # Changed to QVBoxLayout for the main widget
        main_layout.addWidget(self.main_splitter)

    def _init_left_panel(self):
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0) # Remove margins

        left_layout.addWidget(QLabel(self.tr("Categories")))

        self.manageCategoriesButton = QPushButton(self.tr('Manage Categories'))
        self.manageCategoriesButton.setToolTip(self.tr("Manage prompt categories"))
        self.manageCategoriesButton.clicked.connect(self.manageCategories)
        left_layout.addWidget(self.manageCategoriesButton)

        self.categoryList = QListWidget()
        self.categoryList.itemClicked.connect(self.filter_prompts_by_category)
        left_layout.addWidget(self.categoryList)

        left_layout.addWidget(QLabel(self.tr("Tags")))

        self.manageTagsButton = QPushButton(self.tr('Manage Tags'))
        self.manageTagsButton.setToolTip(self.tr("Manage tags globally"))
        self.manageTagsButton.clicked.connect(self.manageTags)
        left_layout.addWidget(self.manageTagsButton)

        self.tagList = QListWidget()
        self.tagList.itemClicked.connect(self.filter_prompts_by_tag)
        left_layout.addWidget(self.tagList)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        left_layout.addWidget(line)

        left_layout.addWidget(QLabel(self.tr("Filters")))

        self.showFavoritesButton = QPushButton(self.tr("⭐ Show Favorites"))
        self.showFavoritesButton.setCheckable(True)
        self.showFavoritesButton.setToolTip(self.tr("Show only prompts marked as favorites"))
        self.showFavoritesButton.clicked.connect(self.toggle_favorites_filter)
        left_layout.addWidget(self.showFavoritesButton)

        self.showAllButton = QPushButton(self.tr("🔄 Show All"))
        self.showAllButton.clicked.connect(self.show_all_prompts)
        left_layout.addWidget(self.showAllButton)

        left_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        return left_layout

    def _init_right_panel(self):
        # Create a splitter for the right side (prompt list and editor)
        self.right_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Widget for the prompt list
        prompt_list_widget = QWidget()
        prompt_list_layout = QVBoxLayout(prompt_list_widget)
        prompt_list_layout.setContentsMargins(0, 0, 0, 0) # Remove margins

        search_layout = QHBoxLayout()
        self.searchBar = QLineEdit()
        self.searchBar.setPlaceholderText(self.tr("Search in title, prompt, note..."))
        self.searchBar.textChanged.connect(self.filter_prompts_by_search)
        search_layout.addWidget(self.searchBar, 1)

        self.caseSensitiveCheckbox = QCheckBox(self.tr("Case Sensitive"))
        self.caseSensitiveCheckbox.setToolTip(self.tr("Enable case-sensitive search"))
        self.caseSensitiveCheckbox.stateChanged.connect(self.filter_prompts_by_search)
        search_layout.addWidget(self.caseSensitiveCheckbox, 0)

        prompt_list_layout.addLayout(search_layout)

        self.promptList = QListWidget()
        self.promptList.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.promptList.itemDoubleClicked.connect(self.editPrompt)
        self.promptList.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.promptList.customContextMenuRequested.connect(self.show_context_menu)
        prompt_list_layout.addWidget(self.promptList)


        button_layout = QHBoxLayout()
        self.addButton = QPushButton(self.tr('Add'))
        self.addButton.setToolTip(self.tr("Add a new prompt"))
        self.addButton.clicked.connect(self.addPrompt)
        button_layout.addWidget(self.addButton)

        self.editButton = QPushButton(self.tr('Edit'))
        self.editButton.setToolTip(self.tr("Edit selected prompt"))
        self.editButton.clicked.connect(self.editPrompt)
        button_layout.addWidget(self.editButton)

        self.deleteButton = QPushButton(self.tr('Delete'))
        self.deleteButton.setToolTip(self.tr("Delete selected prompt(s)"))
        self.deleteButton.clicked.connect(self.deleteSelectedPrompts)
        button_layout.addWidget(self.deleteButton)


        prompt_list_layout.addLayout(button_layout)

        # Widget for the prompt editor
        self.prompt_editor_widget = QWidget()
        self.prompt_editor_widget.setLayout(QVBoxLayout()) # Use a layout for future content
        self.prompt_editor_widget.layout().setContentsMargins(0, 0, 0, 0) # Remove margins
        self.prompt_editor_widget.setMinimumWidth(300) # Set a minimum width for the editor

        # Add widgets to the right splitter
        self.right_splitter.addWidget(prompt_list_widget)
        self.right_splitter.addWidget(self.prompt_editor_widget)

        # Set initial sizes for the right splitter
        self.right_splitter.setSizes([self.width() // 2, self.width() // 2])

        return self.right_splitter # Return the splitter, not a layout

    def clear_editor_panel(self):
        if self.prompt_editor_widget and self.prompt_editor_widget.layout():
            # Remove all widgets from the layout
            while self.prompt_editor_widget.layout().count():
                child = self.prompt_editor_widget.layout().takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            self.current_editor_instance = None # Clear reference to old editor

    def show_editor_panel(self, show=True):
        if self.prompt_editor_widget:
            self.prompt_editor_widget.setVisible(show)

    def update_category_list(self):
        self.categoryList.clear()
        categories_in_use = set(p['data'].get('category', 'No category') for p in self.prompts.values())
        all_display_categories = categories_in_use.union(set(self.categories))

        sorted_display_categories = sorted(list(all_display_categories))
        self.categoryList.addItems(sorted_display_categories)


    def update_tag_list(self):
        self.tagList.clear()
        all_tags_from_prompts = set()
        for prompt_info in self.prompts.values():
            all_tags_from_prompts.update(prompt_info['data'].get('tags', []))
        
        # Combine tags from prompts and globally managed tags
        all_display_tags = all_tags_from_prompts.union(self.global_tags)

        for tag in sorted(list(all_display_tags)):
            self.tagList.addItem(tag)

    def update_prompt_list(self, filter_category=None, filter_tag=None, search_term="", filter_favorites=False):
        self.promptList.clear()
        case_sensitive = self.caseSensitiveCheckbox.isChecked()
        
        # Use the filter service to filter prompts
        filtered_prompts = self.filter_service.filter_prompts(
            self.prompts, filter_category, filter_tag, search_term, filter_favorites, case_sensitive)
        
        # Use the filter service to sort prompts
        sorted_prompts = self.filter_service.sort_prompts(filtered_prompts)

        for prompt_data in sorted_prompts:
            prompt_id = prompt_data['id']
            title = prompt_data.get('title', 'Untitled')
            is_favorite = prompt_data.get('favorite', False)

            list_item, item_widget = self._create_prompt_list_item(prompt_id, title, is_favorite)
            self.promptList.addItem(list_item)
            self.promptList.setItemWidget(list_item, item_widget)

    def _filter_prompts(self, filter_category, filter_tag, search_term, filter_favorites):
        case_sensitive = self.caseSensitiveCheckbox.isChecked()
        processed_search_term = search_term if case_sensitive else search_term.lower()
        
        filtered_prompts = []
        for prompt_id, prompt_info in self.prompts.items():
            data = prompt_info['data']
            category = data.get('category') if data.get('category') else 'No category'
            tags = data.get('tags', [])
            is_favorite = data.get('favorite', False)

            title_text = data.get('title', '')
            prompt_text = data.get('prompt', '')
            note_text = data.get('note', '')

            processed_title = title_text if case_sensitive else title_text.lower()
            processed_prompt = prompt_text if case_sensitive else prompt_text.lower()
            processed_note = note_text if case_sensitive else note_text.lower()

            category_match = filter_category is None or category == filter_category
            tag_match = filter_tag is None or filter_tag in tags
            search_match = (
                processed_search_term == "" or
                processed_search_term in processed_title or
                processed_search_term in processed_prompt or
                processed_search_term in processed_note
            )
            favorite_match = (not filter_favorites) or is_favorite
            
            if category_match and tag_match and search_match and favorite_match:
                filtered_prompts.append({'id': prompt_id, **data})
        return filtered_prompts

    def _create_prompt_list_item(self, prompt_id, title, is_favorite):
        item_widget = QWidget()
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(2, 5, 2, 5)
        item_layout.setSpacing(5)

        if is_favorite:
            fav_label = QLabel("⭐")
            item_layout.addWidget(fav_label, 0)

        title_label = QLabel(title)
        item_layout.addWidget(title_label, 1)

        copy_button = QPushButton()
        copy_button.setObjectName("copyPromptButton") # Add objectName for QSS targeting
        copy_button.setFixedSize(QSize(24, 24))
        copy_button.setToolTip(self.tr("Copy prompt '{0}'").format(title))
        copy_button.setStyleSheet("""
            QPushButton { border: none; background-color: transparent; padding: 0px; }
            QPushButton:hover { background-color: rgba(128, 128, 128, 50); }
            QPushButton:pressed { background-color: rgba(128, 128, 128, 100); }
        """)
        copy_button.setProperty("prompt_id", prompt_id)
        copy_button.clicked.connect(self.copy_prompt_text_from_button)
        copy_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        item_layout.addWidget(copy_button, 0)

        item_widget.setLayout(item_layout)

        list_item = QListWidgetItem(self.promptList)
        list_item.setSizeHint(item_widget.sizeHint())
        list_item.setData(Qt.ItemDataRole.UserRole, prompt_id)
        return list_item, item_widget

    def copy_prompt_text_from_button(self):
        sender_button = self.sender()
        if sender_button:
            prompt_id = sender_button.property("prompt_id")
            if prompt_id is not None and prompt_id in self.prompts:
                prompt_text = self.prompts[prompt_id]['data'].get('prompt', '')
                clipboard = QApplication.clipboard()
                clipboard.setText(prompt_text)
                QToolTip.showText(sender_button.mapToGlobal(sender_button.rect().bottomLeft()),
                                  self.tr("Prompt copied!"), widget=sender_button, msecShowTime=1500)
                print(f"Prompt ID {prompt_id} copied via integrated button.")
            else:
                print(f"Error: Could not find prompt ID {prompt_id} from button.")

    def get_selected_prompt_id(self):
        selected_items = self.promptList.selectedItems()
        if selected_items:
            return selected_items[0].data(Qt.ItemDataRole.UserRole)
        return None

    def get_selected_prompt_ids(self):
        selected_ids = []
        selected_items = self.promptList.selectedItems()
        for item in selected_items:
            prompt_id = item.data(Qt.ItemDataRole.UserRole)
            if prompt_id is not None:
                selected_ids.append(prompt_id)
        return selected_ids

    def filter_prompts_by_category(self, item):
        category = item.text()
        current_tag = self.current_filter_tag()
        current_search = self.searchBar.text()
        favorites_only = self.is_favorites_filter_active()
        print(f"Filtering by Category: {category}, Tag: {current_tag}, Search: {current_search}, Favorites: {favorites_only}")
        self.update_prompt_list(filter_category=category, filter_tag=current_tag, search_term=current_search, filter_favorites=favorites_only)

    def filter_prompts_by_tag(self, item):
        tag = item.text()
        current_category = self.current_filter_category()
        current_search = self.searchBar.text()
        favorites_only = self.is_favorites_filter_active()
        print(f"Filtering by Tag: {tag}, Category: {current_category}, Search: {current_search}, Favorites: {favorites_only}")
        self.update_prompt_list(filter_category=current_category, filter_tag=tag, search_term=current_search, filter_favorites=favorites_only)

    def filter_prompts_by_search(self, text=None):
        search_term = self.searchBar.text()
        current_category = self.current_filter_category()
        current_tag = self.current_filter_tag()
        case_sensitive = self.caseSensitiveCheckbox.isChecked()
        favorites_only = self.is_favorites_filter_active()
        print(f"Filtering by Search: '{search_term}', Category: {current_category}, Tag: {current_tag}, Case Sensitive: {case_sensitive}, Favorites: {favorites_only}")
        self.update_prompt_list(filter_category=current_category, filter_tag=current_tag, search_term=search_term, filter_favorites=favorites_only)

    def toggle_favorites_filter(self):
        favorites_only = self.is_favorites_filter_active()
        current_category = self.current_filter_category()
        current_tag = self.current_filter_tag()
        current_search = self.searchBar.text()
        print(f"Toggling Favorites Filter: {'Activated' if favorites_only else 'Deactivated'}")
        self.update_prompt_list(filter_category=current_category, filter_tag=current_tag, search_term=current_search, filter_favorites=favorites_only)

    def show_all_prompts(self):
        self.categoryList.clearSelection()
        self.tagList.clearSelection()
        self.searchBar.clear()
        self.showFavoritesButton.setChecked(False)
        print("Displaying all prompts (filters reset)")
        self.update_prompt_list()

    def is_favorites_filter_active(self):
        return self.showFavoritesButton.isChecked()

    def current_filter_category(self):
        selected_items = self.categoryList.selectedItems()
        return selected_items[0].text() if selected_items else None

    def current_filter_tag(self):
        selected_items = self.tagList.selectedItems()
        return selected_items[0].text() if selected_items else None

    def addPrompt(self):
        selected_category_items = self.categoryList.selectedItems()
        default_category = 'No category'
        if selected_category_items:
            default_category = selected_category_items[0].text()
        elif self.categories:
            default_category = self.categories[0]

        initial_data = {'category': default_category, 'favorite': False}
        all_available_tags = sorted(list(self.global_tags.union(self._get_all_tags_from_prompts())))

        self.clear_editor_panel() # Clear any previous content

        # Create a new PromptDialog instance, but don't show it as a dialog
        # For a new prompt, there are no existing versions, so pass an empty list
        self.current_editor_instance = PromptDialog(self, data=initial_data, versions=[], categories=self.categories, all_tags=all_available_tags, is_panel=True)
        
        # Add the dialog's layout to the editor panel widget
        self.prompt_editor_widget.layout().addWidget(self.current_editor_instance)
        
        # Connect signals for saving and canceling
        self.current_editor_instance.accepted.connect(self._save_prompt_from_panel)
        self.current_editor_instance.rejected.connect(self._cancel_prompt_edit_from_panel)

        self.show_editor_panel(True) # Show the editor panel
        # No dock widget title to set anymore
        print("Opened Add Prompt panel.")

    def editPrompt(self):
        prompt_id = self.get_selected_prompt_id()

        if prompt_id is None:
             selected_ids = self.get_selected_prompt_ids()
             if not selected_ids:
                 QMessageBox.warning(self, self.tr("No Selection"), self.tr("Please select a prompt to edit."))
                 return
             if len(selected_ids) > 1:
                 QMessageBox.warning(self, self.tr("Multiple Selection"), self.tr("Please select only one prompt to edit."))
                 return
             prompt_id = selected_ids[0]


        if prompt_id not in self.prompts:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Could not find prompt with ID {0}.").format(prompt_id))
            return

        # Use the data service to get prompt data
        current_data = self.data_service.get_prompt_data(prompt_id)
        # Use the data service to get prompt versions
        versions = self.data_service.get_prompt_versions(prompt_id)
        all_available_tags = sorted(list(self.global_tags.union(self._get_all_tags_from_prompts())))

        self.clear_editor_panel() # Clear any previous content

        # Create a new PromptDialog instance, passing versions for history display
        self.current_editor_instance = PromptDialog(self, data=current_data, versions=versions, categories=self.categories, all_tags=all_available_tags, is_panel=True)
        self.current_editor_instance.setProperty("editing_prompt_id", prompt_id) # Store the ID being edited
        
        # Add the dialog's layout to the editor panel widget
        self.prompt_editor_widget.layout().addWidget(self.current_editor_instance)
        
        # Connect signals for saving and canceling
        self.current_editor_instance.accepted.connect(self._save_prompt_from_panel)
        self.current_editor_instance.rejected.connect(self._cancel_prompt_edit_from_panel)

        self.show_editor_panel(True) # Show the editor panel
        # No dock widget title to set anymore
        print(f"Opened Edit Prompt panel for ID {prompt_id}.")

    def deleteSelectedPrompts(self):
        selected_ids = self.get_selected_prompt_ids()

        if not selected_ids:
            QMessageBox.warning(self, self.tr("No Selection"), self.tr("Please select at least one prompt to delete."))
            return

        prompts_to_delete_titles = [self.prompts[pid]['data'].get('title', 'Untitled') for pid in selected_ids if pid in self.prompts]

        count = len(selected_ids)
        if count == 1:
            message = self.tr("Are you sure you want to delete the prompt '{0}'?").format(prompts_to_delete_titles[0])
        else:
            message = self.tr("Are you sure you want to delete the {0} selected prompts?").format(count)

        msgBox = QMessageBox(self)
        msgBox.setWindowTitle(self.tr('Deletion Confirmation'))
        msgBox.setText(message)
        msgBox.setIcon(QMessageBox.Icon.Question)
        yesButton = msgBox.addButton(self.tr("Yes"), QMessageBox.ButtonRole.YesRole)
        noButton = msgBox.addButton(self.tr("No"), QMessageBox.ButtonRole.NoRole)
        msgBox.setDefaultButton(noButton)

        reply = msgBox.exec()

        if msgBox.clickedButton() == yesButton:
            # Create pre-delete backup for bulk operations
            if count > 1:
                print("Creating pre-bulk-delete backup...")
                pre_delete_backup = self.backup_service.create_backup("pre_bulk_delete")
                if not pre_delete_backup:
                    print("Warning: Could not create pre-bulk-delete backup")

            deleted_count = 0
            for prompt_id in selected_ids:
                # Use the data service to delete the prompt
                if self.data_service.delete_prompt(prompt_id):
                    deleted_count += 1
                    print(f"Prompt ID {prompt_id} deleted.")

            if deleted_count > 0:
                # Update local prompts reference
                self.prompts = self.data_service.prompts
                print(f"{deleted_count} prompt(s) deleted.")
                self.update_category_list()
                self.update_tag_list()
                self.update_prompt_list(filter_category=self.current_filter_category(),
                                        filter_tag=self.current_filter_tag(),
                                        search_term=self.searchBar.text(),
                                        filter_favorites=self.is_favorites_filter_active())
                self.save_prompts()

    def current_filter_category(self):
        selected_items = self.categoryList.selectedItems()
        return selected_items[0].text() if selected_items else None

    def current_filter_tag(self):
        selected_items = self.tagList.selectedItems()
        return selected_items[0].text() if selected_items else None

    def save_prompts(self):
        # Update data service properties before saving
        self.data_service.prompts = self.prompts
        self.data_service.next_id = self.next_id
        self.data_service.categories = self.categories
        self.data_service.global_tags = self.global_tags
        
        if not self.data_service.save_prompts():
            QMessageBox.critical(self, self.tr("Save Error"), self.tr("Could not save prompts."))


    def load_prompts(self):
        # Load data using the data service
        if self.data_service.load_prompts():
            # Update local properties from data service
            self.prompts = self.data_service.prompts
            self.next_id = self.data_service.next_id
            self.categories = self.data_service.categories
            self.global_tags = self.data_service.global_tags
        else:
            QMessageBox.critical(self, self.tr("Load Error"), self.tr("Could not load prompts."))

    def _migrate_old_data_structure(self, prompt_id, prompt_info):
        # Migration logic for old data structure
        if 'data' in prompt_info and 'history' in prompt_info and 'versions' not in prompt_info:
            print(f"Migrating old prompt structure for ID {prompt_id}")
            current_data = prompt_info['data']
            history_entries = prompt_info['history']

            versions = []
            # Create initial version from the first history entry or current data
            if history_entries:
                first_data = history_entries[0]
                first_version_id = self._generate_version_id(first_data, "Initial import")
                versions.append({
                    'version_id': first_version_id,
                    'timestamp': self._get_current_timestamp(),
                    'author': self._get_current_user(),
                    'message': "Initial import",
                    'data': first_data,
                    'parents': []
                })
                # Add subsequent history entries as new versions
                for i in range(1, len(history_entries)):
                    prev_version_id = versions[-1]['version_id']
                    new_data = history_entries[i]
                    new_version_id = self._generate_version_id(new_data, "History migration")
                    versions.append({
                        'version_id': new_version_id,
                        'timestamp': self._get_current_timestamp(), # Use current time for migration
                        'author': self._get_current_user(),
                        'message': "History migration",
                        'data': new_data,
                        'parents': [prev_version_id]
                    })
            else: # No history, just current data
                initial_version_id = self._generate_version_id(current_data, "Initial import")
                versions.append({
                    'version_id': initial_version_id,
                    'timestamp': self._get_current_timestamp(),
                    'author': self._get_current_user(),
                    'message': "Initial import",
                    'data': current_data,
                    'parents': []
                })
            
            # Ensure current_data is the latest in versions
            if versions and versions[-1]['data'] != current_data:
                latest_version_id = self._generate_version_id(current_data, "Current state after migration")
                versions.append({
                    'version_id': latest_version_id,
                    'timestamp': self._get_current_timestamp(),
                    'author': self._get_current_user(),
                    'message': "Current state after migration",
                    'data': current_data,
                    'parents': [versions[-1]['version_id']] if versions else []
                })

            prompt_info = {
                'data': current_data,
                'versions': versions,
                'branches': {"main": versions[-1]['version_id']} if versions else {}
            }
        
        # Ensure new fields exist for all prompts
        if 'versions' not in prompt_info:
            prompt_info['versions'] = []
        if 'branches' not in prompt_info:
            prompt_info['branches'] = {}
        if 'data' not in prompt_info: # Should not happen with current structure, but for safety
            prompt_info['data'] = {}

        # Ensure category and favorite defaults
        if 'category' not in prompt_info['data'] or not prompt_info['data']['category']:
            prompt_info['data']['category'] = 'No category'
        if 'favorite' not in prompt_info['data']:
            prompt_info['data']['favorite'] = False
        
        return prompt_info

    def show_context_menu(self, position):
        menu = QMenu()

        edit_action = menu.addAction(self.tr("Edit"))
        delete_action = menu.addAction(self.tr("Delete"))
        copy_prompt_action = menu.addAction(self.tr("Copy Prompt"))
        export_action = menu.addAction(self.tr("Export"))
        toggle_favorite_action = menu.addAction(self.tr("Add to Favorites") if not self.is_selected_prompt_favorite() else self.tr("Remove from Favorites"))
        view_history_action = menu.addAction(self.tr("View Version History")) # New action

        edit_action.triggered.connect(self.editPrompt)
        delete_action.triggered.connect(self.deleteSelectedPrompts)
        copy_prompt_action.triggered.connect(self.copy_selected_prompt_text)
        export_action.triggered.connect(self.export_selected_prompts)
        toggle_favorite_action.triggered.connect(self.toggle_selected_prompt_favorite)
        view_history_action.triggered.connect(self.view_prompt_history) # Connect new action

        selected_items = self.promptList.selectedItems()
        num_selected = len(selected_items)

        edit_action.setEnabled(num_selected == 1)
        copy_prompt_action.setEnabled(num_selected == 1)
        export_action.setEnabled(num_selected > 0)
        toggle_favorite_action.setEnabled(num_selected >= 1)
        delete_action.setEnabled(num_selected >= 1)

        menu.exec(self.promptList.mapToGlobal(position))

    def copy_selected_prompt_text(self):
        prompt_id = self.get_selected_prompt_id()
        if prompt_id is not None and prompt_id in self.prompts:
            prompt_text = self.prompts[prompt_id]['data'].get('prompt', '')
            clipboard = QApplication.clipboard()
            clipboard.setText(prompt_text)
            QToolTip.showText(self.promptList.mapToGlobal(self.promptList.viewport().rect().center()),
                              self.tr("Prompt copied!"), msecShowTime=1500)
            print(f"Prompt ID {prompt_id} copied via context menu.")
        else:
            QMessageBox.warning(self, self.tr("Copy Failed"), self.tr("Please select a prompt to copy."))

    def view_prompt_history(self):
        prompt_id = self.get_selected_prompt_id()
        if prompt_id is None:
            QMessageBox.warning(self, self.tr("No Selection"), self.tr("Please select a prompt to view its version history."))
            return

        if prompt_id not in self.prompts:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Could not find prompt with ID {0}.").format(prompt_id))
            return

        # Use the data service to get prompt data and versions
        prompt_data = self.data_service.get_prompt_data(prompt_id)
        versions = self.data_service.get_prompt_versions(prompt_id)

        prompt_title = prompt_data.get('title', 'Untitled')

        if not versions:
            QMessageBox.information(self, self.tr("No History"), self.tr("This prompt has no version history yet."))
            return

        dialog = VersionHistoryDialog(self, prompt_id=prompt_id, prompt_title=prompt_title, versions=versions)
        dialog.revertVersion.connect(self._handle_revert_version)
        dialog.exec()
        print(f"Viewed version history for prompt ID {prompt_id}.")

    def _handle_revert_version(self, prompt_id, reverted_data, commit_message):
        if prompt_id not in self.prompts:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Could not find prompt with ID {0} to revert.").format(prompt_id))
            return

        # Use the data service to revert the prompt to a specific version
        if self.data_service.revert_prompt_to_version(prompt_id, reverted_data, commit_message):
            # Update local prompts reference
            self.prompts = self.data_service.prompts
            print(f"Prompt ID {prompt_id} reverted with message: {commit_message}.")
        else:
            print(f"Failed to revert prompt ID {prompt_id}.")
            return

        self.update_category_list()
        self.update_tag_list()
        self.update_prompt_list(filter_category=self.current_filter_category(),
                                filter_tag=self.current_filter_tag(),
                                search_term=self.searchBar.text(),
                                filter_favorites=self.is_favorites_filter_active())
        self.save_prompts()
        QMessageBox.information(self, self.tr("Revert Successful"), self.tr("Prompt '{0}' successfully reverted.").format(reverted_data.get('title', 'Untitled')))


    def is_selected_prompt_favorite(self):
        selected_ids = self.get_selected_prompt_ids()
        if not selected_ids:
            return False
        return all(self.prompts[pid]['data'].get('favorite', False) for pid in selected_ids if pid in self.prompts)

    def toggle_selected_prompt_favorite(self):
        selected_ids = self.get_selected_prompt_ids()
        if not selected_ids:
            QMessageBox.warning(self, self.tr("No Selection"), self.tr("Please select at least one prompt to change its favorite status."))
            return

        current_state_all_favorite = self.is_selected_prompt_favorite()
        new_favorite_state = not current_state_all_favorite

        # Create pre-bulk-update backup for multiple prompts
        if len(selected_ids) > 1:
            print("Creating pre-bulk-favorite-update backup...")
            pre_update_backup = self.backup_service.create_backup("pre_bulk_favorite_update")
            if not pre_update_backup:
                print("Warning: Could not create pre-bulk-favorite-update backup")

        prompts_changed = False
        for prompt_id in selected_ids:
            if prompt_id in self.prompts:
                current_favorite = self.prompts[prompt_id]['data'].get('favorite', False)
                if current_favorite != new_favorite_state:
                    # Update the prompt data using the data service
                    prompt_data = self.data_service.get_prompt_data(prompt_id)
                    prompt_data['favorite'] = new_favorite_state

                    # Create a new version with the updated favorite status
                    commit_message = f"Toggle favorite status to {new_favorite_state}"
                    if self.data_service.update_prompt(prompt_id, prompt_data, commit_message):
                        # Update local prompts reference
                        self.prompts = self.data_service.prompts
                        prompts_changed = True
                        print(f"Prompt ID {prompt_id} favorite toggled to {new_favorite_state}.")
                    else:
                        print(f"Failed to toggle favorite status for prompt ID {prompt_id}.")

        if prompts_changed:
            self.update_prompt_list(filter_category=self.current_filter_category(),
                                    filter_tag=self.current_filter_tag(),
                                    search_term=self.searchBar.text(),
                                    filter_favorites=self.is_favorites_filter_active())
            self.save_prompts()
            QToolTip.showText(self.promptList.mapToGlobal(self.promptList.viewport().rect().center()),
                              self.tr("Favorite status updated for {0} prompt(s)!").format(len(selected_ids)), msecShowTime=1500)
        else:
            print("No favorite status change necessary.")

    def export_selected_prompts(self):
        selected_ids = self.get_selected_prompt_ids()
        if not selected_ids:
            QMessageBox.warning(self, self.tr("No Selection"), self.tr("Please select at least one prompt to export."))
            return

        file_name, _ = QFileDialog.getSaveFileName(self, self.tr("Export Selected Prompts"), "",
                                                  self.tr("CSV Files (*.csv);;Markdown Files (*.md);;All Files (*)"))
        if file_name:
            try:
                if file_name.lower().endswith('.csv'):
                    self._export_to_csv(file_name, selected_ids)
                elif file_name.lower().endswith('.md'):
                    self._export_to_markdown(file_name, selected_ids)
                else:
                    QMessageBox.warning(self, self.tr("Export Error"), self.tr("Unsupported file format. Please use .csv or .md"))
                    return
                QMessageBox.information(self, self.tr("Export Successful"), self.tr("Selected prompts exported to {0}").format(file_name))
            except Exception as e:
                QMessageBox.critical(self, self.tr("Export Error"), self.tr("Failed to export selected prompts: {0}").format(e))

    def export_prompts(self):
        file_name, _ = QFileDialog.getSaveFileName(self, self.tr("Export Prompts"), "",
                                                  self.tr("CSV Files (*.csv);;Markdown Files (*.md);;All Files (*)"))
        if file_name:
            try:
                if file_name.lower().endswith('.csv'):
                    self._export_to_csv(file_name)
                elif file_name.lower().endswith('.md'):
                    self._export_to_markdown(file_name)
                else:
                    QMessageBox.warning(self, self.tr("Export Error"), self.tr("Unsupported file format. Please use .csv or .md"))
                    return
                QMessageBox.information(self, self.tr("Export Successful"), self.tr("Prompts exported to {0}").format(file_name))
            except Exception as e:
                QMessageBox.critical(self, self.tr("Export Error"), self.tr("Failed to export prompts: {0}").format(e))

    def _export_to_csv(self, file_path, prompt_ids=None):
        prompts_to_export = list(self.prompts.items())
        if prompt_ids is not None:
            prompts_to_export = [(pid, self.prompts[pid]) for pid in prompt_ids if pid in self.prompts]
            
        # Use the import/export service to export to CSV
        if not self.import_export_service.export_to_csv(file_path, prompts_to_export):
            raise Exception("Failed to export to CSV")

    def _export_to_markdown(self, file_path, prompt_ids=None):
        prompts_to_export = list(self.prompts.items())
        if prompt_ids is not None:
            prompts_to_export = [(pid, self.prompts[pid]) for pid in prompt_ids if pid in self.prompts]
            
        # Use the import/export service to export to Markdown
        if not self.import_export_service.export_to_markdown(file_path, prompts_to_export):
            raise Exception("Failed to export to Markdown")

    def import_prompts(self):
        file_name, _ = QFileDialog.getOpenFileName(self, self.tr("Import Prompts"), "",
                                                  self.tr("CSV Files (*.csv);;Markdown Files (*.md);;All Files (*)"))
        if file_name:
            try:
                # Create pre-import backup
                print("Creating pre-import backup...")
                pre_import_backup = self.backup_service.create_backup("pre_import")
                if not pre_import_backup:
                    print("Warning: Could not create pre-import backup")

                imported_prompts = []
                if file_name.lower().endswith('.csv'):
                    imported_prompts = self._import_from_csv(file_name)
                elif file_name.lower().endswith('.md'):
                    imported_prompts = self._import_from_markdown(file_name)
                else:
                    QMessageBox.warning(self, self.tr("Import Error"), self.tr("Unsupported file format. Please use .csv or .md"))
                    return

                if not imported_prompts:
                    QMessageBox.information(self, self.tr("Import Complete"), self.tr("No prompts found in the selected file."))
                    return

                imported_count = 0
                for prompt_data in imported_prompts:
                    if self._handle_imported_prompt(prompt_data):
                        imported_count += 1

                self.update_category_list()
                self.update_tag_list()
                self.update_prompt_list(filter_category=self.current_filter_category(),
                                        filter_tag=self.current_filter_tag(),
                                        search_term=self.searchBar.text(),
                                        filter_favorites=self.is_favorites_filter_active())
                self.save_prompts()
                QMessageBox.information(self, self.tr("Import Successful"), self.tr("Successfully imported {0} prompt(s).").format(imported_count))

            except Exception as e:
                QMessageBox.critical(self, self.tr("Import Error"), self.tr("Failed to import prompts: {0}").format(e))

    def _import_from_csv(self, file_path):
        # Use the import/export service to import from CSV
        return self.import_export_service.import_from_csv(file_path)

    def _import_from_markdown(self, file_path):
        # Use the import/export service to import from Markdown
        return self.import_export_service.import_from_markdown(file_path)

    def _handle_duplicate_prompt(self, imported_data, existing_prompt_id):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(self.tr("Duplicate Prompt Detected"))
        msg_box.setText(self.tr("A prompt with the title '{0}' already exists.").format(imported_data.get('title', 'Untitled')))
        msg_box.setInformativeText(self.tr("What would you like to do?"))

        skip_button = msg_box.addButton(self.tr("Skip"), QMessageBox.ButtonRole.RejectRole)
        overwrite_button = msg_box.addButton(self.tr("Overwrite"), QMessageBox.ButtonRole.AcceptRole)
        keep_both_button = msg_box.addButton(self.tr("Keep Both"), QMessageBox.ButtonRole.ActionRole)

        msg_box.setDefaultButton(skip_button)

        msg_box.exec()

        if msg_box.clickedButton() == overwrite_button:
            # Overwrite existing prompt, create a new version using the data service
            commit_message = f"Import overwrite: {imported_data.get('title', 'Untitled')}"
            if self.data_service.update_prompt(existing_prompt_id, imported_data, commit_message):
                # Update local prompts reference
                self.prompts = self.data_service.prompts
                print(f"Prompt '{imported_data.get('title')}' overwritten.")
                return True
            else:
                print(f"Failed to overwrite prompt '{imported_data.get('title')}'.")
                return False
        elif msg_box.clickedButton() == keep_both_button:
            # Add as a new prompt with initial version using the data service
            prompt_id = self.data_service.add_new_prompt(imported_data)
            # Update local prompts reference
            self.prompts = self.data_service.prompts
            self.next_id = self.data_service.next_id
            print(f"Prompt '{imported_data.get('title')}' imported as new.")
            return True
        else: # Skip
            print(f"Prompt '{imported_data.get('title')}' skipped.")
            return False

    def _handle_imported_prompt(self, imported_data):
        # Check for existing prompt with the same title
        existing_prompt_id = None
        for pid, p_info in self.prompts.items():
            if p_info['data'].get('title') == imported_data.get('title'):
                existing_prompt_id = pid
                break

        if existing_prompt_id is not None:
            # Duplicate found, delegate to helper method
            return self._handle_duplicate_prompt(imported_data, existing_prompt_id)
        else:
            # No duplicate, add as a new prompt with initial version using the data service
            prompt_id = self.data_service.add_new_prompt(imported_data)
            # Update local prompts reference
            self.prompts = self.data_service.prompts
            self.next_id = self.data_service.next_id
            print(f"Prompt '{imported_data.get('title')}' imported.")
            return True

    def manageCategories(self):
        dialog = CategoryDialog(self, self.categories)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_managed_categories = dialog.getCategories()
            new_managed_categories.sort()

            if new_managed_categories != self.categories:
                removed_categories = set(self.categories) - set(new_managed_categories)
                self.categories = new_managed_categories

                prompts_updated = False
                if removed_categories:
                    print(f"Categories removed from management: {removed_categories}")
                    for prompt_id, prompt_info in self.prompts.items():
                        current_category = prompt_info['data'].get('category', 'No category')
                        if current_category in removed_categories:
                            # Update the prompt data using the data service
                            prompt_data = self.data_service.get_prompt_data(prompt_id)
                            prompt_data['category'] = 'No category'
                            
                            # Create a new version with the updated category
                            commit_message = f"Move to 'No category' because '{current_category}' was removed"
                            if self.data_service.update_prompt(prompt_id, prompt_data, commit_message):
                                # Update local prompts reference
                                self.prompts = self.data_service.prompts
                                print(f"Prompt ID {prompt_id} moved to 'No category' because its category '{current_category}' was removed.")
                                prompts_updated = True
                            else:
                                print(f"Failed to update category for prompt ID {prompt_id}.")

                self.update_category_list()
                self.update_prompt_list(filter_category=self.current_filter_category(),
                                        filter_tag=self.current_filter_tag(),
                                        search_term=self.searchBar.text(),
                                        filter_favorites=self.is_favorites_filter_active())
                self.save_prompts()
                print("Managed categories list and prompts updated and saved.")
            else:
                print("No changes detected in managed categories.")
        else:
            print("Category management cancelled.")

    def manageTags(self):
        # Pass all unique tags (global and from prompts) to the dialog
        all_unique_tags = self.global_tags.union(self._get_all_tags_from_prompts())
        dialog = TagDialog(self, tags=list(all_unique_tags))

        if dialog.exec() == QDialog.DialogCode.Accepted:
            renamed_tags, removed_tags, added_tags = dialog.getChanges()

            if not renamed_tags and not removed_tags and not added_tags:
                print("No tag changes to apply.")
                return

            prompts_updated = False
            # Apply renames and removals to existing prompts
            for prompt_id, prompt_info in self.prompts.items():
                current_prompt_tags = set(prompt_info['data'].get('tags', []))
                new_prompt_tags = set()
                tags_changed_for_prompt = False

                for tag in current_prompt_tags:
                    if tag in removed_tags:
                        tags_changed_for_prompt = True
                        continue
                    elif tag in renamed_tags:
                        new_prompt_tags.add(renamed_tags[tag])
                        tags_changed_for_prompt = True
                    else:
                        new_prompt_tags.add(tag)

                if tags_changed_for_prompt:
                    sorted_new_tags = sorted(list(new_prompt_tags))
                    # Update the prompt data using the data service
                    prompt_data = self.data_service.get_prompt_data(prompt_id)
                    prompt_data['tags'] = sorted_new_tags
                    
                    # Create a new version with the updated tags
                    commit_message = f"Update tags: {', '.join(sorted_new_tags)}"
                    if self.data_service.update_prompt(prompt_id, prompt_data, commit_message):
                        # Update local prompts reference
                        self.prompts = self.data_service.prompts
                        print(f"Tags updated for Prompt ID {prompt_id}: {sorted_new_tags}")
                        prompts_updated = True
                    else:
                        print(f"Failed to update tags for prompt ID {prompt_id}.")

            # Update global_tags based on changes from the dialog
            for old_name, new_name in renamed_tags.items():
                if old_name in self.global_tags:
                    self.global_tags.remove(old_name)
                self.global_tags.add(new_name)

            for tag in removed_tags:
                if tag in self.global_tags:
                    self.global_tags.remove(tag)

            for tag in added_tags:
                self.global_tags.add(tag)

            # Always mark as updated if any changes were made to global_tags or prompts
            if prompts_updated or renamed_tags or removed_tags or added_tags:
                print("Updating UI and saving after tag changes...")
                self.update_tag_list()
                self.update_prompt_list(filter_category=self.current_filter_category(),
                                        filter_tag=self.current_filter_tag(),
                                        search_term=self.searchBar.text(),
                                        filter_favorites=self.is_favorites_filter_active())
                self.save_prompts()
            else:
                print("No changes detected in tags.")
        else:
            print("Tag management cancelled.")

    def _get_all_tags_from_prompts(self):
        # Use the data service to get all tags from prompts
        return self.data_service.get_all_tags_from_prompts()

    def _save_prompt_from_panel(self):
        if not self.current_editor_instance:
            print("No active editor instance to save from.")
            return

        data = self.current_editor_instance.getPromptData()
        if not data['title']:
            QMessageBox.warning(self, self.tr("Missing Title"), self.tr("Prompt title cannot be empty."))
            return

        prompt_id = self.current_editor_instance.property("editing_prompt_id")

        commit_message = data.pop('commit_message', "No commit message provided.") # Extract commit message

        if prompt_id is None: # This is an add operation
            # Use the data service to add a new prompt
            prompt_id = self.data_service.add_new_prompt(data)
            # Update local prompts reference
            self.prompts = self.data_service.prompts
            self.next_id = self.data_service.next_id
            print(f"New prompt ID {prompt_id} added from panel.")
        else: # This is an edit operation
            if prompt_id not in self.prompts:
                QMessageBox.critical(self, self.tr("Error"), self.tr("Could not find prompt with ID {0} to save.").format(prompt_id))
                return

            current_data = self.prompts[prompt_id]['data']
            data_changed = data != current_data

            if data_changed:
                # Use the data service to update the prompt
                if self.data_service.update_prompt(prompt_id, data, commit_message):
                    # Update local prompts reference
                    self.prompts = self.data_service.prompts
                    print(f"Prompt ID {prompt_id} updated from panel.")
                else:
                    print(f"Failed to update prompt ID {prompt_id} from panel.")
            else:
                print(f"No changes detected for ID {prompt_id}, no new version created from panel.")

        self.update_category_list()
        self.update_tag_list()
        self.update_prompt_list(filter_category=self.current_filter_category(),
                                filter_tag=self.current_filter_tag(),
                                search_term=self.searchBar.text(),
                                filter_favorites=self.is_favorites_filter_active())
        self.save_prompts()
        self.clear_editor_panel()
        self.show_editor_panel(False) # Hide the panel after saving
        print("Prompt saved and panel closed.")

    def _cancel_prompt_edit_from_panel(self):
        self.clear_editor_panel()
        self.show_editor_panel(False) # Hide the panel
        print("Prompt edit/add cancelled and panel closed.")

    def _generate_version_id(self, data, message):
        # Using UUID for simpler, unique ID generation
        return str(uuid.uuid4())

    def _get_current_timestamp(self):
        from datetime import datetime
        return datetime.utcnow().isoformat() + 'Z' # ISO 8601 format with UTC indicator

    def _get_current_user(self):
        import getpass
        try:
            return getpass.getuser()
        except Exception:
            return "unknown"
