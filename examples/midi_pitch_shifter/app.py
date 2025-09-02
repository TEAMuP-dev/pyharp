from pyharp import *

import gradio as gr


# Create a ModelCard
model_card = ModelCard(
    name='MIDI Pitch Shifter',
    description="A MIDI pitch shifting example for HARP v3.",
    author='TEAMuP',
    tags=["example", "midi", "pitch shift", "v3"]
)

# Define the process function
def process_fn(
    input_midi_path: str,
    pitch_shift_amount: int
) -> str:

    midi = load_midi(input_midi_path)

    for t in midi.tracks:
        for n in t.notes:
            n.pitch += int(pitch_shift_amount)
    
    output_midi_path = str(save_midi(midi))

    return output_midi_path

# Build Gradio endpoint
with gr.Blocks() as demo:
    # Define input Gradio Components
    input_components = [
        gr.File(type="filepath",
                label="Input Midi",
                file_types=[".mid", ".midi"])
        .harp_required(True),
        gr.Slider(
            minimum=-24,
            maximum=24,
            step=1,
            value=7,
            label="Pitch Shift (semitones)",
            info="Controls the amount of pitch shift in semitones"
        ),
    ]

    # Define output Gradio Components
    output_components = [
        gr.File(type="filepath",
                label="Output Midi",
                file_types=[".mid", ".midi"])
        .set_info("The pitch-shifted MIDI."),
    ]

    # Build a HARP-compatible endpoint
    app = build_endpoint(
        model_card=model_card,
        input_components=input_components,
        output_components=output_components,
        process_fn=process_fn,
    )

demo.queue().launch(share=True, show_error=False, pwa=True)
