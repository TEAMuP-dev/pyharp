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


def process_fn(input_midi_path):
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

    """
    <YOUR MIDI LOADING CODE HERE>
    # Load MIDI at specified path using symusic
    midi = load_midi(input_midi_path)
    """

    """
    <YOUR LABELING CODE HERE>
    # Initialize empty list
    output_labels = list()

    # Create a label for each note
    for t in midi.tracks:
        for n in t.notes:
            start = get_tick_time_in_seconds(n.time, midi)
            duration = get_tick_time_in_seconds(n.time + n.duration, midi)

            output_labels.append(MidiLabel(t=start, label=f'Note {n.pitch}', pitch=n.pitch, duration=duration))
    """

    """
    <YOUR MIDI PROCESSING CODE HERE>
    # Perform a trivial operation (i.e. pitch-shifting)
    for t in midi.tracks:
        for n in t.notes:
            n.pitch += 12
    """

    """
    <YOUR MIDI SAVING CODE HERE>
    # Save processed MIDI and obtain default path
    output_midi_path = save_midi(midi, None)
    """

    return output_midi_path, output_labels


# Build Gradio endpoint
with gr.Blocks() as demo:
    # Define Gradio Components
    components = [
        # <YOUR UI ELEMENTS HERE>
    ]

    # Build endpoint
    app = build_endpoint(model_card=model_card,
                         components=components,
                         process_fn=process_fn)

demo.queue()
demo.launch(share=True, show_error=True)
