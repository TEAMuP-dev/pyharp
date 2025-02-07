"""
Simple "fake cancel" example
"""
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


"""
Threading solution
"""
# import gradio as gr
# import time
# import threading
# class ThreadManager:
#     def __init__(self):
#         self.running_thread = None
#         self.should_stop = False

#     def counter(self):
#         for i in range(300):
#             if self.should_stop:
#                 print("Stopped!")
#                 break
#             print(i)
#             time.sleep(0.5)
#     def start_counter(self):
#         self.should_stop = False  # Reset the stop flag
#         self.running_thread = threading.Thread(target=self.counter)
#         self.running_thread.start()
#         return self.running_thread
#     def stop_counter(self):
#         self.should_stop = True
#         if self.running_thread and self.running_thread.is_alive():
#             self.running_thread.join(timeout=1)  # Wait for the thread to finish

# # Create an instance of ThreadManager
# manager = ThreadManager()
# with gr.Blocks() as block:
#     start_btn = gr.Button("start")
#     stop_btn = gr.Button("stop")
#     # Start the counter function and save the thread reference
#     start_btn.click(fn=manager.start_counter, inputs=None, outputs=None)
#     # Stop the running thread
#     stop_btn.click(fn=manager.stop_counter, inputs=None, outputs=None)
# block.queue().launch()

# """
# Multiprocessing solution
# """

# import gradio as gr
# import time
# import multiprocessing

# class ProcessManager:
#     def __init__(self):
#         self.process = None

#     def counter(self):
#         # Your long PyTorch inference code here
#         for i in range(300):
#             print(i)
#             time.sleep(0.5)

#     def start_counter(self):
#         self.process = multiprocessing.Process(target=self.counter)
#         self.process.start()

#     def stop_counter(self):
#         if self.process and self.process.is_alive():
#             self.process.terminate()
#             self.process.join()

# manager = ProcessManager()
# with gr.Blocks() as block:
#     start_btn = gr.Button("start")
#     stop_btn = gr.Button("stop")
#     # Start the counter function in a new process
#     start_btn.click(fn=manager.start_counter, inputs=None, outputs=None)
#     # Stop the running process
#     stop_btn.click(fn=manager.stop_counter, inputs=None, outputs=None)
# block.queue().launch()