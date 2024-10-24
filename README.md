# Rating System
Implemented in Python/Django , Postgresql , Redis , Celery

## Logic
### Using Exponential Moving Average With Dynamic Alpha Calculation

In this project, we use a dynamic approach to calculate the Exponential Moving Average (EMA) for article ratings. The method `calculate_dynamic_alpha` adjusts the weight given to new ratings based on the time difference between the current rating and the previous one. This allows the system to:
- Give more weight to recent ratings. 
- Smoothly update the EMA over time.

#### How it Works:

- **Alpha Calculation**: The function calculates `alpha`, a weight factor that determines how much the new rating affects the existing EMA.
  - `alpha` increases as the time between ratings increases, meaning newer ratings have a larger impact if there's been a significant time gap.
  - When the time gap is very small, the function reduces `alpha` if the new rating looks like an outlier, to prevent it from distorting the average.

- **Key Parameters**:
  - `K`: A constant (default 86400 seconds, i.e., 1 day) that determines how quickly the EMA adjusts.
  - `MIN_TIME_WINDOW_SECOND`: A threshold to prevent very frequent ratings from disproportionately affecting the EMA.
  - `OUTLIER_THRESHOLD`: Helps detect outliers and reduce their impact when the time gap is small.

By using this approach, the system adapts to user behavior and provides a more reliable representation of an article's average rating over time.

## Optimization
### Database Sync with Celery

To optimize performance and prevent excessive database hits, we use **Celery** to periodically synchronize the article data between the database and Redis. This approach ensures that frequently accessed data, such as article ratings and user interactions, is cached in Redis, minimizing the need for direct database queries on each API request.

#### How it Works:

- **Sync Task**: A Celery task runs every 5 minutes to update the Redis cache with the latest article data from the database. This ensures that the cache stays up-to-date without overwhelming the database.
  
- **Benefits**:
  - Reduces the number of direct database queries, especially for high-traffic endpoints like article listings and user ratings.
  - Improves API response time by serving cached data from Redis whenever possible.
  - Ensures data consistency by periodically refreshing the cache with the latest information from the database.

#### Configuration:

- Celery is configured to run a scheduled task every 5 minutes using a periodic task scheduler (e.g., Celery Beat).
- Redis serves as the message broker and caching layer, ensuring smooth communication between Celery and the Django application.

By using this periodic syncing mechanism, the system achieves a balance between up-to-date data and reduced load on the database.

### Article List with Redis Caching

The `ArticleListView` API uses **Redis** to cache the list of articles and user-specific ratings, improving performance by minimizing database queries.
We also didn't use django model serializers to have better performance!
#### How It Works:

1. **Article List Caching**:
   - When a request is made to fetch the list of articles, the view first checks if the article list is cached in Redis.
   - If cached (`article_list`), the data is retrieved directly from Redis, eliminating the need for a database query.
   - If the article list is not cached, the view queries the database to retrieve the articles' IDs, titles, number of ratings, and average ratings. The retrieved data is then stored in Redis for future requests.
   - The cache is set to expire after a configurable time period (10 minutes by default), ensuring that the data remains reasonably up-to-date without overwhelming the database.

2. **User-Specific Ratings Caching**:
   - If a `user_id` is provided in the request, the API checks whether the user's ratings are cached in Redis (`user_ratings_{user_id}`).
   - If user ratings are cached, they are retrieved and added to the article list response.
   - If not cached, the view queries the database for the user's ratings and caches the result in Redis for 1 hour, preventing repetitive queries for the same user.
   
3. **Pagination**:
   - The list of articles is paginated using a custom pagination class (`ArticlePagination`) to ensure the response is manageable even for large datasets.

#### Redis Cache Keys:

- **`article_list`**: Caches the entire list of articles for 10 minutes.
- **`user_ratings_{user_id}`**: Caches the user's ratings for 1 hour.

#### Benefits of Caching:
- Reduces the load on the database by serving cached data.
- Improves API response times, especially for frequently requested data.
- Ensures that user-specific information (such as their ratings) is included in the article list without constantly querying the database.

By using Redis as a caching layer, the `ArticleListView` can efficiently handle high-traffic requests while keeping the data fresh and responsive.
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
