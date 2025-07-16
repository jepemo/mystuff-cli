# mystuff-cli

[![Tests](https://github.com/jepemo/mystuff-cli/actions/workflows/test.yml/badge.svg)](https://github.com/jepemo/mystuff-cli/actions/workflows/test.yml)
[![Code Quality](https://github.com/jepemo/mystuff-cli/actions/workflows/code-quality.yml/badge.svg)](https://github.com/jepemo/mystuff-cli/actions/workflows/code-quality.yml)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A command-line tool for capturing, organizing and retrieving personal knowledge efficiently.

## Features

- **Single binary**: `mystuff`
- **Configurable data directory**: `~/.mystuff` (default) or `$MYSTUFF_HOME`
- **Simple file formats**: JSONL / YAML / Markdown
- **Honors `$EDITOR` and `$PAGER`** for editing and viewing
- **Tests from day one** (unit + integration)
- **fzf integration**: Interactive fuzzy finding for all modules when available
- **GitHub integration**: Import starred repositories from any GitHub user
- **Export/Import**: Lists support CSV and YAML formats
- **Full-text search**: Search across all content types
- **User-friendly error handling**: Clear guidance when directories don't exist

## Installation

```bash
# Install from source
git clone https://github.com/jepemo/mystuff-cli.git
cd mystuff-cli
pip install -e .
```

### Optional Dependencies

- **fzf**: For interactive fuzzy finding. Install with:
  ```bash
  # macOS
  brew install fzf
  # Ubuntu/Debian
  apt install fzf
  # Other systems: see https://github.com/junegunn/fzf#installation
  ```

## Quick Start

1. **Initialize your mystuff directory**:

   ```bash
   mystuff init
   ```

   This creates the directory structure:

   ```
   ~/.mystuff/
   ├── links.jsonl
   ├── meetings/
   ├── journal/
   ├── wiki/
   ├── eval/
   ├── lists/
   └── config.yaml
   ```

2. **Use custom directory**:

   ```bash
   mystuff init --dir /path/to/custom/location
   # OR
   export MYSTUFF_HOME=/path/to/custom/location
   mystuff init
   ```

3. **Force recreation**:
   ```bash
   mystuff init --force
   ```

## Usage

```bash
mystuff --help
mystuff --version
mystuff init --help
```

### Commands

- `mystuff init` - Initialize the mystuff directory structure
- `mystuff link` - Manage links with JSONL storage
  - `mystuff link add --url <URL>` - Add a new link
  - `mystuff link add --import-github-stars <USERNAME>` - Import GitHub stars for a user
  - `mystuff link list` - List all links
  - `mystuff link list --interactive` - Interactive link browser with fzf
  - `mystuff link search <query>` - Search links
  - `mystuff link edit [--url <URL>]` - Edit a link (uses fzf if URL not provided)
  - `mystuff link delete [--url <URL>]` - Delete a link (uses fzf if URL not provided)
- `mystuff meeting` - Manage meeting notes with Markdown files
  - `mystuff meeting add --title <TITLE>` - Add a new meeting note
  - `mystuff meeting list` - List all meeting notes
  - `mystuff meeting list --interactive` - Interactive meeting browser with fzf
  - `mystuff meeting search <query>` - Search meeting notes
  - `mystuff meeting edit [--title <TITLE>]` - Edit a meeting note (uses fzf if title not provided)
  - `mystuff meeting delete [--title <TITLE>]` - Delete a meeting note (uses fzf if title not provided)
- `mystuff journal` - Manage daily journal entries
  - `mystuff journal add [--date <DATE>]` - Add a new journal entry
  - `mystuff journal list` - List all journal entries
  - `mystuff journal edit [--date <DATE>]` - Edit a journal entry
  - `mystuff journal search <query>` - Search journal entries by text or date range
- `mystuff wiki` - Manage topical notes with backlinks
  - `mystuff wiki new --title <TITLE>` - Create a new wiki note
  - `mystuff wiki view [--title <TITLE>]` - View a wiki note
  - `mystuff wiki edit [--title <TITLE>]` - Edit a wiki note
  - `mystuff wiki list` - List all wiki notes
  - `mystuff wiki search <query>` - Search wiki notes by title, tags, or content
  - `mystuff wiki delete [--title <TITLE>]` - Delete a wiki note
- `mystuff eval` - Manage self-evaluation entries
  - `mystuff eval add --name <NAME>` - Add a new evaluation entry
  - `mystuff eval list` - List all evaluations
  - `mystuff eval edit [--name <NAME>]` - Edit an evaluation
  - `mystuff eval delete [--name <NAME>]` - Delete an evaluation
  - `mystuff eval report` - Generate a summary report of evaluations
- `mystuff list` - Manage arbitrary named lists
  - `mystuff list create --name <NAME>` - Create a new list
  - `mystuff list view [--name <NAME>]` - View a list
  - `mystuff list edit [--name <NAME>]` - Edit a list (add/remove/check items)
  - `mystuff list list` - List all available lists
  - `mystuff list search <query>` - Search lists by name or content
  - `mystuff list delete [--name <NAME>]` - Delete a list
  - `mystuff list export [--name <NAME>]` - Export a list to CSV/YAML
  - `mystuff list import` - Import a list from CSV/YAML

#### Link Examples

```bash
# Add a link with full details
mystuff link add --url "https://github.com/example/repo" \
  --title "Example Repository" \
  --description "Sample project repository" \
  --tag "development" --tag "github"

# Add a link with auto-generated title
mystuff link add --url "https://python.org"

# Import GitHub stars for a user
mystuff link add --import-github-stars "torvalds"

# List all links
mystuff link list

# Interactive link browser (requires fzf)
mystuff link list --interactive

# Search for links
mystuff link search "python"

# Filter by tag
mystuff link list --tag "development"

# Edit a link with fzf selection
mystuff link edit

# Edit a specific link
mystuff link edit --url "https://python.org" --title "Python Official Site"

# Delete a link with fzf selection
mystuff link delete

# Delete a specific link
mystuff link delete --url "https://python.org"
```

#### GitHub Stars Import

You can import all starred repositories from a GitHub user:

```bash
# Import all stars from a GitHub user
mystuff link add --import-github-stars "torvalds"

# Import stars from the octocat user (GitHub's demo user)
mystuff link add --import-github-stars "octocat"

# This will:
# - Fetch all starred repositories for the user using GitHub's public API
# - Add them as links with:
#   - Title: repository full name (e.g., "torvalds/linux")
#   - Description: repository description from GitHub
#   - Tags: username and "github"
# - Skip repositories that are already in your links
# - Show progress and summary of imported stars
# - Handle pagination automatically for users with many stars
# - Respect GitHub API rate limits with proper error handling
```

**Note**: This feature uses GitHub's public API and doesn't require authentication. However, it's subject to GitHub's rate limits for unauthenticated requests (60 requests per hour per IP address).

#### Meeting Examples

```bash
# Add a meeting with full details
mystuff meeting add --title "Team Standup" \
  --date "2025-07-14" \
  --participants "Alice, Bob, Charlie" \
  --tag "standup" --tag "team" \
  --body "Daily standup meeting"

# Add a meeting with default date (today)
mystuff meeting add --title "Project Review" \
  --participants "Alice, David"

# Add a meeting with template
mystuff meeting add --title "Weekly Planning" \
  --template /path/to/meeting-template.md

# List all meetings
mystuff meeting list

# Interactive meeting browser (requires fzf)
mystuff meeting list --interactive

# Search meetings
mystuff meeting search "Alice"

# Filter by tag
mystuff meeting list --tag "standup"

# Filter by date
mystuff meeting list --date "2025-07-14"

# Edit a meeting with fzf selection
mystuff meeting edit

# Edit a specific meeting
mystuff meeting edit --title "Team Standup" --date "2025-07-14"

# Delete a meeting with fzf selection
mystuff meeting delete

# Delete a specific meeting
mystuff meeting delete --title "Team Standup" --date "2025-07-14"
```

#### Journal Examples

```bash
# Add a journal entry for today
mystuff journal add

# Add a journal entry for a specific date
mystuff journal add --date "2025-07-16"

# List all journal entries
mystuff journal list

# Search journal entries
mystuff journal search "project"

# Edit today's journal entry
mystuff journal edit

# Edit a specific date's entry
mystuff journal edit --date "2025-07-16"
```

#### Wiki Examples

```bash
# Create a new wiki note
mystuff wiki new --title "Python Tips"

# View a wiki note (uses fzf if title not provided)
mystuff wiki view --title "Python Tips"

# Edit a wiki note
mystuff wiki edit --title "Python Tips"

# List all wiki notes
mystuff wiki list

# Search wiki notes
mystuff wiki search "python"

# Delete a wiki note
mystuff wiki delete --title "Python Tips"
```

#### Evaluation Examples

```bash
# Add a new evaluation entry
mystuff eval add --name "Q1 2025 Review"

# List all evaluations
mystuff eval list

# Edit an evaluation
mystuff eval edit --name "Q1 2025 Review"

# Generate a report
mystuff eval report

# Delete an evaluation
mystuff eval delete --name "Q1 2025 Review"
```

#### List Examples

```bash
# Create a new list
mystuff list create --name "reading-list"

# View a list
mystuff list view --name "reading-list"

# Edit a list (add/remove/check items)
mystuff list edit --name "reading-list"

# List all available lists
mystuff list list

# Search lists
mystuff list search "reading"

# Export a list to CSV
mystuff list export --name "reading-list" --format csv

# Import a list from file
mystuff list import --file mylist.csv --name "imported-list"

# Delete a list
mystuff list delete --name "reading-list"
```

### fzf Integration

If you have `fzf` installed, mystuff provides enhanced interactive features:

- **Interactive browsing**: Use `--interactive` flag with `list` commands
- **Smart selection**: Edit/delete commands use fzf when parameters are omitted
- **Rich previews**: See content previews in the selection interface

```bash
# Interactive browsing
mystuff link list --interactive
mystuff meeting list --interactive

# Quick edit/delete with fuzzy selection
mystuff link edit         # Select link with fzf
mystuff meeting edit      # Select meeting with fzf
mystuff wiki edit         # Select wiki note with fzf
mystuff list edit         # Select list with fzf
```

## Development

### Running Tests

```bash
# Run all tests using the test script
./run_tests.sh

# Or run individual test files
python tests/test_init_simple.py
python tests/test_link.py
python tests/test_meeting.py
python tests/test_journal_simple.py
python tests/test_wiki_simple.py
python tests/test_eval_simple.py
python tests/test_lists_simple.py
python tests/test_github_stars.py
python tests/test_error_handling.py
python tests/test_fzf_integration.py

# Install with development dependencies
pip install -e ".[dev]"

# Run with pytest (if installed)
pytest tests/ -v
```

### Code Quality

```bash
# Format code
black mystuff/ tests/

# Check linting
flake8 mystuff/ tests/

# Type checking
mypy mystuff/
```

### GitHub Actions

This project includes several GitHub Actions workflows:

- **Tests** (`test.yml`): Runs all tests on multiple Python versions (3.8-3.12)
- **Code Quality** (`code-quality.yml`): Checks formatting, linting, and type hints
- **Release** (`release.yml`): Automatically creates releases and publishes to PyPI when tags are pushed

### Making a Release

```bash
# Create and push a new tag
git tag v0.2.1
git push origin v0.2.1

# This will automatically:
# 1. Run all tests
# 2. Create a GitHub release
# 3. Publish to PyPI (if configured)
```

## Roadmap

See [docs/PLAN.md](docs/PLAN.md) for the full development roadmap.

Current status: **v0.6 - Lists** ✅

### Completed Features

- ✅ **v0.1** - Basic CLI structure and init command
- ✅ **v0.2** - Link management with JSONL storage
- ✅ **v0.3** - Meeting notes with Markdown files
- ✅ **v0.4** - Journal entries for daily notes
- ✅ **v0.5** - Wiki notes with backlinks
- ✅ **v0.6** - Self-evaluation system
- ✅ **v0.7** - Lists management with full CRUD operations
- ✅ **GitHub Stars Import** - Import starred repositories from GitHub users
- ✅ **Enhanced Error Handling** - User-friendly error messages and guidance
