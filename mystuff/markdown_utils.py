"""Markdown helpers shared by generated and locally previewed lessons."""

import re
from html import escape

from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor
from markdown.preprocessors import Preprocessor

MATHJAX_SCRIPT_URL = "https://cdn.jsdelivr.net/npm/mathjax@4.0.0/tex-chtml.js"

_BLOCKQUOTE_LINE = re.compile(r"^(?P<prefix>[ \t]*>)[ \t]?(?P<content>.*?)(?:\r?\n)?$")
_UNORDERED_LIST_ITEM = re.compile(r"[-+*][ \t]+")
_ORDERED_LIST_ITEM = re.compile(r"\d+[.)][ \t]+")
_DISPLAY_MATH_SINGLE_LINE = re.compile(r"^[ \t]*\\\[(?P<content>.*?)\\\][ \t]*$")
_DISPLAY_MATH_START = re.compile(r"^[ \t]*\\\[[ \t]*$")
_DISPLAY_MATH_END = re.compile(r"^[ \t]*\\\][ \t]*$")
_INLINE_MATH = r"(?<!\\)\\\((.+?)(?<!\\)\\\)"


class DisplayMathPreprocessor(Preprocessor):
    """Protect ``\\[...\\]`` blocks before Markdown consumes backslashes."""

    def run(self, lines: list[str]) -> list[str]:
        output: list[str] = []
        index = 0

        while index < len(lines):
            single_line_match = _DISPLAY_MATH_SINGLE_LINE.match(lines[index])
            if single_line_match:
                output.append(self._stash(single_line_match.group("content")))
                index += 1
                continue

            if not _DISPLAY_MATH_START.match(lines[index]):
                output.append(lines[index])
                index += 1
                continue

            end_index = index + 1
            while end_index < len(lines) and not _DISPLAY_MATH_END.match(
                lines[end_index]
            ):
                end_index += 1

            if end_index == len(lines):
                # Preserve malformed input verbatim instead of swallowing the rest
                # of the lesson.
                output.append(lines[index])
                index += 1
                continue

            output.append(self._stash("\n".join(lines[index + 1 : end_index])))
            index = end_index + 1

        return output

    def _stash(self, content: str) -> str:
        return self.md.htmlStash.store(
            f'<div class="math-display">\\[\n{escape(content)}\n\\]</div>'
        )


class InlineMathProcessor(InlineProcessor):
    """Protect ``\\(...\\)`` expressions while keeping them inline."""

    def handleMatch(self, match, data):
        element = self.md.htmlStash.store(
            f'<span class="math-inline">\\({escape(match.group(1))}\\)</span>'
        )
        return element, match.start(0), match.end(0)


class LessonMathExtension(Extension):
    """Preserve TeX delimiters for MathJax in lesson HTML."""

    def extendMarkdown(self, md) -> None:
        # Fenced code is stashed at priority 25, so display-like examples inside
        # code blocks are left untouched. Backticks run at priority 190, before
        # the inline math processor, for the same reason.
        md.preprocessors.register(
            DisplayMathPreprocessor(md), "lesson_display_math", 24
        )
        md.inlinePatterns.register(
            InlineMathProcessor(_INLINE_MATH, md), "lesson_inline_math", 185
        )


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
