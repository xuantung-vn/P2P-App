import hashlib
import json
import os

def sha1_hash(data):
    return hashlib.sha1(data).hexdigest()

def split_and_hash_file(file_path, piece_length):
    pieces = []
    with open(file_path, 'rb') as f:
        while True:
            piece = f.read(piece_length)
            if not piece:
                break
            pieces.append(sha1_hash(piece))
    return pieces

def create_metainfo(file_path, tracker_url, piece_length=512 * 1024):
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    pieces = split_and_hash_file(file_path, piece_length)

    metainfo = {
        "file_name": file_name,
        "file_size": file_size,
        "piece_length": piece_length,
        "num_pieces": len(pieces),
        "pieces": pieces,
        "tracker": tracker_url
    }

    # Tạo tên file metainfo (dạng .metainfo.json)
    metainfo_filename = file_name + ".metainfo.json"
    with open(metainfo_filename, 'w') as out:
        json.dump(metainfo, out, indent=4)

    print(f"✅ Metainfo file created: {metainfo_filename}")
    return metainfo_filename

# Example usage:
if __name__ == "__main__":
    file_path = input("🔍 Nhập đường dẫn tới file cần chia sẻ: ")
    tracker_url = input("🌐 Nhập tracker URL (vd: http://your-tracker.local/announce): ")
    create_metainfo(file_path, tracker_url)
