from gradio.components.base import Component
from dataclasses import dataclass, asdict
from typing import List

import gradio as gr
import inspect

__all__ = [
    'ModelCard',
    'build_endpoint'
]

@dataclass
class ModelCard:
    name: str
    description: str
    author: str
    tags: List[str]

@dataclass
class HarpComponent:
    label: str


@dataclass
class HarpAudioTrack(HarpComponent):
    required: bool
    type: str = "audio_track"

@dataclass
class HarpMidiTrack(HarpComponent):
    required: bool
    type: str = "midi_track"

@dataclass
class HarpSlider(HarpComponent):
    minimum: float
    maximum: float
    step: float
    value: float
    type: str = "slider"
    info: str = ""

@dataclass
class HarpTextBox(HarpComponent):
    value: str
    type: str = "text_box"
    info: str = ""

@dataclass
class HarpToggle(HarpComponent):
    value: bool
    type: str = "toggle"
    info: str = ""

@dataclass
class HarpDropdown(HarpComponent):
    choices: List[str]
    value: str
    type: str = "dropdown"
    info: str = ""

@dataclass
class HarpNumberBox(HarpComponent):
    minimum: float
    maximum: float
    value: bool
    type: str = "number_box"
    info: str = ""

@dataclass
class HarpJSON(HarpComponent):
    type: str = "json"
    info: str = ""

def extend_gradio():
    """
    A hacky way to extend a Gradio component
    with any HARP-specific attributes.

    This needs to be called when importing pyharp
    so we add it at the end of core.py

    The developer can use it like:
    gr.Audio(type="filepath", label="Input Audio A").harp_required(False),
    """
    
    def harp_required(self, required=True):
        self.is_harp_required = required
        return self
        
    Component.harp_required = harp_required
    Component.is_harp_required = True

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

    if isinstance(gr_cmp, gr.Audio):
        assert gr_cmp.type == "filepath", f"Audio input must be of type filepath, not {gr_cmp.type}"
        harp_cmp = HarpAudioTrack(
            label=gr_cmp.label,
            required=gr_cmp.is_harp_required
        )
    elif isinstance(gr_cmp, gr.File) and ('.mid' in gr_cmp.file_types or '.midi' in gr_cmp.file_types):
        assert gr_cmp.type == "filepath", f"File input must be of type filepath, not {gr_cmp.type}"
        harp_cmp = HarpMidiTrack(
            label=gr_cmp.label,
            required=gr_cmp.is_harp_required
        )
    elif isinstance(gr_cmp, gr.Slider):
        harp_cmp = HarpSlider(
            minimum=gr_cmp.minimum,
            maximum=gr_cmp.maximum,
            label=gr_cmp.label,
            value=gr_cmp.value,
            step=gr_cmp.step,
            info=gr_cmp.info
        )
    elif isinstance(gr_cmp, gr.Textbox):
        harp_cmp = HarpTextBox(
            label=gr_cmp.label,
            value=gr_cmp.value,
            info=gr_cmp.info
        )
    elif isinstance(gr_cmp, gr.Checkbox):
        harp_cmp = HarpToggle(
            label=gr_cmp.label,
            value=gr_cmp.value,
            info=gr_cmp.info
        )
    elif isinstance(gr_cmp, gr.Dropdown):
        # TODO - currently no support for multiselect
        harp_cmp = HarpDropdown(
            label=gr_cmp.label,
            choices=gr_cmp.choices,
            value=gr_cmp.value,
            info=gr_cmp.info
        )
    elif isinstance(gr_cmp, gr.JSON):
        harp_cmp = HarpJSON(
            label=gr_cmp.label,
            # value=gr_cmp.value,
        )
    elif isinstance(gr_cmp, gr.Number):
        harp_cmp = HarpNumberBox(
            label=gr_cmp.label,
            value=gr_cmp.value,
            minimum=gr_cmp.minimum,
            maximum=gr_cmp.maximum,
            info=gr_cmp.info
        )
    else:
        raise ValueError(
            f"HARP does not support provided {gr_cmp} component. Please remove it or use an alternative."
        )

    return harp_cmp

def build_endpoint(model_card: ModelCard, input_components: list, output_components: list,
                   process_fn: callable) -> tuple:
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

    # convert Gradio components to simple controls
    harp_inputs = [get_harp_component(gr_cmp) for gr_cmp in input_components]
    harp_outputs = [get_harp_component(gr_cmp) for gr_cmp in output_components]

    # callable returning card and controls
    def fetch_model_info():
        data = {
            "card": asdict(model_card),
            "inputs": [asdict(harp_cmp) for harp_cmp in harp_inputs],
            "outputs": [asdict(harp_cmp) for harp_cmp in harp_outputs]
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

    # Detect the return type of process_fn
    # sig = inspect.signature(process_fn)
    # return_annotation = sig.return_annotation

    # component to store the labels data
    # output_labels = gr.JSON(label="Output Labels")

    # process button to begin processing
    process_button = gr.Button("Process")
    process_event = process_button.click(
        fn=process_fn,
        inputs=input_components,
        outputs=output_components,
        api_name="process"
    )

    # cancel button to stop processing
    cancel_button = gr.Button("Cancel")
    cancel_button.click(
        fn=None,
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

extend_gradio()
