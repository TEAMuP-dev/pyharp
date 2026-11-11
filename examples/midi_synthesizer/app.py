"""
MIDI Synthesizer: a MIDI-to-audio template for PyHARP.

Shows three things: that input and output tracks need not be the same media
type (HARP sends a MIDI track and receives rendered audio back), how to load a
model once at startup rather than on every request, and how to take an optional
file that is neither audio nor MIDI, here a soundfont to render with.
"""

from pyharp import *

from symusic import Synthesizer, BuiltInSF3
import gradio as gr
import audiotools


SAMPLE_RATE = 44100

# Metadata shown in HARP's model info panel
model_card = ModelCard(
    name="MIDI Synthesizer",
    author="TEAMuP",
    description=(
        "Renders a MIDI file into stereo audio with the MuseScore General soundfont, or with a "
        "soundfont of your own."
    ),
    tags=[
        Subcategory.INSTRUMENT_SYNTHESIS,
        Category.UTILITY,
        SampleRate(SAMPLE_RATE),
        Channels(2),
        "example",
        "soundfont",
    ],
)

# Anything expensive to construct belongs outside process_fn, so that it is built
# once when the app starts instead of on every request. Only the worker that runs
# process_fn needs it, and the worker imports this file under a name other than
# __main__, so it is built there alone. The server would otherwise hold a second
# copy, and both processes would download the soundfont at once. A real model
# would be loaded onto the GPU in the same place.
if __name__ != "__main__":
    synthesizer = Synthesizer(
        sf_path=BuiltInSF3.MuseScoreGeneral().path(download=True),
        sample_rate=SAMPLE_RATE,
        quality=4,  # Default quality setting
    )


def process_fn(input_midi_path: str, soundfont_path: str | None) -> str:
    """
    Render the input MIDI to audio with a soundfont.

    Args:
        input_midi_path (str): Path to the MIDI file sent by HARP.
        soundfont_path (str | None): Path to a soundfont to use in place of the
            general-purpose one, if HARP sent one.

    Returns:
        output_audio_path (str): Path to the rendered audio.
    """

    # Refused with a message, since anything but a gr.Error reaches HARP as a
    # failure without a reason on which a user can act
    try:
        midi = load_midi(input_midi_path)
    except Exception as exc:
        raise gr.Error(f"Could not read the MIDI file: {exc}") from exc

    # MuseScore General is the only soundfont symusic provides, so any other comes from
    # the user. It is read for this request alone, which is quick next to the rendering.
    renderer = synthesizer

    if soundfont_path:
        try:
            renderer = Synthesizer(sf_path=soundfont_path, sample_rate=SAMPLE_RATE, quality=4)
        except Exception as exc:
            raise gr.Error(f"Could not read the soundfont: {exc}") from exc

    audio = audiotools.AudioSignal(renderer.render(midi, stereo=True), sample_rate=SAMPLE_RATE)

    output_audio_path = str(save_audio(audio))

    return output_audio_path


# The processing worker imports this file, so the app must not be built there
if __name__ == "__main__":
    # Build the Gradio endpoint
    with gr.Blocks() as demo:
        # Order must match the process_fn signature
        input_components = [
            gr.File(type="filepath", label="Input MIDI", file_types=[".mid", ".midi"])
            .harp_required(True)
            .set_info("The MIDI to render."),
            # A gr.File without MIDI extensions becomes a file picker among the controls
            gr.File(type="filepath", label="Soundfont", file_types=[".sf2", ".sf3"])
            .harp_required(False)
            .set_info("A soundfont to render with in place of MuseScore General."),
        ]

        # Order must match the values returned by process_fn
        output_components = [
            gr.Audio(type="filepath", format="wav", label="Synthesized Audio").set_info(
                "The synthesized audio."
            ),
        ]

        app = build_endpoint(
            model_card=model_card,
            input_components=input_components,
            output_components=output_components,
            process_fn=process_fn,
        )

    demo.queue().launch(share=True, show_error=True, pwa=True, ssr_mode=False)
