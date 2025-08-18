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
    description="A pitch shifting example for HARP v3.",
    author="TeamUP",
    tags=["example", "pitch shift", 'v3'],
)


# Define the process function
@torch.inference_mode()
def process_fn(
    input_audio_path: str,
    pitch_shift_amount: int,
) -> str:

    pitch_shift_amount = int(pitch_shift_amount)

    sig = load_audio(input_audio_path)

    ps = torchaudio.transforms.PitchShift(
        sig.sample_rate,
        n_steps=pitch_shift_amount,
        bins_per_octave=12,
        n_fft=512
    )
    sig.audio_data = ps(sig.audio_data)

    output_audio_path = save_audio(sig)

    return str(output_audio_path)


# Build Gradio endpoint
with gr.Blocks() as demo:
    # Define Gradio Components
    input_components = [
        # Using the .harp_required(True) method to make the input required
        # meaning that HARP won't allow processing without this input
        gr.Audio(type="filepath", label="Input Audio A").harp_required(True),
        gr.Slider(
            minimum=-24, maximum=24, step=1, value=7, label="Pitch Shift (semitones)"
        ),
    ]

    output_components = [
        gr.Audio(type="filepath", label="Output Audio"),
    ]

    app = build_endpoint(
        model_card=model_card,
        input_components=input_components,
        output_components=output_components,
        process_fn=process_fn,
    )


demo.queue().launch(share=True, show_error=False, pwa=True)
