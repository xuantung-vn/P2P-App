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
PIECE_SIZE = 512 * 1024     # 512KB
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
        self.list_files = {}

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
        self.keyword_entry = ttk.Entry(self.dowload_tab, width=40)
        self.keyword_entry.pack()

        ttk.Button(self.dowload_tab, text="Tìm kiếm", command=self.search_file).pack(pady=10)
        ttk.Button(self.dowload_tab, text="Tải file", command=self.download_file_from_peers).pack(pady=10)

        self.download_listbox = tk.Listbox(self.dowload_tab, width=50, height=100)
        self.download_listbox.pack(pady=10, fill='both', expand=True)

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
                    filename, piece_index = command[1], command[2]
                    piece_index = int(piece_index)
                    file_path = os.path.join(f"{self.chunkdir}", f"{filename}_part{chunk}")
                    try:
                        with open(file_path, "rb") as f:
                            f.seek(piece_index * PIECE_SIZE)
                            chunk = f.read(PIECE_SIZE)
                            conn.sendall(chunk)
                            print(f"✅ Gửi piece {piece_index} của {filename} cho {addr}")
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
            messagebox.showerror("Lỗi", f"Không kết nối được với tracker.")
    def refresh_peers(self):
        response = self.get_peers_from_tracker()
        self.peer_listbox.delete(0, tk.END)
        
        if response:
            for idx, peer_info in enumerate(response, start=1):
                self.peer_listbox.insert(tk.END, f"{idx}. {peer_info}")
        else:
            messagebox.showerror("Lỗi", f"Không có peers nào hoặc không kết nối được với tracker.")
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
            messagebox.showerror("Lỗi", f"Không thể tìm danh sách peer")
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
        """Chia file thành các mảnh và tính toán hash cho từng mảnh"""
        pieces = []
        os.makedirs(self.chunk_dir, exist_ok=True)  # Tạo thư mục chunk nếu chưa có

        with open(file_path, 'rb') as f:
            piece_index = 0  # Chỉ số mảnh
            while True:
                # Đọc từng mảnh với kích thước piece_length
                piece = f.read(piece_length)
                if not piece:
                    break

                # Tính toán hash cho mảnh và lưu mảnh vào thư mục chunk
                piece_hash = self.sha1_hash(piece)
                pieces.append(piece_hash)

                # Lưu mảnh vào thư mục chunk
                piece_filename = f"{piece_index}_{piece_hash}.chunk"
                piece_path = os.path.join(self.chunk_dir, piece_filename)
                with open(piece_path, 'wb') as piece_file:
                    piece_file.write(piece)

                piece_index += 1  # Tăng chỉ số mảnh

        return pieces  # Trả về danh sách các hash của các mảnh

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

        file_name = os.path.basename(filename)
        file_size = os.path.getsize(filename)

        pieces = self.split_and_hash_file(filename, PIECE_SIZE)
        metainfo = {
            "file_name": file_name,
            "file_size": file_size,
            "piece_length": PIECE_SIZE,
            "num_pieces": len(pieces),
            "pieces": pieces
        }
        self.notify_tracker(metainfo)

        messagebox.showinfo("Phản hồi", "File đã được chia sẻ thành công!")

    def notify_tracker(self, metainfo):
        """Thông báo tracker rằng node đang giữ file"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((TRACKER_HOST, TRACKER_PORT))
                message = json.dumps({"action": "FILE_AVAILABLE", "node": self.id, "metainfo": metainfo,"host":self.host, "port": self.port})
                s.send(message.encode())
                response = s.recv(1024).decode()
                print("[TRACKER] Response:", response)

        except Exception as e:
            print(f"[ERROR] Không thể thông báo tracker: {e}")

    def search_file(self):
        keyword = self.keyword_entry.get().strip()
        self.list_files = {}
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((TRACKER_HOST, TRACKER_PORT))
                
                # Gửi yêu cầu tìm kiếm
                message = json.dumps({
                    "action": "SEARCH_FILE",
                    "node": self.id,
                    "keyword": keyword,  # dùng từ "keyword" thay vì "filename"
                    "host": self.host,
                    "port": self.port
                })
                s.send(message.encode())
                response = s.recv(4096).decode()  # tăng buffer size để nhận nhiều file
                result_text = ""
                file_data = json.loads(response)
                self.download_listbox.delete(0, tk.END)  # Xóa tất cả các mục trong listbox trước
                self.list_files = file_data.items()
                for file_name, peers in file_data.items():
                    result_text = f"{file_name}\n"  # Tiêu đề file
                    self.download_listbox.insert(tk.END, result_text)
                    for i, peer in enumerate(peers, start=1):
                        # Mỗi peer được hiển thị theo định dạng dễ đọc
                        self.download_listbox.insert(tk.END, f"     #{i} Id: {peer['peer']} - IP: {peer['host']}:{peer['port']}")
                        self.download_listbox.insert(tk.END, f"     ---------------------------------------- ")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể tìm file {e}")
   
    def download_piece_from_peer(self, host, port, file_name, piece_index):
        try:
            s = socket.socket()
            s.settimeout(5)
            s.connect((host, port))

            # Gửi yêu cầu dưới dạng: file_name|piece_index
            s.send(f"{file_name}|{piece_index}".encode())

            data = b""
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                data += chunk
            s.close()
            return data
        except Exception as e:
            print(f"❌ Không tải được piece {piece_index} từ {host}:{port}: {e}")
            return None

    def download_file_from_peers(self):
        self.list_files
        metainfo_path = self.keyword_entry.get().strip()
        peers = self.list_files
        with open(metainfo_path, "r") as f:
            meta = json.load(f)

        file_name = meta["file_name"]
        piece_length = meta["piece_length"]
        pieces_hash = meta["pieces"]
        num_pieces = meta["num_pieces"]

        downloaded_pieces = [None] * num_pieces

        for i in range(num_pieces):
            success = False
            for peer in peers:
                data = self.download_piece_from_peer(peer["host"], peer["port"], file_name, i)
                if data is None:
                    continue

                hash_val = self.sha1_hash(data)
                if hash_val == pieces_hash[i]:
                    downloaded_pieces[i] = data
                    print(f"✅ Piece {i} đã được xác thực và tải về.")
                    success = True
                    break
                else:
                    print(f"⚠️ Piece {i} sai hash từ {peer['host']}:{peer['port']}")

            if not success:
                print(f"❌ Không thể tải piece {i} từ bất kỳ peer nào.")
                return

        # Gộp các mảnh lại và ghi ra file
        os.makedirs("downloads", exist_ok=True)
        with open(f"{self.donwload_dir}/{file_name}", "wb") as f:
            for i, piece in enumerate(downloaded_pieces):
                if piece:
                    f.write(piece)
                else:
                    print(f"❌ Thiếu piece {i}, file không hoàn chỉnh.")
                    return
        print(f"🎉 Tải file {file_name} hoàn tất và lưu tại {self.donwload_dir}")

# Khởi động giao diện
if __name__ == "__main__":
    root = tk.Tk()
    app = P2PGUI(root)
    root.mainloop()
