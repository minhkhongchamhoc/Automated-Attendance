import customtkinter as ctk
from tkinter import messagebox
import datetime
from translator import translations
from control_panel.components import CustomTable
from DatabaseHooking import export_students_list, calculate_attendance_status
from .components import CutoffTimeWindowGMT

def open_cutoff_ui(self):
    CutoffTimeWindowGMT(self, self.cnx, self.cursor, self.language)

class ModeratorControlPanel(ctk.CTk):
    def __init__(self, user_info, cnx, cursor, language):
        super().__init__()
        self.user_info = user_info
        self.cnx = cnx
        self.cursor = cursor
        self.language = language
        self.trans = translations[self.language]
        self.title(self.trans["control_title"] + " - Moderator")
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

        # Tools Bar
        self.frame_controls = ctk.CTkFrame(self)
        self.frame_controls.pack(pady=10, padx=40, fill="x")
        self.button_add = ctk.CTkButton(
            self.frame_controls,
            text=self.trans["add_student"],
            command=lambda: add_student_ui(self, self.cnx, self.cursor, self.language, on_success_callback=self.fetch_data)
        )
        self.button_add.grid(row=0, column=0, padx=10, pady=10)
        self.button_delete = ctk.CTkButton(
            self.frame_controls,
            text=self.trans["delete_student"],
            command=self.delete_student
        )
        self.button_delete.grid(row=0, column=1, padx=10, pady=10)
        self.button_edit = ctk.CTkButton(
            self.frame_controls,
            text=self.trans["edit_student"],
            command=self.edit_student
        )
        self.button_edit.grid(row=0, column=2, padx=10, pady=10)
        self.button_batch_add = ctk.CTkButton(
            self.frame_controls,
            text=self.trans.get("batch_add", "Thêm hàng loạt"),
            command=lambda: add_students_batch_ui(self, self.cnx, self.cursor, self.language, on_success_callback=self.fetch_data)
        )
        self.button_batch_add.grid(row=0, column=3, padx=10, pady=10)
        self.button_cutoff = ctk.CTkButton(
            self.frame_controls,
            text=self.trans["set_cutoff"],
            command=lambda: open_cutoff_ui(self)
        )
        self.button_cutoff.grid(row=0, column=4, padx=10, pady=10)

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

    def fetch_data(self):
        self.load_all_students()

    def load_all_students(self):
        query = "SELECT id, HoVaTen, Lop, DiemDanhStatus, ThoiGianDiemDanh FROM Students ORDER BY id"
        try:
            self.cursor.execute(query)
            rows = self.cursor.fetchall()
        except Exception as e:
            messagebox.showerror("Error", f"Error fetching data:\n{e}")
            return

        self.custom_table.clear_rows()
        if not rows:
            self.custom_table.pack_forget()
            self.watermark_label = ctk.CTkLabel(
                self.table_frame, text=self.trans["no_data"],
                font=("Arial", 48), fg_color="transparent"
            )
            self.watermark_label.place(relx=0.5, rely=0.5, anchor="center")
        else:
            if hasattr(self, "watermark_label"):
                self.watermark_label.destroy()
            self.custom_table.pack(fill="both", expand=True)
            for idx, row in enumerate(rows, start=1):
                if row[4] is not None and isinstance(row[4], datetime.datetime):
                    attendance = calculate_attendance_status(row[4], self.language)
                else:
                    attendance = '✖'
                self.custom_table.add_row((idx, row[1], row[2], attendance))

    def search_student(self):
        search_term = self.search_entry.get().strip().lower()
        if not search_term:
            self.load_all_students()
            return

        query = "SELECT id, HoVaTen, Lop, DiemDanhStatus, ThoiGianDiemDanh FROM Students WHERE LOWER(HoVaTen) LIKE %s ORDER BY id"
        try:
            self.cursor.execute(query, (f"%{search_term}%",))
            rows = self.cursor.fetchall()
        except Exception as e:
            messagebox.showerror("Error", f"Error searching data:\n{e}")
            return

        self.custom_table.clear_rows()
        if not rows:
            self.custom_table.pack_forget()
            self.watermark_label = ctk.CTkLabel(
                self.table_frame, text=self.trans["no_data"],
                font=("Arial", 48), fg_color="transparent"
            )
            self.watermark_label.place(relx=0.5, rely=0.5, anchor="center")
        else:
            if hasattr(self, "watermark_label"):
                self.watermark_label.destroy()
            self.custom_table.pack(fill="both", expand=True)
            for idx, row in enumerate(rows, start=1):
                if row[4] is not None and isinstance(row[4], datetime.datetime):
                    attendance = calculate_attendance_status(row[4], self.language)
                else:
                    attendance = '✖'
                self.custom_table.add_row((idx, row[1], row[2], attendance))

    def logout(self):
        self.destroy()

    def quit_app(self):
        self.quit()

if __name__ == "__main__":
    user_info = (1, "Moderator", "moderator")
    cnx, cursor = None, None
    language = "Tiếng Việt"
    app = ModeratorControlPanel(user_info, cnx, cursor, language)
    app.mainloop()
