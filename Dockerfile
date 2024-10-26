FROM python:3.10

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Tạo thư mục cho ứng dụng
WORKDIR /app

# Cài đặt các dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ mã nguồn vào container
COPY ./backend /app/
# Chạy lệnh khởi động server bằng Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8001", "backend.wsgi:application"]
