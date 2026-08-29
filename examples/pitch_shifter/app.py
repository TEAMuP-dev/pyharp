"""
Pitch Shifter: an audio-to-audio template for PyHARP.

Demonstrates the simplest useful shape for a HARP app: one required audio
input track, one slider control, and one audio output track.
"""

from pyharp import *

import gradio as gr
import torchaudio
import torch


# Metadata shown in HARP's model info panel
model_card = ModelCard(
    name="Pitch Shifter",
    description="A pitch shifting example for HARP v3.",
    author="TEAMuP",
    tags=["example", "audio", "pitch shift", "v3"],
)


@torch.inference_mode()
def process_fn(input_audio_path: str, pitch_shift_amount: int) -> str:
    """
    Shift the pitch of the input audio.

    Args:
        input_audio_path (str): Path to the audio file sent by HARP.
        pitch_shift_amount (int): Amount to shift by, in semitones.

    Returns:
        output_audio_path (str): Path to the pitch-shifted audio.
    """

    signal = load_audio(input_audio_path)

    pitch_shift = torchaudio.transforms.PitchShift(
        signal.sample_rate,
        n_steps=int(pitch_shift_amount),
        bins_per_octave=12,
        n_fft=512
    )
    signal.audio_data = pitch_shift(signal.audio_data)

    output_audio_path = str(save_audio(signal))

    return output_audio_path


if __name__ == "__main__":
    # Build the Gradio endpoint
    with gr.Blocks() as demo:
        # Audio and MIDI components become tracks in HARP; everything else
        # becomes a GUI control. Order must match the process_fn signature.
        input_components = [
            gr.Audio(
                type="filepath",
                label="Input Audio"
            ).harp_required(True),
            gr.Slider(
                minimum=-24,
                maximum=24,
                step=1,
                value=7,
                label="Pitch Shift (semitones)",
                info="Amount to shift the pitch by."
            ),
        ]

        # Order must match the values returned by process_fn
        output_components = [
            gr.Audio(
                type="filepath",
                label="Output Audio"
            ).set_info("The pitch-shifted audio."),
        ]

        app = build_endpoint(
            model_card=model_card,
            input_components=input_components,
            output_components=output_components,
            process_fn=process_fn,
        )

    demo.queue().launch(share=True, show_error=True, pwa=True)
