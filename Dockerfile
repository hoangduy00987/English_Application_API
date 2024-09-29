# Chọn image cơ sở
FROM python:3.8

# Thiết lập thư mục làm việc trong container
WORKDIR /app

# Sao chép tệp yêu cầu vào container
COPY requirements.txt /app/

# Cài đặt các gói yêu cầu
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ mã nguồn vào container
COPY . /app/

# Chạy migrate khi container khởi động
# CMD ["python", "manage.py", "migrate"]

# Nếu cần chạy server, có thể thêm lệnh này:
CMD ["python", "/app/backend/manage.py", "runserver", "0.0.0.0:8000"]
