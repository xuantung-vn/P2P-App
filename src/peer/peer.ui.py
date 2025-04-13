import hashlib
import os
import random
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import socket
import json


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
# TRACKER_IP = "127.0.0.1"
# TRACKER_HOST = os.getenv("TRACKER_HOST")
# TRACKER_PORT = int(os.getenv("TRACKER_PORT"))
# CHUNK_DIR = os.getenv("CHUNK_DIR")
# NODE_DIR = os.getenv("NODE_DIR")
# CHUNK_SIZE = os.getenv("CHUNK_SIZE")
# DOWNLOAD_FOLDER = os.getenv("DOWNLOAD_FOLDER")
# PEER_PORT = int(os.getenv("PEER_PORT"))
TRACKER_HOST = "0.0.0.0"
TRACKER_PORT = 6000

TRACKER_URL = "http://your-tracker-url.local"
DOWNLOAD_DIRECTORY = "./downloads"
TIMEOUT = 30

PEER_PORT = 5000
PEER_HOST = 6881
MAX_CONNECTIONS = 10


NODE_PORT = 7000            # Cổng lắng nghe của node
CHUNK_SIZE = 512 * 1024     # 512KB
CHUNK_DIR = "chunks"
NODE_DIR = "nodes"

DOWNLOAD_FOLDER = "downloads"

# GUI chính
class P2PGUI:
    def __init__(self, root,  host="0.0.0.0", port=PEER_PORT):
        self.root = root
        root.title("Tôi muốn qua môn")
        root.geometry("600x720")

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

        # HOST
        self.host = host
        self.port = self.find_available_port(port)
        self.id = self.generate_id()
        self.peers = set()
        self.running = True

        # Tạo thư mục riêng cho node
        self.node_dir = os.path.join(NODE_DIR, self.id)
        self.chunk_dir = f"{self.node_dir}/{CHUNK_DIR}"
        self.donwload_dir = f"{self.node_dir}/{DOWNLOAD_FOLDER}"
        if not os.path.exists(self.node_dir):
            os.makedirs(self.node_dir)
            os.makedirs(self.donwload_dir)
            os.makedirs(self.chunk_dir)

        # Tạo socket server
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((self.host, self.port))
        self.server.listen(5)

        # Đăng ký với tracker
        self.register_with_tracker()
        # Bắt đầu luồng lắng nghe kết nối
        threading.Thread(target=self.listen_for_peers, daemon=True).start()

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
        ttk.Button(self.peer_tab, text="Kết nối lại với tracker", command=self.register_with_tracker).pack(pady=10)

        self.peer_listbox = tk.Listbox(self.peer_tab, width=50)
        self.peer_listbox.pack(pady=10, fill='both', expand=True)

    def generate_id(self):
        """Tạo ID ngắn gọn cho node"""
        hash_obj = hashlib.sha256()
        random_data = f"{self.host}{self.port}{random.randint(1, 999999)}"
        hash_obj.update(random_data.encode('utf-8'))
        return hash_obj.hexdigest()[:6]  # Lấy 6 ký tự đầu của SHA-256
 
    def listen_for_peers(self):
        """Lắng nghe kết nối từ các node khác"""
        while self.running:
            try:
                conn, addr = self.server.accept()
                threading.Thread(target=self.handle_peer, args=(conn, addr), daemon=True).start()
            except Exception as e:
                print(f"[ERROR] {e}")
    def handle_peer(self, conn, addr):
        """Xử lý khi một node khác kết nối"""
        print(f"[NODE] Connected to {addr}")
        
        try:
            while True:
                data = conn.recv(1024).decode().strip()
                if not data:
                    break
                print(f"[MESSAGE FROM {addr}] {data}")
                command = data.split(" ")

                if command[0] == "DOWNLOAD":
                    filename, chunk = command[1], command[2]
                    file_path = os.path.join(f"{self.chunkdir}", f"{filename}_part{chunk}")
                    try:
                        with open(file_path, "rb") as f:
                            while True:
                                chunk_data = f.read(1024)
                                if not chunk_data:
                                    break
                                conn.sendall(chunk_data)
                        
                        # Gửi tín hiệu EOF để thông báo kết thúc
                        conn.sendall(b"EOF")
                        print(f"[INFO] Đã gửi phần {chunk} của {filename} tới {addr}")
                    except FileNotFoundError:
                        print(f"[ERROR] Không tìm thấy phần {chunk} của {filename}")
                        conn.sendall(b"ERROR: File not found")
        except Exception as e:
            print(f"[ERROR] {e}")
        finally:
            conn.close()
            print(f"[NODE] Disconnected from {addr}")

    def connect_to_peer(self, peer_host, peer_port):
        """Kết nối với một node khác"""
        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.connect((peer_host, int(peer_port)))
            self.peers.add((peer_host, peer_port))
            print(f"[NODE] Connected to {peer_host}:{peer_port}")
            return conn
        except Exception as e:
            return None

    def register_with_tracker(self):
        """Gửi thông tin node đến tracker"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((TRACKER_HOST, TRACKER_PORT))
                s.send(f"REGISTER {self.host} {self.port}".encode())
                response = s.recv(1024).decode()
                print("[TRACKER] Response:", response)
        except Exception as e:
            print(f"[ERROR] Could not register with tracker: {e}")
    def refresh_peers(self):
        response = self.get_peers_from_tracker()
        self.peer_listbox.delete(0, tk.END)
        
        if response:
            for idx, peer_info in enumerate(response, start=1):
                self.peer_listbox.insert(tk.END, f"{idx}. {peer_info}")
        else:
            print("[INFO] Không có peers nào hoặc không kết nối được với tracker.")
            return

    def get_peers_from_tracker(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((TRACKER_HOST, TRACKER_PORT))
                s.send("GET_PEERS".encode())
                response = s.recv(1024).decode()
                
                if response.startswith("PEERS "):
                    # Xử lý danh sách peer từ tracker
                    peers_list = response[6:].split(",")
                    return peers_list
                return []
        except Exception as e:
            print(f"[ERROR] Could not get peers from tracker: {e}")
            return []
    
    def find_available_port(self, port=PEER_PORT):
        """Tìm cổng trống"""
        while not self.is_port_available(port):
            port = random.randint(PEER_PORT, 9999)
        return port

    def is_port_available(self, port):
        """Kiểm tra cổng có trống không"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex((self.host, port)) != 0
    def sha1_hash(self, data):
        """Tính toán SHA-1 hash cho dữ liệu"""
        return hashlib.sha1(data).hexdigest()

    def split_and_hash_file(self, file_path, piece_length):
        """Chia file thành các pieces và tính toán hash cho từng piece"""
        pieces = []
        with open(file_path, 'rb') as f:
            while True:
                piece = f.read(piece_length)
                if not piece:
                    break
                pieces.append(self.sha1_hash(piece))  # Sử dụng self.sha1_hash
        return pieces

    def create_metainfo(self, file_path, tracker_url, piece_length=512 * 1024):
        """Tạo metainfo cho file và lưu vào tệp JSON"""
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        pieces = self.split_and_hash_file(file_path, piece_length)

        metainfo = {
            "file_name": file_name,
            "file_size": file_size,
            "piece_length": piece_length,
            "num_pieces": len(pieces),
            "pieces": pieces,
            "tracker": tracker_url
        }

        metainfo_filename = file_name + ".metainfo.json"
        with open(f"{NODE_DIR}/{self.id}/{CHUNK_DIR}/{metainfo_filename}", 'w') as out:
            json.dump(metainfo, out, indent=4)

        print(f"✅ Metainfo file created: {metainfo_filename}")
        return metainfo_filename

    def select_file(self):
        """Chọn file để chia sẻ"""
        filename = filedialog.askopenfilename(title="Chọn file để chia sẻ", filetypes=(("All Files", "*.*"),))
        if filename:
            self.filename_entry.delete(0, tk.END)
            self.filename_entry.insert(0, filename)

    def share_file(self):
        """Chia sẻ file lên tracker"""
        filename = self.filename_entry.get()

        if not filename:
            messagebox.showerror("Lỗi", "Vui lòng chọn file hợp lệ")
            return

        # Tạo metainfo file
        tracker_url = f"http://{TRACKER_HOST}:{TRACKER_PORT}/"
        metainfo_filename = self.create_metainfo(filename, tracker_url)
        chunk_number = 0
        response = self.notify_tracker(metainfo_filename, chunk_number)

        messagebox.showinfo("Phản hồi", "File đã được chia sẻ thành công!")

    def search_file(self):
        filename = self.filename_entry.get()
        if not filename:
            messagebox.showerror("Lỗi", "Vui lòng nhập tên file hợp lệ")
            return

        response = self.download_file(filename)
        messagebox.showinfo("Phản hồi", response)
        
    def notify_tracker(self, filename, num_chunks):
        """Thông báo tracker rằng node đang giữ file"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((TRACKER_HOST, TRACKER_PORT))
                message = json.dumps({"action": "FILE_AVAILABLE", "node": self.id, "filename": filename, "chunks": num_chunks, "host":self.host, "port": self.port})
                s.send(message.encode())
                response = s.recv(1024).decode()
                print("[TRACKER] Response:", response)

        except Exception as e:
            print(f"[ERROR] Không thể thông báo tracker: {e}")

    def receive_chunk(self, conn, filename, chunk_number):
        """Nhận và lưu chunk vào thư mục riêng của node"""
        chunk_path = os.path.join(self.chunk_dir, f"{filename}.chunk{chunk_number}")
        with open(chunk_path, "wb") as f:
            while True:
                data = conn.recv(CHUNK_SIZE)
                if not data:
                    break
                f.write(data)
        print(f"[RECEIVED] Đã lưu {filename} chunk {chunk_number} tại {self.chunk_dir}")
        
    def send_request(self, command):
        """Gửi lệnh đến tracker và nhận phản hồi."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
                client.connect((TRACKER_HOST, TRACKER_PORT))
                client.send(command.encode())
                response = client.recv(4096).decode()
                print(f"[DEBUG] Phản hồi từ tracker: {response}")  # Thêm debug
                return response
        except Exception as e:
            print(f"[ERROR] Không thể gửi yêu cầu '{command}': {e}")
            return None
    def download_file(self, filename):
        """Tải file từ các peer có sẵn."""
        response = self.send_request(f"GET_FILE_SOURCES {filename}")

        if response is None:
            print(f"[ERROR] Không nhận được phản hồi từ tracker khi yêu cầu {filename}")
            return

        try:
            data = json.loads(response)
            sources = data.get("sources", [])
        except json.JSONDecodeError:
            print(f"[ERROR] Phản hồi từ tracker không phải là JSON hợp lệ: {response}")
            return

        if not sources:
            print(f"[INFO] Không tìm thấy nguồn tải cho file {filename}")
            return

        for source in sources:
            peer, num_chunks = source["peer"], source["chunks"]
            ip = source["host"]
            port = source["port"]
            print(f"[INFO] Đang tải {filename} từ {peer}")

            for chunk in range(num_chunks):
                self.download_chunk(ip, int(port), filename, chunk)
        self.merge_chunks(filename, num_chunks)
    def download_chunk(self, ip, port, filename, chunk):
        """Yêu cầu tải một phần file từ peer."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
                client.connect((ip, port))
                client.send(f"DOWNLOAD {filename} {chunk}".encode())

                with open(f"{self.chunk_dir}/{filename}_part{chunk}", "wb") as f:
                    while True:
                        data = client.recv(1024)
                        if not data:
                            break
                        f.write(data)
            print(f"[INFO] Đã tải xong phần {chunk} của {filename}")
        except Exception as e:
            print(f"[ERROR] Lỗi tải {filename} phần {chunk}: {e}")

    def merge_chunks(self, filename, num_chunks):
        """Ghép các chunk thành file hoàn chỉnh"""
        output_path = os.path.join(self.donwload_dir, filename)
        with open(output_path, "wb") as output_file:
            for chunk_number in range(num_chunks):
                chunk_path = os.path.join(self.chunk_dir, f"{filename}_part{chunk_number}")
                if os.path.exists(chunk_path):
                    with open(chunk_path, "rb") as chunk_file:
                        output_file.write(chunk_file.read())
                    os.remove(chunk_path)  # Xóa chunk sau khi ghép thành công
                else:
                    print(f"[ERROR] Thiếu chunk {chunk_number}, không thể ghép file {filename}")
                    return
        print(f"[MERGE] Đã hoàn tất file {filename} tại {output_path}")
   
    def stop(self):
        """Dừng node"""
        response = self.send_request(f"LEAVE")
        self.running = False
        self.server.close()
        print("[NODE] Shutting down")

# Khởi động giao diện
if __name__ == "__main__":
    root = tk.Tk()
    app = P2PGUI(root)
    root.mainloop()
