import difflib
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTextEdit, QListWidget, QListWidgetItem, QLabel,
                             QSizePolicy, QSplitter, QInputDialog, QMessageBox, QWidget, QLineEdit) # Added QLineEdit
from PyQt6.QtCore import Qt, pyqtSignal # Added pyqtSignal

class VersionHistoryDialog(QDialog):
    revertVersion = pyqtSignal(int, dict, str) # Signal to emit: prompt_id, reverted_data, commit_message

    def __init__(self, parent=None, prompt_id=None, prompt_title="", versions=None):
        super().__init__(parent)
        self.prompt_id = prompt_id # Store prompt_id
        self.setWindowTitle(f"Version History: {prompt_title}")
        self.setMinimumSize(900, 600)

        self.versions_data = versions if versions else []
        self.current_version_index = -1 # Index of the currently displayed version in the list

        self.initUI()
        self._populate_version_list()

    def initUI(self):
        main_layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # Left pane: Version list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.addWidget(QLabel("<b>Versions:</b>"))
        self.versionListWidget = QListWidget()
        self.versionListWidget.itemClicked.connect(self._display_version_details)
        left_layout.addWidget(self.versionListWidget)
        splitter.addWidget(left_widget)

        # Right pane: Details and Diff
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        self.versionDetailsLabel = QLabel("Select a version to view its details and diff.")
        self.versionDetailsLabel.setWordWrap(True)
        right_layout.addWidget(self.versionDetailsLabel)

        right_layout.addWidget(QLabel("<b>Prompt Content:</b>"))
        self.promptContentEdit = QTextEdit()
        self.promptContentEdit.setReadOnly(True)
        right_layout.addWidget(self.promptContentEdit)

        right_layout.addWidget(QLabel("<b>Diff with Previous Version:</b>"))
        self.diffOutput = QTextEdit()
        self.diffOutput.setReadOnly(True)
        self.diffOutput.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        right_layout.addWidget(self.diffOutput)

        splitter.addWidget(right_widget)

        # Set initial sizes for splitter panes
        splitter.setSizes([200, 700]) # Adjust as needed

        # Buttons layout
        button_layout = QHBoxLayout()
        self.revertButton = QPushButton("Revert to this Version")
        self.revertButton.clicked.connect(self._revert_version)
        self.revertButton.setEnabled(False) # Disabled by default
        button_layout.addWidget(self.revertButton)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        main_layout.addLayout(button_layout)

    def _populate_version_list(self):
        self.versionListWidget.clear()
        for i, version_info in enumerate(self.versions_data):
            version_id_short = version_info.get('version_id', 'N/A')[:7]
            message = version_info.get('message', 'No message')
            timestamp = version_info.get('timestamp', 'N/A')
            author = version_info.get('author', 'unknown')
            
            item_text = f"{version_id_short} - {message} ({author}, {timestamp})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, i) # Store original index
            self.versionListWidget.addItem(item)
        
        if self.versions_data:
            self.versionListWidget.setCurrentRow(len(self.versions_data) - 1) # Select latest version by default
            self._display_version_details(self.versionListWidget.currentItem())

    def _display_version_details(self, item):
        index = item.data(Qt.ItemDataRole.UserRole)
        if not (0 <= index < len(self.versions_data)):
            return

        self.current_version_index = index
        version_info = self.versions_data[index]
        version_data = version_info.get('data', {})

        # Update details label
        details_html = f"<b>Version ID:</b> {version_info.get('version_id', 'N/A')}<br>" \
                       f"<b>Commit Message:</b> {version_info.get('message', 'No message')}<br>" \
                       f"<b>Author:</b> {version_info.get('author', 'unknown')}<br>" \
                       f"<b>Timestamp:</b> {version_info.get('timestamp', 'N/A')}<br>" \
                       f"<b>Parents:</b> {', '.join([p[:7] for p in version_info.get('parents', [])]) if version_info.get('parents') else 'None'}<br>" \
                       f"<b>Category:</b> {version_data.get('category', 'No category')}<br>" \
                       f"<b>Tags:</b> {', '.join(version_data.get('tags', []))}<br>" \
                       f"<b>Favorite:</b> {'Yes' if version_data.get('favorite', False) else 'No'}"
        self.versionDetailsLabel.setText(details_html)

        # Update prompt content
        self.promptContentEdit.setPlainText(version_data.get('prompt', ''))

        # Enable/disable revert button
        self.revertButton.setEnabled(index < len(self.versions_data) - 1)

        # Generate and display diff with previous version
        if index > 0:
            previous_version_data = self.versions_data[index - 1].get('data', {})
            diff_html = self._get_diff_html(previous_version_data.get('prompt', ''), version_data.get('prompt', ''), "Prompt")
            
            # Add diff for other fields
            if previous_version_data.get('title', '') != version_data.get('title', ''):
                diff_html += self._get_diff_html(previous_version_data.get('title', ''), version_data.get('title', ''), "Title")
            if previous_version_data.get('note', '') != version_data.get('note', ''):
                diff_html += self._get_diff_html(previous_version_data.get('note', ''), version_data.get('note', ''), "Note")
            if previous_version_data.get('category', 'No category') != version_data.get('category', 'No category'):
                diff_html += f"<b>Category Diff:</b> Changed from '{previous_version_data.get('category', 'No category')}' to '{version_data.get('category', 'No category')}'<br>"
            
            prev_tags = set(previous_version_data.get('tags', []))
            curr_tags = set(version_data.get('tags', []))
            if prev_tags != curr_tags:
                removed_tags = prev_tags - curr_tags
                added_tags = curr_tags - prev_tags
                tag_diff_str = "<b>Tags Diff:</b> "
                if removed_tags:
                    tag_diff_str += f"<span style='color: red;'>Removed: {', '.join(sorted(list(removed_tags)))}</span> "
                if added_tags:
                    tag_diff_str += f"<span style='color: green;'>Added: {', '.join(sorted(list(added_tags)))}</span>"
                diff_html += tag_diff_str + "<br>"

            if previous_version_data.get('favorite', False) != version_data.get('favorite', False):
                diff_html += f"<b>Favorite Diff:</b> Changed from '{'Yes' if previous_version_data.get('favorite', False) else 'No'}' to '{'Yes' if version_data.get('favorite', False) else 'No'}'<br>"

            self.diffOutput.setHtml(diff_html)
        else:
            self.diffOutput.setHtml("<b>This is the first version. No previous version to compare.</b>")

    def _revert_version(self):
        if self.current_version_index == -1:
            QMessageBox.warning(self, "No Version Selected", "Please select a version to revert to.")
            return
        
        version_info_to_revert = self.versions_data[self.current_version_index]
        reverted_data = version_info_to_revert.get('data', {})
        version_id_short = version_info_to_revert.get('version_id', 'N/A')[:7]

        # Prompt for commit message
        commit_message, ok = QInputDialog.getText(self, "Revert Prompt",
                                                  f"Enter a commit message for reverting to version {version_id_short}:",
                                                  QLineEdit.EchoMode.Normal,
                                                  f"Revert to version {version_id_short}")
        if not ok or not commit_message:
            QMessageBox.warning(self, "Commit Message Required", "A commit message is required to perform a revert.")
            return

        reply = QMessageBox.question(self, "Confirm Revert",
                                     f"Are you sure you want to revert to version {version_id_short}?\n\n"
                                     "This will create a new version with the content of the selected version.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            self.revertVersion.emit(self.prompt_id, reverted_data, commit_message)
            self.accept() # Close the dialog after emitting the signal

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
