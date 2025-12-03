import customtkinter

class CollapsibleFrame(customtkinter.CTkFrame):
    def __init__(self, master, text=""):
        super().__init__(master)

        self.grid_columnconfigure(0, weight=1)
        self.collapsed = True

        self.button = customtkinter.CTkButton(self, text=text, command=self.toggle)
        self.button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.content_frame = customtkinter.CTkFrame(self, fg_color="transparent")

    def toggle(self):
        self.collapsed = not self.collapsed
        if self.collapsed:
            self.content_frame.grid_forget()
        else:
            self.content_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
