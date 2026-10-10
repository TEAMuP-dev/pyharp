"""
Tests for the output labels HARP draws over a track.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyharp.labels import AudioLabel, LabelList, MidiLabel, OutputLabel  # noqa: E402


def test_a_label_reports_its_own_type():
    """HARP reads label_type to tell which kind of label it was given."""
    assert OutputLabel(t=0.0, label="a").label_type == "OutputLabel"
    assert AudioLabel(t=0.0, label="a").label_type == "AudioLabel"
    assert MidiLabel(t=0.0, label="a").label_type == "MidiLabel"


def test_a_label_keeps_what_it_was_given():
    label = AudioLabel(t=1.5, label="hit", duration=0.25, amplitude=0.8, description="loud")

    assert (label.t, label.label, label.duration) == (1.5, "hit", 0.25)
    assert (label.amplitude, label.description) == (0.8, "loud")


def test_the_optional_fields_default_to_nothing():
    label = OutputLabel(t=0.0, label="a")

    assert (label.duration, label.description, label.color, label.link) == (0.0, None, 0, None)


def test_a_list_declares_the_type_HARP_matches_on():
    assert LabelList().meta == {"_type": "pyharp.LabelList"}


def test_a_list_keeps_the_meta_it_was_given():
    labels = LabelList(meta={"model": "demo", "run": "7"})

    assert labels.meta["model"] == "demo" and labels.meta["run"] == "7"
    assert labels.meta["_type"] == "pyharp.LabelList"


def test_the_declared_type_cannot_be_overwritten():
    """HARP reads it to tell the output apart, so it is set last."""
    assert LabelList(meta={"_type": "something else"}).meta["_type"] == "pyharp.LabelList"


def test_appending_collects_labels():
    labels = LabelList()
    labels.append(AudioLabel(t=0.0, label="a"))
    labels.append(AudioLabel(t=1.0, label="b"))

    assert [label.label for label in labels.labels] == ["a", "b"]


def test_a_list_serializes_to_what_gradio_sends():
    """
    gr.JSON serializes with orjson, which takes a dataclass instance as it stands, so
    label_type travels even though it is not a declared field. HARP reads that field to
    tell the label kinds apart, and dataclasses.asdict drops it, so the check has to be
    made against the real payload.
    """
    import gradio as gr

    labels = LabelList(labels=[MidiLabel(t=0.0, label="C4", pitch=60)])
    payload = gr.JSON().postprocess(labels).root

    assert payload["meta"]["_type"] == "pyharp.LabelList"
    assert payload["labels"][0]["pitch"] == 60
    assert payload["labels"][0]["label_type"] == "MidiLabel"


@pytest.mark.parametrize("alpha, expected_alpha", [(0.5, 128), (1.0, 255), (0.0, 0)])
def test_a_hex_color_carries_its_alpha(alpha, expected_alpha):
    packed = OutputLabel.hex_color_to_int("#FF0000", a=alpha)

    assert (packed >> 24) & 0xFF == expected_alpha
    assert packed & 0xFFFFFF == 0xFF0000


def test_a_hex_color_reads_with_or_without_the_hash():
    assert OutputLabel.hex_color_to_int("#00FF00") == OutputLabel.hex_color_to_int("00FF00")


def test_an_rgb_color_packs_each_channel():
    packed = OutputLabel.rgb_color_to_int(0x12, 0x34, 0x56, a=1.0)

    assert packed == (255 << 24) + (0x12 << 16) + (0x34 << 8) + 0x56
