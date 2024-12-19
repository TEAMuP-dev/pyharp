# import gradio as gr
# import time
# from threading import Thread

# running_thread = gr.State()

# def callback():
#     for i in range(100):
#         print(i)
#         time.sleep(0.5)
#         # yield
        

# def foo():
#     thread = Thread(target=callback)
#     thread.start()
#     return thread

# with gr.Blocks() as block:
#     start_btn = gr.Button("start")
#     stop_btn = gr.Button("stop")
#     click_event = start_btn.click(fn=foo, inputs=None, outputs=[running_thread], concurrency_limit=2)
#     stop_btn.click(fn=None, inputs=None, outputs=None, cancels=[click_event]).then(lambda t: t.join(timeout=1), inputs=running_thread, outputs=None)
    
    
# block.queue()
# block.launch(share=True, show_error=True)

# running_thread = gr.State()
# def generate_text(text):
#     thread = Thread(target=model.generate, kwargs=generation_kwargs)
#     thread.start()
#     for out in streamer:
#         yield out, thread

# generate = gen.click(generate_text, ..., outputs=[textbox, running_thread])
# stop.click(None, inputs=None, outputs=None, cancels=[generate]).then(lambda t: t.join(timeout=1), inputs=running_thread, outputs=None)

import gradio as gr
import time
import threading

class ThreadManager:
    def __init__(self):
        self.running_thread = None
        self.should_stop = False

    def foo(self):
        for i in range(300):
            if self.should_stop:
                print("Stopped!")
                break
            print(i)
            time.sleep(0.5)

    def start_foo(self):
        self.should_stop = False  # Reset the stop flag
        self.running_thread = threading.Thread(target=self.foo)
        self.running_thread.start()
        return self.running_thread

    def stop_foo(self):
        self.should_stop = True
        if self.running_thread and self.running_thread.is_alive():
            self.running_thread.join(timeout=1)  # Wait for the thread to finish

# Create an instance of ThreadManager
manager = ThreadManager()

with gr.Blocks() as block:
    start_btn = gr.Button("start")
    stop_btn = gr.Button("stop")

    # Start the foo function and save the thread reference
    start_btn.click(fn=manager.start_foo, inputs=None, outputs=None)
    # Stop the running thread
    stop_btn.click(fn=manager.stop_foo, inputs=None, outputs=None)

block.queue().launch()