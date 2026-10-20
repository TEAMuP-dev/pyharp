"""
Tests for build_endpoint: what it tells HARP about a model, and what it refuses.
"""

import multiprocessing
import os
import sys
import time
from pathlib import Path

import gradio as gr
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyharp import ModelCard, build_endpoint  # noqa: E402
from pyharp.core import (check_output_files, enforce_output_file_types,  # noqa: E402
                         rename_outputs)
from pyharp.tags import Channels, Subcategory  # noqa: E402
from pyharp.worker import JobSupervisor  # noqa: E402


def card(**kwargs):
    fields = dict(name="Probe", author="TEAMuP", description="What it does.", tags=[])
    fields.update(kwargs)

    return ModelCard(**fields)


def endpoint(process_fn, inputs=None, outputs=None, **kwargs):
    """
    Builds an endpoint and hands back its widgets and the Blocks holding it.

    Its worker is not started unless a test asks for it, since nothing here runs a job.
    """
    kwargs.setdefault("warm_start", False)

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


def test_the_worker_starts_with_the_endpoint():
    before = {child.pid for child in multiprocessing.active_children()}

    endpoint(passthrough, warm_start=True)

    deadline = time.monotonic() + 30
    started = []

    while not started and time.monotonic() < deadline:
        started = [c for c in multiprocessing.active_children() if c.pid not in before]
        time.sleep(0.05)

    for child in started:
        JobSupervisor._end_process(child)

    # Started by building the endpoint, with no request having reached it
    assert len(started) == 1


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


# --------------------------------------------------------------------------------
# Output file names
# --------------------------------------------------------------------------------


def touch(directory, name):
    path = directory / name
    path.write_bytes(b"data")

    return str(path)


def test_results_are_named_after_the_input_the_model_and_the_output(tmp_path):
    song = touch(tmp_path, "My Song_0123456789abcdef0123456789abcdef.wav")
    inputs = [gr.Audio(type="filepath"), gr.Slider()]
    outputs = [gr.Audio(type="filepath", label="Vocals"), gr.File(label="Sung Notes")]

    vocals, notes = rename_outputs((touch(tmp_path, "tmp3kx9q.wav"), touch(tmp_path, "out.mid")),
                                   [song, 3], inputs, outputs, "Open-Unmix")

    # HARP's download id is dropped, so a chain of models does not carry it forward
    assert Path(vocals).name == "My-Song_open-unmix_vocals.wav"
    assert Path(notes).name == "My-Song_open-unmix_sung-notes.mid"
    assert Path(vocals).read_bytes() == b"data"


def test_the_time_harp_stamps_on_a_download_is_dropped_too(tmp_path):
    take = touch(tmp_path, "My Song_open-unmix_vocals_10-20-2026_14-35-12 (2).wav")
    result = rename_outputs(touch(tmp_path, "x.wav"), [take], [gr.Audio(type="filepath")],
                            [gr.Audio(type="filepath", label="Drums")], "Demucs")

    assert Path(result).name == "My-Song_open-unmix_vocals_demucs_drums.wav"


def test_a_model_without_a_file_input_names_results_after_itself(tmp_path):
    result = rename_outputs(touch(tmp_path, "output.wav"), ["a prompt"], [gr.Textbox()],
                            [gr.Audio(type="filepath", label="Generated Audio")], "MusicGen")

    assert Path(result).name == "musicgen_generated-audio.wav"


def test_outputs_sharing_a_label_or_lacking_one_are_told_apart_by_position(tmp_path):
    outputs = [gr.Audio(type="filepath", label="Take"), gr.Audio(type="filepath", label="Take"),
               gr.Audio(type="filepath")]
    names = [Path(p).name for p in rename_outputs(
        tuple(touch(tmp_path, f"{n}.wav") for n in "abc"), [], [], outputs, "TRIA")]

    assert names == ["tria_take-1.wav", "tria_take-2.wav", "tria_3.wav"]


def test_values_that_are_not_files_pass_through(tmp_path):
    labels = {"labels": []}
    array_audio = (44100, [0.0])
    outputs = [gr.JSON(), gr.Audio(type="numpy", label="Audio"), gr.Audio(type="filepath")]

    assert rename_outputs((labels, array_audio, None), [], [], outputs, "Probe") == \
        (labels, array_audio, None)


def test_a_list_of_files_is_numbered(tmp_path):
    files = [touch(tmp_path, "x.mid"), touch(tmp_path, "y.mid")]
    result = rename_outputs(files, [], [], [gr.File(label="Stems", file_count="multiple")], "Probe")

    assert [Path(p).name for p in result] == ["probe_stems-1.mid", "probe_stems-2.mid"]


def test_the_endpoint_renames_what_the_worker_returns(tmp_path, progress):
    import jobs

    song = touch(tmp_path, "riff.wav")
    _, demo = endpoint(jobs.write_temporary_output, inputs=[gr.Audio(type="filepath")],
                       outputs=[gr.Audio(type="filepath", label="Accompaniment")],
                       model_card=card(name="AnyAccomp"))
    handler = next(spec.fn for spec in demo.fns.values() if spec.api_name == "process")

    try:
        result = handler(song, progress)
    finally:
        for child in multiprocessing.active_children():
            JobSupervisor._end_process(child)

    assert Path(result).name == "riff_anyaccomp_accompaniment.wav"
