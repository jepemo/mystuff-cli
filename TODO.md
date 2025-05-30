# 🛠️ `mystuff` Development Plan

A command-line tool to store, organize, and access personal knowledge efficiently.

---

## ✅ Features Overview

- 📎 Store/search/delete/edit **web links**
- 📝 Store/edit/search **meeting notes**
- 📆 Store/search **daily logs**
- 📚 Store/edit/delete/search **topical notes** (wiki-style)
- 💡 Store/edit/search **self-evaluation notes**
- ✅ Store/search/edit **checklists/lists**

---

## 🔄 CLI Design Principles

- Single binary: `mystuff`
- Subcommands for each category: `link`, `log`, `wiki`, `eval`, `list`, `meeting`
- All data stored under `~/.mystuff/` (configurable)
- Use structured file formats (YAML, Markdown, or JSONL)
- Optional support for `fzf` fuzzy selection
- Designed for fast keyboard-first workflows

---

## 🚧 TODO Roadmap

### `0.1` – Links Module (MVP)

- [ ] Create `mystuff link` subcommand
- [ ] Support adding a link with title, URL, tags, and optional description
- [ ] List all saved links
- [ ] Basic search by title or tag
- [ ] Support deleting and editing links
- [ ] Persist data to disk using simple JSON/YAML
- [ ] Refactor: extract prompt logic to allow testing
- [ ] Refactor: extract storage logic to allow testing
- [ ] Parse all link fields from CLI args (non-interactive)
- [ ] Optional: integrate `fzf` for selecting/editing/deleting entries

---

### `0.2` – Log Module

- [ ] Create `mystuff log` subcommand
- [ ] Store daily entries (by date)
- [ ] Append new entries via CLI prompt or `--text` argument
- [ ] View logs from specific date/range
- [ ] Full-text search

---

### `0.3` – Wiki Module

- [ ] Create `mystuff wiki` subcommand
- [ ] Allow creating named wiki entries (e.g., `mystuff wiki new rest-api-design`)
- [ ] Support editing entries with `$EDITOR`
- [ ] Support basic search
- [ ] Option to organize entries in folders (tags/categories)

---

### `0.4` – Self-Evaluation Module

- [ ] Create `mystuff eval` subcommand
- [ ] Capture self-reflection entries (weekly/monthly)
- [ ] Categorize entries (e.g., productivity, learning, communication)
- [ ] Search and review history over time

---

### `0.5` – Meeting Notes Module

- [ ] Create `mystuff meeting` subcommand
- [ ] Support creating new notes linked to a meeting title/date
- [ ] Add predefined sections: agenda, notes, action items
- [ ] Review past meetings by date or title

---

### `0.6` – List Module

- [ ] Create `mystuff list` subcommand
- [ ] Create, edit, delete named lists (e.g., books-to-read)
- [ ] Add/remove items from lists
- [ ] Export list to plain text or markdown

---

### `1.0` – Polishing & Generalization

- [ ] Unified configuration file for data path and editor
- [ ] Consistent UX across all modules (help text, verbosity, etc.)
- [ ] Testing framework setup (unit and integration tests)
- [ ] Performance optimizations for large collections
- [ ] Optional: support sync/export to Git or remote
- [ ] Optional: support templates for recurring notes

---

## 🧪 Technology Suggestions

- Language: Rust or Python (with Click or Typer)
- Storage: JSON or YAML files per module (flat files)
- Editor: Respect `$EDITOR` env var for editing entries
- Search: Ripgrep or native fuzzy search
- Optional dependencies: `fzf`, `bat`, `jq`

---

## 📁 Directory Structure (default: ~/.mystuff)

```
~/.mystuff/
├── links.json
├── logs/
│   ├── 2024-01-01.md
│   └── ...
├── wiki/
│   ├── rest-api-design.md
│   └── docker-tricks.md
├── eval/
│   └── 2024-Week-01.yaml
├── meetings/
│   └── 2024-05-29-team-sync.md
├── lists/
│   └── books.yaml
└── config.yaml
```


