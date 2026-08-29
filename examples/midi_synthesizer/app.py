"""
MIDI Synthesizer: a MIDI-to-audio template for PyHARP.

Shows two things: that input and output tracks need not be the same media type
(HARP sends a MIDI track and receives rendered audio back), and how to load a
model once at startup rather than on every request.
"""

from pyharp import *

from symusic import Synthesizer, BuiltInSF3
import gradio as gr
import audiotools


SAMPLE_RATE = 44100

# Anything expensive to construct belongs out here, at module scope, so that it is
# built once when the app starts instead of on every request. This soundfont is
# downloaded on first use, and a real model would be loaded onto the GPU in the
# same place; doing either inside process_fn would repeat the cost for every user.
synthesizer = Synthesizer(
    sf_path=BuiltInSF3.MuseScoreGeneral().path(download=True),
    sample_rate=SAMPLE_RATE,
    quality=4 # Default quality setting
)

# Metadata shown in HARP's model info panel
model_card = ModelCard(
    name="MIDI Synthesizer",
    description="A MIDI synthesizer example for HARP v3.",
    author="TEAMuP",
    tags=["example", "midi", "synthesizer", "v3"],
)


def process_fn(input_midi_path: str) -> str:
    """
    Render the input MIDI to audio with a general-purpose soundfont.

    Args:
        input_midi_path (str): Path to the MIDI file sent by HARP.

    Returns:
        output_audio_path (str): Path to the rendered audio.
    """

    midi = load_midi(input_midi_path)

    audio = audiotools.AudioSignal(
        synthesizer.render(midi, stereo=True),
        sample_rate=SAMPLE_RATE
    )

    output_audio_path = str(save_audio(audio))

    return output_audio_path


if __name__ == "__main__":
    # Build the Gradio endpoint
    with gr.Blocks() as demo:
        # Order must match the process_fn signature
        input_components = [
            gr.File(
                type="filepath",
                label="Input MIDI",
                file_types=[".mid", ".midi"]
            ).harp_required(True),
        ]

        # Order must match the values returned by process_fn
        output_components = [
            gr.Audio(
                type="filepath",
                label="Output Audio"
            ).set_info("The synthesized audio."),
        ]

        app = build_endpoint(
            model_card=model_card,
            input_components=input_components,
            output_components=output_components,
            process_fn=process_fn,
        )

    demo.queue().launch(share=True, show_error=True, pwa=True)
