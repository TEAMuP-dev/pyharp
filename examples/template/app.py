from pyharp import ModelCard, build_endpoint, save_and_return_filepath
from audiotools import AudioSignal

import gradio as gr


card = ModelCard(
    name='<APP_NAME>',
    description='<APP_DESCRIPTION>',
    author='<APP_AUTHOR>',
    tags=['<APP>', '<TAGS>']
)

"""<YOUR MODEL INITIALIZATION CODE HERE>"""


def process_fn(input_audio_path):
    """
    This function defines the audio processing steps

    Args:
        input_audio_path (str): the audio filepath to be processed.

        <YOUR_KWARGS>: additional keyword arguments necessary for processing.
            NOTE: These should correspond to and match order of UI elements defined below.

    Returns:
        output_audio_path (str): the filepath of the processed audio.
    """

    """
    <YOUR AUDIO LOADING CODE HERE>
    """
    #sig = AudioSignal(input_audio_path)

    """
    <YOUR AUDIO PROCESSING CODE HERE>
    """
    #sig.audio_data = 2 * sig.audio_data

    """
    <YOUR AUDIO SAVING CODE HERE>
    """
    #output_audio_path = save_and_return_filepath(sig)

    return output_audio_path


# Build the Gradio endpoint
with gr.Blocks() as demo:
    # Define widgets
    inputs = [
        gr.Audio(
            label='Audio Input',
            type='filepath'
        ),
        #<YOUR UI ELEMENTS HERE>
    ]

    # Make an output audio widget
    output = gr.Audio(label='Audio Output', type='filepath')

    output_text = None
    # Add output text widget (OPTIONAL)
    # output_text = gr.Textbox(label='Output text')

    # Build the endpoint
    widgets = build_endpoint(inputs, output, process_fn, card, text_out=output_text)

demo.queue()
demo.launch(share=True)
