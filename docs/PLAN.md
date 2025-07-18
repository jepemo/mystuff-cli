# Unified **mystuff** Development Roadmap

A command‑line tool for capturing, organising and retrieving personal knowledge efficiently.

---

## ⚙️ Design Principles

- **Single binary**: `mystuff`
- **Cohesive sub‑commands**: `init`, `link`, `meeting`, `journal`, `wiki`, `eval`, `list`, `search`, `version`
- **One data directory** (configurable, defaults to `~/.mystuff`) via `--dir/-d` or `MYSTUFF_HOME`
- **Simple file formats** per module: JSONL / YAML / Markdown
- **Optional `fzf` integration** for fuzzy selection and search
- **Honours `$EDITOR` and `$PAGER`** for editing and viewing
- **Clear colourised output**; supports `-v/--verbose` and `-q/--quiet`
- **Tests from day one** (unit + integration)
- **Semantic Versioning** (`0.x` unstable, `1.x` stable)

---

## 📁 Default Directory Layout

```text
~/.mystuff/
├── links.jsonl
├── meetings/
├── journal/
├── wiki/
├── eval/
├── lists/
└── config.yaml
```

_(Empty sub‑folders contain a `.gitkeep`)_

---

## 🛣️ Incremental Roadmap

### 0.0 – Init

| Goal        | Details                                                                                                                                 |
| ----------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| **Command** | `mystuff init`                                                                                                                          |
| **Actions** | • Creates the directory tree above<br>• Generates a default `config.yaml` (path, editor, etc.)<br>• Accepts `--dir/-d` to override path |
| **Tests**   | Directory exists, permissions, idempotency                                                                                              |

---

### 0.1 – Links

- Command: `mystuff link add|list|edit|delete|search`
- Fields: **url**, **title**, **description**, **tags**, timestamp
- Pluggable storage: start with JSONL → optional SQLite
- `fzf` integration for list/open/edit

#### Flags

- `--url` – Target URL (required for `add`).
- `--title` – Human-readable title (defaults to the URL host if omitted).
- `--description` – Optional free-text notes about the link.
- `--tag` – One or more tags for categorization (repeatable flag).
- `--open` – Open the link in the default browser after adding or selecting it.
- `--search` – Search by title, tags, or description (used with `search` subcommand).

#### File Format and Storage

- **File Format**: Links are stored in a JSONL (JSON Lines) file, where each line represents a single link entry.
- **Storage Location**: The file is saved as `~/.mystuff/links.jsonl`.
- **File Structure**:
  - Each line is a JSON object with the following fields:
    ```json
    {
      "url": "https://example.com",
      "title": "Example Website",
      "description": "A sample description for the example website.",
      "tags": ["sample", "example"],
      "timestamp": "2023-10-05T14:30:00Z"
    }
    ```
  - Example content of `links.jsonl`:
    ```json
    {"url": "https://example.com", "title": "Example Website", "description": "A sample description for the example website.", "tags": ["sample", "example"], "timestamp": "2023-10-05T14:30:00Z"}
    {"url": "https://another.com", "title": "Another Site", "description": "Another example link.", "tags": ["example"], "timestamp": "2023-10-06T10:00:00Z"}
    ```

#### Tests

- Validate required fields (`url`) and ensure defaults (e.g., `title` from URL host) are applied.
- CRUD operations for links.
- Ensure `fzf` integration works for filtering by title, tags, or description.
- Verify correct JSONL formatting and idempotent updates.

---

### 0.2 – Meeting Notes

- Command: `mystuff meeting add|list|edit|delete|search`
- Fields: **title**, **date**, **participants**, **body**
- Agenda templates via `--template`
- Fuzzy filter by date/title (`fzf`)

#### Flags

- `--title` – Title of the meeting (required for `add`).
- `--date` – Date of the meeting in `YYYY-MM-DD` format (defaults to today if omitted).
- `--participants` – Comma-separated list of participants (optional).
- `--body` – Free-text content or agenda of the meeting (optional).
- `--template` – Path to a template file for pre-filling the meeting body (optional).
- `--tag` – One or more tags for categorization (repeatable flag).
- `--search` – Search by title, date, or participants (used with `search` subcommand).

#### File Format and Storage

- **File Format**: Each meeting note is stored as a Markdown file with YAML front-matter for metadata.
- **Storage Location**: Files are saved in the `~/.mystuff/meetings/` directory.
- **File Structure**:

  - File name: `<date>_<slugified-title>.md` (e.g., `2023-10-05_team-sync.md`).
  - Example content:

    ```markdown
    ---
    title: "Team Sync"
    date: "2023-10-05"
    participants: ["Alice", "Bob", "Charlie"]
    tags: ["team", "sync"]
    ---

    ## Agenda

    - Discuss project updates
    - Plan next sprint

    ## Notes

    - Alice will handle the deployment.
    - Bob will prepare the presentation.
    ```

#### Tests

- Validate date format and ensure it defaults to today if omitted.
- CRUD operations for meeting notes.
- Ensure `fzf` integration works for filtering by date or title.
- Verify correct file naming and metadata parsing.

---

### 0.3 – Daily Journal

- Command: `mystuff journal add|list|edit|search`
- Auto‑stamps date (YYYY‑MM‑DD), opens in `$EDITOR`
- Search by date range or full‑text
- Quick browse using `fzf`

#### Flags

- `--date` – Specify the date for the journal entry in `YYYY-MM-DD` format (defaults to today if omitted).
- `--body` – Free-text content for the journal entry (optional, opens in `$EDITOR` if omitted).
- `--search` – Search journal entries by date range or full-text (used with `search` subcommand).
- `--range` – Specify a date range for filtering entries (e.g., `--range 2023-10-01:2023-10-07`).

#### File Format and Storage

- **File Format**: Each journal entry is stored as a Markdown file with YAML front-matter for metadata.
- **Storage Location**: Files are saved in the `~/.mystuff/journal/` directory.
- **File Structure**:

  - File name: `<date>.md` (e.g., `2023-10-05.md`).
  - Example content:

    ```markdown
    ---
    date: "2023-10-05"
    tags: ["personal", "reflection"]
    ---

    ## Journal Entry

    Today I worked on the mystuff CLI project. It was productive, and I made significant progress on the journal module.
    ```

#### Tests

- Validate date format and ensure it defaults to today if omitted.
- CRUD operations for journal entries.
- Ensure `fzf` integration works for filtering by date or full-text.
- Verify correct file naming and metadata parsing.

---

### 0.4 – Wiki (Topical Notes)

- Command: `mystuff wiki new|view|edit|delete|search`
- Markdown files with **front‑matter** (tags, aliases)
- Updates backlink index on save
- Search by tag, keyword, or small ASCII graph view

#### Flags

- `--title` – Title of the wiki note (required for `new`).
- `--tags` – One or more tags for categorization (repeatable flag).
- `--alias` – One or more aliases for the note (repeatable flag, optional).
- `--search` – Search by title, tags, or content (used with `search` subcommand).
- `--graph` – Display a small ASCII graph of backlinks (used with `view` or `search`).

#### File Format and Storage

- **File Format**: Each wiki note is stored as a Markdown file with YAML front-matter for metadata.
- **Storage Location**: Files are saved in the `~/.mystuff/wiki/` directory.
- **File Structure**:

  - File name: `<slugified-title>.md` (e.g., `project-overview.md`).
  - Example content:

    ```markdown
    ---
    title: "Project Overview"
    tags: ["project", "overview"]
    aliases: ["summary", "intro"]
    backlinks: ["team-structure", "roadmap"]
    ---

    ## Project Overview

    This note provides a high-level overview of the project, including goals, milestones, and key stakeholders.

    ### Key Points

    - The project aims to improve productivity.
    - Collaboration is a core focus.
    ```

#### Backlink Management

- Backlinks are automatically updated whenever a note is saved.
- The `backlinks` field in the front-matter lists all notes that reference the current note.

#### Tests

- Validate required fields (`title`) and ensure defaults (e.g., empty `tags` or `aliases`) are applied.
- CRUD operations for wiki notes.
- Ensure backlinks are updated consistently across notes.
- Verify `fzf` integration for filtering by title, tags, or content.
- Test ASCII graph generation for backlinks.

---

### 0.5 – Self‑Evaluation

- Command: `mystuff eval add|list|edit|delete|report`
- Fields: **date**, **category**, **score**, **comments**
- Entries stored by month
- Summary report: `mystuff eval report` (stats per category)

#### Flags

- `--date` – Date of the evaluation in `YYYY-MM-DD` format (defaults to today if omitted).
- `--category` – Category of the evaluation (e.g., "productivity", "health").
- `--score` – Numeric score for the evaluation (required for `add`).
- `--comments` – Optional free-text comments for the evaluation.
- `--report` – Generate a summary report of evaluations (used with `report` subcommand).
- `--range` – Specify a date range for filtering evaluations in the report (e.g., `--range 2023-10-01:2023-10-31`).

#### File Format and Storage

- **File Format**: Evaluations are stored in YAML files, grouped by month.
- **Storage Location**: Files are saved in the `~/.mystuff/eval/` directory.
- **File Structure**:
  - File name: `<year>-<month>.yaml` (e.g., `2023-10.yaml`).
  - Example content:
    ```yaml
    - date: "2023-10-05"
      category: "productivity"
      score: 8
      comments: "Felt productive and accomplished key tasks."
    - date: "2023-10-06"
      category: "health"
      score: 7
      comments: "Went for a run and ate healthy meals."
    ```

#### Summary Report

- The `mystuff eval report` command generates a summary of evaluations, showing averages and counts per category.
- By default, the report includes entries from the past year unless a specific range is provided.

#### Tests

- Validate required fields (`date`, `category`, `score`) and ensure defaults (e.g., `date` defaults to today).
- CRUD operations for evaluations.
- Ensure correct YAML formatting and idempotent updates.
- Test summary report generation for accuracy and formatting.
- Verify filtering by date range and category.

---

### 0.6 – Lists

- Command: `mystuff list create|view|edit|delete|search`
- Arbitrary named lists (e.g., _books‑to‑read_)

#### Flags

- `--name` – Name of the list (required for `create` and `view`).
- `--item` – Add an item to the list (used with `edit`).
- `--remove-item` – Remove an item from the list (used with `edit`).
- `--check` – Mark an item as checked (used with `edit`).
- `--uncheck` – Mark an item as unchecked (used with `edit`).
- `--search` – Search for lists or items by name or content.
- `--export` – Export the list to a file in CSV or YAML format.
- `--import` – Import a list from a CSV or YAML file.

#### File Format and Storage

- **File Format**: Lists are stored as individual YAML files, where each file represents a single list.
- **Storage Location**: Files are saved in the `~/.mystuff/lists/` directory.
- **File Structure**:
  - File name: `<list-name>.yaml` (e.g., `books-to-read.yaml`).
  - Example content:
    ```yaml
    name: "Books to Read"
    items:
      - text: "Clean Code by Robert C. Martin"
        checked: false
      - text: "The Pragmatic Programmer by Andrew Hunt and David Thomas"
        checked: true
      - text: "Designing Data-Intensive Applications by Martin Kleppmann"
        checked: false
    ```

#### Tests

- Validate required fields (`name`) and ensure proper file naming.
- CRUD operations for lists and items.
- Ensure `fzf` integration works for filtering by list name or item content.
- Verify correct YAML formatting and idempotent updates.
- Test import/export functionality for both CSV and YAML formats.
- Test marking items as checked/unchecked.

---

### 1.0 – Release Candidate & Polish

- Consolidate shared modules (storage, flags, logging)
- Global `mystuff search` (cross‑type full‑text)
- `mystuff --version` with SemVer and short commit hash
- Colour output, error handling, richer help
- CI/CD with coverage and publishing (PyPI / Homebrew)
- End‑to‑end tests
- 🎉 **Stable 1.0 release**

---

## 🚀 Beyond 1.0 (v2.x+)

- **Plugin/extension** architecture
- **Encryption** / vault mode
- Optional **TUI dashboard**
- **Sync** across machines (Git backend)
- Integration with external services (e.g. bookmarking)

---

## 🛠️ Technology Suggestions

| Area            | Recommended                         | Alternatives |
| --------------- | ----------------------------------- | ------------ |
| Language        | **Python + Typer**                  | Rust + Clap  |
| Storage         | JSONL / YAML                        | SQLite       |
| Text search     | ripgrep                             | Lucene       |
| Fuzzy UI        | `fzf`                               | skim         |
| Coloured output | `rich`                              | click‑rich   |
| MD/JSON parsing | `python-frontmatter`, `ruamel.yaml` |              |

---

## 💡 Tips

- Keep each 0.x cycle **small** with green CI
- Refactor shared code to avoid duplication
- Automate tests and linting early
- Gather continuous feedback before the next module
