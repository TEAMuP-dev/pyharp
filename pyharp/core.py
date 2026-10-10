from gradio.components.base import Component
from gradio_client.utils import is_valid_file
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import List, Optional, Union

import inspect
import gradio as gr
import functools
import inspect

from .tags import INPUT_KEY, OUTPUT_KEY, Modality, Tag, build_tags, io_tag

from .worker import JobSupervisor


__all__ = [
    'ModelCard',
    'build_endpoint'
]

@dataclass(kw_only=True)
class ModelCard:
    """
    Model description shown in the model's tab and used to categorize and filter models.

    Args:
        name (str): Name of the model.
        author (str): Who made the model.
        description (str): What the model does.
        tags (List[Tag]): Any mix of:
            - Category or Subcategory: where the model sits in the taxonomy. Give the most
              specific entries that apply, since a subcategory implies its category, and
              several if the model spans several tasks. Category.UTILITY marks a tool rather
              than an AI model.
            - SampleRate or Channels: the model's sample rate or number of audio channels.
            - A string: a custom tag, e.g. the model family or a notable feature.

    Input and output tags (e.g., audio or MIDI, with any restricted formats) are inferred from
    the Gradio components by build_endpoint (see get_io_tags), so they are not listed here.
    """

    name: str
    author: str
    description: str
    tags: List[Tag] = field(default_factory=list)


@dataclass
class HarpComponent:
    label: str
    info: str

@dataclass
class HarpFileBasedComponent(HarpComponent):
    # A track or generic file, which can be made optional
    required: bool

@dataclass
class HarpRangeComponent(HarpComponent):
    minimum: float
    maximum: float
    step: float
    value: float

@dataclass
class HarpAudioTrack(HarpFileBasedComponent):
    type: str = "audio_track"

@dataclass
class HarpMidiTrack(HarpFileBasedComponent):
    type: str = "midi_track"

@dataclass
class HarpFileComponent(HarpFileBasedComponent):
    file_types: List[str]
    type: str = "generic_file"

@dataclass
class HarpSlider(HarpRangeComponent):
    type: str = "slider"

@dataclass
class HarpNumberBox(HarpRangeComponent):
    type: str = "number_box"

@dataclass
class HarpTextBox(HarpComponent):
    value: str
    type: str = "text_box"

@dataclass
class HarpToggle(HarpComponent):
    value: bool
    type: str = "toggle"

@dataclass
class HarpDropdown(HarpComponent):
    choices: List[str]
    value: Union[str, List[str]]
    multiselect: bool = False
    type: str = "dropdown"

@dataclass
class HarpJSON(HarpComponent):
    type: str = "json"

# Kind of data each component carries (controls such as sliders carry none)
MODALITIES = {
    HarpAudioTrack: Modality.AUDIO,
    HarpMidiTrack: Modality.MIDI,
    HarpFileComponent: Modality.FILE,
    HarpTextBox: Modality.TEXT,
    HarpJSON: Modality.LABELS
}

def extend_gradio():
    """
    A hacky way to extend Gradio components with HARP-specific attributes.
    This needs to be called when importing pyharp, so we invoke it at the
    end of core.py.

    This enables the following types of interactions:
        `gr.Audio(...).harp_required(False)`,
        `gr.File(...).set_info("Output MIDI.")`,
        etc.
    """
    
    def harp_required(self, required=True):
        self.is_harp_required = required
        return self

    Component.harp_required = harp_required
    Component.is_harp_required = True

    def set_info(self, info):
        self.info = info
        return self

    Component.set_info = set_info
    Component.info = None

def is_midi_file(gr_cmp: Component) -> bool:
    """
    Whether a Gradio component is a gr.File accepting MIDI, which HARP treats as a MIDI track
    rather than a generic file.
    """

    return (isinstance(gr_cmp, gr.File) and gr_cmp.file_types is not None
            and ('.mid' in gr_cmp.file_types or '.midi' in gr_cmp.file_types))

def get_harp_component(gr_cmp: Component) -> HarpComponent:
    """
    Obtain a HarpComponent object corresponding to a specified Gradio component.

    Args:
        gr_cmp (gr.Component): A Gradio input component.

    Returns:
        harp_cmp (HarpComponent): Corresponding HarpComponent object.

    Raises:
        ValueError: If input component is not supported.
    """

    common = {"label": gr_cmp.label, "info": gr_cmp.info}

    if isinstance(gr_cmp, (gr.Audio, gr.File)):
        assert gr_cmp.type == "filepath", \
            f"{type(gr_cmp).__name__} components must be of type filepath, not {gr_cmp.type}"
        common["required"] = gr_cmp.is_harp_required

    if isinstance(gr_cmp, gr.Audio):
        return HarpAudioTrack(**common)
    if is_midi_file(gr_cmp):
        return HarpMidiTrack(**common)
    if isinstance(gr_cmp, gr.File):
        return HarpFileComponent(**common, file_types=gr_cmp.file_types or [])
    if isinstance(gr_cmp, (gr.Slider, gr.Number)):
        range_cls = HarpSlider if isinstance(gr_cmp, gr.Slider) else HarpNumberBox
        return range_cls(**common, minimum=gr_cmp.minimum, maximum=gr_cmp.maximum,
                         step=gr_cmp.step, value=gr_cmp.value)
    if isinstance(gr_cmp, gr.Textbox):
        return HarpTextBox(**common, value=gr_cmp.value)
    if isinstance(gr_cmp, gr.Checkbox):
        return HarpToggle(**common, value=gr_cmp.value)
    if isinstance(gr_cmp, gr.Dropdown):
        return HarpDropdown(**common, choices=gr_cmp.choices, value=gr_cmp.value,
                            multiselect=bool(gr_cmp.multiselect))
    if isinstance(gr_cmp, gr.JSON):
        return HarpJSON(**common)

    raise ValueError(
        f"HARP does not support provided \'{gr_cmp}\' component. Please remove it or use an alternative."
    )

def get_modality(harp_cmp: HarpComponent) -> Optional[Modality]:
    """
    Obtain the kind of data a HarpComponent carries, if it carries any.

    Args:
        harp_cmp (HarpComponent): An input or output component.

    Returns:
        modality (Modality | None): Its modality, or None for a control such as a slider.
    """

    return MODALITIES.get(type(harp_cmp))


def get_declared_formats(gr_cmp: Component, is_output: bool) -> List[str]:
    """
    Obtain the file formats to which a component restricts its data, if any.

    A generic gr.File is restricted to its file_types, which Gradio enforces for an input and
    pyharp enforces for an output (see enforce_output_file_types). A gr.Audio output is
    restricted to its format, to which Gradio converts the returned audio. A gr.Audio input
    is not restricted, since its format only sets how Gradio converts incoming audio. A MIDI
    file is not described by format.

    Args:
        gr_cmp (Component): A Gradio input or output component.
        is_output (bool): Whether it is an output.

    Returns:
        formats (List[str]): File extensions, or an empty list if it is not restricted.
    """

    if isinstance(gr_cmp, gr.Audio):
        return [gr_cmp.format] if is_output and gr_cmp.format else []

    if isinstance(gr_cmp, gr.File) and not is_midi_file(gr_cmp):
        # File types can also be categories such as "audio", which name no single format
        return [t for t in (gr_cmp.file_types or []) if t.startswith(".")]

    return []


def get_io_tags(key: str, gr_cmps: list, harp_cmps: List[HarpComponent]) -> List[str]:
    """
    Obtain the tags describing a model's inputs or outputs, in order of appearance.

    Args:
        key (str): INPUT_KEY or OUTPUT_KEY.
        gr_cmps (list): The Gradio components.
        harp_cmps (List[HarpComponent]): The corresponding HarpComponents.

    Returns:
        tags (List[str]): One tag per input or output, without duplicates (see
            pyharp.tags.io_tag). Controls such as sliders are not tagged.
    """

    tags = []

    for gr_cmp, harp_cmp in zip(gr_cmps, harp_cmps):
        modality = get_modality(harp_cmp)

        if modality is not None:
            tags.append(io_tag(key, modality, get_declared_formats(gr_cmp, key == OUTPUT_KEY)))

    return list(dict.fromkeys(tags))


def check_output_files(values, output_components: list):
    """
    Check the files returned for gr.File outputs against their file_types.

    Args:
        values: What process_fn returned.
        output_components (list): Gradio output components.

    Raises:
        gr.Error: If a returned file is not one of its output's file_types.
    """

    values = [values] if len(output_components) == 1 else list(values)

    for index, (gr_cmp, value) in enumerate(zip(output_components, values)):
        if not isinstance(gr_cmp, gr.File) or not gr_cmp.file_types or value is None:
            continue

        name = f"\"{gr_cmp.label}\"" if gr_cmp.label else f"{index + 1}"

        for path in (value if isinstance(value, (list, tuple)) else [value]):
            if not is_valid_file(str(path), gr_cmp.file_types):
                raise gr.Error(
                    f"Output {name} returned \"{Path(str(path)).name}\", which is not one of "
                    f"its file types {gr_cmp.file_types}."
                )


def enforce_output_file_types(process_fn: callable, output_components: list) -> callable:
    """
    Make process_fn fail if it returns a file its gr.File output does not declare.

    Gradio checks an input's file against its file_types and converts a gr.Audio output to
    its format, but passes on whatever file is returned for a gr.File output. Checking it here
    makes the formats HARP is told about (see get_declared_formats) dependable.

    Args:
        process_fn (callable): The processing function.
        output_components (list): Gradio output components.

    Returns:
        process_fn (callable): The function, wrapped with the check where one is needed.
            The wrapper keeps its signature, which Gradio inspects (e.g., for gr.Progress).
    """

    if not any(isinstance(c, gr.File) and c.file_types for c in output_components):
        return process_fn

    if inspect.isgeneratorfunction(process_fn) or inspect.isasyncgenfunction(process_fn):
        # Outputs are streamed rather than returned, so there is no single result to check
        return process_fn

    if inspect.iscoroutinefunction(process_fn):
        @functools.wraps(process_fn)
        async def checked_process_fn(*args, **kwargs):
            values = await process_fn(*args, **kwargs)
            check_output_files(values, output_components)
            return values
    else:
        @functools.wraps(process_fn)
        def checked_process_fn(*args, **kwargs):
            values = process_fn(*args, **kwargs)
            check_output_files(values, output_components)
            return values

    return checked_process_fn


def build_endpoint(model_card: ModelCard, input_components: list, output_components: list,
                   process_fn: callable, show_controls: bool = False,
                   timeout_s: int = 900) -> dict:
    """
    Builds a Gradio endpoint compatible with HARP.

    Args:
        model_card (ModelCard): A ModelCard object describing the model.
        input_components (list): Gradio input widgets.
            - It's crucial that the order of inputs matches the order in the Gradio
              UI to ensure proper alignment when communicating with the HARP client.
            - Currently, HARP supports gr.Audio, gr.File (MIDI or generic), gr.Slider,
              gr.Checkbox, gr.Number, gr.Dropdown, and gr.Textbox widgets as inputs.
        output_components (list): Gradio output widgets.
            - It's crucial that the order of outputs matches the order in the Gradio
              UI to ensure proper alignment when communicating with the HARP client.
            - Currently, HARP supports gr.Audio, gr.File (MIDI or generic), and gr.JSON
              widgets as outputs.
        process_fn (callable):
            - Function processing the inputs to generate the output.
            - The function must accept the inputs in the same order as the inputs list.
            - The function must return the outputs in the same order as the outputs list,
              with a filepath string pointing to each output file.
            - process_fn runs in a worker process, so its arguments and return
              values must be picklable (e.g. filepath strings, numbers, booleans,
              JSON-serializable data), and it must be reachable by import: defined
              at the top level of the app file, not as a lambda, closure, or inside
              a __main__ guard.
            - gr.Progress, gr.Info, gr.Warning and gr.Error are forwarded out of
              the worker and replayed here, so they behave as usual.
            - The request's headers are carried into the worker, so that ZeroGPU
              still bills the GPU quota of whoever made the request.
            - The worker is reused between requests, so anything loaded when the
              module is imported is loaded once rather than per job.
            - If the Cancel button is pressed, or if process_fn runs longer than
              timeout_s, the job is interrupted. A job that will not yield to an
              interrupt has its worker replaced instead.
            - A file returned for a gr.File output with file_types must be one of those
              types, or processing fails with an error.
        show_controls (bool): Whether to show the "View Controls" button and the JSON box
            holding the control data.
            - These exist only so that HARP can read the model's interface, and mean
              nothing to someone opening the Gradio page, so they are hidden by default.
            - The "Process" and "Cancel" buttons are always shown, since they are useful
              to someone running the model from the Gradio page directly.
            - HARP is unaffected either way, since it calls the endpoints rather than
              clicking the buttons.
        timeout_s (int): Maximum time in seconds to let process_fn run before the
            job is stopped. Defaults to 900 (15 minutes). Increase this for models
            that need more time to process their inputs.

    Returns:
        app (dict): A dictionary containing:
            1. A gr.JSON to store the control data.
            2. A gr.Button to get the control data.
            3. A gr.Button to process the input and generate the output.
            4. A gr.Button to cancel processing.
    """

    # Convert Gradio components to simple control objects
    harp_inputs = [get_harp_component(gr_cmp) for gr_cmp in input_components]
    harp_outputs = [get_harp_component(gr_cmp) for gr_cmp in output_components]

    # The card is sent with its tags, and those inferred for its inputs and outputs, flattened
    # into one list (see pyharp.tags)
    card = {
        "name": model_card.name,
        "author": model_card.author,
        "description": model_card.description,
        "tags": build_tags(
            model_card.tags,
            inferred=get_io_tags(INPUT_KEY, input_components, harp_inputs)
                     + get_io_tags(OUTPUT_KEY, output_components, harp_outputs)
        )
    }

    # The model card and controls never change, so they are assembled once
    model_info = {
        "card": card,
        "inputs": [asdict(cmp) for cmp in harp_inputs],
        "outputs": [asdict(cmp) for cmp in harp_outputs]
    }

    # Create a component to store the control data
    controls_data = gr.JSON(label="Controls Data", visible=show_controls)

    # Create a button to fetch model control data
    controls_button = gr.Button("View Controls", visible=show_controls)
    controls_button.click(
        fn=lambda: model_info,
        inputs=[],
        outputs=controls_data,
        api_name="controls"
    )

    # Runs process_fn somewhere it can be stopped once it has started
    supervisor = JobSupervisor(timeout_s=timeout_s)

    def supervised_process(*args):
        *inputs, progress = args

        return supervisor.run(process_fn, *inputs, progress=progress)

    # Gradio injects a progress tracker bound to the current request into any handler
    # that declares one, and finds it by scanning leading positional parameters. It
    # stops at the first *args, so the parameters have to be advertised explicitly.
    # The tracker arrives last, after one value per input component.
    supervised_process.__signature__ = inspect.Signature(
        [
            inspect.Parameter(f"input_{i}", inspect.Parameter.POSITIONAL_OR_KEYWORD)
            for i in range(len(input_components))
        ]
        + [
            inspect.Parameter(
                "progress", inspect.Parameter.POSITIONAL_OR_KEYWORD, default=gr.Progress()
            )
        ]
    )

    def cancel_handler():
        supervisor.cancel()

    # Create a button to begin processing
    process_button = gr.Button("Process")
    process_event = process_button.click(
        fn=enforce_output_file_types(supervised_process, output_components),
        inputs=input_components,
        outputs=output_components,
        api_name="process"
    )

    # Create a button to cancel processing
    cancel_button = gr.Button("Cancel")
    cancel_button.click(
        fn=cancel_handler,
        inputs=[],
        outputs=[],
        api_name="cancel",
        cancels=[process_event]
    )

    return {
        "controls_data": controls_data,
        "controls_button": controls_button,
        "process_button": process_button,
        "cancel_button": cancel_button
    }


extend_gradio()
