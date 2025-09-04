from pyharp import *

from typing import Tuple
import gradio as gr

import tempfile
import requests
import shutil
import time
import os


# Create a ModelCard
model_card = ModelCard(
    name="UI Test for HARP 3.0.0",
    description=\
        '''This is a test for the new UI features in HARP 3.0.0. The audio input is not used. You can click "process" without loading an audio file. Use the "Dropdown 1" to select the output audio file. The audio labels are added at 0%, 50%, and 100% - 1sec of the audio duration and 0, 0.5, and 1 of the amplitude.''',
    author="TEAMuP",
    tags=["example", "ui", "test"],
)

def download_file(url):
    """
    Download a file from GitHub to a local temporary file.

    Args:
        url (str): Path to file to download.

    Returns:
        temp_file_path (str): Path to created temporary file.

    Raises:
        HTTPError: If download is unsuccessful.
    """

    if "github.com" in url and "/blob/" in url:
        # Convert GitHub blob URL to raw content URL
        url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")

    # Determine file extension
    ext = os.path.splitext(url)[1]

    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    temp_file.close()

    temp_file_path = temp_file.name

    # Download file at provided path
    response = requests.get(url, stream=True)
    # Ensure we got a valid response
    response.raise_for_status()

    with open(temp_file_path, 'wb') as f:
        # Write the data to the temporary file
        shutil.copyfileobj(response.raw, f)
    
    return temp_file_path

# Define the process function
def process_fn(
    input_audio_path, # unused
    slider_1_time_sleep,
    slider_2,
    slider_3,
    dropdown_1,
    dropdown_2,
    checkbox_1,
    checkbox_2,
    checkbox_3,
    text_control
) -> Tuple[str, str, LabelList]:

    # Paths to files to use for output
    audio_url = f"https://github.com/TEAMuP-dev/HARP/blob/main/test/{dropdown_1}"
    midi_url = "https://github.com/TEAMuP-dev/HARP/blob/main/test/test.mid"

    # Download audio and MIDI file
    local_audio_path = download_file(audio_url)
    local_midi_path = download_file(midi_url)

    # Load audio and MIDI data
    audio = load_audio(local_audio_path)
    midi = load_midi(local_midi_path)

    try:
        # Clean up temporary files
        os.unlink(local_audio_path)
        os.unlink(local_midi_path)
    except Exception as e:
        print(f"Failed to clean up temporary files: {e}")

    # Save downloaded data to output
    output_audio_path = save_audio(audio)
    output_midi_path = save_midi(midi)

    # Create an empty label list
    output_labels = LabelList()

    # Determine total duration of audio in seconds
    duration = audio.audio_data.shape[2] / audio.sample_rate

    # Convert input controls to text
    descr_1 = f"dropdown_1: {dropdown_1}, dropdown_2: {dropdown_2}"
    descr_2 = f"checkbox_1: {checkbox_1}, checkbox_2: {checkbox_2} checkbox_3: {checkbox_3}"
    descr_3 = f"text_control: {text_control}"
    descr_4 = f"slider_1_time_sleep: {slider_1_time_sleep}, slider_2: {slider_2}, slider_3: {slider_3}"

    # Add dummy waveform labels
    output_labels.labels.extend(
        [
            AudioLabel(
                t=0,
                label="ol-t0-d1",
                duration=1,
                color=OutputLabel.rgb_color_to_int(0, 255, 0),
                link="https://github.com/TEAMuP-dev/pyharp"
            ),
            AudioLabel(
                t=0,
                label="lo-t0-d1-a0",
                duration=1,
                description=descr_1,
                color=OutputLabel.rgb_color_to_int(28, 102, 48),
                amplitude=0
            ),
            AudioLabel(
                t=(0.5 * duration),
                label="ol-t50%-d0",
                duration=0,
                description=descr_4,
                color=OutputLabel.rgb_color_to_int(255, 0, 0)
            ),
            AudioLabel(
                t=(0.5 * duration),
                label="lo-t50%-d1-a0.5",
                duration=1,
                description=descr_2,
                color=OutputLabel.rgb_color_to_int(102, 28, 48),
                link="https://github.com/TEAMuP-dev/pyharp",
                amplitude=0.5
            ),
            AudioLabel(
                t=(duration - 1),
                label="lo-t100%minus1-d1-a1",
                duration=1,
                description=descr_3,
                color=OutputLabel.rgb_color_to_int(48, 102, 28),
                amplitude=1
            ),
            AudioLabel(
                t=(1.0 * duration),
                label="ol-t100%-d0.1",
                duration=0.1,
                description="last overhead label",
                color=OutputLabel.rgb_color_to_int(0, 0, 255)
            ),
        ]
    )

    # Add dummy MIDI labels
    output_labels.labels.extend(
        [
            MidiLabel(
                t=0,
                label="ol-t0-d1",
                duration=1,
                description="first overhead label",
                color=OutputLabel.rgb_color_to_int(255, 255, 0)
            ),
            MidiLabel(
                t=0,
                label="lo-t0-d1-p76",
                duration=1,
                description="first label overlay",
                color=OutputLabel.rgb_color_to_int(255, 128, 78),
                pitch=76
            ),
            MidiLabel(
                t=1,
                label="lo-t1-d0-p86",
                duration=0,
                color=OutputLabel.rgb_color_to_int(78, 128, 255),
                link="https://github.com/TEAMuP-dev/pyharp",
                pitch=86
            ),
            MidiLabel(
                t=1.5,
                label="ol-t1.5-d0.1",
                duration=0.1,
                description="second overhead label",
                color=OutputLabel.rgb_color_to_int(0, 255, 255)
            ),
        ]
    )

    # Delay return for chosen amount of time
    time.sleep(int(slider_1_time_sleep))

    return output_audio_path, output_midi_path, output_labels


# Build Gradio endpoint
with gr.Blocks() as demo:
    # Define input Gradio Components
    input_components = [
        gr.Audio(type="filepath",
                 label="Optional AudioInp")
        .harp_required(False)
        .set_info('This is an optional input track that has no effect on the output.'),
        gr.Slider(
            minimum=0,
            maximum=100,
            step=1,
            value=0,
            label="Time delay (s)",
            info="slider1"
        ),
        gr.Slider(
            minimum=0.0,
            maximum=1.0,
            step=0.01,
            value=0.5,
            label="Slider 2"
        ),
        gr.Slider(
            minimum=-20,
            maximum=20,
            step=1,
            value=0,
            label="Slider 3",
            info="slider3"
        ),
        gr.Dropdown(
            choices=["sad-cry.wav", "5-second.mp3", "Guiro.wav", "Claves.wav",
                     "test.wav", "test-w-gap.wav", "test-w-gap-stereo.wav"],
            value="5-second.mp3",
            label="Dropdown 1",
            info="dropdown1"
        ),
        gr.Dropdown(
            choices=["choice1", "choice2"],
            value="choice2",
            label="Dropdown 2",
            info="dropdown2"
        ),
        gr.Checkbox(
            value=True,
            label="Checkbox 1",
            info="checkbox1"
        ),
        gr.Checkbox(
            value=True,
            label="Checkbox 2"
        ),
        gr.Checkbox(
            value=True,
            label="Checkbox 3",
            info="checkbox1"
        ),
        gr.Textbox(
            value="Hello World",
            label="Input Text Prompt",
            info="textbox"
        )
    ]

    # Define output Gradio Components
    output_components = [
        gr.Audio(type="filepath",
                 label="Output Audio")
        .set_info("The selected audio file."),
        gr.File(type="filepath",
                label="Output Midi",
                file_types=[".mid", ".midi"])
        .set_info("The fixed MIDI file."),
        gr.JSON(label="Output Labels"),
    ]

    # Build a HARP-compatible endpoint
    app = build_endpoint(
        model_card=model_card,
        input_components=input_components,
        output_components=output_components,
        process_fn=process_fn,
    )


demo.queue().launch(share=True, show_error=False, pwa=True)
