# Rating System
Implemented in Python/Django , Postgresql , Redis , Celery

## API Endpoints
### Rate an Article

- **Endpoint:** `/articles/{article_id}/rate/`
- **Method:** POST
- **Description:** Allows a user to rate an article.
- **Request Body:**
    ```json
    {
      "user_id": "<user_id>",
      "score": <rating_score (0-5)>
    }
    ```

### List Articles with Pagination

- **Endpoint:** `/articles/`
- **Method:** GET
- **Description:** Retrieve a paginated list of articles with ratings.
- **Optional Query Params:**
  - `user_id`: If provided, the user-specific rating will be included in the response.
  
## Caching Strategy

- **Article Data Cache:** Article data is cached for 10 minutes to reduce database hits.
- **User Rating Cache:** User-specific ratings are cached for 1 hour to optimize performance when listing articles.
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
