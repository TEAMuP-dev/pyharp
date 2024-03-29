from pyharp import save_midi, load_midi, build_endpoint, ModelCard

import gradio as gr


model_card = ModelCard(
    name='MIDI_PITCH_SHIFTER',
    description='<APP_DESCRIPTION>',
    author='XRIBENE',
    tags=['<APP>', '<TAGS>'],
    midi_in=True,
    midi_out=True
)

# <YOUR MODEL INITIALIZATION CODE HERE>


def process_fn(input_midi, pitch_shift_amount):
    """
    This function defines the MIDI processing steps

    Args:
        input_midi_path (str): the MIDI filepath to be processed.

        <YOUR_KWARGS>: additional keyword arguments necessary for processing.
            NOTE: These should correspond to and match order of UI elements defined below.

    Returns:
        output_midi_path (str): the filepath of the processed MIDI.
    """

    if hasattr(input_midi, 'name'):
        input_midi_path = input_midi.name
    else:
        input_midi_path = input_midi  # Assuming it's already a path in this case

    print(input_midi_path)
    # print(input_midi_path_2)
    midi = load_midi(input_midi_path)

    # Perform a trivial operation (i.e. pitch-shifting)
    for t in midi.tracks:
        for n in t.notes:
            n.pitch += int(pitch_shift_amount)

    output_midi_path = save_midi(midi, None)

    return output_midi_path


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
demo.launch(share=True)
