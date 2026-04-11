import os
import csv
import requests
import time
from dotenv import load_dotenv

# 1. Luôn để sát lề trái, không thụt lề cho các dòng khai báo đầu file
load_dotenv()

def get_embedding(text):
    """
    Sửa lỗi 400: Chỉ định rõ Task Feature Extraction cho Router.
    """
    # URL Router chuẩn
    API_URL = "https://router.huggingface.co/hf-inference/models/sentence-transformers/all-MiniLM-L6-v2"
    
    token = os.getenv("HUGGINGFACE_API_KEY")
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Wait-For-Model": "true" # Ép đợi nếu model đang khởi động
    }
    
    # CHỈNH: Đưa vào cấu trúc inputs chuẩn cho Feature Extraction
    payload = {
        "inputs": text,
        "parameters": {} # Đảm bảo không bị hiểu lầm sang Task khác
    }
    
    try:
        # Thêm timeout dài hơn một chút vì Router điều hướng có thể mất thời gian
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            # Router thường trả về mảng 1D hoặc 2D tùy Provider, mình bóc tách ra
            if isinstance(result, list):
                if len(result) > 0 and isinstance(result[0], list):
                    return result[0]
                return result
            return result
        else:
            print(f"❌ API Error {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Lỗi kết nối: {e}")
        return None

def load_to_supabase(csv_path, table="fact_house_listings"):
    """
    Đọc dữ liệu đã clean, tạo vector qua API và nạp lên Supabase Cloud.
    """
    url = f"{os.getenv('SUPABASE_URL')}/rest/v1/{table}"
    headers = {
        "apikey": os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
        "Authorization": f"Bearer {os.getenv('SUPABASE_SERVICE_ROLE_KEY')}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }

    if not os.path.exists(csv_path):
        print(f"❌ Không tìm thấy file: {csv_path}")
        return None

    with open(csv_path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print(f"🚀 Bắt đầu nạp {len(rows)} bản ghi kèm Vector lên Supabase...")
    
    batch_data = []
    success_count = 0

    for r in rows:
        # 1. Tạo Vector qua API Router
        content = r.get("ai_summary", r.get("title", ""))
        embedding = get_embedding(content)
        
        if not isinstance(embedding, list):
            print(f"⏩ Bỏ qua ID {r['id']} do lỗi tạo Vector.")
            continue

        # 2. Map dữ liệu vào payload chuẩn DB
        payload = {
            "id": int(r["id"]),
            "title": r["title"],
            "description": r["description"],
            "price_million": float(r["price_million"]) if r.get("price_million") else None,
            "area_m2": float(r["area"]) if r.get("area") else None,
            "district_name": r["district_name"],
            "ward_name": r["ward_name"],
            "house_direction": r["house_direction"],
            "legal_status": r["legal_status"],
            "embedding": embedding 
        }
        batch_data.append(payload)
        success_count += 1

        # 3. Gửi batch lên Supabase
        if len(batch_data) >= 15:
            res = requests.post(url, json=batch_data, headers=headers)
            if res.status_code in [200, 201]:
                print(f"✅ Đã nạp thành công {success_count}/{len(rows)} bản ghi...")
            else:
                print(f"❌ Lỗi Supabase: {res.text}")
            batch_data = []
            time.sleep(0.5)

    # Gửi nốt phần còn lại
    if batch_data:
        requests.post(url, json=batch_data, headers=headers)
        
    print(f"🎯 Hoàn tất! Đã nạp thành công {success_count} bản ghi lên Supabase.")
    return True