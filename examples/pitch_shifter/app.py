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
    input_audio_path: str,
    input_audio_path_2: str,
    pitch_shift_amount: int,
    slider_2: int,
    test_checkbox: bool,
    test_number: int,
    test_textbox: str,
    dropdown: str = "option_1",
) -> Tuple[str, LabelList]:

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
    dummy_label = MidiLabel(1, "dummy", 1, "a dummy label", 0, "www.cbenetatos.com", 42)
    dummy_midi_overhead_label = MidiLabel(
        2, "overhead", 1, "an overhead label", 0, "www.cbenetatos.com"
    )
    output_labels.labels.append(dummy_label)
    output_labels.labels.append(dummy_midi_overhead_label)

    midi_file = load_midi("../HARP/test.mid")
    output_midi_path = save_midi(midi_file)

    audio_file = load_audio("../HARP/wav-numbers/0.wav")
    output_audio_path = save_audio(audio_file)
    dummy_audio_label = AudioLabel(
        1, "dummy_audio", 1, "a dummy audio label", 0, "www.cbenetatos.com", 0.5
    )
    dummy_audio_overhead_label = AudioLabel(
        2, "overhead", 1, "an overhead label", 0)
    output_labels.labels.append(dummy_audio_label)
    output_labels.labels.append(dummy_audio_overhead_label)
    counter = 0
    while counter < 1:
        print(counter)
        counter += 1
        time.sleep(1)

    return output_audio_path, output_midi_path, output_labels


# Build Gradio endpoint
with gr.Blocks() as demo:
    # Define Gradio Components
    input_components = [
        gr.Audio(type="filepath", label="Input Audio A").harp_required(True),
        gr.Audio(type="filepath", label="Input Audio B").harp_required(False),
        gr.Slider(
            minimum=-24, maximum=24, step=1, value=7, label="Pitch Shift (semitones)"
        ),
        gr.Slider(minimum=-12, maximum=12, step=1, value=0, label="Slider 2"),
        gr.Checkbox(label="Test Checkbox", value=False),
        gr.Number(label="Test Number", value=42, maximum=100, minimum=0),
        gr.Textbox(label="Test Textbox", value="Hello World"),
        gr.Dropdown(
            label="Dropdown",
            choices=["option_1", "option_2", "option_3"],
            value="option_1",
        ),
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
