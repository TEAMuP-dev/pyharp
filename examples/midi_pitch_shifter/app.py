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
    author="TEAMuP",
    description=(
        "Transposes every note in a MIDI file by a number of semitones, leaving its timing and "
        "instrumentation unchanged."
    ),
    tags=[Category.EFFECTS, Category.UTILITY, "example", "pitch shift"],
)


def process_fn(input_midi_path: str, pitch_shift_amount: int) -> str:
    """
    Transpose every note in the input MIDI.

    Args:
        input_midi_path (str): Path to the MIDI file sent by HARP.
        pitch_shift_amount (int): Semitones by which to transpose.

    Returns:
        output_midi_path (str): Path to the transposed MIDI.
    """

    # Refused with a message, since anything but a gr.Error reaches HARP as a
    # failure without a reason on which a user can act
    try:
        midi = load_midi(input_midi_path)
    except Exception as exc:
        raise gr.Error(f"Could not read the MIDI file: {exc}") from exc

    # Edit the loaded score in place to preserve ticks per quarter, tempo,
    # and track structure.
    for track in midi.tracks:
        for note in track.notes:
            note.pitch += int(pitch_shift_amount)

    output_midi_path = str(save_midi(midi))

    return output_midi_path


# The processing worker imports this file, so the app must not be built there
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
            ).harp_required(True).set_info("The MIDI to transpose."),
            gr.Slider(
                minimum=-24,
                maximum=24,
                step=1,
                value=7,
                label="Pitch Shift (semitones)",
                info="The number of semitones by which to transpose."
            ),
        ]

        # Order must match the values returned by process_fn
        output_components = [
            gr.File(
                type="filepath",
                label="Transposed MIDI",
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
