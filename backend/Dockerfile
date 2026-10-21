# Image của API. Build từ THƯ MỤC GỐC project (cần cả common/ chứa data contract):
#   docker compose build api        (xem docker-compose.yml ở thư mục gốc)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/srv

WORKDIR /srv/backend
COPY backend/requirements.txt /srv/backend/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY common /srv/common
COPY backend /srv/backend

EXPOSE 8000
# Tạo/cập nhật bảng (Alembic) rồi chạy API. Dữ liệu được nạp bằng lệnh riêng (xem docs/huong-dan/18_...).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
