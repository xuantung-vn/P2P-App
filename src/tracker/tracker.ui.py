from datetime import datetime
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
# TRACKER_HOST = os.getenv("TRACKER_HOST")
# TRACKER_PORT = int(os.getenv("TRACKER_PORT"))
TRACKER_HOST = "0.0.0.0"
TRACKER_PORT = 6000

DOWNLOAD_DIRECTORY = "./downloads"
TIMEOUT = 30

TRACKER_HOST = "127.0.0.1"  # IP của tracker
NODE_PORT = 7000            # Cổng lắng nghe của node
CHUNK_SIZE = 512 * 1024     # 512KB
NODE_DIR = "nodes"
DATA = "./src/tracker/data"

# # File lưu thông tin nodes và file chia sẻ
PEERS_FILE = "./src/tracker/peers.json"
FILE_DATABASE = "./src/tracker/files.json"

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
        print(f"[💾 SAVED] Dữ liệu đã được lưu vào {file_path}")
    except Exception as e:
        print(f"[❌ ERROR] Không thể lưu {file_path}: {e}")

# Danh sách các nodes và file chia sẻ (tải từ file nếu có)
peers = load_json(PEERS_FILE)
# Hàm tính toán khoảng thời gian (minutes, hours, days)
def format_time_diff(last_seen):
    now = time.time()  # Thời gian hiện tại
    diff = now - last_seen  # Khoảng cách thời gian
    # Tính số phút, giờ, ngày
    if diff < 60:
        return f"{int(diff)} giây trước"
    elif diff < 3600:
        minutes = int(diff // 60)
        return f"{minutes} phút trước"
    elif diff < 86400:
        hours = int(diff // 3600)
        return f"{hours} giờ trước"
    elif diff < 2592000:  # 30 ngày
        days = int(diff // 86400)
        return f"{days} ngày trước"
    else:
        # Trường hợp đã qua hơn 30 ngày
        return time.strftime('%Y-%m-%d', time.localtime(last_seen))
def create_metainfo(metainfo):
    """Tạo metainfo cho file và lưu vào tệp JSON"""
    metainfo_filename = metainfo["file_name"] + ".metainfo.json"
    with open(f"{DATA}/{metainfo_filename}", 'w') as out:
        json.dump(metainfo, out, indent=4)

    print(f"✅ Metainfo file created: {metainfo_filename}")
    return metainfo_filename

def handle_client(client_socket, addr, log_widget):
    global peers, file_registry
    try:
        data = client_socket.recv(1024).decode().strip()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_widget.insert(tk.END, f"[{timestamp}] {addr}: {data}\n")  # Log nhận lệnh
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
                host = command["host"]
                port = command["port"]

                metainfo = command["metainfo"]
                filename = metainfo["file_name"]
                pieces = metainfo["pieces"]
                metainfo_path = f"{DATA}/{create_metainfo(metainfo)}"
                file_registry = load_json(FILE_DATABASE)
                
                if filename not in file_registry or not isinstance(file_registry[filename], list):
                    log_widget.insert(tk.END, f"[WARNING] file_registry[{filename}] không hợp lệ, khởi tạo lại danh sách.\n")
                    file_registry[filename] = []
                file_registry[filename].append({"peer": peer_id, "host": host, "port": port})
                save_json(FILE_DATABASE, file_registry)

                log_widget.insert(tk.END, f"[DEBUG] file_registry  cập nhật\n")
                log_widget.yview(tk.END)
                client_socket.send(json.dumps({"status": "FILE_UPDATED", "filename": filename}).encode())

            if command['action'] == "SEARCH_FILE":
                file_registry = load_json(FILE_DATABASE)
                keyword = command.get("keyword", "").lower()
                result = {}

                for file_name, peers in file_registry.items():
                    if keyword in file_name.lower() or keyword == "":
                        metainfo_path = os.path.join(f"{DATA}", f"{file_name}.metainfo.json")
                        file_info = {
                            "peers": peers
                        }

                        # Nếu có metainfo thì thêm thông tin vào
                        if os.path.exists(metainfo_path):
                            with open(metainfo_path, "r") as meta_file:
                                metainfo = json.load(meta_file)
                                file_info.update({
                                    "file_size": metainfo.get("file_size"),
                                    "piece_length": metainfo.get("piece_length"),
                                    "num_pieces": metainfo.get("num_pieces"),
                                    "pieces": metainfo.get("pieces"),
                                    "tracker": metainfo.get("tracker")
                                })

                        result[file_name] = file_info

                client_socket.send(json.dumps(result).encode())
        elif isinstance(command, list):  # Xử lý text-based command
            if command[0] == "REGISTER":
                ip, port = command[1], command[2]
                peer_id = f"{ip}:{port}"
                peers[peer_id] = {"ip": ip, "port": port, "status": "connected", "last_seen": time.time()}
                save_json(PEERS_FILE, peers)
                log_widget.insert(tk.END, f"[INFO] REGISTERED {peer_id}\n")
                log_widget.yview(tk.END)
                client_socket.send(f"REGISTERED {peer_id}".encode())
            elif command[0] == "GET_PEERS":
                active_peers = []
                peers = load_json(PEERS_FILE)
                # Tạo danh sách peers chi tiết
                for peer, info in peers.items():
                    # Lấy thông tin chi tiết về peer
                    ip, port = peer.split(":")
                    status = info["status"]
                    last_seen = format_time_diff(info["last_seen"])

                    # Thêm thông tin về peer vào danh sách
                    peer_info = f"Host: {ip} - Port: {port} - Status: {status} - Last Seen: {last_seen}"
                    active_peers.append(peer_info)
                
                peers_list = ",".join(active_peers) if active_peers else "NO_PEERS"
                client_socket.send(f"PEERS {peers_list}".encode())
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
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((TRACKER_HOST, TRACKER_PORT))
    server.listen(5)

    log_widget.insert(tk.END, "[TRACKER] Server is running on port {TRACKER_PORT}...\n")
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
