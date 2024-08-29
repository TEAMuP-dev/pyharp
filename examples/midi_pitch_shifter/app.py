from pyharp import *

import gradio as gr


# Create a ModelCard
model_card = ModelCard(
    name='MIDI Pitch Shifter',
    description="A MIDI pitch shifting example for HARP.",
    author='xribene',
    tags=["example", "midi", "pitch shift"],
    midi_in=True,
    midi_out=True
)


# Define the process function
def process_fn(input_midi_path, pitch_shift_amount):

    midi = load_midi(input_midi_path)

    for t in midi.tracks:
        for n in t.notes:
            n.pitch += int(pitch_shift_amount)
    
    output_midi_path = save_midi(midi, None)

    # No output labels
    output_labels = LabelList()

    return output_midi_path, output_labels


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
