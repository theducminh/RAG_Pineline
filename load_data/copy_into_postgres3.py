import os
import csv
import time
import psycopg2
from psycopg2.extras import execute_values
import json
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

# Đọc cấu hình từ .env
load_dotenv()

def get_embeddings_batch(texts):
    if not texts:
        return []

    token = os.getenv("HUGGINGFACE_API_KEY")
    client = InferenceClient(model="sentence-transformers/all-MiniLM-L6-v2", token=token)
    
    try:
        embeddings = client.feature_extraction(texts)
        if hasattr(embeddings, "tolist"):
            return embeddings.tolist()
        return embeddings
    except Exception as e:
        print(f"❌ Lỗi kết nối HF API: {e}")
        return [None] * len(texts)

def load_to_supabase(csv_path, table="ai_extraction_logs"):
    if not os.path.exists(csv_path):
        print(f"❌ Không tìm thấy file: {csv_path}")
        return None

    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        print("❌ LỖI: Cần bổ sung SUPABASE_DB_URL vào file .env")
        return None

    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    print(f"🚀 Bắt đầu xử lý nạp {len(rows)} bản ghi vào bảng {table} bằng API...")
    
    BATCH_SIZE = 20 
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    # 🚨 ĐÃ ĐƯA is_sell XUỐNG CUỐI CÙNG
    insert_query = f"""
        INSERT INTO {table} (
            source_url, raw_content, extracted_json, confidence_score,
            province_code, district_code, property_type,
            price, area, price_per_m2, status, embedding, is_sell
        ) VALUES %s
        ON CONFLICT (source_url) DO UPDATE SET
            raw_content = EXCLUDED.raw_content,
            extracted_json = EXCLUDED.extracted_json,
            confidence_score = EXCLUDED.confidence_score,
            province_code = EXCLUDED.province_code,
            district_code = EXCLUDED.district_code,
            property_type = EXCLUDED.property_type,
            price = EXCLUDED.price,
            area = EXCLUDED.area,
            price_per_m2 = EXCLUDED.price_per_m2,
            status = EXCLUDED.status,
            embedding = EXCLUDED.embedding,
            is_sell = EXCLUDED.is_sell,
            crawled_at = now();
    """

    success_count = 0

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        
        # 🚨 CHÍNH LÀ TRƯỜNG NÀY ĐƯỢC MANG ĐI EMBEDDING
        texts = [r.get("raw_content", "") for r in batch]
        
        embeddings = get_embeddings_batch(texts)
        
        values = []
        for r, emb in zip(batch, embeddings):
            if not isinstance(emb, list):
                continue
                
            vector_str = json.dumps(emb)
            
            # Định nghĩa các hàm ép kiểu
            def to_float(val): return float(val) if val else None
            def to_str(val): return val.strip() if val and val.strip() else None
            def to_bool(val): return True if str(val).lower() == 'true' else False

            # 🚨 THỨ TỰ ĐÃ CHUẨN 100% VỚI CÂU QUERY (is_sell Ở CUỐI)
            values.append((
                to_str(r.get("source_url")),
                to_str(r.get("raw_content")),
                to_str(r.get("extracted_json")),
                to_float(r.get("confidence_score")),
                to_str(r.get("province_code")),
                to_str(r.get("district_code")), 
                to_str(r.get("property_type")),
                to_float(r.get("price")),
                to_float(r.get("area")),
                to_float(r.get("price_per_m2")),
                to_str(r.get("status")),
                vector_str,                       # embedding
                to_bool(r.get("is_sell"))         # is_sell
            ))
        
        if values:
            try:
                execute_values(cursor, insert_query, values)
                conn.commit()
                success_count += len(values)
                print(f"✅ Đã nạp thành công Batch {i//BATCH_SIZE + 1} ({success_count}/{len(rows)} bản ghi)...")
            except Exception as e:
                conn.rollback()
                print(f"❌ Lỗi SQL tại Batch {i//BATCH_SIZE + 1}: {e}")
        
        time.sleep(1)

    cursor.close()
    conn.close()
    
    if success_count == 0:
        raise RuntimeError(f"❌ CRITICAL: Nạp DB thất bại. Không có bản ghi nào vào Supabase từ file {csv_path}")
    
    print(f"🎯 Hoàn tất! Đã nạp thành công {success_count} bản ghi vào bảng {table}.")
    return True