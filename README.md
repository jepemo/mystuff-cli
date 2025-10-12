# mystuff-cli

[![Tests](https://github.com/jepemo/mystuff-cli/actions/workflows/test.yml/badge.svg)](https://github.com/jepemo/mystuff-cli/actions/workflows/test.yml)
[![Code Quality](https://github.com/jepemo/mystuff-cli/actions/workflows/code-quality.yml/badge.svg)](https://github.com/jepemo/mystuff-cli/actions/workflows/code-quality.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> Capture, organise, and retrieve personal knowledge—directly from your terminal.

---

_mystuff‑cli_ is a single‑binary command‑line toolkit that saves links, notes, meetings, journals, lists, and self‑evaluations in version‑controlled plain‑text files. No databases, no lock‑in—just your data, under Git.

## Quick start

```bash
# Install (recommended)
pipx install mystuff-cli

# Initialise workspace
mystuff init                  # creates ~/.mystuff

# First bookmark
mystuff link add --url https://python.org
mystuff link search python    # locate saved links
```

## Key features

- **Comprehensive toolkit** – links, journal, meetings, wiki, lists, self‑evals, learning materials.
- **Plain‑text storage** – JSONL / Markdown / YAML; ideal for Git workflows.
- **Editor integration** – honours `$EDITOR` and `$PAGER`.
- **Web viewer** – open lessons as beautifully styled HTML in your browser.
- **Static site generator** – create elegant portfolio websites from your data.
- **fzf support** – interactive selection where available.
- **Full‑text search** – across every module.
- **GitHub stars importer** – capture starred repositories as bookmarks.
- **Configurable sync** – run user‑defined shell commands for backup or deployment.

_(Command reference available in [/docs/CLI.md](docs/CLI.md).)_

## Installation

```bash
# pipx
pipx install mystuff-cli

# From source
git clone https://github.com/jepemo/mystuff-cli.git
cd mystuff-cli
pip install -e .
```

### Optional tools

| Tool      | Purpose                                 |
| --------- | --------------------------------------- |
| `fzf`     | Interactive pickers for list/edit tasks |
| `ripgrep` | Faster recursive search (auto‑detected) |

## Directory structure

```
~/.mystuff/
├── links.jsonl           # bookmarks & repositories
├── journal/2025‑07‑28.md
├── meeting/2025/standup.md
├── wiki/elixir‑patterns.md
├── lists/reading.yaml
├── learning/
│   ├── lessons/          # your learning materials (markdown)
│   └── metadata.yaml     # progress tracking
└── config.yaml
```

All data is stored as plain text for transparency and portability.

## Learning Management

The `learn` module helps you track and study educational materials:

```bash
# List all lessons
mystuff learn list

# Start a lesson
mystuff learn start python/01-variables.md

# Open current lesson in web browser (with beautiful HTML styling)
mystuff learn current --web

# Complete and move to next lesson
mystuff learn next --web

# View your progress
mystuff learn stats
```

The `--web` option converts markdown lessons to beautifully styled HTML with:

- Syntax highlighting for code blocks
- Responsive design
- Dark mode support
- Clean, readable typography
- 5 theme options: `default`, `minimal`, `github`, `dark`, `notion`

## Static Website Generation

Generate a beautiful static website from your mystuff data with automatic GitHub integration:

```bash
# Generate with default settings
mystuff generate web

# Generate to specific directory
mystuff generate web --output ~/my-website

# Preview the generated site
open ~/my-website/index.html
```

Configure the website in `~/.mystuff/config.yaml`:

```yaml
generate:
  web:
    output: "~/mystuff_web"
    title: "My Knowledge Base"
    description: "Personal knowledge management"
    author: "Your Name"
    github_username: "yourusername"  # Optional: fetch GitHub repos
    menu_items:
      - name: "GitHub"
        url: "https://github.com/yourusername"
      - name: "Blog"
        url: "/blog"
      - name: "Contact"
        url: "mailto:your@email.com"
```

Features:
- **Elegant jepemo.github.io-inspired design** – Minimal, professional aesthetic
- **Roboto Mono typography** – Clean, readable monospace font
- **Dot pattern background** – Subtle visual texture (#F5F5F0 beige)
- **GitHub integration** – Automatically displays your top 6 starred repositories
- **Sidebar navigation** – Configurable menu with hover states (#558ad8 blue accent)
- **Responsive layout** – Mobile-friendly design
- **No authentication required** – Uses public GitHub API
- **Graceful fallback** – Works without GitHub username or when rate-limited

The GitHub integration fetches your most popular repositories (sorted by stars) and displays them with:
- Repository name (clickable link)
- Description
- Primary programming language

Example: See [jepemo.github.io](https://jepemo.github.io/) for the visual reference.

## Syncing

Define any shell commands under `sync.commands` in `config.yaml`:

```yaml
sync:
  commands:
    - git add .
    - git commit -m "sync $(date)"
    - rsync -av ~/.mystuff /backup/mystuff
```

Execute them with:

```bash
mystuff sync run --verbose
```

## Roadmap

| Version | Status      | Theme                |
| ------- | ----------- | -------------------- |
| v0.7    | **Current** | Custom sync commands |
| v1.0    | Planned     | Stable public API    |

Full roadmap: [/docs/PLAN.md](docs/PLAN.md).

## License

MIT License.

---
