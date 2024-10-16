docker-compose up --build -d
chay cau lenh nay ->  docker-compose up --build

chay cau lenh nay de tao superuser
docker-compose run --rm web sh -c "python manage.py createsuperuser"

k can makemigrations hay migrate gi ca vi khi chay 
docker-compose up --build han se tu dong lam cho r

khi thay doi gi trong 2 file docker moi can chay lenh ni tren server
docker-compose up --build -d