import socket
import threading
import hashlib
import random
import time
import json
import os

TRACKER_HOST = "127.0.0.1"  # IP của tracker
TRACKER_PORT = 6000         # Cổng của tracker
NODE_PORT = 7000            # Cổng lắng nghe của node
CHUNK_SIZE = 512 * 1024     # 512KB
CHUNK_DIR = "chunks"       # Thư mục lưu các chunk
NODE_DIR = "nodes"

DOWNLOAD_FOLDER = "downloads"

# Tạo thư mục lưu file nếu chưa có
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

class Node:
    def __init__(self, host="0.0.0.0", port=5000):
        self.host = host
        self.port = self.find_available_port(port)
        self.id = self.generate_id()
        self.peers = set()
        self.running = True
        
        # Tạo thư mục riêng cho node
        self.node_dir = os.path.join(NODE_DIR, self.id)
        if not os.path.exists(self.node_dir):
            os.makedirs(self.node_dir)

        # Tạo socket server
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((self.host, self.port))
        self.server.listen(5)

        print(f"[NODE] Running on {self.host}:{self.port} with ID {self.id}")

        # Đăng ký với tracker
        self.register_with_tracker()

        # Lấy danh sách nodes từ tracker
        self.get_peers_from_tracker()

        # Bắt đầu luồng lắng nghe kết nối
        threading.Thread(target=self.listen_for_peers, daemon=True).start()
    
    def generate_id(self):
        """Tạo ID ngắn gọn cho node"""
        hash_obj = hashlib.sha256()
        random_data = f"{self.host}{self.port}{random.randint(1, 99999999)}"
        hash_obj.update(random_data.encode('utf-8'))
        return hash_obj.hexdigest()[:8]  # Lấy 8 ký tự đầu của SHA-256
    
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
        self.peers.add(addr)
        while True:
            try:
                data = conn.recv(1024).decode()
                if not data:
                    break
                if data.startswith("UPLOAD"):
                    _, filename, chunk_number = data.split()
                    self.receive_chunk(conn, filename, int(chunk_number))
                print(f"[MESSAGE FROM {addr}] {data}")
            except:
                break
        conn.close()
        self.peers.remove(addr)
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
            print(f"[ERROR] Could not connect to peer {peer_host}:{peer_port} - {e}")
            return None

    def send_message(self, peer_host, peer_port, message):
        """Gửi tin nhắn đến một peer"""
        conn = self.connect_to_peer(peer_host, peer_port)
        if conn:
            try:
                conn.sendall(message.encode())
                conn.close()
            except Exception as e:
                print(f"[ERROR] {e}")

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

    def get_peers_from_tracker(self):
        """Lấy danh sách các nodes từ tracker"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((TRACKER_HOST, TRACKER_PORT))
                s.send("GET_PEERS".encode())
                response = s.recv(1024).decode()
                print("[TRACKER] Danh sách nodes:", response)
                if response.startswith("PEERS "):
                    peers_list = response[6:].split(",")
                    for peer in peers_list:
                        if peer and ":" in peer:
                            peer_host, peer_port = peer.split(":")
                            if peer_host != self.host or int(peer_port) != self.port:
                                self.connect_to_peer(peer_host, peer_port)
        except Exception as e:
            print(f"[ERROR] Could not get peers from tracker: {e}")
    
    def find_available_port(self, port=5000):
        """Tìm cổng trống"""
        while not self.is_port_available(port):
            port = random.randint(5000, 5010)
        return port

    def is_port_available(self, port):
        """Kiểm tra cổng có trống không"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex((self.host, port)) != 0
    def upload_file(self, filename):
        """Lưu file thành các chunk và thông báo tracker"""
        if not os.path.exists(filename):
            print(f"[ERROR] File {filename} không tồn tại.")
            return
        
        file_basename = os.path.basename(filename)  # Lấy tên file, bỏ đường dẫn
        chunks = []
        with open(filename, "rb") as f:
            chunk_number = 0
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                chunk_filename = f"{file_basename}.chunk{chunk_number}"  # Tạo tên file chunk
                chunk_path = os.path.join(self.node_dir, chunk_filename)  # Lưu vào thư mục của node
                with open(chunk_path, "wb") as chunk_file:
                    chunk_file.write(chunk)
                chunks.append(chunk_filename)
                print(f"[UPLOAD] Đã lưu chunk {chunk_number} tại {chunk_path}")
                chunk_number += 1
        
        # Thông báo tracker rằng node này giữ file
        self.notify_tracker(file_basename, chunk_number)
        self.notify_peers(file_basename, chunk_number)
        
    def notify_tracker(self, filename, num_chunks):
        """Thông báo tracker rằng node đang giữ file"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((TRACKER_HOST, TRACKER_PORT))
                message = json.dumps({"action": "FILE_AVAILABLE", "node": self.id, "filename": filename, "chunks": num_chunks})
                s.send(message.encode())
                response = s.recv(1024).decode()
                print("[TRACKER] Response:", response)

        except Exception as e:
            print(f"[ERROR] Không thể thông báo tracker: {e}")
    def notify_peers(self, filename, num_chunks):
        """Gửi thông báo cho các peer rằng file đã được tải lên"""
        for peer in self.peers:
            try:
                peer_host, peer_port = peer  # Lấy host và port từ tuple
                peer_port = int(peer_port)  # Chuyển port thành số nguyên

                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((peer_host, peer_port))
                    message = f"NEW_FILE {filename} {num_chunks}"
                    s.send(message.encode())
                    print(f"[PEER] Đã thông báo {peer} về file {filename}")
            except Exception as e:
                print(f"[ERROR] Không thể thông báo {peer}: {e}")
    def receive_chunk(self, conn, filename, chunk_number):
        """Nhận và lưu chunk vào thư mục riêng của node"""
        chunk_path = os.path.join(self.node_dir, f"{filename}.chunk{chunk_number}")
        with open(chunk_path, "wb") as f:
            while True:
                data = conn.recv(CHUNK_SIZE)
                if not data:
                    break
                f.write(data)
        print(f"[RECEIVED] Đã lưu {filename} chunk {chunk_number} tại {self.node_dir}")
        
    def send_request(self, command):
        """Gửi lệnh đến tracker và nhận phản hồi."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
                client.connect((self.tracker_host, self.tracker_port))
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
            ip, port = peer.split(":")
            print(f"[INFO] Đang tải {filename} từ {peer}")

            for chunk in range(num_chunks):
                self.download_chunk(ip, int(port), filename, chunk)
    def download_chunk(self, ip, port, filename, chunk):
        """Yêu cầu tải một phần file từ peer."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
                client.connect((ip, port))
                client.send(f"DOWNLOAD {filename} {chunk}".encode())

                with open(f"{self.node_dir}/{filename}_part{chunk}", "wb") as f:
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
        output_path = os.path.join(self.node_dir, filename)
        with open(output_path, "wb") as output_file:
            for chunk_number in range(num_chunks):
                chunk_path = os.path.join(self.node_dir, f"{filename}_part{chunk_number}")
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
        self.running = False
        self.server.close()
        print("[NODE] Shutting down")

if __name__ == "__main__":
    node = Node()
    while True:
        cmd = input("\n[COMMAND] list, upload <file>, exit: ").strip()
        if cmd == "list":
            node.get_peers_from_tracker()
        elif cmd.startswith("u "):
            parts = cmd.split(" ")
            node.upload_file(parts[1])
        elif cmd.startswith("s "):
            parts = cmd.split(" ")
            if len(parts) < 4:
                print("[ERROR] Cú pháp: send <peer_host> <peer_port> <message>")
            else:
                peer_host = parts[1]
                peer_port = parts[2]
                message = " ".join(parts[3:])
                node.send_message(peer_host, peer_port, message)
        elif cmd.startswith("d "):
            parts = cmd.split(" ")
            filename = parts[1]
            node.download_file(filename)
        elif cmd == "exit":
            print("[NODE] Đang thoát...")
            node.stop()
            break
        else:
            print("[ERROR] Lệnh không hợp lệ!")
