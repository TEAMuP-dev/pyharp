<a href="https://github.com/TEAMuP-dev/HARP">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://github-stats-extended.vercel.app/api/pin/?username=TEAMuP-dev&repo=HARP&theme=dark_github_repocard">
    <img alt="HARP" src="https://github-stats-extended.vercel.app/api/pin/?username=TEAMuP-dev&repo=HARP&theme=light_github_repocard">
  </picture>
</a>

PyHARP is the **companion package** of [HARP](https://github.com/TEAMuP-dev/HARP), an application that brings machine learning models into Digital Audio Workstations (DAWs). It wraps **arbitrary Python code** for audio and MIDI processing in [Gradio](https://www.gradio.app) endpoints that HARP can reach, so that a model too demanding for common hardware runs remotely and asynchronously. HARP runs standalone or within a DAW that supports external sample editors (_e.g._, [REAPER](https://www.reaper.fm), [Logic Pro](https://www.apple.com/logic-pro/), or [Ableton Live](https://www.ableton.com/en/live/)). [Our website](https://harp.tools/content/install/) covers installing HARP and setting it up with each operating system and DAW.

This README documents how to build a PyHARP app, and our website walks through
[deploying a model](https://harp.tools/content/pyharp_docs/setup.html) step by step,
with two examples taken from the models we host. HARP's [deployment guidelines](https://github.com/TEAMuP-dev/HARP/blob/main/docs/DEPLOYMENT.md) are the conventions our models follow, and cover what to decide while building one: licensing, naming and tagging a model, sourcing weights, reporting errors, preserving the input format, and choosing hardware.

## Table of Contents
* **[Usage](#usage)**
    * **[Installing](#installing)**
    * **[Tests](#tests)**
* **[PyHARP Apps](#pyharp-apps)**
    * **[Model Card](#model-card)**
        * **[Tags](#tags)**
    * **[Processing Code](#processing-code)**
        * **[Worker Processes](#worker-processes)**
    * **[Pre-Trained Models](#pre-trained-models)**
    * **[Gradio Endpoint](#gradio-endpoint)**
        * **[Error Reporting](#error-reporting)**
        * **[Output File Names](#output-file-names)**
    * **[MIDI Inputs & Outputs](#midi-inputs--outputs)**
    * **[Output Labels](#output-labels)**
    * **[Examples](#examples)**
* **[Hosting Endpoints](#hosting-endpoints)**
    * **[Gradio Spaces](#gradio-spaces)**
        * **[ZeroGPU](#zerogpu)**
    * **[Docker Spaces](#docker-spaces)**
    * **[Binary Files](#binary-files)**
    * **[Self-Hosted Endpoints](#self-hosted-endpoints)**
    * **[Accessing Within HARP](#accessing-within-harp)**
        * **[Listing on the Home Tab](#listing-on-the-home-tab)**

# Usage
## Installing
To run or debug a PyHARP app locally, install `pyharp` from a release tag:
```bash
pip install "git+https://github.com/TEAMuP-dev/pyharp.git@v0.4.2"
```

To work on PyHARP itself or run its [examples](#examples), clone it and install it in editable mode instead:
```bash
git clone https://github.com/TEAMuP-dev/pyharp
pip install -e pyharp
cd pyharp
```

PyHARP requires Python 3.10 or newer, and installs [Gradio](https://www.gradio.app/) 6.13 or newer itself.

> [!IMPORTANT]
> **Gradio `4.x` and earlier will not work.** HARP communicates over the `/gradio_api/call/` endpoints introduced in Gradio `5.0.0`. Earlier releases expose a different API and every request will fail.
>
> **Gradio `5.x` works, but reports errors poorly.** Versions before `6.13.0` discard the error payload on the endpoint HARP uses and send an empty response instead, so a failed `process_fn` reaches HARP with no message at all.

## Tests
A test suite covers the model card and its tags, the Gradio components HARP reads, output labels, loading and saving media, and the [worker process](#worker-processes) that makes a job cancelable. Run it after changing anything under `pyharp/`:
```bash
pip install -e ".[test]"
pytest tests
```
The worker tests start real processes and wait on real timeouts, so the suite takes a few minutes.

# PyHARP Apps
A PyHARP app is a `ModelCard` describing the model, a `process_fn` doing the work, and a `gr.Blocks` block wiring the two together through `build_endpoint`. The sections below cover each piece in turn, and [Examples](#examples) puts them together into complete, runnable apps.

## Model Card
The model card defines various attributes of a PyHARP app to help users understand its intended usage. HARP reads it when the model is loaded, showing the description in the model tab and using the tags to categorize it.

<!-- TODO: screenshot. The top of a model tab in HARP, showing the name, author, description, and
     badges that its model card provides.
![A model card, as HARP shows it at the top of the model tab](https://harp.tools/images/model-card.png)
-->

The following model card corresponds to our [pitch shifter](examples/pitch_shifter/app.py) example:
```python
from pyharp import ModelCard, Category


# Metadata shown in HARP's model info panel
model_card = ModelCard(
    name="Pitch Shifter",
    author="TEAMuP",
    description=(
        "Shifts the pitch of an audio file by a number of semitones, without changing its "
        "length."
    ),
    tags=[Category.EFFECTS, Category.UTILITY, "example", "pitch shift"],
)
```

### Tags
HARP's Home tab lists models by category and makes them searchable. It categorizes each model by the `tags` of its model card, which can mix the following:

- **`Category` or `Subcategory`**, _e.g._, `Subcategory.STEM_SEPARATION`: where the model sits in the taxonomy below. List the most specific entries that apply (a `Subcategory` implies its `Category`), and several if the model spans several tasks.
- **`Domain`**, _e.g._, `Domain.SPEECH`: the kind of audio the model is for, as `MUSIC`, `SPEECH`, or `GENERAL_AUDIO`, and more than one where several apply. The Home tab filters by it.
- **`SampleRate`**, _e.g._, `SampleRate(44100)`: the sample rate of the model.
- **`Channels`**, _e.g._, `Channels(2)`: the number of audio channels of the model, tagged as `mono`, `stereo`, or the count itself (_e.g._, `channels:6`).
- **A string**, _e.g._, `"example"`: a custom tag, such as the model family or a notable feature.

The taxonomy is defined in [`taxonomy.json`](pyharp/taxonomy.json), shared by HARP. Its categories are listed below, each followed by its subcategories, which are written `Subcategory.<NAME>` (_e.g._, `Subcategory.HOLISTIC`):

- **Generation** (`Category.GENERATION`): `HOLISTIC`, `INFILLING`, `CONTINUATION`, `ACCOMPANIMENT`, `EDITING`
- **Synthesis** (`Category.SYNTHESIS`): `PERFORMANCE_RENDERING`, `INSTRUMENT_SYNTHESIS`, `SINGING_VOICE_SYNTHESIS`, `TEXT_TO_SPEECH`
- **Effects** (`Category.EFFECTS`): `NEURAL_ANALOG_EFFECTS`, `TIMBRE_TRANSFER`, `EFFECT_REMOVAL`
- **Enhancement** (`Category.ENHANCEMENT`): `DENOISING`, `DEREVERBERATION`, `BANDWIDTH_EXTENSION`, `RESTORATION`
- **Production** (`Category.PRODUCTION`): `AUTOMATIC_MIXING`, `MIXING_STYLE_TRANSFER`, `POST_PROCESSING`
- **Separation** (`Category.SEPARATION`): `STEM_SEPARATION`, `TARGET_SOURCE_EXTRACTION`
- **Analysis** (`Category.ANALYSIS`): `MUSIC_ANALYSIS`, `SPEECH_ANALYSIS`, `GENERAL_AUDIO_ANALYSIS`
- **Utility** (`Category.UTILITY`): no subcategories. Marks a tool rather than an AI model, _e.g._, a DSP effect or a test app.

The taxonomy also defines the three domains, `Domain.MUSIC`, `Domain.SPEECH`, and `Domain.GENERAL_AUDIO`, which cut across the categories.

Tags for what the model takes in and gives back are not added to the model card, since `build_endpoint` infers them from the [Gradio components](#gradio-endpoint), as `input:` and `output:` tags naming the kinds of data it handles: `audio`, `midi`, `file` (a generic file), `text` (an input only), or `labels` (an output only). Components that would produce the same tag are tagged once, so two audio inputs give a single `input:audio`.

The restricted formats of a component follow its tag after a `/`, separated by `|`, _e.g._, `output:audio/wav` or `input:file/json|txt`:

- **`gr.Audio` output**: its `format` (`"wav"` or `"mp3"`), to which Gradio converts the returned audio.
- **Generic `gr.File` input**: its `file_types` (_e.g._, `[".nam"]`). Gradio rejects any other file.
- **Generic `gr.File` output**: its `file_types` (_e.g._, `[".json", ".txt"]`). pyharp raises an error if `process_fn` returns any other file.

Set `format` on a `gr.Audio` output only where the model fixes its output format (see our [MIDI synthesizer](examples/midi_synthesizer/app.py) example). Leaving it unset returns whatever `process_fn` wrote, which is what lets a model preserve the format it was given (see our [pitch shifter](examples/pitch_shifter/app.py) example).

Other components are tagged without a format. A `gr.Audio` input accepts any audio, since its `format` only sets the format to which Gradio converts it before `process_fn` receives it, and MIDI needs no format beyond `input:midi` or `output:midi`.

The sample rate and channels of a model cannot be inferred, as Gradio components do not declare them, so `SampleRate` and `Channels` are listed by hand, if at all.

HARP reads every tag as a string (_e.g._, `category:effects`, `sample-rate:44100`, or `output:audio/wav`). A string in that form is also accepted in the model card in place of the corresponding object, apart from `input:` and `output:`, which are only ever inferred.

A model hosted as a Hugging Face Space can also list these tags in its `README.md`, so that HARP can categorize it before it is loaded (see [Listing on the Home Tab](#listing-on-the-home-tab)).

## Processing Code
In PyHARP, arbitrary audio processing code is wrapped within a single function `process_fn` for use with Gradio. The function arguments and return values should match the input and output [Gradio Components](https://www.gradio.app/docs/gradio/introduction) defined under the main Gradio code block ([see below](#gradio-endpoint)).

<!--
This could be a source separation model, a text-to-music generation model, a music inpainting system, a librosa processing routine, etc.
-->

The following processing code corresponds to our [pitch shifter](examples/pitch_shifter/app.py) example:
```python
from pyharp import load_audio, save_audio, get_default_path

from pathlib import Path

import gradio as gr
import torchaudio
import torch


@torch.inference_mode()
def process_fn(input_audio_path: str, pitch_shift_amount: int) -> str:
    """
    Shift the pitch of the input audio.

    Args:
        input_audio_path (str): Path to the audio file sent by HARP.
        pitch_shift_amount (int): Semitones by which to shift.

    Returns:
        output_audio_path (str): Path to the pitch-shifted audio.
    """

    # Refused with a message, since anything but a gr.Error reaches HARP as a
    # failure without a reason on which a user can act
    try:
        signal = load_audio(input_audio_path)
    except Exception as exc:
        raise gr.Error(f"Could not read the audio file: {exc}") from exc
    if signal.signal_length == 0:
        raise gr.Error("The audio file is empty.")

    pitch_shift = torchaudio.transforms.PitchShift(
        signal.sample_rate,
        n_steps=int(pitch_shift_amount),
        bins_per_octave=12,
        n_fft=512
    )
    signal.audio_data = pitch_shift(signal.audio_data)

    # Returned in the container it arrived in, unless that container is lossy.
    # Such a file was encoded once already, and the shift moves the artifacts of
    # that encoder out from under the maskers that hid them, so writing .mp3 back
    # would layer a second round of loss over a first that is now audible.
    # AIFF comes back as WAV too, since Gradio converts an AIFF output to
    # 16-bit WAV, which browsers can play, and soundfile cannot write .aif.
    input_ext = Path(input_audio_path).suffix.lower()
    output_ext = input_ext if input_ext in {".wav", ".flac"} else ".wav"

    output_audio_path = str(save_audio(signal, get_default_path(ext=output_ext)))

    return output_audio_path
```

The function takes two arguments:
- `input_audio_path`: the filepath of the audio to process
- `pitch_shift_amount`: the amount to pitch shift (in semitones)

and returns:
- `output_audio_path`: the filepath of the processed audio

Note that by default PyHARP uses the [audiotools](https://github.com/descriptinc/audiotools) library from Descript (installation instructions can be found [here](https://github.com/descriptinc/audiotools#installation)) to load and save audio, but any standard method will work.

### Worker Processes

`process_fn` runs in a separate worker process, so that pressing Cancel in HARP stops the work rather
than leaving it to run to completion server-side. `build_endpoint` also takes `timeout_s` (default
`900`, _i.e._ 15 minutes), after which a job is stopped the same way. Increase it for models that
legitimately run longer. One job runs at a time, which `build_endpoint` enforces by giving the
process event a `concurrency_limit` of `1`, and starting a new job stops whatever was running.

The worker is **reused between requests**, so whatever your `app.py` loads on the way to `process_fn`
is loaded once rather than once per job. It starts as soon as `build_endpoint` is called, so that
loading happens while the server comes up rather than during the first request, which on ZeroGPU
could otherwise outlast the request's token. Pass `warm_start=False` to start it on the first
request instead. Canceling interrupts the job where it stands and keeps the
worker, models included. Only a job stuck inside a library call that refuses to be interrupted costs a
restart, and a replacement worker starts loading immediately, so it is usually ready again before the
next request.

Being a separate process, the worker has to import your `app.py` to reach `process_fn`, and running
that file executes everything outside of a `__main__` guard, `launch()` included. The Gradio code
therefore belongs behind one, with `process_fn` defined above it, as in every [example](#examples):

```python
def process_fn(input_audio_path: str, pitch_shift_amount: int) -> str:
    ...

if __name__ == "__main__":
    with gr.Blocks() as demo:
        ...
    demo.queue().launch()
```

An app without one still works, as PyHARP will suppress the second `launch()` with a warning.
However, in this case the interface is rebuilt in each worker, so the guard is worth adding.

A few smaller notes:
- Arguments and return values are sent between processes, so they must be picklable. Filepath strings,
  numbers, booleans and other plain data are fine. An open file handle or a live model object is not.
- `process_fn` must be reachable by import: defined at the top level of `app.py`, not as a `lambda`,
  a closure, or inside the guard.
- `gr.Progress`, `gr.Info` and `gr.Warning` are carried back out of the worker, so they display just
  as they would otherwise. The one exception is `gr.Progress().tqdm(...)`, which is not forwarded.
  Call `progress(...)` directly instead.
- A cancel stops only the job of the caller. HARP sends an id with every request, and a browser on
  the Gradio page is matched on the session Gradio gives it, so neither can stop the work of the other.
- The headers of the request being served are carried into the worker, so a library that reads them
  from Gradio's request context still works. ZeroGPU is the one that matters: it takes the token of the caller
  from those headers to decide whose GPU quota a job spends, and without them every job would
  be scheduled as though the request were anonymous. A `gr.Request` parameter is still not passed
  to `process_fn`, and nothing else of the request reaches the worker.

## Pre-Trained Models
If you want to build an endpoint that utilizes a pre-trained model, we recommend the following:
- Load the model outside of `process_fn`, so that it is only initialized once. Doing it inside would repeat the cost on every request, which usually dominates the runtime. Load it under `if __name__ != "__main__":`, which only the [worker](#worker-processes) runs, since it imports `app.py` under another name. The server never runs `process_fn`, so a model loaded at the top level would be held twice, and two processes downloading the same file at once can read it half written. Our [MIDI synthesizer](examples/midi_synthesizer/app.py) example demonstrates this with its soundfont, and the same applies to moving weights onto a GPU ([see below](#self-hosted-endpoints)). Note that a worker is replaced if a job has to be killed to cancel it ([see above](#worker-processes)).
- Fetch model weights from where they are already published rather than copying them into your app repository. `huggingface_hub.hf_hub_download` covers a model on the Hub, and many projects ship their own downloader. Pin a revision so the app does not change behavior when upstream moves.
- Commit weights into the repository only for small assets with no home of their own. Note that these cannot be committed to Git directly (see [Binary Files](#binary-files)).

HARP's [deployment guidelines](https://github.com/TEAMuP-dev/HARP/blob/main/docs/DEPLOYMENT.md#model-weights) cover the other options, including storage buckets for very large weight sets.

## Gradio Endpoint
The main Gradio code block for a PyHARP app consists of defining the input and output [Gradio Components](https://www.gradio.app/docs/gradio/introduction) and launching the endpoint. Our `build_endpoint` function connects these components to the I/O of `process_fn` and extracts HARP-readable metadata from the model card and components to be embedded within the endpoint. Currently, HARP supports the [Slider](https://www.gradio.app/docs/gradio/slider), [Checkbox](https://www.gradio.app/docs/gradio/checkbox), [Number](https://www.gradio.app/docs/gradio/number), [Dropdown](https://www.gradio.app/docs/gradio/dropdown), and [Textbox](https://www.gradio.app/docs/gradio/textbox) components as GUI controls. The components also tag the model with what it takes in and gives back ([see above](#tags)): a `gr.Audio` adds `input:audio` or `output:audio`, a `gr.File` adds `input:midi` or `output:midi` where it declares MIDI file types and `input:file` or `output:file` otherwise, a `gr.Textbox` adds `input:text`, and a `gr.JSON` carrying labels adds `output:labels`.

The Gradio page also carries HARP's own widgets. The "View Controls" button and the JSON box of control data exist only so that HARP can read the interface of the model, so they are hidden by default. Pass `show_controls=True` to `build_endpoint` if you want to inspect them. The "Process" and "Cancel" buttons are always shown, since they are useful to someone running the model from the page directly. HARP is unaffected either way, since it calls the endpoints rather than clicking the buttons.

<!-- TODO: screenshot. The Gradio page of an app launched with show_controls=True, after clicking
     "View Controls", with the card and its tags showing in the JSON box.
![The View Controls button and the control data it shows](https://harp.tools/images/view-controls.png)
-->

The following endpoint code corresponds to our [pitch shifter](examples/pitch_shifter/app.py) example:
```python
from pyharp import build_endpoint

import gradio as gr


# The processing worker imports this file, so the app must not be built there
if __name__ == "__main__":
    # Build the Gradio endpoint
    with gr.Blocks() as demo:
        # Audio and MIDI components become tracks in HARP. Everything else
        # becomes a GUI control. Order must match the process_fn signature.
        input_components = [
            gr.Audio(
                type="filepath",
                label="Input Audio"
            ).harp_required(True).set_info("The audio to shift."),
            gr.Slider(
                minimum=-24,
                maximum=24,
                step=1,
                value=7,
                label="Pitch Shift (semitones)",
                info="The number of semitones by which to shift the pitch."
            ),
        ]

        # Order must match the values returned by process_fn
        output_components = [
            # No format is set, so Gradio returns the container process_fn chose
            gr.Audio(
                type="filepath",
                label="Shifted Audio"
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

<!-- TODO: screenshot. The pitch shifter open in HARP, showing the input track, the slider, and the
     output track that its components declare, beside the Gradio page of the same app.
![The components of the pitch shifter, as HARP draws them](https://harp.tools/images/pitch-shifter-in-harp.png)
-->

A few requirements are easy to miss:
- Every `gr.Audio` component must set `type="filepath"`.
- The order of `input_components` must match the arguments of `process_fn`, and the order of `output_components` must match its return values.
- `demo.queue()` must be called, otherwise an ongoing job cannot be canceled from HARP.
- `show_error=True` lets HARP report why a job failed ([see below](#error-reporting)).
- Tracks and generic files can go in either position, but a GUI control is an input only and a `gr.JSON` of labels is an output only. `build_endpoint` refuses the other arrangement, since HARP has no matching component. Carry anything else as a generic `gr.File`.

Audio and File components accept two PyHARP extensions: `.harp_required(False)` marks an input as optional, and `.set_info("...")` attaches instructions for HARP to display. Both of these extensions are shown in our [UI tester](examples/ui_tester/app.py). Note that only track and generic file inputs can be made optional. GUI controls always carry a value.

### Error Reporting
Gradio only forwards the text of an exception when `show_error=True` is set or when the exception is a `gr.Error`. Without either, HARP can report only that an unspecified error occurred, so launch with `show_error=True` as above.

Raise `gr.Error` for failures you expect users to hit, such as an input the model cannot use. Its message is always forwarded, regardless of `show_error`, and reads as a deliberate message rather than a crash:

```python
if signal.duration < 3:
    raise gr.Error(f"Key detection needs at least 3 seconds of audio, but received {signal.duration:.1f}.")
```

Convert what can be converted rather than refusing it. A model that runs at a fixed sample rate should resample its input and then restore the rate of the input ([see HARP's guidelines](https://github.com/TEAMuP-dev/HARP/blob/main/docs/DEPLOYMENT.md#preserving-the-input-format)).

Note that `gr.Info` and `gr.Warning` never reach HARP. Gradio does not forward them on the endpoint HARP uses, so they appear only on the Gradio page.

### Output File Names
HARP tells results apart by their file names, which matters most in its media clipboard, where results from many runs and models sit side by side. `build_endpoint` therefore renames every file `process_fn` returns as `<model>_<output>`: the name on the model card and the label of the output component, followed by the extension of the file. For example, Open-Unmix would yield `open-unmix_vocals.wav`, and MusicGen would yield `musicgen_generated-music.wav`. HARP then adds the time each result arrives, which keeps the results of successive runs apart. Give each output component a label that describes what it holds, or pass `name_outputs=False` to keep the names `process_fn` sets.

## MIDI Inputs & Outputs
PyHARP supports MIDI inputs and outputs through Gradio's [File](https://www.gradio.app/docs/gradio/file) component. As with `gr.Audio`, each `gr.File` representing MIDI must set `type="filepath"`, and must also specify `file_types=[".mid", ".midi"]` so that HARP renders it as a MIDI track rather than a generic file picker. It also tags the model with `input:midi` or `output:midi`.

The following corresponds to our [MIDI pitch shifter](examples/midi_pitch_shifter/app.py) example:
```python
from pyharp import load_midi, save_midi

import gradio as gr


def process_fn(input_midi_path, ...):
    midi = load_midi(input_midi_path)

    ...

    output_midi_path = str(save_midi(midi))

    return output_midi_path


# The processing worker imports this file, so the app must not be built there
if __name__ == "__main__":
    # Build the Gradio endpoint
    with gr.Blocks() as demo:
        # A gr.File restricted to MIDI extensions becomes a MIDI track in HARP.
        # Order must match the process_fn signature.
        input_components = [
            gr.File(
                type="filepath",
                label="Input MIDI",
                file_types=[".mid", ".midi"]
            ).harp_required(True).set_info("The MIDI to transpose."),
            ...
        ]

        # Order must match the values returned by process_fn
        output_components = [
            gr.File(
                type="filepath",
                label="Transposed MIDI",
                file_types=[".mid", ".midi"]
            ).set_info("The transposed MIDI."),
            ...
        ]

        ...
```

Note that by default PyHARP uses the [symusic](https://github.com/Yikai-Liao/symusic) package to load and save MIDI, but any standard method will work.

## Output Labels
In order to display output labels in HARP (which also tags the model with `output:labels`), you must define an output [JSON](https://www.gradio.app/docs/gradio/json) component and return our custom `LabelList` object in `process_fn`:
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

# The processing worker imports this file, so the app must not be built there
if __name__ == "__main__":
    # Build the Gradio endpoint
    with gr.Blocks() as demo:

        ...

        output_components = [
            ...,
            gr.JSON(label="Output Labels")
        ]

        ...
```

GUI elements corresponding to these labels will appear on the respective output tracks after processing in HARP.

<!-- TODO: screenshot. An output track in HARP with labels drawn over it, and the mouse over one
     label, whose description is shown in the instructions panel.
![Output labels drawn over an output track in HARP](https://harp.tools/images/output-labels.png)
-->

## Examples
We provide several examples of how to create a PyHARP app under the `examples/` directory. The first three are minimal templates covering each combination of input and output media. The fourth is a reference for every supported component. You can also find a list of models already deployed as PyHARP apps on [our website](https://harp.tools/content/usage/models.html).

| Example | In | Out | Illustrates |
| --- | --- | --- | --- |
| [`pitch_shifter`](examples/pitch_shifter) | audio | audio | The minimal app: one track in, one control, one track out. |
| [`midi_pitch_shifter`](examples/midi_pitch_shifter) | MIDI | MIDI | The same shape, on MIDI tracks. |
| [`midi_synthesizer`](examples/midi_synthesizer) | MIDI | audio | Input and output tracks need not be the same media type. |
| [`ui_tester`](examples/ui_tester) | any | audio, MIDI, file | Every control, track, and output label type. Does no real processing. |

All four share the structure described above. Start from whichever template matches your media types.

In order to run an app, you will need to install its corresponding dependencies, including `gradio` and `pyharp`. For example, to install the dependencies for our [pitch shifter](examples/pitch_shifter) example:

```bash
pip install -r examples/pitch_shifter/requirements.txt
```

The app can then be run from the `app.py` script:

```bash
python examples/pitch_shifter/app.py
```

This will create a local Gradio endpoint at the URL `http://localhost:<PORT>`, as well as a forwarded public Gradio endpoint at the URL `https://<RANDOM_ID>.gradio.live/`.

<!-- TODO: screenshot. The command line output after running app.py, with the local and public URLs.
![Command line output after running app.py, showing the local and public Gradio URLs](https://harp.tools/images/example-terminal.png)
-->

The Gradio app can be loaded in HARP as a custom path using either the local or public URL.

<!-- TODO: screenshot. HARP's Custom Path window, with the URL of a running app entered.
![Loading a Gradio endpoint in HARP by entering its URL as a custom path](https://harp.tools/images/custom-path-dialog.png)
-->

# Hosting Endpoints
The share links Gradio generates expire after a week. If you'd like to keep an endpoint active and share it with other users, you can use [Hugging Face Spaces](https://huggingface.co/docs/hub/spaces-overview) (similar hosting services are also available) to host your PyHARP app indefinitely. If you already have your own GPU machine, you can instead host the app there and reach it from HARP over an [SSH tunnel](#self-hosted-endpoints).

## Gradio Spaces
This is the most convenient solution for hosting a PyHARP app. Hugging Face requires a paid plan to create a Gradio Space (PRO for a personal account, Team or Enterprise for an organization), with one exception: any account in good standing can host up to two Spaces on [ZeroGPU](https://huggingface.co/docs/hub/spaces-zerogpu), which lends a GPU to each request at no charge to the owner of the Space. Our website [compares the options](https://harp.tools/content/hosting/spaces.html).

<!-- TODO: screenshot. The Hugging Face "Create a new Space" form, with the Gradio SDK, the blank
     template, and the hardware selected.
![Creating a Gradio Space on Hugging Face](https://harp.tools/images/space-create.png)
-->

1. Create a new [Hugging Face Space](https://huggingface.co/new-space).
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

     Optionally, add a __short_description__ and the __tags__ of the model card, which HARP can show before the model is loaded (see [Listing on the Home Tab](#listing-on-the-home-tab)).

   - `requirements.txt`

     Place all of the required **pip** packages in this file. It should also include the latest version of `pyharp`:
     ```
     git+https://github.com/TEAMuP-dev/pyharp.git@v0.4.2
     ```
     A released tag never moves, since a fix ships as a new patch release instead. Should one ever move, pin the commit it now names, because pip goes on serving the wheel it already built for the URL of the tag through later rebuilds and factory reboots alike.

     Note that you do not have to include the `gradio` package in this file. Do include `spaces`, which ZeroGPU needs and which does nothing on other hardware ([see below](#zerogpu)).

   - `packages.txt`

     Place any necessary **apt-get install** Debian packages in this file. Some models may require these.

### ZeroGPU
A ZeroGPU Space reserves a GPU for each call, out of the daily allowance of whoever made it. The same `app.py` runs unchanged on CPU, on a dedicated GPU, and on ZeroGPU when it does the following:

- **Import `spaces` first**, before `torch` and `pyharp`, or the Space fails at startup on ZeroGPU.
- **Load the model in the worker alone and place it on the device there** ([see above](#pre-trained-models)). ZeroGPU emulates CUDA outside the GPU function, so placing the model at import works, and placing it inside the function would repeat the move on every call.
- **Decorate the function that does the work of the model, not `process_fn`.** An undecorated `process_fn` checks the inputs first, so a request that cannot run is refused before any GPU is reserved. Read the input there with `soundfile` rather than `torchaudio`, whose decoding fails outside the GPU function on ZeroGPU.
- **Size each reservation to the request.** `duration` takes a function of the same arguments as the decorated function. A call that runs past its reservation is stopped, and can cost the caller the whole reservation. ZeroGPU itself refuses a request that the tier or remaining allowance of the caller cannot cover, before reserving anything, so refuse only what cannot finish, such as a reservation longer than `timeout_s` ([see above](#worker-processes)).

```python
import spaces  # before torch and pyharp, as ZeroGPU requires

from pyharp import ModelCard, build_endpoint

import gradio as gr
import soundfile as sf
import torch


device = "cuda" if torch.cuda.is_available() else "cpu"

# Only the worker, which imports this file under another name, runs process_fn
if __name__ != "__main__":
    model = MyModel.from_pretrained(...).eval().to(device)

# timeout_s stops a job after 15 minutes by default, so a longer reservation could not finish
MAX_GPU_SECONDS = 900


def gpu_seconds(input_audio_path: str) -> float:
    # Timed on real inputs, the longest included, and padded a little
    return 10 + 0.5 * sf.info(input_audio_path).duration


def process_fn(input_audio_path: str) -> str:
    # Checked before a GPU is reserved, so a request that cannot run spends nothing
    try:
        sf.info(input_audio_path)
    except Exception as exc:
        raise gr.Error(f"Could not read the audio file: {exc}") from exc
    if gpu_seconds(input_audio_path) > MAX_GPU_SECONDS:
        raise gr.Error("The recording is too long for one request to finish. Trim it.")

    return separate(input_audio_path)


@spaces.GPU(duration=gpu_seconds)
@torch.inference_mode()
def separate(input_audio_path: str) -> str:
    ...
```

An app with no model to run, such as one that only applies DSP, gains nothing from a GPU, so on a paid plan it belongs on CPU and omits the decorator. A free account can host only on ZeroGPU, which fails to start a Space without a decorated function, so there the processing function keeps its decorator. HARP's deployment guidelines cover the rest, under [Hardware Portability](https://github.com/TEAMuP-dev/HARP/blob/main/docs/DEPLOYMENT.md#hardware-portability) and [Protecting the Caller's Allowance](https://github.com/TEAMuP-dev/HARP/blob/main/docs/DEPLOYMENT.md#protecting-the-callers-allowance).

## Docker Spaces
Some models were written against older versions of Python and cannot run alongside the current version of Gradio. For example, the `madmom` package relies on the `numpy.float` and `numpy.int` aliases removed in `numpy==1.24`, so it cannot share an environment with a package that requires a newer NumPy.

Rather than patching the source of the model, keep the two apart: a **frontend** environment running Gradio and PyHARP, and a **backend** environment on the older Python running the model. The frontend invokes the backend as a subprocess and the two exchange JSON. Both live in a single Docker image, which a Gradio Space cannot express, hence a Docker Space. Note that ZeroGPU is not available for Docker Spaces, so GPU resources must be paid for with this option.

Our [BeatNet Space](https://huggingface.co/spaces/teamup-tech/BeatNet) is a working example of this layout.

Cancellation reaches the backend as well. `process_fn` runs in a [worker process](#worker-processes),
which leads its own process group, so stopping a job stops whatever it started. Invoke the backend
with `subprocess.run` as below and it is torn down with the job rather than left running.

1. Create a new [Hugging Face Space](https://huggingface.co/new-space).
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

     Set **app_port** to any valid `<PORT>`. As with a Gradio Space, a **short_description** and the **tags** of the model card can optionally be added (see [Listing on the Home Tab](#listing-on-the-home-tab)).

   - `requirements-frontend.txt`

     The frontend environment, which needs only `gradio` and `pyharp`:
     ```
     gradio==6.24.0
     git+https://github.com/TEAMuP-dev/pyharp.git@v0.4.2
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

     An ordinary PyHARP app, except that `process_fn` reaches the model through a subprocess rather than importing it. Raising `gr.Error` on failure surfaces the message of the backend in HARP ([see above](#error-reporting)):
     ```python
     from pyharp import ModelCard, build_endpoint

     import gradio as gr

     import subprocess
     import json
     import os


     # Metadata shown in HARP's model info panel
     model_card = ModelCard(
         name="Legacy Restorer",
         author="TEAMuP",
         description="An example restoration model which runs under an older version of Python.",
         tags=["example", "docker", "dual environment"],
     )


     def call_backend(input_path: str):
         """Run the model under the backend interpreter and return its result."""

         # No timeout is needed here. build_endpoint's timeout_s already bounds the
         # job, and interrupting it kills this subprocess along with it.
         completed = subprocess.run(
             [os.environ["BACKEND_PYTHON"], os.environ["BACKEND_SCRIPT"], input_path],
             capture_output=True,
             text=True,
             check=False,
         )

         try:
             response = json.loads(completed.stdout)
         except json.JSONDecodeError as exc:
             raise gr.Error(f"The backend did not return JSON: {completed.stderr}") from exc

         if not response["ok"]:
             raise gr.Error(response["error"])

         return response["result"]


     def process_fn(input_audio_path: str) -> str:
         # Nothing here imports the model. It only ever runs in the backend environment
         result = call_backend(input_audio_path)

         ... # Turn the result into the output

         return output_audio_path


     # The processing worker imports this file, so the app must not be built there
     if __name__ == "__main__":
         # Build the Gradio endpoint
         with gr.Blocks() as demo:
             input_components = [
                 gr.Audio(type="filepath", label="Input Audio").harp_required(True)
                 .set_info("The recording to restore."),
             ]

             output_components = [
                 gr.Audio(type="filepath", label="Restored Audio")
                 .set_info("The restored recording."),
             ]

             app = build_endpoint(
                 model_card=model_card,
                 input_components=input_components,
                 output_components=output_components,
                 process_fn=process_fn,
             )

         # The Space routes traffic to $PORT, and the app must bind to all interfaces
         # so that requests can reach it from outside the container
         demo.queue().launch(
             server_name="0.0.0.0",
             server_port=int(os.environ["PORT"]),
             show_error=True
         )
     ```

   - `Dockerfile`

     Installs the system packages and builds both environments. A Docker Space ignores `packages.txt`, so **apt** packages are installed here instead:
     ```Docker
     # Provides the frontend interpreter (the backend one is installed below)
     FROM python:3.10-slim-bullseye

     ENV DEBIAN_FRONTEND=noninteractive \
         PYTHONUNBUFFERED=1 \
         PIP_NO_BUILD_ISOLATION=1 \
         FRONTEND_VENV=/opt/frontend \
         BACKEND_VENV=/opt/backend \
         BACKEND_PYTHON=/opt/backend/bin/python \
         BACKEND_SCRIPT=/app/backend_worker.py \
         PORT=<PORT>

     # Debian 11 is end of life, so its packages now live on archive.debian.org.
     # Point apt there before the first update, and accept the stale Release files.
     RUN set -eux; \
         printf 'deb http://archive.debian.org/debian bullseye main\ndeb http://archive.debian.org/debian-security bullseye-security main\n' \
           > /etc/apt/sources.list; \
         rm -f /etc/apt/sources.list.d/*.list; \
         printf 'Acquire::Check-Valid-Until "false";\n' > /etc/apt/apt.conf.d/99no-check-valid-until

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
Here are a few tips and best practices when dealing with Hugging Face Spaces:
- Spaces operate based off of the files in the `main` branch
- An [access token](https://huggingface.co/docs/hub/security-tokens) may be required to push commits to Hugging Face Spaces
- A `.gitignore` file should be added to maintain repository orderliness (_e.g._, to ignore `_outputs`)
- Pin the versions against which your app was tested, `numpy`, `torch`, and `torchaudio` included, so that a rebuild cannot change them. On ZeroGPU an exact `torch` pin must be a release it accepts, `2.8.0` or newer ([see HARP's guidelines](https://github.com/TEAMuP-dev/HARP/blob/main/docs/DEPLOYMENT.md#choosing-the-hardware)), or the Space stops before it starts

For more information, please refer to the official documentation from Hugging Face about [Spaces](https://huggingface.co/docs/hub/spaces).

## Binary Files

The Hub rejects any push that adds a binary file to Git directly:

```
remote: Your push was rejected because it contains binary files.
remote: Please use https://huggingface.co/docs/hub/xet to store binary files.
```

Despite what that message points at, the mechanism is still [Git LFS](https://git-lfs.com/). A binary
file has to be committed as an LFS pointer, and `.gitattributes` is what decides that.
[Xet](https://huggingface.co/docs/hub/xet/index) is the Hub's storage backend for those pointers, and
`git-xet` is an optional LFS *transfer agent* that uploads them faster. It registers itself under
`lfs.customtransfer.xet` and changes nothing about what gets committed. Installing it does not fix
this error, and not installing it does not cause it.

A new Space comes with a `.gitattributes` covering common weight extensions (`*.safetensors`, `*.bin`,
`*.ckpt`, `*.pt`, …). However, other file types (_e.g._, audio or MIDI) must be added manually:

```bash
git lfs install                       # once per machine
git lfs track "*.wav" "*.mid"         # writes the patterns into .gitattributes
git add .gitattributes
```

Keep the patterns specific, so that smaller files are not sent through large-file storage.

The order matters, and is the usual reason this still fails after `.gitattributes` looks right:
**`.gitattributes` only applies to files staged after it exists.** A binary already sitting in an
earlier commit stays a raw blob there, and the Hub rejects the push over that commit even though the
tip is now a pointer. Rewrite the history to convert it:

```bash
git lfs migrate import --include="*.wav,*.mid" --everything
git push
```

To confirm a file is a pointer before pushing, check its size in Git. A pointer is a couple of
hundred bytes, whatever the file weighs on disk:

```bash
git cat-file -s HEAD:resources/test.wav
```

## Self-Hosted Endpoints
Spaces are the quickest way to publish an app, but they cap the hardware you can use and require the model and its weights to be uploaded to Hugging Face. When you already have a GPU machine, such as a lab workstation or a compute node, you can host the app there instead and reach it from HARP over an SSH tunnel, keeping private weights and audio on your own hardware.

1. **Load the model once, outside `process_fn`.**

   As described under [Pre-Trained Models](#pre-trained-models), anything expensive is loaded once, in the worker. On a GPU machine this is also where the weights are moved onto the device, and loading them in the worker alone keeps a single copy in GPU memory:

   ```python
   device = "cuda" if torch.cuda.is_available() else "cpu"

   # Only the worker, which imports this file under another name, runs process_fn
   if __name__ != "__main__":
       model = MyModel.from_pretrained(...).to(device)
       model.eval()

   def process_fn(input_audio_path, ...):
       signal = load_audio(input_audio_path)
       ...
   ```

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

The tunnel is what keeps the endpoint reachable. Closing it disconnects it from HARP.

If you would rather expose the app directly instead of tunneling, launch it with `server_name="0.0.0.0"` (the API equivalent of Gradio's `--listen` flag) and use the hostname of the machine in HARP. Be aware that this makes the app reachable by anyone who can route to that host and port, with no authentication, so restrict it with a firewall or a VPN. Gradio's `auth` option is no substitute, since HARP cannot sign in to an app launched with it. Alternatively, `share=True` publishes a temporary public `gradio.live` URL that requires no network configuration at all, though it expires after a week.

## Accessing Within HARP
However a PyHARP app is hosted, it can be loaded in HARP as a custom path:

- **Running locally**, use the local or forwarded URL printed on startup ([see above](#examples)), _e.g._ `http://localhost:7860` or `https://<RANDOM_ID>.gradio.live/`.
- **Hosted on a Space**, use `https://huggingface.co/spaces/<USERNAME>/<SPACE_NAME>`, or just the shorthand `<USERNAME>/<SPACE_NAME>`. The Gradio and Docker Space options produce identical UIs and functionality.
- **Self-hosted behind an SSH tunnel**, use the forwarded address ([see above](#self-hosted-endpoints)), _e.g._ `http://localhost:7860`.

### Listing on the Home Tab
HARP's Home tab lists every Space of the [TEAMuP organization](https://huggingface.co/teamup-tech) on Hugging Face, so a PyHARP app hosted there appears without being entered as a custom path. HARP reads the card of a model only once it is loaded, since reaching the app requires waking a sleeping Space. Until then, it describes and categorizes the model using two fields of the Space's `README.md` metadata, which Hugging Face also shows on the Space's own page:

- `short_description`: a summary of the `description` of the model card, shortened if needed to Hugging Face's limit of 60 characters.
- `tags`: the tags of the model card, including the `input:` and `output:` tags inferred from its Gradio components (see [Tags](#tags)). Their order does not matter. To see the exact list, launch the app with `build_endpoint(..., show_controls=True)` and click "View Controls", which shows it under `card`.

For our [pitch shifter](examples/pitch_shifter/README.md) example, these are:
```yaml
short_description: Shifts the pitch of an audio track.
tags:
  - category:effects
  - category:utility
  - input:audio
  - output:audio
  - example
  - pitch shift
```

<!-- TODO: screenshot. A card on HARP's Home tab for a Space that has not been loaded, showing the
     short_description and tags from its README.
![A Space listed on HARP's Home tab by its README metadata](https://harp.tools/images/home-tab-card.png)
-->

Both fields are optional. A Space without them is still listed, under "Other" and by name alone, and once it is loaded, HARP uses its model card as usual. They are only relevant to Spaces: an app run locally or self-hosted is opened as a custom path, and needs nothing beyond its model card.
