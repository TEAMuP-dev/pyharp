from pyharp import *

import gradio as gr
import torchaudio
import torch
import time
from typing import Tuple
import tempfile
import shutil
import requests
import os

def download_from_github(url, file_extension):
    """Download a file from GitHub to a local temporary file."""
    # Convert GitHub blob URL to raw content URL
    if "github.com" in url and "/blob/" in url:
        url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
    
    # Create a temporary file with the right extension
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
    temp_file.close()
    
    # Download the file
    response = requests.get(url, stream=True)
    response.raise_for_status()  # Ensure we got a valid response
    
    with open(temp_file.name, 'wb') as f:
        shutil.copyfileobj(response.raw, f)
    
    return temp_file.name

# Create a ModelCard
model_card = ModelCard(
    name="UI Test for HARP 3.0.0",
    description=\
        '''This is a test for the new UI features in HARP 3.0.0. The audio input is not used. You can click "process" without loading an audio file. Use the "Dropdown 1" to select the output audio file. The audio labels are added at 0%, 50%, and 100% - 1sec of the audio duration and 0, 0.5, and 1 of the amplitude.''',
    author="TeamUP",
    tags=["example", "ui", "test"],
)


# Define the process function
@torch.inference_mode()
def process_fn(
    input_audio_path, 
    # input_midi_path,
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

    if isinstance(slider_1_time_sleep, torch.Tensor):
        slider_1_time_sleep = slider_1_time_sleep.long().item()
    
    # # # Create dummy output files
    # midi = load_midi("../HARP/test/test.mid")
    # # midi = load_midi("https://github.com/TEAMuP-dev/HARP/blob/cb/gen-inputs/test/test.mid")
    # output_midi_path = save_midi(midi)

    # # # audio_file = load_audio("../wav-numbers/0.wav")
    # audio = load_audio("../HARP/test/5-second.mp3")
    # output_audio_path = save_audio(audio)

    # Ignore uploaded files and use hardcoded GitHub URLs
    midi_url = "https://github.com/TEAMuP-dev/HARP/blob/develop/test/test.mid"
    audio_url = f"https://github.com/TEAMuP-dev/HARP/blob/develop/test/{dropdown_1}"
    
    # Download to local temporary files
    local_midi_path = download_from_github(midi_url, ".mid")
    local_audio_path = download_from_github(audio_url, ".wav")
    
    # Load the downloaded files
    midi = load_midi(local_midi_path)
    audio = load_audio(local_audio_path)
    
    # Clean up temporary files (optional, after they're loaded)
    try:
        os.unlink(local_midi_path)
        os.unlink(local_audio_path)
    except Exception as e:
        print(f"Failed to clean up temporary files: {e}")
    
    output_midi_path = save_midi(midi)
    output_audio_path = save_audio(audio)

    # Dummy processing
    duration = audio.audio_data.shape[2] / audio.sample_rate

    output_labels = LabelList()
    # Create dummy labels
    output_labels.labels.extend(
        [
            MidiLabel(
                t=1,
                label="l-t1-p86",
                duration=1,
                description="a dummy midi label",
                color=OutputLabel.rgb_color_to_int(78, 128, 255),
                link="https://cbenetatos.com/",
                pitch=86,
            ),
            MidiLabel(
                t=0,
                label="l-t0-p76",
                duration=1,
                description="a dummy midi label",
                color=OutputLabel.rgb_color_to_int(255, 128, 78),
                link="https://docs.juce.com/master/classComponent.html",
                pitch=76,
            ),
            MidiLabel(0, "over1", 1, "an overhead label", OutputLabel.rgb_color_to_int(255, 255, 0)),
            MidiLabel(1.5, "over1", 0.1, "an overhead label", OutputLabel.rgb_color_to_int(0, 255, 255)),
        ]
    )

    # Convert input args to text
    descr_1 = f"dropdown_1: {dropdown_1}, dropdown_2: {dropdown_2}"
    descr_2 = f"checkbox_1: {checkbox_1}, checkbox_2: {checkbox_2} checkbox_3: {checkbox_3}"
    descr_3 = f"text_control: {text_control}"
    descr_4 = f"slider_1_time_sleep: {slider_1_time_sleep}, slider_2: {slider_2}, slider_3: {slider_3}"
    output_labels.labels.extend(
        [
            AudioLabel( 
                t=0, 
                label="t0-a0", 
                duration=1, 
                description=descr_1,
                color=OutputLabel.rgb_color_to_int(28, 102, 48), 
                link="https://docs.juce.com/master/classComponent.html", 
                amplitude=0),
            AudioLabel( 
                t=duration/2, 
                label="t05-a05", 
                duration=1, 
                description=descr_2,
                color=OutputLabel.rgb_color_to_int(102, 28, 48), 
                link="https://docs.juce.com/master/classComponent.html", 
                amplitude=0.5),
            AudioLabel( 
                t=duration - 1, 
                label="t1-a1", 
                duration=1, 
                description=descr_3,
                color=OutputLabel.rgb_color_to_int(48, 102, 28),
                link="https://docs.juce.com/master/classComponent.html", 
                amplitude=1),
            AudioLabel( 0, "over1", 1, descr_3, OutputLabel.rgb_color_to_int(0, 255, 0), link="https://docs.juce.com/master/classComponent.html"),
            AudioLabel( duration/2, "over2", 0.5, descr_4, OutputLabel.rgb_color_to_int(255, 0, 0), link="https://docs.juce.com/master/classComponent.html"),
            AudioLabel( duration, "over3", 0.1, "an overhead label", OutputLabel.rgb_color_to_int(0, 0, 255), link="https://docs.juce.com/master/classComponent.html"),
        ]
    )

    # label.description = f"The text control is: {text_control}"
    # output_labels.append(label)
    # Filter out the audio signal to the audible range
    # sig.audio_data = torchaudio.functional.lowpass_biquad(sig.audio_data, sig.sample_rate, cutoff_freq=slider_2)
    # output_audio_path = save_audio(sig)
    time.sleep(int(slider_1_time_sleep))
    # print(checkbox_control)
    # print(text_control)
    return output_audio_path, output_midi_path, output_labels


# Build Gradio endpoint
with gr.Blocks() as demo:
    # Define Gradio Components
    input_components = [
        gr.Audio(type="filepath", label="Optional AudioInp").harp_required(False).set_info('this is an optional input track'),
        # gr.File(type="filepath", label="Input Midi", file_types=[".mid", ".midi"]).harp_required(False),
        gr.Slider(
            minimum=1, 
            maximum=100, 
            step=1, 
            value=1, 
            label="Time delay (s)",
            info="slider1"
        ),
        gr.Slider(
            minimum=100, 
            maximum=10000, 
            step=50, 
            value=500, 
            label="Low-pass cutoff freq (Hz)"
        ),
        gr.Slider(
            minimum=0, 
            maximum=100, 
            step=1, 
            value=50, 
            label="Slider 3",
            info="slider3"
        ),
        gr.Dropdown(
            choices=["sad-cry.wav", "5-second.mp3", "Guiro.wav", "Claves.wav",
                     "test.wav", "test-w-gap.wav", "test-w-gap-stereo.wav"],
            label="Dropdown 1",
            value="5-second.mp3",
            info="dropdown1"
        ),
        gr.Dropdown(
            choices=["choice1", "choice2"], 
            label="Dropdown 2",
            value="choice2",
            info="dropdown2"
        ),
        gr.Checkbox(
            label="Checkbox 1",
            value=True,
            info="checkbox1"
        ),
        gr.Checkbox(
            label="Checkbox 2",
            value=True
        ),
        gr.Checkbox(
            label="Checkbox 3",
            value=True,
            info="checkbox1"
        ),
        gr.Textbox(
            label="Input Text Prompt",
            value="Hello World",
            info="textbox"
        )
    ]

    output_components = [
        gr.Audio(type="filepath", label="Output Audio"),
        gr.File(type="filepath", label="Output Midi", file_types=[".mid", ".midi"]),
        gr.JSON(label="Output Labels"),
    ]

    app = build_endpoint(
        model_card=model_card,
        input_components=input_components,
        output_components=output_components,
        process_fn=process_fn,
    )


demo.queue().launch(share=True, show_error=False, pwa=True)
