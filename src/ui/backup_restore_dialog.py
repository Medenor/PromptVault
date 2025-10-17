import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QListWidget, QListWidgetItem,
                             QMessageBox, QSplitter, QWidget, QTextEdit,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QAbstractItemView, QProgressBar, QApplication)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QFont, QIcon
from datetime import datetime
import humanize


class BackupRestoreDialog(QDialog):
    """Dialog for managing backups and restoration."""

    def __init__(self, backup_service, parent=None):
        super().__init__(parent)
        self.backup_service = backup_service
        self.current_backups = []

        self.setWindowTitle(self.tr("Backup && Restore"))
        self.setModal(True)
        self.resize(800, 600)

        self.initUI()
        self.load_backups()

        # Auto-refresh timer (every 30 seconds)
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.load_backups)
        self.refresh_timer.start(30000)

    def initUI(self):
        layout = QVBoxLayout(self)

        # Title
        title_label = QLabel(self.tr("Backup && Restore Management"))
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Create splitter for backup list and details
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side - Backup list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # Backup list label
        backup_list_label = QLabel(self.tr("Available Backups:"))
        left_layout.addWidget(backup_list_label)

        # Backup list
        self.backup_list = QListWidget()
        self.backup_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.backup_list.itemSelectionChanged.connect(self.show_backup_details)
        left_layout.addWidget(self.backup_list)

        # Backup list buttons
        button_layout = QHBoxLayout()

        self.refresh_button = QPushButton(self.tr("Refresh"))
        self.refresh_button.clicked.connect(self.load_backups)
        button_layout.addWidget(self.refresh_button)

        self.create_backup_button = QPushButton(self.tr("Create Backup"))
        self.create_backup_button.clicked.connect(self.create_backup)
        button_layout.addWidget(self.create_backup_button)

        left_layout.addLayout(button_layout)

        splitter.addWidget(left_widget)

        # Right side - Backup details and actions
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # Backup details label
        details_label = QLabel(self.tr("Backup Details:"))
        right_layout.addWidget(details_label)

        # Backup details table
        self.details_table = QTableWidget(0, 2)
        self.details_table.setHorizontalHeaderLabels([self.tr("Property"), self.tr("Value")])
        self.details_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.details_table.verticalHeader().setVisible(False)
        self.details_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.details_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        right_layout.addWidget(self.details_table)

        # Backup actions
        actions_label = QLabel(self.tr("Actions:"))
        right_layout.addWidget(actions_label)

        actions_button_layout = QHBoxLayout()

        self.restore_button = QPushButton(self.tr("Restore Selected"))
        self.restore_button.clicked.connect(self.restore_selected_backup)
        self.restore_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        actions_button_layout.addWidget(self.restore_button)

        self.delete_button = QPushButton(self.tr("Delete Selected"))
        self.delete_button.clicked.connect(self.delete_selected_backup)
        self.delete_button.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: black;
                border: none;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #e0a800;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        actions_button_layout.addWidget(self.delete_button)

        right_layout.addLayout(actions_button_layout)

        # Statistics
        stats_label = QLabel(self.tr("Backup Statistics:"))
        right_layout.addWidget(stats_label)

        self.stats_text = QTextEdit()
        self.stats_text.setMaximumHeight(100)
        self.stats_text.setReadOnly(True)
        right_layout.addWidget(self.stats_text)

        splitter.addWidget(right_widget)

        # Set splitter proportions
        splitter.setSizes([400, 400])

        layout.addWidget(splitter)

        # Dialog buttons
        dialog_button_layout = QHBoxLayout()

        self.cleanup_button = QPushButton(self.tr("Cleanup Old Backups"))
        self.cleanup_button.clicked.connect(self.cleanup_old_backups)
        dialog_button_layout.addWidget(self.cleanup_button)

        dialog_button_layout.addStretch()

        self.close_button = QPushButton(self.tr("Close"))
        self.close_button.clicked.connect(self.accept)
        dialog_button_layout.addWidget(self.close_button)

        layout.addLayout(dialog_button_layout)

        # Enable/disable buttons based on selection
        self.update_button_states()

    def load_backups(self):
        """Load and display available backups."""
        try:
            self.current_backups = self.backup_service.list_backups()
            self.backup_list.clear()

            if not self.current_backups:
                self.backup_list.addItem(self.tr("No backups found"))
                self.show_backup_details()
                return

            for backup in self.current_backups:
                # Create list item with backup info
                timestamp = backup.get('timestamp', '')
                try:
                    # Parse ISO timestamp and format nicely
                    if timestamp:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                        human_time = humanize.naturaltime(dt)
                    else:
                        formatted_time = self.tr("Unknown")
                        human_time = self.tr("Unknown time")
                except:
                    formatted_time = self.tr("Unknown")
                    human_time = self.tr("Unknown time")

                prompt_count = backup.get('prompt_count', 0)
                size_bytes = backup.get('size_bytes', 0)

                # Format size
                if size_bytes < 1024:
                    size_str = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    size_str = f"{size_bytes/1024:.1f} KB"
                else:
                    size_str = f"{size_bytes/(1024*1024):.1f} MB"

                display_text = f"{formatted_time} - {prompt_count} prompts ({size_str})"

                item = QListWidgetItem(display_text)
                item.setData(Qt.ItemDataRole.UserRole, backup)
                self.backup_list.addItem(item)

            # Update statistics
            self.update_statistics()

        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"),
                               self.tr("Failed to load backups: {0}").format(str(e)))

    def show_backup_details(self):
        """Show details of selected backup."""
        current_item = self.backup_list.currentItem()
        if not current_item or not self.current_backups:
            self.details_table.setRowCount(0)
            self.update_button_states()
            return

        backup = current_item.data(Qt.ItemDataRole.UserRole)
        if not backup:
            self.details_table.setRowCount(0)
            self.update_button_states()
            return

        # Populate details table
        self.details_table.setRowCount(0)

        size_bytes = backup.get('size_bytes', 0)
        size_formatted = f"{size_bytes:,}"
        prompt_count = backup.get('prompt_count', 0)
        created_by = backup.get('created_by', self.tr('Unknown'))
        data_file_modified = backup.get('data_file_modified', self.tr('Unknown'))

        details = [
            (self.tr("Backup ID"), backup.get('backup_id', self.tr('Unknown'))),
            (self.tr("Created"), backup.get('timestamp', self.tr('Unknown'))),
            (self.tr("Size"), f"{size_formatted} bytes"),
            (self.tr("Prompts"), str(prompt_count)),
            (self.tr("Created By"), created_by),
            (self.tr("Data File Modified"), data_file_modified),
        ]

        for row, (prop, value) in enumerate(details):
            self.details_table.insertRow(row)
            self.details_table.setItem(row, 0, QTableWidgetItem(prop))
            self.details_table.setItem(row, 1, QTableWidgetItem(value))

        self.update_button_states()

    def update_button_states(self):
        """Update button enabled states based on selection."""
        has_selection = self.backup_list.currentItem() is not None
        has_backups = len(self.current_backups) > 0

        self.restore_button.setEnabled(has_selection and has_backups)
        self.delete_button.setEnabled(has_selection and has_backups)

    def update_statistics(self):
        """Update backup statistics display."""
        if not self.current_backups:
            self.stats_text.setPlainText(self.tr("No backups available"))
            return

        stats = self.backup_service.get_backup_stats()
        total_backups = stats.get('total_backups', 0)
        total_size = stats.get('total_size', 0)
        oldest = stats.get('oldest_backup', self.tr('Unknown'))
        newest = stats.get('newest_backup', self.tr('Unknown'))
        compressed = stats.get('compressed_count', 0)

        # Format sizes
        if total_size < 1024:
            size_str = f"{total_size} B"
        elif total_size < 1024 * 1024:
            size_str = f"{total_size/1024:.1f} KB"
        else:
            size_str = f"{total_size/(1024*1024):.1f} MB"

        stats_text = self.tr("Total Backups: {0}\nTotal Size: {1}\nOldest Backup: {2}\nNewest Backup: {3}\nCompressed: {4}").format(
            total_backups, size_str, oldest, newest, compressed
        )

        self.stats_text.setPlainText(stats_text)

    def create_backup(self):
        """Create a new backup."""
        backup_id = self.backup_service.create_backup("manual")
        if backup_id:
            QMessageBox.information(self, self.tr("Backup Created"),
                                  self.tr("Backup created successfully.\nBackup ID: {0}").format(backup_id))
            self.load_backups()  # Refresh the list
        else:
            QMessageBox.critical(self, self.tr("Backup Failed"),
                               self.tr("Failed to create backup. Check the console for details."))

    def restore_selected_backup(self):
        """Restore the selected backup."""
        current_item = self.backup_list.currentItem()
        if not current_item:
            return

        backup = current_item.data(Qt.ItemDataRole.UserRole)
        if not backup:
            return

        backup_id = backup.get('backup_id')
        timestamp = backup.get('timestamp', self.tr('Unknown'))

        # Confirmation dialog
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle(self.tr("Confirm Restore"))
        msg.setText(self.tr("Are you sure you want to restore this backup?"))
        msg.setInformativeText(self.tr("""This will:
• Replace all current data with backup from {0}
• Create a pre-restore backup automatically
• Cannot be undone

Continue?""").format(timestamp))

        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.No)

        if msg.exec() == QMessageBox.StandardButton.Yes:
            # Show progress (simulate)
            progress = QProgressBar()
            progress.setWindowTitle(self.tr("Restoring Backup"))
            progress.setRange(0, 0)  # Indeterminate progress
            progress.show()

            QApplication.processEvents()

            # Perform restore
            success = self.backup_service.restore_backup(backup_id)

            progress.close()

            if success:
                QMessageBox.information(self, self.tr("Restore Successful"),
                                      self.tr("Backup restored successfully. Please restart the application to see changes."))
                self.accept()  # Close dialog
            else:
                QMessageBox.critical(self, self.tr("Restore Failed"),
                                   self.tr("Failed to restore backup. Check the console for details."))

    def delete_selected_backup(self):
        """Delete the selected backup."""
        current_item = self.backup_list.currentItem()
        if not current_item:
            return

        backup = current_item.data(Qt.ItemDataRole.UserRole)
        if not backup:
            return

        backup_id = backup.get('backup_id')
        timestamp = backup.get('timestamp', self.tr('Unknown'))

        # Confirmation dialog
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle(self.tr("Confirm Delete"))
        msg.setText(self.tr("Are you sure you want to delete this backup?"))
        msg.setInformativeText(self.tr("Backup from {0} will be permanently deleted.").format(timestamp))
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.No)

        if msg.exec() == QMessageBox.StandardButton.Yes:
            # Find and remove the backup files
            try:
                backup_filename = backup.get('filename', f"{backup_id}.json")
                backup_path = os.path.join(self.backup_service.backups_dir, backup_filename)
                metadata_filename = backup_filename.replace('.json', '_metadata.json')
                metadata_path = os.path.join(self.backup_service.backups_dir, metadata_filename)

                # Remove files
                removed = False
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                    removed = True
                if os.path.exists(metadata_path):
                    os.remove(metadata_path)
                    removed = True

                if removed:
                    QMessageBox.information(self, self.tr("Delete Successful"),
                                          self.tr("Backup deleted successfully."))
                    self.load_backups()  # Refresh the list
                else:
                    QMessageBox.warning(self, self.tr("Delete Failed"),
                                      self.tr("Could not find backup files to delete."))

            except Exception as e:
                QMessageBox.critical(self, self.tr("Delete Error"),
                                   self.tr("Failed to delete backup: {0}").format(str(e)))

    def cleanup_old_backups(self):
        """Clean up old backups based on retention policy."""
        # Ask for retention days
        from PyQt6.QtWidgets import QInputDialog

        days, ok = QInputDialog.getInt(
            self, self.tr("Cleanup Old Backups"),
            self.tr("Remove backups older than (days):"),
            30, 1, 365
        )

        if ok:
            removed_count = self.backup_service.cleanup_old_backups(days)
            QMessageBox.information(self,
                                  self.tr("Cleanup Complete"),
                                  self.tr("{0} old backups removed.").format(removed_count))
            self.load_backups()  # Refresh the list

    def closeEvent(self, event):
        """Clean up when dialog is closed."""
        self.refresh_timer.stop()
        super().closeEvent(event)
