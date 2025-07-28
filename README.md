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

- **Comprehensive toolkit** – links, journal, meetings, wiki, lists, self‑evals.
- **Plain‑text storage** – JSONL / Markdown / YAML; ideal for Git workflows.
- **Editor integration** – honours `$EDITOR` and `$PAGER`.
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
└── config.yaml
```

All data is stored as plain text for transparency and portability.

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

## Extending

- New content types live in `mystuff/modules/`.
- Commands are implemented with [Click](https://click.palletsprojects.com/).
- Tests use `pytest` and run in CI on every push.

See [/CONTRIBUTING.md](CONTRIBUTING.md) for details.

## Roadmap

| Version | Status      | Theme                |
| ------- | ----------- | -------------------- |
| v0.7    | **Current** | Custom sync commands |
| v0.8    | In progress | Encrypted vaults     |
| v1.0    | Planned     | Stable public API    |

Full roadmap: [/docs/PLAN.md](docs/PLAN.md).

## License

MIT License.

---
