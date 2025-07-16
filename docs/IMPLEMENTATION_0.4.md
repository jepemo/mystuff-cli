# Wiki Module (0.4)

## Overview

The Wiki module enables users to create and manage topical notes with interconnected references through backlinks. Each note is stored as a Markdown file with YAML front-matter and supports automatic backlink management for creating a connected knowledge base.

## Features

- **Topical notes**: Create notes on specific topics with titles, tags, and aliases
- **Backlink system**: Automatic detection and management of wiki-style links `[[Note Title]]`
- **Aliases**: Multiple names for the same note for easier reference
- **Full-text search**: Search notes by title, content, tags, or aliases
- **ASCII graph visualization**: Display backlink relationships in a simple text format
- **Interactive selection**: Use `fzf` for interactive browsing and selection
- **Editor integration**: Opens notes in `$EDITOR` for editing

## Commands

### `mystuff wiki new`

Create a new wiki note with a title, optional tags, and aliases.

```bash
# Create a basic note
mystuff wiki new "Project Overview"

# Create note with tags and aliases
mystuff wiki new "Team Structure" --tag "team" --tag "organization" --alias "team-org"

# Create note with content
mystuff wiki new "Development Process" --body "Our development workflow..."

# Create note without opening editor
mystuff wiki new "Quick Note" --body "Brief content" --no-edit
```

**Options:**

- `--tag`: Tags for categorization (can be used multiple times)
- `--alias`: Aliases for the note (can be used multiple times)
- `--body`: Content for the note
- `--no-edit`: Don't open editor after creation

### `mystuff wiki view`

View the content of a wiki note or display its backlink graph.

```bash
# View note content
mystuff wiki view "Project Overview"

# View using alias
mystuff wiki view "overview"

# Display backlink graph
mystuff wiki view "Project Overview" --graph
```

**Options:**

- `--graph`: Display ASCII graph of backlinks instead of content

### `mystuff wiki edit`

Edit an existing wiki note. If the note doesn't exist, offers to create it.

```bash
# Edit existing note
mystuff wiki edit "Project Overview"

# Edit using alias
mystuff wiki edit "overview"

# Edit non-existent note (will offer to create)
mystuff wiki edit "New Note"
```

### `mystuff wiki delete`

Delete a wiki note with optional confirmation.

```bash
# Delete with confirmation
mystuff wiki delete "Old Note"

# Force delete without confirmation
mystuff wiki delete "Old Note" --force
```

**Options:**

- `--force, -f`: Force deletion without confirmation

### `mystuff wiki list`

List all wiki notes with interactive selection if `fzf` is available.

```bash
# List all notes
mystuff wiki list

# List without interactive selection
mystuff wiki list --no-interactive
```

**Options:**

- `--no-interactive`: Disable fzf selection even if available

### `mystuff wiki search`

Search wiki notes by title, content, tags, or aliases.

```bash
# Search by text
mystuff wiki search "project"

# Search with backlink graph display
mystuff wiki search "team" --graph

# Search without interactive selection
mystuff wiki search "process" --no-interactive
```

**Options:**

- `--graph`: Display ASCII graph of backlinks for results
- `--no-interactive`: Disable fzf selection even if available

## File Format

Wiki notes are stored as Markdown files in `~/.mystuff/wiki/` with the following structure:

```
~/.mystuff/wiki/
├── project-overview.md
├── team-structure.md
├── development-process.md
└── ...
```

Each file contains YAML front-matter with metadata:

```markdown
---
title: "Project Overview"
tags:
  - project
  - overview
aliases:
  - overview
  - project-summary
backlinks:
  - team-structure
  - development-process
---

# Project Overview

This note provides a high-level overview of the project, including goals, milestones, and key stakeholders.

## Key Points

- The project aims to improve productivity
- Collaboration is a core focus
- Related to [[Team Structure]] and [[Development Process]]

## References

- [[Team Structure]] - How our team is organized
- [[Development Process]] - Our development workflow
```

## Backlink System

### Wiki Links

Use double square brackets to create links between notes:

```markdown
This note references [[Another Note]] and [[Team Structure|our team]].
```

### Automatic Backlink Updates

- Backlinks are automatically detected and updated when notes are saved
- The system scans for `[[Note Title]]` patterns in content
- Backlinks are stored in the `backlinks` field of the front-matter
- Updates happen after any edit operation

### Link Resolution

Links are resolved in the following order:

1. Exact title match
2. Alias match
3. Slugified filename match

## ASCII Graph Visualization

The `--graph` option displays backlink relationships in a simple text format:

```
Project Overview
  ├── Development Process
  └── Team Structure
```

## Usage Examples

### Creating a Knowledge Base

```bash
# Create main project note
mystuff wiki new "Project Overview" --tag "project" --alias "overview"

# Create related notes with cross-references
mystuff wiki new "Team Structure" --body "This supports the [[Project Overview]]"
mystuff wiki new "Development Process" --body "Process for [[Project Overview]]"

# Edit notes to add more connections
mystuff wiki edit "Project Overview"
# Add: "See [[Team Structure]] and [[Development Process]]"
```

### Exploring Connections

```bash
# View backlink graph
mystuff wiki view "Project Overview" --graph

# Search with graph display
mystuff wiki search "project" --graph

# Find all notes about a topic
mystuff wiki search "team"
```

### Daily Wiki Workflow

```bash
# Quick note creation
mystuff wiki new "Meeting Notes $(date +%Y-%m-%d)" --tag "meeting"

# Reference existing notes
mystuff wiki edit "Meeting Notes 2025-07-16"
# Add: "Discussed [[Project Overview]] and [[Team Structure]]"

# Explore connections
mystuff wiki view "Project Overview" --graph
```

## Integration Features

### fzf Integration

When `fzf` is available, `list` and `search` commands provide interactive selection:

- Browse notes with title, tags, and aliases
- Select and open notes directly in editor
- Fuzzy search through note metadata

### Editor Integration

Respects the `$EDITOR` environment variable:

- Opens notes for editing after creation (unless `--no-edit` is used)
- Allows editing existing notes
- Automatically updates backlinks after editing
- Falls back to `vim` if `$EDITOR` is not set

### Filename Generation

- Titles are automatically converted to URL-friendly slugs
- Spaces become hyphens
- Special characters are removed
- Multiple consecutive hyphens are collapsed

## Testing

The wiki module includes comprehensive tests:

- Unit tests for all core functions
- Integration tests for CLI commands
- Tests for backlink detection and updating
- Tests for search functionality
- Tests for file operations and slugification

Run tests with:

```bash
./run_tests.sh
```

## Implementation Details

- **Storage**: Individual Markdown files per note with slugified filenames
- **Metadata**: YAML front-matter for structured data
- **Backlink detection**: Regex pattern matching for `[[Note Title]]` syntax
- **Search**: Full-text search through title, content, tags, and aliases
- **Graph generation**: Simple ASCII tree visualization
- **Link resolution**: Multi-level matching (title, alias, slug)
- **Automatic updates**: Backlinks updated after edit operations

## Advanced Features

### Alias System

Notes can have multiple aliases for easier reference:

```bash
# Create note with multiple aliases
mystuff wiki new "Application Programming Interface" --alias "API" --alias "api"

# Reference by any alias
mystuff wiki view "API"
mystuff wiki edit "api"
```

### Backlink Maintenance

The system automatically maintains bidirectional links:

- When Note A links to Note B, Note B's backlinks include Note A
- Backlinks are updated whenever any note is edited
- Broken links are automatically cleaned up when notes are deleted

### Cross-Reference Patterns

Support for various wiki link formats:

- `[[Note Title]]` - Simple link
- `[[Note Title|Display Text]]` - Link with custom display text
- Case-insensitive matching for robustness
