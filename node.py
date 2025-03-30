import socket
import threading
import hashlib
import random
import time

TRACKER_HOST = "127.0.0.1"
TRACKER_PORT = 6000

class Node:
    def __init__(self, host="0.0.0.0", port=5000):
        self.host = host
        self.port = self.find_available_port(port)
        self.id = self.generate_id()
        self.peers = set()
        self.running = True

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
        """Lấy danh sách các nodes từ tracker và tự động kết nối"""
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
        """Kiểm tra nếu port đã sử dụng, nếu có thì chọn port mới"""
        if port is None:
            port = random.randint(5000, 9000)  # Chọn cổng ngẫu nhiên ban đầu

        while not self.is_port_available(port):  # Nếu port đã dùng, tìm port khác
            port = random.randint(5000, 9000)
        return port

    def is_port_available(self, port):
        """Kiểm tra xem cổng có đang được sử dụng không"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex((self.host, port)) != 0  # Trả về True nếu cổng chưa bị chiếm

    def stop(self):
        """Dừng node"""
        self.running = False
        self.server.close()
        print("[NODE] Shutting down")

if __name__ == "__main__":
    node = Node()
    # Chạy server để nhận file
    while True:
        cmd = input("\n[COMMAND] Nhập lệnh (list, send <host> <port> <message>, exit): ").strip()
        
        if cmd == "list":
            node.get_peers_from_tracker()
        
        elif cmd.startswith("send "):
            parts = cmd.split(" ")
            if len(parts) < 4:
                print("[ERROR] Cú pháp: send <peer_host> <peer_port> <message>")
            else:
                peer_host = parts[1]
                peer_port = parts[2]
                message = " ".join(parts[3:])
                node.send_message(peer_host, peer_port, message)

        elif cmd == "exit":
            print("[NODE] Đang thoát...")
            break

        else:
            print("[ERROR] Lệnh không hợp lệ!")
