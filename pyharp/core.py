from gradio.components.base import Component
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List

import gradio as gr
import audiotools
import symusic


__all__ = [
    'ModelCard',
    'load_audio',
    'save_audio',
    'load_midi',
    'save_midi',
    'get_tick_time_in_seconds',
    'build_endpoint',
    'OutputLabel'
]


@dataclass
class Control:
    label: str


@dataclass
class AudioInControl(Control):
    ctrl_type: str = "audio_in"


@dataclass
class MidiInControl(Control):
    ctrl_type: str = "midi_in"


@dataclass
class SliderControl(Control):
    minimum: float
    maximum: float
    step: float
    value: float
    ctrl_type: str = "slider"


@dataclass
class TextControl(Control):
    value: str
    ctrl_type: str = "text"


@dataclass
class ToggleControl(Control):
    value: bool
    ctrl_type: str = "toggle"


@dataclass
class DropdownControl(Control):
    choices: List[str]
    value: str
    ctrl_type: str = "dropdown"


@dataclass
class NumberControl(Control):
    minimum: float
    maximum: float
    value: bool
    ctrl_type: str = "number_box"


@dataclass
class OutputLabel:
    label: str
    t: float
    y: float = None
    duration: float = 0.0
    description: str = None

    def __post_init__(self):
        if self.description is None:
            self.description = self.label


@dataclass
class ModelCard:
    name: str
    description: str
    author: str
    tags: List[str]
    midi_in: bool = False
    midi_out: bool = False


def load_audio(input_audio_path):
    """
    Loads audio at a specified path using audiotools (Descript).

    Args:
        input_audio_path (str): the audio filepath to load.

    Returns:
        signal (audiotools.AudioSignal): wrapped audio signal.
    """

    signal = audiotools.AudioSignal(input_audio_path)

    return signal


def save_audio(signal, output_audio_path=None):
    """
    Saves audio to a specified path using audiotools (Descript).

    Args:
        signal (audiotools.AudioSignal): wrapped audio signal.
        output_audio_path (str): the filepath to use to save the audio.

    Returns:
        output_audio_path (str): the filepath of the saved audio.
    """

    assert isinstance(signal, audiotools.AudioSignal), "Default loading only supports instances of audiotools.AudioSignal."

    if output_audio_path is None:
        output_dir = Path("_outputs")
        output_dir.mkdir(exist_ok=True)
        output_audio_path = output_dir / "output.wav"
        output_audio_path = output_audio_path.absolute().__str__()

    signal.write(output_audio_path)

    return signal.path_to_file


def load_midi(input_midi_path):
    """
    Loads MIDI at a specified path using symusic (https://yikai-liao.github.io/symusic/).

    Args:
        input_midi_path (str): the MIDI filepath to load.

    Returns:
        midi (symusic.Score): wrapped midi data.
    """

    midi = symusic.Score.from_file(input_midi_path)

    return midi


def save_midi(midi, output_midi_path=None):
    """
    Saves MIDI to a specified path using symusic (https://yikai-liao.github.io/symusic/).

    Args:
        midi (symusic.Score): wrapped midi data.
        output_midi_path (str): the filepath to use to save the MIDI.

    Returns:
        output_midi_path (str): the filepath of the saved MIDI.
    """

    assert isinstance(midi, symusic.Score), "Default loading only supports instances of symusic.Score."

    if output_midi_path is None:
        output_dir = Path("_outputs")
        output_dir.mkdir(exist_ok=True)
        output_midi_path = output_dir / "output.mid"
        output_midi_path = output_midi_path.absolute().__str__()

    midi.dump_midi(output_midi_path)

    return output_midi_path


def ticks_to_seconds(ticks, tempo, ticks_per_quarter):
    """
    Compute the absolute time corresponding to a tick duration.

    Args:
        ticks (int): duration in ticks.
        tempo (float): tempo in beats per minute.
        ticks_per_quarter (int): number of ticks for one quarter beat.

    Returns:
        seconds (float): duration in seconds.
    """

    #seconds per beat times number of quarter beats
    seconds = (60 / tempo) * ticks / ticks_per_quarter

    return seconds


def get_tick_time_in_seconds(tick, midi):
    """
    Determine the absolute time corresponding to a given tick.

    Args:
        tick (int): tick to convert to seconds.
        midi (symusic.Score): wrapped midi data.

    Returns:
        time (float): absolute time in seconds.
    """

    time, ticks_elapsed = 0.0, 0

    for i in range(len(midi.tempos)):
        tick_duration = tick - ticks_elapsed

        if tick_duration <= 0:
            break

        if i != len(midi.tempos) - 1:
            tick_duration = min(tick_duration, midi.tempos[i + 1].time - ticks_elapsed)

        ticks_elapsed += tick_duration

        time += ticks_to_seconds(tick_duration, midi.tempos[i].qpm, midi.ticks_per_quarter)

    return time


def get_control(cmp: Component) -> Control:
    """
    Obtain a Ctrl object corresponding to a specified Gradio component.

    Args:
        cmp (gr.Component): A Gradio input component.

    Returns:
        ctrl (Control): Corresponding Ctrl object.

    Raises:
        ValueError: If input component is not supported.
    """

    if isinstance(cmp, gr.Audio):
        assert cmp.type == "filepath", f"Audio input must be of type filepath, not {cmp.type}"
        ctrl = AudioInControl(
            label=cmp.label
        )
    elif isinstance(cmp, gr.File) and ('.mid' in cmp.file_types or '.midi' in cmp.file_types):
        assert cmp.type == "filepath", f"File input must be of type filepath, not {cmp.type}"
        ctrl = MidiInControl(
            label=cmp.label
        )
    elif isinstance(cmp, gr.Slider):
        ctrl = SliderControl(
            minimum=cmp.minimum,
            maximum=cmp.maximum,
            label=cmp.label,
            value=cmp.value,
            step=cmp.step,
        )
    elif isinstance(cmp, gr.Textbox):
        ctrl = TextControl(
            label=cmp.label,
            value=cmp.value
        )
    elif isinstance(cmp, gr.Checkbox):
        ctrl = ToggleControl(
            label=cmp.label,
            value=cmp.value
        )
    elif isinstance(cmp, gr.Dropdown):
        ctrl = DropdownControl(
            label=cmp.label,
            choices=cmp.choices,
            value=cmp.value
        )
    elif isinstance(cmp, gr.Number):
        ctrl = NumberControl(
            label=cmp.label,
            value=cmp.value
        )
    else:
        raise ValueError(
            f"HARP does not support provided {cmp} component. Please remove it or use an alternative."
        )

    return ctrl


def build_endpoint(model_card: ModelCard, components: list, process_fn: callable) -> tuple:
    """
    Builds a Gradio endpoint compatible with HARP, facilitating VST3 plugin usage in a DAW.

    Args:
        model_card (ModelCard): A ModelCard object describing the model.
        components (Union[list]): Gradio input widgets.
            NOTE: It's crucial that the order of inputs matches the order in the Gradio UI
            to ensure proper alignment when communicating with the HARP client. Currently,
            HARP supports gr.Slider, gr.Textbox, and gr.Audio widgets as inputs.
        process_fn (callable):
            Function processing the inputs to generate the output.
            The function must accept the inputs in the same order as the inputs list.
            The function must return a filepath string pointing to the output audio file.

    Returns:
        app (dict):
            A dictionary containing:
                1. A gr.JSON to store the control data.
                2. A gr.Button to get the control data.
                3. A gr.Button to process the input and generate the output.
                4. A gr.Button to cancel processing.
    """

    if model_card.midi_in:
        # input MIDI file browser
        media_in = gr.File(
            type='filepath',
            label="Input Midi",
            file_types=[".mid", ".midi"]
        )
    else:
        # input audio file browser
        media_in = gr.Audio(
            type='filepath',
            label='Input Audio'
        )

    # add input file explorer to components
    components.insert(0, media_in)

    # convert Gradio components to simple controls
    controls = [get_control(cmp) for cmp in components]

    # callable returning card and controls
    def fetch_model_info():
        data = {
            "card": asdict(model_card),
            "ctrls": [asdict(ctrl) for ctrl in controls]
        }

        return data

    # component to store the control data
    controls_data = gr.JSON(label="Controls Data")

    # endpoint allowing HARP to fetch model control data
    controls_button = gr.Button("View Controls", visible=True)
    controls_button.click(
        fn=fetch_model_info,
        inputs=[],
        outputs=controls_data,
        api_name="controls"
    )

    if model_card.midi_out:
        # output MIDI file browser
        media_out = gr.File(
            type='filepath',
            label="Output Midi",
            file_types=[".mid", ".midi"]
        )
    else:
        # output audio file browser
        media_out = gr.Audio(
            type='filepath',
            label='Output Audio'
        )

    # component to store the labels data
    output_labels = gr.JSON(label="Output Labels")

    # process button to begin processing
    process_button = gr.Button("Process")
    process_event = process_button.click(
        fn=process_fn,
        inputs=components,
        outputs=[media_out, output_labels],
        api_name="process"
    )

    # cancel button to stop processing
    cancel_button = gr.Button("Cancel")
    cancel_button.click(
        fn=lambda: None,
        inputs=[],
        outputs=[],
        api_name="cancel",
        cancels=[process_event]
    )

    app = {
        "controls_data": controls_data,
        "controls_button": controls_button,
        "process_button": process_button,
        "cancel_button": cancel_button
    }

    return app
