import torch
import torchaudio 

from pathlib import Path
import gradio as gr
import shutil
from pyharp import ModelCard, build_endpoint, save_and_return_filepath

# Define the process function
@torch.inference_mode()
def process_fn(input_audio_path, pitch_shift_amount):
    from audiotools import AudioSignal

    if isinstance(pitch_shift_amount, torch.Tensor):
        pitch_shift_amount = pitch_shift_amount.long().item()

    sig = AudioSignal(input_audio_path)

    ps = torchaudio.transforms.PitchShift(
        sig.sample_rate,
        n_steps=pitch_shift_amount, 
        bins_per_octave=12, 
        n_fft=512
    ) 
    sig.audio_data = ps(sig.audio_data)

    output_audio_path = save_and_return_filepath(sig)

    return output_audio_path

# Create a ModelCard
card = ModelCard(
    name="Pitch Shifter",
    description="A pitch shifting example for HARP.",
    author="Hugo Flores Garcia",
    tags=["example", "pitch shift"]
)


# Build the endpoint
with gr.Blocks() as demo:

    # Define your Gradio interface
    inputs = [
        gr.Audio(
            label="Audio Input", 
            type="filepath"
        ), # make sure to have an audio input with type="filepath"!
        gr.Slider(
            minimum=-24, 
            maximum=24, 
            step=1, 
            value=7, 
            label="Pitch Shift (semitones)"
        ),
    ]
    
    # make an output audio widget
    output = gr.Audio(label="Audio Output", type="filepath")

    # Build the endpoint
    ctrls_data, ctrls_button, process_button = build_endpoint(inputs, output, process_fn, card)

demo.launch(share=True)
