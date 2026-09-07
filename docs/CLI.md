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

Capture sources and compound them into an audited, interconnected wiki.

#### `mystuff wiki ingest`

Capture a URL into immutable raw storage and ask the configured agent to
synthesize or update wiki pages.

```bash
mystuff wiki ingest [OPTIONS] URL
```

**Options:**

- `--capture-only`: Download and normalize the source without running the agent.
- `--dry-run`: Generate and validate the structured change set without applying it.
- `--reprocess`: Run synthesis again when an identical capture is already processed.
- `--codex-command TEXT`: Override the configured Codex executable for this run.

#### `mystuff wiki process`

Process an existing immutable capture by the source id shown by `wiki status`,
without downloading it again. It accepts `--dry-run`, `--reprocess`, and
`--codex-command`.

#### `mystuff wiki process-batch`

Process several related source ids in one synthesis run. This is preferable for
small legacy notes that belong to the same topic because page boundaries and
links are decided together.

#### `mystuff wiki status`

List captured source ids and their `pending`, `processed`, or `error` state.

#### `mystuff wiki audit`

Validate frontmatter, sources, links, aliases, public/private boundaries,
staleness, orphans, and copied source spans. `--full` compares every page
against its captured sources instead of only recently changed pages.

#### `mystuff wiki rebuild-index`

Regenerate page digests, outgoing links, backlinks, and `metadata/index.json`
from the Markdown content.

#### `mystuff wiki remove`

Remove a synthesized page by stable id, slug, or generated web URL. The command
also deletes captured raw sources that no remaining page uses. Shared sources
are preserved, and incoming links are converted to plain text so the wiki does
not acquire broken links.

```bash
mystuff wiki remove wiki-http --dry-run
mystuff wiki remove http --force
mystuff wiki remove https://example.com/wiki/http.html
```

Use `--dry-run` to inspect the affected sources and incoming pages, and
`--force` to skip confirmation. The central `wiki-index` page cannot be removed.

#### `mystuff wiki migrate-legacy`

Capture files from the old wiki tree as immutable `legacy-note` sources. The
original files are preserved and are not automatically published.

#### `mystuff wiki new`

Create a manually authored page in `wiki/content/`.

```bash
mystuff wiki new [OPTIONS] TITLE
```

**Options:**

- `--tag TEXT`: Tags for categorization (can be used multiple times)
- `--alias TEXT`: Aliases for the note (can be used multiple times)
- `--body TEXT`: Content for the wiki note
- `--no-edit`: Don't open editor after creation
- `--public / --private`: Control static-site publication (default: public)

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

The title, alias, or slug is required.

#### `mystuff wiki edit`

Edit a wiki note.

```bash
mystuff wiki edit [OPTIONS] [TITLE]
```

The title, alias, or slug is required.

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

Delete a wiki note without source cleanup. Prefer `wiki remove` for synthesized
pages.

```bash
mystuff wiki delete [OPTIONS] [TITLE]
```

Use `--force` to skip deletion confirmation.

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

### `mystuff learn`

Manage track-based learning content and progress.

Track layout:

```text
learning/
  lessons/
    README.md
    <track_id>/
      TRACK.md
      001.md
      002.md
```

Track metadata is loaded from each `TRACK.md`. Lesson metadata is loaded from
the frontmatter of each `001.md`, `002.md`, and so on. The catalog groups
content by `classification`, so the default navigation is
`classification -> track -> lesson`.

#### `mystuff learn`

Show a compact summary of the current learning state: visible tracks, open
tracks, available tracks, locked tracks, completed lessons, and current
lessons.

```bash
mystuff learn
```

#### `mystuff learn track`

Inspect one track. Without a track id, it opens an interactive selector for
published tracks.

```bash
mystuff learn track [TRACK_ID]
```

Track lesson output is plain text without a header:
`status seq lesson`.

**Options:**

- `--list`: Print published tracks as plain text
- `--include-private`: Include private lessons
- `--selector, --prompt`: Use the full-screen native selector, or the compact numbered search prompt

#### `mystuff learn list`

List visible classifications and tracks, or lessons inside a specific track.

```bash
mystuff learn list [OPTIONS]
```

**Options:**

- `--track TEXT`: List lessons inside a specific track
- `--classification TEXT`: Filter to a specific classification slug
- `--completed, -c`: Show only completed tracks or lessons
- `--pending, -p`: Show only pending tracks or lessons
- `--difficulty, -d TEXT`: Filter by lesson difficulty
- `--tree, -t`: Render the catalog as a tree
- `--include-drafts`: Include draft tracks
- `--include-private`: Include private lessons

#### `mystuff learn start`

Start or resume one learning track. A first start may select a private or draft
track whose dependencies are complete: the learning agent plans it, then
reviews and publishes only lesson 001. Switching focus asks for confirmation
and preserves completed-history.

```bash
mystuff learn start [OPTIONS] [LESSON]
```

**Options:**

- `--selector, --prompt`: Use the full-screen native selector, or the compact numbered search prompt

**Examples:**

```bash
mystuff learn start foundations
mystuff learn start foundations/001
mystuff learn start 438
```

When you pass a track id, `mystuff learn start` resumes from its first
uncompleted lesson. It never makes a cursor active until that lesson has passed
the reviewed-publication gate.

#### `mystuff learn current`

Open the single active lesson in your editor or published website. If it is the
next private lesson, it is reviewed and validated immediately before opening.

```bash
mystuff learn current [REFERENCE] [--web]
```

**Options:**

- `--web`: Open the lesson in the generated website
- `--selector, --prompt`: Use the full-screen native selector, or the compact numbered search prompt

#### `mystuff learn next`

Complete the single active lesson and move within the same track. The next
lesson is reviewed and validated before progress is written, so a failed review
leaves the current lesson unchanged. `learn complete` remains the explicit
operation that records completion without this advance-and-prepare step.

```bash
mystuff learn next [REFERENCE] [--web]
```

**Options:**

- `--web`: Open the next lesson in the generated website
- `--selector, --prompt`: Use the full-screen native selector, or the compact numbered search prompt

#### `mystuff learn stats`

Show track and lesson progress statistics.

```bash
mystuff learn stats [--include-drafts] [--include-private]
```

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
├── wiki/
│   ├── raw/             # Immutable originals and extracted text
│   ├── content/         # Synthesized Markdown pages and index.md
│   ├── metadata/        # Sources, page digests, runs, and audits
│   └── EDITORIAL.md     # Provider-neutral writing contract
├── eval/                # Evaluation entries (YAML)
├── lists/               # Lists (YAML)
├── learning/
│   ├── lessons/         # Tracks and lesson markdown
│   └── metadata.yaml    # Learning progress (schema v2)
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
ai:
  default_provider: codex
  providers:
    codex:
      command: ["codex"]
      model: null
      reasoning_effort: null
      profile: null
  tasks:
    learning:
      provider: codex
    wiki:
      provider: codex
wiki:
  language: English
  capture:
    timeout_seconds: 20
    max_bytes: 20000000
    resolvers:
      x: []
sync:
  commands:
    - echo "Sync data"
generate:
  web:
    output: "~/mystuff_web"
    url: "https://example.com/mystuff"
```

### Environment Variables

- `MYSTUFF_HOME`: Override default data directory (`~/.mystuff`)
- `EDITOR`: Text editor for editing notes (fallback: vim)
- `PAGER`: Pager for viewing content (fallback: less)

---

## Interactive Features

Learning commands use a built-in fuzzy selector. Use `--prompt` on `learn`
selection commands to switch to the compact numbered search prompt: type a
search term to filter, then choose a visible number.

Other commands support interactive selection when `fzf` is installed:

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
