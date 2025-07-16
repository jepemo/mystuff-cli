# Implementation 0.6 – Lists

## Overview

The **Lists** module provides a comprehensive system for managing arbitrary named lists with full CRUD operations, check/uncheck functionality, and import/export capabilities. This module allows users to:

- Create named lists (e.g., "Books to Read", "Movies to Watch")
- Add, remove, and manage items within lists
- Check/uncheck items to track completion
- Search lists by name or item content
- Export lists to CSV or YAML formats
- Import lists from CSV or YAML files
- Interactive browsing with `fzf` integration

## Features Implemented

### Core Commands

- `mystuff list create` - Create new lists
- `mystuff list view` - View list contents with interactive selection
- `mystuff list edit` - Edit lists (add/remove items, check/uncheck)
- `mystuff list delete` - Delete lists with confirmation
- `mystuff list search` - Search lists by name or content
- `mystuff list export` - Export lists to CSV or YAML
- `mystuff list import` - Import lists from CSV or YAML
- `mystuff list list` - List all available lists

### Key Features

- **Individual YAML storage**: Each list is stored in a separate YAML file
- **Item management**: Add, remove, check, and uncheck items
- **Timestamps**: Automatic tracking of creation and modification times
- **Interactive selection**: Uses `fzf` for enhanced user experience
- **Search functionality**: Search by list name or item content
- **Import/Export**: Support for CSV and YAML formats
- **Completion tracking**: Visual indicators for checked/unchecked items

## File Structure

### Storage Location

```
~/.mystuff/lists/
├── books-to-read.yaml
├── movies-to-watch.yaml
├── shopping-list.yaml
└── ...
```

### YAML Format

Each list is stored as a separate YAML file with the following structure:

```yaml
name: "Books to Read"
created: "2025-07-16T10:37:39.586946"
modified: "2025-07-16T10:38:22.767915"
items:
  - text: "Clean Code by Robert C. Martin"
    checked: true
    added: "2025-07-16T10:37:49.802458"
    modified: "2025-07-16T10:38:22.767318"
  - text: "The Pragmatic Programmer"
    checked: false
    added: "2025-07-16T10:37:56.710379"
  - text: "Design Patterns"
    checked: false
    added: "2025-07-16T10:38:09.367990"
```

## Command Usage

### Create List

```bash
# Create a new list
mystuff list create --name "Books to Read"

# Create a list with a complex name
mystuff list create --name "Movies to Watch This Weekend"
```

### View List

```bash
# View a list interactively (with fzf)
mystuff list view --name "Books to Read"

# View a list without interactive mode
mystuff list view --name "Books to Read" --no-interactive
```

### Edit List

```bash
# Add an item to a list
mystuff list edit --name "Books to Read" --item "Clean Code by Robert C. Martin"

# Remove an item from a list
mystuff list edit --name "Books to Read" --remove-item "Old Book"

# Check an item as completed
mystuff list edit --name "Books to Read" --check "Clean Code by Robert C. Martin"

# Uncheck an item
mystuff list edit --name "Books to Read" --uncheck "Clean Code by Robert C. Martin"
```

### List All Lists

```bash
# Show all lists with completion status
mystuff list list

# Show all lists without interactive mode
mystuff list list --no-interactive
```

### Search Lists

```bash
# Search by list name
mystuff list search --search "Books"

# Search by item content
mystuff list search --search "Matrix"

# Search without interactive mode
mystuff list search --search "Books" --no-interactive
```

### Export Lists

```bash
# Export to YAML format
mystuff list export --name "Books to Read" --export /tmp/books.yaml

# Export to CSV format
mystuff list export --name "Books to Read" --export /tmp/books.csv
```

### Import Lists

```bash
# Import from YAML format
mystuff list import --name "Imported Books" --import /tmp/books.yaml

# Import from CSV format
mystuff list import --name "Imported Books" --import /tmp/books.csv
```

### Delete List

```bash
# Delete with confirmation
mystuff list delete --name "Old List"

# Force delete without confirmation
mystuff list delete --name "Old List" --force
```

## Implementation Details

### Data Model

Each list contains:

- `name`: Human-readable list name
- `created`: ISO timestamp of list creation
- `modified`: ISO timestamp of last modification
- `items`: Array of list items

Each item contains:

- `text`: The item content
- `checked`: Boolean completion status
- `added`: ISO timestamp when item was added
- `modified`: ISO timestamp when item was last modified (optional)

### Storage Strategy

- Each list is stored in a separate YAML file
- Filenames are generated using slugification (e.g., "Books to Read" → "books-to-read.yaml")
- Empty lists are preserved (unlike some other modules)
- YAML format provides human-readable storage with proper Unicode support

### Search and Filtering

- **Name search**: Case-insensitive search in list names
- **Content search**: Case-insensitive search in item text
- **Interactive selection**: Uses `fzf` for enhanced user experience
- **Completion display**: Shows checked/unchecked count for each list

### Import/Export System

- **CSV format**: Simple text,checked,added,modified format
- **YAML format**: Complete list structure with all metadata
- **Cross-format compatibility**: Can export to one format and import to another
- **Metadata preservation**: Timestamps and completion status are preserved

### Interactive Features

- **List selection**: `fzf` integration for choosing from multiple lists
- **Item selection**: `fzf` integration for selecting specific items
- **Completion indicators**: Visual ✓ and ○ symbols for checked/unchecked items
- **Progress display**: Shows completion ratio (e.g., "2/5 completed")

## Testing

### Unit Tests

The module includes comprehensive unit tests covering:

- CRUD operations for lists and items
- Check/uncheck functionality
- Search functionality
- Export/import operations (CSV and YAML)
- File structure validation
- Slugification functionality

### Integration Tests

- CLI command integration
- File system operations
- YAML serialization/deserialization
- CSV read/write operations
- Interactive mode compatibility

## CLI Integration

### Version Update

- Updated CLI version to 0.6.0
- Added list command group to main CLI
- Integrated with existing mystuff directory structure

### Interactive Features

- `fzf` integration for list and item selection
- Non-interactive mode available for scripting
- Visual completion indicators
- Progress tracking display

## Technical Notes

### Dependencies

- Uses `pyyaml` for YAML file handling
- Uses Python's `csv` module for CSV operations
- Integrates with `typer` for command-line interface
- Supports `fzf` for interactive selection (optional)

### Performance Considerations

- Individual file storage for efficient access
- Lazy loading of list data
- Optimized search operations
- Minimal memory footprint

### File Naming

- Uses slugification for safe filenames
- Handles special characters and spaces
- Consistent naming convention across the system

## Usage Examples

### Personal Task Management

```bash
# Create and manage a shopping list
mystuff list create --name "Shopping List"
mystuff list edit --name "Shopping List" --item "Milk"
mystuff list edit --name "Shopping List" --item "Bread"
mystuff list edit --name "Shopping List" --item "Eggs"

# Check items as you shop
mystuff list edit --name "Shopping List" --check "Milk"
mystuff list edit --name "Shopping List" --check "Bread"

# View progress
mystuff list view --name "Shopping List"
```

### Reading List Management

```bash
# Create a books list
mystuff list create --name "Books to Read"
mystuff list edit --name "Books to Read" --item "Clean Code"
mystuff list edit --name "Books to Read" --item "The Pragmatic Programmer"

# Mark books as read
mystuff list edit --name "Books to Read" --check "Clean Code"

# Export your reading list
mystuff list export --name "Books to Read" --export reading-list.yaml
```

### Project Management

```bash
# Create project task lists
mystuff list create --name "Website Features"
mystuff list edit --name "Website Features" --item "User authentication"
mystuff list edit --name "Website Features" --item "Payment processing"
mystuff list edit --name "Website Features" --item "Admin dashboard"

# Track completion
mystuff list edit --name "Website Features" --check "User authentication"
mystuff list list  # See overall progress
```

### Data Migration

```bash
# Export from one system
mystuff list export --name "Original List" --export backup.yaml

# Import to another system or rename
mystuff list import --name "Restored List" --import backup.yaml

# Cross-format conversion
mystuff list export --name "My List" --export data.yaml
mystuff list import --name "CSV Version" --import data.csv
```

## Error Handling

### Input Validation

- Required fields validation (list name)
- File format validation for import/export
- Existence checks for lists and items
- Safe filename generation

### User Feedback

- Clear success/error messages
- Confirmation prompts for destructive operations
- Progress indicators for long operations
- Helpful error messages with suggestions

## Future Enhancements

### Planned Features

- List templates and categories
- Due dates for list items
- Priority levels for items
- Bulk operations (check all, uncheck all)
- List sharing and collaboration
- Integration with calendar systems

### Technical Improvements

- Batch operations for performance
- List archiving and restoration
- Advanced search with filters
- Custom sorting options
- Backup and sync capabilities

## Summary

The Lists module (0.6) successfully implements a comprehensive list management system with:

- ✅ **Complete CRUD operations** for lists and items
- ✅ **Individual YAML storage** for efficient organization
- ✅ **Check/uncheck functionality** with visual indicators
- ✅ **Import/export capabilities** for CSV and YAML formats
- ✅ **Interactive features** with fzf integration
- ✅ **Search functionality** by name and content
- ✅ **Robust error handling** and validation
- ✅ **Comprehensive testing** with unit and integration tests
- ✅ **CLI integration** with version 0.6.0

The module provides a solid foundation for personal task management, project tracking, and list organization, with all specified features implemented according to the roadmap requirements.
