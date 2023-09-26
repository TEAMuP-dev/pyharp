from typing import Dict
from pathlib import Path

import librosa
import torch
from audiotools import AudioSignal

import gradio as gr
from pyharp import ModelCard, build_endpoint


def hpss(signal: AudioSignal, **kwargs):
    h, p = librosa.effects.hpss(signal.audio_data.squeeze().numpy(), **kwargs)

    if h.ndim == 1:
        h = h[None, None, :]
        p = p[None, None, :]
    elif h.ndim == 2:
        h = h[None, :, :]
        p = p[None, :, :]
    else:
        assert False

    harmonic_signal = signal.clone()
    harmonic_signal.audio_data = torch.from_numpy(h)

    percussive_signal = signal.clone()
    percussive_signal.audio_data = torch.from_numpy(p)

    return harmonic_signal, percussive_signal


MIN_DB = -120

def process_fn(audio_file, 
               harmonic_db: float, 
               percussive_db: float, 
               kernel_size: int = 31, 
               margin: float = 1.0):
    sig = AudioSignal(audio_file)
    
    harmonic, percussive = hpss(sig, kernel_size=kernel_size, margin=margin)

    def clip(db):
        if db == MIN_DB:
            db = -float("inf")

        return db

    # mix the signals, apply gain
    sig = (
        harmonic.volume_change(clip(harmonic_db)) 
        + percussive.volume_change(clip(percussive_db))
    )

    output_dir = Path("_outputs")
    output_dir.mkdir(exist_ok=True)
    sig.write(output_dir / "output.wav")
    return sig.path_to_file
    
# Create a ModelCard
card = ModelCard(
    name="Harmonic / Percussive Separation",
    description="Remix a Track into its harmonic and percussive components.",
    author="Hugo Flores Garcia",
    tags=["example", "separator", "hpss"]
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
            minimum=MIN_DB, 
            maximum=24, 
            step=1, 
            value=0, 
            label="Harmonic Level (dB)"
        ),
        gr.Slider(
            minimum=MIN_DB, 
            maximum=24, 
            step=1, 
            value=0, 
            label="Percussive Level (dB)"
        ),
        gr.Slider(
            minimum=1, 
            maximum=101, 
            step=1, 
            value=31, 
            label="Kernel Size"
        ),
        gr.Slider(
            minimum=0.5, 
            maximum=5.0, 
            step=0.1, 
            value=1.0, 
            label="Margin"
        ),
    ]
    
    # make an output audio widget
    output = gr.Audio(label="Audio Output", type="filepath")

    # Build the endpoint
    ctrls_data, ctrls_button, process_button = build_endpoint(inputs, output, process_fn, card)

demo.launch(share=True)
