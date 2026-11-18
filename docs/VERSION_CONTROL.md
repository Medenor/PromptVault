# Version Control Documentation

PromptVault includes a robust, Git-like version control system for all prompts, ensuring full traceability and a clear history of changes. This documentation covers how to use the version control features effectively.

## Overview

Every time you update a prompt in PromptVault, a new version is automatically created with complete metadata including timestamp, author, and commit message. This ensures you never lose track of how your prompts evolved and can easily revert to previous versions if needed.

## Key Features

### Automatic Versioning

Every update to a prompt automatically creates a new version with:

- **Unique Version ID**: A UUID identifier for reliable tracking
- **Timestamp**: When the version was created
- **Author**: Who made the change
- **Commit Message**: A description of what changed and why
- **Complete Snapshot**: Full copy of the prompt data at that point in time

### Version History View

Access the version history of any prompt through:

- **Keyboard Shortcut**: `Cmd+H` (Mac) or `Ctrl+H` (Windows/Linux)
- **UI Button**: Click the "Version History" button in the prompt editor

The version history modal displays:

- List of all versions in chronological order (newest first)
- Commit messages and metadata for each version
- Search functionality to find specific versions
- Quick actions for comparison and revert

### Version Comparison

Compare any two versions to see exactly what changed:

1. Open the version history modal
2. Select two versions to compare
3. View the detailed diff visualization

The comparison view shows changes across all prompt fields including title, content, category, tags, and notes.

### Character-Level Diff Visualization

When comparing two versions of a prompt, PromptVault displays character-level changes inline for precise tracking of modifications. This feature makes it easy to identify minor edits like punctuation changes, typo corrections, or single character additions/deletions.

#### Visual Styling

- **Insertions** (added characters): Green background with bold text (`bg-green-100 font-semibold text-green-800`)
- **Deletions** (removed characters): Red background with strikethrough text (`bg-red-100 line-through text-red-800`)
- **Unchanged** (identical characters): Normal gray text (`text-gray-700`)

#### How It Works

The character-level diff uses a smart algorithm to detect the smallest possible changes between two text strings. Instead of showing entire lines or paragraphs as changed, it highlights only the exact characters that were added, removed, or modified.

**Example:**

Comparing these two versions:

- **Version 1**: `Write clean, readable Python code following PEP 8`
- **Version 2**: `Write clean, readable Python code following PEP 8.`

The diff view shows:

- `Write clean, readable Python code following PEP 8` in gray (unchanged)
- `.` in green background with bold styling (insertion)

#### Character-Level Precision

This character-level precision helps reviewers quickly spot:

- **Punctuation fixes**: Added or removed periods, commas, semicolons
- **Typo corrections**: Single character changes or transpositions
- **Whitespace adjustments**: Added or removed spaces, line breaks, indentation
- **Single character additions or deletions**: Any minor edit to the text

#### Supported Fields

Character-level diff visualization is available for:

- **Prompt Title**: See exactly what changed in the prompt's name
- **Prompt Content**: Track modifications to the main prompt text
- **Prompt Notes**: Monitor changes to additional documentation

For fields like categories and tags, the comparison shows the complete old and new values side-by-side for clarity.

#### Technical Implementation

The character-level diff is powered by the `renderCharacterDiff` utility function, which:

1. Receives an array of diff operations from the backend (equal, insert, delete)
2. Renders each operation as an HTML `<span>` element with appropriate styling
3. Preserves whitespace and line breaks with `whitespace-pre-wrap`
4. Escapes HTML to prevent injection attacks
5. Returns a complete DOM element ready for display

### Revert Functionality

You can safely revert a prompt to any previous version:

1. Open the version history modal
2. Find the version you want to revert to
3. Click the "Revert" button
4. The prompt will be restored to that version's state
5. **Important**: A new version is created to record the revert action

This means:

- History is **never lost** or overwritten
- You can see when and why a revert happened
- You can even revert a revert if needed

## Multi-Language Support

The version control UI is available in multiple languages:

- English
- French
- Spanish
- German

The interface will automatically match your application language preference.

## Usage Examples

### Creating a New Version

When you edit a prompt and save it:

1. Make your changes to the prompt title, content, category, tags, or notes
2. Enter a descriptive commit message (e.g., "Improved clarity in instructions")
3. Click "Save"
4. A new version is automatically created with your changes and commit message

### Viewing Version History

To view all versions of a prompt:

1. Open the prompt in the editor
2. Press `Cmd+H` (Mac) or `Ctrl+H` (Windows/Linux), or click "Version History"
3. Browse the list of versions with their commit messages and timestamps
4. Use the search box to filter versions by commit message

### Comparing Versions

To see what changed between two versions:

1. Open the version history modal
2. Select the first version (usually an older version)
3. Select the second version (usually a newer version)
4. Click "Compare" to view the detailed diff
5. Review the character-level changes highlighted in green (additions) and red (deletions)

### Reverting to a Previous Version

To restore a prompt to a previous state:

1. Open the version history modal
2. Find the version you want to restore
3. Click "Revert to this version"
4. Confirm the action
5. The prompt is restored, and a new version is created documenting the revert

## Best Practices

### Commit Messages

Write clear, descriptive commit messages that explain **why** you made changes, not just **what** changed:

- **Good**: "Simplified language for better AI understanding"
- **Good**: "Added examples to clarify expected output format"
- **Bad**: "Updated prompt"
- **Bad**: "Changes"

### When to Use Revert

Use the revert feature when:

- You need to undo recent changes that didn't work well
- You want to compare different approaches by switching between versions
- You accidentally made unwanted modifications
- You want to return to a known-good state

### Version Comparison Tips

- Compare adjacent versions to see incremental changes
- Compare distant versions to see the full evolution
- Use character-level diff to spot subtle changes like punctuation
- Review the commit messages to understand the context of changes

## Integration with Other Features

### Backup System

The version control system works seamlessly with PromptVault's backup system:

- Backups preserve all versions of all prompts
- Restoring from a backup maintains version history integrity
- Pre-operation backups ensure version data is never lost during destructive operations

### Import/Export

When exporting prompts:

- You can optionally include version history in exports
- JSON exports preserve all version metadata
- CSV and Markdown exports focus on the current version

When importing prompts:

- Imported prompts create new initial versions
- Existing prompts that are updated create new versions with import metadata

## Technical Details

### Version Storage

Versions are stored immutably in the database:

- Each version is a complete snapshot of the prompt at that point in time
- Versions are never modified after creation
- The version history is append-only for data integrity

### Performance

The version control system is optimized for performance:

- Version lists support pagination for prompts with many versions
- Diff calculations are performed server-side with efficient algorithms
- Character-level diffs use optimized diffing libraries

### API Endpoints

Version control is accessible via REST API:

- `GET /api/prompts/{id}/versions` - List all versions
- `GET /api/prompts/{id}/versions/{version_id}` - Get specific version
- `POST /api/prompts/{id}/versions/{version_id}/revert` - Revert to version
- `GET /api/prompts/{id}/versions/compare?v1={id1}&v2={id2}` - Compare versions

For complete API documentation, see [Application Specification](SPECS/SPEC_APP.md).

## Troubleshooting

### Version History Not Showing

If the version history modal is empty:

1. Ensure the prompt has been saved at least once
2. Check that you have permission to view the prompt
3. Verify the prompt ID is valid

### Diff Not Displaying Correctly

If character-level diffs appear incorrect:

1. Refresh the comparison view
2. Ensure both versions exist and are accessible
3. Check the browser console for JavaScript errors

### Revert Not Working

If reverting to a previous version fails:

1. Verify you have edit permissions for the prompt
2. Ensure the target version exists
3. Check for any validation errors in the version data

## Security Considerations

The version control system follows security best practices:

- **Access Control**: Users can only view/revert versions of prompts they have permission to access
- **Audit Trail**: All version operations are logged for security auditing
- **Data Integrity**: Immutable versions ensure historical data cannot be tampered with
- **XSS Prevention**: All diff content is properly escaped before rendering

## Future Enhancements

Planned improvements to the version control system include:

- Visual diff tools with side-by-side comparison
- Branch and merge capabilities for collaborative editing
- Diff statistics showing addition/deletion counts
- Automated version tagging based on significant changes
- Export version history to Git format

For the complete roadmap, see [ROADMAP.md](ROADMAP.md).

---

**Need Help?** If you have questions or issues with version control, please [open an issue](https://github.com/Medenor/PromptVault/issues) on GitHub.
