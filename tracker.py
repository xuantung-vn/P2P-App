import socket
import threading

# Danh sách các nodes
peers = {}

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
            peers[peer_id] = True
            client_socket.send(f"REGISTERED {peer_id}".encode())

        elif command[0] == "GET_PEERS":
            peers_list = ",".join(peers.keys())
            client_socket.send(f"PEERS {peers_list}".encode())

        elif command[0] == "LEAVE":
            ip, port = command[1], command[2]
            peer_id = f"{ip}:{port}"
            if peer_id in peers:
                del peers[peer_id]
            client_socket.send("LEFT".encode())

    except Exception as e:
        print(f"[ERROR] {e}")

    finally:
        client_socket.close()

def start_tracker():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", 6000))
    server.listen(5)
    print("[TRACKER] Server is running on port 5000...")

    while True:
        client_sock, addr = server.accept()
        threading.Thread(target=handle_client, args=(client_sock, addr)).start()

if __name__ == "__main__":
    start_tracker()
