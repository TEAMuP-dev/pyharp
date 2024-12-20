from pyharp import *

import gradio as gr
from typing import Tuple

from gtts import gTTS

# Create a ModelCard
model_card = ModelCard(
    name="Text to speech",
    description="Generate speech from input text.",
    author="np",
    tags=["example", "tts"],
)

# Define the process function
def process_fn(input_text: str) -> Tuple[str, list]:

    tts_out = gTTS(text=input_text, lang="en", slow=False)

    output_path = "_outputs/output.wav"
    tts_out.save(output_path)

    # No output labels
    output_labels = LabelList()

    return output_path, output_labels

# Build Gradio endpoint
with gr.Blocks() as demo:
    # Define Gradio Components
    input_components = [
        # gr.Audio(
        #     type='filepath',
        #     label='Output Audio'
        # ),
        gr.Textbox(
            label="Text to process"
        )
    ]
    output_components = [
        gr.Audio(
            type='filepath',
            label='Output Audio'
        ),
        # gr.File(
        #     type='filepath',
        #     label="Output Midi",
        #     file_types=[".mid", ".midi"]
        # ),
        gr.JSON(label="Output Labels")
    ]

    app = build_endpoint(
                model_card=model_card,
                input_components=input_components,
                output_components=output_components,
                process_fn=process_fn)

demo.queue()
demo.launch(share=True, show_error=True)