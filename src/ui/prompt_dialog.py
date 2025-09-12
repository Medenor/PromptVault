import difflib
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
                             QPushButton, QMessageBox, QDialogButtonBox, QLabel,
                             QTextEdit, QComboBox, QToolTip, QCheckBox, QSizePolicy,
                             QCompleter, QListWidget, QListWidgetItem, QInputDialog) # Added QCompleter, QListWidget, QListWidgetItem, QInputDialog
from PyQt6.QtCore import Qt, pyqtSignal, QStringListModel, QEvent # Added pyqtSignal, QStringListModel, QEvent

class PromptDialog(QDialog):
    # Define custom signals for panel mode
    accepted = pyqtSignal()
    rejected = pyqtSignal()

    def __init__(self, parent=None, data=None, versions=None, categories=None, all_tags=None, is_panel=False):
        super().__init__(parent)
        self.versions_data = versions if versions else [] # Use versions_data instead of history_data
        self.current_data = data
        self.categories = categories if categories else []
        self.all_tags = all_tags if all_tags is not None else [] # Store all available tags
        self.is_panel = is_panel # New flag to indicate panel mode
        self.initUI(data)
        if self.is_panel:
            self.setWindowFlags(Qt.WindowType.Widget) # Make it a widget, not a dialog window
            self.setContentsMargins(0, 0, 0, 0) # Remove margins for panel integration
            self.layout().setContentsMargins(0, 0, 0, 0) # Remove layout margins
            self.layout().setSpacing(5) # Adjust spacing for panel
            self.setWindowTitle("") # No title in panel mode
            self.setMinimumWidth(300) # Set a minimum width for the panel
            self.setMaximumWidth(900) # Increased maximum width for the panel
            self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
            self.diffOutput.setMinimumHeight(100) # Ensure diff output is visible
            self.diffOutput.setMaximumHeight(200) # Limit diff output height
            self.promptEdit.setMinimumHeight(300) # Increased prompt editor height
            self.noteEdit.setMinimumHeight(50) # Decreased note editor height
            self.promptEdit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.noteEdit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.diffOutput.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def _get_diff_html(self, old_text, new_text, label=""):
        d = difflib.Differ()
        diff = list(d.compare(old_text.splitlines(keepends=True), new_text.splitlines(keepends=True)))

        html_diff = []
        if label:
            html_diff.append(f"<b>{label} Diff:</b><br>")
        html_diff.append("<pre style='font-family: \"Courier New\", monospace; white-space: pre-wrap;'>")
        for line in diff:
            if line.startswith('+'):
                html_diff.append(f"<span style='color: green;'>{line}</span>")
            elif line.startswith('-'):
                html_diff.append(f"<span style='color: red;'>{line}</span>")
            elif line.startswith('?'):
                # Ignore diff internal markers
                continue
            else:
                html_diff.append(line)
        html_diff.append("</pre>")
        return "".join(html_diff)

    def initUI(self, data=None):
        self.setWindowTitle(self.tr('Add/Edit Prompt'))
        layout = QVBoxLayout(self)

        if self.versions_data and len(self.versions_data) > 1: # Use versions_data
            history_layout = QHBoxLayout()
            self.historyCombo = QComboBox()
            # Populate with version IDs and commit messages
            for i, version_info in enumerate(reversed(self.versions_data)):
                version_label = f"{version_info.get('version_id', 'N/A')[:7]} - {version_info.get('message', 'No message')}"
                if i == 0:
                    version_label += " (Current)"
                self.historyCombo.addItem(version_label, i)
            self.historyCombo.currentIndexChanged.connect(self.display_history_version)
            self.historyCombo.setCurrentIndex(0)
            history_layout.addWidget(QLabel(self.tr("History:")), 0)
            history_layout.addWidget(self.historyCombo, 1)

            # The purge history button and its functionality are removed as they are not compatible
            # with the new Git-like versioning system.
            # If a similar feature is desired in the future, it should be re-designed
            # to work with the new 'versions' data structure and branching model.

            layout.addLayout(history_layout)

        layout.addWidget(QLabel(self.tr('Prompt Title:')))
        self.titleEdit = QLineEdit()
        self.titleEdit.setPlaceholderText(self.tr("Add prompt title here"))
        if data:
            self.titleEdit.setText(data.get('title', ''))
        layout.addWidget(self.titleEdit)

        self.favoriteCheckbox = QCheckBox(self.tr("Mark as favorite"))
        if data:
            self.favoriteCheckbox.setChecked(data.get('favorite', False))
        layout.addWidget(self.favoriteCheckbox)

        layout.addWidget(QLabel(self.tr('Category:')))
        self.categoryCombo = QComboBox()
        display_categories = list(self.categories)
        if 'No category' not in display_categories:
             display_categories.insert(0, 'No category')
        display_categories.sort()

        self.categoryCombo.addItems(display_categories)
        default_category = 'No category'
        if data:
            default_category = data.get('category', 'No category')
        self.categoryCombo.setCurrentText(default_category)
        layout.addWidget(self.categoryCombo)


        layout.addWidget(QLabel(self.tr('Tags:')))

        # New layout for tag input and list
        tag_input_layout = QHBoxLayout()
        self.tagInputEdit = QLineEdit()
        self.tagInputEdit.setPlaceholderText(self.tr("Type a tag and press Enter or click Add"))
        tag_input_layout.addWidget(self.tagInputEdit)

        self.addTagButton = QPushButton(self.tr("Add Tag"))
        self.addTagButton.clicked.connect(self._add_tag_from_input)
        tag_input_layout.addWidget(self.addTagButton)
        layout.addLayout(tag_input_layout)

        self.tagsListWidget = QListWidget()
        self.tagsListWidget.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        if data and 'tags' in data:
            for tag in data['tags']:
                self.tagsListWidget.addItem(tag)
        layout.addWidget(self.tagsListWidget)

        self.removeTagButton = QPushButton(self.tr("Remove Selected Tags"))
        self.removeTagButton.clicked.connect(self._remove_selected_tags)
        layout.addWidget(self.removeTagButton)

        # Setup QCompleter for the new tagInputEdit
        self.tag_completer = QCompleter(self)
        self.tag_model = QStringListModel(self.all_tags)
        self.tag_completer.setModel(self.tag_model)
        self.tag_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.tag_completer.setFilterMode(Qt.MatchFlag.MatchContains)

        self.tagInputEdit.setCompleter(self.tag_completer)
        self.tagInputEdit.textEdited.connect(self._update_completer_prefix)
        self.tagInputEdit.returnPressed.connect(self._add_tag_from_input) # Add tag on Enter key press

        layout.addWidget(QLabel(self.tr('Prompt:')))
        self.promptEdit = QTextEdit()
        self.promptEdit.setPlaceholderText(self.tr("Add prompt here"))
        if data:
            self.promptEdit.setPlainText(data.get('prompt', ''))
        layout.addWidget(self.promptEdit)

        layout.addWidget(QLabel(self.tr('Note:')))
        self.noteEdit = QTextEdit()
        self.noteEdit.setPlaceholderText(self.tr("Add additional notes or information here..."))
        if data:
            self.noteEdit.setPlainText(data.get('note', ''))
        layout.addWidget(self.noteEdit)

        self.diffOutput = QTextEdit()
        self.diffOutput.setReadOnly(True)
        self.diffOutput.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.diffOutput.setPlaceholderText(self.tr("Diff will appear here when comparing history versions."))
        layout.addWidget(self.diffOutput)

        layout.addWidget(QLabel(self.tr('Commit Message:')))
        self.commitMessageEdit = QLineEdit()
        self.commitMessageEdit.setPlaceholderText(self.tr("Enter a commit message for this change (required)"))
        layout.addWidget(self.commitMessageEdit)

        if self.is_panel:
            # For panel mode, use custom buttons and signals
            panel_button_layout = QHBoxLayout()
            self.saveButton = QPushButton(self.tr("Save"))
            self.cancelButton = QPushButton(self.tr("Cancel"))
            panel_button_layout.addStretch(1)
            panel_button_layout.addWidget(self.saveButton)
            panel_button_layout.addWidget(self.cancelButton)
            layout.addLayout(panel_button_layout)

            self.saveButton.clicked.connect(self._save_clicked)
            self.cancelButton.clicked.connect(self._cancel_clicked)
        else:
            # For dialog mode, use QDialogButtonBox
            buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            buttonBox.accepted.connect(self.accept)
            buttonBox.rejected.connect(self.reject)
            layout.addWidget(buttonBox)

    def display_history_version(self, index):
        if not self.versions_data or index < 0:
            return

        # The versions_data is already ordered from oldest to newest.
        # We display it reversed in the combo box, so we need to map the index back.
        original_version_index = len(self.versions_data) - 1 - index
        if 0 <= original_version_index < len(self.versions_data):
            version_info = self.versions_data[original_version_index]
            version_data = version_info.get('data', {}) # Get the actual prompt data from the version object
            
            # Update fields with selected history version's data
            self.titleEdit.setText(version_data.get('title', ''))
            self.favoriteCheckbox.setChecked(version_data.get('favorite', False))
            self.categoryCombo.setCurrentText(version_data.get('category', 'No category'))
            
            self.tagsListWidget.clear()
            for tag in version_data.get('tags', []):
                self.tagsListWidget.addItem(tag)

            self.promptEdit.setPlainText(version_data.get('prompt', ''))
            self.noteEdit.setPlainText(version_data.get('note', ''))
            
            # If displaying the current version, allow editing the commit message
            if original_version_index == len(self.versions_data) - 1:
                self.commitMessageEdit.clear()
                self.commitMessageEdit.setPlaceholderText(self.tr("Enter a commit message for this change (required)"))
                self.commitMessageEdit.setReadOnly(False)
            else:
                self.commitMessageEdit.setText(version_info.get('message', 'No message')) # Corrected to setText
                self.commitMessageEdit.setPlaceholderText(f"Commit message: {version_info.get('message', 'No message')} (by {version_info.get('author', 'unknown')} at {version_info.get('timestamp', 'N/A')})")
                self.commitMessageEdit.setReadOnly(True) # Make it read-only when viewing history

            print(f"Displaying history version ID {version_info.get('version_id', 'N/A')[:7]}")

            # Generate and display diff against the current working data
            if self.current_data:
                current_title = self.current_data.get('title', '')
                current_prompt = self.current_data.get('prompt', '')
                current_note = self.current_data.get('note', '')
                current_category = self.current_data.get('category', 'No category')
                current_tags = set(self.current_data.get('tags', []))
                current_favorite = self.current_data.get('favorite', False)

                history_title = version_data.get('title', '')
                history_prompt = version_data.get('prompt', '')
                history_note = version_data.get('note', '')
                history_category = version_data.get('category', 'No category')
                history_tags = set(version_data.get('tags', []))
                history_favorite = version_data.get('favorite', False)

                full_diff_html = []

                if original_version_index == len(self.versions_data) - 1: # If it's the current version
                    self.diffOutput.setHtml("<b>No changes (this is the current version).</b>")
                    return

                # Text field diffs
                if current_title != history_title:
                    full_diff_html.append(self._get_diff_html(history_title, current_title, "Title"))
                
                if current_prompt != history_prompt:
                    full_diff_html.append(self._get_diff_html(history_prompt, current_prompt, "Prompt"))
                
                if current_note != history_note:
                    full_diff_html.append(self._get_diff_html(history_note, current_note, "Note"))

                # Other field diffs
                if current_category != history_category:
                    full_diff_html.append(f"<b>Category Diff:</b> Changed from '{history_category}' to '{current_category}'<br>")
                
                if current_tags != history_tags:
                    removed_tags = history_tags - current_tags
                    added_tags = current_tags - history_tags
                    tag_diff_str = "<b>Tags Diff:</b> "
                    if removed_tags:
                        tag_diff_str += f"<span style='color: red;'>Removed: {', '.join(sorted(list(removed_tags)))}</span> "
                    if added_tags:
                        tag_diff_str += f"<span style='color: green;'>Added: {', '.join(sorted(list(added_tags)))}</span>"
                    full_diff_html.append(tag_diff_str + "<br>")

                if current_favorite != history_favorite:
                    full_diff_html.append(f"<b>Favorite Diff:</b> Changed from '{'Yes' if history_favorite else 'No'}' to '{'Yes' if current_favorite else 'No'}'<br>")

                if full_diff_html:
                    self.diffOutput.setHtml("".join(full_diff_html))
                else:
                    self.diffOutput.setHtml("<b>No changes between this version and the current version.</b>")
            else:
                self.diffOutput.setHtml("<b>Cannot show diff: Current prompt data is not available.</b>")

    def accept(self):
        title = self.titleEdit.text().strip()
        prompt_text = self.promptEdit.toPlainText().strip()
        commit_message = self.commitMessageEdit.text().strip()

        if not title:
            QMessageBox.warning(self, self.tr("Missing Required Field"), self.tr("The 'Prompt Title' field cannot be empty."))
            self.titleEdit.setFocus()
            return

        if not prompt_text:
            QMessageBox.warning(self, self.tr("Missing Required Field"), self.tr("The 'Prompt' field cannot be empty."))
            self.promptEdit.setFocus()
            return

        if not commit_message:
            QMessageBox.warning(self, self.tr("Missing Required Field"), self.tr("A 'Commit Message' is required to save changes."))
            self.commitMessageEdit.setFocus()
            return

        super().accept()

    def getPromptData(self):
        tags = []
        for i in range(self.tagsListWidget.count()):
            tags.append(self.tagsListWidget.item(i).text())
        
        return {
            'title': self.titleEdit.text(),
            'favorite': self.favoriteCheckbox.isChecked(),
            'category': self.categoryCombo.currentText(),
            'tags': sorted(list(set(tags))), # Ensure unique and sorted tags
            'prompt': self.promptEdit.toPlainText(),
            'note': self.noteEdit.toPlainText(),
            'commit_message': self.commitMessageEdit.text().strip() # Include commit message
        }

    def _save_clicked(self):
        title = self.titleEdit.text().strip()
        prompt_text = self.promptEdit.toPlainText().strip()
        commit_message = self.commitMessageEdit.text().strip()

        if not title:
            QMessageBox.warning(self, self.tr("Missing Required Field"), self.tr("The 'Prompt Title' field cannot be empty."))
            self.titleEdit.setFocus()
            return

        if not prompt_text:
            QMessageBox.warning(self, self.tr("Missing Required Field"), self.tr("The 'Prompt' field cannot be empty."))
            self.promptEdit.setFocus()
            return

        if not commit_message:
            QMessageBox.warning(self, self.tr("Missing Required Field"), self.tr("A 'Commit Message' is required to save changes."))
            self.commitMessageEdit.setFocus()
            return

        self.accepted.emit() # Emit custom accepted signal

    def _cancel_clicked(self):
        self.rejected.emit() # Emit custom rejected signal

    def _add_tag_from_input(self):
        tag_text = self.tagInputEdit.text().strip()
        if tag_text and tag_text not in [self.tagsListWidget.item(i).text() for i in range(self.tagsListWidget.count())]:
            self.tagsListWidget.addItem(tag_text)
            self.tagInputEdit.clear()
            # Optionally add the new tag to the completer model if it's not already there
            if tag_text not in self.all_tags:
                self.all_tags.append(tag_text)
                self.all_tags.sort()
                self.tag_model.setStringList(self.all_tags)

    def _remove_selected_tags(self):
        for item in self.tagsListWidget.selectedItems():
            self.tagsListWidget.takeItem(self.tagsListWidget.row(item))

    def _update_completer_prefix(self, text):
        # For single tag input, the prefix is simply the current text
        self.tag_completer.setCompletionPrefix(text)
        if text and not self.tag_completer.popup().isVisible():
            self.tag_completer.complete()
