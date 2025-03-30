import socket
import threading
import json
import time

# File lưu thông tin nodes
PEERS_FILE = "peers.json"

# Đọc dữ liệu từ file JSON (nếu có)
def load_peers():
    try:
        with open(PEERS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# Lưu dữ liệu vào file JSON
def save_peers():
    try:
        with open(PEERS_FILE, "w") as f:
            json.dump(peers, f, indent=4)
    except Exception as e:
        print(f"[ERROR] Lưu peers thất bại: {e}")

# Danh sách các nodes (tải từ file nếu có)
peers = load_peers()

def handle_client(client_socket, addr):
    global peers
    try:
        data = client_socket.recv(1024).decode().strip()
        if not data:
            return

        command = data.split(" ")
        
        if command[0] == "REGISTER":
            ip, port = command[1], command[2]
            peer_id = f"{ip}:{port}"
            peers[peer_id] = {"ip": ip, "port": port, "status": "connected", "last_seen": time.time()}
            save_peers()
            client_socket.send(f"REGISTERED {peer_id}".encode())

        elif command[0] == "GET_PEERS":
            active_peers = [peer for peer, info in peers.items() if info["status"] == "connected"]
            peers_list = ",".join(active_peers) if active_peers else "NO_PEERS"
            client_socket.send(f"PEERS {peers_list}".encode())

        elif command[0] == "LEAVE":
            ip, port = command[1], command[2]
            peer_id = f"{ip}:{port}"
            if peer_id in peers:
                peers[peer_id]["status"] = "disconnected"
                peers[peer_id]["last_seen"] = time.time()
                save_peers()
            client_socket.send("LEFT".encode())

    except Exception as e:
        print(f"[ERROR] {e}")

    finally:
        client_socket.close()

def start_tracker():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", 6000))
    server.listen(5)
    print("[TRACKER] Server is running on port 6000...")

    while True:
        client_sock, addr = server.accept()
        threading.Thread(target=handle_client, args=(client_sock, addr)).start()

if __name__ == "__main__":
    start_tracker()
