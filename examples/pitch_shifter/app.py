from pyharp import *

import gradio as gr
import torchaudio
import torch
from typing import Tuple
import time
from dataclasses import dataclass, asdict


# Create a ModelCard
model_card = ModelCard(
    name="Pitch Shifter",
    description="A pitch shifting example for HARP.A pitch shifting example for HARPA pitch shifting example for HARPA pitch shifting example for HARPA pitch shifting example for HARPA pitch shifting example for HARPA pitch shifting example for HARPA pitch shifting example for HARPA pitch shifting example for HARPA pitch shifting example for HARPA pitch shifting example for HARPA pitch shifting example for HARPA pitch shifting example for HARPA pitch shifting example for HARPA pitch shifting example for HARPA pitch shifting example for HARPA pitch shifting example for HARPA pitch shifting example for HARPA pitch shifting example for HARP",
    author="Hugo Flores Garcia",
    tags=["example", "pitch shift"],
)

# Define the process function
@torch.inference_mode()
def process_fn(
    input_audio_path: str, input_audio_path_2: str, 
               pitch_shift_amount: int, slider_2: int,
               test_checkbox: bool, 
               test_number: int, test_textbox: str) -> Tuple[str, LabelList]:

    # if isinstance(pitch_shift_amount, torch.Tensor):
    #     pitch_shift_amount = pitch_shift_amount.long().item()

    # sig = load_audio(input_audio_path)

    # ps = torchaudio.transforms.PitchShift(
    #     sig.sample_rate,
    #     n_steps=pitch_shift_amount, 
    #     bins_per_octave=12, 
    #     n_fft=512
    # ) 
    # sig.audio_data = ps(sig.audio_data)

    # output_audio_path = save_audio(sig)

    # No output labels
    output_labels = LabelList()
    dummy_label = MidiLabel(1, "skata", 1, "skatoules", 0, "www.cbenetatos.com", 42)
    output_labels.labels.append(dummy_label)
    
    midi_file = load_midi("../HARP/test.mid")
    output_midi_path = save_midi(midi_file)
    counter = 0
    while counter < 10:
        print(counter)
        counter += 1
        time.sleep(1)

    return output_midi_path, output_labels

# Build Gradio endpoint
with gr.Blocks() as demo:
    # Define Gradio Components
    input_components = [
        gr.Audio(
            type='filepath',
            label='Input Audio A'
        ),
        gr.Audio(
            type='filepath',
            label='Input Audio B'
        ),
        gr.Slider(
            minimum=-24, 
            maximum=24, 
            step=1, 
            value=7, 
            label="Pitch Shift (semitones)"
        ),
        gr.Slider(
            minimum=-12, 
            maximum=12, 
            step=1, 
            value=0, 
            label="Slider 2"
        ),
        gr.Checkbox(
            label="Test Checkbox",
            value=False
        ),
        gr.Number(
            label="Test Number",
            value=42,
            maximum=100,
            minimum=0

        ),
        gr.Textbox(
            label="Test Textbox",
            value="Hello World"
        ),
    ]
    
    output_components = [
        # gr.Audio(
        #     type='filepath',
        #     label='Output Audio'
        # ),
        gr.File(
            type='filepath',
            label="Output Midi",
            file_types=[".mid", ".midi"]
        ),
        gr.JSON(label="Output Labels")
    ]

    app = build_endpoint(
                model_card=model_card,
                input_components=input_components,
                output_components=output_components,
                process_fn=process_fn)
    

demo.queue().launch(share=True, show_error=False)