# load_data/copy_into_postgres3.py
import os
import csv
import requests
import time
import psycopg2
from psycopg2.extras import execute_values
import json
from dotenv import load_dotenv

# Đọc cấu hình từ .env
load_dotenv()

from huggingface_hub import InferenceClient

def get_embeddings_batch(texts):
    """
    Sử dụng InferenceClient chuẩn của Hugging Face. 
    Chống chết yểu khi API endpoint thay đổi và xịn hơn trong việc quản lý connection.
    """
    if not texts:
        return []

    token = os.getenv("HUGGINGFACE_API_KEY")
    
    # Khởi tạo Client bám thẳng vào Model, kệ xác router bên dưới nó trỏ đi đâu
    client = InferenceClient(model="sentence-transformers/all-MiniLM-L6-v2", token=token)
    
    try:
        # Gọi thẳng feature_extraction, client tự động parse payload
        embeddings = client.feature_extraction(texts)
        
        # Parse về chuẩn list of floats để đẩy xuống db psycopg2
        if hasattr(embeddings, "tolist"):
            return embeddings.tolist()
        return embeddings
        
    except Exception as e:
        print(f"❌ Lỗi kết nối HF Hub: {e}")
        return [None] * len(texts)


def load_to_supabase(csv_path, table="fact_house_listings"):
    """
    Đọc dữ liệu, tạo vector theo lô (batch) và dùng psycopg2 Bulk Insert.
    """
    if not os.path.exists(csv_path):
        print(f"❌ Không tìm thấy file: {csv_path}")
        return None

    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        print("❌ LỖI: Cần bổ sung SUPABASE_URL vào file .env")
        return None

    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    print(f"🚀 Bắt đầu xử lý nạp {len(rows)} bản ghi...")
    
    BATCH_SIZE = 100
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    # Query chuẩn bị cho Bulk Insert (sử dụng UPSERT để tránh lỗi trùng ID)
    insert_query = f"""
        INSERT INTO {table} (
            id, title, description, price, price_million, area_m2, price_per_m2, 
            region, district, ward, street, lat, lng, property_type, 
            post_time, images_count, vector_embedding
        ) VALUES %s
        ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            price_million = EXCLUDED.price_million,
            area_m2 = EXCLUDED.area_m2,
            price_per_m2 = EXCLUDED.price_per_m2,
            vector_embedding = EXCLUDED.vector_embedding;
    """

    success_count = 0

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        
        # 1. Trích xuất text để nhét vào mồm API
        texts = [r.get("ai_summary", r.get("title", "")) for r in batch]
        
        # 2. Gọi API lấy Vector nguyên 1 cục
        embeddings = get_embeddings_batch(texts)
        
        # 3. Chế biến data map đúng với Schema CSDL
        values = []
        for r, emb in zip(batch, embeddings):
            if not isinstance(emb, list):
                continue
                
            # pgvector nhận dữ liệu ở dạng chuỗi mảng JSON (vd: "[0.1, 0.2, ...]")
            vector_str = json.dumps(emb)
            
            # Helper xử lý ép kiểu tránh tạch DB
            def to_float(val): return float(val) if val else None
            def to_int(val): return int(float(val)) if val else None

            values.append((
                str(r.get("id")),
                r.get("title"),
                r.get("description"),
                to_float(r.get("price")),
                to_float(r.get("price_million")),
                to_float(r.get("area")),
                to_float(r.get("price_per_m2")),
                r.get("province_name"),   # region
                r.get("district_name"),   # district
                r.get("ward_name"),       # ward
                r.get("street_name"),     # street
                to_float(r.get("lat")),
                to_float(r.get("lng")),
                r.get("property_type_name"),
                r.get("published_at"),    # post_time
                to_int(r.get("images_count")),
                vector_str                # vector_embedding
            ))
        
        # 4. Bơm Bulk Insert vào Supabase
        if values:
            try:
                execute_values(cursor, insert_query, values)
                conn.commit()
                success_count += len(values)
                print(f"✅ Đã nạp nhanh {success_count}/{len(rows)} bản ghi...")
            except Exception as e:
                conn.rollback()
                print(f"❌ Lỗi tại Batch {i}: {e}")
        
        # Nghỉ nửa giây tránh bị Hugging Face block do spam
        time.sleep(0.5) 

    cursor.close()
    conn.close()
    if success_count == 0:
        raise RuntimeError(f"❌ CRITICAL: Nạp DB thất bại toàn tập. Không có bản ghi nào vào Supabase từ file {csv_path}")
    print(f"🎯 Hoàn tất! Đã nạp thành công {success_count} bản ghi bằng Bulk Insert.")
    return True

if __name__ == '__main__':
    # load_to_supabase("data_input/house/2026-04-17/clean_1776361924.csv")
    pass