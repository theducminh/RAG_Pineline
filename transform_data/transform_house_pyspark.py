# transform_data/transform_house_pyspark.py

import pandas as pd
import os

def clean_house(raw_path):
    if not raw_path or not os.path.exists(raw_path):
        return None
        
    df = pd.read_csv(raw_path)
    
    # 1. Xử lý số liệu: Chuyển giá sang triệu đồng và tính đơn giá/m2
    df["price_million"] = df["price"] / 1_000_000
    df["price_per_m2"] = df["price"] / df["area"]
    
    # 2. Xử lý text: Điền giá trị mặc định cho các trường quan trọng
    cols_to_fix = ["project_name", "house_direction", "legal_status", "street_name"]
    for col in cols_to_fix:
        if col in df.columns:
            df[col] = df[col].fillna("Không xác định")

    # 3. TẠO NỘI DUNG CHO AI (AI Context)
    # Đây là chuỗi văn bản mà model Embedding sẽ đọc để hiểu giá trị căn nhà
    df["ai_summary"] = (
        "Bất động sản: " + df["title"] + ". " +
        "Loại hình: " + df["property_type_name"] + ". " +
        "Địa chỉ: " + df["street_name"] + ", " + df["ward_name"] + ", " + df["district_name"] + ". " +
        "Diện tích: " + df["area"].astype(str) + "m2. " +
        "Giá: " + df["price_million"].astype(str) + " triệu. " +
        "Thông tin thêm: " + df["bedroom_count"].astype(str) + " PN, hướng " + df["house_direction"] + 
        ", pháp lý " + df["legal_status"] + ". " +
        "Mô tả chi tiết: " + df["description"].fillna("")
    ).str.slice(0, 1000) # Giới hạn độ dài để model Embedding chạy nhanh

    clean_path = raw_path.replace("raw_", "clean_")
    df.to_csv(clean_path, index=False, encoding="utf-8")
    print(f"✅ Transform hoàn tất: {clean_path}")
    return clean_path