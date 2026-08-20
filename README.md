[![HARP](https://gh-card.dev/repos/TEAMuP-dev/HARP.svg)](https://github.com/TEAMuP-dev/HARP)

PyHARP is a **companion package** for [HARP](https://github.com/TEAMuP-dev/HARP), an application which enables the seamless integration of machine learning models into Digital Audio Workstations (DAWs). This repository provides a lightweight wrapper to embed **arbitrary Python code** for audio processing into [Gradio](https://www.gradio.app) endpoints accessible through HARP. In this way, HARP supports offline remote processing with algorithms or models that may be too resource-hungry to run on common hardware. HARP can be run as a standalone or from within DAWs that support external sample editors (_e.g._, [REAPER](https://www.reaper.fm), [Logic Pro X](https://www.apple.com/logic-pro/), or [Ableton Live](https://www.ableton.com/en/live/)). Please see [our website](https://harp3.netlify.app/content/supported_os.html) for more information and instructions on how to install and run HARP with various operating systems and DAWs.

## Table of Contents
* **[Usage](#usage)**
    * **[Installing](#installing)**
* **[PyHARP Apps](#pyharp-apps)**
    * **[Examples](#examples)**
    * **[Model Card](#model-card)**
    * **[Processing Code](#processing-code)**
    * **[Pre-Trained Models](#pre-trained-models)**
    * **[Gradio Endpoint](#gradio-endpoint)**
        * **[Error Reporting](#error-reporting)**
    * **[MIDI Inputs & Outputs](#midi-inputs--outputs)**
    * **[Output Labels](#output-labels)**
* **[Hosting Endpoints](#hosting-endpoints)**
    * **[Gradio Spaces](#gradio-spaces)**
    * **[Docker Spaces](#docker-spaces)**
    * **[Self-Hosted Endpoints](#self-hosted-endpoints)**
    * **[Accessing Within HARP](#accessing-within-harp)**

# Usage
## Installing
If you plan on running or debugging a PyHARP app locally, you will need to install `pyharp`:
```bash
git clone https://github.com/TEAMuP-dev/pyharp
pip install -e pyharp
cd pyharp
```

Note that PyHARP depends on [Gradio](https://www.gradio.app/). We recommend installing `gradio>=6.13.0`, which requires `python>=3.10`.

> [!IMPORTANT]
> **Gradio `4.x` and earlier will not work.** HARP communicates over the `/gradio_api/call/` endpoints introduced in Gradio `5.0.0`. Earlier releases expose a different API and every request will fail.
>
> **Gradio `5.x` works, but reports errors poorly.** Versions before `6.13.0` discard the error payload on the endpoint HARP uses and send an empty response instead, so a failed `process_fn` reaches HARP with no message at all.

# PyHARP Apps
## Examples
We provide several examples of how to create a PyHARP app under the `examples/` directory. The first three are minimal templates covering each combination of input and output media; the fourth is a reference for every supported component. You can also find a list of models already deployed as PyHARP apps on [our website](https://harp3.netlify.app/content/usage/models.html).

| Example | In | Out | Illustrates |
| --- | --- | --- | --- |
| [`pitch_shifter`](examples/pitch_shifter) | audio | audio | The minimal app: one track in, one control, one track out. |
| [`midi_pitch_shifter`](examples/midi_pitch_shifter) | MIDI | MIDI | The same shape, on MIDI tracks. |
| [`midi_synthesizer`](examples/midi_synthesizer) | MIDI | audio | Input and output tracks need not be the same media type. |
| [`ui_tester`](examples/ui_tester) | any | audio, MIDI, file | Every control, track, and output label type. Does no real processing. |

All four share the same structure: a `ModelCard`, a `process_fn`, and a `gr.Blocks` block which passes lists of input and output components to `build_endpoint`. Start from whichever template matches your media types.

In order to run an app, you will need to install its corresponding dependencies, including `gradio` and `pyharp`. For example, to install the dependences for our [pitch shifter](https://github.com/TEAMuP-dev/pyharp/tree/main/examples/pitch_shifter) example:

```bash
pip install -r examples/pitch_shifter/requirements.txt
```

The app can then be run from the `app.py` script:

```bash
python examples/pitch_shifter/app.py
```

This will create a local Gradio endpoint at the URL `http://localhost:<PORT>`, as well as a forwarded public Gradio endpoint at the URL `https://<RANDOM_ID>.gradio.live/`.

Below, you can see example command line output after running `app.py`. Both the local endpoint (local URL) and the forwarded endpoint (public URL) are shown:

<!--TODO - updated screenshot-->
![Command line output after running app.py, showing the local and public Gradio URLs](https://github.com/user-attachments/assets/6d27b6eb-9cf3-4f45-badc-9547b24f2091)


The Gradio app can be loaded in HARP as a custom path using either the local or public URL, as shown below.

<!--TODO - updated screenshot-->
![Loading a Gradio endpoint in HARP by entering its URL as a custom path](https://github.com/user-attachments/assets/44ef5c6d-582a-4848-9988-cba3ca4ab941)

## Model Card
The model card defines various attributes of a PyHARP app to help users understand its intended usage. This information is extracted and displayed when the model is loaded within HARP.

The following model card corresponds to our [pitch shifter](examples/pitch_shifter/app.py) example:
```python
from pyharp import ModelCard


model_card = ModelCard(
    name="Pitch Shifter",
    description="A pitch shifting example for HARP v3.",
    author="TEAMuP",
    tags=["example", "audio", "pitch shift", "v3"],
)
```

## Processing Code
In PyHARP, arbitrary audio processing code is wrapped within a single function `process_fn` for use with Gradio. The function arguments and return values should match the input and output [Gradio Components](https://www.gradio.app/docs/gradio/introduction) defined under the main Gradio code block ([see below](#gradio-endpoint)).

<!--
This could be a source separation model, a text-to-music generation model, a music inpainting system, a librosa processing routine, etc.
-->

The following processing code corresponds to our [pitch shifter](examples/pitch_shifter/app.py) example:
```python
from pyharp import load_audio, save_audio

import torchaudio
import torch


@torch.inference_mode()
def process_fn(input_audio_path: str, pitch_shift_amount: int) -> str:
    """
    Shift the pitch of the input audio.

    Args:
        input_audio_path (str): Path to the audio file sent by HARP.
        pitch_shift_amount (int): Amount to shift by, in semitones.

    Returns:
        output_audio_path (str): Path to the pitch-shifted audio.
    """

    signal = load_audio(input_audio_path)

    pitch_shift = torchaudio.transforms.PitchShift(
        signal.sample_rate,
        n_steps=int(pitch_shift_amount),
        bins_per_octave=12,
        n_fft=512
    )
    signal.audio_data = pitch_shift(signal.audio_data)

    output_audio_path = str(save_audio(signal))

    return output_audio_path
```

The function takes two arguments:
- `input_audio_path`: the filepath of the audio to process
- `pitch_shift_amount`: the amount to pitch shift (in semitones)

and returns:
- `output_audio_path`: the filepath of the processed audio

Note that by default PyHARP uses the [audiotools](https://github.com/descriptinc/audiotools) library from Descript (installation instructions can be found [here](https://github.com/descriptinc/audiotools#installation)) to load and save audio, but any standard method will work.

## Pre-Trained Models
If you want to build an endpoint that utilizes a pre-trained model, we recommend the following:
- Load the model outside of `process_fn` so that it is only initialized once. Doing it inside would repeat the cost on every request, which usually dominates the runtime. Our [MIDI synthesizer](examples/midi_synthesizer/app.py) example demonstrates this with its soundfont, and the same applies to moving weights onto a GPU ([see below](#self-hosted-endpoints)).
- Store model weights within your app repository using [Git Large File Storage](https://git-lfs.com/)

## Gradio Endpoint
The main Gradio code block for a PyHARP app consists of defining the input and output [Gradio Components](https://www.gradio.app/docs/gradio/introduction) and launching the endpoint. Our `build_endpoint` function connects these components to the I/O of `process_fn` and extracts HARP-readable metadata from the model card and components to be embedded within the endpoint. Currently, HARP supports the [Slider](https://www.gradio.app/docs/gradio/slider), [Checkbox](https://www.gradio.app/docs/gradio/checkbox), [Number](https://www.gradio.app/docs/gradio/number), [Dropdown](https://www.gradio.app/docs/gradio/dropdown), and [Textbox](https://www.gradio.app/docs/gradio/textbox) components as GUI controls. Dropdowns may be declared with `multiselect=True` to allow more than one choice to be selected at once.

The Gradio page also carries HARP's own widgets. The "View Controls" button and the JSON box of control data exist only so that HARP can read the model's interface, so they are hidden by default; pass `show_controls=True` to `build_endpoint` if you want to inspect them. The "Process" and "Cancel" buttons are always shown, since they are useful to someone running the model from the page directly. HARP is unaffected either way, since it calls the endpoints rather than clicking the buttons.

The following endpoint code corresponds to our [pitch shifter](examples/pitch_shifter/app.py) example:
```python
from pyharp import build_endpoint

import gradio as gr


# Build the Gradio endpoint
with gr.Blocks() as demo:
    # Audio and MIDI components become tracks in HARP; everything else
    # becomes a GUI control. Order must match the process_fn signature.
    input_components = [
        gr.Audio(
            type="filepath",
            label="Input Audio"
        ).harp_required(True),
        gr.Slider(
            minimum=-24,
            maximum=24,
            step=1,
            value=7,
            label="Pitch Shift (semitones)",
            info="Amount to shift the pitch by."
        ),
    ]

    # Order must match the values returned by process_fn
    output_components = [
        gr.Audio(
            type="filepath",
            label="Output Audio"
        ).set_info("The pitch-shifted audio."),
    ]

    app = build_endpoint(
        model_card=model_card,
        input_components=input_components,
        output_components=output_components,
        process_fn=process_fn,
    )

demo.queue().launch(share=True, show_error=True, pwa=True)
```

A few requirements are easy to miss:
- Every `gr.Audio` component must set `type="filepath"`.
- The order of `input_components` must match the arguments of `process_fn`, and the order of `output_components` must match its return values.
- `demo.queue()` must be called, otherwise an ongoing job cannot be cancelled from HARP.
- `show_error=True` lets HARP report why a job failed ([see below](#error-reporting)).

Audio and File components accept two PyHARP extensions: `.harp_required(False)` marks an input as optional, and `.set_info("...")` attaches instructions for HARP to display. Both are shown in our [UI tester](examples/ui_tester/app.py), which exercises every supported component.

### Error Reporting
Gradio only forwards the text of an exception when `show_error=True` is set or when the exception is a `gr.Error`. Without either, HARP can report only that an unspecified error occurred, so launch with `show_error=True` as above.

Raise `gr.Error` for failures you expect users to hit, such as unsupported input. Its message is always forwarded, regardless of `show_error`, and reads as a deliberate message rather than a crash:

```python
if signal.sample_rate != 44100:
    raise gr.Error("This model requires 44.1 kHz audio.")
```

Note that `gr.Info` and `gr.Warning` never reach HARP. Gradio does not forward them on the endpoint HARP uses, so they appear only on the Gradio page.

## MIDI Inputs & Outputs
PyHARP supports MIDI inputs and outputs through Gradio's [File](https://www.gradio.app/docs/gradio/file) component. As with `gr.Audio`, each `gr.File` representing MIDI must set `type="filepath"`, and must also specify `file_types=[".mid", ".midi"]` so that HARP renders it as a MIDI track rather than a generic file picker.

The following corresponds to our [MIDI pitch shifter](examples/midi_pitch_shifter/app.py) example:
```python
from pyharp import load_midi, save_midi

import gradio as gr


def process_fn(input_midi_path, ...):
    midi = load_midi(input_midi_path)

    ...

    output_midi_path = str(save_midi(midi))

    return output_midi_path


with gr.Blocks() as demo:
    input_components = [
        gr.File(
            type="filepath",
            label="Input MIDI",
            file_types=[".mid", ".midi"]
        ).harp_required(True),
        ...
    ]

    output_components = [
        gr.File(
            type="filepath",
            label="Output MIDI",
            file_types=[".mid", ".midi"]
        ).set_info("The transposed MIDI."),
        ...
    ]

    ...
```

Note that by default PyHARP uses the [symusic](https://github.com/Yikai-Liao/symusic) package to load and save MIDI, but any standard method will work.

## Output Labels
In order to display output labels in HARP, you must define an output [JSON](https://www.gradio.app/docs/gradio/json) component and return our custom `LabelList` object in `process_fn`:
```python
from pyharp import LabelList, AudioLabel, MidiLabel, OutputLabel, ...

import gradio as gr

...

@torch.inference_mode()
def process_fn(...):
    ...

    output_labels = LabelList()

    output_labels.labels.extend(
        [
            AudioLabel(
                t=0.0, # seconds
                label="Audio label",
                # The following are optional:
                duration=1.0, # seconds
                description="long description",
                color=OutputLabel.rgb_color_to_int(255, 255, 255, 0.5),
                amplitude=0 # vertical positioning
            ),
            ...,
            MidiLabel(
                t=0.0, # seconds
                label="MIDI label",
                # The following are optional:
                duration=1.0, # seconds
                description="long description",
                link="https://github.com/TEAMuP-dev/pyharp",
                pitch=60 # vertical positioning
            ),
            ...
        ]
    )

    return ..., output_labels

with gr.Blocks() as demo:

    ...

    output_components = [
        ...,
        gr.JSON(label="Output Labels")
    ]

    ...
```

GUI elements corresponding to these labels will appear on the respective output tracks after processing in HARP.

# Hosting Endpoints
Automatically generated Gradio endpoints are only available for a maximum of 72 hours. If you'd like to keep an endpoint active and share it with other users, you can use [HuggingFace Spaces](https://huggingface.co/docs/hub/spaces-overview) (similar hosting services are also available) to host your PyHARP app indefinitely. If you already have your own GPU machine, you can instead host the app there and reach it from HARP over an [SSH tunnel](#self-hosted-endpoints).

## Gradio Spaces
This is the most convenient solution for hosting a PyHARP app. If you are a Hugging Face PRO subscriber, you can use [ZeroGPU](https://huggingface.co/docs/hub/spaces-zerogpu) to dynamically allocate GPU resources according to user requests without any additional charges. Non-PRO users can select from CPU environments or paid GPU options.

1. Create a new [HuggingFace Space](https://huggingface.co/new-space).
2. Choose Gradio as the SDK along with the blank template.
3. Select the desired hardware option.
4. Create the space and clone the initialized repository locally:
```bash
git clone https://huggingface.co/spaces/<USERNAME>/<SPACE_NAME>
```
5. Add your files to the repository, commit, then push to the `main` branch:
```bash
git add .
git commit -m "initial commit"
git push -u origin main
```
6. Configure the following repository files:
   - `README.md`
  
     Set __sdk_version__ to __6.24.0__, the recommended version of `gradio`. This is what the Space actually deploys with, so it must be set even though `gradio` is not listed in `requirements.txt`. Note that Gradio `4.x` and earlier are incompatible with HARP, and that versions before `6.13.0` cannot report error messages (see [Installing](#installing)).

   - `requirements.txt`

     Place all of the required **pip** packages in this file. It should also include the latest version of `pyharp`:
     ```
     git+https://github.com/TEAMuP-dev/pyharp.git@v0.3.1
     ```
     Note that you do not have to include the `gradio` package in this file.

   - `packages.txt`
     
     Place any necessary **apt-get install** debian packages in this file. Some models may require these.

## Docker Spaces
Some models were written against older versions of Python and cannot run alongside a current Gradio. For example, `madmom` relies on the `numpy.float` and `numpy.int` aliases removed in `numpy==1.24`, so it cannot share an environment with a package that requires a newer NumPy.

Rather than patching the model's source, keep the two apart: a **frontend** environment running Gradio and PyHARP, and a **backend** environment on the older Python running the model. The frontend invokes the backend as a subprocess and the two exchange JSON. Both live in a single Docker image, which a Gradio Space cannot express, hence a Docker Space. Note that ZeroGPU is not available for Docker Spaces, so GPU resources must be paid for with this option.

Our [BeatNet Space](https://huggingface.co/spaces/teamup-tech/BeatNet-dual) is a working example of this layout.

1. Create a new [HuggingFace Space](https://huggingface.co/new-space).
2. Choose Docker as the SDK along with the blank template.
3. Select the desired hardware option.
4. Create the space and clone the initialized repository locally:
```bash
git clone https://huggingface.co/spaces/<USERNAME>/<SPACE_NAME>
```
5. Add your files to the repository, commit, then push to the `main` branch:
```bash
git add .
git commit -m "initial commit"
git push -u origin main
```
6. Configure the following repository files:
   - `README.md`

     Set **app_port** to any valid `<PORT>`.

   - `requirements-frontend.txt`

     The frontend environment, which needs only `gradio` and `pyharp`:
     ```
     gradio==6.24.0
     git+https://github.com/TEAMuP-dev/pyharp.git@v0.3.1
     ```

   - `requirements-backend.txt`

     The backend environment, holding the model and its pinned dependencies. Nothing here is visible to the frontend, so old versions are free to conflict with it.

   - `backend_worker.py`

     Runs the model under the older interpreter. It takes the input path as an argument and writes a single JSON object to **stdout**:
     ```python
     import json
     import sys


     def main():
         try:
             result = run_model(sys.argv[1]) # Your model code
             print(json.dumps({"ok": True, "result": result}))
         except Exception as exc:
             print(json.dumps({"ok": False, "error": str(exc)}))


     if __name__ == "__main__":
         main()
     ```
     Nothing else may be written to stdout, or the JSON will be unreadable. Send any logging or progress output to stderr instead.

   - `app.py`

     The usual PyHARP app, except that `process_fn` reaches the model through a subprocess. Raising `gr.Error` on failure surfaces the backend's own message in HARP ([see above](#error-reporting)):
     ```python
     import json
     import os
     import subprocess

     import gradio as gr


     def call_backend(input_path: str, timeout_s: float = 120.0):
         completed = subprocess.run(
             [os.environ["BACKEND_PYTHON"], os.environ["BACKEND_SCRIPT"], input_path],
             capture_output=True,
             text=True,
             check=False,
             timeout=timeout_s,
         )

         try:
             response = json.loads(completed.stdout)
         except json.JSONDecodeError as exc:
             raise gr.Error(f"The backend did not return JSON: {completed.stderr}") from exc

         if not response["ok"]:
             raise gr.Error(response["error"])

         return response["result"]
     ```
     The app must also listen on the port the Space routes traffic to, and must bind to all interfaces so that requests can reach it from outside the container:
     ```python
     demo.queue().launch(
         server_name="0.0.0.0",
         server_port=int(os.environ["PORT"]),
         show_error=True
     )
     ```

   - `Dockerfile`

     Installs the system packages and builds both environments. A Docker Space ignores `packages.txt`, so **apt** packages are installed here instead:
     ```Docker
     # Provides the frontend interpreter; the backend one is installed below
     FROM python:3.10-slim-bullseye

     ENV DEBIAN_FRONTEND=noninteractive \
         PYTHONUNBUFFERED=1 \
         PIP_NO_BUILD_ISOLATION=1 \
         FRONTEND_VENV=/opt/frontend \
         BACKEND_VENV=/opt/backend \
         BACKEND_PYTHON=/opt/backend/bin/python \
         BACKEND_SCRIPT=/app/backend_worker.py \
         PORT=<PORT>

     # The python3.9 packages provide the backend interpreter. Add whatever
     # system libraries your model needs to this list.
     RUN apt-get update && apt-get install -y --no-install-recommends \
             build-essential \
             git \
             python3.9 \
             python3.9-dev \
             python3.9-distutils \
             python3.9-venv \
         && rm -rf /var/lib/apt/lists/*

     WORKDIR /app

     # Backend environment, on the older interpreter
     COPY requirements-backend.txt /tmp/requirements-backend.txt
     RUN /usr/bin/python3.9 -m venv "$BACKEND_VENV" \
         && "$BACKEND_VENV/bin/pip" install --no-cache-dir -U pip wheel "Cython<3" \
         && "$BACKEND_VENV/bin/pip" install --no-cache-dir -r /tmp/requirements-backend.txt

     # Frontend environment, on the image's own interpreter
     COPY requirements-frontend.txt /tmp/requirements-frontend.txt
     RUN python -m venv "$FRONTEND_VENV" \
         && "$FRONTEND_VENV/bin/pip" install --no-cache-dir -U pip wheel \
         && "$FRONTEND_VENV/bin/pip" install --no-cache-dir -r /tmp/requirements-frontend.txt

     COPY app.py backend_worker.py ./

     EXPOSE <PORT>

     CMD ["/opt/frontend/bin/python", "/app/app.py"]
     ```
     Confirm the split works before pushing, by importing the model under the backend interpreter alone:
     ```Docker
     RUN "$BACKEND_VENV/bin/python" -c "import my_model; print('backend OK')"
     ```

---
Here are a few tips and best practices when dealing with HuggingFace Spaces:
- Spaces operate based off of the files in the `main` branch
- An [access token](https://huggingface.co/docs/hub/security-tokens) may be required to push commits to HuggingFace Spaces
- A `.gitignore` file should be added to maintain repository orderliness (_e.g._, to ignore `_outputs`)
- Pin versions for `numpy` (_e.g._, `<2`), `torch` (_e.g._, `==2.2.2`), and `torchaudio` (_e.g._, `==2.2.2`) to avoid unexpected build issues caused by the latest versions of these packages

For more information, please refer to the offical document from Hugging Face about [Spaces](https://huggingface.co/docs/hub/spaces).

## Self-Hosted Endpoints
Spaces are the quickest way to publish an app, but they cap the hardware you can use and require the model and its weights to be uploaded to Hugging Face. When you already have a GPU machine — a lab workstation or a compute node — you can host the app there instead and reach it from HARP over an SSH tunnel, keeping private weights and audio on your own hardware. This is also the setup that best showcases what HARP is for: heavy processing on remote compute, driven from a DAW on your laptop.

1. **Load the model once, outside `process_fn`.**

   Anything expensive belongs at module scope so that it is built when the app starts rather than on every request. Our [MIDI synthesizer](examples/midi_synthesizer) example does this with its soundfont, and a real model would be moved onto the GPU in the same place:

   ```python
   model = MyModel.from_pretrained(...).to("cuda")
   model.eval()

   def process_fn(input_audio_path, ...):
       signal = load_audio(input_audio_path)
       ...
   ```

   Loading inside `process_fn` would transfer the weights to the GPU again for every request, which typically dominates the runtime.

2. **Launch the app on the GPU machine, on a fixed port.**

   ```python
   demo.queue().launch(server_port=7860, show_error=True)
   ```

   Gradio binds to `127.0.0.1` by default, which is all a tunnel needs and means the app is not reachable from anywhere else. Keep `server_port` fixed so the tunnel always targets the same port.

3. **Forward that port to the machine running HARP.**

   ```bash
   ssh -N -L 7860:localhost:7860 <USER>@<GPU_HOST>
   ```

   `-L` forwards your local port 7860 to the same port on the remote host, and `-N` holds the connection open without starting a shell. The `localhost` in that argument is resolved on the GPU machine, which is why the app can stay bound to `127.0.0.1` there. If the GPU node is only reachable through a login node, chain the hops with `-J`:

   ```bash
   ssh -N -J <USER>@<LOGIN_HOST> -L 7860:localhost:7860 <USER>@<GPU_HOST>
   ```

4. **Load `http://localhost:7860` in HARP** as a custom path, exactly as you would an app running locally.

The tunnel is what keeps the endpoint reachable; closing it disconnects HARP.

If you would rather expose the app directly instead of tunnelling, launch it with `server_name="0.0.0.0"` (the API equivalent of Gradio's `--listen` flag) and use the machine's hostname in HARP. Be aware that this makes the app reachable by anyone who can route to that host and port, with no authentication, so restrict it with a firewall or pass `auth=("<USER>", "<PASSWORD>")` to `launch()`. Alternatively, `share=True` publishes a temporary public `gradio.live` URL that requires no network configuration at all, though it expires after 72 hours.

## Accessing Within HARP
PyHARP apps deployed to HuggingFace will begin running at `https://huggingface.co/spaces/<USERNAME>/<SPACE_NAME>`. The shorthand `<USERNAME>/<SPACE_NAME>` can also be used within HARP to reference the endpoint. The Gradio and Docker Space options produce identical UIs and functionality.

PyHARP apps can be accessed from within HARP through the local or forwarded URL corresponding to their active Gradio endpoints ([see above](#examples)), or the URL corresponding to their dedicated hosting service ([see above](#hosting-endpoints)), if applicable.
