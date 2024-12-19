from pyharp import *

import gradio as gr
import torchaudio
import torch
from typing import Tuple

# Create a ModelCard
model_card = ModelCard(
    name="Pitch Shifter",
    description="A pitch shifting example for HARP.",
    author="Hugo Flores Garcia",
    tags=["example", "pitch shift"],
    midi_in=False,
    midi_out=True
)

# Define the process function
@torch.inference_mode()
def process_fn(input_audio_path: str, pitch_shift_amount: int) -> Tuple[str, list]:

    if isinstance(pitch_shift_amount, torch.Tensor):
        pitch_shift_amount = pitch_shift_amount.long().item()

    sig = load_audio(input_audio_path)

    ps = torchaudio.transforms.PitchShift(
        sig.sample_rate,
        n_steps=pitch_shift_amount, 
        bins_per_octave=12, 
        n_fft=512
    ) 
    sig.audio_data = ps(sig.audio_data)

    output_audio_path = save_audio(sig)

    # No output labels
    output_labels = LabelList()

    midi_file = load_midi("../HARP/test.mid")
    output_midi_path = save_midi(midi_file)

    return output_midi_path, output_labels

# Build Gradio endpoint
with gr.Blocks() as demo:
    # Define Gradio Components
    input_components = [
        gr.Audio(
            type='filepath',
            label='Output Audio'
        ),
        gr.Slider(
            minimum=-24, 
            maximum=24, 
            step=1, 
            value=7, 
            label="Pitch Shift (semitones)"
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

demo.queue()
demo.launch(share=True, show_error=True)