# transform_data/transform_house_pandas.py
import os
import sys
import pandas as pd
import csv
import json

# =========================================================
# THIẾT LẬP ĐƯỜNG DẪN TUYỆT ĐỐI (TRÁNH LỖI AIRFLOW DOCKER)
# =========================================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

# =========================================================
# HÀM LÀM SẠCH TÊN ĐỊA LÝ & LOAD MASTER DATA
# =========================================================
def clean_location_name(name):
    """Loại bỏ các tiền tố hành chính để so sánh chuẩn xác"""
    if pd.isna(name): return ""
    name = str(name).strip().lower()
    prefixes = ['thành phố ', 'tỉnh ', 'quận ', 'huyện ', 'thị xã ', 'phường ', 'xã ', 'thị trấn ']
    for p in prefixes:
        if name.startswith(p):
            name = name.replace(p, "", 1)
            break
    return name.strip()

def load_location_dicts(provinces_csv, districts_csv, wards_csv):
    prov_dict, dist_dict, ward_dict = {}, {}, {}

    # 1. Load Provinces
    if os.path.exists(provinces_csv):
        df_p = pd.read_csv(provinces_csv, dtype=str)
        for _, row in df_p.iterrows():
            code = str(row['code']).strip()
            if pd.notna(row['name']): prov_dict[clean_location_name(row['name'])] = code
            if pd.notna(row['full_name']): prov_dict[clean_location_name(row['full_name'])] = code

    # 2. Load Districts
    if os.path.exists(districts_csv):
        df_d = pd.read_csv(districts_csv, dtype=str)
        for _, row in df_d.iterrows():
            code = str(row['code']).strip()
            p_code = str(row['province_code']).strip()
            if pd.notna(row['name']): 
                dist_dict[f"{p_code}_{clean_location_name(row['name'])}"] = code
            if pd.notna(row['full_name']): 
                dist_dict[f"{p_code}_{clean_location_name(row['full_name'])}"] = code

    # 3. Load Wards
    if os.path.exists(wards_csv):
        df_w = pd.read_csv(wards_csv, dtype=str)
        for _, row in df_w.iterrows():
            code = str(row['code']).strip()
            d_code = str(row['district_code']).strip()
            if pd.notna(row['name']): 
                ward_dict[f"{d_code}_{clean_location_name(row['name'])}"] = code
            if pd.notna(row['full_name']): 
                ward_dict[f"{d_code}_{clean_location_name(row['full_name'])}"] = code

    return prov_dict, dist_dict, ward_dict


# Nạp sẵn từ điển
PROV_CSV = os.path.join(PROJECT_ROOT, 'data_input/master_data/provinces.csv')
DIST_CSV = os.path.join(PROJECT_ROOT, 'data_input/master_data/districts.csv')
WARD_CSV = os.path.join(PROJECT_ROOT, 'data_input/master_data/wards.csv')

PROV_DICT, DIST_DICT, WARD_DICT = load_location_dicts(PROV_CSV, DIST_CSV, WARD_CSV)
print(f"📊 Đã tải Master Data: {len(PROV_DICT)} Tỉnh, {len(DIST_DICT)} Quận, {len(WARD_DICT)} Phường.")


def clean_house(raw_path):
    if not raw_path or not os.path.exists(raw_path):
        print(f"❌ Đường dẫn raw_path không tồn tại: {raw_path}")
        return None

    try:
        df = pd.read_csv(raw_path)
        if df.empty: return None
        print(f"🔍 Số dòng ban đầu cào về: {len(df)}")

        df = df.dropna(subset=['id']).drop_duplicates(subset=['id'])

        df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0)
        df['area'] = pd.to_numeric(df['area'], errors='coerce').fillna(0)
        df['price_per_m2'] = df.apply(lambda row: round(row['price'] / row['area'], 2) if row['area'] > 0 else 0.0, axis=1)

        df['source_url'] = df['id'].apply(lambda x: f"https://chotot.com/{x}" if str(x).isdigit() else f"https://huggingface.co/tinixai/{x}")

        def map_property_type(t):
            t_str = str(t).lower()
            if 'chung cư' in t_str or 'căn hộ' in t_str or 'studio' in t_str: return 'APARTMENT'
            if 'đất' in t_str: return 'PLOT'
            return 'HOUSE'
        df['property_type'] = df['property_type_name'].apply(map_property_type)

        # =========================================================
        # MAP ĐỊA CHỈ TỪ CHỮ SANG MÃ CODE
        # =========================================================
        
        # 1. Tỉnh/Thành
        df['province_code'] = df['province_name'].apply(
            lambda x: PROV_DICT.get(clean_location_name(x))
        )
        
        # 2. Quận/Huyện 
        def get_district_code(row):
            if pd.isna(row['province_code']) or pd.isna(row['district_name']): return None
            key = f"{row['province_code']}_{clean_location_name(row['district_name'])}"
            return DIST_DICT.get(key)
        df['district_code'] = df.apply(get_district_code, axis=1)
        
        # 3. Phường/Xã 
        def get_ward_code(row):
            if pd.isna(row['district_code']) or pd.isna(row['ward_name']): return None
            key = f"{row['district_code']}_{clean_location_name(row['ward_name'])}"
            return WARD_DICT.get(key)
        df['ward_code'] = df.apply(get_ward_code, axis=1)

        # ĐÃ SỬA CHỖ NÀY: Khoan hồng hơn, chỉ xóa nếu mất Tỉnh hoặc Quận. Nếu Phường map tạch thì gán None, giữ lại bài.
        df = df.dropna(subset=['province_code', 'district_code'])
        print(f"✅ Số dòng giữ lại sau khi map địa chỉ: {len(df)}")
        
        if df.empty:
            print("❌ LỖI DATA: Toàn bộ dữ liệu đã bị xóa do không map được Tỉnh/Quận! (Hãy check lại file CSV Master Data)")
            return None

        # =========================================================

        str_cols = ["title", "property_type_name", "street_name", "ward_name", "district_name", "house_direction", "legal_status", "description"]
        df[str_cols] = df[str_cols].fillna("Không xác định")

        def build_raw_content(row):
            return (f"Bất động sản: {row['title']}. Địa chỉ: {row['street_name']}, {row['ward_name']}, {row['district_name']}. "
                    f"Diện tích: {row['area']}m2, Giá: {row['price']} VNĐ. Mô tả: {row['description']}")[:2000]
        df['raw_content'] = df.apply(build_raw_content, axis=1)

        def build_extracted_json(row):
            detail_dict = {
                "title": row.get("title"), "bedroom_count": row.get("bedroom_count"),
                "bathroom_count": row.get("bathroom_count"), "frontage_width": row.get("frontage_width")
            }
            return json.dumps({k: v for k, v in detail_dict.items() if pd.notna(v)}, ensure_ascii=False)
        
        df['extracted_json'] = df.apply(build_extracted_json, axis=1)
        df['confidence_score'] = 0.95
        df['status'] = 'SUCCESS'

        if 'vector_embedding' in df.columns:
            df = df.rename(columns={'vector_embedding': 'embedding'})
        elif 'embedding' not in df.columns:
            df['embedding'] = None

        target_columns = [
            'source_url', 'raw_content', 'extracted_json', 'confidence_score',
            'province_code', 'district_code', 'ward_code', 
            'property_type', 'price', 'area', 'price_per_m2',
            'status', 'embedding'
        ]
        
        out_df = df[[c for c in target_columns if c in df.columns]]
        clean_path = raw_path.replace("raw_", "clean_")
        out_df.to_csv(clean_path, index=False, quoting=csv.QUOTE_ALL, escapechar='\\')
        print(f"🎯 File Cleaned sẵn sàng: {clean_path}")
        return clean_path

    except Exception as e:
        print(f"❌ Lỗi nội bộ Transform Pandas: {e}")
        import traceback
        traceback.print_exc()
        return None