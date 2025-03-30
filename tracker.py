import socket
import threading
import json

peers = {}

def handle_client(conn, addr):
    global peers
    print(f"[+] Peer {addr} connected.")

    while True:
        try:
            data = conn.recv(1024).decode()
            if not data:
                break
            request = json.loads(data)

            if request["action"] == "register":
                peer_ip = addr[0]
                peer_port = request["port"]
                file_list = request["files"]
                peers[(peer_ip, peer_port)] = file_list
                conn.send(json.dumps({"status": "registered"}).encode())

            elif request["action"] == "find":
                filename = request["filename"]
                available_peers = [
                    (ip, port) for (ip, port), files in peers.items() if filename in files
                ]
                conn.send(json.dumps({"peers": available_peers}).encode())

        except:
            break

    print(f"[-] Peer {addr} disconnected.")
    conn.close()

def start_tracker():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", 6000))
    server.listen(5)
    print("[TRACKER] Server is running on port 5000...")

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr)).start()

start_tracker()
