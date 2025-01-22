# from pyharp import *

# import gradio as gr
# import torchaudio
# import torch
# from typing import Tuple
# import time

# # Create a ModelCard
# model_card = ModelCard(
#     name="Pitch Shifter",
#     description="A pitch shifting example for HARP.A pitch shifting example for HARPA pitch shifting example for HARPA pitch shifting example for HARPA pitch shifting example for HARPA pitch shifting example for HARPA pitch shifting example for HARPA pitch shifting example for HARPA pitch shifting example for HARPA pitch shifting example for HARPA pitch shifting example for HARPA pitch shifting example for HARPA pitch shifting example for HARPA pitch shifting example for HARPA pitch shifting example for HARPA pitch shifting example for HARPA pitch shifting example for HARPA pitch shifting example for HARPA pitch shifting example for HARP",
#     author="Hugo Flores Garcia",
#     tags=["example", "pitch shift"],
# )

# # Define the process function
# @torch.inference_mode()
# def process_fn(seconds_to_wait: int): # -> Tuple[str, LabelList]:

#     counter = 0
#     while counter < seconds_to_wait:
#         print(counter)
#         counter += 1
#         time.sleep(1)

#     return

# # Build Gradio endpoint
# with gr.Blocks() as demo:
#     # Define Gradio Components
#     input_components = [
#         gr.Number(
#             label='Seconds to wait',
#             value=10,
#             # type='number'
#         )
#     ]
    
#     output_components = [
#         # gr.Audio(
#         #     type='filepath',
#         #     label='Output Audio'
#         # ),
#         # gr.File(
#         #     type='filepath',
#         #     label="Output Midi",
#         #     file_types=[".mid", ".midi"]
#         # ),
#         # gr.JSON(label="Output Labels")
#     ]

#     app = build_endpoint(
#                 model_card=model_card,
#                 input_components=input_components,
#                 output_components=output_components,
#                 process_fn=process_fn)

# demo.queue(max_size=100, default_concurrency_limit=100)
# demo.launch(share=True, show_error=True)

import gradio as gr
import time

def counter():
    for i in range(30):
        # yield i
        print(i)
        time.sleep(0.5)

with gr.Blocks() as block:
    start_btn = gr.Button("start")
    textbox = gr.Textbox()
    stop_btn = gr.Button("stop")

    click_event = start_btn.click(fn=counter, inputs=None, outputs=textbox)
    stop_btn.click(fn=None, inputs=None, outputs=None, cancels=[click_event])
    
block.queue().launch()