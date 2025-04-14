import hashlib
import os
import queue
import random
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import socket
import json

TRACKER_HOST = "0.0.0.0"
TRACKER_PORT = 6000

TRACKER_URL = "http://your-tracker-url.local"
DOWNLOAD_DIRECTORY = "./downloads"
TIMEOUT = 30

PEER_PORT = 5000
PEER_HOST = 6881
MAX_CONNECTIONS = 10


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
        tab_control.add(self.peer_tab, text='Các Peer khác')

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
        self.chunkdir = f"{self.node_dir}/{CHUNK_DIR}"
        self.download_dir = f"{self.node_dir}/{DOWNLOAD_FOLDER}"
        if not os.path.exists(self.node_dir):
            os.makedirs(self.node_dir)
            os.makedirs(self.download_dir)
            os.makedirs(self.chunkdir)

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
        """Xử lý khi một peer khác kết nối để yêu cầu tải một phần của file"""
        try:
            while True:
                data = conn.recv(1024).decode().strip()
                if not data:
                    break

                print(f"[REQUEST] {data} from {addr}")
                command = data.split(" ")

                if command[0] == "DOWNLOAD":
                    if len(command) < 3:
                        conn.sendall(b"ERROR: Invalid DOWNLOAD command")
                        continue

                    filename = command[1]
                    piece_index = command[2]

                    try:
                        piece_index = int(piece_index)
                    except ValueError:
                        conn.sendall(b"ERROR: Invalid piece index")
                        continue

                    file_path = os.path.join(self.chunkdir, f"{piece_index}_{filename}.chunk")
                    if not os.path.exists(file_path):
                        conn.sendall(b"ERROR: File not found")
                        print(f"[ERROR] File not found: {file_path}")
                        continue

                    try:
                        with open(file_path, "rb") as f:
                            while True:
                                chunk_data = f.read(1024)
                                if not chunk_data:
                                    break
                                conn.sendall(chunk_data)

                        conn.sendall(b"EOF")
                        print(f"[SENT] Sent piece {piece_index} of {filename} to {addr}")
                    except Exception as file_err:
                        conn.sendall(b"ERROR: Failed to read file")
                        print(f"[ERROR] Failed to read/send {file_path}: {file_err}")
        except Exception as e:
            print(f"[ERROR] {e}")
        finally:
            conn.close()
            print(f"[DISCONNECTED] {addr}")

    def connect_to_peer(self, peer_host, peer_port):
        """Kết nối với một node khác và kiểm tra xem peer có online không"""
        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.settimeout(5)
            conn.connect((peer_host, int(peer_port)))

            self.peers.add((peer_host, peer_port))
            print(f"[NODE] Kết nối thành công với {peer_host}:{peer_port}")
            conn.close()
            return True
        except (socket.timeout, socket.error) as e:
            print(f"[ERROR] Không thể kết nối đến {peer_host}:{peer_port}. Lỗi: {e}")
            return False 


    def register_with_tracker(self):
        """Gửi thông tin node đến tracker"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((TRACKER_HOST, TRACKER_PORT))
                s.send(f"REGISTER {self.host} {self.port} {self.id}".encode())
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

                response = s.recv(8192).decode()
                data = json.loads(response)

                if data.get("type") == "PEERS":
                    peers_data = data.get("data", [])
                    peers_list = []

                    for peer in peers_data:
                        ip = peer.get("ip")
                        port = int(peer.get("port"))
                        last_seen = peer.get("last_seen", "N/A")

                        # Kiểm tra kết nối
                        conn = self.connect_to_peer(ip, port)
                        status = "🟢 Online" if conn else "🔴 Offline"

                        # Chuỗi hiển thị
                        peer_info = f"Host: {ip} - Port: {port} - Status: {status} - Last Seen: {last_seen}"
                        peers_list.append(peer_info)

                    return peers_list
                else:
                    return []

        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể tìm danh sách peer: {e}")
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
        os.makedirs(self.chunkdir, exist_ok=True)  # Tạo thư mục chunk nếu chưa có
        file_name = os.path.basename(file_path)
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
                piece_filename = f"{piece_index}_{file_name}.chunk"
                piece_path = os.path.join(self.chunkdir, piece_filename)
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
                response = s.recv(16384).decode()
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
                response = s.recv(8192).decode()  # tăng buffer size nếu dữ liệu nhiều
                self.download_listbox.delete(0, tk.END)  # Xóa tất cả các mục trong listbox trước

                file_data = json.loads(response)
                self.list_files = file_data.items()

                for file_name, file_info in file_data.items():
                    # Thông tin cơ bản về file
                    result_text = (
                        f"{file_name} - {file_info.get('file_size', 'N/A')} bytes - Pieces: {file_info.get('num_pieces', 'N/A')}"
                    )
                    self.download_listbox.insert(tk.END, result_text)

                    # Thông tin các peer
                    peers = file_info.get("peers", [])
                    for i, peer in enumerate(peers, start=1):
                        self.download_listbox.insert(
                            tk.END,
                            f"     #{i} 🧑‍💻 Id: {peer.get('peer', 'unknown')} - IP: {peer.get('host')}:{peer.get('port')}"
                        )
                        self.download_listbox.insert(tk.END, f"     ---------------------------------------- ")

        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể tìm file {e}")
   
    def download_piece_from_peer(self, host, port, file_name, piece_index):
        try:
            s = socket.socket()
            s.settimeout(5)
            s.connect((host, port))

            s.send(f"DOWNLOAD {file_name} {piece_index}".encode())

            data = b""
            while True:
                chunk = s.recv(4096)
                if b"EOF" in chunk:
                    chunk = chunk.replace(b"EOF", b"")
                    data += chunk
                    break
                if not chunk:
                    break
                data += chunk

            s.close()
            return data if data else None

        except Exception as e:
            print(f"[ERROR] Không tải được piece {piece_index} từ {host}:{port} - {e}")
            return None

    def download_file_from_peers(self):
        selected_index = self.download_listbox.curselection()
        if not selected_index:
            messagebox.showwarning("Thông báo", "⚠️ Vui lòng chọn một file để tải.")
            return

        selected_line = self.download_listbox.get(selected_index[0]).strip()
        try:
            file_name = selected_line.split(" - ")[0]
        except IndexError:
            print("❌ Không thể xác định tên file từ dòng đã chọn.")
            return
        
        file_info = dict(self.list_files).get(file_name)
        if not file_info:
            print("❌ Không tìm thấy thông tin file.")
            return

        num_pieces = file_info["num_pieces"]
        pieces_hash = file_info["pieces"]
        peers = file_info["peers"]
        downloaded_pieces = [None] * num_pieces

        log_queue = queue.Queue()

        def log(msg):
            log_queue.put(msg)

        def process_log_queue():
            while not log_queue.empty():
                self.download_listbox.insert(tk.END, log_queue.get())
            self.download_listbox.after(100, process_log_queue)

        def download_piece_thread(i):
            for peer in peers:
                host = peer["host"]
                port = peer["port"]
                log(f"📥 Tải piece {i} - {host}:{port}")
                data = self.download_piece_from_peer(host, port, file_name, i)
                if data is None:
                    continue

                hash_val = self.sha1_hash(data)
                if hash_val == pieces_hash[i]:
                    downloaded_pieces[i] = data
                    piece_filename = f"{i}_{file_name}.chunk"
                    piece_path = os.path.join(self.chunkdir, piece_filename)
                    with open(piece_path, 'wb') as piece_file:
                        piece_file.write(data)
                    
                    log(f"✅ Piece {i} đã được xác thực từ {host}:{port}")
                    return
                else:
                    log(f"⚠️ Piece {i} sai hash - {host}:{port}")

            log(f"❌ Không thể tải piece {i} từ bất kỳ peer nào.")

        # Bắt đầu tải - mỗi pieces tương đương với 1 thread
        threads = []
        for i in range(num_pieces):
            t = threading.Thread(target=download_piece_thread, args=(i,))
            t.start()
            threads.append(t)

        process_log_queue()  # Bắt đầu xử lý log từ queue

        def wait_for_completion():
            if any(t.is_alive() for t in threads):
                self.download_listbox.after(200, wait_for_completion)
            else:
                # Khi tất cả thread đã xong
                if None in downloaded_pieces:
                    for i, piece in enumerate(downloaded_pieces):
                        if piece is None:
                            self.download_listbox.insert(tk.END, f"❌ Thiếu piece {i}, file không hoàn chỉnh.")
                    return

                os.makedirs(self.download_dir, exist_ok=True)
                file_path = os.path.join(self.download_dir, file_name)
                with open(file_path, "wb") as f:
                    for piece in downloaded_pieces:
                        f.write(piece)

                self.download_listbox.insert(tk.END, f"🎉 Tải file {file_name} hoàn tất và lưu tại {file_path}")
                
                metainfo = {
                    "file_name": file_name,
                    "file_size": file_info["file_size"],
                    "piece_length": PIECE_SIZE,
                    "num_pieces": len(downloaded_pieces),
                    "pieces": []
                }
                self.notify_tracker(metainfo)


        wait_for_completion()

# Khởi động giao diện
if __name__ == "__main__":
    root = tk.Tk()
    app = P2PGUI(root)
    root.mainloop()
