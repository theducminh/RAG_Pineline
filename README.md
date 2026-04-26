# RAG-Pipeline: Hệ thống Data Pipeline Bất Động Sản

Đây là dự án tự động thu thập và xử lý dữ liệu bất động sản, sau đó đưa vào cơ sở dữ liệu Vector để phục vụ cho AI (RAG Chatbot). Hệ thống được quản lý và chạy tự động hàng ngày bằng Apache Airflow.

## 🏗 Kiến trúc tổng quan
Hệ thống hoạt động theo 4 bước cơ bản (ETL):
1. **Extract (Cào dữ liệu):** Lấy dữ liệu nhà đất thô từ Chợ Tốt và HuggingFace.
2. **Transform (Làm sạch):** Dùng Pandas để lọc bỏ dữ liệu rác, tính toán giá/m2 và chuẩn hóa thông tin.
3. **Embedding ():** Đưa dữ liệu qua HuggingFace API để biến văn bản thành các vector số (AI mới hiểu được).
4. **Load (Lưu trữ):** Đẩy dữ liệu đã xử lý lên Supabase (PostgreSQL + pgvector).

---

## 💻 Hướng dẫn Cài đặt & Chạy (Dành cho người mới)

Dự án này được cấu hình tốt nhất để chạy trên môi trường **Linux** hoặc **WSL2 (Ubuntu) trên Windows**.

### Bước 1: Tải code về máy
Mở Terminal (Ubuntu/WSL2) và chạy lệnh sau:
```Bash
git clone https://github.com/theducminh/RAG_Pineline.git
cd RAG_Pineline
```

### Bước 2: Cấu hình Khóa bảo mật (API Keys)
Tạo một file mới tên là `.env` nằm ngay trong thư mục gốc của dự án. Copy và điền các thông số sau vào file:

```Bash
HUGGINGFACE_API_KEY=hf_xxxx...
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhxxxx...
SUPABASE_DB_URL=postgresql://postgres.xxxx:[PASSWORD]@[aws-1-ap-northeast-2.pooler.supabase.com:5432/postgres]

AIRFLOW__WEBSERVER__SECRET_KEY=Diền-bừa-vào-đây
AIRFLOW_UID=1000
```
(Hỏi người quản lý dự án để lấy các đoạn mã xxxx thực tế. Tham số AIRFLOW_UID=1000 bắt buộc phải có để map quyền tạo/sửa file đúng với user của máy host).

### Bước 3: Build Image và Khởi tạo Database Airflow
Do pipeline có sử dụng thêm các thư viện xử lý data và AI bên ngoài (như pandas, huggingface_hub, supabase), ta cần build custom image dựa trên image gốc của Airflow:

```Bash
# Build custom image theo requirements.txt
docker compose build

# Khởi tạo các bảng dữ liệu metadata cho DB của Airflow
docker compose --profile init up airflow-init
```
(Đợi lệnh init chạy xong và báo exited with code 0 trước khi qua bước 4).

### Bước 4: Khởi động Hệ thống
Tiến hành chạy toàn bộ cụm container (Postgres DB, Webserver, Scheduler) dưới nền (background):

```Bash
docker compose up -d
```

### Bước 5: Truy cập giao diện quản lý
Mở trình duyệt web và vào địa chỉ: http://127.0.0.1:8081
(Lưu ý: Port đã được map ra ngoài là `8081` để tránh xung đột với các dịch vụ dùng port `8080` khác trên OS của bạn).

- Tài khoản đăng nhập: `admin`

- Mật khẩu: `admin`

Tại giao diện, bạn có thể bật (unpause) DAG có tên real_estate_rag_pipeline_v2 để hệ thống tự động chạy luồng ETL hàng ngày.

🛑 Cách tắt Hệ thống an toàn
Tuyệt đối không dùng Ctrl+C tắt ngang terminal. Để tắt, dọn dẹp sạch sẽ network của container và giải phóng RAM, hãy chạy:

```Bash
docker compose down
```
(Trong trường hợp bị lỗi hoặc muốn xóa sạch toàn bộ lịch sử chạy của Airflow để bắt đầu lại, hãy thêm cờ `-v` (`docker compose down -v`) để dọn luôn cả dữ liệu Volume).