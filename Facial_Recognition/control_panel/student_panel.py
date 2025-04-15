class StudentControlPanel(ctk.CTk):
    def __init__(self, user_info, cnx, cursor, language):
        super().__init__()
        self.user_info = user_info
        self.cnx = cnx
        self.cursor = cursor
        self.language = language
        self.trans = translations[self.language]
        self.title(self.trans["control_title"] + " - Student")
        self.geometry("1200x800")
        try:
            self.state("zoomed")
        except Exception:
            pass
        self.resizable(True, True)
        self.create_widgets()
        self.fetch_data()

    def create_widgets(self):
        greeting = f"{self.trans['welcome']} {self.user_info[1]} ({self.user_info[2]})"
        self.label_greeting = ctk.CTkLabel(self, text=greeting, font=("Arial", 24))
        self.label_greeting.pack(pady=20)

        # Table of Students
        self.table_frame = ctk.CTkFrame(self)
        self.table_frame.pack(pady=10, padx=40, fill="both", expand=True)
        columns = [self.trans["col_index"], self.trans["col_name"], "Lớp", self.trans["col_attendance"]]
        self.custom_table = CustomTable(self.table_frame, columns=columns, corner_radius=8)
        self.custom_table.pack(fill="both", expand=True)

        # Search Bar
        self.search_frame = ctk.CTkFrame(self)
        self.search_frame.pack(pady=10)
        self.search_entry = ctk.CTkEntry(self.search_frame, placeholder_text=self.trans["search"])
        self.search_entry.pack(side="left", padx=10)
        self.search_button = ctk.CTkButton(self.search_frame, text=self.trans["search"], command=self.search_student)
        self.search_button.pack(side="left", padx=10)

        # Bottom Buttons
        self.frame_buttons = ctk.CTkFrame(self)
        self.frame_buttons.pack(pady=10, padx=40, fill="x")
        self.frame_buttons.grid_columnconfigure(0, weight=1)
        self.frame_buttons.grid_columnconfigure(1, weight=1)
        self.frame_buttons.grid_columnconfigure(2, weight=1)
        self.button_export = ctk.CTkButton(
            self.frame_buttons,
            text=self.trans["export"],
            command=lambda: export_students_list(self.cursor, self.language)
        )
        self.button_export.grid(row=0, column=0, padx=20, pady=10)
        self.button_logout = ctk.CTkButton(
            self.frame_buttons,
            text=self.trans["logout"],
            command=self.logout
        )
        self.button_logout.grid(row=0, column=1, padx=20, pady=10)
        self.button_quit = ctk.CTkButton(
            self.frame_buttons,
            text=self.trans["quit"],
            command=self.quit_app
        )
        self.button_quit.grid(row=0, column=2, padx=20, pady=10) 