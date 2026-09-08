# mystuff-cli

[![Tests](https://github.com/jepemo/mystuff-cli/actions/workflows/test.yml/badge.svg)](https://github.com/jepemo/mystuff-cli/actions/workflows/test.yml)
[![Code Quality](https://github.com/jepemo/mystuff-cli/actions/workflows/code-quality.yml/badge.svg)](https://github.com/jepemo/mystuff-cli/actions/workflows/code-quality.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
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
- **Interactive selectors** – built-in fuzzy learning selectors, plus optional `fzf` pickers where available.
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
| `fzf`     | Optional interactive pickers for non-learning list/edit tasks |
| `ripgrep` | Faster recursive search (auto‑detected) |

## Directory structure

```
~/.mystuff/
├── links.jsonl           # bookmarks & repositories
├── journal/2025‑07‑28.md
├── meeting/2025/standup.md
├── wiki/
│   ├── raw/              # immutable source captures
│   ├── content/          # synthesized public/private Markdown pages
│   ├── metadata/         # source records, lexical index, and audit state
│   └── EDITORIAL.md      # provider-neutral writing contract
├── lists/reading.yaml
├── learning/
│   ├── lessons/
│   │   ├── README.md
│   │   └── foundations/
│   │       ├── TRACK.md
│   │       ├── 001.md
│   │       └── 002.md
│   └── metadata.yaml     # schema v2 progress tracking by lesson_id
└── config.yaml
```

All data is stored as plain text for transparency and portability.

## Compounding Wiki

The wiki turns captured sources into interconnected, explanatory pages. Raw
documents are immutable and are never published; `wiki/content/index.md` is the
human navigational entry point and `wiki/metadata/index.json` is a regenerable
lexical index used for related-page retrieval and fast audits.

```bash
# Capture a URL, let the configured agent synthesize pages, and audit changes
mystuff wiki ingest https://example.com/article

# Capture now and process later
mystuff wiki ingest https://example.com/article --capture-only
mystuff wiki process src-CONTENT_HASH
mystuff wiki process-batch src-FIRST src-SECOND src-THIRD

# Preview the structured change set without applying it
mystuff wiki ingest https://example.com/article --dry-run

# Re-run synthesis for content that was already processed
mystuff wiki ingest https://example.com/article --reprocess

# Inspect source state and regenerate derived metadata
mystuff wiki status
mystuff wiki rebuild-index

# Fast structural audit or full source-overlap audit
mystuff wiki audit
mystuff wiki audit --full

# Remove a generated page by id, slug, or public URL, including unused raw data
mystuff wiki remove wiki-http --dry-run
mystuff wiki remove https://example.com/wiki/http.html

# Preserve old wiki files as immutable legacy inputs
mystuff wiki migrate-legacy
```

One source can create several pages or improve existing ones. Generated pages
use normal relative Markdown links and default to `public: true`; set a page to
`public: false` to exclude it from the static website. Backlinks are derived
from the content and are not stored in page frontmatter.

The external agent is configured once and shared with Learning:

```yaml
ai:
  default_provider: codex
  providers:
    codex:
      command: ["codex"]
      model: null      # inherit Codex's current default
      reasoning_effort: null # for example: medium
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
      x: []            # optional URL templates for thread-reader fallbacks
```

The agent receives captured source ids and a small lexical neighborhood. It
returns a JSON change set; the CLI validates and applies that result rather than
granting the source document direct write authority.

## Learning Management

The `learn` module is track-aware: every track lives in
`learning/lessons/<track_id>/`, exposes track metadata through `TRACK.md`, and
stores real lessons as `001.md`, `002.md`, and so on. Tracks are grouped by
`classification`, so the main catalog now flows as `classification -> track ->
lesson`.

```bash
# Show current learning state
mystuff learn

# List visible tracks grouped by classification
mystuff learn list

# Select or inspect an active track
mystuff learn track
mystuff learn track foundations
mystuff learn track --list

# Inspect lessons inside a track
mystuff learn list --track foundations

# Filter the catalog to one classification
mystuff learn list --classification systems-thinking

# Start a new track from a selector, or resume a specific track
mystuff learn start
mystuff learn start foundations

# Select and open an active lesson
mystuff learn current

# Open a specific active lesson in web browser (opens configured web URL)
mystuff learn current --web

# Select an active lesson and advance within its track
mystuff learn next

# View your progress
mystuff learn stats
```

Important behavior:

- `mystuff learn` shows a compact status summary with one current learning focus.
- `mystuff learn track` opens an interactive selector for published tracks when no track id is passed.
- `mystuff learn track --list` prints published tracks as plain text.
- `mystuff learn start` can select an unlocked private or draft track and prepares it just in time; switching focus requires confirmation.
- `mystuff learn current` and `mystuff learn next` operate on the single active lesson when no reference is passed.
- Learning selectors are built in: use `--prompt` to filter with text and choose by visible number instead of the full-screen selector.
- `mystuff learn start <track_id>` plans new tracks, then reviews only the first uncompleted lesson before setting the cursor.
- `mystuff learn current` reviews a private active lesson only when it must be opened; a public lesson opens without an agent call.
- `mystuff learn next` prepares the next lesson before recording completion; `mystuff learn complete` only records an explicit completion.
- Progress is stored in `learning/metadata.yaml` with schema v2 and exactly one cursor; `completed_lessons` remains historical when focus changes.
- `mystuff learn current --web` opens the published lesson URL from `config.yaml` under `generate.web.url`.

## Static Website Generation

Generate a beautiful static website from your mystuff data with automatic GitHub integration:

```bash
# Generate with default settings
mystuff generate web

# Generate to specific directory
mystuff generate web --output ~/my-website

# Force overwrite without confirmation
mystuff generate web --force

# Preview the generated site
open ~/my-website/index.html
```

Configure the website in `~/.mystuff/config.yaml`:

```yaml
generate:
  web:
    output: "~/mystuff_web"
    url: "https://example.com/mystuff"
    title: "My Knowledge Base"
    description: "Personal knowledge management"
    author: "Your Name"
    github_username: "yourusername" # Required for GitHub integration
    repositories: # List of repos to display (in order)
      - "repo-name-1"
      - "repo-name-2"
      - "repo-name-3"
    menu_items:
      - name: "GitHub"
        url: "https://github.com/yourusername"
      - name: "Blog"
        url: "/blog"
      - name: "Contact"
        url: "mailto:your@email.com"
```

Features:

- **Public compounding wiki** – `wiki/index.html` and one page per public wiki entry
- **Privacy-safe regeneration** – private wiki pages and stale generated HTML are removed
- **Classification hub** – `learning.html` is now the top-level directory of classifications
- **Intermediate classification pages** – each classification gets its own page listing the tracks inside it
- **Minimal track pages** – each track page now acts as a clean syllabus of lessons
- **Intra-track lesson navigation** – prev/next stays inside the active track
- **Minimal brutalist curriculum UI** – public pages show only the key metadata needed to keep moving
- **GitHub integration** – Display your chosen repositories with automatic data fetching
- **User-controlled repo list** – Specify exactly which repos to show and in what order
- **Responsive layout** – Mobile-friendly design
- **No authentication required** – Uses public GitHub REST API
- **Force mode** – Use `-f` flag to skip overwrite confirmation

The GitHub integration fetches repository details for each repo in your list and displays:

- Repository name (clickable link)
- Description
- Primary programming language

Repositories are shown in the exact order you specify in the config.

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
