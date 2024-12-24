import ttkbootstrap as tb
from ttkbootstrap.constants import *
import asyncio
import tkinter as tk

class ProgressWindow:
    def __init__(self, parent):
        """Create a borderless window with centered progress bar."""
        self.parent = parent
        self.window = tb.Toplevel(parent)
        self.window.overrideredirect(True)  # Remove window decorations
        self.window.attributes('-topmost', True)  # Keep on top
        
        # Set size and center the window
        width = 300
        height = 50
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.window.geometry(f'{width}x{height}+{x}+{y}')
        
        # Configure window appearance
        self.window.configure(highlightbackground='white', highlightthickness=1)
        
        # Create progress bar
        self.progress_bar = tb.Progressbar(
            self.window,
            mode='indeterminate',
            bootstyle='info-striped',
            length=250
        )
        self.progress_bar.place(relx=0.5, rely=0.5, anchor='center')
        
        # Initialize animation state
        self._animation_id = None
        self.is_running = False

    def start(self):
        """Show window and start progress animation."""
        self.window.deiconify()
        self.is_running = True
        self.progress_bar.configure(mode='indeterminate')
        self.progress_bar.start(10)  # Faster animation
        self.window.update()

    def stop(self):
        """Stop progress animation and hide window."""
        self.is_running = False
        if self._animation_id:
            self.window.after_cancel(self._animation_id)
            self._animation_id = None
        self.progress_bar.stop()
        self.window.withdraw()
        self.window.update()

    async def run_with_progress(self, coro):
        """Run a coroutine while showing the progress bar."""
        self.start()
        try:
            # Process tkinter events while running coroutine
            task = asyncio.create_task(coro)
            while not task.done():
                self.parent.update()
                await asyncio.sleep(0.01)
            return await task
        finally:
            self.stop()
