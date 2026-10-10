"""
Tests for how Gradio components are read: what HARP is told each one is, and the
input and output tags inferred from them.
"""

import os
import sys

import gradio as gr
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyharp.core import (  # noqa: E402
    HarpAudioTrack,
    HarpDropdown,
    HarpFileComponent,
    HarpJSON,
    HarpMidiTrack,
    HarpNumberBox,
    HarpSlider,
    HarpTextBox,
    HarpToggle,
    get_declared_formats,
    get_harp_component,
    get_io_tags,
    is_midi_file,
)
from pyharp.tags import INPUT_KEY, OUTPUT_KEY  # noqa: E402

MIDI_TYPES = [".mid", ".midi"]


# --------------------------------------------------------------------------------
# What HARP is told a component is
# --------------------------------------------------------------------------------


@pytest.mark.parametrize("component, expected", [
    (lambda: gr.Audio(type="filepath"), HarpAudioTrack),
    (lambda: gr.File(type="filepath", file_types=MIDI_TYPES), HarpMidiTrack),
    (lambda: gr.File(type="filepath", file_types=[".json"]), HarpFileComponent),
    (lambda: gr.File(type="filepath"), HarpFileComponent),
    (lambda: gr.Slider(minimum=0, maximum=1), HarpSlider),
    (lambda: gr.Number(value=1), HarpNumberBox),
    (lambda: gr.Textbox(value="x"), HarpTextBox),
    (lambda: gr.Checkbox(value=True), HarpToggle),
    (lambda: gr.Dropdown(choices=["a", "b"]), HarpDropdown),
    (lambda: gr.JSON(), HarpJSON),
])
def test_each_supported_component_maps_to_its_harp_counterpart(component, expected):
    assert isinstance(get_harp_component(component()), expected)


def test_an_unsupported_component_is_refused():
    with pytest.raises(ValueError):
        get_harp_component(gr.Image())


def test_a_track_has_to_carry_a_filepath():
    """HARP sends a path, so any other type would arrive as something it cannot read."""
    with pytest.raises(AssertionError):
        get_harp_component(gr.Audio(type="numpy"))


def test_midi_file_types_make_a_track_rather_than_a_file_picker():
    assert is_midi_file(gr.File(type="filepath", file_types=MIDI_TYPES))
    assert not is_midi_file(gr.File(type="filepath", file_types=[".json"]))
    assert not is_midi_file(gr.File(type="filepath"))


def test_either_midi_extension_is_enough():
    assert is_midi_file(gr.File(type="filepath", file_types=[".mid"]))
    assert is_midi_file(gr.File(type="filepath", file_types=[".midi"]))


def test_a_track_is_required_unless_marked_otherwise():
    assert get_harp_component(gr.Audio(type="filepath")).required
    assert not get_harp_component(gr.Audio(type="filepath").harp_required(False)).required


def test_set_info_is_what_HARP_shows_beside_a_track():
    track = gr.Audio(type="filepath").set_info("A dry vocal.")

    assert get_harp_component(track).info == "A dry vocal."


def test_a_control_carries_the_info_gradio_was_given():
    assert get_harp_component(gr.Slider(minimum=0, maximum=1, info="Amount.")).info == "Amount."


# --------------------------------------------------------------------------------
# The formats a component restricts itself to
# --------------------------------------------------------------------------------


def test_an_audio_output_is_restricted_by_its_format():
    audio = gr.Audio(type="filepath", format="wav")

    assert get_declared_formats(audio, is_output=True) == ["wav"]


def test_an_audio_output_without_a_format_is_unrestricted():
    """Leaving it unset is what lets a model return the container it was given."""
    audio = gr.Audio(type="filepath")

    assert get_declared_formats(audio, is_output=True) == []


def test_an_audio_input_is_never_restricted_by_format():
    """Its format only sets what Gradio converts incoming audio to."""
    audio = gr.Audio(type="filepath", format="wav")

    assert get_declared_formats(audio, is_output=False) == []


def test_a_generic_file_is_restricted_by_its_file_types():
    """Extensions keep their dot here, and io_tag strips it for the tag itself."""
    generic = gr.File(type="filepath", file_types=[".json", ".txt"])

    assert get_declared_formats(generic, is_output=True) == [".json", ".txt"]


def test_a_file_type_category_names_no_single_format():
    """file_types can hold things like "audio", which is not an extension."""
    generic = gr.File(type="filepath", file_types=["audio", ".nam"])

    assert get_declared_formats(generic, is_output=False) == [".nam"]


def test_midi_is_not_described_by_format():
    midi = gr.File(type="filepath", file_types=MIDI_TYPES)

    assert get_declared_formats(midi, is_output=True) == []


# --------------------------------------------------------------------------------
# The tags inferred from a set of components
# --------------------------------------------------------------------------------


def tags_for(key, components):
    return get_io_tags(key, components, [get_harp_component(c) for c in components])


def test_each_kind_of_data_is_tagged():
    components = [
        gr.Audio(type="filepath"),
        gr.File(type="filepath", file_types=MIDI_TYPES),
        gr.File(type="filepath"),
        gr.Textbox(value="x"),
    ]

    assert tags_for(INPUT_KEY, components) == [
        "input:audio", "input:midi", "input:file", "input:text"
    ]


def test_a_json_output_is_tagged_as_labels():
    assert tags_for(OUTPUT_KEY, [gr.JSON()]) == ["output:labels"]


def test_controls_are_not_tagged():
    """Only the data a model takes in and gives back is described this way."""
    controls = [gr.Slider(minimum=0, maximum=1), gr.Checkbox(), gr.Dropdown(choices=["a"])]

    assert tags_for(INPUT_KEY, controls) == []


def test_two_components_of_one_kind_are_tagged_once():
    two = [gr.Audio(type="filepath"), gr.Audio(type="filepath")]

    assert tags_for(INPUT_KEY, two) == ["input:audio"]


def test_formats_keep_two_files_of_one_kind_apart():
    two = [
        gr.File(type="filepath", file_types=[".json"]),
        gr.File(type="filepath", file_types=[".nam"]),
    ]

    assert tags_for(INPUT_KEY, two) == ["input:file/json", "input:file/nam"]


def test_an_audio_output_carries_the_format_it_fixes():
    assert tags_for(OUTPUT_KEY, [gr.Audio(type="filepath", format="wav")]) == [
        "output:audio/wav"
    ]
