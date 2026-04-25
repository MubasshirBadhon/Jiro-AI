"""Always-on-top GUI Overlay for Jiro AI.

Dark-themed, transparent, minimizable overlay with:
- Chat display with scrolling
- Text input field
- Voice input button (MIC)
- Status indicator
- Minimize to floating bubble
"""

import logging
import queue
import threading
from typing import Callable, Optional

logger = logging.getLogger("jiro.ui.overlay")


class JiroOverlay:
    """Always-on-top GUI overlay."""

    def __init__(self, config: dict,
                 on_text: Optional[Callable] = None,
                 on_voice_start: Optional[Callable] = None,
                 on_voice_stop: Optional[Callable] = None):
        self._config = config
        self._on_text = on_text
        self._on_voice_start = on_voice_start
        self._on_voice_stop = on_voice_stop
        self._msg_queue: queue.Queue = queue.Queue()
        self._minimized = False
        self._recording = False
        self._root = None
        self._status_label = None

    def _build(self) -> None:
        import customtkinter as ctk

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        gui = self._config.get("gui", {})
        w, h = gui.get("width", 400), gui.get("height", 600)

        self._root = ctk.CTk()
        self._root.title("Jiro AI")
        self._root.geometry(f"{w}x{h}")
        self._root.attributes("-topmost", gui.get("always_on_top", True))
        self._root.attributes("-alpha", gui.get("opacity", 0.95))
        self._root.configure(fg_color="#1a1a2e")

        sw = self._root.winfo_screenwidth()
        pos = gui.get("position", "top-right")
        x = sw - w - 20 if "right" in pos else 20
        y = 20 if "top" in pos else self._root.winfo_screenheight() - h - 60
        self._root.geometry(f"+{x}+{y}")

        header = ctk.CTkFrame(self._root, fg_color="#16213e", height=50)
        header.pack(fill="x", padx=5, pady=5)
        header.pack_propagate(False)

        ctk.CTkLabel(header, text="JIRO AI",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color="#00d4ff").pack(side="left", padx=15, pady=10)

        self._status_label = ctk.CTkLabel(header, text="Online",
                                          font=ctk.CTkFont(size=11),
                                          text_color="#00ff88")
        self._status_label.pack(side="left", padx=5)

        ctk.CTkButton(header, text="_", width=30, height=30,
                      fg_color="transparent", hover_color="#333",
                      command=self._toggle_min).pack(side="right", padx=5)

        self._chat = ctk.CTkScrollableFrame(self._root, fg_color="#0f3460", corner_radius=10)
        self._chat.pack(fill="both", expand=True, padx=5, pady=5)

        self._add_msg("Jiro", "Hello! I'm Jiro AI, your personal assistant. How can I help?")

        inp = ctk.CTkFrame(self._root, fg_color="#1a1a2e")
        inp.pack(fill="x", padx=5, pady=5)

        self._text_input = ctk.CTkEntry(inp, placeholder_text="Type a message...",
                                        height=40, fg_color="#16213e",
                                        text_color="white", border_color="#00d4ff")
        self._text_input.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self._text_input.bind("<Return>", self._submit)

        self._mic_btn = ctk.CTkButton(inp, text="MIC", width=50, height=40,
                                      fg_color="#e94560", hover_color="#ff6b6b",
                                      command=self._toggle_mic)
        self._mic_btn.pack(side="right")

        ctk.CTkButton(inp, text="Send", width=60, height=40,
                      fg_color="#00d4ff", hover_color="#00a8cc",
                      command=lambda: self._submit(None)).pack(side="right", padx=5)

        self._root.after(100, self._process_queue)
        self._root.protocol("WM_DELETE_WINDOW", lambda: self._root.withdraw())

    def _add_msg(self, sender: str, text: str) -> None:
        try:
            import customtkinter as ctk
            is_user = sender.lower() == "you"
            frame = ctk.CTkFrame(self._chat,
                                 fg_color="#16213e" if is_user else "#533483",
                                 corner_radius=10)
            frame.pack(fill="x", padx=5, pady=2, anchor="e" if is_user else "w")

            ctk.CTkLabel(frame, text=sender,
                         font=ctk.CTkFont(size=10, weight="bold"),
                         text_color="#ff6b6b" if is_user else "#00d4ff"
                         ).pack(anchor="w", padx=10, pady=(5, 0))

            ctk.CTkLabel(frame, text=text, font=ctk.CTkFont(size=13),
                         text_color="white", wraplength=320, justify="left"
                         ).pack(anchor="w", padx=10, pady=(0, 5))
        except Exception as e:
            logger.error("GUI message error: %s", e)

    def display(self, sender: str, text: str) -> None:
        """Thread-safe message display."""
        self._msg_queue.put((sender, text))

    def _process_queue(self) -> None:
        try:
            while not self._msg_queue.empty():
                sender, text = self._msg_queue.get_nowait()
                self._add_msg(sender, text)
        except queue.Empty:
            pass
        if self._root:
            self._root.after(100, self._process_queue)

    def _submit(self, event) -> None:
        text = self._text_input.get().strip()
        if text:
            self._add_msg("You", text)
            self._text_input.delete(0, "end")
            if self._on_text:
                threading.Thread(target=self._run_cb, args=(self._on_text, text),
                                 daemon=True).start()

    def _toggle_mic(self) -> None:
        self._recording = not self._recording
        if self._recording:
            self._mic_btn.configure(fg_color="#00ff88", text="REC")
            if self._on_voice_start:
                threading.Thread(target=self._run_cb, args=(self._on_voice_start,),
                                 daemon=True).start()
        else:
            self._mic_btn.configure(fg_color="#e94560", text="MIC")
            if self._on_voice_stop:
                threading.Thread(target=self._run_cb, args=(self._on_voice_stop,),
                                 daemon=True).start()

    def _toggle_min(self) -> None:
        gui = self._config.get("gui", {})
        if self._minimized:
            self._root.geometry(f"{gui.get('width', 400)}x{gui.get('height', 600)}")
            self._chat.pack(fill="both", expand=True, padx=5, pady=5)
        else:
            self._root.geometry(f"{gui.get('minimized_width', 60)}x{gui.get('minimized_height', 60)}")
            self._chat.pack_forget()
        self._minimized = not self._minimized

    def set_status(self, text: str, color: str = "#00ff88") -> None:
        if self._status_label:
            self._status_label.configure(text=text, text_color=color)

    def _run_cb(self, cb, *args) -> None:
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(cb(*args))
        except Exception as e:
            logger.error("Callback error: %s", e)
        finally:
            loop.close()

    def run(self) -> None:
        self._build()
        self._root.mainloop()

    def run_threaded(self) -> threading.Thread:
        t = threading.Thread(target=self.run, daemon=True)
        t.start()
        return t

    def destroy(self) -> None:
        if self._root:
            self._root.destroy()
