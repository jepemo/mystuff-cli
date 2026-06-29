"""Small normalizations for lesson Markdown authored by generators."""

import re

_BLOCKQUOTE_LINE = re.compile(r"^(?P<prefix>[ \t]*>)[ \t]?(?P<content>.*?)(?:\r?\n)?$")
_UNORDERED_LIST_ITEM = re.compile(r"[-+*][ \t]+")
_ORDERED_LIST_ITEM = re.compile(r"\d+[.)][ \t]+")


def normalize_lesson_markdown(content: str) -> str:
    """Make generated blockquote lists valid Markdown.

    A list immediately following text in a blockquote needs an empty quoted line
    before it. Lesson generators commonly omit that separator, which makes the
    Markdown parser render every item as text in a single paragraph.
    """
    lines = content.splitlines(keepends=True)
    normalized_lines = []

    for index, line in enumerate(lines):
        normalized_lines.append(line)

        if index == len(lines) - 1:
            continue

        current_match = _BLOCKQUOTE_LINE.match(line)
        next_match = _BLOCKQUOTE_LINE.match(lines[index + 1])
        if not current_match or not next_match:
            continue

        current_content = current_match.group("content").strip()
        next_content = next_match.group("content").lstrip()
        is_list_item = _UNORDERED_LIST_ITEM.match(
            next_content
        ) or _ORDERED_LIST_ITEM.match(next_content)
        if current_content and is_list_item:
            newline = "\r\n" if line.endswith("\r\n") else "\n"
            normalized_lines.append(f"{current_match.group('prefix')}{newline}")

    return "".join(normalized_lines)
