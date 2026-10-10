"""
Tests for build_endpoint: what it tells HARP about a model, and what it refuses.
"""

import os
import sys

import gradio as gr
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyharp import ModelCard, build_endpoint  # noqa: E402
from pyharp.core import check_output_files, enforce_output_file_types  # noqa: E402
from pyharp.tags import Channels, Subcategory  # noqa: E402


def card(**kwargs):
    fields = dict(name="Probe", author="TEAMuP", description="What it does.", tags=[])
    fields.update(kwargs)

    return ModelCard(**fields)


def endpoint(process_fn, inputs=None, outputs=None, **kwargs):
    """Builds an endpoint and hands back its widgets and the Blocks holding it."""
    with gr.Blocks() as demo:
        built = build_endpoint(
            model_card=kwargs.pop("model_card", card()),
            input_components=inputs if inputs is not None else [gr.Textbox(value="x")],
            output_components=outputs if outputs is not None else [gr.Audio(type="filepath")],
            process_fn=process_fn,
            **kwargs,
        )

    return built, demo


def model_info(demo):
    """
    The payload the View Controls button returns, which is everything HARP reads about
    a model before it has run anything.
    """
    for spec in demo.fns.values():
        handler = getattr(spec, "fn", None)

        if handler is None or not callable(handler):
            continue

        try:
            value = handler()
        except TypeError:
            continue

        if isinstance(value, dict) and "card" in value:
            return value

    raise AssertionError("no controls handler found")


def passthrough(value):
    return value


# --------------------------------------------------------------------------------
# What build_endpoint hands back
# --------------------------------------------------------------------------------


def test_it_returns_the_widgets_HARP_drives():
    built, _ = endpoint(passthrough)

    assert set(built) == {"controls_data", "controls_button", "process_button", "cancel_button"}


def test_the_payload_describes_the_card_its_inputs_and_its_outputs():
    _, demo = endpoint(
        passthrough,
        inputs=[gr.Audio(type="filepath").set_info("The input."), gr.Slider(minimum=0, maximum=4)],
        outputs=[gr.Audio(type="filepath", format="wav")],
    )
    info = model_info(demo)

    assert info["card"]["name"] == "Probe"
    assert info["card"]["author"] == "TEAMuP"
    assert info["card"]["description"] == "What it does."
    assert [cmp["info"] for cmp in info["inputs"]][0] == "The input."
    assert len(info["inputs"]) == 2 and len(info["outputs"]) == 1


def test_the_payload_tags_carry_both_the_declared_and_the_inferred():
    model_card = card(tags=[Subcategory.STEM_SEPARATION, Channels(2), "demo"])
    _, demo = endpoint(
        passthrough,
        inputs=[gr.Audio(type="filepath")],
        outputs=[gr.Audio(type="filepath", format="wav")],
        model_card=model_card,
    )

    assert model_info(demo)["card"]["tags"] == [
        "category:separation",
        "subcategory:stem-separation",
        "input:audio",
        "output:audio/wav",
        "channels:stereo",
        "demo",
    ]


def test_a_card_tag_cannot_claim_an_inferred_one():
    """input: and output: are the components' to declare, so the card cannot set them."""
    with pytest.raises(ValueError):
        endpoint(passthrough, model_card=card(tags=["input:audio"]))


# --------------------------------------------------------------------------------
# What it refuses
# --------------------------------------------------------------------------------


def test_an_async_process_fn_is_refused():
    """
    The worker returns a value, and a coroutine is an object instead, so this is said
    here rather than left to fail as a pickling error on the first request.
    """
    async def process_fn(value):
        return value

    with pytest.raises(ValueError, match="async"):
        endpoint(process_fn)


def test_a_generator_process_fn_is_refused():
    def process_fn(value):
        yield value

    with pytest.raises(ValueError, match="generator"):
        endpoint(process_fn)


def test_an_async_generator_process_fn_is_refused():
    async def process_fn(value):
        yield value

    with pytest.raises(ValueError, match="generator"):
        endpoint(process_fn)


def test_a_plain_process_fn_is_accepted():
    built, _ = endpoint(passthrough)

    assert built


# --------------------------------------------------------------------------------
# Where a component can be placed
# --------------------------------------------------------------------------------


@pytest.mark.parametrize("control", [
    lambda: gr.Slider(minimum=0, maximum=1),
    lambda: gr.Number(value=1),
    lambda: gr.Textbox(value="x"),
    lambda: gr.Checkbox(value=True),
    lambda: gr.Dropdown(choices=["a"]),
])
def test_a_control_cannot_be_an_output(control):
    """
    HARP has no output component for a control, and would refuse the model by a type
    name the app never wrote, so this is said here instead.
    """
    with pytest.raises(ValueError, match="cannot be an output"):
        endpoint(passthrough, outputs=[control()])


def test_labels_cannot_be_an_input():
    with pytest.raises(ValueError, match="cannot be an input"):
        endpoint(passthrough, inputs=[gr.JSON()])


def test_a_refusal_points_at_the_generic_file():
    """A gr.File carries whatever HARP has no component for, in either position."""
    with pytest.raises(ValueError, match="gr.File"):
        endpoint(passthrough, outputs=[gr.Textbox()])

    with pytest.raises(ValueError, match="gr.File"):
        endpoint(passthrough, inputs=[gr.JSON()])


@pytest.mark.parametrize("component", [
    lambda: gr.Audio(type="filepath"),
    lambda: gr.File(type="filepath", file_types=[".mid", ".midi"]),
    lambda: gr.File(type="filepath"),
])
def test_tracks_and_files_are_accepted_in_either_position(component):
    assert endpoint(passthrough, inputs=[component()], outputs=[component()])


# --------------------------------------------------------------------------------
# Output file types
# --------------------------------------------------------------------------------


def test_a_declared_output_type_passes():
    outputs = [gr.File(type="filepath", file_types=[".json"], label="Out")]

    check_output_files("result.json", outputs)


def test_an_undeclared_output_type_is_reported():
    outputs = [gr.File(type="filepath", file_types=[".json"], label="Out")]

    with pytest.raises(gr.Error, match="file types"):
        check_output_files("result.txt", outputs)


def test_an_output_without_file_types_accepts_anything():
    check_output_files("result.anything", [gr.File(type="filepath")])


def test_a_missing_output_is_not_a_type_error():
    """An output of None is Gradio's way of leaving a track untouched."""
    check_output_files(None, [gr.File(type="filepath", file_types=[".json"])])


def test_every_output_is_checked():
    outputs = [
        gr.File(type="filepath", file_types=[".json"], label="First"),
        gr.File(type="filepath", file_types=[".txt"], label="Second"),
    ]

    check_output_files(("a.json", "b.txt"), outputs)

    with pytest.raises(gr.Error, match="Second"):
        check_output_files(("a.json", "b.json"), outputs)


def test_the_check_is_skipped_where_no_output_declares_types():
    """Nothing to enforce, so process_fn is handed back untouched."""
    assert enforce_output_file_types(passthrough, [gr.Audio(type="filepath")]) is passthrough


def test_the_check_keeps_the_signature_gradio_inspects():
    import inspect

    outputs = [gr.File(type="filepath", file_types=[".json"])]
    wrapped = enforce_output_file_types(passthrough, outputs)

    assert wrapped is not passthrough
    assert inspect.signature(wrapped) == inspect.signature(passthrough)
