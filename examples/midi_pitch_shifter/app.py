from pyharp import *

import gradio as gr


# Create a ModelCard
model_card = ModelCard(
    name='MIDI Pitch Shifter',
    description="A MIDI pitch shifting example for HARP.",
    author='xribene',
    tags=["example", "midi", "pitch shift", "v3"]
)


# Define the process function
def process_fn(input_midi_path, pitch_shift_amount):

    midi = load_midi(input_midi_path)

    for t in midi.tracks:
        for n in t.notes:
            n.pitch += int(pitch_shift_amount)
    
    output_midi_path = save_midi(midi, None)

    return str(output_midi_path)


# Build Gradio endpoint
with gr.Blocks() as demo:
    # Define Gradio Components
    input_components = [
        # Using the .harp_required(True) method to make the input required
        # meaning that HARP won't allow processing without this input
        gr.File(type="filepath", label="Input Midi", file_types=[".mid", ".midi"]).harp_required(True),
        gr.Slider(
            minimum=-24, maximum=24, step=1, value=7, label="Pitch Shift (semitones)"
        ),
    ]

    output_components = [
        gr.File(type="filepath", label="Output Midi", file_types=[".mid", ".midi"]),
    ]

    app = build_endpoint(
        model_card=model_card,
        input_components=input_components,
        output_components=output_components,
        process_fn=process_fn,
    )

demo.queue()
demo.launch(share=True, show_error=True)