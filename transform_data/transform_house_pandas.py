# transform_data/transform_house_pandas.py
import os
import pandas as pd
import csv

def clean_house(raw_path):
    if not raw_path or not os.path.exists(raw_path):
        print(f"❌ Đường dẫn không hợp lệ: {raw_path}")
        return None

    try:
        # 1. Đọc dữ liệu thô
        df = pd.read_csv(raw_path)
        if df.empty:
            return None

        # 2. Loại bỏ ID lỗi và xóa trùng lặp
        df = df.dropna(subset=['id'])
        df = df.drop_duplicates(subset=['id']).sort_values(by='published_at', ascending=False)

        # 3. Transform số liệu
        df['price_million'] = df['price'] / 1000000.0
        df['price_per_m2'] = df['price'] / df['area']

        # 4. Quét và dập lỗi Null (Tránh lỗi lan truyền NaN)
        str_cols = ["title", "property_type_name", "street_name", "ward_name", 
                    "district_name", "house_direction", "legal_status", "description"]
        df[str_cols] = df[str_cols].fillna("Không xác định")

        # Ép kiểu an toàn cho các cột số để đưa vào chuỗi
        df['area_str'] = df['area'].fillna(0).astype(str)
        df['price_str'] = df['price_million'].fillna(0).astype(str)
        
        # Xử lý riêng cột phòng ngủ tránh lỗi ".0" (ví dụ: 2.0 PN)
        df['bed_str'] = df['bedroom_count'].fillna(0).astype(int).astype(str)

        # 5. Tạo AI Context Vector (Gộp chuỗi)
        def build_ai_summary(row):
            summary = (
                f"Bất động sản: {row['title']}. "
                f"Loại hình: {row['property_type_name']}. "
                f"Địa chỉ: {row['street_name']}, {row['ward_name']}, {row['district_name']}. "
                f"Diện tích: {row['area_str']}m2. "
                f"Giá: {row['price_str']} triệu. "
                f"Thông tin thêm: {row['bed_str']} PN, hướng {row['house_direction']}, pháp lý {row['legal_status']}. "
                f"Mô tả chi tiết: {row['description']}"
            )
            return summary[:1000] # Giới hạn token đầu vào cho mô hình Embedding

        df['ai_summary'] = df.apply(build_ai_summary, axis=1)

        # 6. Ghi file
        clean_path = raw_path.replace("raw_", "clean_")
        df.to_csv(clean_path, index=False, quoting=csv.QUOTE_ALL, escapechar='\\')
        
        print(f"✅ Transform Pandas hoàn tất: {clean_path}")
        return clean_path

    except Exception as e:
        print(f"❌ Lỗi khi Transform bằng Pandas: {e}")
        return None