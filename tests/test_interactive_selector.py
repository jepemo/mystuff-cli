from mystuff import interactive_selector


def test_fuzzy_filter_labels_prefers_direct_match():
    labels = [
        "foundations - Intro",
        "systems - Distributed Reads",
        "ai lab - Experiments",
    ]

    matches = interactive_selector.fuzzy_filter_labels(labels, "sys")

    assert matches[0] == "systems - Distributed Reads"


def test_select_label_prompt_filters_then_selects_number(monkeypatch):
    labels = ["foundations - Intro", "systems - Distributed Reads"]
    choices = iter(["sys", "1"])
    monkeypatch.setattr(
        interactive_selector.typer,
        "prompt",
        lambda *args, **kwargs: next(choices),
    )

    selected = interactive_selector.select_label(
        labels,
        "Select track: ",
        use_selector=False,
    )

    assert selected == "systems - Distributed Reads"


def test_select_from_options_maps_selected_label_to_item(monkeypatch):
    items = [
        {"track_id": "foundations", "name": "Foundations"},
        {"track_id": "systems", "name": "Systems"},
    ]
    choices = iter(["sys", "1"])
    monkeypatch.setattr(
        interactive_selector.typer,
        "prompt",
        lambda *args, **kwargs: next(choices),
    )

    selected = interactive_selector.select_from_options(
        items,
        lambda item: f"{item['track_id']} - {item['name']}",
        "Select track: ",
        use_selector=False,
    )

    assert selected == {"track_id": "systems", "name": "Systems"}


def test_select_label_prompt_ignores_arrow_escape(monkeypatch):
    labels = ["foundations - Intro", "systems - Distributed Reads"]
    choices = iter(["\x1b[A", "1"])
    monkeypatch.setattr(
        interactive_selector.typer,
        "prompt",
        lambda *args, **kwargs: next(choices),
    )

    selected = interactive_selector.select_label(
        labels,
        "Select track: ",
        use_selector=False,
    )

    assert selected == "foundations - Intro"
