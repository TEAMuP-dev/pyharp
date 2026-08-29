"""
MIDI Pitch Shifter: a MIDI-to-MIDI template for PyHARP.

Mirrors the audio pitch shifter, but operates on MIDI. HARP renders a MIDI
track as a piano roll rather than a waveform.
"""

from pyharp import *

import gradio as gr


# Metadata shown in HARP's model info panel
model_card = ModelCard(
    name="MIDI Pitch Shifter",
    description="A MIDI pitch shifting example for HARP v3.",
    author="TEAMuP",
    tags=["example", "midi", "pitch shift", "v3"],
)


def process_fn(input_midi_path: str, pitch_shift_amount: int) -> str:
    """
    Transpose every note in the input MIDI.

    Args:
        input_midi_path (str): Path to the MIDI file sent by HARP.
        pitch_shift_amount (int): Amount to transpose by, in semitones.

    Returns:
        output_midi_path (str): Path to the transposed MIDI.
    """

    midi = load_midi(input_midi_path)

    for track in midi.tracks:
        for note in track.notes:
            note.pitch += int(pitch_shift_amount)

    output_midi_path = str(save_midi(midi))

    return output_midi_path


if __name__ == "__main__":
    # Build the Gradio endpoint
    with gr.Blocks() as demo:
        # A gr.File restricted to MIDI extensions becomes a MIDI track in HARP.
        # Order must match the process_fn signature.
        input_components = [
            gr.File(
                type="filepath",
                label="Input MIDI",
                file_types=[".mid", ".midi"]
            ).harp_required(True),
            gr.Slider(
                minimum=-24,
                maximum=24,
                step=1,
                value=7,
                label="Pitch Shift (semitones)",
                info="Amount to transpose by."
            ),
        ]

        # Order must match the values returned by process_fn
        output_components = [
            gr.File(
                type="filepath",
                label="Output MIDI",
                file_types=[".mid", ".midi"]
            ).set_info("The transposed MIDI."),
        ]

        app = build_endpoint(
            model_card=model_card,
            input_components=input_components,
            output_components=output_components,
            process_fn=process_fn,
        )

    demo.queue().launch(share=True, show_error=True, pwa=True)
