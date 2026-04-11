# extract_data/extract_house.py

import os, json, datetime, requests, csv, time

def extract_house(limit_rows=100):
    today = datetime.date.today().isoformat()
    download_dir = f"data_input/house/{today}"
    os.makedirs(download_dir, exist_ok=True)
    
    # 1. Lấy danh sách ID tin đăng (Vòng lặp lấy đủ số lượng limit)
    ids = []
    page = 0
    while len(ids) < limit_rows:
        url_list = f"https://gateway.chotot.com/v1/public/ad-listing?region_v2=12000&cg=1000&o={page*20}&limit=20"
        resp = requests.get(url_list, headers={"User-Agent": "Mozilla/5.0"}).json()
        ads = resp.get("ads", [])
        if not ads: break
        for ad in ads:
            if "list_id" in ad: ids.append(ad["list_id"])
        page += 1
        if page > 10: break # Tránh vòng lặp vô hạn

    # 2. Lấy chi tiết từng tin và map vào schema đồ án
    rows = []
    for ad_id in ids[:limit_rows]:
        try:
            url_detail = f"https://gateway.chotot.com/v1/public/ad-listing/{ad_id}"
            res = requests.get(url_detail, headers={"User-Agent": "Mozilla/5.0"}).json()
            detail = res.get("ad", {})
            params = detail.get("parameters", [])
            
            # Hàm nhanh để bóc tách thông số kỹ thuật (Số phòng, hướng, pháp lý...)
            get_v = lambda label: next((p.get("value") for p in params if p.get("label") == label), None)

            row = {
                "id": detail.get("list_id"),
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
                # Trích xuất các trường quan trọng cho AI Advisor & Smart Filter
                "bedroom_count": get_v("Số phòng ngủ"),
                "bathroom_count": get_v("Số phòng vệ sinh"),
                "floor_count": get_v("Số tầng"),
                "house_direction": get_v("Hướng cửa chính"),
                "legal_status": get_v("Giấy tờ pháp lý"),
                "road_width": get_v("Độ rộng đường trước nhà"),
                "frontage_width": get_v("Chiều ngang"),
                "house_depth": get_v("Chiều dài"),
                "published_at": detail.get("list_time"),
                "images_count": len(detail.get("images", []))
            }
            rows.append(row)
            print(f"Successfully extracted: {ad_id}")
            time.sleep(0.4) # Tránh bị block IP
        except Exception as e:
            print(f"Error at {ad_id}: {e}")

    # 3. Lưu file CSV
    if not rows: return None
    out_csv = os.path.join(download_dir, f"raw_{int(time.time())}.csv")
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    
    return out_csv

if __name__ == "__main__":
    path = extract_house(limit_rows=10) # Test thử 10 tin
    print(f"Saved to: {path}")