import os
def load_env(filepath=".env"):
    if not os.path.exists(filepath):
        print(f"⚠️ File {filepath} không tồn tại.")
        return

    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()
