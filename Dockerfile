FROM apache/airflow:2.9.1-python3.10

USER airflow
# Copy requirements và cài đặt
COPY requirements.txt /
RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" -r /requirements.txt