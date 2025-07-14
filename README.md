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
- **fzf integration**: Interactive fuzzy finding for links and meetings when available

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

#### Link Examples

```bash
# Add a link with full details
mystuff link add --url "https://github.com/example/repo" \
  --title "Example Repository" \
  --description "Sample project repository" \
  --tag "development" --tag "github"

# Add a link with auto-generated title
mystuff link add --url "https://python.org"

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
mystuff link delete       # Select link to delete with fzf
mystuff meeting delete    # Select meeting to delete with fzf
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

See [PLAN.md](PLAN.md) for the full development roadmap.

Current status: **v0.2 - Meeting Notes** ✅
