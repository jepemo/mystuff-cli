# CLI Reference

Complete command reference for mystuff-cli.

## Global Options

```bash
mystuff --version    # Show version and exit
mystuff --help       # Show help message
```

## Core Commands

### `mystuff init`

Initialize the mystuff directory structure.

```bash
mystuff init [OPTIONS]
```

**Options:**

- `--dir, -d TEXT`: Directory path for mystuff data (default: `~/.mystuff` or `$MYSTUFF_HOME`)
- `--force, -f`: Force creation even if directory exists

**Examples:**

```bash
mystuff init                           # Create ~/.mystuff
mystuff init --dir /custom/path        # Create custom directory
mystuff init --force                   # Overwrite existing directory
export MYSTUFF_HOME=/custom && mystuff init  # Use environment variable
```

---

## Content Management

### `mystuff link`

Manage links with JSONL storage.

#### `mystuff link add`

Add a new link to your collection.

```bash
mystuff link add [OPTIONS]
```

**Options:**

- `--url TEXT`: URL of the link (required)
- `--title TEXT`: Title of the link (auto-generated if not provided)
- `--description TEXT`: Description of the link
- `--tag TEXT`: Tags for categorization (can be used multiple times)
- `--import-github-stars TEXT`: Import starred repositories from a GitHub user

**Examples:**

```bash
mystuff link add --url "https://python.org"
mystuff link add --url "https://github.com/example/repo" --title "Example Repo" --description "Cool project" --tag "dev" --tag "python"
mystuff link add --import-github-stars "torvalds"
```

#### `mystuff link list`

List all links.

```bash
mystuff link list [OPTIONS]
```

**Options:**

- `--tag TEXT`: Filter by tag
- `--interactive`: Use fzf for interactive browsing (requires fzf)

#### `mystuff link search`

Search links by title, description, or URL.

```bash
mystuff link search [OPTIONS] QUERY
```

#### `mystuff link edit`

Edit an existing link.

```bash
mystuff link edit [OPTIONS]
```

**Options:**

- `--url TEXT`: URL of the link to edit (uses fzf selection if not provided)
- `--title TEXT`: New title
- `--description TEXT`: New description
- `--tag TEXT`: Add tags

#### `mystuff link delete`

Delete a link.

```bash
mystuff link delete [OPTIONS]
```

**Options:**

- `--url TEXT`: URL of the link to delete (uses fzf selection if not provided)

---

### `mystuff meeting`

Manage meeting notes with Markdown files.

#### `mystuff meeting add`

Add a new meeting note.

```bash
mystuff meeting add [OPTIONS]
```

**Options:**

- `--title TEXT`: Title of the meeting (required)
- `--date TEXT`: Date in YYYY-MM-DD format (defaults to today)
- `--participants TEXT`: Comma-separated list of participants
- `--body TEXT`: Meeting content or agenda
- `--template TEXT`: Path to template file for pre-filling
- `--tag TEXT`: Tags for categorization (can be used multiple times)
- `--no-edit`: Don't prompt to edit after creation

**Examples:**

```bash
mystuff meeting add --title "Team Standup"
mystuff meeting add --title "Project Review" --date "2025-07-23" --participants "Alice,Bob" --tag "planning"
mystuff meeting add --title "Weekly Planning" --template ./meeting-template.md --no-edit
```

#### `mystuff meeting list`

List all meeting notes.

```bash
mystuff meeting list [OPTIONS]
```

**Options:**

- `--tag TEXT`: Filter by tag
- `--date TEXT`: Filter by date (YYYY-MM-DD)
- `--interactive`: Use fzf for interactive browsing

#### `mystuff meeting search`

Search meeting notes.

```bash
mystuff meeting search [OPTIONS] QUERY
```

#### `mystuff meeting edit`

Edit a meeting note.

```bash
mystuff meeting edit [OPTIONS]
```

**Options:**

- `--title TEXT`: Title of meeting to edit (uses fzf if not provided)
- `--date TEXT`: Date of meeting to edit

#### `mystuff meeting delete`

Delete a meeting note.

```bash
mystuff meeting delete [OPTIONS]
```

**Options:**

- `--title TEXT`: Title of meeting to delete (uses fzf if not provided)
- `--date TEXT`: Date of meeting to delete

---

### `mystuff journal`

Manage daily journal entries.

#### `mystuff journal add`

Add a new journal entry.

```bash
mystuff journal add [OPTIONS]
```

**Options:**

- `--date TEXT`: Date in YYYY-MM-DD format (defaults to today)
- `--body TEXT`: Journal entry content
- `--tag TEXT`: Tags for categorization (can be used multiple times)
- `--no-edit`: Don't prompt to edit after creation

**Examples:**

```bash
mystuff journal add                                    # Today's entry
mystuff journal add --date "2025-07-23"              # Specific date
mystuff journal add --body "Great day!" --no-edit    # Quick entry
```

#### `mystuff journal list`

List all journal entries.

```bash
mystuff journal list [OPTIONS]
```

**Options:**

- `--no-interactive`: Disable interactive features
- `--date-range TEXT`: Filter by date range (YYYY-MM-DD:YYYY-MM-DD)

#### `mystuff journal search`

Search journal entries.

```bash
mystuff journal search [OPTIONS] QUERY
```

**Options:**

- `--no-interactive`: Disable interactive features
- `--date-range TEXT`: Search within date range

#### `mystuff journal edit`

Edit a journal entry.

```bash
mystuff journal edit [OPTIONS]
```

**Options:**

- `--date TEXT`: Date of entry to edit (defaults to today)

---

### `mystuff wiki`

Manage topical notes with backlinks.

#### `mystuff wiki new`

Create a new wiki note.

```bash
mystuff wiki new [OPTIONS] TITLE
```

**Options:**

- `--tag TEXT`: Tags for categorization (can be used multiple times)
- `--alias TEXT`: Aliases for the note (can be used multiple times)
- `--body TEXT`: Content for the wiki note
- `--no-edit`: Don't open editor after creation

**Examples:**

```bash
mystuff wiki new "Python Tips"
mystuff wiki new "API Design" --tag "programming" --tag "design" --alias "REST API"
mystuff wiki new "Quick Note" --body "Short content" --no-edit
```

#### `mystuff wiki view`

View a wiki note.

```bash
mystuff wiki view [OPTIONS] [TITLE]
```

**Options:**

- Uses fzf selection if title not provided

#### `mystuff wiki edit`

Edit a wiki note.

```bash
mystuff wiki edit [OPTIONS] [TITLE]
```

**Options:**

- Uses fzf selection if title not provided

#### `mystuff wiki list`

List all wiki notes.

```bash
mystuff wiki list [OPTIONS]
```

**Options:**

- `--no-interactive`: Disable interactive features

#### `mystuff wiki search`

Search wiki notes.

```bash
mystuff wiki search [OPTIONS] QUERY
```

**Options:**

- `--no-interactive`: Disable interactive features

#### `mystuff wiki delete`

Delete a wiki note.

```bash
mystuff wiki delete [OPTIONS] [TITLE]
```

**Options:**

- Uses fzf selection if title not provided

---

### `mystuff eval`

Manage self-evaluation entries.

#### `mystuff eval add`

Add a new evaluation entry.

```bash
mystuff eval add [OPTIONS]
```

**Options:**

- `--category TEXT`: Evaluation category (required, e.g., 'productivity', 'health')
- `--score INTEGER`: Numeric score 1-10 (required)
- `--date TEXT`: Date in YYYY-MM-DD format (defaults to today)
- `--comments TEXT`: Optional comments

**Examples:**

```bash
mystuff eval add --category "productivity" --score 8 --comments "Great focus today"
mystuff eval add --category "health" --score 7 --date "2025-07-22"
```

#### `mystuff eval list`

List all evaluations.

```bash
mystuff eval list [OPTIONS]
```

**Options:**

- `--no-interactive`: Disable interactive features
- `--category TEXT`: Filter by category
- `--date-range TEXT`: Filter by date range

#### `mystuff eval report`

Generate evaluation reports.

```bash
mystuff eval report [OPTIONS]
```

**Options:**

- `--category TEXT`: Generate report for specific category
- `--date-range TEXT`: Generate report for date range

#### `mystuff eval edit`

Edit an evaluation entry.

```bash
mystuff eval edit [OPTIONS]
```

**Options:**

- `--category TEXT`: Category of evaluation to edit
- `--date TEXT`: Date of evaluation to edit

#### `mystuff eval delete`

Delete an evaluation entry.

```bash
mystuff eval delete [OPTIONS]
```

**Options:**

- `--category TEXT`: Category of evaluation to delete
- `--date TEXT`: Date of evaluation to delete

---

### `mystuff list`

Manage arbitrary named lists.

#### `mystuff list create`

Create a new list.

```bash
mystuff list create [OPTIONS]
```

**Options:**

- `--name TEXT`: Name of the list (required)
- `--description TEXT`: Description of the list

**Examples:**

```bash
mystuff list create --name "reading-list" --description "Books to read"
mystuff list create --name "todo"
```

#### `mystuff list view`

View a list.

```bash
mystuff list view [OPTIONS]
```

**Options:**

- `--name TEXT`: Name of list to view (uses fzf if not provided)

#### `mystuff list edit`

Edit a list (add/remove/check items).

```bash
mystuff list edit [OPTIONS]
```

**Options:**

- `--name TEXT`: Name of list to edit (uses fzf if not provided)
- `--item TEXT`: Add an item to the list

#### `mystuff list list`

List all available lists.

```bash
mystuff list list
```

#### `mystuff list search`

Search lists by name or content.

```bash
mystuff list search [OPTIONS] QUERY
```

#### `mystuff list delete`

Delete a list.

```bash
mystuff list delete [OPTIONS]
```

**Options:**

- `--name TEXT`: Name of list to delete (uses fzf if not provided)

#### `mystuff list export`

Export a list to CSV/YAML.

```bash
mystuff list export [OPTIONS]
```

**Options:**

- `--name TEXT`: Name of list to export (uses fzf if not provided)
- `--format TEXT`: Export format (csv, yaml)
- `--output TEXT`: Output file path

#### `mystuff list import`

Import a list from CSV/YAML.

```bash
mystuff list import [OPTIONS]
```

**Options:**

- `--file TEXT`: Path to file to import (required)
- `--name TEXT`: Name for the imported list (required)

---

### `mystuff sync`

Execute custom sync commands from configuration.

#### `mystuff sync run`

Execute all sync commands defined in config.yaml.

```bash
mystuff sync run [OPTIONS]
```

**Options:**

- `--dry-run`: Show commands without executing them
- `--verbose`: Show detailed output during execution
- `--continue-on-error`: Continue executing even if one command fails

**Examples:**

```bash
mystuff sync run                        # Execute all sync commands
mystuff sync run --dry-run              # Preview without executing
mystuff sync run --verbose              # Detailed output
mystuff sync run --continue-on-error    # Don't stop on errors
mystuff sync run --dry-run --verbose    # Combined flags
```

#### `mystuff sync list-commands`

List all sync commands defined in config.yaml.

```bash
mystuff sync list-commands
```

---

## Configuration

### Directory Structure

After running `mystuff init`, your directory will contain:

```
~/.mystuff/
├── links.jsonl          # Link storage
├── meetings/            # Meeting notes (Markdown)
├── journal/             # Journal entries (Markdown)
├── wiki/                # Wiki notes (Markdown)
├── eval/                # Evaluation entries (YAML)
├── lists/               # Lists (YAML)
└── config.yaml          # Configuration file
```

### config.yaml

Basic configuration structure:

```yaml
data_directory: "/home/user/.mystuff"
editor: "vim"
pager: "less"
settings:
  default_tags: []
  date_format: "%Y-%m-%d"
  time_format: "%H:%M:%S"
sync:
  commands:
    - echo "Sync data"
```

### Environment Variables

- `MYSTUFF_HOME`: Override default data directory (`~/.mystuff`)
- `EDITOR`: Text editor for editing notes (fallback: vim)
- `PAGER`: Pager for viewing content (fallback: less)

---

## Interactive Features (fzf)

Many commands support interactive selection when `fzf` is installed:

- **List browsing**: Use `--interactive` flag with list commands
- **Smart selection**: Edit/delete commands use fzf when IDs not provided
- **Preview support**: See content previews in selection interface

**Install fzf:**

```bash
# macOS
brew install fzf

# Ubuntu/Debian
apt install fzf

# See: https://github.com/junegunn/fzf#installation
```

---

## Examples & Workflows

### Daily Workflow

```bash
# Morning review
mystuff journal add --body "Today's goals: ..."

# During the day
mystuff link add --url "https://interesting-article.com"
mystuff meeting add --title "Client Call" --participants "Alice,Bob"

# Evening sync
mystuff sync run
```

### Research Workflow

```bash
# Collect information
mystuff link add --import-github-stars "torvalds"
mystuff wiki new "Linux Kernel" --tag "research"

# Organize
mystuff list create --name "research-papers"
mystuff list edit --name "research-papers" --item "Advanced Scheduling"

# Review
mystuff eval add --category "research" --score 9 --comments "Made good progress"
```

### Team Workflows

```bash
# Meeting preparation
mystuff meeting add --title "Sprint Planning" --template ./sprint-template.md

# Knowledge sharing
mystuff wiki new "Team Conventions" --tag "team" --tag "process"

# Follow-ups
mystuff list create --name "action-items"
mystuff journal add --body "Discussed new API design with team"
```
