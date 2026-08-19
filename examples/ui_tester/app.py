"""
UI Tester: a reference app exercising every PyHARP feature.

Unlike the other examples, this app does no real processing. It exists to
verify that HARP renders each supported input control, each track type, and
each output label type correctly. Use it as a lookup for how a given
component is declared, and as a smoke test after changing HARP's UI.

Covered here:
  - Track inputs and outputs: audio and MIDI
  - Generic file input and output (a file picker rather than a track)
  - Every control type: slider, number box, dropdown (single and
    multiple selection), checkbox, text box
  - Optional inputs, via harp_required(False)
  - Control and output descriptions, via set_info()
  - Output labels over both audio and MIDI, with every label field
"""

from pyharp import *

from typing import Optional, Tuple
import gradio as gr

import time
import os


# Reference media, used only when the corresponding input track is left empty.
# Bundled alongside this app so it also works offline and once deployed.
RESOURCE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources")
REFERENCE_AUDIO_PATH = os.path.join(RESOURCE_DIR, "test.wav")
REFERENCE_MIDI_PATH = os.path.join(RESOURCE_DIR, "test.mid")

# Metadata shown in HARP's model info panel
model_card = ModelCard(
    name="UI Tester",
    description=(
        "Exercises every input control, track type, and output label type "
        "supported by HARP. No real processing is performed: input tracks are "
        "passed through unchanged, and bundled reference media is substituted for any "
        "track left empty, so the app can be run without loading anything. "
        "The control values are echoed into the output label descriptions."
    ),
    author="TEAMuP",
    tags=["example", "ui", "test", "v3"],
)


def build_audio_labels(duration: float, descriptions: dict) -> list:
    """
    Build one audio label of each supported variety.

    A label with an amplitude is drawn as an overlay on the waveform, and one
    without is drawn in the overhead strip above it.

    Args:
        duration (float): Duration of the output audio, in seconds.
        descriptions (dict): Control values to echo into the labels.

    Returns:
        labels (list): The constructed AudioLabel objects.
    """

    return [
        # Overhead, at the start, with a clickable link
        AudioLabel(
            t=0.0,
            label="start",
            duration=1.0,
            description=descriptions["sliders"],
            color=OutputLabel.rgb_color_to_int(0, 255, 0),
            link="https://github.com/TEAMuP-dev/pyharp"
        ),
        # Overlay, pinned to the bottom of the waveform
        AudioLabel(
            t=0.0,
            label="amplitude 0.0",
            duration=1.0,
            description=descriptions["dropdown"],
            color=OutputLabel.rgb_color_to_int(28, 102, 48),
            amplitude=0.0
        ),
        # Overlay, pinned to the middle of the waveform
        AudioLabel(
            t=0.5 * duration,
            label="amplitude 0.5",
            duration=1.0,
            description=descriptions["checkboxes"],
            color=OutputLabel.rgb_color_to_int(102, 28, 48),
            amplitude=0.5
        ),
        # Overhead, at the end, with no duration (a marker rather than a span)
        AudioLabel(
            t=duration,
            label="end",
            duration=0.0,
            description=descriptions["text"],
            color=OutputLabel.rgb_color_to_int(0, 0, 255)
        ),
    ]


def build_midi_labels(descriptions: dict) -> list:
    """
    Build one MIDI label of each supported variety.

    A label with a pitch is drawn as an overlay on the corresponding piano
    roll row, and one without is drawn in the overhead strip above it.

    Args:
        descriptions (dict): Control values to echo into the labels.

    Returns:
        labels (list): The constructed MidiLabel objects.
    """

    return [
        # Overhead, spanning the first second
        MidiLabel(
            t=0.0,
            label="start",
            duration=1.0,
            description=descriptions["sliders"],
            color=OutputLabel.rgb_color_to_int(255, 255, 0)
        ),
        # Overlay, on the piano roll row for the given pitch
        MidiLabel(
            t=0.0,
            label="pitch 76",
            duration=1.0,
            description=descriptions["text"],
            color=OutputLabel.rgb_color_to_int(255, 128, 78),
            pitch=76
        ),
        # Overlay, as a marker with a clickable link
        MidiLabel(
            t=1.0,
            label="pitch 86",
            duration=0.0,
            color=OutputLabel.rgb_color_to_int(78, 128, 255),
            link="https://github.com/TEAMuP-dev/pyharp",
            pitch=86
        ),
    ]


def process_fn(
    input_audio_path: Optional[str],
    input_midi_path: Optional[str],
    input_file_path: Optional[str],
    processing_delay: float,
    gain: float,
    repetitions: float,
    dropdown: str,
    effects: list,
    enable_audio_labels: bool,
    enable_midi_labels: bool,
    text_prompt: str
) -> Tuple[str, str, LabelList, str]:
    """
    Pass the input tracks through and annotate them with output labels.

    Args:
        input_audio_path (Optional[str]): Audio track, or None if left empty.
        input_midi_path (Optional[str]): MIDI track, or None if left empty.
        input_file_path (Optional[str]): Generic file, or None if left empty.
        processing_delay (float): Seconds to sleep, to test HARP's cancel button.
        gain (float): Unused; demonstrates a fractional slider.
        repetitions (float): Unused; demonstrates a number box.
        dropdown (str): Unused; demonstrates a dropdown.
        effects (list): Unused; demonstrates a multiple-selection dropdown.
        enable_audio_labels (bool): Whether to emit labels over the audio.
        enable_midi_labels (bool): Whether to emit labels over the MIDI.
        text_prompt (str): Unused; demonstrates a text box.

    Returns:
        output_audio_path (str): Path to the output audio.
        output_midi_path (str): Path to the output MIDI.
        output_labels (LabelList): Labels drawn over the output tracks.
        output_file_path (str): Path to the generic output file.
    """

    if input_audio_path is None:
        input_audio_path = REFERENCE_AUDIO_PATH

    if input_midi_path is None:
        input_midi_path = REFERENCE_MIDI_PATH

    audio = load_audio(input_audio_path)
    midi = load_midi(input_midi_path)

    output_audio_path = str(save_audio(audio))
    output_midi_path = str(save_midi(midi))

    # A generic file input arrives as a path, and is echoed back unchanged.
    # When none is provided, write one so the output component is populated.
    if input_file_path is None:
        output_file_path = get_default_path(".txt")

        with open(output_file_path, "w") as f:
            f.write(f"text_prompt: {text_prompt}\n")
    else:
        output_file_path = input_file_path

    # Echo the control values so they can be read back in HARP
    descriptions = {
        "sliders": f"processing_delay: {processing_delay}, gain: {gain}",
        "dropdown": f"dropdown: {dropdown}, effects: {effects}, repetitions: {repetitions}",
        "checkboxes": (
            f"enable_audio_labels: {enable_audio_labels}, "
            f"enable_midi_labels: {enable_midi_labels}"
        ),
        "text": f"text_prompt: {text_prompt}",
    }

    output_labels = LabelList()

    if enable_audio_labels:
        # Total duration of the audio, in seconds
        duration = audio.audio_data.shape[-1] / audio.sample_rate
        output_labels.labels.extend(build_audio_labels(duration, descriptions))

    if enable_midi_labels:
        output_labels.labels.extend(build_midi_labels(descriptions))

    # Stall so that HARP's cancel button and status area can be exercised
    time.sleep(float(processing_delay))

    return output_audio_path, output_midi_path, output_labels, output_file_path


# Build the Gradio endpoint
with gr.Blocks() as demo:
    # Audio and MIDI components become tracks in HARP. A gr.File with any
    # other extension becomes a GUI file picker instead. Every input here is
    # optional, so the app can be run without loading anything.
    # Order must match the process_fn signature.
    input_components = [
        gr.Audio(
            type="filepath",
            label="Input Audio"
        )
        .harp_required(False)
        .set_info("Passed through unchanged. Bundled reference audio is used if empty."),
        gr.File(
            type="filepath",
            label="Input MIDI",
            file_types=[".mid", ".midi"]
        )
        .harp_required(False)
        .set_info("Passed through unchanged. Bundled reference MIDI is used if empty."),
        gr.File(
            type="filepath",
            label="Input File",
            file_types=[".txt", ".csv", ".json", ".nam"]
        )
        .harp_required(False)
        .set_info("A generic file. HARP shows this as a file picker, not a track."),
        gr.Slider(
            minimum=0,
            maximum=60,
            step=1,
            value=0,
            label="Processing Delay (s)",
            info="Stalls processing, so the cancel button can be tested."
        ),
        gr.Slider(
            minimum=0.0,
            maximum=1.0,
            step=0.01,
            value=0.5,
            label="Gain",
            info="A fractional slider."
        ),
        gr.Number(
            minimum=1,
            maximum=16,
            value=4,
            label="Repetitions",
            info="A number box."
        ),
        gr.Dropdown(
            choices=["first", "second", "third"],
            value="second",
            label="Mode",
            info="A dropdown."
        ),
        gr.Dropdown(
            choices=["reverb", "delay", "chorus"],
            value=["reverb", "chorus"],
            multiselect=True,
            label="Effects",
            info="A dropdown allowing more than one selection."
        ),
        gr.Checkbox(
            value=True,
            label="Audio Labels",
            info="Emit output labels over the audio track."
        ),
        gr.Checkbox(
            value=True,
            label="MIDI Labels",
            info="Emit output labels over the MIDI track."
        ),
        gr.Textbox(
            value="Hello World",
            label="Text Prompt",
            info="A text box."
        ),
    ]

    # A gr.JSON output receives the LabelList and is drawn over the tracks.
    # Order must match the values returned by process_fn.
    output_components = [
        gr.Audio(
            type="filepath",
            label="Output Audio"
        ).set_info("The input audio, unchanged."),
        gr.File(
            type="filepath",
            label="Output MIDI",
            file_types=[".mid", ".midi"]
        ).set_info("The input MIDI, unchanged."),
        gr.JSON(
            label="Output Labels"
        ).set_info("Labels drawn over the output tracks."),
        gr.File(
            type="filepath",
            label="Output File"
        ).set_info("A generic file output."),
    ]

    app = build_endpoint(
        model_card=model_card,
        input_components=input_components,
        output_components=output_components,
        process_fn=process_fn,
    )

demo.queue().launch(share=True, show_error=True, pwa=True)
