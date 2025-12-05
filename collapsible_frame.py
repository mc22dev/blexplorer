import customtkinter
from typing import Any

class CollapsibleFrame(customtkinter.CTkFrame):
    """A custom tkinter frame that can be collapsed and expanded."""

    def __init__(self, master: Any, text: str = "") -> None:
        """
        Initializes the CollapsibleFrame.

        Args:
            master: The parent widget.
            text: The text to display on the collapse/expand button.
        """
        super().__init__(master)

        self.grid_columnconfigure(0, weight=1)
        self.collapsed = True

        self.button = customtkinter.CTkButton(self, text=text, command=self.toggle)
        self.button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.content_frame = customtkinter.CTkFrame(self, fg_color="transparent")

    def toggle(self) -> None:
        """Toggles the visibility of the content frame."""
        self.collapsed = not self.collapsed
        if self.collapsed:
            self.content_frame.grid_forget()
        else:
            self.content_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
