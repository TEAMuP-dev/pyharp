from pyharp import *

import gradio as gr


model_card = ModelCard(
    name='<APP_NAME>',
    description='<APP_DESCRIPTION>',
    author='<APP_AUTHOR>',
    tags=['<APP>', '<TAGS>'],
    midi_in=True,
    midi_out=True
)

# <YOUR MODEL INITIALIZATION CODE HERE>


def process_fn(input_midi_path, pitch_shift_amount):
    """
    This function defines the MIDI processing steps

    Args:
        input_midi_path (str): the MIDI filepath to be processed.

        <YOUR_KWARGS>: additional keyword arguments necessary for processing.
            NOTE: These should correspond to and match order of UI elements defined below.

    Returns:
        output_midi_path (str): the filepath of the processed MIDI.
        output_labels (list of OutputLabel): any labels to display.
    """

    midi = load_midi(input_midi_path)

    output_labels = LabelList(labels=[])

    # Create a label for each note
    for t in midi.tracks:
        for n in t.notes:
            start = get_tick_time_in_seconds(n.time, midi)
            duration = get_tick_time_in_seconds(n.time + n.duration, midi)

            output_labels.append(MidiLabel(t=start, label=f'Note {n.pitch}', pitch=n.pitch, duration=duration))
    
    for t in midi.tracks:
        for n in t.notes:
            n.pitch += pitch_shift_amount
    
    output_midi_path = save_midi(midi, None)

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

    # Build endpoint
    app = build_endpoint(model_card=model_card,
                         components=components,
                         process_fn=process_fn)

demo.queue()
demo.launch(share=True, show_error=True)
