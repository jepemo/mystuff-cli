# mystuff-cli

[![Tests](https://github.com/jepemo/mystuff-cli/actions/workflows/test.yml/badge.svg)](https://github.com/jepemo/mystuff-cli/actions/workflows/test.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

A command-line tool for keeping personal knowledge in local, plain-text files.
It manages links, journal entries, meeting notes, lists, wiki pages, learning
tracks, and self-evaluations. Data stays portable, readable, and easy to keep
under Git.

## Installation

Requires Python 3.10 or newer. The recommended installation method is
[`pipx`](https://pipx.pypa.io/):

```bash
pipx install mystuff-cli
```

## Quick start

```bash
# Create the default workspace at ~/.mystuff
mystuff init

# Save and find a link
mystuff link add --url https://python.org
mystuff link search python

# Create today's journal entry in your editor
mystuff journal add
```

Run `mystuff --help` to see every command, or
`mystuff <command> --help` for help with a specific command group.

## Commands

| Command | Purpose |
| --- | --- |
| `mystuff init` | Create the data directory and initial configuration |
| `mystuff link` | Save, search, edit, and import links |
| `mystuff journal` | Manage daily journal entries |
| `mystuff meeting` | Manage meeting notes |
| `mystuff list` | Manage named lists |
| `mystuff wiki` | Capture sources and build interconnected notes |
| `mystuff learn` | Organize learning tracks and progress |
| `mystuff eval` | Record and report self-evaluations |
| `mystuff generate web` | Generate a static website from your data |
| `mystuff sync` | Run configured backup or publishing commands |

## Data and configuration

By default, mystuff stores data in `~/.mystuff`. Set `MYSTUFF_HOME` to use a
different directory. Configuration lives in `config.yaml` inside that data
directory, and commands that open files use your `$EDITOR`.

`fzf` is optional and enables interactive selection in supported commands.

Licensed under the [MIT License](LICENSE).
