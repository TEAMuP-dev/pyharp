from pyharp import *

import gradio as gr
import torchaudio
import torch
import time

# Create a ModelCard
model_card = ModelCard(
    name="Dummy UI Test",
    description="A demo of labels and all the input controls suppoerted in HARP",
    author="xribene",
    tags=["example", "pitch shift"],
    midi_in=False,
    midi_out=False
)


# Define the process function
@torch.inference_mode()
def process_fn(input_audio_path, 
               slider_1_time_sleep, 
               slider_2,
               slider_3,
               dropdown_1, 
               dropdown_2,
               checkbox_1,
               checkbox_2,
               checkbox_3,
               text_control
               ):

    if isinstance(slider_1_time_sleep, torch.Tensor):
        slider_1_time_sleep = slider_1_time_sleep.long().item()

    # No output labels
    output_labels = LabelList()
    output_label = None
    
    sig = load_audio(input_audio_path)
    # Get duration in seconds
    duration = sig.audio_data.shape[2] / sig.sample_rate

    if dropdown_1 == "zero":
        sig.audio_data = torch.zeros_like(sig.audio_data)
        label = AudioLabel(
            t = 0.0,
            label = "silence",
            amplitude = 0.0,
            duration = duration / 5
        )
        
    elif dropdown_1 == "half":
        sig.audio_data = 0.5 * torch.randn_like(sig.audio_data)
        
        label = AudioLabel(
            t = duration / 2 - duration / 8,
            label = "low",
            amplitude = 0.5,
            duration = duration / 4
        )
    elif dropdown_1 == "full":
        sig.audio_data = torch.randn_like(sig.audio_data)
        label = AudioLabel(
            t = duration - duration / 3,
            label = "full",
            amplitude = 1.0,
            duration = duration / 3
        )

    label.description = f"The text control is: {text_control}"
    output_labels.append(label)
    # Filter out the audio signal to the audible range
    sig.audio_data = torchaudio.functional.lowpass_biquad(sig.audio_data, sig.sample_rate, cutoff_freq=slider_2)
    output_audio_path = save_audio(sig)
    time.sleep(int(slider_1_time_sleep))
    # print(checkbox_control)
    # print(text_control)
    return output_audio_path, output_labels


# Build Gradio endpoint
with gr.Blocks() as demo:
    # Define Gradio Components
    components = [
        gr.Slider(
            minimum=1, 
            maximum=100, 
            step=1, 
            value=1, 
            label="Time delay (s)"
        ),
        gr.Slider(
            minimum=100, 
            maximum=10000, 
            step=50, 
            value=500, 
            label="Low-pass cutoff freq (Hz)"
        ),
        gr.Slider(
            minimum=0, 
            maximum=100, 
            step=1, 
            value=50, 
            label="Slider 3"
        ),
        gr.Dropdown(
            choices=["zero", "half", "full"], 
            label="Dropdown 1",
            value="zero"
        ),
        gr.Dropdown(
            choices=["choice1", "choice2"], 
            label="Dropdown 2",
            value="choice2"
        ),
        gr.Checkbox(
            label="Checkbox 1",
            value=True
        ),
        gr.Checkbox(
            label="Checkbox 2",
            value=True
        ),
        gr.Checkbox(
            label="Checkbox 3",
            value=True
        ),
        gr.Textbox(
            label="Input Text Prompt",
        )
    ]

    app = build_endpoint(model_card=model_card,
                         components=components,
                         process_fn=process_fn)

demo.queue()
demo.launch(share=True, show_error=True)