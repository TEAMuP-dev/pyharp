"""
Pitch Shifter: an audio-to-audio template for PyHARP.

Demonstrates the simplest useful shape for a HARP app: one required audio
input track, one slider control, and one audio output track.
"""

from pyharp import *

from pathlib import Path

import gradio as gr
import torchaudio
import torch


# Metadata shown in HARP's model info panel
model_card = ModelCard(
    name="Pitch Shifter",
    author="TEAMuP",
    description="A pitch shifting example for HARP v3.",
    tags=[Category.EFFECTS, Category.UTILITY, "example", "pitch shift"],
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

    # Returned in the container it arrived in, unless that container is lossy.
    # Such a file was encoded once already, and the shift moves that encoder's
    # artifacts out from under the maskers that hid them, so writing .mp3 back
    # would layer a second round of loss over a first that is now audible.
    input_ext = Path(input_audio_path).suffix.lower()
    output_ext = input_ext if input_ext in {".wav", ".aiff", ".flac"} else ".wav"

    output_audio_path = str(save_audio(signal, get_default_path(ext=output_ext)))

    return output_audio_path


# The processing worker imports this file, so the app must not be built there
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
            # No format is set, so Gradio returns the container process_fn chose
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
