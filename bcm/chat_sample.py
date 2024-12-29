import asyncio
import threading
import tkinter as tk
from tkinter import scrolledtext, VERTICAL
import ttkbootstrap as ttk
from pydantic_ai import Agent

# Initialize the agent with the desired model
agent = Agent('ollama:llama3.2', system_prompt='You are a helpful assistant.')

class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PydanticAI Chat with Streaming")
        self.message_history = []
        self.ai_response_labels = {}  # Dictionary to store AI response labels
        self.is_scrolling = False # Flag to indicate if scroll is in progress

        # Set up the GUI components
        self.setup_widgets()

    def setup_widgets(self):
        # Chat display area (using a Frame to hold messages)
        self.chat_frame = ttk.Frame(self.root)
        self.chat_frame.grid(row=0, column=0, padx=10, pady=10, columnspan=2, sticky="nsew")

        # Scrollbar for the chat display
        self.scrollbar = ttk.Scrollbar(self.chat_frame, orient=VERTICAL)
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        # Canvas to hold the chat messages
        self.chat_canvas = tk.Canvas(self.chat_frame, yscrollcommand=self.scrollbar.set)
        self.chat_canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.config(command=self.chat_canvas.yview)

        # Frame inside the canvas to hold the messages
        self.messages_frame = ttk.Frame(self.chat_canvas)
        self.chat_canvas.create_window((0, 0), window=self.messages_frame, anchor="nw", width=self.chat_canvas.winfo_width()) # Set initial width

        # Configure weights for resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.chat_frame.columnconfigure(0, weight=1)
        self.chat_frame.rowconfigure(0, weight=1)

        # Bind the canvas to adjust when the messages frame changes size
        self.messages_frame.bind("<Configure>", self.on_frame_configure)
        
        # Bind resize event to the canvas to adjust the width of the messages_frame
        self.chat_canvas.bind("<Configure>", self.on_canvas_configure)

        
        # Bind scroll event to update the flag
        self.chat_canvas.bind("<B1-Motion>", self.on_scroll_start)
        self.chat_canvas.bind("<ButtonRelease-1>", self.on_scroll_end)
        self.scrollbar.bind("<B1-Motion>", self.on_scroll_start)
        self.scrollbar.bind("<ButtonRelease-1>", self.on_scroll_end)

        # Entry widget for user input
        self.user_input = ttk.Entry(self.root, width=70)
        self.user_input.grid(row=1, column=0, padx=10, pady=10, sticky='ew')
        self.user_input.bind("<Return>", self.on_enter_pressed)

        # Send button
        self.send_button = ttk.Button(self.root, text="Send", command=self.on_send_clicked)
        self.send_button.grid(row=1, column=1, padx=10, pady=10)

    def on_scroll_start(self, event):
        self.is_scrolling = True

    def on_scroll_end(self, event):
        self.is_scrolling = False
        
    def on_frame_configure(self, event):
        # Update the scroll region of the canvas only if not scrolling
        if not self.is_scrolling:
            self.update_scroll_region()

    def on_canvas_configure(self, event):
        # Adjust the width of the messages_frame to match the canvas width
        self.chat_canvas.itemconfig(self.chat_canvas.create_window((0, 0), window=self.messages_frame, anchor="nw"), width=event.width)
        self.update_scroll_region()

    def update_scroll_region(self):
        self.root.update_idletasks()
        self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all"))

    def on_enter_pressed(self, event):
        self.on_send_clicked()

    def on_send_clicked(self):
        user_message = self.user_input.get().strip()
        if user_message:
            self.display_message("You", user_message)
            self.user_input.delete(0, tk.END)
            # Start a new thread to handle the AI response
            threading.Thread(target=self.handle_ai_response, args=(user_message,), daemon=True).start()

    def display_message(self, sender, message):
        if sender == "AI":
            # Create a new label for the AI response
            ai_label = ttk.Label(self.messages_frame, text=f"{sender}: ", wraplength=self.chat_canvas.winfo_width()-10, anchor="w", justify="left")
            ai_label.pack(fill="x", expand=True)
            self.ai_response_labels[len(self.message_history)] = ai_label  # Store the label with the message index

        else:
            # Display user messages normally
            message_label = ttk.Label(self.messages_frame, text=f"{sender}: {message}", wraplength=self.chat_canvas.winfo_width()-10, anchor="w", justify="left")
            message_label.pack(fill="x", expand=True)

        self.update_scroll_region()
        self.chat_canvas.yview_moveto(1.0)  # Scroll to the bottom

    def handle_ai_response(self, user_message):
        asyncio.run(self.fetch_and_display_response(user_message))

    async def fetch_and_display_response(self, user_message):
        async with agent.run_stream(user_message, message_history=self.message_history) as result:
            response_text = ""
            message_index = len(self.message_history)  # Get the index for this response
            self.display_message("AI", "")  # Create the initial label for the AI response
            async for message in result.stream_text(delta=True):
                response_text += message
                self.root.after(0, self.update_label, message_index, "AI", response_text)

            # Append new messages to the history after the full response is received
            self.message_history.extend(result.new_messages())

    def update_label(self, message_index, sender, message):
        if message_index in self.ai_response_labels:
            label = self.ai_response_labels[message_index]
            label.config(text=f"{sender}: {message}")
            self.update_scroll_region()
            self.chat_canvas.yview_moveto(1.0)  # Scroll to the bottom


if __name__ == '__main__':
    root = ttk.Window(themename="superhero")
    app = ChatApp(root)
    root.mainloop()