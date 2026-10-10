"""
Tests for the tags a model declares, and for the taxonomy behind them.

HARP categorizes and searches by these, and a tag it cannot place is shown as a custom
tag rather than raising, so a value that is wrong in the model card has to be caught
here instead (see pyharp/tags.py).
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyharp.tags import (  # noqa: E402
    Category,
    Channels,
    Modality,
    SampleRate,
    Subcategory,
    build_tags,
    io_tag,
    validate_tag,
)


# --------------------------------------------------------------------------------
# The taxonomy
# --------------------------------------------------------------------------------


def test_every_subcategory_belongs_to_a_category():
    for subcategory in Subcategory:
        assert subcategory.category in list(Category)


def test_ids_are_unique_across_the_whole_taxonomy():
    """A subcategory tag alone has to be enough to place a model, so ids cannot repeat."""
    ids = [entry.id for entry in list(Category) + list(Subcategory)]

    assert len(ids) == len(set(ids))


def test_utility_has_no_subcategories():
    """It marks a tool rather than a model, so there is nothing to subdivide."""
    assert [s for s in Subcategory if s.category is Category.UTILITY] == []


# --------------------------------------------------------------------------------
# What a tag object produces
# --------------------------------------------------------------------------------


def test_a_category_tags_itself():
    assert Category.SEPARATION.tag == "category:separation"


def test_a_subcategory_tags_itself_without_its_category():
    """build_tags adds the category, so the tag itself names only the subcategory."""
    assert Subcategory.STEM_SEPARATION.tag == "subcategory:stem-separation"


def test_sample_rate_tags_in_hz():
    assert SampleRate(44100).tag == "sample-rate:44100"


@pytest.mark.parametrize("count, expected", [(1, "mono"), (2, "stereo"), (6, "6")])
def test_channels_are_named_where_a_name_exists(count, expected):
    assert Channels(count).tag == f"channels:{expected}"


@pytest.mark.parametrize("count", [0, -1])
def test_a_channel_count_has_to_be_positive(count):
    with pytest.raises(ValueError):
        Channels(count)


def test_a_sample_rate_has_to_be_positive():
    with pytest.raises(ValueError):
        SampleRate(0)


# --------------------------------------------------------------------------------
# Validating a tag given as a string
# --------------------------------------------------------------------------------


@pytest.mark.parametrize("tag", [
    "example",
    "pitch shift",
    "category:separation",
    "subcategory:stem-separation",
    "sample-rate:44100",
    "channels:mono",
    "channels:stereo",
    "channels:6",
])
def test_a_usable_tag_is_accepted(tag):
    assert validate_tag(tag) == tag


@pytest.mark.parametrize("tag", [
    "category:separtion",
    "subcategory:stem-seperation",
    "sample-rate:44.1kHz",
    "channels:banana",
    "channels:0",
    "",
    "   ",
])
def test_a_tag_HARP_could_not_place_is_rejected(tag):
    """
    HARP keeps an unrecognized structured tag as a custom one rather than raising, so a
    typo would leave the model quietly uncategorized unless it is caught here.
    """
    with pytest.raises(ValueError):
        validate_tag(tag)


@pytest.mark.parametrize("tag", ["input:audio", "output:audio/wav"])
def test_an_inferred_tag_cannot_be_given_by_hand(tag):
    with pytest.raises(ValueError):
        validate_tag(tag)


def test_surrounding_whitespace_is_dropped():
    assert validate_tag("  example  ") == "example"


# --------------------------------------------------------------------------------
# Assembling the list HARP reads
# --------------------------------------------------------------------------------


def test_a_subcategory_brings_its_category_with_it():
    tags = build_tags([Subcategory.STEM_SEPARATION])

    assert tags == ["category:separation", "subcategory:stem-separation"]


def test_naming_both_a_category_and_its_subcategory_does_not_repeat_it():
    tags = build_tags([Category.SEPARATION, Subcategory.STEM_SEPARATION])

    assert tags.count("category:separation") == 1


def test_the_taxonomy_leads_then_inputs_and_outputs_then_the_rest():
    tags = build_tags(
        [Category.EFFECTS, SampleRate(44100), "example"],
        inferred=["input:audio", "output:audio/wav"],
    )

    assert tags == [
        "category:effects",
        "input:audio",
        "output:audio/wav",
        "sample-rate:44100",
        "example",
    ]


def test_a_repeated_tag_appears_once():
    assert build_tags(["example", "example"]) == ["example"]


def test_a_tag_of_an_unusable_type_is_rejected():
    with pytest.raises(ValueError):
        build_tags([object()])


# --------------------------------------------------------------------------------
# Input and output tags
# --------------------------------------------------------------------------------


def test_an_unrestricted_modality_tags_without_a_format():
    assert io_tag("input", Modality.AUDIO) == "input:audio"


def test_restricted_formats_follow_the_tag():
    assert io_tag("output", Modality.FILE, [".json", ".txt"]) == "output:file/json|txt"


def test_formats_naming_one_thing_are_tagged_once():
    """A comma would split the tag in an inline YAML list, hence the pipe."""
    assert io_tag("input", Modality.AUDIO, [".wav", "wave"]) == "input:audio/wav"
