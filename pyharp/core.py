from gradio.components.base import Component
from dataclasses import dataclass, asdict
from typing import List, Union

import multiprocessing as mp
import threading
import gradio as gr


# "spawn" avoids deadlocks with CUDA/PyTorch libraries that "fork" can cause on Linux (HuggingFace Spaces)
mp.set_start_method("spawn", force=True)


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
    info: str

@dataclass
class HarpAudioTrack(HarpComponent):
    required: bool
    type: str = "audio_track"

@dataclass
class HarpMidiTrack(HarpComponent):
    required: bool
    type: str = "midi_track"

@dataclass
class HarpFileComponent(HarpComponent):
    required: bool
    file_types: List[str]
    type: str = "generic_file"

@dataclass
class HarpSlider(HarpComponent):
    minimum: float
    maximum: float
    step: float
    value: float
    type: str = "slider"

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
class HarpNumberBox(HarpComponent):
    minimum: float
    maximum: float
    step: float
    value: float
    type: str = "number_box"

@dataclass
class HarpJSON(HarpComponent):
    type: str = "json"

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
        assert gr_cmp.type == "filepath", \
            f"Audio input must be of type filepath, not {gr_cmp.type}"
        harp_cmp = HarpAudioTrack(
            label=gr_cmp.label,
            info=gr_cmp.info,
            required=gr_cmp.is_harp_required
        )
    elif isinstance(gr_cmp, gr.File):
        assert gr_cmp.type == "filepath", \
            f"File input must be of type filepath, not {gr_cmp.type}"

        if gr_cmp.file_types is not None and ('.mid' in gr_cmp.file_types or '.midi' in gr_cmp.file_types):
            harp_cmp = HarpMidiTrack(
                label=gr_cmp.label,
                info=gr_cmp.info,
                required=gr_cmp.is_harp_required
            )
        else:
            harp_cmp = HarpFileComponent(
                label=gr_cmp.label,
                info=gr_cmp.info,
                required=gr_cmp.is_harp_required,
                file_types=gr_cmp.file_types if gr_cmp.file_types is not None else []
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
        harp_cmp = HarpDropdown(
            label=gr_cmp.label,
            choices=gr_cmp.choices,
            value=gr_cmp.value,
            info=gr_cmp.info,
            multiselect=bool(gr_cmp.multiselect)
        )
    elif isinstance(gr_cmp, gr.JSON):
        harp_cmp = HarpJSON(
            label=gr_cmp.label,
            info=gr_cmp.info
            #value=gr_cmp.value,
        )
    elif isinstance(gr_cmp, gr.Number):
        harp_cmp = HarpNumberBox(
            label=gr_cmp.label,
            value=gr_cmp.value,
            minimum=gr_cmp.minimum,
            maximum=gr_cmp.maximum,
            step=gr_cmp.step,
            info=gr_cmp.info
        )
    else:
        raise ValueError(
            f"HARP does not support provided \'{gr_cmp}\' component. Please remove it or use an alternative."
        )

    return harp_cmp

def _worker_entry(fn, args, result_q):
    import traceback
    try:
        result = fn(*args)
        result_q.put(("ok", result))
    except gr.Error as e:
        traceback.print_exc()
        result_q.put((
            "gr_error",
            (e.message, e.duration, e.visible, e.title),
        ))
    except Exception as e:
        tb = traceback.format_exc()
        result_q.put(("err", (str(e), tb)))

class JobSupervisor:
    """
    Runs a callable in a subprocess and allows it to be cancelled or
    timed out via SIGTERM, rather than running to completion server-side.
    """

    def __init__(self, timeout_s=900):
        self.timeout_s = timeout_s
        self._process = None
        self._result_q = None
        self._lock = threading.Lock()

    def run(self, fn, *args):
        self.cancel()  # single-flight: kill any previous job first

        with self._lock:
            self._result_q = mp.Queue()
            self._process = mp.Process(
                target=_worker_entry,
                args=(fn, args, self._result_q),
                daemon=True,
            )
            self._process.start()
            process, result_q = self._process, self._result_q

        process.join(self.timeout_s)

        with self._lock:
            if self._process is process and process.is_alive():
                try:
                    self._terminate("timeout")
                except RuntimeError:
                    pass  # sentinel pushed to result_q, handled below

        status, payload = result_q.get()

        with self._lock:
            if self._process is process:
                self._cleanup()

        if status == "gr_error":
            message, duration, visible, title = payload
            raise gr.Error(message, duration=duration, visible=visible, title=title)
        if status == "err":
            short_msg, tb = payload
            raise RuntimeError(f"{short_msg}\n\n{tb}")
        return payload

    def cancel(self):
        with self._lock:
            if self._process and self._process.is_alive():
                self._terminate("cancelled")

    def _terminate(self, reason):
        self._process.terminate()
        self._process.join()
        if self._result_q is not None:
            self._result_q.put(("gr_error", (f"Job {reason}.", 10, True, reason.capitalize())))
        self._cleanup()
        raise RuntimeError(f"Job {reason}")

    def _cleanup(self):
        self._process = None
        self._result_q = None

def build_endpoint(model_card: ModelCard, input_components: list, output_components: list,
                   process_fn: callable, show_controls: bool = False, timeout_s: int = 900) -> tuple:
    """
    Builds a Gradio endpoint compatible with HARP.

    Args:
        model_card (ModelCard): A ModelCard object describing the model.
        input_components (list): Gradio input widgets.
            - It's crucial that the order of inputs matches the order in the Gradio
              UI to ensure proper alignment when communicating with the HARP client.
            - Currently, HARP supports gr.Audio, gr.File(file_types=[".mid", ".midi"]),
              gr.Slider, gr.Checkbox, gr.Number, gr.Dropdown, and gr.Textbox widgets as
              inputs.
        output_components (list): Gradio output widgets.
            - It's crucial that the order of outputs matches the order in the Gradio
              UI to ensure proper alignment when communicating with the HARP client.
            - Currently, HARP supports gr.Audio, gr.File(file_types=[".mid", ".midi"]),
              and gr.JSON widgets as outputs.
        process_fn (callable):
            - Function processing the inputs to generate the output.
            - The function must accept the inputs in the same order as the inputs list.
            - The function must return the outputs in the same order as the outputs list,
              with a filepath string pointing to each output file.
            - process_fn runs in a separate subprocess, so its arguments and
              return values must be picklable (e.g. filepath strings, numbers,
              booleans, JSON-serializable data). It cannot rely on gr.Progress
              or other objects tied to the Gradio request context.
            - If the Cancel button is pressed, or if process_fn runs longer
              than timeout_s, the subprocess is killed (SIGTERM) and the job
              is aborted.
        show_controls (bool): Whether to show the "View Controls" button and the JSON box
            holding the control data.
            - These exist only so that HARP can read the model's interface, and mean
              nothing to someone opening the Gradio page, so they are hidden by default.
            - The "Process" and "Cancel" buttons are always shown, since they are useful
              to someone running the model from the Gradio page directly.
            - HARP is unaffected either way, since it calls the endpoints rather than
              clicking the buttons.
        timeout_s (int): Maximum time in seconds to let process_fn run before
            it is forcibly killed. Defaults to 900 (15 minutes). Increase this
            for models that need more time to process their inputs.

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

    # Create a callable returning model card and controls
    def fetch_model_info():
        data = {
            "card": asdict(model_card),
            "inputs": [asdict(cmp) for cmp in harp_inputs],
            "outputs": [asdict(cmp) for cmp in harp_outputs]
        }
        return data

    # Create a component to store the control data
    controls_data = gr.JSON(label="Controls Data", visible=show_controls)

    # Create a button to fetch model control data
    controls_button = gr.Button("View Controls", visible=show_controls)
    controls_button.click(
        fn=fetch_model_info,
        inputs=[],
        outputs=controls_data,
        api_name="controls"
    )

    # Supervise process_fn in a subprocess so it can be killed on cancel/timeout
    supervisor = JobSupervisor(timeout_s=timeout_s)

    def supervised_process(*args):
        return supervisor.run(process_fn, *args)

    def cancel_handler():
        try:
            supervisor.cancel()
        except RuntimeError:
            pass  # expected -- job was cancelled successfully

    # Create a button to begin processing
    process_button = gr.Button("Process")
    process_event = process_button.click(
        fn=supervised_process,
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

    app = {
        "controls_data": controls_data,
        "controls_button": controls_button,
        "process_button": process_button,
        "cancel_button": cancel_button
    }

    return app


extend_gradio()
