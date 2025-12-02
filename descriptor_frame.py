import customtkinter

class DescriptorFrame(customtkinter.CTkFrame):
    def __init__(self, master, descriptor, read_callback, write_callback):
        super().__init__(master)
        self.descriptor = descriptor
        self.read_callback = read_callback
        self.write_callback = write_callback

        self.grid_columnconfigure(1, weight=1)

        self.uuid_label = customtkinter.CTkLabel(self, text=str(descriptor.uuid), wraplength=200, justify="left")
        self.uuid_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.read_button = customtkinter.CTkButton(self, text="Read", command=self.read_pressed, width=50)
        self.read_button.grid(row=0, column=2, padx=5, pady=5, sticky="e")

        self.read_value_entry = customtkinter.CTkEntry(self)
        self.read_value_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.write_button = customtkinter.CTkButton(self, text="Write", command=self.write_pressed, width=50)
        self.write_button.grid(row=1, column=2, padx=5, pady=5, sticky="e")

        self.write_entry = customtkinter.CTkEntry(self)
        self.write_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

    def read_pressed(self):
        self.read_callback(self.descriptor, self)

    def write_pressed(self):
        self.write_callback(self.descriptor, self)

    def update_value(self, raw_bytes):
        self.read_value_entry.delete(0, "end")
        self.read_value_entry.insert(0, raw_bytes.hex())
