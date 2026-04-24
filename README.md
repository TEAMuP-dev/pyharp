[![HARP Repo](https://github-readme-stats.vercel.app/api/pin/?username=TEAMuP-dev&repo=HARP)](https://github.com/TEAMuP-dev/HARP)

PyHARP is a **companion package** for [HARP](https://github.com/TEAMuP-dev/HARP), an application which enables the seamless integration of machine learning models into Digital Audio Workstations (DAWs). This repository provides a lightweight wrapper to embed **arbitrary Python code** for audio processing into [Gradio](https://www.gradio.app) endpoints accessible through HARP. In this way, HARP supports offline remote processing with algorithms or models that may be too resource-hungry to run on common hardware. HARP can be run as a standalone or from within DAWs that support external sample editors (_e.g._, [REAPER](https://www.reaper.fm), [Logic Pro X](https://www.apple.com/logic-pro/), or [Ableton Live](https://www.ableton.com/en/live/)). Please see [our website](https://harp-plugin.netlify.app/content/supported_os.html) for more information and instructions on how to install and run HARP with various operating systems and DAWs.

## Table of Contents
* **[Usage](#usage)**
    * **[Installing](#installing)**
* **[PyHARP Apps](#pyharp-apps)**
    * **[Examples](#examples)**
    * **[Model Card](#model-card)**
    * **[Processing Code](#processing-code)**
    * **[Pre-Trained Models](#pre-trained-models)**
    * **[Gradio Endpoint](#gradio-endpoint)**
    * **[MIDI Inputs & Outputs](#midi-inputs--outputs)**
    * **[Output Labels](#output-labels)**
* **[Hosting Endpoints (HuggingFace Spaces)](#hosting-endpoints-huggingface-spaces)**
    * **[Gradio Endpoints](#gradio-endpoints)**
    * **[Docker Endpoints](#docker-endpoints)**
    * **[Accessing Within HARP](#accessing-within-harp)**

# Usage
## Installing
If you plan on running or debugging a PyHARP app locally, you will need to install `pyharp`:
```bash
git clone https://github.com/TEAMuP-dev/pyharp
pip install -e pyharp
cd pyharp
```

Note that PyHARP depends on [Gradio](https://www.gradio.app/). We recommend installing `gradio==5.28.0`, which requires `python>=3.10`.

# PyHARP Apps
## Examples
We provide several examples of how to create a PyHARP app under the `examples/` directory. You can also find a list of models already deployed as PyHARP apps on [our website](https://harp-plugin.netlify.app/content/usage/models.html).

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
![example commandline output for deploying a gradio app.py](https://github.com/user-attachments/assets/6d27b6eb-9cf3-4f45-badc-9547b24f2091)


The Gradio app can be loaded in HARP as a custom path using either the local or public URL, as shown below.

<!--TODO - updated screenshot-->
![example commandline output for deploying a gradio app.py](https://github.com/user-attachments/assets/44ef5c6d-582a-4848-9988-cba3ca4ab941)

## Model Card
The model card defines various attributes of a PyHARP app to help users understand its intended usage. This information is extracted and displayed when the model is loaded within HARP.

The following model card corresponds to our [pitch shifter](examples/pitch_shifter/app.py) example:
```python
from pyharp import ModelCard


model_card = ModelCard(
    name="Pitch Shifter",
    description="A pitch shifting example for HARP v3.",
    author="TEAMuP",
    tags=["example", "pitch shift", 'v3'],
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
def process_fn(
    input_audio_path: str,
    pitch_shift_amount: int
)-> str:

    pitch_shift_amount = int(pitch_shift_amount)

    sig = load_audio(input_audio_path)

    ps = torchaudio.transforms.PitchShift(
        sig.sample_rate,
        n_steps=pitch_shift_amount,
        bins_per_octave=12,
        n_fft=512
    )
    sig.audio_data = ps(sig.audio_data)

    output_audio_path = str(save_audio(sig))

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
- Load the model outside of `process_fn` so that it is only initialized once
- Store model weights within your app repository using [Git Large File Storage](https://git-lfs.com/)

## Gradio Endpoint
The main Gradio code block for a PyHARP app consists of defining the input and output [Gradio Components](https://www.gradio.app/docs/gradio/introduction) and launching the endpoint. Our `build_endpoint` function connects these components to the I/O of `process_fn` and extracts HARP-readable metadata from the model card and components to be embedded within the endpoint. Currently, HARP supports the [Slider](https://www.gradio.app/docs/gradio/slider), [Checkbox](https://www.gradio.app/docs/gradio/checkbox), <!-- [Number](https://www.gradio.app/docs/gradio/number),--> [Dropdown](https://www.gradio.app/docs/gradio/dropdown), and [Textbox](https://www.gradio.app/docs/gradio/textbox) components as GUI controls.

The following endpoint code corresponds to our [pitch shifter](examples/pitch_shifter/app.py) example:
```python
from pyharp import build_endpoint

import gradio as gr


# Build Gradio endpoint
with gr.Blocks() as demo:
    # Define input Gradio Components
    input_components = [
        gr.Audio(type="filepath",
                 label="Input Audio A")
        .harp_required(True),
        gr.Slider(
            minimum=-24,
            maximum=24,
            step=1,
            value=7,
            label="Pitch Shift (semitones)",
            info="Controls the amount of pitch shift in semitones"
        ),
    ]

    # Define output Gradio Components
    output_components = [
        gr.Audio(type="filepath",
                 label="Output Audio")
        .set_info("The pitch-shifted audio."),
    ]

    # Build a HARP-compatible endpoint
    app = build_endpoint(
        model_card=model_card,
        input_components=input_components,
        output_components=output_components,
        process_fn=process_fn,
    )

demo.queue().launch(share=True, show_error=False, pwa=True) # see the third NOTE below
```
**NOTE (1):** All of the `gr.Audio` components must have `type="filepath"` in order to work with HARP.

**NOTE (2):** Make sure the order of the inputs and outputs matches the order of the arguments and return values in `process_fn`.

**NOTE (3):** In order to be able to cancel an ongoing processing job within HARP, queueing in Gradio needs to be enabled by calling `demo.queue()`.

**NOTE (4):** Input Audio and File components can be registered as optional in HARP using `.harp_required(False)`.

**NOTE (5):** All Audio and File components can be extended with the `info` attribute to define displayable instructions in HARP using our `set_info` function.

## MIDI Inputs & Outputs
PyHARP supports MIDI inputs and outputs through Gradio's [File](https://www.gradio.app/docs/gradio/file) component. As with `gr.Audio`, all `gr.File` corresponding MIDI should set `type="filepath"`, and additionally specify `file_types=[".mid", ".midi"]` file.

```python
from pyharp import load_midi, save_midi

def process_fn(input_midi_path, ...):
    midi = load_midi(input_midi_path)

    ...

    output_midi_path = str(save_midi(midi))

    return out_path

with gr.Blocks() as demo:

    input_components = [
        gr.File(
            type="filepath",
            label="Input Midi File",
            file_types=[".mid", ".midi"]
        ),
        ...

    output_components = [
        gr.File(
            type="filepath"
            label="Output MIDI File",
            file_types=[".mid", ".midi"]
        ),
        ...
    ]

    ...

```

Note that by default PyHARP uses the [symusic](https://github.com/Yikai-Liao/symusic) package to load and save MIDI, but any standard method will work.

## Output Labels
In order to display output labels in HARP, you must define an output JSON component and return our custom `LabelList` object in `process_fn`:
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

## Hosting Endpoints (HuggingFace Spaces)
Automatically generated Gradio endpoints are only available for a maximum of 72 hours. If you'd like to keep an endpoint active and share it with other users, you can use [HuggingFace Spaces](https://huggingface.co/docs/hub/spaces-overview) (similar hosting services are also available) to host your PyHARP app indefinitely.

### Gradio Endpoints
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
  
     Set __sdk_version__ to __5.28.0__, the recommended version of `gradio`. HARP may not work with the very latest or earlier versions.

   - `requirements.txt`

     Place all of the required **pip** packages in this file. It should also include the latest version of `pyharp`:
     ```
     git+https://github.com/TEAMuP-dev/pyharp.git@v0.3.0
     ```
     Note that you do not have to include the `gradio` package in this file.

   - `packages.txt`
     
     Place any necessary **apt-get install** debian packages in this file. Some models may require these.

### Docker Endpoints
Some models may have been developed with older versions of Python, and attempting to deploy them would lead to dependency issues. For example, the `numpy.float` and `numpy.int` deprecation in `numpy==1.24` breaks older packages such as `madmom`. Therefore, we may need to patch any corresponding source files during the deployment process. However, this is not supported by the highly-modularized Gradio SDK.

Using Docker endpoints can help circumvent these issues. Docker will allow you to customize the deployment, which makes room for any necessary patches. Note however that ZeroGPU is not available for Docker spaces, meaning you must pay to use GPU resources with this option.

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

   - `requirements.txt`

     Place all of the required **pip** packages in this file. It should also include the recommended version of `gradio` and the latest version of `pyharp`:
     ```
     gradio==5.28.0
     git+https://github.com/TEAMuP-dev/pyharp.git@v0.3.0
     ```

   - `packages.txt`
     
     Place any necessary **apt-get install** debian packages in this file. Some models may require these.

    - `Dockerfile`

      Installs the required **pip** and **apt-get** packages, and supports manual patching (_e.g._ of `madmom` in the following example):
      ```Docker
      FROM python:3.10-slim # Set python version

      WORKDIR /app
      COPY packages.txt /app/packages.txt

      # System dependencies for building packages from source
      RUN apt-get update
      RUN xargs apt-get install -y --no-install-recommends < /app/packages.txt
      RUN rm -rf /var/lib/apt/lists/*

      COPY requirements.txt /app/requirements.txt
      # Disable build isolation so Cython installed in the environment is visible at build time
      ENV PIP_NO_BUILD_ISOLATION=1
      RUN pip install --no-cache-dir -U pip wheel Cython
      RUN pip install --no-cache-dir setuptools==80.9.0
      RUN pip install --no-cache-dir -r /app/requirements.txt
      RUN pip install --no-cache-dir --no-build-isolation madmom

      # Patch madmom package
      COPY patch_madmom.py /app/scripts/patch_madmom.py # Script to patch madmom source files
      RUN python /app/scripts/patch_madmom.py
      RUN python -c "import madmom; print('madmom import OK')"

      # Copy remainder of the repo
      COPY . /app

      # HF Spaces route traffic to <PORT>
      # Gradio should listen accordingly
      ENV PORT=<PORT> # <PORT> in README.md
      EXPOSE <PORT>

      # Run the app
      CMD ["python", "app.py"]
      ```

---
Here are a few tips and best practices when dealing with HuggingFace Spaces:
- Spaces operate based off of the files in the `main` branch
- An [access token](https://huggingface.co/docs/hub/security-tokens) may be required to push commits to HuggingFace Spaces
- A `.gitignore` file should be added to maintain repository orderliness (_e.g._, to ignore `src/_outputs`)
- Pin versions for `numpy` (_e.g._, `<2`), `torch` (_e.g._, `==2.2.2`), and `torchaudio` (_e.g._, `==2.2.2`) to avoid unexpected build issues caused by the latest versions of these packages

For more information, please refer to the offical document from Hugging Face about [Spaces](https://huggingface.co/docs/hub/spaces).

## Accessing Within HARP
PyHARP apps deployed to HuggingFace will begin running at `https://huggingface.co/spaces/<USERNAME>/<SPACE_NAME>`. The shorthand `<USERNAME>/<SPACE_NAME>` can also be used within HARP to reference the endpoint. The two deployment methods above produce identical UIs and functionality.

PyHARP apps can be accessed from within HARP through the local or forwarded URL corresponding to their active Gradio endpoints ([see above](#examples)), or the URL corresponding to their dedicated hosting service ([see above](#hosting-endpoints-huggingface-spaces))), if applicable.
