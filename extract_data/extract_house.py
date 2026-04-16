# extract_data/extract_house.py
import os, json, datetime, requests, csv, time, uuid

def extract_chotot(limit_rows):
    """Cào dữ liệu từ Gateway API của Chợ Tốt"""
    print(f"🔄 Đang cào {limit_rows} tin từ Chợ Tốt...")
    ids = []
    page = 0
    # Cần logic retry/backoff ở production, nhưng hiện tại giữ cấu trúc cũ
    while len(ids) < limit_rows:
        url_list = f"https://gateway.chotot.com/v1/public/ad-listing?region_v2=12000&cg=1000&o={page*20}&limit=20"
        try:
            resp = requests.get(url_list, headers={"User-Agent": "Mozilla/5.0"}).json()
            ads = resp.get("ads", [])
            if not ads: break
            for ad in ads:
                if "list_id" in ad: ids.append(ad["list_id"])
        except Exception as e:
            print(f"Lỗi lấy danh sách Chợ Tốt: {e}")
            break
        page += 1
        if page > 10: break

    rows = []
    for ad_id in ids[:limit_rows]:
        try:
            url_detail = f"https://gateway.chotot.com/v1/public/ad-listing/{ad_id}"
            res = requests.get(url_detail, headers={"User-Agent": "Mozilla/5.0"}).json()
            detail = res.get("ad", {})
            params = detail.get("parameters", [])
            
            get_v = lambda label: next((p.get("value") for p in params if p.get("label") == label), None)

            row = {
                "id": str(detail.get("list_id")),
                "title": detail.get("subject"),
                "description": detail.get("body"),
                "property_type_name": detail.get("property_type_name"),
                "province_name": detail.get("region_name"),
                "district_name": detail.get("area_name"),
                "ward_name": detail.get("ward_name"),
                "street_name": detail.get("street_name"),
                "project_name": detail.get("project_name"),
                "price": detail.get("price"),
                "area": detail.get("area"),
                "lat": detail.get("latitude"),
                "lng": detail.get("longitude"),
                "bedroom_count": get_v("Số phòng ngủ"),
                "bathroom_count": get_v("Số phòng vệ sinh"),
                "floor_count": get_v("Số tầng"),
                "house_direction": get_v("Hướng cửa chính"),
                "legal_status": get_v("Giấy tờ pháp lý"),
                "road_width": get_v("Độ rộng đường trước nhà"),
                "frontage_width": get_v("Chiều ngang"),
                "house_depth": get_v("Chiều dài"),
                "published_at": datetime.datetime.fromtimestamp(detail.get("list_time") / 1000).isoformat(),
                "images_count": len(detail.get("images", []))
            }
            rows.append(row)
            time.sleep(0.4) 
        except Exception as e:
            print(f"Lỗi tại Chợ Tốt ID {ad_id}: {e}")
            
    return rows

def extract_huggingface(limit_rows):
    """Kéo dữ liệu từ dataset Hugging Face bằng Streaming để tránh OOM"""
    print(f"🔄 Đang kéo {limit_rows} tin từ Hugging Face (tinixai/vietnam-real-estates)...")
    try:
        from datasets import load_dataset
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("❌ Chưa cài thư viện datasets. Hãy chạy: pip install datasets")
        return []

    # Bắt buộc dùng streaming=True để không load file Parquet khổng lồ vào RAM
    ds = load_dataset("tinixai/vietnam-real-estates", split="train", streaming=True, token=os.getenv('HUGGINGFACE_API_KEY'))
    
    rows = []
    for item in ds.take(limit_rows):
        rows.append({
            "id": f"hf_{uuid.uuid4().hex[:10]}",  # Tự sinh ID ảo
            "title": item.get("name"),
            "description": item.get("description"),
            "property_type_name": item.get("property_type_name"),
            "province_name": item.get("province_name"),
            "district_name": item.get("district_name"),
            "ward_name": item.get("ward_name"),
            "street_name": item.get("street_name"),
            "project_name": item.get("project_name"),
            "price": item.get("price"),
            "area": item.get("area"),
            "lat": None, # Tác giả đã xóa khỏi repo
            "lng": None, # Tác giả đã xóa khỏi repo
            "bedroom_count": item.get("bedroom_count"),
            "bathroom_count": item.get("bathroom_count"),
            "floor_count": item.get("floor_count"),
            "house_direction": item.get("house_direction"),
            "legal_status": "Không xác định", # Tác giả đã xóa cột legal_paper
            "road_width": item.get("road_width"),
            "frontage_width": item.get("frontage"),
            "house_depth": item.get("depth"),
            "published_at": item.get("published_at"),
            "images_count": 0
        })
    return rows

def extract_house(limit_rows=100):
    today = datetime.date.today().isoformat()
    download_dir = f"data_input/house/{today}"
    os.makedirs(download_dir, exist_ok=True)
    
    # Chia đều số lượng cho 2 nguồn
    limit_per_source = limit_rows // 2
    
    rows = []
    rows.extend(extract_chotot(limit_per_source))
    rows.extend(extract_huggingface(limit_per_source))

    if not rows:
        print("❌ Không lấy được dữ liệu từ nguồn nào.")
        return None

    out_csv = os.path.join(download_dir, f"raw_{int(time.time())}.csv")
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"✅ Đã lưu {len(rows)} dòng dữ liệu gộp vào: {out_csv}")
    return out_csv

if __name__ == "__main__":
    # Chạy độc lập để test
    path = extract_house(limit_rows=20)