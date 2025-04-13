# tracker_utils.py
import socket
import json
import threading

TRACKER_IP = "127.0.0.1"
TRACKER_PORT = 6000

def get_file_sources(filename):
    try:
        s = socket.socket()
        s.connect((TRACKER_IP, TRACKER_PORT))
        message = f"GET_FILE_SOURCES {filename}"
        s.send(message.encode())
        data = s.recv(4096).decode()
        s.close()

        json_data = json.loads(data)
        return json_data.get("sources", [])
    except Exception as e:
        print(f"[ERROR] Lỗi khi lấy nguồn file: {e}")
        return []

# Demo tải file song song (giả lập)
def download_file_multithreaded(filename):
    sources = get_file_sources(filename)
    if not sources:
        return False

    def fake_download(peer_info):
        print(f"[INFO] Đang tải từ {peer_info['peer']} ...")
        # ở đây bạn có thể mở socket đến peer_info["host"], tải mảnh...
        # hoặc gọi hàm thật xử lý chunk
        import time
        time.sleep(1)

    threads = []
    for src in sources:
        t = threading.Thread(target=fake_download, args=(src,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    return True
