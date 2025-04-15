import tkinter as tk
from tkinter import ttk, messagebox
import sys, json, os, base64, threading
from DatabaseHooking import connect_db, create_tables, verify_user, create_default_users
from translator import translations
import FacialRecognition
import ctypes

# Tắt DPI Awareness
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(0)
except Exception:
    pass

def load_config():
    config_file = "config.json"
    default = {
        "theme": "Light",
        "language": "Tiếng Việt",
        "db_host": "",
        "db_username": "",
        "db_password": "",
        "camera_type": "Webcam mặc định",
        "camera_url": "",
        "camera_types": ["Webcam mặc định", "Camera IP LAN", "Camera WiFi"],
        "camera_simple_mode": False,
        "camera_protocol": "RTSP",
        "camera_user": "",
        "camera_pass": "",
        "camera_ip": "",
        "camera_port": ""
    }
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            if config.get("db_username"):
                config["db_username"] = base64.b64decode(config["db_username"].encode()).decode()
            if config.get("db_password"):
                config["db_password"] = base64.b64decode(config["db_password"].encode()).decode()
            if "camera_types" not in config:
                config["camera_types"] = default["camera_types"]
            for key in default:
                if key not in config:
                    config[key] = default[key]
            return config
        except Exception:
            return default
    else:
        return default

def save_config(theme, language, db_host, db_username, db_password,
                camera_type, camera_url, camera_types,
                camera_simple_mode=False, camera_protocol="RTSP",
                camera_user="", camera_pass="", camera_ip="", camera_port=""):
    config_file = "config.json"
    try:
        enc_username = base64.b64encode(db_username.encode()).decode() if db_username else ""
        enc_password = base64.b64encode(db_password.encode()).decode() if db_password else ""
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump({
                "theme": theme,
                "language": language,
                "db_host": db_host,
                "db_username": enc_username,
                "db_password": enc_password,
                "camera_type": camera_type,
                "camera_url": camera_url,
                "camera_types": camera_types,
                "camera_simple_mode": camera_simple_mode,
                "camera_protocol": camera_protocol,
                "camera_user": camera_user,
                "camera_pass": camera_pass,
                "camera_ip": camera_ip,
                "camera_port": camera_port
            }, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print("Error saving config:", e)

config = load_config()

class CameraConfigWindow(tk.Toplevel):
    def __init__(self, parent, current_camera_types):
        super().__init__(parent)
        self.title("Chỉnh sửa cấu hình Camera")
        self.geometry("400x300")
        self.parent = parent
        self.textbox = tk.Text(self, width=40, height=10)
        self.textbox.pack(pady=10)
        initial_text = "\n".join(current_camera_types)
        self.textbox.insert("1.0", initial_text)
        self.button_frame = ttk.Frame(self)
        self.button_frame.pack(pady=10)
        self.save_button = ttk.Button(self.button_frame, text="Lưu", command=self.save)
        self.save_button.grid(row=0, column=0, padx=10)
        self.cancel_button = ttk.Button(self.button_frame, text="Hủy", command=self.destroy)
        self.cancel_button.grid(row=0, column=1, padx=10)

    def save(self):
        content = self.textbox.get("1.0", "end").strip()
        new_camera_types = [line.strip() for line in content.splitlines() if line.strip()]
        if not new_camera_types:
            messagebox.showerror("Lỗi", "Danh sách loại kết nối không được để trống.")
            return
        self.parent.camera_types = new_camera_types
        self.parent.combo_camera_type.configure(values=new_camera_types)
        if self.parent.combo_camera_type.get() not in new_camera_types:
            self.parent.combo_camera_type.set(new_camera_types[0])
        self.destroy()

class MySQLLoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.language = config.get("language", "Tiếng Việt")
        self.trans = translations[self.language]
        self.title(self.trans["mysql_title"])
        self.geometry("800x600")
        self.resizable(True, True)
        self.camera_types = config.get("camera_types", ["Webcam mặc định", "Camera IP LAN", "Camera WiFi"])
        self.simple_mode = config.get("camera_simple_mode", False)
        self.selected_protocol = config.get("camera_protocol", "RTSP")
        self.camera_user = config.get("camera_user", "")
        self.camera_pass = config.get("camera_pass", "")
        self.camera_ip = config.get("camera_ip", "")
        self.camera_port = config.get("camera_port", "")
        self.create_widgets()
        if config.get("db_host"):
            self.entry_db_host.insert(0, config["db_host"])
        if config.get("db_username"):
            self.entry_db_username.insert(0, config["db_username"])
        if config.get("db_password"):
            self.entry_db_password.insert(0, config["db_password"])
        if config.get("camera_type"):
            self.combo_camera_type.set(config["camera_type"])
        if config.get("camera_url"):
            self.entry_camera_url.insert(0, config["camera_url"])
        if self.combo_camera_type.get() in ["Webcam mặc định", "Default Webcam"]:
            self.entry_camera_url.configure(state="disabled")
        if self.simple_mode:
            self.switch_simple_mode.select()
            self.show_simple_mode()
        else:
            self.hide_simple_mode()

    def create_widgets(self):
        self.label_title = ttk.Label(self, text=self.trans["mysql_label"], font=("Arial", 24))
        self.label_title.pack(pady=20)
        self.frame_form = ttk.Frame(self)
        self.frame_form.pack(pady=10, padx=40, fill="both", expand=True)
        self.label_db_host = ttk.Label(self.frame_form, text=self.trans["db_host"])
        self.label_db_host.grid(row=0, column=0, padx=10, pady=10, sticky="e")
        self.entry_db_host = ttk.Entry(self.frame_form)
        self.entry_db_host.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        self.label_db_username = ttk.Label(self.frame_form, text=self.trans["db_username"])
        self.label_db_username.grid(row=1, column=0, padx=10, pady=10, sticky="e")
        self.entry_db_username = ttk.Entry(self.frame_form)
        self.entry_db_username.grid(row=1, column=1, padx=10, pady=10, sticky="w")
        self.label_db_password = ttk.Label(self.frame_form, text=self.trans["db_password"])
        self.label_db_password.grid(row=2, column=0, padx=10, pady=10, sticky="e")
        self.entry_db_password = ttk.Entry(self.frame_form, show="*")
        self.entry_db_password.grid(row=2, column=1, padx=10, pady=10, sticky="w")
        self.label_language = ttk.Label(self.frame_form, text=self.trans["language"])
        self.label_language.grid(row=3, column=0, padx=10, pady=10, sticky="e")
        self.combo_language = ttk.Combobox(self.frame_form, values=["Tiếng Việt", "English"], state="readonly")
        self.combo_language.set(self.language)
        self.combo_language.grid(row=3, column=1, padx=10, pady=10, sticky="w")
        self.checkbox_remember = ttk.Checkbutton(self.frame_form, text=self.trans["remember"])
        self.checkbox_remember.grid(row=4, column=1, padx=10, pady=10, sticky="w")
        self.remember_var = tk.BooleanVar()
        self.checkbox_remember.configure(variable=self.remember_var)
        self.frame_camera = ttk.Frame(self)
        self.frame_camera.pack(pady=10, padx=40, fill="both", expand=True)
        self.label_camera_header = ttk.Label(self.frame_camera, text=self.trans["camera_header"], font=("Arial", 20, "bold"))
        self.label_camera_header.grid(row=0, column=0, columnspan=3, pady=10)
        self.label_camera_type = ttk.Label(self.frame_camera, text=self.trans["camera_type_label"])
        self.label_camera_type.grid(row=1, column=0, padx=10, pady=10, sticky="e")
        self.combo_camera_type = ttk.Combobox(self.frame_camera, values=self.camera_types, state="readonly")
        self.combo_camera_type.grid(row=1, column=1, padx=10, pady=10, sticky="w")
        self.button_camera_config = ttk.Button(self.frame_camera, text="⚙️", width=3, command=self.open_camera_config)
        self.button_camera_config.grid(row=1, column=2, padx=10, pady=10)
        self.label_camera_url = ttk.Label(self.frame_camera, text=self.trans["camera_url_label"])
        self.label_camera_url.grid(row=2, column=0, padx=10, pady=10, sticky="e")
        self.entry_camera_url = ttk.Entry(self.frame_camera)
        self.entry_camera_url.grid(row=2, column=1, padx=10, pady=10, sticky="w")
        self.switch_simple_mode = ttk.Checkbutton(self.frame_camera, text=self.trans["simple_mode"], command=self.toggle_simple_mode)
        self.switch_simple_mode.grid(row=3, column=0, padx=10, pady=10, sticky="w")
        self.frame_simple = ttk.Frame(self.frame_camera)
        self.frame_simple.grid(row=4, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")
        self.label_connection_mode = ttk.Label(self.frame_simple, text=self.trans["connection_mode"])
        self.label_connection_mode.grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.protocol_options = ["RTSP", "HTTP", "HTTPS", "ONVIF", "RTP", "HLS", "WebRTC"]
        self.optionmenu_protocol = ttk.Combobox(self.frame_simple, values=self.protocol_options, state="readonly")
        self.optionmenu_protocol.set(self.selected_protocol)
        self.optionmenu_protocol.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.label_camera_user = ttk.Label(self.frame_simple, text=self.trans["camera_username_label"])
        self.label_camera_user.grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.entry_camera_user = ttk.Entry(self.frame_simple)
        self.entry_camera_user.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        self.label_camera_pass = ttk.Label(self.frame_simple, text=self.trans["camera_password_label"])
        self.label_camera_pass.grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.entry_camera_pass = ttk.Entry(self.frame_simple, show="*")
        self.entry_camera_pass.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        self.label_camera_ip = ttk.Label(self.frame_simple, text=self.trans["camera_ip_label"])
        self.label_camera_ip.grid(row=3, column=0, padx=5, pady=5, sticky="e")
        self.entry_camera_ip = ttk.Entry(self.frame_simple)
        self.entry_camera_ip.grid(row=3, column=1, padx=5, pady=5, sticky="w")
        self.label_camera_port = ttk.Label(self.frame_simple, text=self.trans["camera_port_label"])
        self.label_camera_port.grid(row=4, column=0, padx=5, pady=5, sticky="e")
        self.entry_camera_port = ttk.Entry(self.frame_simple)
        self.entry_camera_port.grid(row=4, column=1, padx=5, pady=5, sticky="w")
        self.button_generate_link = ttk.Button(self.frame_simple, text=self.trans["generate_link"], command=self.generate_camera_url)
        self.button_generate_link.grid(row=5, column=0, columnspan=2, padx=5, pady=10)
        self.entry_camera_user.insert(0, self.camera_user)
        self.entry_camera_pass.insert(0, self.camera_pass)
        self.entry_camera_ip.insert(0, self.camera_ip)
        self.entry_camera_port.insert(0, self.camera_port)
        self.frame_buttons = ttk.Frame(self)
        self.frame_buttons.pack(pady=10, padx=40, fill="x")
        self.frame_buttons.grid_columnconfigure(0, weight=1)
        self.frame_buttons.grid_columnconfigure(1, weight=1)
        self.button_login = ttk.Button(self.frame_buttons, text=self.trans["login"], command=self.handle_login)
        self.button_login.grid(row=0, column=0, padx=20, pady=10)
        self.button_exit = ttk.Button(self.frame_buttons, text=self.trans["exit"], command=self.exit_app)
        self.button_exit.grid(row=0, column=1, padx=20, pady=10)

    def open_camera_config(self):
        CameraConfigWindow(self, self.camera_types)

    def on_camera_type_change(self, event):
        if self.combo_camera_type.get() in ["Webcam mặc định", "Default Webcam"]:
            self.entry_camera_url.delete(0, "end")
            self.entry_camera_url.configure(state="disabled")
        else:
            self.entry_camera_url.configure(state="normal")

    def toggle_simple_mode(self):
        self.simple_mode = not self.simple_mode
        if self.simple_mode:
            self.show_simple_mode()
        else:
            self.hide_simple_mode()

    def show_simple_mode(self):
        self.frame_simple.grid()

    def hide_simple_mode(self):
        self.frame_simple.grid_remove()

    def generate_camera_url(self):
        protocol = self.optionmenu_protocol.get().strip()
        user = self.entry_camera_user.get().strip()
        pwd = self.entry_camera_pass.get().strip()
        ip = self.entry_camera_ip.get().strip()
        port = self.entry_camera_port.get().strip()
        link = ""
        if protocol == "RTSP":
            link = f"rtsp://{user}:{pwd}@{ip}:{port}/stream"
        elif protocol == "HTTP":
            link = f"http://{user}:{pwd}@{ip}:{port}/"
        elif protocol == "HTTPS":
            link = f"https://{user}:{pwd}@{ip}:{port}/"
        elif protocol == "ONVIF":
            link = f"http://{user}:{pwd}@{ip}:{port}/onvif"
        elif protocol == "RTP":
            link = f"rtp://{ip}:{port}"
        elif protocol == "HLS":
            link = f"http://{ip}:{port}/hls/stream.m3u8"
        elif protocol == "WebRTC":
            link = "webrtc://..."
        self.entry_camera_url.configure(state="normal")
        self.entry_camera_url.delete(0, "end")
        self.entry_camera_url.insert(0, link)

    def change_language(self, event):
        self.language = self.combo_language.get()
        self.trans = translations[self.language]
        self.title(self.trans["mysql_title"])
        self.label_title.configure(text=self.trans["mysql_label"])
        self.label_db_host.configure(text=self.trans["db_host"])
        self.label_db_username.configure(text=self.trans["db_username"])
        self.label_db_password.configure(text=self.trans["db_password"])
        self.label_language.configure(text=self.trans["language"])
        self.button_login.configure(text=self.trans["login"])
        self.button_exit.configure(text=self.trans["exit"])
        self.label_camera_header.configure(text=self.trans["camera_header"])
        self.label_camera_type.configure(text=self.trans["camera_type_label"])
        self.label_camera_url.configure(text=self.trans["camera_url_label"])
        self.switch_simple_mode.configure(text=self.trans["simple_mode"])
        self.label_connection_mode.configure(text=self.trans["connection_mode"])
        self.label_camera_user.configure(text=self.trans["camera_username_label"])
        self.label_camera_pass.configure(text=self.trans["camera_password_label"])
        self.label_camera_ip.configure(text=self.trans["camera_ip_label"])
        self.label_camera_port.configure(text=self.trans["camera_port_label"])
        self.button_generate_link.configure(text=self.trans["generate_link"])
        self.combo_camera_type.configure(values=self.camera_types)
        if self.combo_camera_type.get() not in self.camera_types:
            self.combo_camera_type.set(self.camera_types[0])
        self.on_camera_type_change(None)

    def handle_login(self):
        db_host = self.entry_db_host.get().strip()
        db_username = self.entry_db_username.get().strip()
        db_password = self.entry_db_password.get().strip()
        language = self.language
        if not db_username or not db_password:
            if self.language == "Tiếng Việt":
                messagebox.showerror("Lỗi", "❌ Vui lòng nhập tên đăng nhập và mật khẩu CSDL.")
            else:
                messagebox.showerror("Error", "❌ Please enter database username and password.")
            return
        cnx, cursor = connect_db(db_username, db_password, db_host)
        if cnx is None:
            if self.language == "Tiếng Việt":
                messagebox.showerror("Lỗi CSDL",
                                     "❌ Kết nối CSDL thất bại!\nVui lòng kiểm tra thông tin đăng nhập MySQL hoặc thực hiện thao tác setup.")
            else:
                messagebox.showerror("Database Error",
                                     "❌ Database connection failed!\nPlease check your MySQL credentials or run the setup operation.")
            return
        create_tables(cursor)
        create_default_users(cursor, cnx)
        camera_type = self.combo_camera_type.get().strip()
        camera_url = self.entry_camera_url.get().strip()
        self.selected_protocol = self.optionmenu_protocol.get().strip()
        self.camera_user = self.entry_camera_user.get().strip()
        self.camera_pass = self.entry_camera_pass.get().strip()
        self.camera_ip = self.entry_camera_ip.get().strip()
        self.camera_port = self.entry_camera_port.get().strip()
        if self.remember_var.get():
            save_config(
                "Light", language, db_host, db_username, db_password,
                camera_type, camera_url, self.camera_types,
                camera_simple_mode=self.simple_mode,
                camera_protocol=self.selected_protocol,
                camera_user=self.camera_user,
                camera_pass=self.camera_pass,
                camera_ip=self.camera_ip,
                camera_port=self.camera_port
            )
        else:
            save_config(
                "Light", language, "", "", "",
                camera_type, camera_url, self.camera_types,
                camera_simple_mode=self.simple_mode,
                camera_protocol=self.selected_protocol,
                camera_user=self.camera_user,
                camera_pass=self.camera_pass,
                camera_ip=self.camera_ip,
                camera_port=self.camera_port
            )
        self.destroy()
        from control_panel import open_user_login_window
        open_user_login_window(cnx, cursor, language)

    def exit_app(self):
        save_config("Light", self.language, self.entry_db_host.get().strip(),
                    self.entry_db_username.get().strip(), self.entry_db_password.get().strip(),
                    self.combo_camera_type.get().strip(), self.entry_camera_url.get().strip(), self.camera_types,
                    camera_simple_mode=self.simple_mode,
                    camera_protocol=self.optionmenu_protocol.get().strip(),
                    camera_user=self.entry_camera_user.get().strip(),
                    camera_pass=self.entry_camera_pass.get().strip(),
                    camera_ip=self.entry_camera_ip.get().strip(),
                    camera_port=self.entry_camera_port.get().strip())
        self.destroy()
        sys.exit(0)

class UserLoginWindow(tk.Tk):
    def __init__(self, cnx, cursor, language):
        super().__init__()
        self.cnx = cnx
        self.cursor = cursor
        self.language = language
        self.trans = translations[self.language]
        self.title(self.trans["user_title"])
        self.geometry("600x400")
        self.resizable(False, False)
        self.create_widgets()

    def create_widgets(self):
        self.label_title = ttk.Label(self, text=self.trans["user_title"], font=("Arial", 20))
        self.label_title.pack(pady=10)
        self.frame_form = ttk.Frame(self)
        self.frame_form.pack(pady=5, padx=20, fill="both", expand=True)
        self.label_username = ttk.Label(self.frame_form, text=self.trans["username"])
        self.label_username.grid(row=0, column=0, padx=10, pady=10, sticky="e")
        self.entry_username = ttk.Entry(self.frame_form)
        self.entry_username.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        self.label_password = ttk.Label(self.frame_form, text=self.trans["password"])
        self.label_password.grid(row=1, column=0, padx=10, pady=10, sticky="e")
        self.entry_password = ttk.Entry(self.frame_form, show="*")
        self.entry_password.grid(row=1, column=1, padx=10, pady=10, sticky="w")
        self.frame_buttons = ttk.Frame(self)
        self.frame_buttons.pack(pady=10, padx=40, fill="x")
        self.frame_buttons.grid_columnconfigure(0, weight=1)
        self.frame_buttons.grid_columnconfigure(1, weight=1)
        self.frame_buttons.grid_columnconfigure(2, weight=1)
        self.button_login = ttk.Button(self.frame_buttons, text=self.trans["login"],
                                      command=self.handle_user_login)
        self.button_login.grid(row=0, column=0, padx=20, pady=10)
        self.button_back = ttk.Button(self.frame_buttons, text=self.trans["back"],
                                     command=self.go_back)
        self.button_back.grid(row=0, column=1, padx=20, pady=10)
        self.button_attendance = ttk.Button(self.frame_buttons, text=self.trans["attendance"],
                                          command=self.open_attendance)
        self.button_attendance.grid(row=0, column=2, padx=20, pady=10)

    def handle_user_login(self):
        user_username = self.entry_username.get().strip()
        user_password = self.entry_password.get().strip()
        if not user_username or not user_password:
            if self.language == "Tiếng Việt":
                messagebox.showerror("Lỗi", "❌ Vui lòng nhập tên đăng nhập và mật khẩu.")
            else:
                messagebox.showerror("Error", "❌ Please enter username and password.")
            return
        user_info = verify_user(self.cursor, user_username, user_password)
        if user_info is None:
            if self.language == "Tiếng Việt":
                messagebox.showerror("Đăng nhập thất bại", "❌ Tên đăng nhập hoặc mật khẩu không hợp lệ!")
            else:
                messagebox.showerror("Login Failed", "❌ Invalid username or password!")
            return
        self.destroy()
        from control_panel import open_control_panel
        open_control_panel(user_info, self.cnx, self.cursor, self.language)

    def open_attendance(self):
        try:
            import json
            with open("config.json", "r", encoding="utf-8") as f:
                config_data = json.load(f)
            camera_type = config_data.get("camera_type", "Webcam mặc định")
            camera_url = config_data.get("camera_url", "")
            camera_source = 0 if camera_type in ["Webcam mặc định", "Default Webcam"] else camera_url
            AttendanceWindow(self.cnx, self.cursor, camera_source)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể mở chức năng điểm danh:\n{e}")

    def go_back(self):
        self.destroy()
        from GUI import MySQLLoginWindow
        win = MySQLLoginWindow()
        win.mainloop()

class AttendanceWindow(tk.Toplevel):
    def __init__(self, cnx, cursor, camera_source):
        super().__init__()
        self.cnx = cnx
        self.cursor = cursor
        self.camera_source = camera_source
        self.title("Giao diện điểm danh")
        self.geometry("300x100")
        self.create_widgets()
        self.attendance_thread = threading.Thread(target=self.run_attendance, daemon=True)
        self.attendance_thread.start()

    def create_widgets(self):
        self.button_close = ttk.Button(self, text="Đóng điểm danh", command=self.close_attendance)
        self.button_close.pack(pady=20)

    def run_attendance(self):
        try:
            FacialRecognition.main(self.cnx, self.cursor, self.camera_source)
        except Exception as e:
            print("Lỗi khi chạy điểm danh:", e)

    def close_attendance(self):
        self.destroy()

def main():
    app = MySQLLoginWindow()
    app.mainloop()

if __name__ == "__main__":
    main()
