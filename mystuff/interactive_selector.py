"""Reusable fuzzy selectors for interactive CLI choices."""

import sys
from typing import Any, Callable, Dict, Iterable, List, Optional, TypeVar

import typer

T = TypeVar("T")


def fuzzy_match_score(label: str, query: str) -> Optional[int]:
    normalized_label = label.lower()
    normalized_query = " ".join(query.lower().split())
    if not normalized_query:
        return 0

    query_tokens = normalized_query.split()
    if all(token in normalized_label for token in query_tokens):
        first_index = min(normalized_label.index(token) for token in query_tokens)
        return first_index + len(normalized_label) - len(normalized_query)

    score = len(normalized_label)
    search_from = 0
    last_index = -1
    for char in normalized_query:
        index = normalized_label.find(char, search_from)
        if index == -1:
            return None
        if last_index >= 0:
            score += index - last_index - 1
            if index == last_index + 1:
                score -= 1
        else:
            score += index
        last_index = index
        search_from = index + 1

    return score


def fuzzy_filter_labels(
    labels: Iterable[str], query: str, *, limit: Optional[int] = None
) -> List[str]:
    scored_labels = []
    for index, label in enumerate(labels):
        score = fuzzy_match_score(label, query)
        if score is not None:
            scored_labels.append((score, index, label))

    scored_labels.sort(key=lambda item: (item[0], item[1]))
    matches = [label for _, _, label in scored_labels]
    if limit is not None:
        return matches[:limit]
    return matches


def can_use_native_selector() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def select_label(
    labels: Iterable[str],
    prompt: str,
    *,
    use_selector: bool = True,
) -> Optional[str]:
    label_list = list(labels)
    if not label_list:
        return None

    if use_selector and can_use_native_selector():
        return _select_with_native_fuzzy(label_list, prompt)

    return _select_with_search_prompt(label_list, prompt)


def select_from_options(
    items: Iterable[T],
    label_factory: Callable[[T], str],
    prompt: str,
    *,
    use_selector: bool = True,
) -> Optional[T]:
    labels: List[str] = []
    label_to_item: Dict[str, T] = {}
    for index, item in enumerate(items, start=1):
        label = label_factory(item)
        if label in label_to_item:
            label = f"{label} #{index}"
        labels.append(label)
        label_to_item[label] = item

    selected_label = select_label(labels, prompt, use_selector=use_selector)
    if selected_label is None:
        return None
    return label_to_item.get(selected_label)


def _select_with_native_fuzzy(labels: List[str], prompt: str) -> Optional[str]:
    try:
        import curses
    except ImportError:
        return None

    def run_selector(screen: Any) -> Optional[str]:
        query = ""
        selected_index = 0
        top_index = 0
        try:
            curses.curs_set(1)
        except curses.error:
            pass
        curses.use_default_colors()

        while True:
            height, width = screen.getmaxyx()
            visible_rows = max(1, height - 4)
            matches = fuzzy_filter_labels(labels, query)
            if selected_index >= len(matches):
                selected_index = max(0, len(matches) - 1)
            if selected_index < top_index:
                top_index = selected_index
            if selected_index >= top_index + visible_rows:
                top_index = selected_index - visible_rows + 1

            screen.erase()
            title = f"{prompt}{query}"
            screen.addnstr(0, 0, title, max(1, width - 1), curses.A_BOLD)
            screen.addnstr(
                1,
                0,
                "Type to search | Up/Down move | Enter select | Esc cancel",
                max(1, width - 1),
                curses.A_DIM,
            )

            if not matches:
                screen.addnstr(3, 0, "No matches", max(1, width - 1), curses.A_DIM)
            else:
                visible_matches = matches[top_index : top_index + visible_rows]
                for row, label in enumerate(visible_matches, start=3):
                    match_index = top_index + row - 3
                    style = curses.A_REVERSE if match_index == selected_index else 0
                    screen.addnstr(row, 0, label, max(1, width - 1), style)

            screen.move(0, min(len(title), max(0, width - 1)))
            key = screen.get_wch()

            if key in ("\n", "\r", curses.KEY_ENTER):
                if matches:
                    return matches[selected_index]
                curses.beep()
                continue
            if key == "\x1b":
                return None
            if key in ("\x03", "\x04"):
                raise KeyboardInterrupt
            if key in ("\x7f", "\b"):
                query = query[:-1]
                selected_index = 0
                top_index = 0
                continue
            if key == "\x15":
                query = ""
                selected_index = 0
                top_index = 0
                continue
            if key in ("\x0e", curses.KEY_DOWN):
                if matches:
                    selected_index = min(selected_index + 1, len(matches) - 1)
                continue
            if key in ("\x10", curses.KEY_UP):
                selected_index = max(0, selected_index - 1)
                continue

            if isinstance(key, str) and key.isprintable():
                query += key
                selected_index = 0
                top_index = 0

    try:
        return curses.wrapper(run_selector)
    except (KeyboardInterrupt, curses.error):
        return None


def _select_with_search_prompt(labels: List[str], prompt: str) -> Optional[str]:
    query = ""
    prompt_label = prompt.rstrip(": ")
    while True:
        matches = fuzzy_filter_labels(labels, query, limit=8)
        typer.echo(prompt_label)
        if query:
            typer.echo(f"Search: {query}")
        if matches:
            for index, label in enumerate(matches, start=1):
                typer.echo(f"{index}. {label}")
        else:
            typer.echo("No matches.")

        raw_choice = typer.prompt(
            "Choose number, type search, Enter selects first, /cancel cancels",
            default="",
            show_default=False,
        )
        choice = str(raw_choice).strip()
        if choice == "/cancel":
            return None
        if not choice:
            if matches:
                return matches[0]
            query = ""
            continue

        if choice.startswith("\x1b"):
            typer.echo("Use a number to select in prompt mode.")
            continue

        if choice.isdigit():
            numeric_index = int(choice)
            if 1 <= numeric_index <= len(matches):
                return matches[numeric_index - 1]
            typer.echo("❌ Invalid selection.")
            continue

        query = choice
