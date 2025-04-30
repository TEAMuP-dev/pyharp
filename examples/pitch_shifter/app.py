from pyharp import *

import gradio as gr
import torchaudio
import torch


# Create a ModelCard
model_card = ModelCard(
    name="Pitch Shifter",
    description="A pitch shifting example for HARP.",
    author="Hugo Flores Garcia",
    tags=["example", "pitch shift"],
    midi_in=False,
    midi_out=False
)


# Define the process function
@torch.inference_mode()
def process_fn(input_audio_path, pitch_shift_amount):

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

    output_labels = LabelList()

    max_val = sig.numpy().mean(0).mean(0).max()
    max_t = sig.numpy().mean(0).mean(0).argmax() / sig.sample_rate
    output_labels.append(AudioLabel(t=max_t, label='max', amplitude=max_val))

    min_val = sig.numpy().mean(0).mean(0).min()
    min_t = sig.numpy().mean(0).mean(0).argmin() / sig.sample_rate
    output_labels.append(AudioLabel(
        t=min_t,
        label='min',
        description='this is the lowest amplitude in the audio waveform',
        amplitude=min_val,
        duration=2.0,
        color=OutputLabel.rgb_color_to_int(0, 128, 145, 0.8),
        link="https://www.google.com/"
    ))

    output_labels.append(AudioLabel(t=1, label='1 sec'))

    return output_audio_path, output_labels


# Build Gradio endpoint
with gr.Blocks() as demo:
    # Define Gradio Components
    components = [
        gr.Slider(
            minimum=-24, 
            maximum=24, 
            step=1, 
            value=7, 
            label="Pitch Shift (semitones)"
        ),
    ]

    app = build_endpoint(model_card=model_card,
                         components=components,
                         process_fn=process_fn)

demo.queue()
demo.launch(share=True, show_error=True)