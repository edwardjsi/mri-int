import os

def find_large_files(start_path):
    for root, dirs, files in os.walk(start_path):
        if 'node_modules' in root or '.git' in root or 'venv' in root:
            continue
        for file in files:
            path = os.path.join(root, file)
            try:
                size = os.path.getsize(path)
                if size > 10 * 1024 * 1024:  # >10MB
                    print(f"Large file: {path} ({size/1024/1024:.2f} MB)")
            except:
                pass

find_large_files('/home/immanuels/Desktop/mri-int')
