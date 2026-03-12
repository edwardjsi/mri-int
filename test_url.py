from urllib.parse import urlparse
url = "postgresql://user:pass@host/neondb?sslmode=require"
parsed = urlparse(url)
print(f"Path: '{parsed.path}'")
print(f"DB Name: '{parsed.path.lstrip('/')}'")
