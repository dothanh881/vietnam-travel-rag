"""
migrate_qdrant.py - Di chuyển data từ Qdrant Cloud sang Qdrant Local
Chạy: python migrate_qdrant.py

Yêu cầu:
- Qdrant local đang chạy tại http://localhost:6333
- Các biến môi trường QDRANT_URL và QDRANT_API_KEY trong .env
"""
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams, Distance, SparseVectorParams, SparseIndexParams,
    PayloadSchemaType, PointStruct, SparseVector
)

# Tìm file .env trong thư mục backend/
script_dir = Path(__file__).parent
env_path = script_dir / "backend" / ".env"
if not env_path.exists():
    env_path = script_dir / ".env"

load_dotenv(dotenv_path=env_path)
print(f"[INFO] Doc .env tu: {env_path}")

CLOUD_URL = os.getenv("QDRANT_URL")
CLOUD_KEY  = os.getenv("QDRANT_API_KEY")
LOCAL_URL  = "http://localhost:6333"
COLLECTION = "travel_knowledge_base"
BATCH_SIZE = 50

if not CLOUD_URL or "localhost" in CLOUD_URL:
    print(f"[ERROR] QDRANT_URL khong hop le hoac dang tro ve localhost: '{CLOUD_URL}'")
    print("   Hay kiem tra file backend/.env co dong QDRANT_URL=https://...")
    sys.exit(1)

print(f"=== Qdrant Migration Tool ===")
print(f"Nguon  : {CLOUD_URL}")
print(f"Dich   : {LOCAL_URL}")
print(f"Collection: {COLLECTION}")
print()

# Ket noi Cloud
try:
    cloud = QdrantClient(url=CLOUD_URL, api_key=CLOUD_KEY, timeout=30)
    info = cloud.get_collection(COLLECTION)
    total_points = info.points_count
    print(f"[OK] Ket noi Cloud thanh cong | Tong so diem: {total_points:,}")
except Exception as e:
    print(f"[ERROR] Loi ket noi Cloud: {e}")
    sys.exit(1)

# Ket noi Local
try:
    local = QdrantClient(url=LOCAL_URL, timeout=10)
    print(f"[OK] Ket noi Local thanh cong")
except Exception as e:
    print(f"[ERROR] Loi ket noi Local: {e}")
    print("   -> Hay dam bao Docker Desktop dang chay va Qdrant container da duoc start!")
    sys.exit(1)

# Kiem tra/tao collection o Local
existing = [c.name for c in local.get_collections().collections]
if COLLECTION in existing:
    ans = input(f"\n[WARN] Collection '{COLLECTION}' da ton tai o Local. Xoa va tao lai? (y/N): ")
    if ans.lower() == 'y':
        local.delete_collection(COLLECTION)
        print(f"[INFO] Da xoa collection cu.")
    else:
        print("Huy migrate.")
        sys.exit(0)

# Lay config tu Cloud de tao collection y het
vectors_config = info.config.params.vectors
sparse_config  = info.config.params.sparse_vectors

local.create_collection(
    collection_name=COLLECTION,
    vectors_config=vectors_config,
    sparse_vectors_config=sparse_config
)
local.create_payload_index(COLLECTION, "destination", PayloadSchemaType.KEYWORD)
local.create_payload_index(COLLECTION, "category",    PayloadSchemaType.KEYWORD)
print(f"[OK] Da tao collection '{COLLECTION}' o Local")

# Migrate theo batch dung scroll API
print(f"\n[INFO] Bat dau migrate {total_points:,} diem (batch={BATCH_SIZE})...")
offset = None
migrated = 0
t0 = time.time()

while True:
    records, next_offset = cloud.scroll(
        collection_name=COLLECTION,
        limit=BATCH_SIZE,
        offset=offset,
        with_payload=True,
        with_vectors=True
    )

    if not records:
        break

    points = []
    for rec in records:
        vector_dict = {}
        if isinstance(rec.vector, dict):
            for name, vec in rec.vector.items():
                if isinstance(vec, dict):
                    vector_dict[name] = SparseVector(
                        indices=vec.get("indices", []),
                        values=vec.get("values", [])
                    )
                else:
                    vector_dict[name] = vec
        else:
            vector_dict = rec.vector

        points.append(PointStruct(
            id=rec.id,
            vector=vector_dict,
            payload=rec.payload
        ))

    local.upsert(collection_name=COLLECTION, points=points)
    migrated += len(records)

    elapsed = time.time() - t0
    pct = (migrated / total_points * 100) if total_points > 0 else 0
    speed = migrated / elapsed if elapsed > 0 else 0
    print(f"  [{pct:5.1f}%] {migrated:,}/{total_points:,} diem | {speed:.1f} pts/s", end="\r")

    if next_offset is None:
        break
    offset = next_offset

print(f"\n\n[DONE] Migrate hoan tat! {migrated:,} diem trong {time.time()-t0:.1f}s")
print(f"\nBuoc tiep theo: Sua file backend/.env")
print(f"  Thay:  QDRANT_URL=\"{CLOUD_URL}\"")
print(f"  Bang:  QDRANT_URL=\"http://localhost:6333\"")
print(f"  Va xoa hoac de trong: QDRANT_API_KEY=")
