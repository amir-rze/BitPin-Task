# Rating System
Implemented in Python/Django , Postgresql , Redis , Celery

# Logic


### Run locally
- Fill out `.env.example` and rename it to `.env`.
- Create virtualenv
- pip install -r requirements.txt.
- Start Postgresql , Redis 
- python manage.py makemigrations
- python manage.py migrate
- python manage.py populate_db <Articles_Count> # to fill database with random data
- run celery
  - celery -A BitPin worker -l info
  - celery -A BitPin beat -l info
- python manage.py runserver <Port>
