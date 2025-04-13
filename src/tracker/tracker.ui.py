import tkinter as tk
from tkinter import scrolledtext
import threading
import socket
import time
import json
import os

def load_env(filepath=".env"):
    if not os.path.exists(filepath):
        print(f"⚠️ File {filepath} không tồn tại.")
        return

    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()

# Gọi khi import
load_env()

# Lấy giá trị của các biến môi trường
TRACKER_HOST = os.getenv("TRACKER_HOST")
TRACKER_PORT = int(os.getenv("TRACKER_PORT"))
CHUNK_DIR = os.getenv("CHUNK_DIR")
NODE_DIR = os.getenv("NODE_DIR")
CHUNK_SIZE = os.getenv("CHUNK_SIZE")
DOWNLOAD_FOLDER = os.getenv("DOWNLOAD_FOLDER")
PEER_PORT = int(os.getenv("PEER_PORT"))
# File lưu thông tin nodes và file chia sẻ
PEERS_FILE = "tracker/peers.json"
FILE_DATABASE = "tracker/file_registry.json"

# Đọc dữ liệu từ file JSON (nếu có)
def load_json(file_path):
    try:
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                return json.load(f)
    except json.JSONDecodeError:
        pass
    return {}

# Lưu dữ liệu vào file JSON
def save_json(file_path, data):
    try:
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"[ERROR] Không thể lưu {file_path}: {e}")

# Danh sách các nodes và file chia sẻ (tải từ file nếu có)
peers = load_json(PEERS_FILE)
file_registry = load_json(FILE_DATABASE)

def handle_client(client_socket, addr, log_widget):
    global peers, file_registry
    try:
        data = client_socket.recv(1024).decode().strip()
        log_widget.insert(tk.END, f"[DEBUG] {addr}: {data}\n")  # Log nhận lệnh
        log_widget.yview(tk.END)  # Cuộn đến cuối

        if not data:
            return

        # Kiểm tra xem data có phải JSON không
        try:
            command = json.loads(data)  # Nếu thành công -> JSON
        except json.JSONDecodeError:
            command = data.split(" ")  # Nếu lỗi -> xử lý theo dạng chuỗi thường

        if isinstance(command, dict):  # Xử lý JSON command
            if command["action"] == "FILE_AVAILABLE":
                peer_id = command["node"]
                filename = command["filename"]
                host = command["host"]
                port = command["port"]
                num_chunks = command["chunks"]

                if filename not in file_registry or not isinstance(file_registry[filename], list):
                    log_widget.insert(tk.END, f"[WARNING] file_registry[{filename}] không hợp lệ, khởi tạo lại danh sách.\n")
                    file_registry[filename] = []

                file_registry[filename].append({"peer": peer_id, "host": host, "port": port, "chunks": num_chunks})
                save_json(FILE_DATABASE, file_registry)

                log_widget.insert(tk.END, f"[DEBUG] file_registry sau cập nhật: {json.dumps(file_registry, indent=4)}\n")
                log_widget.yview(tk.END)
                client_socket.send(json.dumps({"status": "FILE_UPDATED", "filename": filename}).encode())

        elif isinstance(command, list):  # Xử lý text-based command
            if command[0] == "REGISTER":
                ip, port = command[1], command[2]
                peer_id = f"{ip}:{port}"
                peers[peer_id] = {"ip": ip, "port": port, "status": "connected", "last_seen": time.time()}
                save_json(PEERS_FILE, peers)
                log_widget.insert(tk.END, f"[INFO] REGISTERED {peer_id}\n")
                log_widget.yview(tk.END)
                client_socket.send(f"REGISTERED {peer_id}".encode())
            elif command[0] == "LEAVE":
                ip, port = command[1], command[2]
                peer_id = f"{ip}:{port}"
                if peer_id in peers:
                    peers[peer_id]["status"] = "disconnected"
                    peers[peer_id]["last_seen"] = time.time()
                    save_json(PEERS_FILE, peers)
                log_widget.insert(tk.END, f"[INFO] LEFT {peer_id}\n")
                log_widget.yview(tk.END)
                client_socket.send("LEFT".encode())
            elif command[0] == "GET_PEERS":
                active_peers = [peer for peer, info in peers.items() if info["status"] == "connected"]
                peers_list = ",".join(active_peers) if active_peers else "NO_PEERS"
                client_socket.send(f"PEERS {peers_list}".encode())
            if command[0] == "GET_FILE_SOURCES":
                filename = command[1]
                sources = file_registry.get(filename, [])
                response = json.dumps({"sources": sources})  
                client_socket.send(response.encode())
        else:
            log_widget.insert(tk.END, f"[ERROR] Không xác định được loại lệnh: {command}\n")
            log_widget.yview(tk.END)

    except Exception as e:
        log_widget.insert(tk.END, f"[ERROR] {e}\n")
        log_widget.yview(tk.END)

    finally:
        client_socket.close()

def start_tracker(log_widget):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", 6000))
    server.listen(5)
    log_widget.insert(tk.END, "[TRACKER] Server is running on port 6000...\n")
    log_widget.yview(tk.END)

    while True:
        client_sock, addr = server.accept()
        threading.Thread(target=handle_client, args=(client_sock, addr, log_widget)).start()

# GUI chính
class TrackerGUI:
    def __init__(self, root):
        self.root = root
        root.title("Tracker UI")
        root.geometry("800x600")

        # Hiển thị log
        self.log_text = scrolledtext.ScrolledText(root, width=100, height=30, wrap=tk.WORD)
        self.log_text.pack(pady=10)

        # Nút bắt đầu tracker
        self.start_button = tk.Button(root, text="Start Tracker", command=self.start_tracker)
        self.start_button.pack(pady=10)

    def start_tracker(self):
        self.start_button.config(state=tk.DISABLED)  # Vô hiệu hóa nút sau khi nhấn
        threading.Thread(target=start_tracker, args=(self.log_text,), daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = TrackerGUI(root)
    root.mainloop()
