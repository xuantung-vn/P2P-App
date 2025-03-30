import socket
import threading
import json
import time
import os

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

def handle_client(client_socket, addr):
    global peers, file_registry
    try:
        data = client_socket.recv(1024).decode().strip()
        print(f"[DEBUG] Nhận lệnh từ {addr}: {data}")  # Log nhận lệnh

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
                    print(f"[WARNING] file_registry[{filename}] không hợp lệ, khởi tạo lại danh sách.")
                    file_registry[filename] = []

                file_registry[filename].append({"peer": peer_id, "host": host, "port": port, "chunks": num_chunks})
                save_json(FILE_DATABASE, file_registry)

                print(f"[DEBUG] file_registry sau cập nhật: {json.dumps(file_registry, indent=4)}")
                client_socket.send(json.dumps({"status": "FILE_UPDATED", "filename": filename}).encode())


        elif isinstance(command, list):  # Xử lý text-based command
            if command[0] == "REGISTER":
                ip, port = command[1], command[2]
                peer_id = f"{ip}:{port}"
                peers[peer_id] = {"ip": ip, "port": port, "status": "connected", "last_seen": time.time()}
                save_json(PEERS_FILE, peers)
                client_socket.send(f"REGISTERED {peer_id}".encode())
            elif command[0] == "LEAVE":
                ip, port = command[1], command[2]
                peer_id = f"{ip}:{port}"
                if peer_id in peers:
                    peers[peer_id]["status"] = "disconnected"
                    peers[peer_id]["last_seen"] = time.time()
                    save_json(PEERS_FILE, peers)
                client_socket.send("LEFT".encode())
            elif command[0] == "GET_PEERS":
                active_peers = [peer for peer, info in peers.items() if info["status"] == "connected"]
                peers_list = ",".join(active_peers) if active_peers else "NO_PEERS"
                client_socket.send(f"PEERS {peers_list}".encode())
            if command[0] == "GET_FILE_SOURCES":
                filename = command[1]
                sources = file_registry.get(filename, [])
                response = json.dumps({"sources": sources})  
                print(f"[DEBUG] Trả về nguồn file: {response}")
                client_socket.send(response.encode())
        else:
            print(f"[ERROR] Không xác định được loại lệnh: {command}")

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