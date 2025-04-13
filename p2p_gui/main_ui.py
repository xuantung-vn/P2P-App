import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import socket
import json

TRACKER_IP = "127.0.0.1"
TRACKER_PORT = 6000

# Gửi dữ liệu đến tracker và nhận phản hồi
def send_to_tracker(data, is_json=False):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((TRACKER_IP, TRACKER_PORT))
            s.send(json.dumps(data).encode() if is_json else data.encode())
            return s.recv(4096).decode()
    except Exception as e:
        return f"Error: {e}"

# GUI chính
class P2PGUI:
    def __init__(self, root):
        self.root = root
        root.title("Tôi muốn qua môn")
        root.geometry("1024x720")

        tab_control = ttk.Notebook(root)

        self.share_tab = ttk.Frame(tab_control)
        self.dowload_tab = ttk.Frame(tab_control)
        self.peer_tab = ttk.Frame(tab_control)

        tab_control.add(self.share_tab, text='Chia sẻ File')
        tab_control.add(self.dowload_tab, text='Tải file Online')
        tab_control.add(self.peer_tab, text='Danh sách các Node khác')

        tab_control.pack(expand=1, fill='both')

        self.create_donwload_tab()
        self.create_share_tab()
        self.create_peer_tab()

    def create_donwload_tab(self):
        ttk.Label(self.dowload_tab, text="Tên File:").pack(pady=5)
        self.filename_entry = ttk.Entry(self.dowload_tab, width=40)
        self.filename_entry.pack()

        ttk.Button(self.dowload_tab, text="Tìm kiếm", command=self.search_file).pack(pady=10)

        self.peer_listbox = tk.Listbox(self.dowload_tab, width=50)
        self.peer_listbox.pack(pady=10, fill='both', expand=True)

    def create_share_tab(self):
        ttk.Label(self.share_tab, text="Tên File:").pack(pady=5)
        self.filename_entry = ttk.Entry(self.share_tab, width=40)
        self.filename_entry.pack()

        # Nút chọn file
        ttk.Button(self.share_tab, text="Chọn File", command=self.select_file).pack(pady=5)

        ttk.Button(self.share_tab, text="Gửi đến Tracker", command=self.share_file).pack(pady=10)

    def create_peer_tab(self):
        ttk.Button(self.peer_tab, text="Làm mới danh sách", command=self.refresh_peers).pack(pady=10)

        self.peer_listbox = tk.Listbox(self.peer_tab, width=50)
        self.peer_listbox.pack(pady=10, fill='both', expand=True)

    def select_file(self):
        filename = filedialog.askopenfilename(title="Chọn file để chia sẻ", filetypes=(("All Files", "*.*"),))
        if filename:
            self.filename_entry.delete(0, tk.END)  # Xóa entry cũ
            self.filename_entry.insert(0, filename)  # Đặt đường dẫn tệp vào entry

    def share_file(self):
        filename = self.filename_entry.get()

        if not filename:
            messagebox.showerror("Lỗi", "Vui lòng nhập tên file và số lượng mảnh hợp lệ")
            return

        command = {
            "action": "FILE_AVAILABLE",
            "node": "127.0.0.1:5001",  # ID của node (tuỳ chỉnh)
            "host": "127.0.0.1",
            "port": 5001,
            "filename": filename
        }

        response = send_to_tracker(command, is_json=True)
        if "Error" in response:
            messagebox.showerror("Lỗi", response)
        else:
            messagebox.showinfo("Phản hồi", response)

    def search_file(self):
        filename = self.filename_entry.get()
        if not filename:
            messagebox.showerror("Lỗi", "Vui lòng nhập tên file hợp lệ")
            return

        command = {
            "action": "FILE_AVAILABLE",
            "node": "127.0.0.1:5001",  # ID của node (tuỳ chỉnh)
            "host": "127.0.0.1",
            "port": 5001,
            "filename": filename,
        }

        response = send_to_tracker(command, is_json=True)
        messagebox.showinfo("Phản hồi", response)

    def refresh_peers(self):
        response = send_to_tracker("GET_PEERS")
        self.peer_listbox.delete(0, tk.END)

        if "PEERS" in response:
            parts = response.split(" ", 1)
            if len(parts) == 2 and parts[1] != "NO_PEERS":
                for peer in parts[1].split(","):
                    self.peer_listbox.insert(tk.END, peer)
            else:
                self.peer_listbox.insert(tk.END, "Không có node nào online.")
        else:
            self.peer_listbox.insert(tk.END, "Lỗi khi lấy danh sách node.")

# Khởi động giao diện
if __name__ == "__main__":
    root = tk.Tk()
    app = P2PGUI(root)
    root.mainloop()
