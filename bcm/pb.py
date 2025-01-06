import ttkbootstrap as tb
import asyncio
from typing import Any, Coroutine
import threading


class ProgressWindow:
    def __init__(self, parent):
        """Create a borderless window with centered progress bar."""
        self.parent = parent
        self.window = tb.Toplevel(parent)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)

        # Set size and center the window
        width = 300
        height = 50
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.window.geometry(f"{width}x{height}+{x}+{y}")

        self.window.configure(highlightbackground="black", highlightthickness=1)

        self.progress_bar = tb.Progressbar(
            self.window, mode="indeterminate", bootstyle="info-striped", length=250
        )
        self.progress_bar.place(relx=0.5, rely=0.5, anchor="center")

        # Add flag to control updates
        self.running = False

    def run_with_progress(self, coro: Coroutine[Any, Any, Any]) -> Any:
        """Run a coroutine while showing the progress window."""
        result = None
        error = None
        event = threading.Event()

        async def wrapped_coro():
            nonlocal result, error
            try:
                result = await coro
            except Exception as e:
                error = e
            finally:
                event.set()

        self.window.deiconify()
        self.progress_bar.start(10)
        self.running = True

        # Schedule the coroutine in the main event loop
        asyncio.run_coroutine_threadsafe(wrapped_coro(), asyncio.get_event_loop())

        # Update windows while waiting
        while not event.is_set():
            if not self.running:
                break
            try:
                self.window.update()
                self.parent.update()
            except:
                self.running = False
                break

        self.progress_bar.stop()
        self.window.withdraw()

        if error:
            raise error
        return result

    def close(self):
        """Clean up resources."""
        self.running = False
        try:
            self.window.destroy()
        except:
            pass
