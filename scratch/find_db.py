import os

for root, dirs, files in os.walk('/home/immanuels/Desktop/mri-int'):
    if 'node_modules' in root or '.git' in root or 'venv' in root:
        continue
    for file in files:
        if file.endswith('.db') or file.endswith('.sqlite') or file.endswith('.sqlite3') or file.endswith('.parquet'):
            path = os.path.join(root, file)
            print(f"Found DB/Parquet: {path} ({os.path.getsize(path)/1024/1024:.2f} MB)")
