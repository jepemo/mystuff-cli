"""Compounding wiki primitives.

The public CLI lives in :mod:`mystuff.commands.wiki`.  This package contains
the storage, capture, indexing, auditing, and synthesis pipeline so those
pieces can be tested independently from Typer.
"""

from mystuff.wiki.storage import WikiPaths, ensure_wiki_layout, get_wiki_paths

__all__ = ["WikiPaths", "ensure_wiki_layout", "get_wiki_paths"]
