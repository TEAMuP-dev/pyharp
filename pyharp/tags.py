"""
Tags describing what a HARP model does and the data it handles.

Tags are declared in the model card (see ModelCard), which HARP reads once a model is
loaded. They are plain strings, so that a model hosted as a Hugging Face Space can also list
them in its README metadata, where HARP reads them to categorize the model before it is
loaded (see "Tags" in the pyharp README).

Structured tags take the form "<key>:<value>" (e.g., "category:separation"), and any other
string is a custom tag, shown and searched as-is.

The taxonomy itself lives in taxonomy.json, which HARP embeds when it is built, so the two
cannot disagree. A HARP built against an older taxonomy still shows a tag it does not
recognize, just without categorizing the model by it.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, List, Union

import json


__all__ = [
    'Category',
    'Subcategory',
    'SampleRate',
    'Channels',
    'Modality',
    'Tag',
    'build_tags',
    'validate_tag'
]


class _Category(Enum):
    def __init__(self, taxonomy_id: str, display_name: str):
        self.id = taxonomy_id
        self.display_name = display_name

    @property
    def tag(self) -> str:
        return f"{CATEGORY_KEY}:{self.id}"


class _Subcategory(Enum):
    def __init__(self, category: "Category", taxonomy_id: str, display_name: str):
        self.category = category
        self.id = taxonomy_id
        self.display_name = display_name

    @property
    def tag(self) -> str:
        return f"{SUBCATEGORY_KEY}:{self.id}"


def _member_name(taxonomy_id: str) -> str:
    return taxonomy_id.upper().replace("-", "_")


# The taxonomy is defined once, in taxonomy.json, which HARP also embeds when it is built
_TAXONOMY = json.loads((Path(__file__).parent / "taxonomy.json").read_text(encoding="utf-8"))

# Top level of the audio production model taxonomy, e.g. Category.SEPARATION
Category = _Category("Category", [
    (_member_name(c["id"]), (c["id"], c["name"])) for c in _TAXONOMY["categories"]
])

# Second level of the taxonomy, e.g. Subcategory.STEM_SEPARATION. Each subcategory belongs
# to exactly one category, and ids are unique across the whole taxonomy so that a
# subcategory tag alone is enough to place a model.
Subcategory = _Subcategory("Subcategory", [
    (_member_name(s["id"]), (Category[_member_name(c["id"])], s["id"], s["name"]))
    for c in _TAXONOMY["categories"] for s in c["subcategories"]
])


class Modality(Enum):
    """
    Kind of data a model takes in or gives back. These are inferred from the Gradio
    components passed to build_endpoint, so they never have to be declared by hand.
    """

    AUDIO = "audio"
    MIDI = "midi"
    TEXT = "text"
    FILE = "file"
    LABELS = "labels"


CATEGORY_KEY = "category"
SUBCATEGORY_KEY = "subcategory"
INPUT_KEY = "input"
OUTPUT_KEY = "output"
SAMPLE_RATE_KEY = "sample-rate"
CHANNELS_KEY = "channels"

# Extensions naming the same format, reduced to one so that it is tagged once
FORMAT_ALIASES = {"wave": "wav", "aif": "aiff"}


@dataclass(frozen=True)
class SampleRate:
    """
    The model's sample rate, e.g. SampleRate(44100).
    """

    hz: int

    def __post_init__(self):
        if int(self.hz) <= 0:
            raise ValueError(f"Sample rate must be a positive number of Hz, not {self.hz}.")

    @property
    def tag(self) -> str:
        return f"{SAMPLE_RATE_KEY}:{int(self.hz)}"


@dataclass(frozen=True)
class Channels:
    """
    The model's number of audio channels, e.g. Channels(2). Any positive count is accepted:
    one and two channels are tagged by name ("channels:mono" and "channels:stereo"), and any
    other count by number (e.g., "channels:6").
    """

    count: int

    # Counts that are tagged by name rather than by number
    NAMES = {1: "mono", 2: "stereo"}

    def __post_init__(self):
        if int(self.count) <= 0:
            raise ValueError(f"Number of channels must be positive, not {self.count}.")

    @property
    def tag(self) -> str:
        return f"{CHANNELS_KEY}:{self.NAMES.get(int(self.count), int(self.count))}"


# Anything that can go in a model card's tag list
Tag = Union[str, Category, Subcategory, SampleRate, Channels]


def _check_unique_ids():
    ids = [c.id for c in Category] + [s.id for s in Subcategory]
    duplicates = {i for i in ids if ids.count(i) > 1}
    assert not duplicates, f"Taxonomy ids must be unique, but {duplicates} repeat"


_check_unique_ids()


def validate_tag(tag: str) -> str:
    """
    Check a tag given as a string.

    Custom tags are free-form, but a string using one of the structured keys must carry a
    value HARP can interpret, since a misspelled category would otherwise leave the model
    silently uncategorized.

    Args:
        tag (str): Tag to check.

    Returns:
        tag (str): The tag, stripped of surrounding whitespace.

    Raises:
        ValueError: If the tag is empty, or uses a structured key with an invalid value.
    """

    tag = str(tag).strip()

    if not tag:
        raise ValueError("Tags cannot be empty.")

    key, _, value = tag.partition(":")

    if key == CATEGORY_KEY and value not in {c.id for c in Category}:
        raise ValueError(f"Unknown category in tag '{tag}'. Choose one of "
                         f"{[c.id for c in Category]}.")
    if key == SUBCATEGORY_KEY and value not in {s.id for s in Subcategory}:
        raise ValueError(f"Unknown subcategory in tag '{tag}'. Choose one of "
                         f"{[s.id for s in Subcategory]}.")
    if key in (INPUT_KEY, OUTPUT_KEY):
        raise ValueError(f"Tag '{tag}' is inferred from the Gradio components passed to "
                         f"build_endpoint, so it cannot be given by hand.")
    if key == SAMPLE_RATE_KEY and not value.isdigit():
        raise ValueError(f"Sample rate in tag '{tag}' must be a whole number of Hz.")

    return tag


def io_tag(key: str, modality: Modality, formats: Iterable[str] = ()) -> str:
    """
    Obtain the tag for one input or output of a model.

    Args:
        key (str): INPUT_KEY or OUTPUT_KEY.
        modality (Modality): Kind of data it carries.
        formats (Iterable[str]): File extensions it is restricted to, if any.

    Returns:
        tag (str): The tag, with any formats after a "/" and separated by "|", e.g.
            "output:file/json|txt", or without, e.g. "output:audio", when it is not
            restricted to any. A comma would split the tag in an inline YAML list.
    """

    extensions = [str(f).strip().lstrip(".").lower() for f in formats]
    extensions = list(dict.fromkeys(FORMAT_ALIASES.get(e, e) for e in extensions if e))

    if not extensions:
        return f"{key}:{modality.value}"

    return f"{key}:{modality.value}/{'|'.join(extensions)}"


def build_tags(tags: Iterable[Tag] = (), inferred: Iterable[str] = ()) -> List[str]:
    """
    Assemble the full tag list for a model, as HARP reads it.

    Args:
        tags (Iterable[Tag]): The model card's tags. A Category or Subcategory places the
            model in the taxonomy (a subcategory implies its category), SampleRate and
            Channels describe the audio it works with, and a string is a custom tag.
        inferred (Iterable[str]): Tags for the model's inputs and outputs, as inferred from
            its Gradio components (see io_tag).

    Returns:
        tags (List[str]): Tags without duplicates, taxonomy first, then inputs and outputs,
            then the rest in the order given.

    Raises:
        ValueError: If a tag is invalid (see validate_tag).
    """

    taxonomy, others = [], []

    for tag in tags:
        if isinstance(tag, Subcategory):
            taxonomy += [tag.category.tag, tag.tag]
        elif isinstance(tag, Category):
            taxonomy.append(tag.tag)
        elif isinstance(tag, (SampleRate, Channels)):
            others.append(tag.tag)
        elif isinstance(tag, str):
            others.append(validate_tag(tag))
        else:
            raise ValueError(f"'{tag}' is not a Category, Subcategory, SampleRate, Channels, "
                             f"or string.")

    # Preserve order while dropping repeats (e.g., a category implied twice)
    return list(dict.fromkeys(taxonomy + list(inferred) + others))
