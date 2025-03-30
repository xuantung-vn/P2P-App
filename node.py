import socket
import threading
import hashlib
import random

class Node:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.id = self.generate_id()
        self.peers = set()
        self.running = True

        # Tạo socket server
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((self.host, self.port))
        self.server.listen(5)

        print(f"[NODE] Running on {self.host}:{self.port} with ID {self.id}")

        # Bắt đầu luồng lắng nghe kết nối
        threading.Thread(target=self.listen_for_peers, daemon=True).start()
    
    def generate_id(self):
        """Tạo ID duy nhất cho node"""
        hash_obj = hashlib.sha256()
        random_data = f"{self.host}{self.port}{random.randint(1, 99999999)}"
        hash_obj.update(random_data.encode('utf-8'))
        return hash_obj.hexdigest()
    
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
            conn.connect((peer_host, peer_port))
            self.peers.add((peer_host, peer_port))
            print(f"[NODE] Connected to {peer_host}:{peer_port}")
            return conn
        except Exception as e:
            print(f"[ERROR] Could not connect to peer {peer_host}:{peer_port} - {e}")
            return None

    def send_message(self, conn, message):
        """Gửi tin nhắn đến một peer đã kết nối"""
        try:
            conn.sendall(message.encode())
        except Exception as e:
            print(f"[ERROR] {e}")

    def stop(self):
        """Dừng node"""
        self.running = False
        self.server.close()
        print("[NODE] Shutting down")

if __name__ == "__main__":
    node = Node("127.0.0.1", 5001)  # Chạy node trên cổng 5001
