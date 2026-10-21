#!/usr/bin/env bash
# Cài môi trường chạy Phase 2 trên Ubuntu / WSL2 (giống môi trường đã chạy thực tế).
#   bash scripts/setup_spark_linux.sh
set -e
sudo apt-get update
sudo apt-get install -y openjdk-17-jre-headless python3-venv python3-pip
python3 -m venv .venv-spark
. .venv-spark/bin/activate
pip install -U pip setuptools wheel
pip install -r requirements-spark.txt
# Máy không phân giải được hostname thì Spark không khởi động (lỗi UnknownHostException)
echo 'export SPARK_LOCAL_HOSTNAME=localhost' >> ~/.bashrc
python -c "import pyspark; print('PySpark', pyspark.__version__, 'OK')"
