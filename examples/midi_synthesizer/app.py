from pyharp import *

from symusic import Synthesizer, BuiltInSF3, dump_wav
import gradio as gr
import audiotools


# Create a ModelCard
model_card = ModelCard(
    name='MIDI Synthesizer',
    description="A MIDI synthesizer example for HARP v3.",
    author='TEAMuP',
    tags=["example", "midi", "synthesizer", "v3"]
)

# Define the process function
def process_fn(input_midi_path: str) -> str:

    midi = load_midi(input_midi_path)

    # Create a synthesizer with default settings
    synthesizer = Synthesizer(
        sf_path=BuiltInSF3.MuseScoreGeneral().path(download=True),
        sample_rate=44100,
        quality=4 # Default quality setting
    )

    data = synthesizer.render(midi, stereo=True)
    audio = audiotools.AudioSignal(data, sample_rate=44100)

    output_audio_path = str(save_audio(audio))

    return output_audio_path

# Build Gradio endpoint
with gr.Blocks() as demo:
    # Define input Gradio Components
    input_components = [
        gr.File(type="filepath",
                label="Input Midi",
                file_types=[".mid", ".midi"])
        .harp_required(True),
    ]

    # Define output Gradio Components
    output_components = [
        gr.Audio(type="filepath",
                label="Output Audio")
        .set_info("The synthesized audio."),
    ]

    # Build a HARP-compatible endpoint
    app = build_endpoint(
        model_card=model_card,
        input_components=input_components,
        output_components=output_components,
        process_fn=process_fn,
    )

demo.queue().launch(share=True, show_error=False, pwa=True)
