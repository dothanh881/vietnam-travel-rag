#!/usr/bin/env python3
"""
scripts/export_snapshot.py
Tạo Qdrant snapshot và lưu vào infra/snapshots/ để commit vào repo.
Chạy 1 lần khi có data mới: python scripts/export_snapshot.py
"""
import os
import sys
import shutil
import requests
from pathlib import Path

QDRANT_URL = "http://localhost:6333"
COLLECTION = "travel_knowledge_base"
SNAPSHOT_DIR = Path(__file__).parent.parent / "infra" / "snapshots"

SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

print(f"[INFO] Dang tao snapshot cho collection '{COLLECTION}'...")

# 1. Tao snapshot
r = requests.post(f"{QDRANT_URL}/collections/{COLLECTION}/snapshots")
if r.status_code != 200:
    print(f"[ERROR] Khong the tao snapshot: {r.text}")
    sys.exit(1)

snapshot_name = r.json()["result"]["name"]
print(f"[OK] Snapshot da tao: {snapshot_name}")

# 2. Download snapshot file tu Qdrant container
download_url = f"{QDRANT_URL}/collections/{COLLECTION}/snapshots/{snapshot_name}"
dest_path = SNAPSHOT_DIR / snapshot_name

print(f"[INFO] Dang tai snapshot ve: {dest_path}")
with requests.get(download_url, stream=True) as resp:
    resp.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

size_mb = dest_path.stat().st_size / 1024 / 1024
print(f"[DONE] Snapshot da luu: {dest_path} ({size_mb:.1f} MB)")
print(f"\nBuoc tiep theo:")
print(f"  git add infra/snapshots/{snapshot_name}")
print(f"  git commit -m 'chore: update qdrant snapshot'")
print(f"  git push")
