#!/usr/bin/env python3

import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

def run_tracker():
    # Chạy trực tiếp file main.py của tracker
    os.system("python3 src/tracker/tracker.ui.py")

def run_peer():
    # Chạy trực tiếp file main.py của peer
    os.system("python3 src/peer/peer.ui.py")

def show_help():
    print("Usage:")
    print("  python3 p2p.py tracker   # Run tracker UI")
    print("  python3 p2p.py peer      # Run peer UI")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_help()
        sys.exit(1)

    command = sys.argv[1]

    if command == "tracker":
        run_tracker()
    elif command == "peer":
        run_peer()
    else:
        print(f"Unknown command: {command}")
        show_help()
