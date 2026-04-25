"""Always-on-top GUI Overlay for Jiro AI.

Provides a compact, always-on-top window with:
- Text input field
- Voice input button
- Chat display
- Minimize to floating bubble
"""

import asyncio
import logging
import threading
import queue
from typing import Callable, Optional

logger = logging.getLogger("jiro.gui")


class JiroGUI:
    """Always-on-top GUI for Jiro AI with text and voice input."""

    def __init__(self, config_manager, on_text_input: Optional[Callable] = None,
                 on_voice_start: Optional[Callable] = None,
                 on_voice_stop: Optional[Callable] = None):
        self.config = config_manager
        self._on_text_input = on_text_input
        self._on_voice_start = on_voice_start
        self._on_voice_stop = on_voice_stop
        self._message_queue: queue.Queue = queue.Queue()
        self._is_minimized = False
        self._is_recording = False
        self._root = None
        self._chat_display = None

    def _build_ui(self) -> None:
        """Build the GUI using customtkinter."""
        import customtkinter as ctk

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        width = self.config.get("gui.width", 400)
        height = self.config.get("gui.height", 600)

        self._root = ctk.CTk()
        self._root.title("Jiro AI")
        self._root.geometry(f"{width}x{height}")
        self._root.attributes("-topmost", self.config.get("gui.always_on_top", True))
        self._root.attributes("-alpha", self.config.get("gui.opacity", 0.95))

        position = self.config.get("gui.position", "top-right")
        screen_w = self._root.winfo_screenwidth()
        screen_h = self._root.winfo_screenheight()
        if position == "top-right":
            x = screen_w - width - 20
            y = 20
        elif position == "top-left":
            x, y = 20, 20
        elif position == "bottom-right":
            x = screen_w - width - 20
            y = screen_h - height - 60
        else:
            x = screen_w - width - 20
            y = 20
        self._root.geometry(f"+{x}+{y}")

        self._root.configure(fg_color="#1a1a2e")

        header = ctk.CTkFrame(self._root, fg_color="#16213e", height=50)
        header.pack(fill="x", padx=5, pady=5)
        header.pack_propagate(False)

        title_label = ctk.CTkLabel(
            header, text="JIRO AI",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#00d4ff",
        )
        title_label.pack(side="left", padx=15, pady=10)

        status_label = ctk.CTkLabel(
            header, text="Online",
            font=ctk.CTkFont(size=11),
            text_color="#00ff88",
        )
        status_label.pack(side="left", padx=5)
        self._status_label = status_label

        minimize_btn = ctk.CTkButton(
            header, text="_", width=30, height=30,
            fg_color="transparent", hover_color="#333",
            command=self._toggle_minimize,
        )
        minimize_btn.pack(side="right", padx=5)

        self._chat_frame = ctk.CTkScrollableFrame(
            self._root, fg_color="#0f3460",
            corner_radius=10,
        )
        self._chat_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self._add_message("Jiro", "Hello! I'm Jiro AI, your personal assistant. How can I help you today?")

        input_frame = ctk.CTkFrame(self._root, fg_color="#1a1a2e")
        input_frame.pack(fill="x", padx=5, pady=5)

        self._text_input = ctk.CTkEntry(
            input_frame,
            placeholder_text="Type a message...",
            height=40,
            fg_color="#16213e",
            text_color="white",
            border_color="#00d4ff",
        )
        self._text_input.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self._text_input.bind("<Return>", self._handle_text_submit)

        self._voice_btn = ctk.CTkButton(
            input_frame, text="MIC",
            width=50, height=40,
            fg_color="#e94560",
            hover_color="#ff6b6b",
            command=self._toggle_voice,
        )
        self._voice_btn.pack(side="right")

        send_btn = ctk.CTkButton(
            input_frame, text="Send",
            width=60, height=40,
            fg_color="#00d4ff",
            hover_color="#00a8cc",
            command=lambda: self._handle_text_submit(None),
        )
        send_btn.pack(side="right", padx=5)

        self._root.after(100, self._process_message_queue)

        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _add_message(self, sender: str, text: str) -> None:
        """Add a message to the chat display."""
        try:
            import customtkinter as ctk

            is_user = sender.lower() == "you"
            fg_color = "#16213e" if is_user else "#533483"
            anchor = "e" if is_user else "w"

            msg_frame = ctk.CTkFrame(self._chat_frame, fg_color=fg_color, corner_radius=10)
            msg_frame.pack(fill="x", padx=5, pady=2, anchor=anchor)

            sender_label = ctk.CTkLabel(
                msg_frame, text=sender,
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color="#00d4ff" if not is_user else "#ff6b6b",
            )
            sender_label.pack(anchor="w", padx=10, pady=(5, 0))

            msg_label = ctk.CTkLabel(
                msg_frame, text=text,
                font=ctk.CTkFont(size=13),
                text_color="white",
                wraplength=320,
                justify="left",
            )
            msg_label.pack(anchor="w", padx=10, pady=(0, 5))

        except Exception as e:
            logger.error("Failed to add message to GUI: %s", e)

    def display_message(self, sender: str, text: str) -> None:
        """Thread-safe method to display a message."""
        self._message_queue.put((sender, text))

    def _process_message_queue(self) -> None:
        """Process pending messages from the queue."""
        try:
            while not self._message_queue.empty():
                sender, text = self._message_queue.get_nowait()
                self._add_message(sender, text)
        except queue.Empty:
            pass

        if self._root:
            self._root.after(100, self._process_message_queue)

    def _handle_text_submit(self, event) -> None:
        """Handle text input submission."""
        text = self._text_input.get().strip()
        if text:
            self._add_message("You", text)
            self._text_input.delete(0, "end")
            if self._on_text_input:
                threading.Thread(
                    target=self._run_async_callback,
                    args=(self._on_text_input, text),
                    daemon=True,
                ).start()

    def _toggle_voice(self) -> None:
        """Toggle voice recording."""
        self._is_recording = not self._is_recording
        if self._is_recording:
            self._voice_btn.configure(fg_color="#00ff88", text="REC")
            if self._on_voice_start:
                threading.Thread(
                    target=self._run_async_callback,
                    args=(self._on_voice_start,),
                    daemon=True,
                ).start()
        else:
            self._voice_btn.configure(fg_color="#e94560", text="MIC")
            if self._on_voice_stop:
                threading.Thread(
                    target=self._run_async_callback,
                    args=(self._on_voice_stop,),
                    daemon=True,
                ).start()

    def _toggle_minimize(self) -> None:
        """Toggle between full and minimized views."""
        if self._is_minimized:
            min_w = self.config.get("gui.width", 400)
            min_h = self.config.get("gui.height", 600)
            self._root.geometry(f"{min_w}x{min_h}")
            self._chat_frame.pack(fill="both", expand=True, padx=5, pady=5)
        else:
            mw = self.config.get("gui.minimized_width", 60)
            mh = self.config.get("gui.minimized_height", 60)
            self._root.geometry(f"{mw}x{mh}")
            self._chat_frame.pack_forget()
        self._is_minimized = not self._is_minimized

    def set_status(self, status: str, color: str = "#00ff88") -> None:
        """Update the status indicator."""
        if self._status_label:
            self._status_label.configure(text=status, text_color=color)

    def _run_async_callback(self, callback, *args) -> None:
        """Run an async callback from a thread."""
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(callback(*args))
        except Exception as e:
            logger.error("Callback error: %s", e)
        finally:
            loop.close()

    def _on_close(self) -> None:
        """Handle window close."""
        self._root.withdraw()
        self._is_minimized = True

    def run(self) -> None:
        """Start the GUI main loop (blocks)."""
        self._build_ui()
        self._root.mainloop()

    def run_in_thread(self) -> threading.Thread:
        """Start the GUI in a separate thread."""
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        return thread

    def destroy(self) -> None:
        """Destroy the GUI window."""
        if self._root:
            self._root.destroy()
