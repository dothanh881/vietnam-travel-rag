#!/usr/bin/env python3
"""
scripts/setup.py - First-run setup script
Chạy lần đầu khi clone project: python scripts/setup.py

Tự động:
1. Kiểm tra Qdrant đang chạy
2. Nếu collection chưa tồn tại -> restore từ snapshot
3. In hướng dẫn bước tiếp theo
"""
import sys
import time
import requests
from pathlib import Path

QDRANT_URL = "http://localhost:6333"
COLLECTION = "travel_knowledge_base"
SNAPSHOT_DIR = Path(__file__).parent.parent / "infra" / "snapshots"

def wait_for_qdrant(timeout=30):
    """Chờ Qdrant sẵn sàng."""
    print("[INFO] Dang doi Qdrant khoi dong...")
    for i in range(timeout):
        try:
            r = requests.get(f"{QDRANT_URL}/healthz", timeout=2)
            if r.status_code == 200:
                print("[OK] Qdrant san sang!")
                return True
        except Exception:
            pass
        time.sleep(1)
        print(f"  ... {i+1}s", end="\r")
    return False

def collection_exists():
    try:
        r = requests.get(f"{QDRANT_URL}/collections/{COLLECTION}", timeout=5)
        return r.status_code == 200
    except Exception:
        return False

def restore_snapshot(snapshot_path: Path):
    print(f"[INFO] Dang restore snapshot: {snapshot_path.name}")
    with open(snapshot_path, "rb") as f:
        r = requests.post(
            f"{QDRANT_URL}/collections/{COLLECTION}/snapshots/upload?priority=snapshot",
            files={"snapshot": (snapshot_path.name, f, "application/octet-stream")},
            timeout=120
        )
    if r.status_code in (200, 201):
        print(f"[OK] Restore thanh cong!")
        return True
    else:
        print(f"[ERROR] Restore that bai: {r.text}")
        return False

# === MAIN ===
print("=" * 50)
print("  Travel Agent - First Run Setup")
print("=" * 50)

# 1. Kiem tra Qdrant
if not wait_for_qdrant():
    print("\n[ERROR] Qdrant khong phan hoi sau 30s.")
    print("  -> Hay chay: docker compose -f infra/docker-compose.yaml up -d")
    print("  -> Roi chay lai script nay.")
    sys.exit(1)

# 2. Kiem tra collection da ton tai chua
if collection_exists():
    count = requests.get(f"{QDRANT_URL}/collections/{COLLECTION}").json()
    points = count.get("result", {}).get("points_count", "?")
    print(f"[OK] Collection '{COLLECTION}' da ton tai ({points} diem). Bo qua restore.")
else:
    # Tim snapshot moi nhat
    snapshots = sorted(SNAPSHOT_DIR.glob("*.snapshot"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not snapshots:
        print(f"\n[ERROR] Khong tim thay file .snapshot trong {SNAPSHOT_DIR}")
        print("  -> Lien he tac gia de lay file snapshot.")
        sys.exit(1)
    
    latest = snapshots[0]
    print(f"[INFO] Tim thay snapshot: {latest.name} ({latest.stat().st_size/1024/1024:.1f} MB)")
    
    if not restore_snapshot(latest):
        sys.exit(1)

print("\n" + "=" * 50)
print("  Setup hoan tat! Buoc tiep theo:")
print("=" * 50)
print("  1. Kiem tra file backend/.env (them API keys can thiet)")
print("  2. cd backend && python main.py")
print("  3. cd frontend && npm run dev")
print("  4. Truy cap: http://localhost:3000")
