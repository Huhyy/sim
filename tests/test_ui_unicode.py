import re

from sim_app.content.translations import UI_TEXT, get_localized_narrative, get_display_pre_sections, get_display_post_sections
from sim_app.application.participant_views import _stage_view
from sim_app.application.state import ParticipantState
from sim_app.config import SCENARIO_VERSION


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from strings(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from strings(child)


def test_all_ui_copy_has_no_corrupt_unicode_or_question_marks_inside_words():
    content = [UI_TEXT]
    for language in ("ro", "en"):
        content.extend([get_display_pre_sections(language), get_display_post_sections(language)])
        content.extend(get_localized_narrative(month, language) for month in range(1, 25))
    for text in strings(content):
        assert "\ufffd" not in text, text
        assert not re.search(r"\w\?\w", text), text
        assert not re.search(r"[ÃÄÈ][\x80-\xbf]", text), text
    consent = UI_TEXT["ro"]["consent"]["markdown"]
    assert "?" not in consent
    assert "consimțământ informat" in consent
    assert "informațiile" in consent


def test_corrected_consent_still_omits_battery_copy_when_disabled():
    state = ParticipantState.initial(SCENARIO_VERSION)
    state.language = "ro"
    state.experimental_condition = "C5"
    view = _stage_view(state, "consent", "ro")
    assert "consimțământ informat" in view["content"]
    assert "- vei răspunde la un chestionar psihologic inițial;" not in view["content"]
    assert "- răspunsuri la chestionare psihometrice;" not in view["content"]
