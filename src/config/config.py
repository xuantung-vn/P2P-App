# config/config.py

# Thông tin về tracker
TRACKER_URL = "http://your-tracker-url.local"
TRACKER_PORT = 8080
TRACKER_PROTOCOL = "http"

# Thông tin về torrent
DOWNLOAD_DIRECTORY = "./downloads"
TIMEOUT = 30  # Thời gian chờ kết nối

PEER_PORT = 6881
MAX_CONNECTIONS = 10


TRACKER_HOST = "127.0.0.1"  # IP của tracker
NODE_PORT = 7000            # Cổng lắng nghe của node
CHUNK_SIZE = 512 * 1024     # 512KB
CHUNK_DIR = "chunks"       # Thư mục lưu các chunk
NODE_DIR = "nodes"

DOWNLOAD_FOLDER = "downloads"
