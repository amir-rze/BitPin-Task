import json

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache
from .models import Article, Rating
from django.db.models import Avg, Count
from django.db import transaction
import redis
from django.utils import timezone
from .classes import ArticlePagination
from BitPin.settings import REDIS_HOST, REDIS_PORT

USER_RATING_CACHE_TTL = 60 * 60  # 1 hour
ARTICLE_CACHE_TTL = 10 * 60  # 10 minutes
CACHE_TTL = 60 * 15  # 15 minutes cache TTL
OUTLIER_THRESHOLD = 2
NUM_RATING_THRESHOLD = 50
MIN_TIME_WINDOW_SECOND = 10
MID_TIME_WINDOW_SECOND = 60
WEIGHT = 1.0
# Initialize Redis
r = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=0)


class RatingView(APIView):

    def calculate_simple_avg(self, article, new_score):

        article.num_ratings += 1
        article.avg_rating = (article.avg_rating * (article.num_ratings - 1) + new_score) / article.num_ratings
        article.last_rating_time = timezone.now()
        article.save()
        return article.avg_rating

    def calculate_ema(self, article, new_score):

        diff = timezone.now() - article.last_rating_time
        diff_seconds = diff.total_seconds()

        if diff_seconds <= MIN_TIME_WINDOW_SECOND:
            alpha = 0.02  # Lower alpha for recent ratings
        elif (diff_seconds < MID_TIME_WINDOW_SECOND) and (diff_seconds > MIN_TIME_WINDOW_SECOND):
            alpha = 0.1  # Higher alpha for older ratings
        else:
            alpha = 0.3

        # Calculate new EMA
        article.avg_rating = alpha * new_score + (1 - alpha) * article.avg_rating
        article.num_ratings += 1
        article.last_rating_time = timezone.now()
        article.save()
        return article.avg_rating

    def get_article_from_cache_or_db(self, article_id):

        cache_key = f"article_{article_id}"
        cached_article = r.hgetall(cache_key)

        if cached_article:
            article_data = {k.decode(): v.decode() for k, v in cached_article.items()}
            return Article(**article_data)

        try:
            article = Article.objects.get(id=article_id)
        except Article.DoesNotExist:
            return None

        r.hmset(cache_key, {
            "id": article.id,
            "title": article.title,
            "content": article.content,
            "num_ratings": article.num_ratings,
            "avg_rating": article.avg_rating,
            "last_rating_time": article.last_rating_time.isoformat()
        })
        return article

    def post(self, request, article_id):

        user_id = request.data.get('user_id')
        score = request.data.get('score')

        if not (1 <= score <= 5):
            return Response({'error': 'Score must be between 1 and 5'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # Update or create rating
            rating, created = Rating.objects.update_or_create(
                article_id=article_id, user_id=user_id,
                defaults={'score': score}
            )

        article = self.get_article_from_cache_or_db(article_id)
        if not article:
            return Response({'error': 'Article not found'}, status=status.HTTP_404_NOT_FOUND)

        if article.num_ratings < NUM_RATING_THRESHOLD:
            new_avg = self.calculate_simple_avg(article, score)
        else:
            new_avg = self.calculate_ema(article, score)

        cache_key = f"article_{article_id}"
        r.hmset(cache_key, {
            "id": article.id,
            "title": article.title,
            "content": article.content,
            "num_ratings": article.num_ratings,
            "avg_rating": article.avg_rating,
            "last_rating_time": article.last_rating_time.isoformat()
        })

        return Response({
            'message': 'Rating submitted successfully',
            'new_avg_rating': new_avg
        }, status=status.HTTP_200_OK)


class ArticleListView(APIView):
    pagination_class = ArticlePagination

    def get(self, request):
        user_id = request.query_params.get('user_id')

        cached_article_list = r.get('article_list')

        if cached_article_list:
            article_list = json.loads(
                cached_article_list)
        else:
            articles = Article.objects.all().values('id', 'title', 'num_ratings', 'avg_rating')

            article_list = []
            for article in articles:
                article_data = {
                    'id': article['id'],
                    'title': article['title'],
                    'num_ratings': article['num_ratings'],
                    'avg_rating': article['avg_rating'],
                    'user_rating': None
                }
                article_list.append(article_data)

            r.set('article_list', json.dumps(article_list), ex=ARTICLE_CACHE_TTL)

        if user_id:
            user_rating_key = f"user_ratings_{user_id}"
            cached_user_ratings = r.hgetall(user_rating_key)

            if cached_user_ratings:
                user_ratings = {int(k): int(v) for k, v in
                                cached_user_ratings.items()}
            else:
                user_ratings = Rating.objects.filter(user_id=user_id).values_list('article_id', 'score')
                user_ratings = {article_id: score for article_id, score in user_ratings}

                if user_ratings:
                    r.set(user_rating_key, json.dumps(user_ratings), ex=USER_RATING_CACHE_TTL)

            for article_data in article_list:
                article_id = article_data['id']
                article_data['user_rating'] = user_ratings.get(article_id, None)  # None if no user rating exists

        paginator = self.pagination_class()
        paginated_articles = paginator.paginate_queryset(article_list, request)
        return paginator.get_paginated_response(paginated_articles)
