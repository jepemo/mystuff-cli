# mystuff-cli 🗃️

[![Tests](https://github.com/jepemo/mystuff-cli/actions/workflows/test.yml/badge.svg)](https://github.com/jepemo/mystuff-cli/actions/workflows/test.yml)
[![Code Quality](https://github.com/jepemo/mystuff-cli/actions/workflows/code-quality.yml/badge.svg)](https://github.com/jepemo/mystuff-cli/actions/workflows/code-quality.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> Capture everything. Find anything. From the terminal you already love.

---

mystuff‑cli is a **single‑binary, zero‑DB toolkit** for developers who live in `$SHELL` but still forget where they parked that brilliant idea from last week.

## 👟 TL;DR (60 seconds)

```bash
pipx install mystuff-cli      # or: git clone && pip install -e .
mystuff init                  # bootstrap ~/.mystuff
mystuff link add --url https://python.org
mystuff link search python    # 🥳  found it!
```

## ✨ Highlights

- **Batteries included** – links, journal, meetings, wiki, lists, self‑evals.
- **Plain files, plain joy** – JSONL / Markdown / YAML. 100% Git‑friendly.
- **Bring‑your‑own‑editor** – respects `$EDITOR` & `$PAGER` out of the box.
- **Instant fuzzy magic** – optional [`fzf`](https://github.com/junegunn/fzf) everywhere.
- **Full‑text search** – across _all_ modules in one go.
- **GitHub stars importer** – turn "I’ll read that later" into actual knowledge.
- **Scriptable sync** – run any shell you fancy and pretend it’s automation.

_(Need every sub‑command? See [/docs/CLI.md](docs/CLI.md).)_

## 🚀 Installation

```bash
# pipx (recommended)
pipx install mystuff-cli

# pip
git clone https://github.com/jepemo/mystuff-cli.git
cd mystuff-cli
pip install -e .
```

### Optional Goodies

| Tool      | Why you might want it                    |
| --------- | ---------------------------------------- |
| `fzf`     | buttery‑smooth interactive pickers       |
| `ripgrep` | faster cross‑note search (auto‑detected) |

## 📂 Anatomy of `~/.mystuff`

```
links.jsonl          # bookmarks & repos
journal/2025-07-23.md
meeting/2025/standup.md
wiki/elixir-patterns.md
lists/reading.yaml
config.yaml
```

It’s all plain text. Lose the binary, keep your knowledge.

## 🔄 Syncing (a.k.a. "my future self will thank me")

Add any shell commands to `sync.commands` in `config.yaml`:

```yaml
sync:
  commands:
    - git add .
    - git commit -m "sync $(date)"
    - rsync -av ~/.mystuff /backup/mystuff
```

Then run:

```bash
mystuff sync run --verbose
```

## 🛠️ Extending

- New content types live under `mystuff/modules/`.
- Commands are plain [Click](https://click.palletsprojects.com/) groups.
- Tests: pytest with coverage from day zero.

See [/CONTRIBUTING.md](CONTRIBUTING.md).

## 🗺️ Roadmap

| Version | Status      | Key theme                    |
| ------- | ----------- | ---------------------------- |
| v0.7    | **Current** | Custom sync commands         |
| v0.8    | In progress | Testing and stability        |
| v1.0    | Planned     | Stable public API && Release |

Full plan lives in [/docs/PLAN.md](docs/PLAN.md).

## 📜 License

MIT – because knowledge wants to be free.

---

_Built by developers who keep forgetting things so you don’t have to._ ✨
