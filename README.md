# RAG-Pineline
1. Cài Ubunru 22.04 trong Microsoft Store

2. Cập nhật hệ thống
sudo apt update && sudo apt upgrade -y
sudo apt install software-properties-common -y
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt install python3.9 python3.9-venv python3.9-dev libpq-dev build-essential libre2-dev -y

3. Cài đặt Java & Spark Runtime
sudo apt install openjdk-11-jdk -y
# Kiểm tra đường dẫn để cấu hình môi trường
readlink -f $(which java)


4. Tạo virtual environment (.venv)
cd ~
python3.9 -m venv rag_env
source ~/rag_env/bin/activate
pip install --upgrade pip setuptools wheel

5. Cài thư viện
Tạo file requirements.txt:
numpy==1.26.4
pandas==2.2.3
requests==2.32.3
pyspark==3.5.2
selenium==4.21.0
beautifulsoup4
supabase
python-dotenv
psycopg2-binary

# Cài Airflow bằng file ràng buộc (Constraints) để né lỗi biên dịch
PYTHON_VERSION="3.9"
CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-2.9.1/constraints-${PYTHON_VERSION}.txt"
pip install "apache-airflow==2.9.1" --constraint "${CONSTRAINT_URL}" --no-cache-dir

# Cài các thư viện còn lại trong file của cậu
pip install -r "/mnt/d/Do an tot nghiep 2026/RAG Pineline/requirements.txt" --no-cache-dir


7. Cấu hình Biến môi trường (Vào .bashrc)
echo 'export AIRFLOW_HOME="/mnt/d/Do an tot nghiep 2026/RAG Pineline/airflow_home"' >> ~/.bashrc
echo 'export PYTHONPATH="/mnt/d/Do an tot nghiep 2026/RAG Pineline"' >> ~/.bashrc
echo 'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64' >> ~/.bashrc
source ~/.bashrc



9. Setup Airflow
cd "/mnt/d/Do an tot nghiep 2026/RAG Pineline"
airflow db init



10. Tạo user
airflow users create \
  --username admin \
  --firstname Duc \
  --lastname Minh \
  --role Admin \
  --email minhchoi2004@gmail.com \
  --password admin

11. Xử lý Selenium & Chrome trên WSL2
# Cài đặt Google Chrome bản ổn định cho Linux
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install ./google-chrome-stable_current_amd64.deb -y


12. Check Health 
python3 -c "import pyspark; import airflow; import supabase; print('🚀 Mọi thứ đã sẵn sàng!')"

13. Import path trong DAG
PROJECT_ROOT = "/mnt/d/Do an tot nghiep 2026/RAG Pineline"
import sys
sys.path.insert(0, PROJECT_ROOT)

14. Chạy Airflow
#!/bin/bash
source ~/airflow_env/bin/activate
export AIRFLOW_HOME="/mnt/d/Do an tot nghiep 2026/RAG Pineline/airflow_home"
airflow webserver --port 8081 & airflow scheduler

15. Mở UI ở http://localhost:8081
Login với admin / admin

16. Cài đặt PostgreSQL Local và LocalExecutor
# Cập nhật và cài đặt
sudo apt update
sudo apt install postgresql postgresql-contrib -y

# Khởi động dịch vụ (Mẹo: Mỗi lần bật máy Ubuntu lên phải chạy lệnh này)
sudo service postgresql start

# Tạo User và Database riêng cho Airflow
sudo -u postgres psql

CREATE USER airflow_user WITH PASSWORD 'airflow_pass';
CREATE DATABASE airflow_db OWNER airflow_user;
GRANT ALL PRIVILEGES ON DATABASE airflow_db TO airflow_user;
\q

#  Cấu hình Airflow sử dụng Postgres
nano "/mnt/d/Do an tot nghiep 2026/RAG Pineline/airflow_home/airflow.cfg"

+ Chuyển sang LocalExecutor: executor = LocalExecutor
+ Kết nối Database : sql_alchemy_conn = postgresql+psycopg2://airflow_user:airflow_pass@localhost:5432/airflow_db

# Khởi tạo lại Database 
source ~/airflow_env/bin/activate

# Khởi tạo lại (Airflow sẽ tự tạo các bảng metadata trên Supabase)
airflow db init

# Tạo lại User Admin vì đây là Database mới
airflow users create \
  --username admin \
  --firstname Duc \
  --lastname Minh \
  --role Admin \
  --email minhchoi2004@gmail.com \
  --password admin

# Mở file cấu hình
nano "/mnt/d/Do an tot nghiep 2026/RAG Pineline/airflow_home/airflow.cfg"
dags_folder = /mnt/d/Do an tot nghiep 2026/RAG Pineline/dags
  
# Xóa file PID cũ nếu còn kẹt
rm -rf "/mnt/d/Do an tot nghiep 2026/RAG Pineline/airflow_home"/*.pid
airflow dags list

# Giết tiến trình cũ (nếu có) và chạy mới
pkill -f airflow
airflow webserver --port 8081 &
airflow scheduler &


# RAG_Pineline
