# Daily Journal Module (0.3)

## Overview

The Daily Journal module enables users to maintain a personal journal with daily entries stored as Markdown files with YAML front-matter. Each entry is automatically dated and can be tagged for easy categorization and search.

## Features

- **Daily entries**: One entry per day with automatic date stamping
- **YAML front-matter**: Structured metadata including date and tags
- **Full-text search**: Search entries by content or tags
- **Date range filtering**: Filter entries by date ranges
- **Interactive selection**: Use `fzf` for interactive browsing and selection
- **Editor integration**: Opens entries in `$EDITOR` for editing

## Commands

### `mystuff journal add`

Add a new journal entry for today or a specific date.

```bash
# Add entry for today (opens in editor)
mystuff journal add

# Add entry with specific date and content
mystuff journal add --date "2025-07-16" --body "Today was productive"

# Add entry with tags
mystuff journal add --tag "work" --tag "meeting" --body "Team meeting went well"

# Add entry without opening editor
mystuff journal add --body "Quick note" --no-edit
```

**Options:**

- `--date`: Date in YYYY-MM-DD format (defaults to today)
- `--body`: Free-text content for the entry
- `--tag`: Tags for categorization (can be used multiple times)
- `--no-edit`: Don't open editor after creation

### `mystuff journal list`

List all journal entries, newest first.

```bash
# List all entries
mystuff journal list

# List with interactive selection (if fzf available)
mystuff journal list

# List without interactive selection
mystuff journal list --no-interactive

# List limited number of entries
mystuff journal list --limit 10

# List entries in date range
mystuff journal list --range "2025-07-01:2025-07-31"
```

**Options:**

- `--limit, -l`: Limit number of entries displayed
- `--range`: Filter by date range (YYYY-MM-DD:YYYY-MM-DD)
- `--no-interactive`: Disable fzf selection even if available

### `mystuff journal edit`

Edit an existing journal entry.

```bash
# Edit today's entry
mystuff journal edit

# Edit specific date
mystuff journal edit --date "2025-07-15"
```

**Options:**

- `--date`: Date of entry to edit (defaults to today)

### `mystuff journal search`

Search journal entries by content or tags.

```bash
# Search by text content
mystuff journal search "meeting"

# Search with date range
mystuff journal search "project" --range "2025-07-01:2025-07-31"

# Search without interactive selection
mystuff journal search "work" --no-interactive
```

**Options:**

- `--range`: Filter by date range before searching
- `--no-interactive`: Disable fzf selection even if available

## File Format

Journal entries are stored as Markdown files in `~/.mystuff/journal/` with the following structure:

```
~/.mystuff/journal/
├── 2025-07-15.md
├── 2025-07-16.md
└── ...
```

Each file contains YAML front-matter with metadata:

```markdown
---
date: "2025-07-16"
tags:
  - programming
  - mystuff
---

## Journal Entry

Today I completed the implementation of the journal module for mystuff-cli. It was a productive day of programming.

## Reflections

- The module integrates well with the existing architecture
- Tests are all passing
- Users can now maintain daily journals easily

## Tomorrow's Goals

- Document the new feature
- Consider adding more advanced search capabilities
```

## Integration Features

### fzf Integration

When `fzf` is available, `list` and `search` commands provide interactive selection:

- Browse entries with preview
- Select and open entries directly in editor
- Fuzzy search through entry previews

### Editor Integration

Respects the `$EDITOR` environment variable:

- Opens entries for editing after creation (unless `--no-edit` is used)
- Allows editing existing entries
- Falls back to `vim` if `$EDITOR` is not set

## Usage Examples

### Daily Workflow

```bash
# Morning: Add today's entry
mystuff journal add --body "Goals for today: finish journal module, write tests"

# During day: Edit entry to add progress
mystuff journal edit

# Evening: Search for yesterday's entry
mystuff journal search "yesterday" --range "2025-07-15:2025-07-15"
```

### Weekly Review

```bash
# Review last week's entries
mystuff journal list --range "2025-07-08:2025-07-14"

# Search for specific topics in the week
mystuff journal search "meeting" --range "2025-07-08:2025-07-14"
```

## Testing

The journal module includes comprehensive tests:

- Unit tests for all core functions
- Integration tests for CLI commands
- Tests for date parsing and filtering
- Tests for search functionality
- Tests for file operations

Run tests with:

```bash
./run_tests.sh
```

## Implementation Details

- **Storage**: Individual Markdown files per day
- **Metadata**: YAML front-matter for structured data
- **Search**: Full-text search through content and tags
- **Date handling**: Strict YYYY-MM-DD format validation
- **Error handling**: Graceful handling of missing files and invalid dates
- **Interactive features**: Optional fzf integration for enhanced UX
